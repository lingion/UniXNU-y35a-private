"""Experimental Y35A direct-XNU handoff layout, not a booted kernel or completed port.
ABI source: drivers/DarwinBoot/DarwinBootPkg/Driver/{BootArgs.h,DarwinBoot.c}.
RAM ranges are the physical Y35A's /proc/iomem recorded in evidence/y35a-20261102.
No peripheral firmware or user data is read or written by this offline module.
"""
import struct
RAM_RANGES=((0x80000000,0x86000000),(0x8c300000,0x9ff00000),(0xa0000000,0xfffff000))
def physical_base_for(virtual_base,window_start=0xa0000000):
 if window_start%0x200000:raise ValueError('Allocation start must be 2 MiB aligned')
 return window_start+(virtual_base&0x1fffff)
def validate_window(base,size):
 if size<=0 or base%4096 or size%4096 or not any(start<=base and base+size<=end for start,end in RAM_RANGES):
  raise ValueError('Window is not wholly inside one measured non-reserved RAM range')
def make_boot_args(*,virtual_base,physical_base,memory_size,top,tree_physical,tree_size,command_line):
 validate_window(physical_base,memory_size)
 if (virtual_base-physical_base)%0x200000:raise ValueError('Bootstrap virtual and physical block offsets must match')
 if not physical_base<top<=physical_base+memory_size:raise ValueError('TopOfKernelData outside owned memory')
 if tree_size<=0 or not physical_base<=tree_physical<tree_physical+tree_size<=top:raise ValueError('Device tree outside loaded memory')
 command=command_line.encode('ascii')
 # BOOT_LINE_LENGTH=256 in the booted kernel (xnu-4903 pexpert/arm64/boot.h):
 # the field includes its NUL, so content caps at 255. A longer string would
 # lose its terminator inside the field and bleed into what arm_init reads
 # as bootFlags@0x170. The 0x480 buffer size stays: the entry shim flushes
 # it whole and the kernel never fetches the 4903-tail fields we leave zero.
 if len(command)>=256 or b'\0' in command:raise ValueError('Kernel command line exceeds BOOT_LINE_LENGTH (256 with NUL)')
 tree_virtual=virtual_base+tree_physical-physical_base
 if not 0<=tree_virtual<2**64:raise ValueError('Virtual pointer overflows')
 b=bytearray(0x180)
 struct.pack_into('<HH',b,0,2,2)
 struct.pack_into('<QQQQ',b,8,virtual_base,physical_base,memory_size,top)
 # Initial bring-up is headless; do not claim a GOP 32bpp mode for the phone's 24bpp splash.
 struct.pack_into('<QI',b,0x60,tree_virtual,tree_size)
 b[0x6c:0x6c+len(command)]=command
 struct.pack_into('<QQ',b,0x170,0,memory_size)
 return bytes(b)
def parse_macho(image):
 if len(image)<32:raise ValueError('Mach-O header truncated')
 magic,cpu,subtype,kind,count,command_bytes,flags,reserved=struct.unpack_from('<8I',image)
 if magic!=0xfeedfacf or cpu!=0x100000c or kind not in (2,0xc):raise ValueError('Expected linked plain ARM64 Mach-O')
 if command_bytes>len(image)-32 or count>command_bytes//8:raise ValueError('Load commands exceed image')
 offset=32;segments=[];entry=None
 for _ in range(count):
  if offset+8>32+command_bytes:raise ValueError('Load command header outside table')
  cmd,size=struct.unpack_from('<II',image,offset)
  if size<8 or offset+size>32+command_bytes:raise ValueError('Invalid load command length')
  if cmd==0x19:
   if size<72:raise ValueError('Segment header truncated')
   _,_,name,va,vm_size,file_offset,file_size,max_prot,prot,sections,segment_flags=struct.unpack_from('<II16sQQQQIIII',image,offset)
   if file_size>vm_size or file_offset>len(image) or file_size>len(image)-file_offset:raise ValueError('Segment file range invalid')
   if vm_size and name.split(b'\0')[0]!=b'__PAGEZERO':segments.append({'address':va,'size':vm_size,'offset':file_offset,'file_size':file_size,'protection':prot})
  elif cmd==5:
   if size!=288 or struct.unpack_from('<II',image,offset+8)!=(6,68) or entry is not None:raise ValueError('Invalid ARM64 UNIXTHREAD')
   entry=struct.unpack_from('<Q',image,offset+272)[0]
  offset+=size
 if offset!=32+command_bytes or not segments or entry is None:raise ValueError('Missing or inconsistent kernel entry')
 ordered=sorted(segments,key=lambda s:s['address'])
 if any(a['address']+a['size']>b['address'] for a,b in zip(ordered,ordered[1:])):raise ValueError('Overlapping Mach-O memory ranges')
 if entry%4 or not any(s['protection']&4 and s['address']<=entry<s['address']+s['file_size'] for s in segments):raise ValueError('Entry not in file-backed executable segment')
 base=ordered[0]['address'];end=max(s['address']+s['size'] for s in segments)
 if base%4096 or end-base>0x10000000 or end>2**64:raise ValueError('Kernel window unsupported')
 return {'base':base,'end':end,'entry':entry,'segments':ordered}
