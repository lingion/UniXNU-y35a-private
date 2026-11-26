#!/bin/bash
# Wait for the fastboot transaction path to self-recover after the r4/reset
# e00002ed wedge, then fire EXACTLY ONE bounded oem debug readq of the live
# kernel-entry codeword (0xa026e0a0) and the two panic-carrier PAs. Clean
# getvar first, then single reads only (multiple back-to-back reads re-wedge
# the pipe, proven this round). Prints a verdict line and exits.
DEV=efff9d92
LOG=evidence/y35a-20261102/boot3-20261106/boot4-r3-20261108/livedram-readq.log
: > "$LOG"
for i in $(seq 1 40); do
  if perl -e "alarm 12; exec @ARGV or die" fastboot -s "$DEV" getvar product >/dev/null 2>&1; then
    echo "recovered at attempt $i ($(date +%T))" >> "$LOG"
    break
  fi
  echo "attempt $i still wedged ($(date +%T))" >> "$LOG"
  sleep 15
done
# one clean gap, then the decisive single reads, each bounded, 8s apart.
sleep 3
echo '--- kernel entry codeword @0xa026e0a0 (kernel file expects 0x52800062d65f03c0) ---' >> "$LOG"
perl -e 'alarm 15; exec @ARGV or die' fastboot -s "$DEV" oem debug readq 0xa026e0a0 2>&1 | tail -4 >> "$LOG"
sleep 8
echo '--- _gPanicBase PA @0xa07726a8 ---' >> "$LOG"
perl -e 'alarm 15; exec @ARGV or die' fastboot -s "$DEV" oem debug readq 0xa07726a8 2>&1 | tail -4 >> "$LOG"
sleep 8
echo '--- _debug_buf_base PA @0xa0713890 ---' >> "$LOG"
perl -e 'alarm 15; exec @ARGV or die' fastboot -s "$DEV" oem debug readq 0xa0713890 2>&1 | tail -4 >> "$LOG"
echo '--- boot-args page first u64 @0xa0b7c000 (LK-written, nonzero proves LK handoff) ---' >> "$LOG"
sleep 8
perl -e 'alarm 15; exec @ARGV or die' fastboot -s "$DEV" oem debug readq 0xa0b7c000 2>&1 | tail -4 >> "$LOG"
echo DONE >> "$LOG"
