#!/usr/bin/env python3
"""Build a hash-bound Y35A launchd diagnostic RAM-boot package in CI."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import plistlib
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
import package_native

sys.path.insert(0, str(ROOT / "scripts/ci"))
from build_y35a_qcdt import build_qcdt
from build_y35a_tf_apfs_image import extract_root_tree_archive, tree_metadata_manifest, tree_sha256
from extract_ios12_package_inputs import extract_inputs
from verify_y35a_trustcache import verify_staged_root


PAGE_SIZE = 2048
SCRATCH = 0x90000000
PIN_KERNEL_MAX = 0x3180000
FIRMWARE_VOLUME = "PeaceG16G102.J81J82J85mJ86mJ87mJ96J97OS"
REQUIRED_PACKAGE_COMPONENTS = (
    "entry.bin",
    "boot-args.bin",
    "board.adt",
    "ramdisk-second.bin",
    "trustcache.bin",
)
ALLOWED_NATIVE_MANIFESTS = {
    "ci/native-build-manifest.r208.json",
    "ci/native-build-manifest.r208-fallback-v2.json",
    "ci/native-build-manifest.r208-fallback-v3.json",
}
PACKAGE_SOURCE_FILES = (
    ".github/workflows/y35a-ci-package.yml",
    ".github/workflows/unixnu-native-build.yml",
    "ci/manifests/r208-tf-sd-driver.json",
    "ci/native-build-manifest.r208.json",
    "ci/native-source-provenance.r208.json",
    "ci/native-build-manifest.r208-fallback-v2.json",
    "ci/native-source-provenance.r208-fallback-v2.json",
    "patches/xnu/native-y35a-tf-emmc-root-fallback-v2.patch",
    "scripts/ci/verify_r208_fallback_v2_source.py",
    "ci/native-build-manifest.r208-fallback-v3.json",
    "ci/native-source-provenance.r208-fallback-v3.json",
    "ci/manifests/r208-tf-emmc-root-fallback-v3-candidate.json",
    "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch",
    "scripts/ci/verify_r208_fallback_v3_source.py",
    "ci/y35a-ci-package-manifest.json",
    "ci/manifests/r208-tf-apfs-package-contract.json",
    "scripts/ci/build_y35a_ci_package.py",
    "scripts/ci/build_y35a_tf_apfs_image.py",
    "scripts/ci/build_y35a_qcdt.py",
    "scripts/ci/extract_ios12_package_inputs.py",
    "scripts/ci/patch_xnu_host_tools.py",
    "scripts/ci/prepare_native_inputs.py",
    "scripts/ci/run_native_build.py",
    "scripts/ci/verify_y35a_trustcache.py",
    "scripts/build-xnu-4903-native.py",
    "scripts/stage-ios12-root.py",
    "scripts/unixnu/ipsw.py",
    "scripts/y35a/boot_layout.py",
    "scripts/y35a/make_adt.py",
    "scripts/y35a/package_native.py",
    "scripts/y35a/verify_r208_tf_apfs_package_contract.py",
    "scripts/unixnu/devicetree.py",
    "scripts/unixnu/udif.py",
    "scripts/unixnu/util.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def version_line(executable: Path) -> str:
    result = subprocess.run(
        [str(executable), "--version"], check=False, capture_output=True, text=True,
    )
    output = result.stdout or result.stderr
    if result.returncode:
        raise ValueError(
            f"tool version probe failed ({result.returncode}): {executable}: "
            f"{output.strip() or 'no diagnostic output'}")
    return output.splitlines()[0] if output else "version output unavailable"


def validate_package_toolchain(
    manifest_path: Path,
    config: dict,
    *,
    compiler: Path,
    linker: Path,
    objcopy: Path,
) -> dict:
    manifest = load_json(manifest_path.resolve(strict=True))
    ndk = manifest.get("android_ndk", {})
    expected_revision = config.get("toolchain", {}).get("android_ndk_revision")
    if not expected_revision or ndk.get("revision") != expected_revision:
        raise ValueError("package toolchain Android NDK revision does not match the package manifest")
    ndk_root = Path(ndk.get("root", "")).resolve(strict=True)
    host_tag = ndk.get("host_tag")
    if host_tag not in {"darwin-x86_64", "darwin-arm64"}:
        raise ValueError("package toolchain has an unsupported Android NDK host prebuilt")
    if ndk_root.name != expected_revision or ndk_root.parent.name != "ndk":
        raise ValueError("Android NDK root does not identify the pinned revision")
    tools = manifest.get("tools", {})
    actual_paths = {"clang": compiler, "ld.lld": linker, "llvm-objcopy": objcopy}
    resolved = {}
    for name, expected_path in actual_paths.items():
        record = tools.get(name, {})
        path = expected_path.expanduser().absolute()
        recorded_path = Path(record.get("path", "")).expanduser().absolute()
        if path != recorded_path:
            raise ValueError(f"package toolchain path mismatch for {name}")
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"package tool is not executable: {name}")
        actual_sha = sha256(path)
        if actual_sha != record.get("sha256"):
            raise ValueError(f"package tool SHA-256 mismatch: {name}")
        actual_version = version_line(path)
        if actual_version != record.get("version"):
            raise ValueError(f"package tool version mismatch: {name}")
        resolved_path = path.resolve(strict=True)
        if name != "clang" and resolved_path.relative_to(ndk_root).parts[:4] != (
                "toolchains", "llvm", "prebuilt", host_tag):
            raise ValueError(f"package tool is outside pinned NDK host tools: {name}")
        resolved[name] = {"path": str(path), "sha256": actual_sha, "version": actual_version}
    return {
        "manifest_sha256": sha256(manifest_path),
        "android_ndk_revision": expected_revision,
        "android_ndk_root": str(ndk_root),
        "android_ndk_host_tag": host_tag,
        "tools": resolved,
    }


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def validate_native_artifact(
    directory: Path,
    run_id: str,
    head_sha: str,
    native_manifest_path: Path,
) -> tuple[Path, dict, dict]:
    artifact_path = directory / "kernel-artifact.json"
    provenance_path = directory / "build-provenance.json"
    plan_path = directory / "native-build-plan.json"
    artifact = load_json(artifact_path)
    provenance = load_json(provenance_path)
    plan = load_json(plan_path)
    native_manifest_path = native_manifest_path.resolve(strict=True)
    native_manifest = load_json(native_manifest_path)

    if artifact.get("schema") != 2 or artifact.get("status") != "success":
        raise ValueError("native kernel artifact manifest is not a successful schema-2 artifact")
    if str(artifact.get("run_id")) != run_id:
        raise ValueError("kernel artifact run ID does not match the selected Actions run")
    if artifact.get("head_sha") != head_sha:
        raise ValueError("kernel artifact commit does not match the selected Actions run")
    if artifact.get("build_provenance_path") != provenance_path.name:
        raise ValueError("kernel artifact does not name the expected build provenance file")
    if artifact.get("native_build_plan_path") != plan_path.name:
        raise ValueError("kernel artifact does not name the expected native build plan")
    plan_hash = sha256(plan_path)
    if artifact.get("native_build_plan_sha256") != plan_hash:
        raise ValueError("native build plan SHA-256 does not match kernel-artifact.json")
    expected_manifest_hash = sha256(native_manifest_path)
    if (plan.get("ok") is not True
            or plan.get("manifest_sha256") != expected_manifest_hash
            or Path(plan.get("manifest", "")).name != native_manifest_path.name):
        raise ValueError("native build plan does not bind the package's R208 build manifest")

    source_identity = provenance.get("source_identity", {})
    if source_identity.get("commit") != native_manifest.get("source_ref"):
        raise ValueError("native provenance XNU commit does not match the R208 build manifest")
    inputs = provenance.get("inputs", {})
    expected_patches = [
        (Path(item["path"]).name, item["sha256"])
        for item in native_manifest.get("patches", [])
    ]
    actual_patches = [
        (Path(item.get("path", "")).name, item.get("sha256"))
        for item in inputs.get("source_diff", [])
    ]
    if actual_patches != expected_patches:
        raise ValueError("native provenance patches do not match the ordered R208 build manifest")
    source_provenance_ref = Path(native_manifest["source_provenance"])
    source_provenance_path = (
        source_provenance_ref if source_provenance_ref.is_absolute()
        else ROOT / source_provenance_ref
    ).resolve(strict=True)
    if inputs.get("source_provenance", {}).get("sha256") != sha256(source_provenance_path):
        raise ValueError("native provenance source contract does not match the R208 build manifest")
    driver_artifact = native_manifest.get("driver_artifact", {})
    driver_archives = inputs.get("driver_archives", [])
    if (len(driver_archives) != 1
            or Path(driver_archives[0].get("path", "")).name != driver_artifact.get("archive")
            or driver_archives[0].get("sha256") != driver_artifact.get("sha256")):
        raise ValueError("native provenance driver archive does not match the R208 build manifest")
    if provenance.get("driver_integration", {}).get("status") != "passed":
        raise ValueError("native provenance does not confirm the R208 driver integration")

    kernel_name = artifact.get("artifact_path")
    if not isinstance(kernel_name, str):
        raise ValueError("kernel artifact manifest is missing artifact_path")
    relative_kernel_path = Path(kernel_name)
    if relative_kernel_path.is_absolute() or ".." in relative_kernel_path.parts:
        raise ValueError("kernel artifact path must stay inside the downloaded artifact")
    kernel = (directory / relative_kernel_path).resolve(strict=True)
    try:
        kernel.relative_to(directory.resolve(strict=True))
    except ValueError as error:
        raise ValueError("kernel artifact path escapes the downloaded artifact") from error
    if not kernel.is_file():
        raise ValueError("kernel artifact directory has no kernel payload")

    kernel_sha256 = sha256(kernel)
    kernel_bytes = kernel.stat().st_size
    if kernel_sha256 != artifact.get("kernel_sha256"):
        raise ValueError("kernel payload SHA-256 does not match kernel-artifact.json")
    if kernel_bytes != artifact.get("kernel_size"):
        raise ValueError("kernel payload size does not match kernel-artifact.json")

    provenance_hash = sha256(provenance_path)
    if artifact.get("build_provenance_sha256") != provenance_hash:
        raise ValueError("build provenance SHA-256 does not match kernel-artifact.json")
    if provenance.get("status") != "complete":
        raise ValueError("native build provenance is not complete")
    verification = provenance.get("kernel_static_verification", {})
    if verification.get("status") != "passed":
        raise ValueError("native kernel static verification did not pass")
    if artifact.get("kernel_static_verification") != verification:
        raise ValueError("kernel artifact manifest does not match static verification provenance")
    provenance_kernel = provenance.get("kernel_artifact", {})
    if (provenance_kernel.get("sha256") != kernel_sha256
            or provenance_kernel.get("bytes") != kernel_bytes):
        raise ValueError("build provenance does not bind the downloaded kernel")

    binding = {
        "run_id": run_id,
        "head_sha": head_sha,
        "artifact_manifest_sha256": sha256(artifact_path),
        "provenance_sha256": provenance_hash,
        "native_build_plan_sha256": plan_hash,
        "native_build_manifest_sha256": expected_manifest_hash,
        "kernel_path": kernel.name,
        "kernel_sha256": kernel_sha256,
        "kernel_bytes": kernel_bytes,
    }
    return kernel, binding, provenance


def resolve_native_manifest(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(ROOT).as_posix()
    except ValueError as error:
        raise ValueError("native build manifest must be inside the checked-out repository") from error
    if relative not in ALLOWED_NATIVE_MANIFESTS:
        raise ValueError(f"unsupported native build manifest: {relative}")
    return resolved


def validate_native_artifact_api_binding(artifact_id: str, artifact_digest: str) -> dict:
    if not re.fullmatch(r"[0-9]+", str(artifact_id)):
        raise ValueError("native artifact ID must be a decimal Actions artifact ID")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest):
        raise ValueError("native artifact digest must be an exact sha256:<64 lowercase hex> value")
    return {"id": int(artifact_id), "digest": artifact_digest}


def attached_device(output: bytes) -> str:
    result = plistlib.loads(output)
    entities = result.get("system-entities", [])
    for entity in entities:
        value = entity.get("dev-entry")
        if isinstance(value, str) and value.startswith("/dev/"):
            return value
    raise RuntimeError("hdiutil attach did not return a device node")


def find_volume_device(value, volume_name: str) -> str | None:
    if isinstance(value, dict):
        name = value.get("Name") or value.get("VolumeName")
        identifier = value.get("DeviceIdentifier") or value.get("APFSVolumeDisk")
        if name == volume_name and isinstance(identifier, str):
            return identifier.removeprefix("/dev/")
        for child in value.values():
            found = find_volume_device(child, volume_name)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_volume_device(child, volume_name)
            if found:
                return found
    return None


@contextmanager
def mounted_firmware(system_dmg: Path, ramdisk_image: Path, work: Path):
    system_mount = work / "system-root"
    ramdisk_mount = work / "apple-ramdisk-root"
    system_mount.mkdir()
    ramdisk_mount.mkdir()
    system_device = None
    ramdisk_device = None
    system_mounted = False
    ramdisk_mounted = False
    try:
        attached = subprocess.run(
            ["hdiutil", "attach", "-readonly", "-nobrowse", "-nomount", "-plist",
             str(system_dmg)], check=True, capture_output=True,
        )
        system_device = attached_device(attached.stdout)
        apfs = subprocess.run(
            ["diskutil", "apfs", "list", "-plist"], check=True, capture_output=True,
        )
        volume = find_volume_device(plistlib.loads(apfs.stdout), FIRMWARE_VOLUME)
        if volume is None:
            raise RuntimeError(f"APFS volume not found: {FIRMWARE_VOLUME}")
        subprocess.run(
            ["mount_apfs", "-o", "rdonly", f"/dev/{volume}", str(system_mount)],
            check=True,
        )
        system_mounted = True

        attached = subprocess.run(
            ["hdiutil", "attach", "-readonly", "-nobrowse", "-nomount",
             "-imagekey", "diskimage-class=CRawDiskImage", "-plist", str(ramdisk_image)],
            check=True, capture_output=True,
        )
        ramdisk_device = attached_device(attached.stdout)
        subprocess.run(
            ["mount_hfs", "-o", "rdonly", ramdisk_device, str(ramdisk_mount)],
            check=True,
        )
        ramdisk_mounted = True
        yield system_mount, ramdisk_mount
    finally:
        if ramdisk_mounted:
            subprocess.run(["umount", str(ramdisk_mount)], check=False)
        if ramdisk_device:
            subprocess.run(["hdiutil", "detach", "-quiet", ramdisk_device], check=False)
        if system_mounted:
            subprocess.run(["umount", str(system_mount)], check=False)
        if system_device:
            subprocess.run(["hdiutil", "detach", "-quiet", system_device], check=False)


def verify_package_components(directory: Path, manifest: dict) -> dict:
    components = manifest.get("package_components")
    if not isinstance(components, dict):
        raise ValueError("package manifest is missing package component bindings")
    missing = sorted(set(REQUIRED_PACKAGE_COMPONENTS) - components.keys())
    if missing:
        raise ValueError(f"package manifest is missing required components: {missing}")

    verified = {}
    for name, binding in components.items():
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError(f"package component path must be a file name: {name}")
        if not isinstance(binding, dict) or binding.get("path") != name:
            raise ValueError(f"package component binding is missing or misnamed: {name}")
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"package component is missing: {name}")
        size = path.stat().st_size
        digest = sha256(path)
        if size != binding.get("bytes") or digest != binding.get("sha256"):
            raise ValueError(f"package component hash or size mismatch: {name}")
        verified[name] = {"bytes": size, "sha256": digest}
    return verified


def verify_android_container(
    image_path: Path,
    expected_qcdt_sha256: str,
    expected_entry_sha256: str,
    expected_second_sha256: str,
) -> dict:
    image = image_path.read_bytes()
    if image[:8] != b"ANDROID!":
        raise ValueError("package does not start with an Android boot header")
    if len(image) < PAGE_SIZE:
        raise ValueError("package is shorter than one Android header page")
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr, tags_addr, page_size, dt_size, _ = struct.unpack_from(
        "<10I", image, 8,
    )
    if page_size != PAGE_SIZE:
        raise ValueError(f"unexpected Android page size: {page_size}")
    if kernel_size > PIN_KERNEL_MAX:
        raise ValueError("kernel domain exceeds the verified lk2nd fork-pin budget")
    if (kernel_addr, ramdisk_size, ramdisk_addr, tags_addr) != (0x80080000, 1, 0x85700000, 0x85800000):
        raise ValueError("Android kernel/ramdisk/tags geometry differs from the Y35A boot contract")
    kernel_offset = page_size
    second_offset = kernel_offset + ((kernel_size + page_size - 1) // page_size) * page_size
    second_offset += ((ramdisk_size + page_size - 1) // page_size) * page_size
    qcdt_offset = second_offset + ((second_size + page_size - 1) // page_size) * page_size
    expected_size = qcdt_offset + ((dt_size + page_size - 1) // page_size) * page_size
    if expected_size != len(image):
        raise ValueError(f"Android header geometry expects {expected_size} bytes, found {len(image)}")
    kernel = image[kernel_offset:kernel_offset + kernel_size]
    if hashlib.sha256(kernel).hexdigest() != expected_entry_sha256:
        raise ValueError("Android kernel domain does not match the generated entry binary")
    second = image[second_offset:second_offset + second_size]
    if hashlib.sha256(second).hexdigest() != expected_second_sha256:
        raise ValueError("Android second domain does not match the generated rootfs")
    if image[kernel_offset + 56:kernel_offset + 60] != b"ARMd":
        raise ValueError("kernel domain is not an AArch64 Image handoff shim")
    if second_size == 0 or dt_size == 0:
        raise ValueError("Y35A boot package requires second-domain rootfs and QCDT")
    qcdt = image[qcdt_offset:qcdt_offset + dt_size]
    if hashlib.sha256(qcdt).hexdigest() != expected_qcdt_sha256:
        raise ValueError("embedded QCDT SHA-256 differs from the generated input")
    selected = package_native.select_device_dt(qcdt)
    entry = struct.unpack_from("<10I", selected, 12)
    if entry[:3] != (206, 8, 23):
        raise ValueError("embedded QCDT does not select the measured Y35A board tuple")
    if second_addr != SCRATCH + second_offset:
        raise ValueError("second-domain address does not match the shim copy source")
    return {
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "image_bytes": len(image),
        "kernel_bytes": kernel_size,
        "entry_sha256": expected_entry_sha256,
        "second_domain_bytes": second_size,
        "second_domain_sha256": expected_second_sha256,
        "second_domain_address": hex(second_addr),
        "qcdt_bytes": dt_size,
        "qcdt_sha256": hashlib.sha256(qcdt).hexdigest(),
        "board_tuple": list(entry[:3]),
        "static_container_checks": "passed",
    }


def verify_hfs_ramdisk(path: Path) -> dict:
    size = path.stat().st_size
    if size == 0 or size % 4096:
        raise ValueError("HFS+ RAMDisk must be non-empty and 4 KiB aligned")
    with path.open("rb") as image:
        image.seek(0x400)
        signature = image.read(2)
    if signature not in (b"H+", b"HX"):
        raise ValueError("RAMDisk does not contain an HFS+ or HFSX volume header")
    return {
        "sha256": sha256(path),
        "bytes": size,
        "volume_signature": signature.decode("ascii"),
    }


def build_metadata_preserving_root_tree_archive(root_tree: Path, archive_path: Path,
                                                 output_root_tree: Path) -> dict:
    """Create and round-trip a macOS tar carrying root-tree metadata for CI artifacts."""
    tar = shutil.which("tar")
    if not tar:
        raise RuntimeError("macOS bsdtar is required to archive root-tree metadata")
    root_tree = root_tree.resolve(strict=True)
    archive_path = archive_path.resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [tar, "--format", "pax", "--xattrs", "--fflags", "--mac-metadata",
         "--numeric-owner", "-cpf", str(archive_path),
         "-C", str(root_tree.parent), root_tree.name],
        check=True,
    )
    source_manifest = tree_metadata_manifest(root_tree)
    with tempfile.TemporaryDirectory(prefix="y35a-root-tree-archive-", dir=archive_path.parent) as temporary:
        extracted = extract_root_tree_archive(archive_path, Path(temporary))
        extracted_manifest = tree_metadata_manifest(extracted)
        if extracted_manifest["tree_sha256"] != source_manifest["tree_sha256"]:
            raise ValueError("root-tree metadata archive round-trip changed the tree hash")
        if output_root_tree.exists():
            raise ValueError(f"refusing to overwrite existing root-tree output: {output_root_tree}")
        shutil.move(str(extracted), str(output_root_tree))
    return {
        **extracted_manifest,
        "path": archive_path.name,
        "bytes": archive_path.stat().st_size,
        "sha256": sha256(archive_path),
        "entries_sha256": hashlib.sha256(
            json.dumps(extracted_manifest["entries"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "metadata": ["numeric-owner", "posix-mode", "mac-acl", "extended-attributes", "symlinks"],
        "round_trip": "passed",
    }


def build_package(args) -> dict:
    config_path = args.config.resolve(strict=True)
    config = load_json(config_path)
    package_toolchain = validate_package_toolchain(
        args.toolchain_manifest, config,
        compiler=args.compiler, linker=args.linker, objcopy=args.objcopy)
    package_scope = config.get("package_scope", {})
    expected_macho_count = package_scope.get("expected_staged_macho_count")
    if package_scope.get("require_all_staged_machos_trusted") is not True:
        raise ValueError("package manifest must require TrustCache coverage for every staged Mach-O")
    if not isinstance(expected_macho_count, int) or isinstance(expected_macho_count, bool) or expected_macho_count < 1:
        raise ValueError("package manifest has an invalid expected staged Mach-O count")
    native_manifest_path = resolve_native_manifest(args.native_manifest)
    native_artifact_api = validate_native_artifact_api_binding(
        args.native_artifact_id, args.native_artifact_digest,
    )
    kernel, native_binding, native_provenance = validate_native_artifact(
        args.native_artifact_dir.resolve(strict=True), args.native_run_id,
        args.native_head_sha, native_manifest_path,
    )
    output = args.output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise SystemExit(f"Use a new or empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.toolchain_manifest.resolve(strict=True), output / "package-toolchain-manifest.json")

    with tempfile.TemporaryDirectory(prefix="y35a-package-", dir=output.parent) as temporary:
        work = Path(temporary)
        firmware_dir = work / "firmware"
        firmware_report = extract_inputs(args.ipsw.resolve(strict=True), firmware_dir, config_path)

        qcdt_path = work / "y35a.qcdt"
        dts = ROOT / config["board"]["dts_path"]
        qcdt_report = build_qcdt(dts, args.dtc, qcdt_path, args.dtc_revision)

        root_tree = work / "ios12-root"
        with mounted_firmware(
            firmware_dir / "system.dmg", firmware_dir / "restore-ramdisk.hfsx", work,
        ) as (system_root, apple_ramdisk_root):
            subprocess.run(
                ["sudo", sys.executable, str(ROOT / "scripts/stage-ios12-root.py"),
                 "--system-root", str(system_root),
                 "--apple-ramdisk-root", str(apple_ramdisk_root),
                 "--out", str(root_tree), "--hfs-image",
                 "--trustcache", str(firmware_dir / "static-trustcache.im4p")],
                check=True,
            )

        root_work = root_tree.with_name(root_tree.name + ".work")
        subprocess.run(
            ["sudo", "chown", "-R", f"{os.getuid()}:{os.getgid()}",
             str(root_tree), str(root_work)],
            check=True,
        )
        root_closure = load_json(root_tree / "CLOSURE.json")
        entries = root_closure.get("entries", {})
        required_entries = {"sbin/launchd", "usr/lib/dyld"}
        missing_entries = sorted(required_entries - entries.keys())
        if missing_entries:
            raise ValueError(f"rootfs closure is missing required boot files: {missing_entries}")
        unresolved_gaps = [gap for gap in root_closure.get("gaps", []) if not gap.get("note")]
        if unresolved_gaps:
            raise ValueError(f"rootfs closure has unresolved dependencies: {unresolved_gaps}")

        trustcache_path = work / "combined-trustcache.bin"
        trustcache_report_path = work / "trustcache-coverage.json"
        trustcache_report = verify_staged_root(
            root_tree,
            root_closure,
            firmware_dir / "restore-trustcache.bin",
            firmware_dir / "static-trustcache.bin",
            trustcache_path,
            expected_macho_count,
        )
        trustcache_report_path.write_text(
            json.dumps(trustcache_report, indent=2, sort_keys=True) + "\n",
        )

        rootfs_path = root_work / "ramdisk-hfs.raw"
        if not rootfs_path.is_file():
            raise FileNotFoundError("root stager did not emit the HFS+ RAMDisk image")
        if not os.access(rootfs_path, os.R_OK):
            raise PermissionError("root-owned RAMDisk image is not readable by the package job")
        rootfs_report = verify_hfs_ramdisk(rootfs_path)

        package_dir = work / "package"
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/y35a/package_native.py"),
             "--kernel", str(kernel), "--qcdt", str(qcdt_path),
             "--directory", str(package_dir), "--ramdisk", str(rootfs_path),
             "--trust-cache", str(trustcache_path),
             "--compiler", str(args.compiler), "--objcopy", str(args.objcopy)],
            check=True,
        )
        image_path = package_dir / "boot3.img"
        package_manifest_path = package_dir / "manifest.json"
        package_manifest = load_json(package_manifest_path)
        components = verify_package_components(package_dir, package_manifest)
        container = verify_android_container(
            image_path,
            qcdt_report["qcdt_sha256"],
            components["entry.bin"]["sha256"],
            components["ramdisk-second.bin"]["sha256"],
        )
        if package_manifest.get("kernel_sha256") != native_binding["kernel_sha256"]:
            raise ValueError("package manifest does not bind the native kernel")
        if package_manifest.get("boot_image_sha256") != container["image_sha256"]:
            raise ValueError("package manifest does not bind boot3.img")

        shutil.copy2(kernel, output / "kernel.macho")
        shutil.copy2(
            args.native_artifact_dir / "kernel-artifact.json",
            output / "native-kernel-artifact.json",
        )
        shutil.copy2(
            args.native_artifact_dir / "build-provenance.json",
            output / "native-build-provenance.json",
        )
        shutil.copy2(
            args.native_artifact_dir / "native-build-plan.json",
            output / "native-build-plan.json",
        )
        shutil.copy2(qcdt_path, output / "y35a.qcdt")
        shutil.copy2(qcdt_path.with_suffix(qcdt_path.suffix + ".json"), output / "y35a.qcdt.json")
        shutil.copy2(firmware_dir / "firmware-inputs.json", output / "firmware-inputs.json")
        shutil.copy2(root_tree / "CLOSURE.json", output / "rootfs-closure.json")
        root_tree_archive = build_metadata_preserving_root_tree_archive(
            root_tree, output / "root-tree.tar", output / "root-tree",
        )
        shutil.copy2(rootfs_path, output / "ramdisk-hfs.raw")
        shutil.copy2(firmware_dir / "restore-trustcache.im4p", output / "restore-trustcache.im4p")
        shutil.copy2(firmware_dir / "restore-trustcache.bin", output / "restore-trustcache.bin")
        shutil.copy2(firmware_dir / "static-trustcache.im4p", output / "static-trustcache.im4p")
        shutil.copy2(firmware_dir / "static-trustcache.bin", output / "static-trustcache.bin")
        shutil.copy2(trustcache_path, output / "combined-trustcache.bin")
        shutil.copy2(trustcache_report_path, output / "trustcache-coverage.json")
        shutil.copy2(image_path, output / "boot3.img")
        shutil.copy2(package_manifest_path, output / "package-manifest.json")
        for name in package_manifest["package_components"]:
            shutil.copy2(package_dir / name, output / name)
        copied_components = verify_package_components(output, package_manifest)
        if copied_components != components:
            raise ValueError("copied package components differ from the validated build directory")
        if sha256(output / "boot3.img") != container["image_sha256"]:
            raise ValueError("copied boot3.img differs from the validated Android container")
        components = copied_components

        root_tree_metadata = {
            "schema_version": 1,
            "archive_path": root_tree_archive["path"],
            "archive_bytes": root_tree_archive["bytes"],
            "archive_sha256": root_tree_archive["sha256"],
            "tree_sha256": root_tree_archive["tree_sha256"],
            "entries_sha256": root_tree_archive["entries_sha256"],
            "entries": root_tree_archive["entries"],
            "metadata": root_tree_archive["metadata"],
            "round_trip": root_tree_archive["round_trip"],
        }
        (output / "root-tree.metadata.json").write_text(
            json.dumps(root_tree_metadata, indent=2, sort_keys=True) + "\n",
        )
        files = {}
        for path in sorted(output.iterdir()):
            if path.is_file():
                record = {"bytes": path.stat().st_size, "sha256": sha256(path)}
                if path.name == "root-tree.metadata.json":
                    record["entries_sha256"] = root_tree_archive["entries_sha256"]
                files[path.name] = record
        report = {
            "schema_version": 1,
            "status": "offline-package-complete",
            "candidate_kind": config["package_scope"]["kind"],
            "native_build": native_binding,
            "native_kernel_artifact_api": {
                **native_artifact_api,
                "run_id": args.native_run_id,
                "head_sha": args.native_head_sha,
                "manifest_path": native_manifest_path.relative_to(ROOT).as_posix(),
                "manifest_sha256": sha256(native_manifest_path),
            },
            "native_build_status": native_provenance["status"],
            "firmware": firmware_report,
            "device_tree": qcdt_report,
            "package_source": {
                "commit": args.package_source_sha,
                "workflow_run_id": args.package_run_id,
                "toolchain": {
                    "macos_version": platform.mac_ver()[0],
                    "package_toolchain_manifest": package_toolchain,
                    "dtc_revision": args.dtc_revision,
                    "dtc_sha256": qcdt_report["dtc_sha256"],
                },
                "files": {
                    path: sha256(ROOT / path) for path in PACKAGE_SOURCE_FILES
                },
            },
            "rootfs": {
                "path": "ramdisk-hfs.raw",
                **rootfs_report,
                "closure_sha256": sha256(output / "rootfs-closure.json"),
                "scope": "launchd diagnostic closure",
                "tree_artifact": "root-tree.tar",
                "tree_sha256": root_tree_archive["tree_sha256"],
                "tree_archive": {
                    key: root_tree_archive[key]
                    for key in ("path", "bytes", "sha256", "tree_sha256", "entries_sha256", "entries", "metadata", "round_trip")
                },
            },
            "trust_cache": {
                "restore": firmware_report["restore_trustcache_payload"],
                "static": firmware_report["static_trustcache_payload"],
                "combined": trustcache_report,
            },
            "package": {
                "path": "boot3.img",
                "manifest_sha256": sha256(output / "package-manifest.json"),
                "components": components,
                **container,
            },
            "qualification": {
                "device_run_allowed": False,
                "runtime_qualified": False,
                "springboard_included": False,
                "touch_runtime_validated": False,
                "device_boot": "not-run",
            },
            "files": files,
        }
        provenance_path = output / "package-provenance.json"
        provenance_path.write_text(json.dumps(report, indent=2) + "\n")
        checksum_paths = [path for path in sorted(output.iterdir()) if path.is_file()
                          and path.name != "SHA256SUMS"]
        (output / "SHA256SUMS").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in checksum_paths)
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-run-id", required=True)
    parser.add_argument("--native-head-sha", required=True)
    parser.add_argument("--native-artifact-dir", required=True, type=Path)
    parser.add_argument("--native-artifact-id", required=True)
    parser.add_argument("--native-artifact-digest", required=True)
    parser.add_argument("--native-manifest", type=Path,
                        default=ROOT / "ci/native-build-manifest.r208.json")
    parser.add_argument("--package-source-sha", required=True)
    parser.add_argument("--package-run-id", required=True)
    parser.add_argument("--ipsw", required=True, type=Path)
    parser.add_argument("--dtc", required=True, type=Path)
    parser.add_argument("--dtc-revision", required=True)
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--linker", required=True, type=Path)
    parser.add_argument("--objcopy", required=True, type=Path)
    parser.add_argument("--toolchain-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "ci/y35a-ci-package-manifest.json")
    args = parser.parse_args()
    print(json.dumps(build_package(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
