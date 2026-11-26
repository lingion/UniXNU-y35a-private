#!/usr/bin/env python3
"""Validate the offline R208 TF/SD source and artifact contract."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def fail(items):
    print(json.dumps({'ok':False,'failures':items},indent=2))
    return 1

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--repo-root',type=Path,default=Path.cwd())
    ap.add_argument('--xnu-source',type=Path)
    a=ap.parse_args(); root=a.repo_root.resolve(); mpath=a.manifest.resolve()
    m=json.loads(mpath.read_text()); errors=[]
    if m.get('candidate')!='R208-tf-sd': errors.append('candidate must be R208-tf-sd')
    if m.get('device_run_allowed') is not False: errors.append('device_run_allowed must remain false')
    if m.get('status')!='offline-plan-only': errors.append('status must be offline-plan-only')
    if m.get('source',{}).get('commit')!='494ffe1c29d37ca720c37328feb83069c9641b67': errors.append('XNU source commit mismatch')
    patches=m.get('patches',[])
    for i,item in enumerate(patches):
        if item.get('order')!=i: errors.append(f'patch order mismatch at {i}')
        p=root/item['path']
        if not p.is_file(): errors.append(f'missing patch: {item.get("path")}')
        elif sha(p)!=item.get('sha256'): errors.append(f'patch hash mismatch: {item["path"]}')
    lk=m.get('lk2nd_patch',{}); lp=root/lk.get('path','')
    if not lp.is_file(): errors.append('missing lk2nd patch')
    elif sha(lp)!=lk.get('sha256'): errors.append('lk2nd patch hash mismatch')
    for path,digest in m.get('driver',{}).get('source_sha256',{}).items():
        p=root/path
        if not p.is_file(): errors.append(f'missing driver source: {path}')
        elif sha(p)!=digest: errors.append(f'driver source hash mismatch: {path}')
    for path,digest in m.get('source_files',{}).items():
        p=root/path
        if not p.is_file(): errors.append(f'missing source file: {path}')
        elif sha(p)!=digest: errors.append(f'source file hash mismatch: {path}')
    adt=m.get('adt',{})
    for key in ('script','contract_test'):
        p=root/adt[key]; expected=adt[key+'_sha256']
        if not p.is_file(): errors.append(f'missing ADT file: {adt[key]}')
        elif sha(p)!=expected: errors.append(f'ADT hash mismatch: {adt[key]}')
    if a.xnu_source:
        source=a.xnu_source.resolve()
        if not source.is_dir(): errors.append('XNU source root missing')
        else:
            r=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True,text=True)
            if r.returncode or r.stdout.strip()!=m['source']['commit']: errors.append('XNU source checkout commit mismatch')
            if patches:
                r=subprocess.run(['git','-C',str(source),'apply','--check',str(root/patches[0]['path'])],capture_output=True,text=True)
                if r.returncode: errors.append('R208 XNU personality patch apply-check failed')
    if errors: return fail(errors)
    print(json.dumps({'ok':True,'manifest_sha256':sha(mpath),'candidate':m['candidate'],'device_run_allowed':False,'driver_compile':'pending','root_mount':'unverified'},indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
