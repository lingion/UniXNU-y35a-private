#!/usr/bin/env python3
"""Build the experimental Y35A kernel with the matching prelinked crypto ABI.

Requires the prepared source tree, toolchain and source archives. Run inside
Linux native storage; the host SSHFS workspace is unsuitable for this build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from unixnu.kernel import linux_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--diagnostic-user', action='store_true',
                        help='Include mockfs and trust cache runtime for the signed syscall test root')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(linux_env(SimpleNamespace(tree=ROOT)))
    flags = dict(XNU_BOOTSTRAP='0', XNU_SOURCE_CORECRYPTO14='1',
                 XNU_CRYPTO_BOOTSTRAP='prelinked', XNU_ARMCPU='1',
                 XNU_SOURCE_PTHREAD='1',
                 XNU_NATIVE_EARLY_FAULT='1',
                 XNU_NATIVE_CRYPTO_INSTRUCTIONS='1',
                 XNU_ARM_DT_PLATFORM='1', XNU_NATIVE_UARTDM='1',
                 XNU_NATIVE_ARCH_TIMER='1', XNU_DT_PANIC_REGION='1', JOBS='4')
    env.update(flags)
    if args.diagnostic_user:
        flags.update(XNU_SOURCE_MOCKFS='1', XNU_TRUST_CACHE_RUNTIME='1')
        env.update(flags)
    profile = tomllib.loads((ROOT / 'profiles/os/ipados-17.7.11-21H461/profile.toml').read_text())
    spec = profile['kernel']['prelink']
    cache = ROOT / 'out/ipsw/21H461/kernelcache.decompressed'
    if hashlib.sha256(cache.read_bytes()).hexdigest() != spec['kernelcache_sha256']:
        raise ValueError('Original kernelcache differs from the selected OS profile')
    (output / 'configuration.json').write_text(json.dumps(flags, indent=2)+'\n')
    with (output / 'build.log').open('x') as log:
        for driver in ('ArmDTPlatform', 'ArmCpu'):
            subprocess.run(['python3', 'scripts/build-arm-driver.py', driver], cwd=ROOT,
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        if args.diagnostic_user:
            subprocess.run(['python3', 'scripts/build-mockfs-fixture.py'], cwd=ROOT,
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['bash', 'scripts/build-xnu-4k-baseline.sh'], cwd=ROOT,
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    command = ['python3', spec['tool'], '--kernel', spec['kernel'], '--prelinked', str(cache),
               '--slide='+spec['slide'], '--early-security-init', spec['early_security_init']]
    for root in spec['roots']:
        command.extend(['--root', root])
    command.extend(['--output', str(output / 'kernel.macho')])
    subprocess.run(command, cwd=ROOT, check=True)
    print('Built', output, flush=True)


if __name__ == '__main__':
    main()
