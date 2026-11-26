#!/usr/bin/env python3
"""Stage a minimal RAMDisk root for the iOS 12.4.1 (j96ap) userland handoff to XNU-4570.

Why the inputs look like this (all measured from IPSW 16G102, see
scripts/data/ios12-root-staging-evidence.json):

- The RestoreSystemImage DMG (048-78033-095.dmg) is a UDIF wrapping a GPT with a
  case-sensitive APFS volume, NOT HFS+ as the 2026-11-04 pivot note assumed.
- The system volume is dyld-cache-stripped: most dylibs and framework binaries
  exist only inside System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64
  (1,269,743,616 bytes). Staging that cache would blow the RAM budget; a ~128 MB
  gz RAMDisk alongside the 30 MB kernelcache on a 2 GiB device is the ceiling.
- Apple's own customer Restore RamDisk (048-78047-096.dmg: IM4P 'rdsk' wrapping a
  raw HFSX volume, 91,602,944 bytes logical) is the proven cacheless closure:
  370 files, 62 MiB, real dylib files, no shared cache. Its launchd, dyld, mount
  and mount_hfs are byte-identical (sha256) to the system volume's, so its
  dependency closure transfers exactly.

The staged tree therefore takes executable bits from the system volume where a
real file exists, falling back to Apple's ramdisk copy for cache-only dylibs
(same build, verified per-file by sha256 when both exist). XNU-4570 roots from
/dev/md0 as a mounted filesystem, so the RAMDisk bytes that boot are a filesystem
image; the cpio.gz is the pipeline-portable representation for a privileged
repackager (see tools/check-ios12-closure.py for the red/green proof).

Idempotent: the output tree is rebuilt from scratch on every run; the cpio.gz
rewrites uid/gid/inode/mtime to zero in the newc headers, so two consecutive
runs hash identically (verified). The HFS+ image carries a volume UUID and
fsevents stamps, so it is content-reproducible (diff -r against the tree) but
not byte-reproducible.

Usage:
  scripts/stage-ios12-root.py --system-root /path/to/mounted/system \
      --apple-ramdisk-root /path/to/mounted/apple-restore-ramdisk \
      --out out/y35a/ios12-root [--hfs-image] [--trustcache PATH] [--no-archive]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MACHO_MAGICS = (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca', b'\x12\x00\x00\x00')

# Seeds: the smallest set of executables launchd + a serial single-user boot needs,
# chosen from what Apple's own restore ramdisk ships (its restored(1) stack trimmed
# to the mount/reboot/console tools our first boot actually calls).
SEED_BINARIES = [
    'sbin/launchd',
    'usr/lib/dyld',
    'sbin/mount',
    'sbin/mount_hfs',
    'sbin/fsck',
    'sbin/fsck_hfs',
    'sbin/newfs_hfs',
    'sbin/reboot',
    'sbin/halt',
    'bin/ps',
    'bin/df',
    'bin/cat',
    'bin/ln',
    'bin/mkdir',
    'bin/mv',
    'bin/rm',
]

# /private/etc: the minimal set launchd and libinfo read at boot. fstab is
# deliberately excluded (the RAMDisk root is md0; the system fstab names
# /dev/disk0s1/s2 which do not exist on this boot path).
ETC_FILES = ['passwd', 'group', 'master.passwd', 'hosts', 'ttys', 'protocols', 'services', 'networks']

EMPTY_DIRS = [
    'dev', 'mnt1', 'mnt2', 'mnt3', 'System/Library/Caches', 'System/Library/LaunchAgents',
    'System/Library/LaunchDaemons', 'private/root', 'private/mnt',
    'private/var/tmp', 'private/var/logs', 'private/var/run', 'private/var/db',
    'private/var/mobile', 'private/var/root', 'private/var/spool', 'private/var/vm',
    'private/var/backups', 'private/var/empty', 'private/var/msgs', 'private/etc/defaults',
    'private/etc/ssl/certificates',
]

ROOT_SYMLINKS = {  # the iOS flat-root layout the system volume itself uses
    'etc': 'private/etc',
    'var': 'private/var',
    'tmp': 'private/var/tmp',
}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def is_macho(path):
    try:
        with path.open('rb') as stream:
            head = stream.read(4)
    except OSError:
        return False
    return head in MACHO_MAGICS


def otool_deps(binary):
    """Every dylib path in the load commands except the binary's own id."""
    result = subprocess.run(['otool', '-L', str(binary)], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f'otool failed on {binary}: {result.stderr.strip()}')
    deps = []
    own = None
    for line in result.stdout.splitlines():
        if line.endswith(':') and not line.startswith('\t'):
            own = line[:-1]
            continue
        line = line.strip()
        if line.startswith('/') or line.startswith('@'):
            deps.append(line.split(' (')[0].strip())
    if own and own in deps:
        deps.remove(own)
    return deps


def candidates(volume, install_path, tree_rel):
    """Where a load path may live: exact install path, or the flattened framework
    variant iOS uses (frameworks lose /Versions/A/ on disk but keep it in
    install names — Apple's restore ramdisk proves dyld resolves it)."""
    out = []
    parts = install_path.split('/')
    if 'Versions' in parts:
        index = parts.index('Versions')
        flat = '/'.join(parts[:index] + parts[index + 2:])
        out.append(flat)
    out.append(install_path)
    return out


def volume_realpath(root, path):
    """Resolve symlinks staying inside the mounted volume: absolute link targets
    name paths on the *staged device's* root, not the host's, so they must be
    re-based onto the volume root instead of following them into macOS."""
    root = Path(root)
    current = Path(path)
    for _ in range(40):
        if not current.is_symlink():
            return current if current.is_file() else None
        target = os.readlink(current)
        current = (root / target.lstrip('/')) if target.startswith('/') else (current.parent / target).resolve()
        try:
            current.relative_to(root)
        except ValueError:
            return None
    return None


class Stager:
    def __init__(self, system, apple_ramdisk, out):
        self.system = Path(system).resolve()
        self.apple = Path(apple_ramdisk).resolve() if apple_ramdisk else None
        self.out = Path(out).resolve()
        self.planned = {}   # staging-relative path -> dict(source, sha256, size, via)
        self.gaps = []

    def source_for(self, install_path):
        """(volume, absolute source path) for a load path, preferring a real file
        on the system volume, then Apple's ramdisk (same build for the overlap).
        Filesystem helpers (mount_hfs, fsck_hfs, newfs_hfs) are symlinks into
        /System/Library/Filesystems/<fs>.fs/Contents/Resources on both volumes;
        we stage the resolved Mach-O at the load path."""
        tree_rel = install_path.lstrip('/')
        for volume, root in (('system', self.system), ('apple-ramdisk', self.apple)):
            if root is None:
                continue
            for alt in candidates(root, install_path, tree_rel):
                candidate = root / alt.lstrip('/')
                if candidate.is_symlink():
                    resolved = volume_realpath(root, candidate)
                    if resolved is not None:
                        return volume, resolved, tree_rel
                elif candidate.is_file():
                    return volume, candidate, tree_rel
        return None, None, tree_rel

    def add(self, staging_rel, volume, source, via):
        staging_rel = Path(staging_rel)
        if staging_rel.as_posix() in self.planned:
            self.planned[staging_rel.as_posix()]['via'].append(via)
            return False
        self.planned[staging_rel.as_posix()] = {
            'source': volume, 'origin': str(source), 'via': [via],
            'sha256': sha256_file(source), 'size': source.stat().st_size,
        }
        return True

    def walk_closure(self):
        queue = [(seed, 'seed') for seed in SEED_BINARIES]
        seen = set()
        while queue:
            staging_rel, via = queue.pop(0)
            install_path = '/' + staging_rel
            key = install_path
            if key in seen:
                continue
            seen.add(key)
            volume, source, rel = self.source_for(install_path)
            if source is None:
                self.gaps.append({'load-path': install_path, 'pulled-by': via})
                continue
            added = self.add(rel, volume, source, via)
            if not added:
                continue
            if is_macho(source):
                for dep in otool_deps(source):
                    if dep.startswith('@rpath') or dep.startswith('@executable_path'):
                        self.gaps.append({'load-path': dep, 'pulled-by': install_path,
                                          'note': 'rpath/executable-path install name; dyld needs no file when the loader carries the path'})
                        continue
                    queue.append((dep.lstrip('/'), install_path))

    def copy_tree(self):
        if self.out.exists():
            for dirpath, dirnames, filenames in os.walk(self.out, topdown=False):
                for name in filenames + dirnames:
                    os.chmod(os.path.join(dirpath, name), 0o700)
            subprocess.run(['rm', '-rf', str(self.out)], check=True)
        self.out.mkdir(parents=True)
        for rel in EMPTY_DIRS:
            (self.out / rel).mkdir(parents=True, exist_ok=True)
        for link, target in ROOT_SYMLINKS.items():
            path = self.out / link
            if not path.is_symlink():
                path.symlink_to(target)
        for rel, meta in sorted(self.planned.items()):
            dest = self.out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            source = Path(meta['origin'])
            # clonefile keeps iOS12 content byte-identical without a second copy;
            # APFS falls back to a plain copy when the volumes differ.
            if subprocess.run(['cp', '-c', str(source), str(dest)],
                              capture_output=True).returncode:
                subprocess.run(['cp', str(source), str(dest)], check=True)
            os.chmod(dest, 0o755 if is_macho(dest) else 0o644)

    def copy_config(self):
        copied = {}

        def readable(path):
            try:
                return path.is_file() and os.access(path, os.R_OK)
            except OSError:
                return False

        for name in ETC_FILES:
            for root, tag in ((self.system, 'system'), (self.apple, 'apple-ramdisk')):
                source = root / 'private/etc' / name
                if readable(source):
                    dest = self.out / 'private/etc' / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(source.read_bytes())
                    os.chmod(dest, 0o644)
                    copied['private/etc/' + name] = {'source': tag, 'sha256': sha256_file(dest), 'size': dest.stat().st_size}
                    break
            else:
                copied.setdefault('missing', []).append('private/etc/' + name)
        for root, tag in ((self.system, 'system'), (self.apple, 'apple-ramdisk')):
            source = root / 'System/Library/CoreServices/SystemVersion.plist'
            if readable(source):
                dest = self.out / 'System/Library/CoreServices/SystemVersion.plist'
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(source.read_bytes())
                os.chmod(dest, 0o644)
                copied['System/Library/CoreServices/SystemVersion.plist'] = {'source': tag, 'sha256': sha256_file(dest), 'size': dest.stat().st_size}
                break
        return copied


def build_cpio(out, work):
    """newc cpio with forced uid/gid 0 and no CRC, gzipped into work/; verified
    by re-reading. Built before any artifact lands in out/, so the archive never
    packs itself."""
    cpio = work / 'rootfs.cpio'
    listing = subprocess.run(['find', '.'], cwd=out, capture_output=True, check=True)
    ordered = b'\n'.join(sorted(listing.stdout.split(b'\n'))) + b'\n'
    archive = subprocess.run(['cpio', '-o', '--format=newc'],
                             cwd=out, input=ordered, capture_output=True)
    if archive.returncode:
        raise SystemExit('cpio pack failed: ' + archive.stderr.decode(errors='replace'))
    # Rewrite ownership to root:root deterministically at the field level instead
    # of relying on libarchive version flags; newc fields are 8-hex ASCII.
    data = bytearray(archive.stdout)
    if data[:6] != b'070701':
        raise SystemExit('cpio output is not newc (magic %r)' % bytes(data[:6]))
    at = 0
    count = 0
    saw_trailer = False
    while at + 110 <= len(data):
        if data[at:at + 6] != b'070701':
            raise SystemExit('cpio header lost sync at %d' % at)
        namesize = int(data[at + 94:at + 102], 16)
        filesize = int(data[at + 54:at + 62], 16)
        uid_off, gid_off = at + 6 + 8 + 8, at + 6 + 8 + 8 + 8
        data[uid_off:uid_off + 8] = b'00000000'
        data[gid_off:gid_off + 8] = b'00000000'
        # field offsets: magic(6) ino(8) mode(8) uid(8) gid(8) nlink(8) mtime(8) filesize(8)
        data[at + 6:at + 14] = b'00000000'            # inode numbers are re-rolled per staging run; archives ignore them
        mtime_off = at + 6 + 8 + 8 + 8 + 8 + 8
        data[mtime_off:mtime_off + 8] = b'00000000'   # reproducibility: fix every mtime to the epoch
        name = data[at + 110:at + 110 + namesize - 1]
        # newc pads the name so the *data* starts on a 4-byte boundary relative
        # to the record start (header 110 + name), then pads data itself.
        at += 110 + namesize
        at += -at % 4
        at += filesize
        at += -filesize % 4
        count += 1
        if name == b'TRAILER!!!':
            # cpio pads the tail to a 512-byte block boundary; nothing follows
            # the trailer record except zeros.
            saw_trailer = True
            if data[at:].strip(b'\0') != b'':
                raise SystemExit('nonzero bytes after the cpio trailer')
            break
    if not saw_trailer:
        raise SystemExit('cpio stream ended without a TRAILER record (at %d of %d)' % (at, len(data)))
    cpio.write_bytes(bytes(data))
    gz = out / 'rootfs.cpio.gz'
    with gz.open('wb') as sink:
        subprocess.run(['gzip', '-9n', '-c', str(cpio)], stdout=sink, check=True)
    (out / 'rootfs.gz').unlink(missing_ok=True)
    os.link(gz, out / 'rootfs.gz')  # both names: mirror the 17-era packager input alias
    return gz, count


def verify_cpio(gz):
    listing = subprocess.run('gzip -dc %s | cpio -it --quiet 2>/dev/null | head -20' % gz,
                             shell=True, capture_output=True, text=True, executable='/bin/zsh')
    entries = [line for line in listing.stdout.splitlines() if line.strip()]
    magic = subprocess.run('gzip -dc %s | head -c 6' % gz, shell=True, capture_output=True, text=True, executable='/bin/zsh').stdout
    return magic, entries


def build_hfs_image(out, work, content_bytes):
    """Raw case-sensitive HFS+ volume image with no partition map — byte-for-byte
    the shape of Apple's restore RAMDisk (verified: 'HX' superblock at 0x400,
    attributes 0x10080, single volume, 91,602,944 bytes), which XNU-4570 mounts
    from /dev/md0 as-is. hdiutil makehybrid and partitioned create both add a GPT
    and would reach the device as garbage, so create a PM-less UDRW image,
    newfs_hfs -s it, and copy the tree in with ditto (preserves symlinks/modes).
    NOTE: an unprivileged host build stamps the current uid/gid; Apple's own
    ramdisk has the same property (host-readable 0755 files). A root-owned device
    image must be repacked by the privileged boot-packaging step."""
    image = (work / 'ramdisk-hfs.dmg').resolve()
    if image.exists():
        image.unlink()
    size_bytes = (content_bytes * 4 + (8 << 20)) // 3   # files, B-tree slack, catalog headroom
    size_mb = min(110, size_bytes // (1 << 20) + 1)
    subprocess.run(['hdiutil', 'create', '-quiet', '-layout', 'NONE', '-size', f'{size_mb}m',
                    '-o', str(image)[:-4]], check=True)
    if not image.is_file():
        raise SystemExit('hdiutil create produced no image at ' + str(image))
    attached = subprocess.run(['hdiutil', 'attach', '-readwrite', '-nomount', str(image)],
                              capture_output=True, text=True, check=True).stdout
    dev = None
    for line in attached.splitlines():
        if '/dev/disk' in line:
            dev = line.split('\t')[0].strip()
    if dev is None:
        raise SystemExit('cannot attach the new RAMDisk image: ' + attached)
    rdev = '/dev/' + dev.rsplit('/', 1)[-1].replace('disk', 'rdisk')
    subprocess.run(['/sbin/newfs_hfs', '-s', '-v', 'Y35A_Root', rdev], check=True, capture_output=True)
    subprocess.run(['hdiutil', 'detach', '-quiet', dev], check=True)
    mounted = subprocess.run(['hdiutil', 'attach', '-readwrite', str(image)],
                             capture_output=True, text=True, check=True).stdout
    mount = None
    for line in mounted.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3 and parts[-1].startswith('/Volumes/'):
            mount = parts[-1]
    if mount is None:
        raise SystemExit('the formatted RAMDisk image did not mount: ' + mounted)
    try:
        subprocess.run(['ditto', str(out) + '/', mount + '/'], check=True)
    finally:
        subprocess.run(['hdiutil', 'detach', '-quiet', mount], check=False)
    with image.open('rb') as stream:
        stream.seek(0x400)
        magic = stream.read(2)
    if magic not in (b'H+', b'HX'):
        raise SystemExit('the RAMDisk image does not carry an HFS+ superblock (%r at 0x400)' % magic)
    raw = (work / 'ramdisk-hfs.raw').resolve()
    if raw.exists():
        raw.unlink()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from unixnu.udif import Image
    udif = Image(image)
    with raw.open('wb') as sink:
        for block in udif.blocks():
            sink.write(block)
    with raw.open('rb') as stream:
        stream.seek(0x400)
        if stream.read(2) not in (b'H+', b'HX'):
            raise SystemExit('the expanded raw RAMDisk lost its HFS+ superblock')
    image.unlink()
    return raw, raw.stat().st_size


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--system-root', type=Path, required=True, help='mounted (read-only) RestoreSystemImage volume')
    parser.add_argument('--apple-ramdisk-root', type=Path, default=None, help='mounted customer RestoreRamDisk volume (cache-stripped dylib donor)')
    parser.add_argument('--out', type=Path, required=True, help='staging tree + artifact directory')
    parser.add_argument('--hfs-image', action='store_true', help='also emit a raw HFS+ RAMDisk image in the work dir')
    parser.add_argument('--trustcache', type=Path, default=None,
                        help='IM4P static trustcache to stage as out/.trustcache (a boot sidecar; deliberately not inside the RAMDisk)')
    parser.add_argument('--no-archive', action='store_true', help='stage files only, skip cpio.gz')
    args = parser.parse_args()

    work = args.out.parent / (args.out.name + '.work')
    if work.exists():
        subprocess.run(['rm', '-rf', str(work)], check=True)
    work.mkdir(parents=True)

    stager = Stager(args.system_root, args.apple_ramdisk_root, args.out)
    stager.walk_closure()
    stager.copy_tree()
    config = stager.copy_config()

    # Measure the pristine tree first; the HFS+ volume is copied from it before any
    # artifact (CLOSURE.json, cpio.gz) lands in out/, so the RAMDisk never carries
    # its own archive.
    tree_files = [f for f in args.out.rglob('*') if f.is_file() and not f.is_symlink()]
    content_bytes = sum(f.stat().st_size for f in tree_files)
    report = {'staged_files': len(stager.planned), 'closure_bytes': sum(e['size'] for e in stager.planned.values()),
              'tree_bytes': content_bytes, 'gaps': len(stager.gaps)}
    if args.hfs_image:
        image, logical = build_hfs_image(args.out, work, content_bytes)
        report['hfs'] = {'path': str(image), 'logical_bytes': logical,
                         'page_aligned': logical % 4096 == 0,
                         'sha256': sha256_file(image), 'size': image.stat().st_size,
                         'note': 'host-uid stamped (same as Apple restore ramdisks); repack as root for device boot'}
    if not args.no_archive:
        gz, entries = build_cpio(args.out, work)
        magic, listing = verify_cpio(gz)
        report['cpio'] = {'path': str(gz), 'magic': magic, 'entries': entries,
                          'relisted_sample': listing[:6], 'sha256': sha256_file(gz), 'size': gz.stat().st_size}
    if args.trustcache:
        sidecar = args.out / '.trustcache'   # boot sidecar next to the RAMDisk, never inside it
        sidecar.write_bytes(args.trustcache.read_bytes())
        report['trustcache'] = {'path': str(sidecar), 'sha256': sha256_file(sidecar), 'size': sidecar.stat().st_size}

    closure = {'entries': stager.planned, 'config': config, 'gaps': stager.gaps}
    (args.out / 'CLOSURE.json').write_text(json.dumps(closure, indent=1, sort_keys=True) + '\n')
    print(json.dumps(report, indent=1))
    if stager.gaps:
        print('GAPS (not fatal: recorded in CLOSURE.json):', file=sys.stderr)
        for gap in stager.gaps:
            print(' ', gap, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
