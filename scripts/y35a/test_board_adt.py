#!/usr/bin/env python3
"""Check the emitted ADT against measured MMIO and XNU's early clock contract."""
import struct
import unittest
from make_adt import make_tree


def decode(blob, offset=0):
    properties, children = struct.unpack_from('<II', blob, offset)
    offset += 8
    values = {}
    for _ in range(properties):
        name = blob[offset:offset+32].split(b'\0')[0].decode()
        length = struct.unpack_from('<I', blob, offset+32)[0]
        offset += 36
        values[name] = blob[offset:offset+length]
        offset += (length+3) & ~3
    nodes = {}
    for _ in range(children):
        child, offset = decode(blob, offset)
        nodes[child[0]['name'].rstrip(b'\0').decode()] = child
    return (values, nodes), offset


class BoardADT(unittest.TestCase):
    def test_interrupts_resolve_to_a_complete_xnu_controller(self):
        root, _ = decode(make_tree(random_seed=bytes(64)))
        entries = []
        def visit(entry):
            entries.append(entry[0])
            for child in entry[1].values():
                visit(child)
        visit(root)
        handles = {p['AAPL,phandle']: p for p in entries if 'AAPL,phandle' in p}
        for props in entries:
            if 'interrupts' not in props:
                continue
            self.assertIn('interrupt-parent', props)
            self.assertIn(props['interrupt-parent'], handles)
            controller = handles[props['interrupt-parent']]
            self.assertIn('interrupt-controller', controller)
            cells, = struct.unpack('<I', controller['#interrupt-cells'])
            self.assertEqual(cells, 3)
            self.assertEqual(len(props['interrupts']) % (4 * cells), 0)
            self.assertEqual(controller['#address-cells'], struct.pack('<I', 0))

    def test_stock_architectural_timer_wiring(self):
        root, _ = decode(make_tree(random_seed=bytes(64)))
        props = root[1]['timer'][0]
        self.assertEqual(props['compatible'], b'arm,armv8-timer\0')
        self.assertEqual(struct.unpack('<12I',props['interrupts']),
                         (1,2,0xf08,1,3,0xf08,1,4,0xf08,1,1,0xf08))

    def test_sdhci_emmc_node_encodes_measured_windows(self):
        # SPEC 3.4/2: hc window first (index 0), core window second (index 1),
        # relative to arm-io ranges (SOC_BASE 0x07800000), each two 64-bit cells.
        root, _ = decode(make_tree(random_seed=bytes(64)))
        props = root[1]['arm-io'][1]['sdhc1'][0]
        self.assertEqual(props['compatible'], b'qcom,sdhci-msm\0')
        hc_rel, hc_len, core_rel, core_len = struct.unpack('<4Q', props['reg'])
        self.assertEqual((hc_rel, hc_len), (0x24900, 0x11c))
        self.assertEqual((core_rel, core_len), (0x24000, 0x800))
        io_ranges = struct.unpack('<QQQ', root[1]['arm-io'][0]['ranges'])[1]  # parent base
        self.assertEqual((io_ranges + hc_rel, io_ranges + core_rel),
                         (0x07824900, 0x07824000))
        self.assertEqual(props['reg-names'], b'hc_mem\0core_mem\0')
        self.assertEqual(props['qcom,bus-width'], struct.pack('<I', 8))
        self.assertEqual(struct.unpack('<5I', props['qcom,clk-rates']),
                         (400000, 25000000, 50000000, 100000000, 192000000))
        self.assertEqual(props['qcom,bus-speed-mode'], b'HS200_1p8v\0DDR_1p8v\0')
        self.assertEqual(props['unixnu,handoff'], struct.pack('<I', 1))
        self.assertEqual(props['vdd-always-on'], struct.pack('<I', 1))
        self.assertEqual(props['vdd-io-always-on'], struct.pack('<I', 1))

    def test_sdhci_interrupts_resolve_to_intid_155_and_170(self):
        root, _ = decode(make_tree(random_seed=bytes(64)))
        props = root[1]['arm-io'][1]['sdhc1'][0]
        cells = struct.unpack('<6I', props['interrupts'])
        self.assertEqual(cells, (0, 123, 4, 0, 138, 4))  # SPI 123 hc_irq, SPI 138 pwr_irq
        self.assertEqual(props['interrupt-parent'],
                         root[1]['arm-io'][1]['intc'][0]['AAPL,phandle'])
        # GICv2 legacy accounting: SPI n maps to INTID n + 32.
        self.assertEqual([cells[1] + 32, cells[4] + 32], [155, 170])

    def test_touch_i2c_bus_node_encodes_measured_windows_and_irqs(self):
        # facts 49-60: BLSP1 QUP5 SE at 0x78b9000 len 0x600, qup_irq SPI 99
        # (INTID 131), bam_irq SPI 238 (INTID 270), 400 kHz out / 19.2 MHz in.
        # PMIC supplies and pinctrl are board-strapped always-on (lk2nd leaves
        # them configured), so the node carries presence facts only, same
        # convention as sdhc1's vdd-always-on flags.
        root, _ = decode(make_tree(random_seed=bytes(64)))
        props = root[1]['arm-io'][1]['qup_i2c5'][0]
        self.assertEqual(props['compatible'], b'qcom,i2c-msm-v2\0')
        se_rel, se_len, bam_rel, bam_len = struct.unpack('<4Q', props['reg'])
        self.assertEqual((se_rel, se_len), (0xb9000, 0x600))
        self.assertEqual((bam_rel, bam_len), (0x84000, 0x23000))
        cells = struct.unpack('<6I', props['interrupts'])
        self.assertEqual(cells, (0, 99, 4, 0, 238, 4))
        self.assertEqual([cells[1] + 32, cells[4] + 32], [131, 270])
        self.assertEqual(props['interrupt-parent'],
                         root[1]['arm-io'][1]['intc'][0]['AAPL,phandle'])
        self.assertEqual(struct.unpack('<I', props['clock-frequency'])[0], 400000)

    def test_rmi4_child_node_carries_probe_identity_and_geometry(self):
        # facts 53-60: rmi_i2c@20 "synaptics_3202"; reset-gpio TLMM 12,
        # irq-gpio TLMM 13 (attn_polarity 0); ts 1266x2220 scaled to lcd
        # 720x1280.  arm-io #address-cells/#size-cells are 2+2 for the 64-bit
        # MMIO parents, so the child declares 1+1 locally and its single-cell
        # reg is the literal I2C address.
        root, _ = decode(make_tree(random_seed=bytes(64)))
        bus = root[1]['arm-io'][1]['qup_i2c5']
        self.assertEqual(struct.unpack('<I', bus[0]['#address-cells'])[0], 1)
        self.assertEqual(struct.unpack('<I', bus[0]['#size-cells'])[0], 1)
        props = bus[1]['rmi4'][0]
        self.assertEqual(struct.unpack('<I', props['reg'])[0], 0x20)
        # The personality matches this nub by IONameMatch='synaptics_3202';
        # IODTCompareNubName only consults name/compatible/device_type/model,
        # so the identity must live in the standard compatible property.
        self.assertEqual(props['compatible'], b'synaptics_3202\0')
        self.assertEqual(props['vivo,use-ic-list'], b'synaptics_3202\0')
        self.assertEqual(struct.unpack('<I', props['reset-gpio'])[0], 12)
        self.assertEqual(struct.unpack('<I', props['irq-gpio'])[0], 13)
        self.assertEqual(struct.unpack('<I', props['attn_polarity'])[0], 0)
        self.assertEqual(struct.unpack('<2I', props['ts-dimension']), (1266, 2220))
        self.assertEqual(struct.unpack('<2I', props['lcd-dimension']), (720, 1280))

    def test_memory_disks_are_explicit_owned_ranges(self):
        root, _ = decode(make_tree(random_seed=bytes(64),
                                  memory_map={'RAMDisk': (0xa6000000, 8192),
                                              'TrustCache': (0xa6002000, 56)}))
        props = root[1]['chosen'][1]['memory-map'][0]
        self.assertEqual(struct.unpack('<QQ', props['RAMDisk']), (0xa6000000, 8192))
        self.assertEqual(struct.unpack('<QQ', props['TrustCache']), (0xa6002000, 56))
        for mapping in ({'RAMDisk': (0x80000000, 4096)},
                        {'RAMDisk': (0xaffff000, 8192)},
                        {'RAMDisk': (0xa6000001, 4096)},
                        {'RAMDisk': (0xa6000000, 0)}):
            with self.assertRaises(ValueError):
                make_tree(random_seed=bytes(64), memory_map=mapping)

    def test_manifest_container_has_no_fabricated_properties(self):
        root, _ = decode(make_tree(random_seed=bytes(range(64))))
        chosen = root[1]['chosen']
        self.assertIn('manifest-properties', chosen[1])
        properties, children = chosen[1]['manifest-properties']
        self.assertEqual(properties, {'name': b'manifest-properties\0'})
        self.assertEqual(children, {})

    def test_xnu_clock_discovery_and_mmio_translation(self):
        blob = make_tree(random_seed=bytes(range(64)))
        root, consumed = decode(blob)
        self.assertEqual(consumed, len(blob))
        bus, devices = root[1]['arm-io']
        child_base, parent_base, length = struct.unpack('<QQQ', bus['ranges'])
        # pe_identify_machine returns before reading timebase-frequency if zero.
        self.assertNotEqual(parent_base, 0)
        for name, expected in [('uart0', [(0x078b0000,0x200)]),
                               ('intc', [(0x0b000000,0x1000),(0x0b002000,0x2000)])]:
            actual = []
            for address, size in struct.iter_unpack('<QQ', devices[name][0]['reg']):
                self.assertGreaterEqual(address, child_base)
                self.assertLessEqual(address-child_base+size, length)
                actual.append((parent_base+address-child_base,size))
            self.assertEqual(actual, expected)
        cpu = root[1]['cpus'][1]['cpu0'][0]
        self.assertEqual(cpu['state'], b'running\0')
        self.assertEqual(struct.unpack('<I', cpu['timebase-frequency'])[0], 19200000)


if __name__ == '__main__':
    unittest.main()
