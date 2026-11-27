#!/usr/bin/env python3
"""Apply the full fallback-v3 patch chain to the exact pinned XNU in CI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    manifest_path = args.manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text())
    source_ref = manifest.get("source_ref")

    provenance_path = (repo_root / manifest["source_provenance"]).resolve(strict=True)
    provenance_sha = sha256(provenance_path)
    if provenance_sha != manifest.get("source_provenance_sha256"):
        raise SystemExit("fallback-v3 source provenance SHA does not match its manifest")
    provenance = json.loads(provenance_path.read_text())
    if provenance.get("source", {}).get("commit") != source_ref:
        raise SystemExit("fallback-v3 provenance commit does not match source_ref")

    patches = [
        {key: item.get(key) for key in ("order", "target_tree", "path", "sha256")}
        for item in manifest.get("patches", [])
    ]
    provenance_patches = [
        {key: item.get(key) for key in ("order", "target_tree", "path", "sha256")}
        for item in provenance.get("patches", [])
    ]
    if provenance_patches != patches:
        raise SystemExit("fallback-v3 ordered patch list differs from source provenance")

    candidate = manifest.get("fallback_candidate", {})
    candidate_path = candidate.get("path")
    if candidate_path != "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch":
        raise SystemExit("fallback-v3 manifest points at an unexpected candidate patch")
    if candidate.get("sha256") != next(
            (item["sha256"] for item in patches if item["path"] == candidate_path), None):
        raise SystemExit("fallback-v3 candidate hash is not bound to the ordered patch list")
    if "--y35a-storage-fallback" not in manifest.get("build", {}).get("flags", []):
        raise SystemExit("native build manifest does not enable the fallback feature macro")

    xnu_patches: list[tuple[dict, Path]] = []
    for item in patches:
        if item["target_tree"] != "xnu-source":
            continue
        patch_path = (repo_root / item["path"]).resolve(strict=True)
        if not patch_path.is_file() or sha256(patch_path) != item["sha256"]:
            raise SystemExit(f"XNU patch SHA mismatch: {item['path']}")
        xnu_patches.append((item, patch_path))
    ordered_paths = [item["path"] for item, _ in xnu_patches]
    if ordered_paths.count(candidate_path) != 1:
        raise SystemExit("fallback-v3 patch must appear exactly once in the XNU patch chain")
    if "patches/xnu/native-y35a-tf-emmc-root-fallback-v2.patch" in ordered_paths:
        raise SystemExit("standalone fallback-v3 candidate must not apply the superseded v2 patch")

    with tempfile.TemporaryDirectory(prefix="r208-xnu-fallback-v3-") as temp_dir:
        checkout = Path(temp_dir) / "xnu"
        run(["git", "clone", "--filter=blob:none", "--no-checkout",
             "https://github.com/apple-oss-distributions/xnu.git", str(checkout)])
        run(["git", "-C", str(checkout), "fetch", "--depth=1", "origin", source_ref])
        run(["git", "-C", str(checkout), "checkout", "--detach", source_ref])
        actual_source = run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip()
        if actual_source != source_ref:
            raise SystemExit(f"XNU source identity mismatch: {actual_source} != {source_ref}")
        for item, patch_path in xnu_patches:
            run(["git", "-C", str(checkout), "apply", "--check", str(patch_path)])
            run(["git", "-C", str(checkout), "apply", str(patch_path)])

        bsd = (checkout / "bsd/kern/bsd_init.c").read_text()
        iokit = (checkout / "iokit/bsddev/IOKitBSDInit.cpp").read_text()
        setconf = bsd[bsd.index("setconf(void)"):]
        lookup = setconf.index("err = IOFindBSDRoot")
        retry = setconf.index("IOY35ARequestEmmcRootFallback()", lookup)
        legacy_default = setconf.index("setting rootdevice to 'sd0a'")
        if not lookup < retry < legacy_default:
            raise SystemExit("setconf does not retry the eMMC selector before the legacy root fallback")
        for required in (
                "y35aRootWaitAttempts >= 3",
                "return kIOReturnNotFound",
                "Y35A eMMC root failed after the single fallback attempt",
                "Y35A TF root failed without emmc-boot-uuid"):
            if required not in iokit:
                raise SystemExit(f"patched IOKitBSDInit.cpp lacks required behavior: {required}")

    print(json.dumps({
        "ok": True,
        "source_commit": source_ref,
        "source_provenance_sha256": provenance_sha,
        "ordered_xnu_patches": ordered_paths,
        "fallback_v3_patch_sha256": candidate["sha256"],
        "storage_fallback_build_flag": "--y35a-storage-fallback",
        "bounded_root_wait_attempts": 3,
        "emmc_failure_policy": "fail-closed",
        "device_run_allowed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
