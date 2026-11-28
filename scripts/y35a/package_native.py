#!/usr/bin/env python3
"""Experimental RAM-only native-XNU Android-container builder for Y35A.

No flashing is performed. The kernel must already be linked; a generated image
is not evidence of kernel execution. The shim reproduces the owned-memory and
boot_args handoff ABI in DarwinBoot, without claiming full UEFI implementation.
"""
from pathlib import Path
import argparse,struct,hashlib,subprocess,json,re,uuid
from boot_layout import parse_macho,make_boot_args,validate_window,physical_base_for
from make_adt import make_tree
PAGE=2048
LOAD=0x80080000
OWNED_BASE=0xa0000000
DEFAULT_OWNED_SIZE=0x10000000
align=lambda x,n:(x+n-1)//n*n

def select_device_dt(table):
    if len(table)<12 or table[:4]!=b'QCDT':raise ValueError('Expected stock QCDT')
    version,count=struct.unpack_from('<II',table,4)
    if version!=3 or not 0<count<=4096 or 12+count*40>len(table):raise ValueError('Unsupported/truncated QCDT')
    matches=[]
    for i in range(count):
        fields=list(struct.unpack_from('<10I',table,12+i*40))
        if fields[:3]!=[206,8,23]:continue
        offset,size=fields[8:10]
        if size<40 or offset<12+count*40 or offset+size>len(table):raise ValueError('Invalid stock DTB range')
        dtb=table[offset:offset+size]
        if dtb[:4]!=b'\xd0\x0d\xfe\xed':raise ValueError('Invalid stock FDT magic')
        matches.append((fields,dtb))
    if not matches:raise ValueError('No DTB matches measured MSM8916/MTP/subtype23')
    # Preserve all revisions/PMIC variants for this measured board; let LK apply its normal revision selection.
    cursor=align(12+40*len(matches),PAGE);result=bytearray(cursor)
    struct.pack_into('<III',result,0,0x54444351,3,len(matches))
    for i,(fields,dtb) in enumerate(matches):
        fields[8]=cursor;struct.pack_into('<10I',result,12+i*40,*fields)
        result.extend(dtb);result.extend(bytes(align(len(result),PAGE)-len(result)));cursor=len(result)
    return bytes(result)

SCRATCH=0x90000000  # lk2nd download buffer base (target/msm8916 iomap/SCRATCH_ADDR)
PIN_KERNEL_MAX=0x3180000  # aboot.c:412 fork-pin kernel_size budget
CMDLINE=b'y35a-native-xnu-experimental'
RAMDISK_COMMAND_LINE='-v serial=3 cpus=1 debug=0x8 rd=md0'

def _canonical_apfs_uuid(value, label):
    if not isinstance(value, str) or not re.fullmatch(
            r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}',
            value):
        raise ValueError(f'{label} must be a canonical 8-4-4-4-12 UUID string')
    canonical=str(uuid.UUID(value)).upper()
    if canonical == '00000000-0000-0000-0000-000000000000':
        raise ValueError(f'{label} must not be the nil UUID')
    return canonical

def make_external_root_command_line(tf_uuid, emmc_uuid=None):
    tf=_canonical_apfs_uuid(tf_uuid, 'TF APFS root UUID')
    command=f'-v serial=3 cpus=1 debug=0x8 rd=uuid boot-uuid={tf}'
    if emmc_uuid is not None:
        command+=' emmc-boot-uuid='+_canonical_apfs_uuid(emmc_uuid, 'eMMC APFS root UUID')
    if len(command.encode('ascii')) >= 256:
        raise ValueError('External-root boot arguments exceed BOOT_LINE_LENGTH')
    return command

def second_off_for(entry_len):
    # cmd_boot geometry: page + ROUND(kernel) + ROUND(ramdisk=1B) before second.
    return PAGE+align(max(entry_len,1),PAGE)+PAGE

def generate_entry_source(*,segments,kernel_data_name,physical_base,memory_end,
    args_pa,args_len,tree_pa,tree_len,tree_name,rootfs,trustcache,entry,kernel_sha256_8):
    # The shim reproduces the owned-memory and boot_args handoff ABI. rootfs
    # rides the container's second domain at SCRATCH+second_off (no incbin),
    # everything else keeps the boot1-proven copy logic byte-for-byte.
    segment_rows = []
    for segment in segments:
        if len(segment) == 3:
            o, a, file_size = segment
            zero_size = 0
        else:
            o, a, file_size, vm_size = segment
            zero_size = align(max(vm_size - file_size, 0), 64)
        segment_rows.append(f" .quad {o}, {a}, {file_size}, {zero_size}")
    segment_table='\n'.join(segment_rows)
    tc_copy=f" adr x0,sidecar_0\n ldr x1,={trustcache['physical']:#x}\n ldr x2,={trustcache['size']:#x}\n bl copy_bytes" if trustcache else ""
    tc_clean=''
    if trustcache:
        clean_bytes=align(trustcache['size'],64)
        tc_clean=(f"\n // Clean the TrustCache sidecar to PoC before XNU remaps it.\n"
                  f" ldr x0,={trustcache['physical']:#x}\n"
                  f" mov x2, #{clean_bytes:#x}\n"
                  f"trustcache_clean:\n"
                  f" dc cvac, x0\n"
                  f" add x0, x0, #64\n"
                  f" subs x2, x2, #64\n"
                  f" b.ne trustcache_clean\n"
                  f" dsb sy")
    tc_probe=(f" ldr x9,={trustcache['physical']:#x}\n"
              f" ldr w10, [x9]\n"
              f" ldr x9,=0x859f0000\n"
              f" str w10, [x9,#32]") if trustcache else ''
    tc_data=f' .balign 16\nsidecar_0:\n .incbin "{trustcache["name"]}"' if trustcache else ""
    rootfs_copy=''
    if rootfs:
        rootfs_copy=(f" ldr x0,={rootfs['scratch']:#x}\n ldr x1,={rootfs['physical']:#x}"
                     f"\n ldr x2,={rootfs['size']:#x}\n bl copy_bytes")
    return f'''// Experimental EL1 handoff shim. No storage writes, no full-OS claim.
.section .text
.global _start
_start:
 b enter
 .word 0
 .quad 0x80000
 .quad image_end-_start
 .quad 0
 .quad 0
 .quad 0
 .quad 0
 .word 0x644d5241
 .word 0
enter:
 msr daifset,#15
 ldr x10,=0x859f0000
 ldr x11,={int.from_bytes(b'Y35AXNU1','little'):#x}
 str x11,[x10]
 ldr x11,={int.from_bytes(kernel_sha256_8,'little'):#x}
 str x11,[x10,#8]
 mrs x9,CurrentEL
 str x9,[x10,#16]
 cmp x9,#4
 b.ne halt
 mrs x9,sctlr_el1
 tst x9,#1
 b.ne halt
 // Pet APCS KPSS Watchdog via WDT_RST (0x0b017004)
 ldr x9,=0x0b017004
 mov w10,#1
 str w10,[x9]
 ldr x0,={physical_base:#x}
 ldr x2,={align(memory_end,16):#x}
zero_loop:
 stp xzr,xzr,[x0],#16
 subs x2,x2,#16
 b.ne zero_loop
 // The raw Android image is loaded at 0x80080000 after its ELF/Mach-O
 // section headers are stripped. Anchor to the executing _start and add a
 // link-time delta so __text section prefixes cannot skew the source pointer.
 adr x19,_start
 ldr x9,=kernel_data-_start
 add x19,x19,x9
 adr x20,segment_table
 mov x21,#{len(segments)}
segment_loop:
 ldr x0,[x20],#8
 ldr x1,[x20],#8
 ldr x2,[x20],#8
 ldr x3,[x20],#8
 mov x6,x1
 mov x5,x3
 mov x7,x2
 add x0,x19,x0
 bl copy_bytes
 add x6,x6,x7
 mov x0,x6
 mov x2,x5
 bl zero_segment_tail
 mov x0,x6
 mov x2,x5
 bl clean_segment_tail
 subs x21,x21,#1
 b.ne segment_loop
 adr x0,args_data
 ldr x1,={args_pa:#x}
 mov x2,#{args_len}
 bl copy_bytes
 // Reserved diagnostic bytes in the remainder of the boot-args page.
 ldr x0,={args_pa+0x800:#x}
 mov x2,#32
zero_diagnostic:
 stp xzr,xzr,[x0],#16
 subs x2,x2,#1
 b.ne zero_diagnostic
 // R260: publish the copied kernel entry and its first two instructions in
 // the reserved boot-args tail. XNU start_first_cpu overwrites +0xa00 with
 // R84FS00, so this distinguishes shim copy completion from XNU entry.
 ldr x10,={args_pa+0xa00:#x}
 ldr x11,={int.from_bytes(b'R260CPY0','little'):#x}
 str x11,[x10,#8]
 ldr x11,={entry:#x}
 str x11,[x10]
 ldr x12,[x11]
 ldr x13,[x11,#8]
 str x12,[x10,#16]
 str x13,[x10,#24]
 dsb sy
 dc civac,x10
 dsb sy
 adr x0,tree_data
 ldr x1,={tree_pa:#x}
 ldr x2,={tree_len:#x}
 bl copy_bytes
{rootfs_copy}
{tc_copy}
{tc_clean}
{tc_probe}
 // The firmware handoff already disabled caches, as verified by SCTLR in the register probe.
 dsb sy
 ic iallu
 dsb sy
 isb
 ldr x10,=0x859f0000
 ldr x11,={int.from_bytes(b'Y35AXNU2','little'):#x}
 str x11,[x10]
 ldr x11,={entry:#x}
 str x11,[x10,#24]
 // R260 retained carrier: boot-args memory is reused by the resident loader
 // before the matching readback probe, so keep the copy witness in the
 // report-page gap that the probe preserves (0x859f0080..0x859f009f).
 ldr x10,=0x859f0080
 ldr x11,={int.from_bytes(b'R260CPY0','little'):#x}
 str x11,[x10]
 ldr x11,={entry:#x}
 str x11,[x10,#8]
 ldr x12,[x11]
 ldr x13,[x11,#8]
 str x12,[x10,#16]
 str x13,[x10,#24]
 dsb sy
 ldr x0,={args_pa:#x}
 ldr x1,={entry:#x}
 br x1
copy_bytes:
 cmp x2,#16
 b.lo copy_tail
copy_words:
 ldp x3,x4,[x0],#16
 stp x3,x4,[x1],#16
 sub x2,x2,#16
 cmp x2,#16
 b.hs copy_words
copy_tail:
 cbz x2,copy_done
copy_loop:
 ldrb w3,[x0],#1
 strb w3,[x1],#1
 subs x2,x2,#1
 b.ne copy_loop
copy_done:
 ret
zero_segment_tail:
 cbz x2,zero_segment_done
zero_segment_loop:
 stp xzr,xzr,[x0],#16
 subs x2,x2,#16
 b.ne zero_segment_loop
zero_segment_done:
 ret
clean_segment_tail:
 cbz x2,clean_segment_done
clean_segment_loop:
 dc cvac,x0
 add x0,x0,#64
 subs x2,x2,#64
 b.ne clean_segment_loop
 dsb sy
clean_segment_done:
 ret
halt:
 wfe
 b halt
 .ltorg
 .balign 8
segment_table:
{segment_table}
 .balign 16
args_data:
 .incbin "boot-args.bin"
 .balign 16
tree_data:
 .incbin "{tree_name}"
{tc_data}
 .balign 16
kernel_data:
 .incbin "{kernel_data_name}"
image_end:
'''

def _dt_sanity(dt):
    # copy_dtb source truth: dev_tree_validate requires a QCDT table whose
    # matched entry holds an FDT inside the domain (docs/board/boot3-container-layout.md §3).
    if len(dt)<12 or dt[:4]!=b'QCDT':raise ValueError('dt domain must be a QCDT table (bare FDT fails copy_dtb)')
    version,count=struct.unpack_from('<II',dt,4)
    if version!=3 or not 0<count<=4096:raise ValueError('unsupported QCDT table version/count')
    hdr=align(12+count*40,PAGE)
    if hdr>align(len(dt),PAGE):raise ValueError('QCDT header exceeds its page-rounded domain')
    for i in range(count):
        fields=list(struct.unpack_from('<10I',dt,12+i*40))
        if fields[:3]!=[206,8,23]:continue
        offset,size=fields[8:10]
        if size<40 or offset<hdr or offset+size>len(dt):raise ValueError('QCDT entry outside table')
        if dt[offset:offset+4]!=b'\xd0\x0d\xfe\xed':raise ValueError('QCDT entry is not an FDT')
    return

def android_container(kernel,dt,second=b'',ramdisk=b'\0'):
    if len(kernel)<64 or kernel[56:60]!=b'ARMd':raise ValueError('Expected compiled AArch64 Linux-Image header')
    # Keep code/data below the actually observed 0x83200000 continuous-splash buffer.
    if LOAD+len(kernel)>0x83200000:raise ValueError('Image overlaps measured continuous-splash framebuffer')
    if len(kernel)>PIN_KERNEL_MAX:raise ValueError('kernel domain exceeds the aboot.c:412 fork-pin budget')
    if len(ramdisk)!=1:raise ValueError('ramdisk domain must be the 1-byte pin placeholder (ramdisk_size==1)')
    _dt_sanity(dt)
    header=bytearray(PAGE);header[:8]=b'ANDROID!'
    rk,rr,r2=align(len(kernel),PAGE),align(len(ramdisk),PAGE),align(len(second),PAGE)
    second_off=PAGE+rk+rr
    struct.pack_into('<10I',header,8,len(kernel),LOAD,len(ramdisk),0x85700000,
        len(second),SCRATCH+second_off if second else 0,0x85800000,PAGE,len(dt),0)
    command=b'y35a-native-xnu-experimental';header[64:64+len(command)]=command
    digest=hashlib.sha1()
    for data in (kernel,ramdisk,second,dt):digest.update(data);digest.update(struct.pack('<I',len(data)))
    header[576:608]=digest.digest().ljust(32,b'\0')
    image=bytes(header)+kernel+bytes(rk-len(kernel))+ramdisk+bytes(rr-len(ramdisk))+second+bytes(r2-len(second))+dt+bytes(align(len(dt),PAGE)-len(dt))
    if len(image)>256*1024*1024:raise ValueError('container exceeds the source-verified 256 MiB download budget')
    return image

def assemble_entry(source,directory,compiler,objcopy):
    (directory/'entry.S').write_text(source)
    subprocess.run([compiler,'--target=aarch64-none-elf','-nostdlib','-fuse-ld=lld','-Wl,-Ttext=0x80080000','-Wl,-e,_start','-o','entry.elf','entry.S'],cwd=directory,check=True)
    subprocess.run([objcopy,'-O','binary','entry.elf','entry.bin'],cwd=directory,check=True)
    return (directory/'entry.bin').read_bytes()

def build(args):
    image=args.kernel.read_bytes();layout=parse_macho(image)
    physical_base=physical_base_for(layout['base'],OWNED_BASE)
    owned_size=args.owned_memory_size
    validate_window(physical_base,owned_size)
    if args.external_root_uuid is not None:
        if args.ramdisk is not None:
            raise ValueError('External APFS root mode cannot include a RAMDisk')
        if args.stock_boot is None:
            raise ValueError('External APFS root mode requires the pinned stock boot image')
        if args.command_line is not None:
            raise ValueError('External APFS root mode generates its own root-selection boot arguments')
        if args.external_root_reference is None:
            raise ValueError('External APFS root mode requires a hash-bound TF root reference')
        root_reference=json.loads(args.external_root_reference.read_text())
        if root_reference.get('status')!='verified-nonbootable-tf-apfs-input':
            raise ValueError('External APFS root reference status is not verified')
        artifact=root_reference.get('artifact',{})
        if (not re.fullmatch(r'[0-9a-f]{40}',str(artifact.get('head_sha','')))
                or not str(artifact.get('run_id','')).isdecimal()
                or not isinstance(artifact.get('artifact_id'),int)
                or not re.fullmatch(r'sha256:[0-9a-f]{64}',str(artifact.get('artifact_digest','')))):
            raise ValueError('External APFS root reference does not bind a valid Actions artifact identity')
        for field in ('image_sha256','report_sha256'):
            if not re.fullmatch(r'[0-9a-f]{64}',str(root_reference.get(field,''))):
                raise ValueError(f'External APFS root reference is missing a valid {field}')
        if root_reference.get('apfs_volume_uuid')!=_canonical_apfs_uuid(args.external_root_uuid,'TF APFS root UUID'):
            raise ValueError('External APFS root UUID differs from the root reference')
        if root_reference.get('device_run_allowed') is not False or root_reference.get('bootable') is not False:
            raise ValueError('External APFS root reference cannot claim device or boot qualification')
        command_line=make_external_root_command_line(args.external_root_uuid,args.emmc_root_uuid)
    else:
        if args.emmc_root_uuid is not None or args.external_root_reference is not None:
            raise ValueError('eMMC UUID and external-root reference require external APFS root mode')
        root_reference=None
        command_line=args.command_line or RAMDISK_COMMAND_LINE
    if args.directory.exists() and any(args.directory.iterdir()):raise ValueError('Use an empty output directory')
    args.directory.mkdir(parents=True,exist_ok=True)
    memory_end=layout['end']-layout['base']
    args_pa=align(physical_base+memory_end,16384);tree_pa=args_pa+4096
    import os
    seed=os.urandom(64)
    # The rootfs rides the second domain (SCRATCH), not the kernel domain:
    # boot2 proved a 43MB incbin pushes kernel_size past the fork-pin budget.
    rootfs=None
    if args.ramdisk is not None:
        data=args.ramdisk.read_bytes()
        if not data:raise ValueError('Empty memory sidecar: RAMDisk')
        data+=bytes(align(len(data),4096)-len(data))
        (args.directory/'ramdisk-second.bin').write_bytes(data)
        rootfs=dict(name='RAMDisk',bytes=data,scratch=None,physical=None,size=len(data),
                    sha256=hashlib.sha256(data).hexdigest())
    trustcache=None
    if args.trust_cache is not None:
        tc=args.trust_cache.read_bytes()
        if not tc:raise ValueError('Empty memory sidecar: TrustCache')
        if tc.startswith(b'\x30') and b'IM4P' in tc[:32]:
            idx = tc.find(b'\x01\x00\x00\x00')
            if idx != -1:
                tc = tc[idx:]
        (args.directory/'trustcache.bin').write_bytes(tc)
        trustcache=dict(name='TrustCache',bytes=tc,physical=None,size=len(tc),
                        sha256=hashlib.sha256(tc).hexdigest(),filename='trustcache.bin')
    # Physical layout: args page, tree page, then sidecars page-aligned.
    cursor=align(tree_pa+16384,16384)
    placements=[]
    if rootfs:rootfs['physical']=cursor;placements.append(rootfs);cursor=align(cursor+rootfs['size'],16384)
    if trustcache:trustcache['physical']=cursor;placements.append(trustcache);cursor=align(cursor+trustcache['size'],16384)
    tree=make_tree(random_seed=seed,physical_base=physical_base,memory_size=owned_size,
        warm_reset_prepared=args.warm_reset_prepared,
        memory_map={p['name']:(p['physical'],p['size']) for p in placements})
    if len(tree)>16384:raise ValueError('Device tree exceeds its reserved allocation')
    top=cursor if placements else align(tree_pa+len(tree),16384)
    bootargs=make_boot_args(virtual_base=layout['base'],physical_base=physical_base,memory_size=owned_size,
        top=top,tree_physical=tree_pa,tree_size=len(tree),command_line=command_line)
    (args.directory/'kernel-packed.macho').write_bytes(image)
    (args.directory/'boot-args.bin').write_bytes(bootargs)
    (args.directory/'board.adt').write_bytes(tree)
    entry=physical_base+layout['entry']-layout['base']
    segments=[(s['offset'],physical_base+s['address']-layout['base'],s['file_size'],s['size']) for s in layout['segments']]
    tc_out=dict(physical=trustcache['physical'],size=trustcache['size'],name='trustcache.bin') if trustcache else None
    def emit(second_off):
        root=dict(scratch=SCRATCH+second_off,physical=rootfs['physical'],size=rootfs['size']) if rootfs else None
        return generate_entry_source(segments=segments,kernel_data_name='kernel-packed.macho',
            physical_base=physical_base,memory_end=memory_end,args_pa=args_pa,args_len=len(bootargs),
            tree_pa=tree_pa,tree_len=len(tree),tree_name='board.adt',rootfs=root,trustcache=tc_out,
            entry=entry,kernel_sha256_8=hashlib.sha256(image).digest()[:8])
    # Fixed point: second_off depends on len(entry.bin), whose literal widths
    # are value-independent (ldr =literal pool), so this converges.
    second_off=0;entry_bin=b''
    for _ in range(4):
        entry_bin=assemble_entry(emit(second_off),args.directory,args.compiler,args.objcopy)
        nxt=second_off_for(len(entry_bin)) if rootfs else 0
        if nxt==second_off:break
        second_off=nxt
    if rootfs and second_off_for(len(entry_bin))!=second_off:
        raise ValueError('second_off fixed point did not converge')
    if rootfs:rootfs['scratch']=SCRATCH+second_off
    if args.qcdt is not None:
        qcdt_input=args.qcdt.read_bytes()
        dt=select_device_dt(qcdt_input)
        dt_source={'source_type':'derived-qcdt','path':args.qcdt.name,
                   'input_sha256':hashlib.sha256(qcdt_input).hexdigest()}
    else:
        stock=args.stock_boot.read_bytes()
        if stock[:8]!=b'ANDROID!':raise ValueError('Invalid stock boot reference')
        values=struct.unpack_from('<10I',stock,8);page=values[7]
        dt_offset=page+align(values[0],page)+align(values[2],page)+align(values[4],page)
        qcdt_input=stock[dt_offset:dt_offset+values[8]]
        dt=select_device_dt(qcdt_input)
        dt_source={'source_type':'stock-boot-qcdt','path':args.stock_boot.name,
                   'input_sha256':hashlib.sha256(stock).hexdigest()}
    dt_source['selected_qcdt_sha256']=hashlib.sha256(dt).hexdigest()
    packed=android_container(entry_bin,dt,second=rootfs['bytes'] if rootfs else b'',ramdisk=b'\0')
    output=args.directory/'experimental-native-xnu.img';output.write_bytes(packed)
    if rootfs or root_reference:(args.directory/'boot3.img').write_bytes(packed)
    sidecars=[dict(name=p['name'],physical=hex(p['physical']),size=p['size'],sha256=p['sha256'],
                   scratch=(hex(p['scratch']) if p.get('scratch') else None)) for p in placements]
    record={'kernel_sha256':hashlib.sha256(image).hexdigest(),'boot_image_sha256':hashlib.sha256(packed).hexdigest(),
        'kernel_physical_base':hex(physical_base),'kernel_entry_physical':hex(entry),'args_physical':hex(args_pa),
        'tree_physical':hex(tree_pa),'top_of_kernel_data':hex(top),'owned_memory':hex(owned_size),
        'memory_profile':('max-contiguous-measured' if owned_size > DEFAULT_OWNED_SIZE else 'restricted-diagnostic'),
        'memory_range':{'base':hex(physical_base),'end':hex(physical_base+owned_size),
                        'measured_source':(
                            'evidence/y35a-20261102/PROGRESS.md:11 recorded /proc/iomem windows; '
                            'evidence/y35a-20261102/lk2nd-runtime.dtb '
                            'sha256=36555c5e66b4a09cd38506706b0a301c2c8b8d6b883de51c51b89971825e9709 '
                            '(staged prior-loader 2GiB identity only); '
                            'docs/board/y35a-facts.md:19-21'
                        ),
                        'multi_bank_supported':False,
                        'multi_bank_note':'XNU-4903 arm_vm_init consumes one boot_args physBase/memSize span; lower banks are not represented as contiguous memory'},
        'early_fault_record_physical':hex(args_pa+0x800),'early_fault_record_bytes':384,
        'diagnostic_carrier_bytes':512,
        'second_offset':hex(second_off) if rootfs else None,
        'entry_bytes':len(entry_bin),
        'boot_arguments':command_line,
        'sidecars':sidecars,'device_tree':dt_source,
        'root_selection':({
            'mode':'external-apfs-diagnostic',
            'selector':'rd=uuid',
            'tf_volume_uuid':root_reference['apfs_volume_uuid'],
            'tf_root_reference_sha256':hashlib.sha256(args.external_root_reference.read_bytes()).hexdigest(),
            'emmc_fallback':({'selector':'emmc-boot-uuid','volume_uuid':_canonical_apfs_uuid(args.emmc_root_uuid,'eMMC APFS root UUID'),'status':'configured-unverified'} if args.emmc_root_uuid is not None else {'selector':'emmc-boot-uuid','volume_uuid':None,'status':'unavailable'}),
            'runtime_selection_status':'unverified',
        } if root_reference else {'mode':'ramdisk-diagnostic','selector':'rd=md0','runtime_selection_status':'unverified'}),
        'external_root_reference':root_reference,
        'warm_reset_prepared_required':args.warm_reset_prepared,
        'status':'offline-built experimental image; not device-boot validated'}
    component_names = ['entry.S', 'entry.bin', 'boot-args.bin', 'board.adt', 'kernel-packed.macho']
    if rootfs:
        component_names.append('ramdisk-second.bin')
    if trustcache:
        component_names.append('trustcache.bin')
    record['package_components'] = {}
    for name in component_names:
        component = args.directory / name
        data = component.read_bytes()
        record['package_components'][name] = {
            'path': name,
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
        }
    (args.directory/'manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel',required=True,type=Path)
    dt_input=p.add_mutually_exclusive_group(required=True)
    dt_input.add_argument('--stock-boot',type=Path)
    dt_input.add_argument('--qcdt',type=Path,help='QCDT v3 input, for CI-derived board DT packaging')
    p.add_argument('--directory',required=True,type=Path);p.add_argument('--compiler',default='clang');p.add_argument('--objcopy',default='llvm-objcopy')
    p.add_argument('--command-line',default=None)
    p.add_argument('--external-root-uuid')
    p.add_argument('--emmc-root-uuid')
    p.add_argument('--external-root-reference',type=Path)
    p.add_argument('--owned-memory-size',type=lambda x:int(x,0),default=DEFAULT_OWNED_SIZE, help='Contiguous measured RAM span exposed to XNU')
    p.add_argument('--ramdisk',type=Path,help='Explicit RAM root bytes; copied into reserved owned memory')
    p.add_argument('--trust-cache',type=Path,help='Explicit boot-owner trust cache bundle for the supplied code')
    p.add_argument('--warm-reset-prepared',action='store_true',help='Requires PMIC warm-reset readback immediately before RAM boot')
    build(p.parse_args())
if __name__=='__main__':main()
