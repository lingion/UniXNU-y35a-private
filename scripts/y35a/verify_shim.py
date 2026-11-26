#!/usr/bin/env python3
"""Execute the compiled phone shim on QEMU, stopping before XNU entry.

Compare every loaded segment, BSS and address gap with the input Mach-O.
This verifies the loader, not Y35A hardware or XNU boot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from boot_layout import parse_macho

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qemu-entry'))
from gdb_packets import Packets


def verify(directory):
    directory = directory.resolve()
    manifest = json.loads((directory / 'manifest.json').read_text())
    kernel = (directory / 'kernel-packed.macho').read_bytes()
    layout = parse_macho(kernel)
    physical = int(manifest['kernel_physical_base'], 16)
    entry = int(manifest['kernel_entry_physical'], 16)
    length = layout['end'] - layout['base']
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    qmp_path = directory / 'shim-qmp.sock'
    command = ['qemu-system-aarch64', '-M', 'virt,virtualization=off,secure=off',
               '-cpu', 'cortex-a53', '-accel', 'tcg', '-m', '2048', '-smp', '1',
               '-display', 'none', '-serial', 'none', '-monitor', 'none', '-nic', 'none',
               '-gdb', f'tcp:127.0.0.1:{port}', '-S',
               '-qmp', f'unix:{qmp_path},server=on,wait=off',
               '-device', f'loader,file={directory / "entry.bin"},addr=0x80080000,cpu-num=0,force-raw=on']
    with (directory / 'shim-qemu.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    connection = socket.create_connection(('127.0.0.1', port), timeout=1)
                    break
                except OSError:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError('QEMU debugger did not start')
                    time.sleep(.05)
            with connection:
                connection.settimeout(45)
                packets = Packets(connection)
                assert packets.request(f'Z1,{entry:x},4') == 'OK'
                stopped = packets.request('c')
                assert stopped.startswith(('T05', 'S05')), stopped
                registers = bytes.fromhex(packets.request('g'))
                assert int.from_bytes(registers[32*8:33*8], 'little') == entry
                assert int.from_bytes(registers[:8], 'little') == int(manifest['args_physical'], 16)
                with socket.socket(socket.AF_UNIX) as qmp:
                    qmp.settimeout(10)
                    qmp.connect(str(qmp_path))
                    stream = qmp.makefile('rwb')
                    json.loads(stream.readline())
                    def request(execute, arguments=None):
                        stream.write((json.dumps(dict(execute=execute, arguments=arguments or {}))+'\n').encode())
                        stream.flush()
                        while True:
                            reply = json.loads(stream.readline())
                            if 'event' in reply:
                                continue
                            if 'error' in reply:
                                raise RuntimeError(reply)
                            return reply
                    request('qmp_capabilities')
                    dump = directory / 'shim-loaded-memory.bin'
                    request('pmemsave', dict(val=physical, size=length, filename=str(dump)))
                actual = dump.read_bytes()
                expected = bytearray(length)
                for segment in layout['segments']:
                    start = segment['address'] - layout['base']
                    count = segment['file_size']
                    expected[start:start+count] = kernel[segment['offset']:segment['offset']+count]
                assert actual == expected, 'Shim loaded bytes differ from Mach-O segment map'
                for name, address in [('boot-args.bin', 'args_physical'), ('board.adt', 'tree_physical')]:
                    expected_data = (directory / name).read_bytes()
                    observed = b''.join(bytes.fromhex(packets.request(
                        f'm{int(manifest[address],16)+offset:x},{min(1024,len(expected_data)-offset):x}'))
                        for offset in range(0,len(expected_data),1024))
                    assert observed == expected_data, f'{name} differs after shim execution'
                result = dict(kernel_sha256=hashlib.sha256(kernel).hexdigest(),
                              compared_memory_bytes=length, segments=len(layout['segments']),
                              entry_reached=hex(entry), boot_arguments_match=True,
                              device_tree_matches=True, hardware_boot_demonstrated=False)
                for sidecar in manifest.get('sidecars',[]):
                    expected_data=(directory/sidecar['filename']).read_bytes()
                    assert len(expected_data)==sidecar['size']
                    assert hashlib.sha256(expected_data).hexdigest()==sidecar['sha256']
                    observed=b''.join(bytes.fromhex(packets.request(
                        f"m{int(sidecar['physical'],16)+offset:x},{min(1024,len(expected_data)-offset):x}"))
                        for offset in range(0,len(expected_data),1024))
                    assert observed==expected_data, 'Memory sidecar differs: '+sidecar['name']
                result['sidecars_verified']=[s['name'] for s in manifest.get('sidecars',[])]
                if 'early_fault_record_physical' in manifest:
                    observed = packets.request(f'm{int(manifest["early_fault_record_physical"],16):x},180')
                    assert observed == '00'*384, 'Reserved early-fault record was not zeroed'
                    result['early_fault_record_zeroed'] = True
                (directory / 'shim-verification.json').write_text(json.dumps(result, indent=2)+'\n')
                print(json.dumps(result, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
