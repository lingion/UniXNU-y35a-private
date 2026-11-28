---
name: unixnu-evidence-gate
description: Use for every UniXNU Y35A build, package, readback probe, experiment plan, device run, failure adjudication, or recovery. Enforces source provenance, patch closure, linked order, package and DT provenance, probe geometry, positive and negative controls, device permission, and state synchronization.
---

# UniXNU evidence gate

## Trigger

Use this skill before and after every candidate build, package, probe generation, run plan, device operation, or failure adjudication. Read `GOAL.md`, `LIVE-TARGET.md`, `STATE.md`, the relevant `docs/sop/LESSONS.md` entries, and the latest ledger entries first.

## Required output

Produce or update one experiment contract containing:

- run identity and parent candidate
- source root, commit, tree hash, ordered patch paths and hashes
- build provenance and kernel hash
- package, DT, boot args, entry, rootfs and trustcache hashes
- regular and clear probe hashes and record map
- positive and negative controls
- run count, time limit, nonce, stop conditions and device permission
- verdict status and raw evidence paths

## Procedure

1. Reject stale summaries when newer raw artifacts exist.
2. Verify every path, size and SHA-256.
2a. UniXNU is CI-only: the local machine may edit files and passively read source, logs and status only. Do not invoke any local project validation command, including generic `git diff --check`, tests, builds, static verifiers, linters, or package/image validation. Use GitHub Actions for these checks; any accidental local command is excluded evidence and must be recorded in LESSONS.md.
2b. For passive local repository review, execute each Git command in a separate tool invocation from an explicit read-only allowlist (`git status --short --branch`, `git rev-parse`, `git log`, `git diff --stat`, or `git diff -- <specified paths>`). Do not chain commands with `;`, `&&`, or another shell control operator. Inspect the full shell command before execution; never append `git diff --check` to status/diff output commands, and do not use an alias/wrapper whose hidden arguments can invoke a check.
Before invoking a combined shell command, inspect every subcommand for validation flags. In particular, never append `git diff --check` to an otherwise read-only status/diff command; use the Actions `Check tracked text` step instead.
For macOS root-tree metadata/content scans, retain xattr digests and file-content hashes. If a read-only root-owned source returns explicit permission denied, retry that exact xattr query or file hash using a non-interactive privileged command; do not silently treat unreadable xattrs as empty or omit content.
3. Verify source commit, clean status, tree hash and ordered patch closure. Run `git apply --check` against the exact source tree.
4. Verify build provenance, linked Mach-O and local disassembly. Check the actual instruction window, caller contract, marker codeword, owner, slot, offset, width and alignment.
5. Verify package closure. Mark DT as `stock`, `derived` or `unknown`. A derived DT must include original source, extraction range, derived output and both hashes.
6. Verify probe closure. Derive addresses from the current manifest. Reject copied addresses and old manifests.
7. Verify positive and negative controls. A negative result without a working positive control remains unverified.
8. Compute device permission from the complete contract. Never accept a runner-supplied permission override.
9. Run at most the planned number of times. On candidate/final absence, record `UNVERIFIED` or `INCONCLUSIVE`.
10. Append the lesson for every error, retry, verifier bug, schema mismatch, stale path or missed check.
11. Synchronize `LIVE-TARGET.md`, `STATE.md`, `CURRENT.md`, `LONG-RUN-STATE.md` and `LOG.md` before starting the next candidate.

## Delegation

Use one reference agent for local source reuse, one evidence agent for independent hash/raw adjudication, and one control agent for competing hypotheses when those tasks are independent. Give each agent an input path, required references, output file, stop condition and forbidden actions. Review the output before using it as a run prerequisite.
