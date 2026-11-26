#!/usr/bin/env python3
"""Check the legacy prelink metadata contract used by XNU 4903 loader."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'kits/XnuPrelink'))
from legacy_prelink import macho,unserialize_legacy_xml
ROOTS={'com.apple.driver.AppleMobileFileIntegrity','com.apple.kec.corecrypto','com.apple.kext.CoreTrust'}
def inside(addr,size,seg): return seg['va'] <= addr and addr+size <= seg['va']+seg['size']
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True,type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 d=a.candidate.read_bytes();m=macho(d);ss={s['name']:s for s in m['segments']};info=ss['__PRELINK_INFO'];meta=unserialize_legacy_xml(d[info['fileoff']:info['fileoff']+info['filesize']]);by={e['CFBundleIdentifier']:e for e in meta['_PrelinkInfoDictionary']}
 out={'ok':True,'runtime_qualified':False,'components':[]}
 for ident in sorted(ROOTS):
  e=by.get(ident); reasons=[]
  if not e: reasons.append('missing metadata entry'); out['ok']=False; out['components'].append({'id':ident,'ok':False,'reasons':reasons}); continue
  if not isinstance(e.get('_PrelinkExecutableLoadAddr'),int) or not isinstance(e.get('_PrelinkExecutableSourceAddr'),int): reasons.append('missing executable address');
  if e.get('_PrelinkExecutableLoadAddr') != e.get('_PrelinkExecutableSourceAddr'): reasons.append('load/source mismatch')
  va=e.get('_PrelinkExecutableLoadAddr',0); size=e.get('_PrelinkExecutableSize',0); k=e.get('_PrelinkKmodInfo',0)
  exec_ok=any(inside(va,size,ss[n]) for n in ('__PRELINK_TEXT','__PLK_TEXT_EXEC') if n in ss and ss[n]['size'])
  kmod_ok=bool(k) and any(inside(k,196,ss[n]) for n in ('__PRELINK_DATA','__PLK_DATA_CONST') if n in ss and ss[n]['size'])
  if not exec_ok: reasons.append('executable outside prelink text');
  if not kmod_ok: reasons.append('kmod_info outside prelink data')
  if ident=='com.apple.driver.AppleMobileFileIntegrity':
   if e.get('AppleSecurityExtension') is not True: reasons.append('AppleSecurityExtension missing')
   if e.get('OSBundleRequired')!='Root': reasons.append('OSBundleRequired is not Root')
   deps=e.get('OSBundleLibraries',{})
   for dep in ('com.apple.kec.corecrypto','com.apple.kext.CoreTrust'):
    if dep not in deps: reasons.append('missing dependency '+dep)
  ok=not reasons; out['ok'] &= ok
  out['components'].append({'id':ident,'ok':ok,'executable_in_prelink':exec_ok,'kmod_in_prelink':kmod_ok,'load_addr':hex(va),'size':size,'kmod_info':hex(k),'reasons':reasons})
 if a.output:a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out,indent=2)); raise SystemExit(0 if out['ok'] else 1)
if __name__=='__main__':main()
