#!/usr/bin/env python3
"""Static integrity gate for the R159 legacy security graft candidate.

This gate proves candidate structure and relocation-table consistency only. It
never claims loader acceptance, AMFI registration, Image4 validation, PPL
semantics, or device runtime qualification.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kits/XnuPrelink'))
from legacy_prelink import macho, unserialize_legacy_xml

ROOTS = {
    'com.apple.driver.AppleMobileFileIntegrity',
    'com.apple.kec.corecrypto',
    'com.apple.kext.CoreTrust',
}

def fail(msg):
    raise SystemExit('FAIL: ' + msg)

def inside(addr, size, segments):
    return any(s['va'] <= addr and addr + size <= s['va'] + s['size'] for s in segments if s['size'])

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate',required=True,type=Path)
    p.add_argument('--report',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    data=a.candidate.read_bytes()
    report=json.loads((a.report or Path(str(a.candidate)+'.json')).read_text())
    digest=hashlib.sha256(data).hexdigest()
    if digest != report['candidate_sha256']: fail(f'candidate sha mismatch {digest} != {report["candidate_sha256"]}')
    image=macho(data)
    nonempty=[s for s in image['segments'] if s['size']]
    seg_by_name={s['name']:s for s in image['segments']}
    for n in ('__PRELINK_TEXT','__PRELINK_INFO','__PRELINK_DATA','__PLK_TEXT_EXEC','__PLK_DATA_CONST'):
        if n not in seg_by_name or not seg_by_name[n]['size']: fail(f'missing/nonempty graft segment {n}')
    info_seg=seg_by_name['__PRELINK_INFO']
    info=unserialize_legacy_xml(data[info_seg['fileoff']:info_seg['fileoff']+info_seg['filesize']])
    entries=info.get('_PrelinkInfoDictionary')
    if not isinstance(entries,list): fail('legacy prelink dictionary missing')
    by_id={e.get('CFBundleIdentifier'):e for e in entries}
    if not ROOTS.issubset(by_id): fail('security roots missing from metadata')
    for ident in ROOTS:
        e=by_id[ident]
        va=e.get('_PrelinkExecutableLoadAddr'); src=e.get('_PrelinkExecutableSourceAddr'); size=e.get('_PrelinkExecutableSize')
        if not all(isinstance(x,int) for x in (va,src,size)): fail(f'incomplete executable metadata {ident}')
        if va != src: fail(f'load/source mismatch {ident}')
        if not inside(va,size,nonempty): fail(f'executable outside candidate segments {ident}')
    bindings=report.get('bindings',[])
    if len(bindings) != report.get('binding_count'): fail('binding_count mismatch')
    for b in bindings:
        if not inside(b['site'],8,nonempty): fail(f'binding site outside image {b["site"]:#x}')
        if not inside(b['target'],1,nonempty): fail(f'binding target outside image {b["target"]:#x}')
    table=info.get('_PrelinkLinkKASLROffsets')
    if not isinstance(table,(bytes,bytearray)) or len(table)<4: fail('KASLR table missing')
    count,=struct.unpack_from('<I',table,0)
    if count != report.get('kaslr_offset_count'): fail(f'KASLR count mismatch {count} != {report.get("kaslr_offset_count")}')
    if len(table) < 4 + count*4: fail('KASLR table truncated')
    if hashlib.sha256(table).hexdigest() != report.get('kaslr_offsets_sha256'): fail('KASLR table digest mismatch')
    result={'ok':True,'candidate_sha256':digest,'candidate_bytes':len(data),'prelink_entries':len(entries),'security_roots':sorted(ROOTS),'binding_count':len(bindings),'kaslr_offset_count':count,'missing_exports':report.get('missing_exports',{}),'collision_count':report.get('collision_count',0),'runtime_qualified':False,'scope':'static candidate integrity only'}
    if a.output: a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
