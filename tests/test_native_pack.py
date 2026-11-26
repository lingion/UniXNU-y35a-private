#!/usr/bin/env python3
"""T-PKG boot3 gate-model tests: the RAMBoot container must pass the resident
lk2nd cmd_boot path end-to-end on paper, re-derived from source.

Every constant and formula in GateModel below is quoted from the resident
lk2nd tree (container unixnu-y35a-native-20261103, /work/lk2nd-y35a-codex,
version 23.1-y35a-xnu-layout-v1), deliberately NOT imported from the packer,
so these tests can contradict scripts/y35a/package_native.py:

  app/aboot/aboot.c:3216   sz < sizeof(hdr*)==8 -> refuse
  app/aboot/aboot.c:3226   eMMC boot adopts hdr->page_size
  app/aboot/aboot.c:3238   dt_size = hdr->dt_size (OSVERSION_IN_BOOTIMAGE off)
  app/aboot/aboot.c:3243   image_actual = page+ROUND(k)+ROUND(rd)+ROUND(sec)+ROUND(dt)
  app/aboot/aboot.c:3248   refuse iff image_actual > sz   (V14.7: gate proven alive)
  app/aboot/aboot.c:3317   refuse iff (download_max - page) < image_actual
  app/aboot/aboot.c:3374   kernel-domain gzip sniff; raw Image stays in place
  app/aboot/aboot.c:3393   text_offset > 2MiB is zeroed
  app/aboot/aboot.c:400    stock policy (ABOOT_IGNORE_BOOT_HEADER_ADDRS=1,
              build config.h:16; platform/msm8916/include/platform/iomap.h:49-52):
              kernel=DDR+0x80000, ramdisk=DDR+0x2000000, tags=DDR+0x1E00000
  app/aboot/aboot.c:412    fork pin v1 fires iff compatible vivo,pd1502a AND
              IS_ARM64 AND text_offset==0x80000 AND kernel_size<=0x3180000
              AND ramdisk_size==1 AND cmdline memcmp == "y35a-native-xnu-experimental"
              -> ramdisk_addr=0x85700000, tags_addr=0x85800000
  app/aboot/aboot.c:434    image_size!=0 -> kernel_addr = align_down_2MiB + text_offset
  app/aboot/aboot.c:3421   kernel+ramdisk overlap/bound gates; aboot owns only
              [0x8F600000,0x8F700000) (config.h MEMBASE/MEMSIZE); DDR=[0x80000000,0x100000000)
  app/aboot/aboot.c:3431   copy_dtb iff dt_size!=0: QCDT table at
              page+ROUND(k)+ROUND(rd)+(ROUND(sec) iff second_size!=0);
              version/magic/entry validation; matched FDT memmoved to tags_addr
  app/aboot/aboot.c:3445   tags bound gate check_ddr_addr_range_bound(tags, kernel_actual)
  app/aboot/aboot.c:3449   copy_dtb fail -> dev_tree_appended(kernel-domain scan)
              -> both miss -> fastboot_fail "dtb not found" (3469)
  app/aboot/aboot.c:3467   memmove(ramdisk_addr, ptr+page+ROUND(k), hdr->ramdisk_size)
  app/aboot/aboot.c:3468   memmove(kernel_addr, kernel_start, kernel_size)
  app/aboot/aboot.c:1218   boot_linux: second domain never touched on this path
  platform/msm_shared/dev_tree.c:2225 update_device_tree requires /memory and
              /chosen nodes; fdt_open_into grows totalsize by DTB_PAD_SIZE+cmdline
              in place at tags_addr
  app/aboot/fastboot.c:578 cmd handlers receive (download_base, download_size);
              base==SCRATCH 0x90000000, download_max==256MiB (target/msm8916/meminfo.c:79,84)
"""
import struct
import unittest
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO / 'scripts' / 'y35a'))
spec = importlib.util.spec_from_file_location(
    'native_pkg', REPO / 'scripts/y35a/package_native.py')
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)

SCRATCH = 0x90000000
DOWNLOAD_MAX = 256 * 1024 * 1024
DDR_START, DDR_END = 0x80000000, 0x100000000
ABOOT_BASE, ABOOT_SIZE = 0x8F600000, 0x00100000  # config.h: MEMBASE/MEMSIZE
SPLASH_START = 0x83200000  # measured continuous-splash framebuffer (y35a-facts V10)
PIN_WINDOW_END = 0x85900000  # ramdisk+tags reserved window end (V14.7)
PIN_RAMDISK, PIN_TAGS = 0x85700000, 0x85800000
PIN_KERNEL_MAX = 0x3180000
PIN_CMDLINE = b'y35a-native-xnu-experimental'
DTB_PAD_SIZE = 1024  # dev_tree.h DTB_PAD_SIZE


def round_up(x, n):
    return (x + n - 1) // n * n


class GateError(AssertionError):
    pass


def gate_model(img, sz=None):
    """One re-derivation of cmd_boot's decisions over container bytes."""
    if sz is None:
        sz = len(img)
    if sz < 8:
        raise GateError('3216: invalid bootimage header')
    (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size,
     second_addr, tags_addr, page_size, dt_size, _unused) = struct.unpack_from('<10I', img, 8)
    cmdline = img[64:64 + 512].split(b'\0')[0]
    if page_size == 0 or page_size > 4096 or page_size & (page_size - 1):
        raise GateError('3226: bad page_size adopted from header')
    actual = page_size + round_up(kernel_size, page_size) + round_up(ramdisk_size, page_size) \
        + round_up(second_size, page_size) + round_up(dt_size, page_size)
    if actual > sz:
        raise GateError('3248: bootimage header fields are invalid')
    if (DOWNLOAD_MAX - page_size) < actual:
        raise GateError('3317: image greater than boot buffer')

    kernel_bytes = img[page_size:page_size + kernel_size]
    if kernel_bytes[:2] == b'\x1f\x8b':
        raise GateError('3374: kernel-domain gzip path unmodelled (must ship raw Image)')
    text_offset = struct.unpack_from('<Q', kernel_bytes, 8)[0]
    image_size = struct.unpack_from('<Q', kernel_bytes, 16)[0]
    if struct.unpack_from('<I', kernel_bytes, 56)[0] != 0x644D5241:
        raise GateError('not an ARM64 Image header: IS_ARM64 false, pin cannot fire')
    if text_offset > 2 * 1024 * 1024:
        text_offset = 0  # 3393 HACK

    # update_ker_tags_rdisk_addr: stock policy then fork pin then text_offset remap
    ka, ra, ta = DDR_START + 0x80000, DDR_START + 0x2000000, DDR_START + 0x1E00000
    pinned = (text_offset == 0x80000 and kernel_size <= PIN_KERNEL_MAX
              and ramdisk_size == 1
              and img[64:64 + len(PIN_CMDLINE)] == PIN_CMDLINE
              and img[64 + len(PIN_CMDLINE)] == 0)
    if pinned:
        ra, ta = PIN_RAMDISK, PIN_TAGS
    if image_size:
        ka = (ka & ~0x1FFFFF) + text_offset

    rk, rr = round_up(kernel_size, page_size), round_up(ramdisk_size, page_size)
    for addr, size, name in ((ka, rk, 'kernel'), (ra, rr, 'ramdisk')):
        if not (addr < ABOOT_BASE or addr >= ABOOT_BASE + ABOOT_SIZE):
            raise GateError('3421 overlap: %s in aboot region' % name)
        if not (addr + size <= ABOOT_BASE or addr >= ABOOT_BASE + ABOOT_SIZE):
            raise GateError('3421 overlap: %s crosses into aboot region' % name)
        if addr < DDR_START or addr >= DDR_END or addr + size > DDR_END:
            raise GateError('3421 ddr: %s beyond DDR' % name)

    second_off = page_size + rk + rr
    dt_copied = False
    total = 0
    if dt_size:
        off = second_off + (round_up(second_size, page_size) if second_size else 0)
        table = img[off:off + dt_size]
        if table[:4] != b'QCDT':
            raise GateError('copy_dtb: bad QCDT magic')
        version, entries = struct.unpack_from('<II', table, 4)
        if version != 3:
            raise GateError('copy_dtb: unsupported table version %d' % version)
        hdr_size = round_up(12 + entries * 40, page_size)
        if hdr_size > round_up(dt_size, page_size):
            raise GateError('copy_dtb: invalid device tree size')
        matched = None
        for i in range(entries):
            fields = list(struct.unpack_from('<10I', table, 12 + i * 40))
            if fields[:3] != [206, 8, 23]:
                continue
            e_off, e_size = fields[8], fields[9]
            if e_size < 40 or e_off < hdr_size or e_off + e_size > len(table):
                raise GateError('copy_dtb: entry outside table')
            matched = table[e_off:e_off + e_size]
        if matched is None or matched[:4] != b'\xd0\x0d\xfe\xed':
            raise GateError('copy_dtb/dev_tree_appended: dtb not found (3469)')
        total = struct.unpack_from('>I', matched, 4)[0]
        if ta < DDR_START or ta + len(matched) > DDR_END:
            raise GateError('copy_dtb: tags beyond DDR')
        if not (ta < ABOOT_BASE or ta >= ABOOT_BASE + ABOOT_SIZE):
            raise GateError('copy_dtb: tags/aboot overlap')
        # boot_linux update_device_tree: grows in place, needs /memory + /chosen
        grown = total + DTB_PAD_SIZE + len(cmdline) + 1
        if ta + grown > PIN_WINDOW_END:
            raise GateError('update_device_tree: FDT growth exceeds reserved window')
        if ta + grown > DDR_END:
            raise GateError('update_device_tree: growth beyond DDR')
        dt_copied = True
    else:
        raise GateError('3445+: dt_size==0 -> dev_tree_appended has no FDT in our '
                        'kernel domain -> dtb not found (3469)')
    if ta < DDR_START or ta + rk > DDR_END:
        raise GateError('3445: tags bound vs kernel_actual')

    return dict(sz=sz, actual=actual, page=page_size, ka=ka, ra=ra, ta=ta,
                pinned=pinned, kernel_size=kernel_size, dt_size=dt_size,
                second_size=second_size, second_addr=second_addr,
                second_off=second_off, dt_copied=dt_copied,
                fdt_total=total, ramdisk_size=ramdisk_size)


def arm64_image_kernel(size):
    """Synthetic raw Image: valid kernel64_hdr geometry, not gzip."""
    k = bytearray(size)
    struct.pack_into('<Q', k, 8, 0x80000)           # text_offset
    struct.pack_into('<Q', k, 16, size)             # image_size (nonzero)
    struct.pack_into('<I', k, 56, 0x644D5241)       # 'ARMd'
    return bytes(k)


def synthetic_qcdt(fdt_size=4096):
    fdt = bytearray(fdt_size)
    fdt[:4] = b'\xd0\x0d\xfe\xed'
    struct.pack_into('>I', fdt, 4, fdt_size)
    table = bytearray(2048 + fdt_size)
    struct.pack_into('<III', table, 0, 0x54444351, 3, 1)
    struct.pack_into('<10I', table, 12, 206, 8, 23, 0, 0, 0, 0, 0, 2048, fdt_size)
    table[2048:2048 + fdt_size] = fdt
    return bytes(table)


class FourDomainContainerTest(unittest.TestCase):
    def test_header_arithmetic_and_domain_order(self):
        k = arm64_image_kernel(11 * 1024 * 1024)
        dt = synthetic_qcdt()
        second = b'S' * 64 * 1024
        img = pkg.android_container(k, dt, second=second, ramdisk=b'\0')
        m = gate_model(img)
        self.assertTrue(m['pinned'], 'fork pin v1 must fire')
        self.assertTrue(m['dt_copied'], 'copy_dtb must succeed')
        self.assertEqual((m['ka'], m['ra'], m['ta']), (0x80080000, 0x85700000, 0x85800000))
        self.assertEqual(m['actual'], len(img), 'image_actual must equal sz exactly')
        p = m['page']
        self.assertEqual(img[64:64 + len(PIN_CMDLINE)], PIN_CMDLINE)
        self.assertEqual(img[p:p + len(k)], k)
        rk = round_up(len(k), p)
        self.assertEqual(img[p + rk], 0, 'ramdisk domain byte must be the \\0 placeholder')
        self.assertEqual(img[p + rk + 1:p + rk + p], b'\0' * (p - 1))
        self.assertEqual(img[p + rk + p:p + rk + p + len(second)], second)
        r2 = round_up(len(second), p)
        self.assertEqual(img[p + rk + p + r2:p + rk + p + r2 + len(dt)], dt)
        self.assertEqual(len(img), p + rk + p + r2 + round_up(len(dt), p))

    def test_second_addr_names_scratch_placement(self):
        k = arm64_image_kernel(11 * 1024 * 1024)
        second = b'S' * (1 << 20)
        img = pkg.android_container(k, synthetic_qcdt(), second=second, ramdisk=b'\0')
        m = gate_model(img)
        self.assertEqual(m['second_addr'], SCRATCH + m['second_off'])

    def test_ramdisk_must_be_single_byte_placeholder(self):
        with self.assertRaises(ValueError):
            pkg.android_container(arm64_image_kernel(8192), synthetic_qcdt(),
                                  second=b'x' * 4096, ramdisk=b'ab')

    def test_kernel_beyond_pin_budget_refused(self):
        with self.assertRaises(ValueError):
            pkg.android_container(arm64_image_kernel(PIN_KERNEL_MAX + 2048),
                                  synthetic_qcdt(), second=b'x' * 4096, ramdisk=b'\0')

    def test_bare_fdt_dt_domain_refused(self):
        # source truth (copy_dtb calls dev_tree_validate first): QCDT required
        with self.assertRaises(ValueError):
            pkg.android_container(arm64_image_kernel(8192), b'\xd0\x0d\xfe\xed' + bytes(4092),
                                  second=b'', ramdisk=b'\0')

    def test_kernel_domain_end_never_reaches_splash(self):
        k = arm64_image_kernel(PIN_KERNEL_MAX)
        img = pkg.android_container(k, synthetic_qcdt(), second=b'x' * 4096, ramdisk=b'\0')
        m = gate_model(img)
        self.assertLessEqual(m['ka'] + round_up(len(k), m['page']), SPLASH_START)

    def test_dt_domain_is_page_padded_in_total(self):
        k = arm64_image_kernel(8192)
        dt = synthetic_qcdt(3000)  # 3000+2048 = 5048 not page-multiple
        img = pkg.android_container(k, dt, second=b'', ramdisk=b'\0')
        self.assertEqual(len(img) % 2048, 0, 'container total must end page-aligned')
        self.assertEqual(gate_model(img)['dt_size'], len(dt))

    def test_sha1_digest_covers_second_domain(self):
        k = arm64_image_kernel(8192)
        dt = synthetic_qcdt()
        a = pkg.android_container(k, dt, second=b'A' * 8192, ramdisk=b'\0')
        b = pkg.android_container(k, dt, second=b'B' * 8192, ramdisk=b'\0')
        self.assertNotEqual(a[576:596], b[576:596])

    def test_legacy_two_arg_call_keeps_probe_geometry(self):
        # probe_emmc.py / readback_native.py call android_container(k, dt)
        k = arm64_image_kernel(8192)
        img = pkg.android_container(k, synthetic_qcdt())
        m = gate_model(img)
        self.assertTrue(m['pinned'] and m['dt_copied'])
        self.assertEqual(m['second_size'], 0)
        self.assertEqual(m['actual'], len(img))


class EntrySourceContractTest(unittest.TestCase):
    """generate_entry_source must be exposed and read rootfs from SCRATCH."""

    def source(self):
        return pkg.generate_entry_source(
            segments=[(0, 0xA0000000, 802816)],
            kernel_data_name='kernel-packed.macho',
            physical_base=0xA0000000, memory_end=0xB78000,
            args_pa=0xA0B7C000, args_len=1152, tree_pa=0xA0B7D000,
            tree_len=64, tree_name='board.adt',
            rootfs=dict(scratch=0x90AE3000, physical=0xA0B84000, size=1 << 20),
            trustcache=dict(physical=0xA3484000, size=3875, name='trustcache.bin'),
            entry=0xA026E0A0, kernel_sha256_8=bytes(8))

    def test_rootfs_sources_from_scratch_address(self):
        src = self.source().lower()
        self.assertIn('ldr x0,=0x90ae3000', src)
        self.assertIn('ldr x1,=0xa0b84000', src)

    def test_rootfs_not_incbinned_into_kernel_domain(self):
        src = self.source()
        self.assertNotIn('ramdisk.bin', src)
        self.assertNotIn('.incbin "board.adt"', '')  # sanity for the next line
        self.assertIn('.incbin "board.adt"', src)   # ADT stays a real sidecar
        self.assertIn('.incbin "trustcache.bin"', src)
        self.assertIn('.incbin "kernel-packed.macho"', src)


class ArtifactGateTest(unittest.TestCase):
    PATH = REPO / 'out/y35a/ios12-boot3/boot3.img'

    def test_shipped_boot3_walks_every_gate(self):
        if not self.PATH.exists():
            self.skipTest('boot3.img not built yet')
        m = gate_model(self.PATH.read_bytes())
        self.assertTrue(m['pinned'] and m['dt_copied'])
        self.assertLessEqual(m['ka'] + round_up(m['kernel_size'], m['page']), SPLASH_START)
        self.assertLessEqual(m['ta'] + m['fdt_total'] + DTB_PAD_SIZE + len(PIN_CMDLINE) + 1, PIN_WINDOW_END)

    def test_shipped_second_domain_matches_host_hfs_rootfs(self):
        if not self.PATH.exists():
            self.skipTest('boot3.img not built yet')
        raw = (REPO / 'out/y35a/ios12-root.work/ramdisk-hfs.raw').read_bytes()
        m = gate_model(self.PATH.read_bytes())
        img = self.PATH.read_bytes()
        self.assertEqual(raw[0x400:0x402], b'HX')
        self.assertEqual(img[m['second_off']:m['second_off'] + len(raw)], raw)


class BootArgsEraContractTest(unittest.TestCase):
    """make_boot_args must match the kernel we actually boot (xnu-4903,
    pexpert/pexpert/arm64/boot.h + genassym.c BA_* offsets).

    The 4903 prefix (virtBase@8 .. deviceTreeLength@0x68) is byte-identical
    to the Darwin-23 struct the packer emits, but the command line is
    BOOT_LINE_LENGTH=256 (not 1024) and bootFlags/memSizeActual live at
    0x170/0x178. The shim flushes the whole 0x480 buffer and the entry
    branch never fetches the 4903 tail fields, so zeros there are safe;
    the one real guard is that the command line must NUL-terminate inside
    its 256-byte field, or it bleeds into what the kernel reads as
    bootFlags."""

    def setUp(self):
        import boot_layout
        self.bl = boot_layout

    def pack(self, cmdline):
        return self.bl.make_boot_args(
            virtual_base=0xFFFFFFF007004000, physical_base=0xA0004000,
            memory_size=0x10000000, top=0xA3488000,
            tree_physical=0xA0B7D000, tree_size=12400, command_line=cmdline)

    def test_kernel_actual_field_offsets(self):
        b = self.pack('-v serial=3 cpus=1 debug=0x8 rd=md0')
        self.assertEqual(len(b), 0x180)  # iOS 12.4.1 boot_args layout; shim flushes this whole buffer
        self.assertEqual(struct.unpack_from('<HH', b, 0), (2, 2))
        self.assertEqual(struct.unpack_from('<Q', b, 0x08)[0], 0xFFFFFFF007004000)
        self.assertEqual(struct.unpack_from('<Q', b, 0x10)[0], 0xA0004000)
        self.assertEqual(struct.unpack_from('<Q', b, 0x18)[0], 0x10000000)
        self.assertEqual(struct.unpack_from('<Q', b, 0x20)[0], 0xA3488000)
        self.assertEqual(struct.unpack_from('<Q', b, 0x60)[0], 0xFFFFFFF007004000 + (0xA0B7D000 - 0xA0004000))
        self.assertEqual(struct.unpack_from('<I', b, 0x68)[0], 12400)
        self.assertEqual(struct.unpack_from('<QQ', b, 0x170), (0, 0x10000000))  # 4903 bootFlags/memSizeActual
        self.assertEqual(b[0x6c:0x6c + 35], b'-v serial=3 cpus=1 debug=0x8 rd=md0')

    def test_cmdline_beyond_kernel_field_refused(self):
        # RED until the bound matches BOOT_LINE_LENGTH: a 256-byte command
        # has no NUL inside the kernel's CommandLine field and would spill
        # into what 4903 reads as bootFlags@0x170.
        with self.assertRaises(ValueError):
            self.pack('x' * 256)

    def test_cmdline_at_kernel_field_boundary_accepted(self):
        b = self.pack('x' * 255)  # 255 + NUL = exactly BOOT_LINE_LENGTH
        self.assertEqual(b[0x6c + 255], 0)


class RealQCDTGateTest(unittest.TestCase):
    STOCK = REPO.parent / 'evidence/y35a-20261102/stock-boot.img'

    def test_minified_stock_qcdt_passes_copy_dtb(self):
        if not self.STOCK.exists():
            self.skipTest('stock boot.img evidence absent')
        stock = self.STOCK.read_bytes()
        v = struct.unpack_from('<10I', stock, 8)
        off = v[7] + round_up(v[0], v[7]) + round_up(v[2], v[7]) + round_up(v[4], v[7])
        qcdt = pkg.select_device_dt(stock[off:off + v[8]])
        k = arm64_image_kernel(8192)
        m = gate_model(pkg.android_container(k, qcdt, second=b'S' * 4096, ramdisk=b'\0'))
        self.assertTrue(m['dt_copied'])
        fields = struct.unpack_from('<10I', qcdt, 12)
        total = struct.unpack_from('>I', qcdt[fields[8]:fields[8] + fields[9]], 4)[0]
        self.assertLessEqual(m['ta'] + total + DTB_PAD_SIZE + len(PIN_CMDLINE) + 1, PIN_WINDOW_END,
                             'stock FDT plus LK growth must fit the reserved window')


if __name__ == '__main__':
    unittest.main()
