# Y35A power/PMIC delivery contract gap (offline auxiliary audit)

- Timestamp: 2026-11-25T20:00:00Z
- Scope: one auxiliary item; no overlap with the active main-line `ARMRET00` / `arm_init` investigation or the review session's touch/I2C asset audit.
- Device/build/probe operations: none.
- Shared state files modified: none.
- Runtime qualification: not established by this audit.

## Impact

The current native package generator emits an XNU ADT that omits the measured PMIC and RPM-SMD regulator topology, while power-consuming board nodes use `always-on` assumptions. This is a concrete **delivery-contract gap**, not evidence that the rails are off. It means a generated image alone cannot establish that XNU owns, preserves, or can restore touch/WCNSS/GPU supplies; warm-reset continuation currently depends on the earlier loader's rail state.

## Evidence paths and SHA-256

### Authoritative state read during this cycle

| Path | SHA-256 |
|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/AGENTS.md` | `ea11e40ead1e83cb46514407413aa7934f577b38ab615ab002fa97c75296841a` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `9557bbdda44ee18067c07e189f3464050f27740e2e8d7ee762a2b91dd343ed9f` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/CURRENT.md` | `0781b3bd58351607bf2e16a45e27c654edd33f784a4346171c6ef67f500b7a9f` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LONG-RUN-STATE.md` | `fd66a2093a7d9b6f43b1fe3f44b9059360a9c6ec8b5f2a54b58111912bf993c4` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md` | `bf1f421a513b79f02e6245cbe93642a58fc15d1908dbd25543b897618bde566e` |

These hashes bind the state at the hash-computation point. Main-line edits can continue afterward; no shared state was edited by this audit.

### Power-delivery evidence

| Path | SHA-256 | Evidence used |
|---|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/touch-t02-20261109/dtb10-cache/dtb10.dts` | `4b2a7fda53ab9b4a69aa3bf9c1247feb7f767b577612914b353f076b391a8714` | Original measured-board DT: RPM-SMD regulators, touch supply phandles, PM8916/SPMI nodes |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/make_adt.py` | `d9d4d8874d6b7d8b59bc06094aa396598f672950d0dee762b2ce9ea542af244e` | Generated XNU ADT: no PMIC/battery/charger/regulator subtree; sdhc1/qup5 supply assumptions |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/package_native.py` | `c15d4fd3b3ee22e4590d656f4811179d6c9ecc8d963391c4d8b0e332720a79fe` | Stock QCDT retained for LK selection; XNU `board.adt` is separately produced by `make_tree()` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/components.toml` | `bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a` | No dedicated power/battery/charger/PMIC/fuel-gauge component |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/porting/ios12/drivers-plan.md` | `21874187559933adb72d4db95d0dfa89fcb17562c8643752f91c4e0ce89b32b1` | Documents RPM-SMD ownership and PMIC supply dependency; legacy `xnu-4570` framing requires care |

## Facts

1. **The stock board description contains the missing power topology.** In `dtb10.dts`:
   - `qcom,rpm-smd` begins at line 5644.
   - `rpm-regulator-smpa*` / `ldoa*` nodes use `qcom,rpm-smd-regulator` throughout lines 5648–6154.
   - Touch at line 6862 uses `vdd_ana-supply = <0xe3>` and line 6863 uses `vcc_i2c-supply = <0x49>`.
   - The corresponding LDOA16 and LDOA6 regulator resources are at lines 6103 and 5877.
   - `qcom,spmi@200f000` and `qcom,pm8916@0` are present at lines 7021 and 7036.
2. **The XNU-facing ADT drops that topology.** `make_adt.py:81-95` describes `qup_i2c5` and `rmi4` but uses `vdd_ana-always-on` / `vcc_i2c-always-on` presence flags. Its generated tree has no PMIC, battery, charger, fuel-gauge, SPMI, RPM, SMD/GLINK, or regulator nodes. `make_adt.py:51-54` only optionally adds a warm-reset-aware `pshold` node.
3. **Stock-DT preservation does not fill the XNU ADT gap.** `package_native.py:18-38` preserves matching stock DT/PMIC variants inside a QCDT table for LK revision selection. Separately, `package_native.py:345-354` calls `make_tree()` and writes its result as `board.adt`; it does not substitute the preserved stock FDT for XNU's tree.
4. **The component catalog has no power-management component.** `components.toml` contains no dedicated power, PMIC, battery, charger, or fuel-gauge entry.
5. **The repository plan already identifies the ownership distinction.** `drivers-plan.md:42` says the rails are RPM-SMD regulators reached through SMD to RPM/APSS, not merely the local SPMI arb. `drivers-plan.md:213-216` identifies the supply dependency and recommends GCC/GDSC work first. The plan is supporting evidence, not proof of current hardware state.

## Pending confirmation

- The exact rail states at the instant of XNU entry, including warm-reset behavior and whether LK/lk2nd leaves every assumed supply enabled.
- Whether any external RAM-disk/kext path supplies an XNU-side power controller outside the generated ADT/component catalog inspected here.
- The actual RPM-SMD/SMD transport and runtime protocol required if XNU is to own supply transitions rather than inherit loader state.
- Battery/fuel-gauge/charger hardware facts and their necessity for the immediate boot milestone; their absence from the ADT is established, but no battery driver requirement is inferred.

## Inference

- `always-on` is currently an **unverified handoff assumption**, not a regulator implementation or runtime observation.
- The gap does not by itself explain the current early-boot boundary, and it does not prove that touch, Wi-Fi, or GPU rails are presently unpowered.
- It is a packaging/qualification defect if future manifests claim those consumers are power-ready solely because their board nodes exist. The generated ADT preserves no executable ownership contract for these supplies.

## Single next-step recommendation

Add an offline package-generation gate requiring an explicit **Y35A PowerHandoff contract** before a manifest may mark touch/WCNSS/GPU power-ready: record loader-owned RPM-SMD rails, warm-reset provenance, per-consumer supply ownership, and the evidence that validates each `always-on` assumption. Keep this separate from the current `ARMRET00` investigation and do not begin device power experiments as part of this auxiliary task.
