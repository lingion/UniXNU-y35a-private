# Claude and Codex Shared Log

This directory is the shared handoff point for Claude Desktop and Codex work on UniXNU Y35A. Both sessions have access to the `UniXNU-y35a` project directory. Keep decisions here so the next session can pick up the current evidence without relying on a chat summary.

```text
docs/coordination/claude-codex-sync/
|-- README.md   collaboration rules and reading order
|-- CURRENT.md  current evidence, disputed claims, and next action
|-- LONG-RUN-STATE.md  durable queue, ownership, and device boundary
`-- LOG.md      append-only dated handoffs
```

## Reading Order

At the start of a UniXNU session, read `CURRENT.md`, then `LONG-RUN-STATE.md`, then read new entries at the end of `LOG.md`. Use the evidence files linked from those documents as the source data. Update `CURRENT.md` only when new evidence changes the current state; append the evidence and decision to `LOG.md` in the same turn.

## Evidence Rules

- Label statements as directly measured, source-verified, inferred, or unresolved. Keep raw observations separate from interpretations.
- Identify every device image and probe by full SHA-256. A bootloader handoff stamp identifies the image passed by the shim; by itself, it does not prove which XNU function ran.
- Treat a readback as runtime evidence only after checking the capture chain, address translation, field width, and whether the value can also come from the loaded image or an earlier stage.
- For `full-readback`, a record `offset` is relative to raw body offset `0x00`; for `minimal-boundary`, `report_offset` is relative to raw body offset `0x10000`. Never apply the minimal base to a full-readback manifest.
- When later evidence overturns an earlier claim, preserve the old entry in `LOG.md` and mark the claim superseded in `CURRENT.md`. Do not silently carry it forward.
- Keep device actions within the current user authorization. RAM-only boot and readback do not authorize flashing, partition writes, or userdata changes.
- Do not run concurrent fastboot operations against the same phone. Record the device state immediately before and after each experiment.

## Per-Experiment Record

Before a device run, add the question, hypothesis, exact image and probe hashes, expected observation, and stop condition to `CURRENT.md` or a new dated `LOG.md` entry. Afterward record the actual command, output, raw evidence path and hash, and the narrowest conclusion the data supports. A failed transport attempt is not a kernel result.
