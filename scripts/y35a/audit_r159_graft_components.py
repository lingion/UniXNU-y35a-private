#!/usr/bin/env python3
"""Audit graft component bytes allowing only declared relocations/rebases."""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kits/XnuPrelink'))
from legacy_prelink import macho, cache_metadata, backed_offset, unserialize_legacy_xml, _component_enumeration
ROOTS={'com.apple.driver.AppleMobileFileIntegrity','com.apple.kec.corecrypto','com.apple.kext.CoreTrust'}
FIELDS=(0x9c,0xb4,0xbc)
def sha(x): return hashlib.sha256(x).hexdigest()
def ranges_cover(i, n, ranges): return any(a <= i and i+n <= b for a,b in ranges)
def main():
 p=argparse.ArgumentParser(); p.add_argument('--candidate',required=True,type=Path); p.add_argument('--cache',required=True,type=Path); p.add_argument('--slide',required=True,type=lambda x:int(x,0)); p.add_argument('--output',type=Path); a=p.parse_args()
 cand=a.candidate.read_bytes(); cache=a.cache.read_bytes(); cm=macho(cand); _,cs,_,_,meta=cache_metadata(cache)
 info_seg=next(s for s in cm['segments'] if s['name']=='__PRELINK_INFO')
 cmeta=unserialize_legacy_xml(cand[info_seg['fileoff']:info_seg['fileoff']+info_seg['filesize']])
 byc={e['CFBundleIdentifier']:e for e in cmeta['_PrelinkInfoDictionary']}
 (_,_,_,_,_,_,_,modules,_,_)=_component_enumeration(cache)
 entries={e['CFBundleIdentifier']:e for e in meta['_PrelinkInfoDictionary']}
 binding_sites=[b['site'] for b in json.loads((Path(str(a.candidate)+'.json')).read_text()).get('bindings',[])]
 out={'ok':True,'runtime_qualified':False,'components':[]}
 for ident in sorted(ROOTS):
  old=entries[ident]; new=byc[ident]; oldva=old['_PrelinkExecutableLoadAddr']; newva=new['_PrelinkExecutableLoadAddr']; size=old['_PrelinkExecutableSize']
  oldoff=backed_offset(cs,oldva,size,len(cache)); newoff=backed_offset(cm['segments'],newva,size,len(cand)); ob=cache[oldoff:oldoff+size]; nb=cand[newoff:newoff+size]
  allowed=[]
  for site in binding_sites:
   rel=site-newva
   if 0 <= rel < size: allowed.append((rel,rel+8))
  old_header=backed_offset(cs,oldva,32,len(cache))
  for seg in modules[ident]['segments']:
   if seg.get('va'):
    rel=seg['command_offset']-old_header+24
    if 0 <= rel < size: allowed.append((rel,rel+8))
   for sec in seg.get('sections',[]):
    if sec.get('va'):
     rel=sec['command_offset']-old_header+32
     if 0 <= rel < size: allowed.append((rel,rel+8))
  unexpected=[]
  for i,(x,y) in enumerate(zip(ob,nb)):
   if x != y and not ranges_cover(i,1,allowed): unexpected.append(i)
  if unexpected: out['ok']=False
  kmod_old=old.get('_PrelinkKmodInfo'); rebases=[]
  if kmod_old:
   ko=backed_offset(cs,kmod_old,196,len(cache)); kn=backed_offset(cm['segments'],kmod_old+a.slide,196,len(cand))
   for field in FIELDS:
    ov,=struct.unpack_from('<Q',cache,ko+field); nv,=struct.unpack_from('<Q',cand,kn+field); expected=ov+a.slide if ov else 0
    rebases.append({'field':hex(field),'ok':nv==expected})
    if nv != expected: out['ok']=False
  out['components'].append({'id':ident,'size':size,'original_sha256':sha(ob),'candidate_sha256':sha(nb),'allowed_relocation_ranges':len(allowed),'unexpected_diff_bytes':len(unexpected),'kmod_rebases':rebases})
 if a.output: a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out,indent=2)); raise SystemExit(0 if out['ok'] else 1)
if __name__=='__main__':main()
