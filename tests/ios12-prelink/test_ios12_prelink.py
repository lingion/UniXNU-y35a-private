#!/usr/bin/env python3
"""iOS 9-12 legacy kernelcache (xnu-4903, iOS 12.4 build 16G102) tests.

Covers the legacy __PRELINK_INFO XML dialect (ID/IDREF interning, integer
envelope, KPI stub entries), the iOS 12 KASLR contract (unslid distribution,
boot-time vm_kernel_slide applied to the offset table including NULL sites),
component enumeration, the derived root plan, and the in-place kernel-slice
emit contract.

Dialect code targets python3.7 syntax (parse-checked with feature_version
3.7): ID/IDREF parsing is hand-written here, not plistlib, and XML is
canonicalized by this module's own serializer.  The suite is run-verified
green on CPython 3.10, 3.12 and 3.13.  The byte-exact roundtrip is
interpreter-independent because integers intern by VALUE and parsed IDREF
strings resolve to the definition's own object -- no CPython small-int
identity is relied on.  The cache is 30 MB so full-parse tests make the
suite take roughly 45 seconds; no pytest markers are used (the file runs
under plain unittest discovery too).

Two fixtures:
  * 16G102 kernelcache.decompressed  (iOS 12.4; sha256 70e80388...;
    file at out/ipsw/16G102/)
  * synthetic cache built from make_synthetic_native over the real bytes
    (placeholder-cleared prelink segments standing in for a native image:
    the built XNU-4903.270.47 P1 kernel is refused by the geometry gate
    until link-edited -- see evidence/y35a-20261102/ios12-prelink-real-p1-
    refusal-20261105.json).

ABI: kextc's OSSerializer interns scalars by OSObject pointer identity.
OSNumber::withNumber deduplicates equal values globally, so an integer
value interns iff it occurs at least twice anywhere in the document (the
16G102 cache proves it: <integer ID="1" size="64">0x0</integer> defined at
the first _PrelinkKmodInfo, referenced from 25 unrelated personality keys).
OSString instances are NOT value-deduplicated: 'KEXT' appears 193 times as
distinct instances and re-defines every time, while shared objects like
'English' intern.  One counter is shared across integers and strings in
write order.  dict/array/data/bool never intern.
"""
import hashlib
import os
import struct
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, 'kits', 'XnuPrelink'))
import legacy_prelink  # noqa: E402

IOS12_SHA256 = '70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1'
IOS12_KCACHE = os.path.join(REPO_ROOT, 'out', 'ipsw', '16G102', 'kernelcache.decompressed')


def require_real_kcache(test):
    """Skip cleanly until the IPSW-extracted iOS 12.4 cache is on disk."""
    if not os.path.exists(IOS12_KCACHE):
        raise unittest.SkipTest('16G102 kernelcache.decompressed missing (out/ipsw/16G102/)')
    with open(IOS12_KCACHE, 'rb') as handle:
        if hashlib.sha256(handle.read()).hexdigest() != IOS12_SHA256:
            raise unittest.SkipTest('16G102 kernelcache.decompressed sha256 mismatch')


class ReaderTests(unittest.TestCase):
    """Dialect parsing: hand-written blobs, no fixture needed."""

    def setUp(self):
        require_real_kcache(self)

    def test_reads_legacy_integer_envelope(self):
        # Real dialect: <integer size="64"> carries lowercase hex; plistlib
        # rejects this envelope outright.
        with open(IOS12_KCACHE, 'rb') as handle:
            data = handle.read()
        _, _, _, _, metadata = legacy_prelink.cache_metadata(data)
        entry = metadata['_PrelinkInfoDictionary'][0]
        self.assertIsInstance(entry['_PrelinkExecutableLoadAddr'], int)
        self.assertGreater(entry['_PrelinkExecutableLoadAddr'], 2 ** 63 - 2 ** 32)

    def test_detect_accepts_bare_dict_and_rejects_junk(self):
        blob = (b'<dict><key>_PrelinkInfoDictionary</key><array><dict>'
                b'<key>CFBundleIdentifier</key><string>com.apple.x</string>'
                b'</dict></array></dict>')
        self.assertEqual(legacy_prelink.detect_format(blob), 'legacy')
        self.assertEqual(legacy_prelink.detect_format(b'GZIP\x00garbage'), 'unknown')

    def test_rejects_envelope_wrapped_variant(self):
        # Byte-level fact from the 21H461 cache on this host: ITS
        # __PRELINK_INFO segment (fileoff 0x292c000) also opens with the
        # bare <dict><key>_PrelinkInfoDictionary legacy body; the full
        # <?xml?><!DOCTYPE><plist> envelope appears there only inside
        # per-kext Info.plist blobs embedded in the payload (e.g. the
        # AppleImage4 one at file offset 10970904).  So a wrapped top-level
        # document is NOT what iOS 12 ships -- if metadata ever arrives
        # wrapped (a future generation, or a hand-written plist exporter),
        # the dialect module must refuse rather than parse it as a
        # byte-compatible legacy document; emit is generation identity,
        # parsing alone would mislabel it as an iOS 12 cache.
        # Partial envelopes a hand-written exporter might produce
        # (declaration only, or <plist> only) stay in the legacy grammar --
        # _tokenize tolerates them - so the refusal keys on the full
        # DOCTYPE-plus-plist signature.
        with open(IOS12_KCACHE, 'rb') as handle:
            metadata = legacy_prelink.cache_metadata(handle.read())[4]
        wrapped = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                   '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                   '<plist version="1.0">'
                   + legacy_prelink.serialize_xml(metadata).decode()
                   + '</plist>').encode()
        self.assertEqual(legacy_prelink.detect_format(wrapped), 'unknown')

    def test_rejects_unknown_idref_and_duplicate_ids(self):
        with self.assertRaises(ValueError):
            legacy_prelink.unserialize_legacy_xml(
                b'<dict><key>x</key><integer IDREF="1" size="64"/></dict>')
        with self.assertRaises(ValueError):
            legacy_prelink.unserialize_legacy_xml(
                b'<dict><key>x</key><integer ID="1" size="64">0x1</integer>'
                b'<key>y</key><integer ID="1" size="64">0x2</integer></dict>')

    def test_tolerates_comments_and_rejects_trailing_garbage(self):
        parsed = legacy_prelink.unserialize_legacy_xml(
            b'<dict><key>x</key><!-- hi --><true/></dict>\0\0')
        self.assertEqual(parsed, {'x': True})
        with self.assertRaises(ValueError):
            legacy_prelink.unserialize_legacy_xml(b'<dict><key>x</key><true/></dict>garbage')

    def test_integer_grammar_covers_getnumber(self):
        # kextc getNumber(): optional minus, 0x hex, leading-0 octal, else
        # decimal; empty body (TAG_EMPTY) is zero.
        blob = (b'<dict>'
                b'<key>a</key><integer size="64">0x10</integer>'
                b'<key>b</key><integer size="64">-0xff</integer>'
                b'<key>c</key><integer size="64">010</integer>'
                b'<key>d</key><integer size="64">-42</integer>'
                b'<key>e</key><integer size="64"/>'
                b'</dict>')
        parsed = legacy_prelink.unserialize_legacy_xml(blob)
        self.assertEqual(parsed, {'a': 16, 'b': -255, 'c': 8, 'd': -42, 'e': 0})


class InterningTests(unittest.TestCase):
    """Serialize must reproduce kextc's pointer-identity interning."""

    def test_interning_rule_on_synthetic_document(self):
        # Built like the real cache: integers that repeat INTERN (OSNumber
        # value dedup); plain strings parsed from separate elements DO NOT
        # intern even when equal (OSString instances are not deduplicated -
        # the 16G102 'KEXT' x193 case); IDREF-referenced strings intern
        # because unserialize reuses the definition object; data/dict/array/
        # bool never intern.  One counter across kinds in write order.
        blob = (b'<dict>'
                b'<key>big</key><integer ID="0" size="64">0x200000000</integer>'
                b'<key>big2</key><integer IDREF="0" size="64"/>'
                b'<key>one</key><integer size="64">0x1</integer>'
                b'<key>one2</key><integer size="64">0x1</integer>'
                b'<key>str</key><string ID="1">Shared</string>'
                b'<key>str2</key><string IDREF="1"/>'
                b'<key>dup</key><string>Kext</string>'
                b'<key>dup2</key><string>Kext</string>'
                b'<key>data</key><data>AAAAAAAAAAAAAAAA</data>'
                b'<key>data2</key><data>AAAAAAAAAAAAAAAA</data>'
                b'<key>dict</key><dict><key>k</key><integer size="64">0x1</integer></dict>'
                b'<key>dict2</key><dict><key>k</key><integer size="64">0x1</integer></dict>'
                b'<key>arr</key><array><integer size="64">0x1</integer></array>'
                b'<key>arr2</key><array><integer size="64">0x1</integer></array>'
                b'</dict>')
        parsed = legacy_prelink.unserialize_legacy_xml(blob)
        rebuilt = legacy_prelink.serialize_xml(parsed)
        # kextc writes the size="64" envelope only where the OSNumber is
        # first serialized; every reference is the bare <integer IDREF="n"/>
        # (all 1827 references in the 16G102 bytes carry no size=).
        expected = (b'<dict>'
                    b'<key>big</key><integer ID="0" size="64">0x200000000</integer>'
                    b'<key>big2</key><integer IDREF="0"/>'
                    b'<key>one</key><integer ID="1" size="64">0x1</integer>'
                    b'<key>one2</key><integer IDREF="1"/>'
                    b'<key>str</key><string ID="2">Shared</string>'
                    b'<key>str2</key><string IDREF="2"/>'
                    b'<key>dup</key><string>Kext</string>'
                    b'<key>dup2</key><string>Kext</string>'
                    b'<key>data</key><data>AAAAAAAAAAAAAAAA</data>'
                    b'<key>data2</key><data>AAAAAAAAAAAAAAAA</data>'
                    b'<key>dict</key><dict><key>k</key><integer IDREF="1"/></dict>'
                    b'<key>dict2</key><dict><key>k</key><integer IDREF="1"/></dict>'
                    b'<key>arr</key><array><integer IDREF="1"/></array>'
                    b'<key>arr2</key><array><integer IDREF="1"/></array>'
                    b'</dict>')
        self.assertEqual(rebuilt, expected)

    def test_plain_python_scalars_intern_by_value(self):
        # Hand-built dicts have no parse identity: integers and strings
        # reaching the same value at least twice intern by (kind, value)
        # GLOBALLY (OSNumber dedup ignores nesting), never data/dict/array/
        # bool.  7 occurs four times (a, b, i.z, j.z) -> one definition plus
        # three references; 'x' twice -> one reference; 1 and 2 each twice
        # across the two equal lists -> two references.  Six IDREFs total.
        value = {'a': 7, 'b': 7, 'c': 'x', 'd': 'x', 'e': b'\x00' * 16,
                 'f': b'\x00' * 16, 'g': [1, 2], 'h': [1, 2], 'i': {'z': 7},
                 'j': {'z': 7}, 'k': True, 'l': True}
        rebuilt = legacy_prelink.serialize_xml(value)
        self.assertIn(b'<integer ID="0" size="64">0x7</integer>', rebuilt)
        self.assertIn(b'<integer IDREF="0"/>', rebuilt)
        self.assertIn(b'<string ID="1">x</string>', rebuilt)
        self.assertIn(b'<string IDREF="1"/>', rebuilt)
        # 16 zero bytes base64 to 22 A's plus '=='; count 2 but <data>
        # never interns, and both copies re-define in full.
        self.assertIn(b'<data>AAAAAAAAAAAAAAAAAAAAAA==</data>', rebuilt)
        self.assertIn(b'<true/>', rebuilt)
        self.assertEqual(rebuilt.count(b'IDREF'), 6)
        self.assertEqual(rebuilt.count(b'<integer IDREF="0"/>'), 3)
        self.assertEqual(legacy_prelink.unserialize_legacy_xml(rebuilt)['a'], 7)

    def test_negative_integers_render_signed_hex(self):
        # kextc renders negatives as "-0x..." - never decimal - and writes
        # references bare (no size= on the IDREF element, matching all 1827
        # integer references in the 16G102 bytes).
        blob = b'<dict><key>n</key><integer ID="0" size="64">-0x3e7</integer>' \
               b'<key>m</key><integer IDREF="0"/></dict>'
        value = legacy_prelink.unserialize_legacy_xml(blob)
        self.assertEqual(legacy_prelink.serialize_xml(value), blob)

    def test_shared_scalar_identity_survives_deeper_containers(self):
        # An IDREF-referenced scalar appearing in a 3-level-nested dict tree
        # must stay one shared object through the whole write, even when the
        # nesting contains other scalars.
        blob = (b'<dict>'
                b'<key>anchor</key><integer ID="0" size="64">0x55aa</integer>'
                b'<key>tree</key><dict><key>mid</key><array>'
                b'<dict><key>leaf</key><integer IDREF="0"/></dict>'
                b'<integer size="64">0x9</integer>'
                b'</array></dict>'
                b'<key>again</key><dict><key>deep</key><dict>'
                b'<key>more</key><integer IDREF="0"/></dict></dict>'
                b'</dict>')
        value = legacy_prelink.unserialize_legacy_xml(blob)
        rebuilt = legacy_prelink.serialize_xml(value)
        self.assertEqual(rebuilt, blob)


class ParserDialectTests(unittest.TestCase):
    """Hand-written blobs that must parse or must be rejected."""

    def test_parses_all_supported_tags(self):
        blob = (b'<dict>'
                b'<key>s</key><string>a&amp;b</string>'
                b'<key>i</key><integer size="64">0x10</integer>'
                b'<key>d</key><data>QUJD</data>'
                b'<key>t</key><true/>'
                b'<key>f</key><false/>'
                b'<key>a</key><array><integer size="64">0x1</integer></array>'
                b'<key>e</key><dict/>'
                b'</dict>')
        parsed = legacy_prelink.unserialize_legacy_xml(blob)
        self.assertEqual(parsed['s'], 'a&b')
        self.assertEqual(parsed['i'], 16)
        self.assertEqual(parsed['d'], b'ABC')
        self.assertIs(parsed['t'], True)
        self.assertIs(parsed['f'], False)
        self.assertEqual(parsed['a'], [1])
        self.assertEqual(parsed['e'], {})
        self.assertIsInstance(parsed['i'], legacy_prelink.LegacyInteger)
        self.assertIsInstance(parsed['s'], legacy_prelink.LegacyString)

    def test_rejects_malformed_dialect(self):
        cases = (
            b'<array/>',                                      # root not dict
            b'<dict><key>a</key><key>b</key></dict>',         # key without value
            b'<dict><integer size="64">0x1</integer></dict>', # value without key
            b'<dict><key>a</key><key>a</key><true/><true/></dict>',  # dup key
            b'<dict><key>a</key><dict><key>b</key><true/></array>',  # mismatched close
            b'<dict><key>a</key><dict ID="1"/><true/></dict>',  # dict with ID
            b'<dict><key>a</key><array IDREF="0"/><true/></dict>',  # array IDREF
            b'<dict><key>a</key><real>1.0</real></dict>',     # unsupported tag
            b'<dict><key>a</key><string ID="x">y</string>'
            b'<key>b</key><integer ID="x" size="64">0x1</integer></dict>',  # dup ID
            b'<dict><key>a</key><true ID="0"/></dict>',       # true with ID
            b'<dict><key>a</key><true/></dict>trailing',      # junk after root
            b'<dict><key>a</key>',                            # unclosed body
            b'<garbage/>',                                    # not a dialect document
            b'<dict><key>a</key><data>!!!!</data></dict>',    # invalid base64
        )
        for blob in cases:
            with self.assertRaises(ValueError, msg=blob[:40]):
                legacy_prelink.unserialize_legacy_xml(blob)

    def test_rejects_65_bit_negative_integer(self):
        # getNumber() clamps magnitude at 64 bits; the dialect has no legal
        # value below -2^63.
        with self.assertRaises(ValueError):
            legacy_prelink.unserialize_legacy_xml(
                b'<dict><key>n</key><integer size="64">-0x8000000000000001</integer></dict>')

    def test_detects_wrapped_dialects(self):
        body = b'<dict><key>_PrelinkInfoDictionary</key><array/></dict>'
        self.assertEqual(legacy_prelink.detect_format(
            b'<?xml version="1.0"?>\n' + body), 'legacy')
        self.assertEqual(legacy_prelink.detect_format(
            b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "x.dtd">'
            + body), 'legacy')
        self.assertEqual(legacy_prelink.detect_format(
            b'<plist version="1.0">' + body + b'</plist>'), 'legacy')
        # plist-wrapped but NOT a prelink document: unknown.
        self.assertEqual(legacy_prelink.detect_format(
            b'<plist version="1.0"><dict/></plist>'), 'unknown')
        # self-closed root with prelink key present: still legacy body.
        self.assertEqual(legacy_prelink.detect_format(
            b'<dict><key>_PrelinkInfoDictionary</key><array/></dict>\0'), 'legacy')

    def test_plist_wrapper_parses_to_same_value(self):
        blob = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                b'<plist version="1.0"><dict><key>_PrelinkInfoDictionary</key>'
                b'<array/></dict></plist>\0\0')
        self.assertEqual(legacy_prelink.unserialize_legacy_xml(blob),
                         {'_PrelinkInfoDictionary': []})

    def test_macho_parse_rejects_bounded_and_bad_cmdsize(self):
        # (a) a segment command claiming filesize past EOF must refuse;
        # (b) a segment mapped with nonzero vmsize but zero filesize must
        #     refuse (placeholders are legal only with vmsize zero);
        # (c) a BadLoadCommands-style zero cmdsize must terminate instead of
        #     spinning, and must name the offending offset.
        # mach_header_64 is 32 bytes (magic, cputype, cpusubtype, filetype,
        # ncmds, sizeofcmds, flags, reserved); two commands of 72 + 8 bytes
        # give sizeofcmds 80.  Padding must cover case (c)'s legitimate
        # 0x1000+0x1000 extent so only the zero cmdsize is illegal there.
        header = struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, 2, 2, 80, 0, 0)
        bad = struct.pack('<II', 0x80000020, 0)  # BadLoadCommands cmd, cmdsize 0
        seg = struct.pack('<II16sQQQQIIII', 0x19, 72, b'__TEXT',
                          0x0, 0x1000, 0x0, 0xFFFFFFFF, 5, 5, 0, 0)
        with self.assertRaisesRegex(ValueError, 'past the image'):
            legacy_prelink.macho(header + seg + bad + b'\0' * 0x2000)
        seg2 = struct.pack('<II16sQQQQIIII', 0x19, 72, b'__TEXT',
                           0x0, 0x1000, 0x0, 0x0, 5, 5, 0, 0)
        with self.assertRaisesRegex(ValueError, 'zero-sized'):
            legacy_prelink.macho(header + seg2 + b'\0' * 0x2000)
        seg3 = struct.pack('<II16sQQQQIIII', 0x19, 72, b'__TEXT',
                           0x0, 0x1000, 0x0, 0x1000, 5, 5, 0, 0)
        with self.assertRaises(ValueError) as caught:
            legacy_prelink.macho(header + seg3 + bad + b'\0' * 0x2000)
        self.assertRegex(str(caught.exception),
                         'BadLoadCommands|Invalid load command extent')


class EmittedBytesTests(unittest.TestCase):
    """The emitted candidate's payload and metadata must be byte-correct."""

    def setUp(self):
        require_real_kcache(self)

    def test_kernel_payload_and_metadata_are_emitted_byte_exact(self):
        with open(IOS12_KCACHE, 'rb') as handle:
            original = handle.read()
        native = legacy_prelink.make_synthetic_native(original)
        roots = legacy_prelink.ios12_kernel_roots(original)['roots']
        emitted, _ = legacy_prelink.emit_legacy(native, original, roots)
        # 1) kernel payload: every byte of the native kernel slice at or
        #    past __TEXT's first section (code + data) must appear at the
        #    identical file offset; the header region below it stays the
        #    cache's own (a header-preserving in-place swap), and
        #    __LINKEDIT keeps the cache table the preserved header points to.
        parent = legacy_prelink.macho(original)['segments']
        text = next(s for s in parent if s['name'] == '__TEXT')
        header_end = min(sec['fileoff'] for sec in text['sections'] if sec['size'])
        cachebase = next(s['fileoff'] for s in parent if s['name'] == '__PRELINK_TEXT')
        self.assertEqual(emitted[header_end:cachebase], native[header_end:cachebase])
        # 2) metadata: the emitted plist must re-parse to the retained
        #    enumeration AND the raw bytes inside __PRELINK_INFO must equal
        #    serialize_xml of the same document padded to the segment -
        #    pinning the interning writer against the real bytes.
        _, _, info, at, _ = legacy_prelink.cache_metadata(original)
        _, _, _, _, emitted_metadata = legacy_prelink.cache_metadata(emitted)
        rebuilt = legacy_prelink.serialize_xml(emitted_metadata)
        window = emitted[at:at + info['filesize']]
        self.assertEqual(window[:len(rebuilt)], rebuilt)
        self.assertEqual(window[len(rebuilt):], b'\0' * (info['filesize'] - len(rebuilt)))
        self.assertEqual(len(emitted_metadata['_PrelinkInfoDictionary']), len(roots) + 15)
        # 3) KASLR table: the emitted blob re-parses to exactly the same
        #    count/offsets (identity, not just presence).
        packed = emitted_metadata['_PrelinkLinkKASLROffsets']
        self.assertEqual(packed, original_metadata_packed(original))


def original_metadata_packed(data):
    return legacy_prelink.cache_metadata(data)[4]['_PrelinkLinkKASLROffsets']


class RealCacheTests(unittest.TestCase):
    """Roundtrip, component enumeration, plan, and emit on the 16G102 cache."""

    def setUp(self):
        require_real_kcache(self)
        with open(IOS12_KCACHE, 'rb') as handle:
            self.data = handle.read()

    def test_detects_legacy_metadata(self):
        image, parent, info, at, metadata = legacy_prelink.cache_metadata(self.data)
        self.assertEqual(legacy_prelink.detect_format(self.data[at:at + info['filesize']]),
                         'legacy')
        self.assertEqual(len(metadata['_PrelinkInfoDictionary']), 193)
        # LC_SEGMENT __PRELINK_INFO in the 16G102 cache: vmaddr
        # 0xfffffff0077e4000 fileoff 0x1ad0000 vmsize/filesize 0x204000.
        self.assertEqual(info['filesize'], 2113536)

    def test_byte_exact_roundtrip(self):
        # The interning rule is value-keyed for integers and object-keyed
        # for strings; parsed IDREFs resolve to the definition's own object,
        # so the roundtrip is byte-exact on every supported interpreter
        # (this session reproduced 35/35 green on CPython 3.10, 3.12 and
        # 3.13 alike).  An earlier docstring blamed CPython small-int
        # identity for a 3.12 requirement -- that claim was wrong: the 18
        # failures this suite shipped with reproduced identically on both.
        _, _, _, at, metadata = legacy_prelink.cache_metadata(self.data)
        body = self.data[at:].split(b'\0', 1)[0]
        rebuilt = legacy_prelink.serialize_xml(metadata)
        self.assertEqual(rebuilt, body)
        reparsed = legacy_prelink.unserialize_legacy_xml(rebuilt)
        self.assertEqual(legacy_prelink.serialize_xml(reparsed), body)

    def test_interning_proven_on_real_cache(self):
        # The three load-bearing facts of the dialect, asserted against the
        # 16G102 bytes themselves so the interning rule cannot silently
        # invert into 'never intern' or 'always intern'.
        image, parent, info, at, metadata = legacy_prelink.cache_metadata(self.data)
        body = self.data[at:at + info['filesize']]
        # 1. integers DO intern by value: shared ID-numbered <integer>
        #    envelopes; kextc writes the size= only on the definition, so
        #    every reference is the bare <integer IDREF="n"/> form.
        self.assertIn(b'<integer ID="', body)
        self.assertNotRegex(body, rb'<integer IDREF="\d+" size=')
        # 2. strings intern by OBJECT identity, never by value: shared
        #    instances like 'English' define an ID and are re-used through
        #    <string IDREF>, while 'KEXT' appears 193 times as distinct
        #    instances and never receives an ID definition.
        self.assertEqual(body.count(b'<string>KEXT</string>'), 193)
        self.assertNotRegex(body, rb'<string ID="\d+">KEXT</string>')
        self.assertIn(b'<string IDREF="', body)
        self.assertRegex(body, rb'<string ID="\d+">English</string>')
        # 3. dict/array/data NEVER intern: none carries ID=.
        self.assertNotIn(b'<dict ID=', body)
        self.assertNotIn(b'<array ID=', body)
        self.assertNotIn(b'<data ID=', body)

    def test_component_enumeration(self):
        plan = legacy_prelink.ios12_kernel_roots(self.data)
        self.assertEqual(plan['plist_entries'], 193)
        self.assertEqual(plan['exec_addr_entries'], 184)
        self.assertEqual(plan['kpi_stubs'], 7)
        self.assertEqual(plan['codeless'], 8)
        self.assertEqual(plan['pruned'], 1)
        self.assertEqual(plan['loadable'], 177)
        self.assertEqual(len(plan['roots']), 170)
        self.assertEqual(plan['kaslr_sites'], 251829)

    def test_plan_identity_on_synthetic_native_zero_slide(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        _, report = legacy_prelink.emit_legacy(native, self.data,
                                               legacy_prelink.ios12_kernel_roots(self.data)['roots'])
        self.assertEqual(report['pipeline'], 'legacy-ios12-in-place')
        self.assertEqual(report['slide'], 0)
        self.assertEqual(report['component_count'], 170)
        self.assertEqual(report['plist_entries'], 185)
        self.assertEqual(report['kpi_stubs'], 7)
        self.assertEqual(report['codeless'], 8)
        self.assertEqual(report['pruned'], 1)
        self.assertEqual(report['pointer_sites'], {'component': 75712, 'kernel': 171556,
                                                  'dropped': 4561, 'null': 0})
        # 75712 + 171556 + 4561 + 0 = 251829 = every KASLR site in this
        # cache; the T7001 16G102 build ships no NULL-target sites, so the
        # null bucket is counted, not assumed.
        self.assertEqual(sum(report['pointer_sites'].values()), 251829)
        self.assertFalse(report['runtime_qualified'])
        self.assertFalse(report['loadable'])

    def test_roots_exclude_pointer_opaque_drm_modules(self):
        # The excluded set is DERIVED (interior pointers like _memcpy+2),
        # not hardcoded.  The 16G102 bytes carry unresolvable kernel-
        # interior pointer sites in exactly four modules (ASIOKit,
        # FairPlayIOKit, LSKDIOKit, LSKDIOKitMSE); exclusion then spreads
        # transitively to the three that reference them (IOAudioCodecs via
        # a pointer edge into FairPlayIOKit, IOTextEncryptionFamily and
        # AppleVXD393 via OSBundleLibraries).  DispAlg/DispAlgNative do not
        # exist in this cache at all - those names belong to other
        # generations and must not appear.
        plan = legacy_prelink.ios12_kernel_roots(self.data)
        excluded = set(plan['excluded_modules'])
        self.assertEqual(excluded, {
            'com.apple.driver.ASIOKit', 'com.apple.driver.FairPlayIOKit',
            'com.apple.driver.LSKDIOKit', 'com.apple.driver.LSKDIOKitMSE',
            'com.apple.driver.IOAudioCodecs', 'com.apple.IOTextEncryptionFamily',
            'com.apple.driver.AppleVXD393'})
        self.assertNotIn('com.apple.driver.DispAlg', excluded)
        self.assertNotIn('com.apple.driver.DispAlgNative', excluded)
        for family in ('com.apple.iokit.IO80211Family', 'com.apple.iokit.IOHIDFamily',
                       'com.apple.filesystems.apfs', 'com.apple.filesystems.hfs.kext',
                       'com.apple.security.sandbox', 'com.apple.security.AppleImage4',
                       'com.apple.kec.corecrypto', 'com.apple.iokit.IOSurface'):
            self.assertIn(family, plan['roots'])
        self.assertEqual(len(plan['roots']), 170)

    def test_roots_exclude_only_pointer_opaque_drm_modules(self):
        # DRM families FairPlayIOKit/LSKD*/ASIOKit carry _memcpy+2-style
        # interior pointers into dispatch tables; exclusion must spread to
        # anything referencing them.
        plan = legacy_prelink.ios12_kernel_roots(self.data)
        excluded = set(plan['excluded_modules'])
        self.assertTrue(excluded)
        drm = {name for name in excluded if 'FairPlay' in name or 'LSKD' in name or 'ASIO' in name}
        self.assertTrue(drm, 'expected DRM-family modules among the exclusions')
        for identifier in excluded:
            self.assertNotIn(identifier, plan['roots'])

    def test_emit_refuses_unknown_roots_and_17gen_native(self):
        # A root outside the component enumeration must be named; a native
        # kernel carrying the 10063 sparse export must be refused outright
        # (it belongs to emit_prelink.py).
        native = legacy_prelink.make_synthetic_native(self.data)
        roots = legacy_prelink.ios12_kernel_roots(self.data)['roots']
        with self.assertRaisesRegex(ValueError, 'outside component enumeration'):
            legacy_prelink.emit_legacy(native, self.data,
                                       ['com.apple.nonexistent.kext', 'com.apple.driver.AppleARMPlatform'])
        # The sparse-index name is a byte-stream marker on the native image;
        # appending it inside the file padding reproduces the condition the
        # real 10063 kernel carries without needing LC_SYMTAB surgery.
        marker = bytes(legacy_prelink._SPARSE_MARKER)
        with self.assertRaisesRegex(ValueError, 'sparse index ABI'):
            legacy_prelink.emit_legacy(native + b'\0' + marker + b'\0', self.data, roots)

    def test_emit_refuses_baked_slide(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        with self.assertRaisesRegex(ValueError, 'unslid'):
            legacy_prelink.emit_legacy(native, self.data,
                                       legacy_prelink.ios12_kernel_roots(self.data)['roots'],
                                       slide=0x4000000)

    def test_emit_refuses_missing_kernel_symbols(self):
        # A native kernel whose symbol table lacks even one name the retained
        # kexts bind to must be refused with the names listed.  Zero the
        # LC_SYMTAB nlist span itself (a zeroed n_type is neither external
        # nor sectioned, so every entry reads as unexported).
        native = legacy_prelink.make_synthetic_native(self.data)
        image = legacy_prelink.macho(native)
        symtab = [(offset, length) for command, offset, length in image['commands']
                  if command == 2]
        self.assertEqual(len(symtab), 1)
        symoff, count, _, _ = struct.unpack_from('<4I', native, symtab[0][0] + 8)
        broken = bytearray(native)
        broken[symoff:symoff + count * 16] = b'\0' * (count * 16)
        with self.assertRaises(ValueError) as caught:
            legacy_prelink.emit_legacy(bytes(broken), self.data,
                                       legacy_prelink.ios12_kernel_roots(self.data)['roots'])
        self.assertIn('lacks exports', str(caught.exception))

    def test_emit_preserves_parent_header_and_geometry(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        roots = legacy_prelink.ios12_kernel_roots(self.data)['roots']
        emitted, report = legacy_prelink.emit_legacy(native, self.data, roots)
        self.assertEqual(len(emitted), len(self.data))
        # The parent header survives untouched: the command count and every
        # segment's vmaddr/vmsize/fileoff/filesize (including the five
        # __PRELINK* segments) are identical to the original.
        original_header = legacy_prelink.macho(self.data)
        emitted_image = legacy_prelink.macho(emitted)
        self.assertEqual(len(original_header['commands']), len(emitted_image['commands']))
        for before, after in zip(original_header['segments'], emitted_image['segments']):
            self.assertEqual((before['name'], before['va'], before['size'],
                              before['fileoff'], before['filesize']),
                             (after['name'], after['va'], after['size'],
                              after['fileoff'], after['filesize']))
        # Prelink payload and header region of __TEXT stay byte-identical.
        text = next(s for s in emitted_image['segments'] if s['name'] == '__TEXT')
        cachebase = next(s['fileoff'] for s in emitted_image['segments']
                         if s['name'] == '__PRELINK_TEXT')
        header_end = min(sec['fileoff'] for sec in text['sections'] if sec['size'])
        self.assertEqual(emitted[:header_end], self.data[:header_end])
        self.assertEqual(emitted[cachebase:cachebase + 0x1000],
                         self.data[cachebase:cachebase + 0x1000])

    def test_emit_refuses_nonmatching_native_geometry(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        image = legacy_prelink.macho(native)
        text = next(s for s in image['segments'] if s['name'] == '__TEXT')
        broken = bytearray(native)
        # segment_command_64: cmd(4) cmdsize(4) name(16) then vmaddr at +24,
        # vmsize at +32.  Drift vmsize (vmaddr drift would push the extent
        # past the file and trip the parser before emit could name the
        # segment); emit matches vmaddr AND vmsize against the cache.
        struct.pack_into('<Q', broken, text['command_offset'] + 32,
                         text['size'] + 0x4000)
        with self.assertRaisesRegex(ValueError, 'geometry'):
            legacy_prelink.emit_legacy(bytes(broken), self.data,
                                       legacy_prelink.ios12_kernel_roots(self.data)['roots'])

    def test_emit_refuses_nonmatching_native_fileoff(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        image = legacy_prelink.macho(native)
        textexec = next(s for s in image['segments'] if s['name'] == '__TEXT_EXEC')
        broken = bytearray(native)
        struct.pack_into('<Q', broken, textexec['command_offset'] + 40,
                         textexec['fileoff'] + 0x1000)  # fileoff drift
        with self.assertRaisesRegex(ValueError, 'file extent'):
            legacy_prelink.emit_legacy(bytes(broken), self.data,
                                       legacy_prelink.ios12_kernel_roots(self.data)['roots'])

    def test_emit_refuns_nonmatching_section_extent(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        image = legacy_prelink.macho(native)
        text = next(s for s in image['segments'] if s['name'] == '__TEXT')
        section = next(sec for sec in text['sections'] if sec['size'])
        broken = bytearray(native)
        struct.pack_into('<I', broken, section['command_offset'] + 48,
                         struct.unpack_from('<I', native, section['command_offset'] + 48)[0] + 1)
        with self.assertRaisesRegex(ValueError, 'file extent'):
            legacy_prelink.emit_legacy(bytes(broken), self.data,
                                       legacy_prelink.ios12_kernel_roots(self.data)['roots'])

    def test_make_synthetic_native_clears_placeholders(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        image = legacy_prelink.macho(native)
        cleared = [s for s in image['segments'] if s['name'] in legacy_prelink.PRELINK_SEGMENT_NAMES]
        self.assertEqual(len(cleared), 5)
        self.assertTrue(all(s['filesize'] == 0 for s in cleared))
        self.assertTrue(all(s['va'] for s in cleared))  # vmaddr kept
        # section addr kept, size cleared (parser key for section address
        # is 'va', mirroring the segment key)
        for segment in cleared:
            for section in segment['sections']:
                self.assertEqual(section['size'], 0)
                self.assertTrue(section['va'])

    def test_kernel_target_symbols_nonempty_on_real_cache(self):
        names = legacy_prelink.kernel_target_symbols(self.data)
        # every exported kernel name the KASLR table can point at; assert the
        # count and a few load-bearing names rather than the exact 2324 set.
        self.assertGreater(len(names), 1000)
        # _panic/_memcpy are bound by retained kexts in the 16G102 table;
        # _rootit is a boot path name that never appears as a pointer target
        # export in this cache's nlist at all.
        self.assertIn('_panic', names)
        self.assertIn('_memcpy', names)

    def test_plan_refuses_unfiltered_drm_roots(self):
        # Passing the FULL component list as roots must be refused: the
        # pointer-opaque DRM modules then stay retained, and their own
        # interior kernel sites (e.g. _memcpy+2) have no name to bind -
        # 'Unresolvable pointer target ... from ...LSKDIOKitMSE'.  Dropping
        # just the four derived opaque sources but keeping everything that
        # references them trips the second gate instead: a retained module
        # (IOAudioCodecs) holding a pointer into an excluded one
        # (FairPlayIOKit) - 'Undeclared pointer dependency'.
        image, parent, info, at, metadata, entries, kpi, modules, codeless, pruned = \
            legacy_prelink._component_enumeration(self.data)
        native = legacy_prelink.make_synthetic_native(self.data)
        with self.assertRaisesRegex(ValueError, 'Unresolvable pointer target'):
            legacy_prelink.emit_legacy(native, self.data, sorted(modules))
        opaque = {'com.apple.driver.ASIOKit', 'com.apple.driver.FairPlayIOKit',
                  'com.apple.driver.LSKDIOKit', 'com.apple.driver.LSKDIOKitMSE'}
        with self.assertRaisesRegex(ValueError, 'Undeclared pointer dependency'):
            legacy_prelink.emit_legacy(native, self.data, sorted(set(modules) - opaque))

    def test_emit_is_deterministic(self):
        native = legacy_prelink.make_synthetic_native(self.data)
        roots = legacy_prelink.ios12_kernel_roots(self.data)['roots']
        first, _ = legacy_prelink.emit_legacy(native, self.data, roots)
        second, _ = legacy_prelink.emit_legacy(native, self.data, roots)
        self.assertEqual(hashlib.sha256(first).hexdigest(),
                         hashlib.sha256(second).hexdigest())


if __name__ == '__main__':
    unittest.main()
