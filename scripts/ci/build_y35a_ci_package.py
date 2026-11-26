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
PACKAGE_SOURCE_FILES = (
    ".github/workflows/y35a-ci-package.yml",
    ".github/workflows/unixnu-native-build.yml",
    "ci/manifests/r208-tf-sd-driver.json",
    "ci/native-build-manifest.r208.json",
    "ci/native-source-provenance.r208.json",
    "ci/y35a-ci-package-manifest.json",
    "scripts/ci/build_y35a_ci_package.py",
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
        [str(executable), "--version"], check=True, capture_output=True, text=True,
    )
    output = result.stdout or result.stderr
    return output.splitlines()[0] if output else "version output unavailable"


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


def build_package(args) -> dict:
    config_path = args.config.resolve(strict=True)
    config = load_json(config_path)
    package_scope = config.get("package_scope", {})
    expected_macho_count = package_scope.get("expected_staged_macho_count")
    if package_scope.get("require_all_staged_machos_trusted") is not True:
        raise ValueError("package manifest must require TrustCache coverage for every staged Mach-O")
    if not isinstance(expected_macho_count, int) or isinstance(expected_macho_count, bool) or expected_macho_count < 1:
        raise ValueError("package manifest has an invalid expected staged Mach-O count")
    kernel, native_binding, native_provenance = validate_native_artifact(
        args.native_artifact_dir.resolve(strict=True), args.native_run_id,
        args.native_head_sha, ROOT / "ci/native-build-manifest.r208.json",
    )
    output = args.output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise SystemExit(f"Use a new or empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

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

        files = {}
        for path in sorted(output.iterdir()):
            if path.is_file():
                files[path.name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        report = {
            "schema_version": 1,
            "status": "offline-package-complete",
            "candidate_kind": config["package_scope"]["kind"],
            "native_build": native_binding,
            "native_build_status": native_provenance["status"],
            "firmware": firmware_report,
            "device_tree": qcdt_report,
            "package_source": {
                "commit": args.package_source_sha,
                "workflow_run_id": args.package_run_id,
                "toolchain": {
                    "macos_version": platform.mac_ver()[0],
                    "clang": {"path": str(args.compiler), "version": version_line(args.compiler)},
                    "lld": {"path": str(args.linker), "version": version_line(args.linker)},
                    "llvm_objcopy": {"path": str(args.objcopy), "version": version_line(args.objcopy)},
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
    parser.add_argument("--package-source-sha", required=True)
    parser.add_argument("--package-run-id", required=True)
    parser.add_argument("--ipsw", required=True, type=Path)
    parser.add_argument("--dtc", required=True, type=Path)
    parser.add_argument("--dtc-revision", required=True)
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--linker", required=True, type=Path)
    parser.add_argument("--objcopy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "ci/y35a-ci-package-manifest.json")
    args = parser.parse_args()
    print(json.dumps(build_package(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
