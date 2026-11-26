#!/usr/bin/env python3
"""Experimental, single-CPU Y35A hardware ADT for native 4KiB XNU bring-up.

Measured inputs: efff9d92 PD1502A_A_1.18.0, /proc/iomem and the AArch64
register probe preserved under unixnu-research/evidence/y35a-20261102.
This is neither Apple device identity nor evidence of a booted XNU kernel.
Only an explicitly owned contiguous RAM window is exposed, not secure carveouts.
"""
from pathlib import Path
import argparse,os,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unixnu.devicetree import node,empty_nvram_proxy
RAM_RANGES=((0x80000000,0x83000000),(0x84400000,0x86000000),(0x8c300000,0x9ff00000),(0xa0000000,0xfffff000))
# XNU treats a zero SoC base as a missing bus and skips clock discovery.
# Describe the real UART/GIC window with relative child addresses instead.
SOC_BASE=0x07800000
def make_tree(*,random_seed,physical_base=0xa0000000,memory_size=0x10000000,warm_reset_prepared=False,memory_map=None):
    if len(random_seed)!=64:raise ValueError('XNU random-seed must contain 64 supplied entropy bytes')
    if (physical_base%4096 or memory_size<0x10000000 or memory_size%0x200000 or
        not any(start<=physical_base and physical_base+memory_size<=end for start,end in RAM_RANGES)):
        raise ValueError('Owned RAM window crosses an unverified or reserved physical range')
    mappings=[]
    for name,(address,size) in (memory_map or {}).items():
        if (name not in ('RAMDisk','TrustCache') or address%4096 or size<=0 or
            not physical_base<=address<address+size<=physical_base+memory_size):
            raise ValueError('Memory sidecar is outside owned RAM or has an invalid extent')
        mappings.append((name,struct.pack('<QQ',address,size)))
    return node('device-tree',[
        ('model',b'vivo Y35A experimental\0'),('compatible',b'vivo,pd1502a\0'),
        ('#address-cells',struct.pack('<I',2)),('#size-cells',struct.pack('<I',2)),
    ],[
        node('chosen',[
            ('random-seed',random_seed),('dram-base',struct.pack('<Q',physical_base)),
            ('crypto-hash-method',b'sha2-384\0'),
            ('amfi-only-platform-code',struct.pack('<I',1)),
            ('embedded-panic-log-size',struct.pack('<I',0x10000)),
            ('dram-size',struct.pack('<Q',memory_size)),('darwinboot-memory-size',struct.pack('<Q',memory_size)),
            ('osenvironment',b'ramdisk\0'),*empty_nvram_proxy(),
        ],[node('memory-map',mappings),node('manifest-properties')]),
        node('cpus',children=[node('cpu0',[
            ('state',b'running\0'),('device_type',b'cpu\0'),('compatible',b'arm,cortex-a53\0'),
            ('reg',struct.pack('<I',0)),('timebase-frequency',struct.pack('<I',19200000)),
        ])]),
        # Original PD1502A DTB and upstream msm8916.dtsi agree: virtual PPI 4,
        # INTID 20. The frequently used QEMU virtual timer is INTID 27 instead.
        node('timer',[('compatible',b'arm,armv8-timer\0'),
            ('interrupt-parent',struct.pack('<I',1)),
            ('interrupts',struct.pack('<12I',1,2,0xf08,1,3,0xf08,1,4,0xf08,1,1,0xf08))]),
        node('defaults',[('sleep-disabled',struct.pack('<I',1))]),
        node('options'),
        node('pram',[('reg',struct.pack('<QQ',0x859e0000,0x10000))]),
        *([node('pshold',[('compatible',b'qcom,pshold\0'),
            ('reg',struct.pack('<QQ',0x004ab000,4)),
            ('unixnu,warm-reset-prepared',struct.pack('<I',1))])] if warm_reset_prepared else []),
        node('product',[('product-name',b'vivo Y35A experimental\0'),('model',b'vivo,pd1502a\0')]),
        node('arm-io',[
            ('device_type',b'qcom-msm8916\0'),('#address-cells',struct.pack('<I',2)),
            ('#size-cells',struct.pack('<I',2)),('ranges',struct.pack('<QQQ',0,SOC_BASE,0x10000000-SOC_BASE)),
        ],[
            node('intc',[('compatible',b'qcom,msm-qgic2\0arm,gic-400\0'),
                ('AAPL,phandle',struct.pack('<I',1)),('interrupt-controller',b''),
                ('#interrupt-cells',struct.pack('<I',3)),('#address-cells',struct.pack('<I',0)),
                ('reg',struct.pack('<4Q',0x0b000000-SOC_BASE,0x1000,0x0b002000-SOC_BASE,0x2000))]),
            node('uart0',[('compatible',b'qcom,msm-uartdm-v1.4\0'),
                ('reg',struct.pack('<2Q',0x078b0000-SOC_BASE,0x200))]),
            # Measured PD1502A DTB sdhc1 facts (SPEC 2/3.4): hc window maps at
            # index 0, core window at index 1 — NativeSdcc depends on this
            # order; regulators are board-strapped always-on and lk2nd leaves
            # them configured, hence the presence flags only.
            node('sdhc1',[('compatible',b'qcom,sdhci-msm\0'),
                ('reg',struct.pack('<4Q',0x07824900-SOC_BASE,0x11c,0x07824000-SOC_BASE,0x800)),
                ('reg-names',b'hc_mem\0core_mem\0'),
                ('interrupt-parent',struct.pack('<I',1)),
                ('interrupts',struct.pack('<6I',0,123,4,0,138,4)),
                ('qcom,bus-width',struct.pack('<I',8)),
                ('qcom,clk-rates',struct.pack('<5I',400000,25000000,50000000,100000000,192000000)),
                ('qcom,bus-speed-mode',b'HS200_1p8v\0DDR_1p8v\0'),
                ('vdd-always-on',struct.pack('<I',1)),
                ('vdd-io-always-on',struct.pack('<I',1)),
                ('unixnu,handoff',struct.pack('<I',1))]),
            # Stock PD1502A exposes the removable TF controller as sdhc2:
            # 4-bit bus and active-low card detect on TLMM GPIO38. The first
            # SD adapter is polling-only; card detect is retained as board
            # metadata until a TLMM consumer is linked into XNU.
            node('sdhc2',[('compatible',b'qcom,sdhci-msm\0'),
                ('reg',struct.pack('<4Q',0x07864900-SOC_BASE,0x11c,0x07864000-SOC_BASE,0x800)),
                ('reg-names',b'hc_mem\0core_mem\0'),
                ('qcom,bus-width',struct.pack('<I',4)),
                ('qcom,clk-rates',struct.pack('<4I',400000,25000000,50000000,100000000)),
                ('qcom,card-detect-gpio',struct.pack('<I',38)),
                ('qcom,card-detect-active-low',struct.pack('<I',1)),
                ('unixnu,slot',struct.pack('<I',2)),
                ('unixnu,poll-only',struct.pack('<I',1)),
                ('vdd-always-on',struct.pack('<I',1)),
                ('vdd-io-always-on',struct.pack('<I',1)),
                ('unixnu,handoff',struct.pack('<I',1))]),
            # Measured PD1502A DTB touch facts (y35a-facts 49-60): BLSP1 QUP5
            # SE + BAM windows, qup_irq SPI 99, bam_irq SPI 238, 400 kHz out.
            # pinctrl/PIC_3B/PMIC supplies are DT phandles with no XNU-side
            # consumer yet; lk2nd leaves the bus powered, hence always-on
            # presence flags only (same convention as sdhc1).
            node('qup_i2c5',[('compatible',b'qcom,i2c-msm-v2\0'),
                ('reg',struct.pack('<4Q',0x078b9000-SOC_BASE,0x600,0x07884000-SOC_BASE,0x23000)),
                ('reg-names',b'qup_mem\0bam_mem\0'),
                ('interrupt-parent',struct.pack('<I',1)),
                ('interrupts',struct.pack('<6I',0,99,4,0,238,4)),
                ('clock-frequency',struct.pack('<I',400000)),
                ('#address-cells',struct.pack('<I',1)),('#size-cells',struct.pack('<I',1)),
                ('vdd_ana-always-on',struct.pack('<I',1)),
                ('vcc_i2c-always-on',struct.pack('<I',1)),
                ('unixnu,handoff',struct.pack('<I',1))],
                # rmi_i2c@20 identity facts (facts 53-60); NativeHidDigitizer
                # reads reg/attn_polarity/gpios/dimensions.
                [node('rmi4',[('reg',struct.pack('<I',0x20)),
                    # IONameMatch in the personality patch consults the
                    # standard compatible property (IODTCompareNubName), so
                    # the dtb10.dts IC identity lives here, not only in the
                    # vendor key below.
                    ('compatible',b'synaptics_3202\0'),
                    ('vivo,use-ic-list',b'synaptics_3202\0'),
                    ('reset-gpio',struct.pack('<I',12)),
                    ('irq-gpio',struct.pack('<I',13)),
                    ('attn_polarity',struct.pack('<I',0)),
                    ('ts-dimension',struct.pack('<2I',1266,2220)),
                    ('lcd-dimension',struct.pack('<2I',720,1280))])]),
        ]),
    ])
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--physical-base',type=lambda x:int(x,0),default=0xa0000000)
    p.add_argument('--memory-size',type=lambda x:int(x,0),default=0x10000000)
    a=p.parse_args();blob=make_tree(random_seed=os.urandom(64),physical_base=a.physical_base,memory_size=a.memory_size)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(blob)
    print('Experimental Y35A ADT:',len(blob),'bytes; one CPU, GICv2, initialized UARTDM; not hardware-boot validated')
if __name__=='__main__':main()
