# R326 BATOP and BAFLAG boundaries — 2026-11-21

Two paired RAM-only experiments completed on `efff9d92` / `lk2nd-msm8916`, using `fastboot oem y35a panic` before every staged readback. No persistent writes were performed.

## BATOP000 V24

Candidate kernel SHA: `4bdd19402ffaea37fcc41ac6e47299e6adee93d033f18b19d4a7a15689d32cac`.
Candidate boot SHA: `2bc5ae4f32c64cff7b3947d8e0ab4fb05a84c4f73b794e0f9fd5d1ff1564851c`.
Probe SHA: `2a3ebd57206961cd178a451f4a668ee3a0895508746699b9b6d0fe340fcacd70`.

The candidate raw contains `BATOP000` at `0x106e0`; baseline and final are zero. Raw hashes are `d2964ad5f4df880076361c12641a8f6a43c288674f1d20ab360090a79da1f52e`, `46d56ed6b9b360ccb5453b8e506ce94f7b52a50ca753c802e621ea7eb909997e`, and `018e73d269264a9ebdcf94220e4f5915c6d1dc3b05ee1dea059b9d137b547eae`.

## BAFLAG00 V25

Candidate kernel SHA: `ab4069e8129ea386f566eb81ba5191341664bf2eb03dee3ba6e05d2d5b340404`.
Candidate boot SHA: `b4c278ff4d97cff5b8b01fc58db8ba9a28cbd21f801482829300ff31f7af1974`.
Probe SHA: `63e96c505657516cf091f68fb5229cf28f1ada008b30a3800388692a01ea9288`.

The candidate raw contains `BAFLAG00` at `0x106e0`; baseline and final are zero. Raw hashes are `5865a02f1a01205f0267d78be437f47e9455acc07aedb1596ccad1eb44b8e655`, `8d8340dcbc19bc27c01deb96cad6a84c4f90b069c01b6104f024e4fcccec349c`, and `b3da1ca731e2f8d16bc965d6a43126d99516566b90ffb10b5cc6dea89eb135c3`.

The next boundary is `ARGSLOAD` at `+0x8e0`, followed by the first post-bootargs startup call. Evidence is in the corresponding `decoded-v24.json` and `decoded-v25.json` files under the persistent run checkpoints.
