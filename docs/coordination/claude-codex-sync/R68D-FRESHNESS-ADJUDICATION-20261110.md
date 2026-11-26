# r68d readback freshness adjudication

Date: 2026-11-10. Repository HEAD when recorded: `8a95fec`.

## Direct observations

- The r68c final, r68d baseline, and r68d final captures are each 69,632 bytes. Their SHA-256 values are `68aa916dc5c3c3984c2d40100e7b24f1cf05b304cf53b724f784441347083a93`, `e71223f314d6239ba11916e737b0f013754dec936ef26ae10e483e6cfe9a84d3`, and `fa52ddf407f3bb64789039f086358bd17e2eace0e531b3598717d7c2a2dce798` respectively.
- r68d final has the r68d kernel prefix `de4bf9407c994bee`, the matching probe header, and a CNTVCT different from baseline. This establishes image/probe identity and a fresh probe read; it does not establish that XNU executed a particular marker store.
- Slot 16 is `0x3030554d4d455250` (`PREMMU00`) in all three captures. Slots 41–44 also match across all three captures. Slots 56–57 and 61–63 are zero in all three captures.
- The complete r68d baseline-to-final raw comparison has 13 differing bytes: eight kernel-stamp bytes and five CNTVCT bytes. No byte in the captured diagnostic carrier changes.
- The package source contains a 512-byte clear at `args_pa+0x800` before its `Y35AXNU2` stamp and branch. The stamp is written by the boot shim before branching to XNU, so the stamp alone is not an XNU-entry witness.

## Adjudication

The earlier claim that r68d freshly reached `PREMMU00` is not supported: the codeword was already present in the r68c generation and is identical in r68d final. The claim that the unchanged carrier proves the boot shim failed to clear it is also not supported. A successful clear followed by XNU rewriting the same fixed marker values produces the same bytes; unchanged data alone cannot distinguish that path from stale retained data. The slot-49 argument that a marker must change when text layout changes is invalid for the fixed `HDRADJ00` codeword.

Therefore r68d does not establish either side of the SCTLR boundary. The matching stamps and CNTVCT validate the probe package and probe execution, while the XNU progress markers remain freshness-ambiguous. Do not claim that the device reached the last pre-SCTLR instruction, or that the shim failed before XNU entry, from these captures.

## r68e discriminator

The r68e diagnostic patch changes the slot-16 codeword to the `R68EPRE0` value. Its matching baseline must lack that value; its final readback must carry the r68e kernel/probe identity and the new codeword before it can count as fresh evidence. The same build records the raw `_native_early_fault_address` operand, payload, `x16-x22+x23` candidate, and pre/post store markers in slots 58–62. The separate physical readback range is `0xa0b7c9d0..0xa0b7ca00` (48 bytes), with slot 63 reserved. The readback manifest records the actual `_native_early_fault_address` physical symbol and its offset inside the 16-byte pointer window; the final verifier checks that binding against the exact Mach-O and rejects aliases among independent diagnostic windows. A zero post-store marker remains a valid diagnostic result because it can show that the global store did not return. A positive r68e pre-SCTLR witness still says nothing about C entry, iOS userspace, or drivers.

No device operation was performed while making this correction. No persistent device write occurred in r68d.
