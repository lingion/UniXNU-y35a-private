#!/usr/bin/env python3
"""uncomplzss.py -- decompress Apple "complzss" (legacy AppleLZSS) IM4P payloads.

Proven format (iOS <= 12.x kernelcaches on K32/ARMv8, fourcc 'comp', payload
magic "complzss"):

  offset  size  field
  0x000   8     magic "complzss"
  0x008   4     adler32 of the DECOMPRESSED stream, big-endian
  0x00C   4     raw (decompressed) size, big-endian
  0x010   4     compressed-stream size, big-endian
  0x014   4     version flag, big-endian (1)
  0x018   360   zero padding (header is 0x180 = 384 bytes total)
  0x180   cmp   the LZSS stream (classic HaPuff/ring-buffer LZSS, NOT LZVN)
  0x180+cmp ... optional trailer (on iOS 9-11 A7-A9 a separate KPP Mach-O is
                appended here; on 12.x K32 this is the "extra" region)
  up to EOF zero padding

This is NOT an LZVN/bvxn stream; the Apple lzfse repo decoder cannot be used.
The actual codec is implemented by the `lzss` PyPI package (pylzss, C
extension) which pyimg4 already calls for Compression.LZSS.

Usage (end-to-end recipe, verified 2026-11-04 on iPad mini 4 12.4.1):
  python3 uncomplzss.py kernelcache.release.ipad5.im4p -o kernelcache.decompressed
Requires: python3 with pyimg4 + pylzss importable
(both present on this Mac and in container unixnu-y35a-native-20261103).
"""
import argparse
import hashlib
import json
import struct
import sys
import zlib

MAGIC = b"complzss"
HEADER_SIZE = 0x180


def find_payload(data: bytes) -> bytes:
    """Return the 'complzss' blob from either a raw stream or an IM4P.

    For IM4P we defer to pyimg4 (DER decode). Falls back to scanning for the
    magic if the input is a container we cannot parse (e.g. detached blob)."""
    if data[:8] == MAGIC:
        return data
    try:
        import pyimg4
        im4p = pyimg4.IM4P(data)
        payload = bytes(im4p.payload.data)
        # pyimg4 already splits the appended KPP region off into .extra at
        # parse time; re-attach it so the trailer logic below sees the full blob
        if getattr(im4p.payload, "extra", None):
            payload += bytes(im4p.payload.extra)
        if payload[:8] == MAGIC:
            return payload
        raise ValueError(
            f"IM4P payload fourcc={im4p.fourcc} compression="
            f"{im4p.payload.compression.name}: not a complzss stream")
    except ValueError:
        idx = data.find(MAGIC)
        if idx < 0:
            raise SystemExit("no 'complzss' magic found in input")
        return data[idx:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help=".im4p file or raw complzss blob")
    ap.add_argument("-o", "--output", required=True, help="decompressed output path")
    ap.add_argument("--extra", default=None,
                    help="optional path for the appended trailer (KPP region)")
    ap.add_argument("--json", default=None, help="write provenance JSON here")
    args = ap.parse_args()

    blob = find_payload(open(args.input, "rb").read())
    if blob[:8] != MAGIC:
        raise SystemExit("input is not a complzss stream")

    adler_hdr, raw_size, cmp_size = struct.unpack_from(">3I", blob, 0x08)
    version, = struct.unpack_from(">I", blob, 0x14)
    stream = blob[HEADER_SIZE:HEADER_SIZE + cmp_size]
    trailer = blob[HEADER_SIZE + cmp_size:]

    import lzss
    out = lzss.decompress(stream)

    got_adler = zlib.adler32(out) & 0xFFFFFFFF
    if len(out) != raw_size:
        print(f"WARNING: decoded {len(out)} bytes, header promised {raw_size}",
              file=sys.stderr)
    if got_adler != adler_hdr:
        raise SystemExit(f"FATAL: adler32 {got_adler:08x} != header {adler_hdr:08x}")

    open(args.output, "wb").write(out)
    report = {
        "input": args.input,
        "input_sha256": hashlib.sha256(blob).hexdigest(),
        "format": "complzss (Apple legacy LZSS, pylzss/lzss.decompress)",
        "adler32_of_raw": f"{got_adler:08x}",
        "adler32_match": True,
        "header": {
            "raw_size": raw_size,
            "compressed_size": cmp_size,
            "version_flag": version,
            "header_bytes": HEADER_SIZE,
        },
        "output": args.output,
        "output_sha256": hashlib.sha256(out).hexdigest(),
        "output_magic": out[:4].hex(),
        "trailer_bytes": len(trailer),
    }
    if trailer and any(trailer):
        if args.extra:
            open(args.extra, "wb").write(trailer)
            report["extra_file"] = args.extra
        print(f"note: {len(trailer)} trailer bytes (KPP region) preserved",
              file=sys.stderr)
    if args.json:
        open(args.json, "w").write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
