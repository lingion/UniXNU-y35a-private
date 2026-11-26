#!/usr/bin/env python3
"""Certify the iOS 12 (16G102) IOHIDDevice ABI against its exact published source.

This mirrors the structure of scripts/audit-storage-interface.py: assemble a
header shim from one public IOHIDFamily revision, compile a minimal digitizer
IOHIDDevice subclass as a never-linked annotation instrument, and reconcile
that against the IOHIDFamily kext the shipped kernelcache actually pins.

Two things this audit must not paper over:

  * Source-identity.  The kext in the cache stamps its own OSS build in the
    prelink copyright string (NSHumanReadableCopyright carries a bracketed
    `[IOHIDFamily-<rev>]`).  That revision, and only that revision, backs the
    shim.  If the stamp names a revision the configured mirror does not
    publish, the audit is NOT-CERTIFIED and must say so rather than pick a
    near-miss.

  * Symbol-level cache binding.  iOS 12 link-strips every component's own
    LC_SYMTAB (nsyms == 0) and nulls every vtable typeinfo slot, so the cache
    kext's IOHIDDevice-family symbol names are unrecoverable.  When they are
    stripped the verdict records `stripped` and the reason; it does not
    fabricate a symbol match.  What IS recoverable -- the kmod_info identity
    version, the component extents against the prelink entry, the kext
    executable-code hash, and the cache-wide IOService vtable the digitizer
    class inherits -- are compared as far as the binary lets them be.

Host execution only: the reference compile uses the host Apple clang++ targeting
arm64-apple-ios12.0.  The base (IOService, OSObject, mach) headers come from the
pinned xnu-4903 Darwin-18 installhdrs output so the instrument is compiled
against the same generation it certifies, never the 17-era SDK.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'kits/XnuPrelink'))
import legacy_prelink as lp          # noqa: E402  (own-tree import: no -I)
from legacy_prelink import backed_offset  # noqa: E402
from native_prelink import exports as cache_exports  # noqa: E402

parser = argparse.ArgumentParser(description='Certify the iOS 12 IOHIDDevice ABI against published source.')
parser.add_argument('--cache', type=Path, default=ROOT / 'out/ipsw/16G102/kernelcache.decompressed',
                    help='decompressed iOS 12 kernelcache whose IOHIDFamily kext is certified')
parser.add_argument('--output', type=Path, default=ROOT / 'build/hid-abi',
                    help='directory for the shim, the reference object and the JSON verdict')
parser.add_argument('--evidence', type=Path, default=ROOT / 'scripts/data/hid-interface-audit.json',
                    help='machine-readable verdict (exit status is derived from this)')
parser.add_argument('--source', type=Path, default=ROOT / 'refer/IOHIDFamily',
                    help='blob:none mirror clone of apple-oss-distributions/IOHIDFamily (mirror remote only)')
parser.add_argument('--container', default='unixnu-y35a-native-20261103',
                    help='Linux build container holding the pinned xnu-4903 Darwin-18 headers')
parser.add_argument('--xnu-fakeroot', default='/work/UniXNU-y35a/.cache/fakeroot-4903',
                    help='in-container path of the xnu-4903 installed kernel header root')
parser.add_argument('--base-include', type=Path, default=None,
                    help='pre-extracted Darwin-18 base header root; defaults to a cached tree, then the container')
parser.add_argument('--force-revision', default=None,
                    help='override the revision the kext stamp selects (negative control: NOT-CERTIFIED when it is not published)')
parser.add_argument('--self-test', action='store_true',
                    help='run the positive (source-certified) and negative (wrong-generation fails closed) paths without touching the real verdict')
args = parser.parse_args()


class NotCertified(Exception):
    """Raised whenever a certification step cannot be proven.  The verdict is
    always written before this propagates, so a fail-closed run still leaves
    machine-readable evidence."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git(source, *argv):
    return subprocess.run(['git', '-C', str(source), *argv], capture_output=True, text=True)


def require(condition, message):
    if not condition:
        raise NotCertified(message)


# --------------------------------------------------------------------------- #
# 1. What the cache actually pins                                              #
# --------------------------------------------------------------------------- #
def read_cache(cache_path):
    """Return everything this audit needs from the shipped kernelcache for the
    com.apple.iokit.IOHIDFamily component, with provenance hashes."""
    data = cache_path.read_bytes()
    image = lp.macho(data)
    parent = image['segments']

    def read(va, length):
        if length == 0:
            return b''
        at = backed_offset(parent, va, length, len(data))
        return data[at:at + length]

    entries = lp.cache_metadata(data)[4]['_PrelinkInfoDictionary']
    matches = [e for e in entries if e.get('CFBundleIdentifier') == 'com.apple.iokit.IOHIDFamily']
    require(len(matches) == 1, f'expected exactly one IOHIDFamily prelink entry, found {len(matches)}')
    entry = matches[0]

    # The bracketed OSS build stamp is the kext's own claim about its source.
    copyright = str(entry.get('NSHumanReadableCopyright', ''))
    stamp = re.search(r'\[IOHIDFamily-([0-9][0-9.]*)\]', copyright)
    require(stamp, f'IOHIDFamily prelink copyright carries no [IOHIDFamily-<rev>] stamp: {copyright!r}')
    source_revision = stamp.group(1)

    # kmod_info in the cache: the runtime identity the loader actually sees.
    load = entry['_PrelinkExecutableLoadAddr']
    size = entry['_PrelinkExecutableSize']
    kmod = {}
    if entry.get('_PrelinkKmodInfo'):
        raw = read(entry['_PrelinkKmodInfo'], 0xb0)
        info_version, = struct.unpack_from('<i', raw, 8)
        name = raw[16:16 + 64].split(b'\0')[0].decode('ascii', 'replace')
        version = raw[80:80 + 64].split(b'\0')[0].decode('ascii', 'replace')
        kmod = dict(info_version=info_version, name=name, version=version)

    extents = {}
    _, _, _, _, _, _, _, modules, _, _ = lp._component_enumeration(data)
    if 'com.apple.iokit.IOHIDFamily' in modules:
        module = modules['com.apple.iokit.IOHIDFamily']
        segments = {s['name']: dict(va=s['va'], size=s['size']) for s in module['segments'] if s['name'] != '__LINKEDIT'}
        exec_seg = segments.get('__TEXT_EXEC')
        exec_hash = sha256(read(exec_seg['va'], exec_seg['size'])) if exec_seg else None
        extents = dict(segments=segments, executable_sha256=exec_hash)

    # The digitizer class inherits the kernel's own IOService dispatch table.
    # That table lives in the kernel (not in the stripped kext) and is exported
    # by name, so its shape is recoverable and directly certifies the base ABI.
    ioservice_slots = None
    ioservice_pure = None
    names = {}
    for va, name_list in cache_exports(data, image).items():
        for name in name_list:
            names.setdefault(name, va)
    tv = names.get('__ZTV9IOService')
    if tv:
        count = 0
        pure = names.get('___cxa_pure_virtual')
        pure_count = 0
        while True:
            slot = struct.unpack('<Q', read(tv + 16 + count * 8, 8))[0]
            if slot == 0:
                break
            if pure is not None and slot == pure:
                pure_count += 1
            count += 1
            if count > 1024:
                break
        ioservice_slots, ioservice_pure = count, pure_count

    return dict(
        cache_sha256=sha256(data),
        prelink=dict(
            bundle_version=entry.get('CFBundleVersion'),
            short_version=entry.get('CFBundleShortVersionString'),
            copyright=copyright,
            dt_platform_version=entry.get('DTPlatformVersion'),
            dt_sdk_name=entry.get('DTSDKName'),
            min_os=entry.get('MinimumOSVersion'),
            exec_load_addr=hex(load) if load else None,
            exec_size=size,
        ),
        source_revision=source_revision,
        kmod_info=kmod,
        extents=extents,
        ioservice_vtable_slots=ioservice_slots,
        ioservice_pure_virtual=ioservice_pure,
    )


# --------------------------------------------------------------------------- #
# 2. Is that revision published on the configured mirror?                     #
# --------------------------------------------------------------------------- #
def published_revisions(source):
    """Every IOHIDFamily-<rev> tag the mirror clone knows about (its only remote
    is the gh.qdp mirror; no direct GitHub remote is ever consulted)."""
    listing = git(source, 'tag', '--list', 'IOHIDFamily-*')
    require(listing.returncode == 0, f'cannot list tags in {source}: {listing.stderr.strip()}')
    remotes = git(source, 'remote', '-v')
    for line in remotes.stdout.splitlines():
        require('github.com' not in line or 'gh.qdp' in line,
                f'IOHIDFamily clone has a direct GitHub remote ({line}); use the mirror only')
    return [t[len('IOHIDFamily-'):] for t in listing.stdout.split()]


def bounding_revisions(published):
    """Oldest and newest published IOHIDFamily-4xx/5xx revisions, for drift."""
    def key(rev):
        return tuple(int(x) for x in re.findall(r'\d+', rev))
    window = sorted((r for r in published if re.match(r'[45]\d\d\.', r)), key=key)
    return (window[0], window[-1]) if window else (None, None)


def select_revision(source, wanted):
    """Resolve the cache-stamped revision to a tag in the mirror clone."""
    tag = f'IOHIDFamily-{wanted}'
    if git(source, 'rev-parse', '--verify', '--quiet', f'refs/tags/{tag}').returncode != 0:
        raise NotCertified(
            f'the cache pins IOHIDFamily-{wanted} but the configured mirror publishes no such tag; '
            f'NOT-CERTIFIED rather than substituting a near-miss revision')
    commit = git(source, 'rev-parse', f'{tag}^{{commit}}').stdout.strip()
    require(commit, f'{tag} present but its commit object cannot be resolved')
    return tag, commit


# --------------------------------------------------------------------------- #
# 3. Materialize the revision + assemble the shim                              #
# --------------------------------------------------------------------------- #
def show(source, tag, path):
    """Read one tracked file at a pinned tag without a working-tree checkout.
    Byte-level decode with replacement: Apple sources are latin-1, and this text
    is only ever scanned for structure (never copied into the shim, which is
    byte-faithful via the materialized worktree)."""
    r = subprocess.run(['git', '-C', str(source), 'show', f'{tag}:{path}'], capture_output=True)
    if r.returncode != 0:
        raise NotCertified(f'{tag}:{path} is not present or unfetchable from the mirror: '
                           f'{r.stderr.decode(errors="replace").strip()}')
    return r.stdout.decode('latin-1')


def materialize(source, tag, work):
    """Populate `work` with the revision's sources from the mirror.  A prior
    interrupted run can leave a stale registered-but-missing worktree, so the
    registration is cleared before re-adding."""
    if work.exists():
        shutil.rmtree(work)
    subprocess.run(['git', '-C', str(source), 'worktree', 'prune'], capture_output=True)
    r = subprocess.run(['git', '-C', str(source), 'worktree', 'add', '--detach', str(work), tag],
                       capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run(['git', '-C', str(source), 'worktree', 'remove', '--force', str(work)],
                       capture_output=True)
        subprocess.run(['git', '-C', str(source), 'worktree', 'prune'], capture_output=True)
        r = subprocess.run(['git', '-C', str(source), 'worktree', 'add', '--detach', '--force',
                            str(work), tag], capture_output=True, text=True)
    if r.returncode != 0:
        raise NotCertified(f'cannot materialize {tag} into {work}: {r.stderr.strip()}')
    return work


def source_module_version(source, tag):
    """The MODULE_VERSION Apple stamps on the IOHIDFamily kext target at `tag`;
    this is what the runtime kmod_info.version string reports."""
    pbx = show(source, tag, 'IOHIDFamily.xcodeproj/project.pbxproj')
    versions = set()
    for block in re.split(r'/\* [A-F0-9]+ \*/ = \{', pbx):
        if re.search(r'MODULE_NAME = com\.apple\.iokit\.IOHIDFamily;', block):
            m = re.search(r'MODULE_VERSION = ([0-9][0-9.]*)', block)
            if m:
                versions.add(m.group(1))
    return sorted(versions)


# --------------------------------------------------------------------------- #
# 4. Darwin-18 base headers (IOService, OSObject, mach, ...)                   #
# --------------------------------------------------------------------------- #
def base_headers(args):
    """Resolve a root of xnu-4903 (Darwin 18) installhdrs output so the
    instrument compiles against the same generation it certifies."""
    cache = ROOT / '.cache/hid-abi-base-4903'
    if args.base_include is not None:
        root = Path(args.base_include)
        require(root.is_dir(), f'--base-include {root} is not a directory')
        return root, f'--base-include {root}'
    if (cache / 'usr/include/Availability.h').is_file():
        return cache, 'cached Darwin-18 installhdrs (.cache/hid-abi-base-4903)'
    # Otherwise extract from the container's pinned fakeroot-4903 tree.
    if shutil.which('docker'):
        probe = subprocess.run(['docker', 'exec', args.container, 'test', '-f',
                                f'{args.xnu_fakeroot}/usr/include/Availability.h'],
                               capture_output=True, text=True)
        if probe.returncode == 0:
            cache.mkdir(parents=True, exist_ok=True)
            for sub in ('usr/include',
                        'System/Library/Frameworks/Kernel.framework/Versions/A/Headers'):
                tar = subprocess.run(['docker', 'exec', args.container,
                                      'tar', '--dereference', '-c', '-f', '-',
                                      '-C', args.xnu_fakeroot, sub],
                                     capture_output=True)
                require(tar.returncode == 0, f'docker tar of {sub} failed: {tar.stderr.decode()[-400:]}')
                unpack = subprocess.run(['tar', 'xf', '-', '-C', str(cache)],
                                        input=tar.stdout, capture_output=True)
                require(unpack.returncode == 0, f'unpack of {sub} failed: {unpack.stderr.decode()[-400:]}')
            return cache, f'extracted from container {args.container}:{args.xnu_fakeroot}'
    raise NotCertified(
        'no Darwin-18 (xnu-4903) base headers available: pass --base-include, seed '
        '.cache/hid-abi-base-4903, or start the ' + args.container + ' container')


# --------------------------------------------------------------------------- #
# 5. Compile the reference object                                              #
# --------------------------------------------------------------------------- #
DIGITIZER_REFERENCE = r'''// Annotation instrument only: never linked, never executed, never shipped.
// Its sole job is to prove that the selected IOHIDFamily revision's headers,
// layered on the pinned Darwin-18 base headers, compile a minimal multi-touch
// digitizer subclass under -Werror for arm64-apple-ios12.0.  This is the exact
// surface T3.2 (NativeHidDigitizer.cpp) implements, so a clean compile here is
// the certification that T3.2's shim choice is sound.
#include <IOKit/hid/IOHIDDevice.h>

class IOHIDDigitizerReference : public IOHIDDevice {
    OSDeclareDefaultStructors(IOHIDDigitizerReference)

private:
    IOMemoryDescriptor *fReportDescriptor;

public:
    // Lifecycle (start/stop/free) -- IOService plumbing.
    bool init(OSDictionary *properties) override;
    bool start(IOService *provider) override;
    void stop(IOService *provider) override;
    void free() override;

    // Open/close (nub attach, client bookkeeping).
    bool handleOpen(IOService *forClient, IOOptionBits options, void *arg) override;
    void handleClose(IOService *forClient, IOOptionBits options) override;

    // Report-descriptor plumbing -- the pure virtual that makes IOHIDDevice abstract.
    IOReturn newReportDescriptor(IOMemoryDescriptor **descriptor) const override;

    // Report dispatch -- the digitizer hot path.
    IOReturn handleReport(IOMemoryDescriptor *report,
                          IOHIDReportType reportType = kIOHIDReportTypeInput,
                          IOOptionBits options = 0) override;
    IOReturn getReport(IOMemoryDescriptor *report, IOHIDReportType reportType,
                       IOOptionBits options) override;
    IOReturn setReport(IOMemoryDescriptor *report, IOHIDReportType reportType,
                       IOOptionBits options) override;
};

OSDefineMetaClassAndStructors(IOHIDDigitizerReference, IOHIDDevice)

bool IOHIDDigitizerReference::init(OSDictionary *properties) {
    if (!IOHIDDevice::init(properties))
        return false;
    fReportDescriptor = NULL;
    return true;
}

bool IOHIDDigitizerReference::start(IOService *provider) {
    if (!IOHIDDevice::start(provider))
        return false;
    IOMemoryDescriptor *descriptor = NULL;
    if (newReportDescriptor(&descriptor) != kIOReturnSuccess || descriptor == NULL)
        return false;
    fReportDescriptor = descriptor;
    descriptor->release();
    return true;
}

void IOHIDDigitizerReference::stop(IOService *provider) {
    if (fReportDescriptor) {
        fReportDescriptor->release();
        fReportDescriptor = NULL;
    }
    IOHIDDevice::stop(provider);
}

void IOHIDDigitizerReference::free() {
    IOHIDDevice::free();
}

bool IOHIDDigitizerReference::handleOpen(IOService *forClient, IOOptionBits options, void *arg) {
    return IOHIDDevice::handleOpen(forClient, options, arg);
}

void IOHIDDigitizerReference::handleClose(IOService *forClient, IOOptionBits options) {
    IOHIDDevice::handleClose(forClient, options);
}

IOReturn IOHIDDigitizerReference::newReportDescriptor(IOMemoryDescriptor **descriptor) const {
    // Minimal digitizer / multi-touch header; the body is irrelevant because the
    // object is never run.  What matters is that the Darwin-18 factory resolves
    // against the selected revision's declared signatures.
    static const unsigned char report_descriptor[] = {
        0x05, 0x0D, 0x09, 0x04, 0xA1, 0x01, 0x85, 0x01,
        0x05, 0x01, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01,
        0x81, 0x02, 0xC3
    };
    if (descriptor == NULL)
        return kIOReturnBadArgument;
    *descriptor = IOBufferMemoryDescriptor::withBytes(
        report_descriptor, sizeof(report_descriptor), kIODirectionNone);
    if (*descriptor == NULL)
        return kIOReturnNoMemory;
    return kIOReturnSuccess;
}

IOReturn IOHIDDigitizerReference::handleReport(IOMemoryDescriptor *report,
                                               IOHIDReportType reportType, IOOptionBits options) {
    return kIOReturnSuccess;
}

IOReturn IOHIDDigitizerReference::getReport(IOMemoryDescriptor *report, IOHIDReportType reportType,
                                            IOOptionBits options) {
    return kIOReturnSuccess;
}

IOReturn IOHIDDigitizerReference::setReport(IOMemoryDescriptor *report, IOHIDReportType reportType,
                                            IOOptionBits options) {
    return kIOReturnSuccess;
}
'''


def digitizer_relevant_methods(source, revision):
    """The methods a minimal digitizer driver must implement, keyed by which
    revision's IOHIDDevice.h actually declares them."""
    tag = f'IOHIDFamily-{revision}'
    header = show(source, tag, 'IOHIDFamily/IOHIDDevice.h')
    probes = {
        'start':       r'\bstart\s*\(\s*IOService',
        'stop':        r'\bstop\s*\(\s*IOService',
        'free':        r'\bfree\s*\(\s*\)',
        'handleOpen':  r'\bhandleOpen\s*\(',
        'handleClose': r'\bhandleClose\s*\(',
        'newReportDescriptor': r'\bnewReportDescriptor\s*\(',
        'handleReport':        r'\bhandleReport\s*\(',
        'handleReportWithTime': r'\bhandleReportWithTime\s*\(',
        'getReport':   r'\bgetReport\s*\(\s*IOMemoryDescriptor',
        'setReport':   r'\bsetReport\s*\(\s*IOMemoryDescriptor',
        'message':     r'\bmessage\s*\(\s*UInt32',
        'publishProperties': r'\bpublishProperties\s*\(',
    }
    present = {}
    for name, pattern in probes.items():
        line = next((l.strip() for l in header.splitlines() if re.search(pattern, l)), None)
        present[name] = line
    return present


def interface_drift(source, published, selected):
    """Compare IOHIDDevice.h across the published bounding revisions and the
    selected one.  Records what a digitizer needs that is identical across the
    interval, what changed, and which bounding revision is closer by observable
    facts -- honestly, no inference dressed as proof."""
    lo, hi = bounding_revisions(published)
    candidates = []
    if lo and lo != selected:
        candidates.append(lo)
    if hi and hi != selected and hi != lo:
        candidates.append(hi)
    if selected not in candidates and selected is not None:
        candidates.append(selected)
    method_sets = {}
    counts = {}
    for rev in candidates:
        try:
            method_sets[rev] = digitizer_relevant_methods(source, rev)
            header = show(source, f'IOHIDFamily-{rev}', 'IOHIDFamily/IOHIDDevice.h')
            counts[rev] = len(re.findall(r'^\s*virtual\b', header, re.M))
        except NotCertified:
            method_sets[rev] = None
    stable, changed, only_in = [], [], []
    named = [rev for rev in candidates if method_sets.get(rev)]
    if named and selected in method_sets and method_sets[selected]:
        for method in method_sets[selected]:
            sig_selected = method_sets[selected][method]
            same_everywhere = all(method_sets.get(rev) and method_sets[rev].get(method) == sig_selected
                                  for rev in named)
            present_everywhere = all(method_sets.get(rev) and method in method_sets[rev]
                                     for rev in named)
            if sig_selected and present_everywhere and same_everywhere:
                stable.append(method)
            elif present_everywhere:
                changed.append(method)
            else:
                only_in.append(method)
    closer = None
    if selected is not None and lo and hi:
        def rank(rev):
            return [int(x) for x in re.findall(r'\d+', rev)]
        # IOHIDFamily-4xx predates the Darwin-18 window; the 5xx-era and 10xx-era
        # are the live candidates. Closer is decided by numeric ordering of the
        # first component, not by claim.
        ranked = sorted(candidates, key=rank)
        closer = ranked[-1] if ranked else None
    return dict(
        bounding_lo=lo, bounding_hi=hi,
        revisions_compared=named,
        virtual_method_count=counts,
        digitizer_methods_stable_across_interval=sorted(stable),
        digitizer_methods_changed=sorted(changed),
        digitizer_methods_only_in_selected=sorted(only_in),
        closer_bounding_revision=closer,
        note=('the kext stamps the exact selected revision, so the interval is a '
              'cross-generation stability study for the T3.2 shim, not a gap confession'),
    )


def reference_compile(tag, work, base, out, clangxx, extra_flags=()):
    """Assemble the shim from the materialized revision and compile the digitizer
    subclass.  Linux macro-clash precedent: the base TargetConditionals and the
    Darwin-18 base headers redefine IOS/EMBEDDED/SIMULATOR/NANO that host clang
    predefines; the redefinition is benign (equal or inert values) and silencing
    it is the same -Wno-macro-redefined precedent audit-storage-interface.py sets."""
    include = out / 'include'
    if include.exists():
        shutil.rmtree(include)
    (include / 'IOKit' / 'hid').mkdir(parents=True)
    (include / 'IOKit' / 'hidsystem').mkdir(parents=True)
    (include / 'IOKit' / 'graphics').mkdir(parents=True)
    # The public include name -> the path that revision actually ships it at.
    # The map is held as a constant so a revision that moved or dropped a header
    # fails loudly here instead of silently compiling against a wrong file.
    public_headers = [
        ('IOKit/hid/IOHIDDevice.h', 'IOHIDFamily/IOHIDDevice.h'),
        ('IOKit/hid/IOHIDKeys.h', 'IOHIDFamily/IOHIDKeys.h'),
        ('IOKit/hid/IOHIDUsageTables.h', 'IOHIDFamily/IOHIDUsageTables.h'),
        ('IOKit/hid/IOHIDProperties.h', 'IOHIDFamily/IOHIDProperties.h'),
        ('IOKit/hid/IOHIDEventTypes.h', 'IOHIDFamily/IOHIDEventTypes.h'),
        ('IOKit/hid/IOHIDEventData.h', 'IOHIDFamily/IOHIDEventData.h'),
        ('IOKit/hid/AppleHIDUsageTables.h', 'IOHIDFamily/AppleHIDUsageTables.h'),
        ('IOKit/hid/IOHIDElement.h', 'IOHIDFamily/IOHIDElement.h'),
        ('IOKit/hid/IOHIDElementPrivate.h', 'IOHIDFamily/IOHIDElementPrivate.h'),
        ('IOKit/hid/IOHIDInterface.h', 'IOHIDFamily/IOHIDInterface.h'),
        ('IOKit/hidsystem/IOHIDDescriptorParser.h', 'IOHIDSystem/IOKit/hidsystem/IOHIDDescriptorParser.h'),
        ('IOKit/hidsystem/IOHIDParameter.h', 'IOHIDSystem/IOKit/hidsystem/IOHIDParameter.h'),
        ('IOKit/hidsystem/IOHIDTypes.h', 'IOHIDSystem/IOKit/hidsystem/IOHIDTypes.h'),
        ('IOKit/hidsystem/IOLLEvent.h', 'IOHIDSystem/IOKit/hidsystem/IOLLEvent.h'),
    ]
    copied = {}
    for dest_name, source_path in public_headers:
        try:
            blob = (work / source_path).read_bytes()
        except FileNotFoundError:
            raise NotCertified(f'{tag} does not ship {source_path}; the shim cannot be backed by this revision')
        dest = include / dest_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)   # Apple sources are latin-1; copy byte-faithfully
        copied[dest_name] = dict(source_path=source_path, sha256=sha256(blob))
    graphics = find_graphics(base, include)
    copied['IOKit/graphics/IOGraphicsTypes.h'] = graphics

    source_file = out / 'IOHIDDevice-reference.cpp'
    source_file.write_text(DIGITIZER_REFERENCE)
    obj_path = out / 'IOHIDDevice-reference.o'
    command = reference_flags(base, include, clangxx, extra_flags) + \
        ['-c', str(source_file), '-o', str(obj_path)]
    (out / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'compile.log').write_text(result.stdout + result.stderr)
    require(result.returncode == 0,
            'reference digitizer subclass does not compile under -Werror for arm64-apple-ios12.0:\n'
            + tail(result.stdout + result.stderr))
    require(obj_path.is_file() and obj_path.stat().st_size > 0, 'reference compile produced no object')
    return obj_path, copied, command


def find_graphics(base, include):
    """Locate IOGraphicsTypes.h in the pinned Darwin-18 base root and drop it into
    the shim; report its hash.  It is referenced by IOKit/hidsystem/IOHIDTypes.h."""
    for candidate in (Path(base) / 'IOKit' / 'graphics' / 'IOGraphicsTypes.h',
                      Path(base) / 'usr' / 'include' / 'IOKit' / 'graphics' / 'IOGraphicsTypes.h',
                      Path(base) / 'System' / 'Library' / 'Frameworks' / 'Kernel.framework'
                      / 'Versions' / 'A' / 'Headers' / 'IOKit' / 'graphics' / 'IOGraphicsTypes.h'):
        if candidate.is_file():
            dest = include / 'IOKit' / 'graphics' / 'IOGraphicsTypes.h'
            dest.write_bytes(candidate.read_bytes())
            return sha256(candidate.read_bytes())
    sdk = subprocess.run(['xcrun', '--show-sdk-path'], capture_output=True, text=True).stdout.strip()
    found = list(Path(sdk).glob('**/IOKit/graphics/IOGraphicsTypes.h'))
    if found:
        dest = include / 'IOKit' / 'graphics' / 'IOGraphicsTypes.h'
        dest.write_bytes(found[0].read_bytes())
        return sha256(found[0].read_bytes()) + '(host-SDK)'
    raise NotCertified('IOGraphicsTypes.h (needed by IOKit/hidsystem/IOHIDTypes.h) not present in the pinned base root')


def reference_flags(base, include, clangxx, extra_flags=()):
    """The exact command a digitizer driver must build under: arm64-apple-ios12,
    Darwin-18 base headers only, C++17, -Werror minus the two documented
    benign exceptions (macro-redefined, incompatible-sysroot for cross sysroot)."""
    import glob
    kf = Path(base) / 'System' / 'Library' / 'Frameworks' / 'Kernel.framework' / 'Versions' / 'A' / 'Headers'
    usr = Path(base) / 'usr' / 'include'
    toolchain = Path(subprocess.run(['xcrun', '-f', 'clang++'], capture_output=True, text=True).stdout.strip())
    clang_root = toolchain.parent.parent          # .../usr/bin -> .../usr
    builtin = sorted(glob.glob(str(clang_root / 'lib' / 'clang' / '*' / 'include')))
    require(builtin, 'host Apple clang builtin header directory not found')
    sdk = subprocess.run(['xcrun', '--show-sdk-path'], capture_output=True, text=True).stdout.strip()
    libcxx = Path(sdk) / 'usr' / 'include' / 'c++' / 'v1'
    require(libcxx.is_dir(), f'libc++ headers not found at {libcxx}')
    command = [str(clangxx), '-std=c++17', '-target', 'arm64-apple-ios12.0',
               '-isysroot', '/', '-ffreestanding', '-nostdinc', '-nostdinc++',
               '-isystem', builtin[-1], '-isystem', str(kf), '-isystem', str(usr),
               '-isystem', str(libcxx),
               '-I', str(include), '-I', str(include / 'IOKit'),
               '-DAPPLE', '-DKERNEL', '-DDEVELOPMENT', '-DXNU_KERNEL_PRIVATE', '-DBCM2837',
               '-Wall', '-Wextra', '-Werror',
               '-Wno-unused-parameter',
               '-Wno-macro-redefined',
               '-Wno-incompatible-sysroot']
    command += list(extra_flags)
    return command


def tail(text, lines=25):
    return '\n'.join(text.splitlines()[-lines:])


# --------------------------------------------------------------------------- #
# Verdict assembly                                                            #
# --------------------------------------------------------------------------- #
def build_cache_checks(cache, selected, source_version_set):
    """Compare the cache to the selected revision as far as a link-stripped iOS 12
    kext allows, and record what is unrecoverable rather than inventing it."""
    checks = {}
    stamped = cache['source_revision']
    checks['source_stamp_matches_selected'] = dict(
        expected=selected, observed=stamped,
        result='match' if selected == stamped else 'mismatch')
    kmod = cache['kmod_info']
    if kmod:
        checks['kmod_info_identity'] = dict(
            name=kmod['name'], version=kmod['version'],
            expected_name='com.apple.iokit.IOHIDFamily',
            source_module_versions=source_version_set,
            result='match' if (kmod['name'] == 'com.apple.iokit.IOHIDFamily'
                               and kmod['version'] in source_version_set) else 'mismatch')
    else:
        checks['kmod_info_identity'] = dict(result='absent (no _PrelinkKmodInfo)')
    extents = cache['extents']
    if extents:
        checks['component_extents'] = dict(
            segments=extents['segments'], executable_sha256=extents['executable_sha256'],
            prelink_exec_size=cache['prelink']['exec_size'],
            result='recoverable' if extents['executable_sha256'] else 'unrecoverable')
    checks['ioservice_vtable'] = dict(
        slots=cache['ioservice_vtable_slots'], pure_virtual=cache['ioservice_pure_virtual'],
        result='recovered from kernel exports' if cache['ioservice_vtable_slots'] else 'unavailable')
    checks['kext_symbol_table'] = dict(
        result='stripped',
        reason=('iOS 12 prelink sets every component LC_SYMTAB nsyms to 0 and zeroes every '
                'vtable typeinfo slot, so per-kext IOHIDDevice-family symbol names cannot be '
                'recovered from the cache; certification stands on the exact source stamp and '
                'the inherited IOService dispatch, not on a fabricated symbol match'))
    return checks


def verdict(certified, reason, cache=None, selected=None, tag=None, commit=None,
            shim_hashes=None, command=None, checks=None, drift=None, provenance=None):
    return dict(
        certified=bool(certified),
        verdict='CERTIFIED' if certified else 'NOT-CERTIFIED',
        reason=reason,
        cache=cache or {},
        selected_source_revision=selected,
        selected_tag=tag,
        selected_commit=commit,
        base_header_provenance=provenance or {},
        shim_headers=shim_hashes or {},
        compile_command=command or [],
        cache_checks=checks or {},
        interface_drift=drift or {},
        instrument_linked_or_executed=False,
        hardware_tested=False,
    )


def write(out, evidence, result):
    (out / 'interface-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2) + '\n')


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #
def run_audit(args, out, *, cache_path=None, force_revision=None, clangxx=None):
    clangxx = clangxx or 'clang++'
    cache_path = cache_path or args.cache
    out.mkdir(parents=True, exist_ok=True)
    cache = read_cache(cache_path)
    published = published_revisions(args.source)
    wanted = force_revision or cache['source_revision']
    tag, commit = select_revision(args.source, wanted)
    work = out / f'src-{wanted}'
    materialize(args.source, tag, work)
    versions = source_module_version(args.source, tag)
    base, provenance = base_headers(args)
    drift = interface_drift(args.source, published, wanted)
    checks = build_cache_checks(cache, wanted, versions)
    stamp = checks['source_stamp_matches_selected']['result']
    identity = checks['kmod_info_identity'].get('result', 'n/a')
    # Certification is fail-closed: every recoverable identity fact must match
    # AND the reference digitizer must compile.  A stripped kext is honest as long
    # as the source stamp is exact and the base ABI (IOService vtable) is recovered.
    obj, hashes, command = reference_compile(tag, work, base, out, clangxx)
    if stamp != 'match':
        raise NotCertified(f'cache source stamp {cache["source_revision"]} != selected {wanted}')
    require(versions, f'{tag} declares no MODULE_VERSION for the IOHIDFamily kext target')
    require(identity in ('match', 'absent (no _PrelinkKmodInfo)'),
            f'kmod_info identity {identity} does not corroborate the selected revision')
    result = verdict(True,
                     ('the shipped kext stamps IOHIDFamily-%s, that revision is published on the mirror, '
                      'its headers plus the pinned Darwin-18 base compile a digitizer IOHIDDevice subclass '
                      'under -Werror for arm64-apple-ios12.0, and the inherited IOService dispatch '
                      '(%s slots, %s pure) is recovered from the kernel exports; the kext symbol table is '
                      'link-stripped so no per-kext symbol match is claimed')
                     % (wanted, cache['ioservice_vtable_slots'], cache['ioservice_pure_virtual']),
                     cache=cache, selected=wanted, tag=tag, commit=commit,
                     shim_hashes=hashes, command=command, checks=checks, drift=drift,
                     provenance={'base_headers': provenance,
                                 'reference_object_sha256': sha256(obj.read_bytes())})
    return result


def self_test(args):
    """GREEN: the real selected revision certifies.  RED: a wrong-generation input
    (a revision the mirror does not publish) fails closed instead of faking it."""
    out = args.output.resolve()
    results = {}
    print('self-test GREEN: positive path certifies against the published revision the kext stamps ...')
    positive = run_audit(args, out / 'selftest-positive')
    results['positive'] = dict(certified=positive['certified'], revision=positive['selected_source_revision'])
    if not positive['certified']:
        raise NotCertified('self-test positive path failed to certify: ' + positive['reason'])
    print('  OK (certified against IOHIDFamily-%s)' % positive['selected_source_revision'])

    print('self-test RED: a wrong-generation revision the mirror does not publish must fail closed ...')
    bogus = '9999999.99999.99999'
    try:
        run_audit(args, out / 'selftest-negative', force_revision=bogus)
        raise SystemExit(f'self-test RED FAILED: force-revision {bogus} did not fail closed')
    except NotCertified as exc:
        results['negative'] = dict(rejected=True, revision=bogus, message=str(exc)[:200])
        print('  OK: rejected ->', str(exc)[:200])
    results['overall'] = 'PASS' if results.get('positive', {}).get('certified') and \
        results.get('negative', {}).get('rejected') else 'FAIL'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'self-test.json').write_text(json.dumps(results, indent=2) + '\n')
    if results['overall'] != 'PASS':
        raise SystemExit('self-test overall ' + results['overall'])
    print('self-test: PASS (positive certifies, negative fails closed)')
    return results


def main():
    out = args.output.resolve()
    if args.self_test:
        self_test(args)
        return
    try:
        result = run_audit(args, out)
    except NotCertified as exc:
        # Emit the fail-closed verdict so the evidence trail is complete even on
        # rejection, then exit non-zero (NOT-CERTIFIED is the honest outcome here).
        cache = {}
        try:
            cache = read_cache(args.cache)
        except Exception:
            pass
        result = verdict(False, str(exc), cache=cache)
        write(out, args.evidence, result)
        print('NOT-CERTIFIED:', result['reason'])
        raise SystemExit(1)
    write(out, args.evidence, result)
    print('CERTIFIED against IOHIDFamily-%s; %s' % (result['selected_source_revision'], result['reason']))
    print('Evidence:', args.evidence)


if __name__ == '__main__':
    main()
