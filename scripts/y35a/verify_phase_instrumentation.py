#!/usr/bin/env python3
"""Verify that a built XNU kernel really contains the Y35A phase probes.

This is an offline gate. It never boots a device and never changes files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from boot_layout import parse_macho, physical_base_for

PHASE_MARKERS = {
    "ARMINITE": (5, 0x41524D494E495445),
    "PEINITEN": (6, 0x5045494E4954454E),
    "PEINITRT": (7, 0x5045494E49545254),
    "ARMVMINI": (8, 0x41524D564D494E49),
    "PANICINI": (9, 0x50414E4943494E49),
    "CONSOLE": (10, 0x434F4E534F4C45),
}
HANDOFF_MARKERS = {
    "PREARGS0": (22, 0x3053475241455250),
    "BAVIRT00": (23, 0x3030545249564142),
    "BAPHYS00": (24, 0x3030535948504142),
    "BAMEM000": (25, 0x3030304D454D4142),
    "BATOP000": (26, 0x303030504F544142),
    "BAFLAG00": (27, 0x303047414C464142),
    "KVACALC0": (28, 0x30434C414341564B),
    "TPIDR000": (31, 0x3030305244495054),
    "EXCADDR0": (32, 0x3052444441435845),
    "EXCSPS00": (33, 0x3030535053435845),
    "EXCSP000": (34, 0x3030305053435845),
    "INTADDR0": (35, 0x3052444441544E49),
    "INTSPS00": (36, 0x3030535053544E49),
    "INTSP000": (37, 0x3030305053544E49),
    "LRPRE000": (38, 0x303030455250524C),
    "LRPAGE00": (39, 0x3030454741504C52),
    "LROFF000": (40, 0x30303046464F4C52),
    "FPGVA00": (41, int.from_bytes(b"R68E7GV0", "little")),
    "FPBEFOR0": (43, int.from_bytes(b"R68E7BF0", "little")),
    "FPSTOR00": (44, int.from_bytes(b"R68E7ST0", "little")),
    "PUBLPR00": (61, int.from_bytes(b"R68E7PR0", "little")),
    "PUBLPS00": (62, int.from_bytes(b"R68E7PS0", "little")),
    "LRADD000": (45, 0x303030444441524C),
    "LINKADDR": (38, 0x524444414B4E494C),
    "INVPREF0": (39, 0x3046455250564E49),
    "INVONE00": (40, 0x3030454E4F564E49),
    "HDRLOAD0": (48, 0x3044414F4C524448),
    "HDRADJ00": (49, 0x30304A4441524448),
    "L1ALLOC0": (50, 0x30434F4C4C41314C),
    "PTPRE000": (41, 0x3030304552505450),
    "PTEEMPTY": (42, 0x5954504D45455450),
    "PTBASE00": (43, 0x3030455341425450),
    "PTCOUNT0": (44, 0x30544E554F435450),
    "PTSHIFT0": (45, 0x3054464948535450),
    "VPPRE000": (52, 0x3030304552505056),
    "VPCALL00": (53, 0x30304C4C41435056),
    "KVPRE000": (54, 0x303030455250564B),
    "KVCALL00": (55, 0x30304C4C4143564B),
    "ARGSLOAD": (17, 0x44414F4C53475241),
    "STACKS00": (18, 0x3030534B43415453),
    "INVALID0": (19, 0x3044494C41564E49),
    "VPMAP000": (20, 0x30303050414D5056),
    "KVAMAP00": (21, 0x303050414D41564B),
    "COMMON00": (13, 0x30304E4F4D4D4F43),
    "MAPDONE0": (14, 0x30454E4F4450414D),
    "TTBRDONE": (15, 0x454E4F4452425454),
    "PREMMU00": (16, int.from_bytes(b"R68E7PM0", "little")),
    "SCTLRRD0": (56, int.from_bytes(b"R68E7RD0", "little")),
    "ARMRET": (12, 0x30305445524D5241),
}
HANDOFF_ORDER = (
    "PREARGS0",
    "BAVIRT00",
    "BAPHYS00",
    "BAMEM000",
    "BATOP000",
    "BAFLAG00",
    "KVACALC0",
    "ARGSLOAD",
    "TPIDR000",
    "EXCADDR0",
    "EXCSPS00",
    "EXCSP000",
    "INTADDR0",
    "INTSPS00",
    "INTSP000",
    "LRPRE000",
    "LRPAGE00",
    "LROFF000",
    "FPGVA00",
    "FPBEFOR0",
    "FPSTOR00",
    "PUBLPR00",
    "PUBLPS00",
    "LRADD000",
    "LINKADDR",
    "STACKS00",
    "PTPRE000",
    "PTEEMPTY",
    "PTBASE00",
    "PTCOUNT0",
    "PTSHIFT0",
    "INVPREF0",
    "INVONE00",
    "INVALID0",
    "HDRLOAD0",
    "HDRADJ00",
    "L1ALLOC0",
    "VPPRE000",
    "VPMAP000",
    "VPCALL00",
    "KVPRE000",
    "KVAMAP00",
    "KVCALL00",
    "MAPDONE0",
    "COMMON00",
    "TTBRDONE",
    "PREMMU00",
    "SCTLRRD0",
    "ARMRET",
)
PHASE_ORDER = tuple(PHASE_MARKERS)
ENTRY_PATH_MARKERS = {
    "FIRST_CPU": (64, int.from_bytes(b"R68E7FS0", "little")),
}
ENTRY_MARKER = int.from_bytes(b"R68E7AR0", "little")
R83_ENTRY_MARKER = int.from_bytes(b"R83ENT00", "little")
R83_C_ENTRY_MARKER = int.from_bytes(b"R83CIN00", "little")
R83_FIRST_CPU_MARKER = int.from_bytes(b"R83FS00\0", "little")
R84_ENTRY_MARKER = int.from_bytes(b"R84ENT00", "little")
R84_C_ENTRY_MARKER = int.from_bytes(b"R84CIN00", "little")
R84_FIRST_CPU_MARKER = int.from_bytes(b"R84FS00\0", "little")
R84_ARM_ENTRY_PHASE = int.from_bytes(b"R84ARM00", "little")
R84_LATE_PHASE = int.from_bytes(b"R84LATE0", "little")
R84_SETTER_RETURN_MARKER = int.from_bytes(b"R84SET00", "little")
R85_LATE_RETURN_MARKER = int.from_bytes(b"R85LRET0", "little")
R85_MACHINE_START_MARKER = int.from_bytes(b"R85MSB00", "little")
R85_MACHINE_RETURN_MARKER = int.from_bytes(b"R85MACH0", "little")
R86_STARTUP_MARKERS = {
    "R86MSE00": (14, int.from_bytes(b"R86MSE00", "little")),
    "R86KBE00": (15, int.from_bytes(b"R86KBE00", "little")),
    "R86VMB00": (16, int.from_bytes(b"R86VMB00", "little")),
    "R86CSI00": (17, int.from_bytes(b"R86CSI00", "little")),
    "R86VMI00": (18, int.from_bytes(b"R86VMI00", "little")),
    "R86CON00": (19, int.from_bytes(b"R86CON00", "little")),
    "R86SCH00": (20, int.from_bytes(b"R86SCH00", "little")),
    "R86IPC00": (21, int.from_bytes(b"R86IPC00", "little")),
}
R87_STARTUP_MARKERS = {
    "R87PMAP0": (22, int.from_bytes(b"R87PMAP0", "little")),
    "R87FREE0": (23, int.from_bytes(b"R87FREE0", "little")),
    "R87MACH0": (24, int.from_bytes(b"R87MACH0", "little")),
    "R87CLK00": (25, int.from_bytes(b"R87CLK00", "little")),
    "R87TASK0": (26, int.from_bytes(b"R87TASK0", "little")),
    "R87THRD0": (27, int.from_bytes(b"R87THRD0", "little")),
    "R87KTC00": (28, int.from_bytes(b"R87KTC00", "little")),
    "R87KBT00": (29, int.from_bytes(b"R87KBT00", "little")),
    "R87CPU00": (30, int.from_bytes(b"R87CPU00", "little")),
}
R88_STARTUP_MARKERS = {
    "R88PRBEG": (31, int.from_bytes(b"R88PRBEG", "little")),
    "R88PRNOK": (31, int.from_bytes(b"R88PRNOK", "little")),
    "R88IDLE0": (32, int.from_bytes(b"R88IDLE0", "little")),
    "R88SCHED": (33, int.from_bytes(b"R88SCHED", "little")),
    "R88DAEM0": (34, int.from_bytes(b"R88DAEM0", "little")),
    "R88CALL0": (35, int.from_bytes(b"R88CALL0", "little")),
    "R88BIND0": (36, int.from_bytes(b"R88BIND0", "little")),
    "R88IPCT0": (37, int.from_bytes(b"R88IPCT0", "little")),
    "R88MAP00": (38, int.from_bytes(b"R88MAP00", "little")),
    "R88CLK00": (39, int.from_bytes(b"R88CLK00", "little")),
    "R88DEV00": (40, int.from_bytes(b"R88DEV00", "little")),
    "R88BSDE0": (41, int.from_bytes(b"R88BSDE0", "little")),
    "R88LOCK0": (42, int.from_bytes(b"R88LOCK0", "little")),
    "R88IOKIT": (43, int.from_bytes(b"R88IOKIT", "little")),
    "R88SPL00": (44, int.from_bytes(b"R88SPL00", "little")),
    "R88SHR00": (45, int.from_bytes(b"R88SHR00", "little")),
    "R88BSDC0": (46, int.from_bytes(b"R88BSDC0", "little")),
    "R88BSDRT": (47, int.from_bytes(b"R88BSDRT", "little")),
}
R89_BSD_MARKERS = {
    "R89BSDI0": (31, int.from_bytes(b"R89BSDI0", "little")),
    "R89THRTL": (32, int.from_bytes(b"R89THRTL", "little")),
    "R89KMEM0": (33, int.from_bytes(b"R89KMEM0", "little")),
    "R89ARGS0": (34, int.from_bytes(b"R89ARGS0", "little")),
    "R89KAUT0": (35, int.from_bytes(b"R89KAUT0", "little")),
    "R89PROC0": (36, int.from_bytes(b"R89PROC0", "little")),
    "R89TTY00": (37, int.from_bytes(b"R89TTY00", "little")),
    "R89MNTC0": (38, int.from_bytes(b"R89MNTC0", "little")),
    "R89MNTOK": (39, int.from_bytes(b"R89MNTOK", "little")),
    "R89MNTER": (39, int.from_bytes(b"R89MNTER", "little")),
    "R89ROOT0": (40, int.from_bytes(b"R89ROOT0", "little")),
    "R89DEVF0": (41, int.from_bytes(b"R89DEVF0", "little")),
    "R89UTBS0": (42, int.from_bytes(b"R89UTBS0", "little")),
    "R89BSRET": (43, int.from_bytes(b"R89BSRET", "little")),
    "R89BTASK": (44, int.from_bytes(b"R89BTASK", "little")),
    "R89VMIL0": (45, int.from_bytes(b"R89VMIL0", "little")),
    "R89INIT0": (46, int.from_bytes(b"R89INIT0", "little")),
    "R89LRET0": (47, int.from_bytes(b"R89LRET0", "little")),
}
R90_BSD_MARKERS = {
    "R90PNAM0": (38, int.from_bytes(b"R90PNAM0", "little")),
    "R90LOCK0": (39, int.from_bytes(b"R90LOCK0", "little")),
    "R90SUBM0": (40, int.from_bytes(b"R90SUBM0", "little")),
    "R90FPX00": (41, int.from_bytes(b"R90FPX00", "little")),
    "R90VPG00": (42, int.from_bytes(b"R90VPG00", "little")),
    "R90TOD00": (43, int.from_bytes(b"R90TOD00", "little")),
    "R90MNTC0": (44, int.from_bytes(b"R90MNTC0", "little")),
    "R90MNTOK": (45, int.from_bytes(b"R90MNTOK", "little")),
    "R90MNTER": (45, int.from_bytes(b"R90MNTER", "little")),
    "R90ROOT0": (46, int.from_bytes(b"R90ROOT0", "little")),
    "R90DEVF0": (41, int.from_bytes(b"R90DEVF0", "little")),
    "R90UTBS0": (47, int.from_bytes(b"R90UTBS0", "little")),
    "R90BSRET": (43, int.from_bytes(b"R90BSRET", "little")),
    "R90BTASK": (44, int.from_bytes(b"R90BTASK", "little")),
    "R90VMIL0": (45, int.from_bytes(b"R90VMIL0", "little")),
    "R90INIT0": (46, int.from_bytes(b"R90INIT0", "little")),
    "R90LRET0": (47, int.from_bytes(b"R90LRET0", "little")),
}
R90_PROGRESS_ORDER = (
    "R90PNAM0", "R90LOCK0", "R90SUBM0", "R90FPX00", "R90VPG00",
    "R90TOD00", "R90MNTC0", "R90MNTOK", "R90MNTER", "R90ROOT0",
    "R90DEVF0", "R90UTBS0", "R90BSRET", "R90BTASK", "R90VMIL0",
    "R90INIT0", "R90LRET0",
)
R90_SLOT_SUCCESSORS = {
    "R90FPX00": "R90DEVF0",
    "R90TOD00": "R90BSRET",
    "R90MNTC0": "R90BTASK",
    "R90MNTOK": "R90VMIL0",
    "R90MNTER": "R90VMIL0",
    "R90ROOT0": "R90INIT0",
    "R90UTBS0": "R90LRET0",
}
R90_SLOT_ALTERNATES = {
    "R90MNTOK": "R90MNTER",
    "R90MNTER": "R90MNTOK",
}
R91_BSD_MARKERS = {
    "R91BBEG0": (37, int.from_bytes(b"R91BBEG0", "little")),
    "R91BEND0": (37, int.from_bytes(b"R91BEND0", "little")),
    "R91TIME0": (37, int.from_bytes(b"R91TIME0", "little")),
    "R91UBC00": (37, int.from_bytes(b"R91UBC00", "little")),
    "R91VFS00": (37, int.from_bytes(b"R91VFS00", "little")),
    "R91UUID0": (37, int.from_bytes(b"R91UUID0", "little")),
    "R91MBIN0": (37, int.from_bytes(b"R91MBIN0", "little")),
    "R91PIPE0": (37, int.from_bytes(b"R91PIPE0", "little")),
    "R91PTHR0": (37, int.from_bytes(b"R91PTHR0", "little")),
    "R91SLCT0": (37, int.from_bytes(b"R91SLCT0", "little")),
    "R91DOMN0": (37, int.from_bytes(b"R91DOMN0", "little")),
    "R91ACCT0": (37, int.from_bytes(b"R91ACCT0", "little")),
    "R91AUTO0": (37, int.from_bytes(b"R91AUTO0", "little")),
    "R91OSRS0": (37, int.from_bytes(b"R91OSRS0", "little")),
    "R91NETDN": (37, int.from_bytes(b"R91NETDN", "little")),
    "R91VPPRE": (37, int.from_bytes(b"R91VPPRE", "little")),
    "R91VPGOK": (37, int.from_bytes(b"R91VPGOK", "little")),
    "R91TOD00": (37, int.from_bytes(b"R91TOD00", "little")),
    "R91CONF0": (37, int.from_bytes(b"R91CONF0", "little")),
    "R91MNTC0": (37, int.from_bytes(b"R91MNTC0", "little")),
    "R91MNTOK": (37, int.from_bytes(b"R91MNTOK", "little")),
    "R91MNTER": (37, int.from_bytes(b"R91MNTER", "little")),
    "R91ROOT0": (37, int.from_bytes(b"R91ROOT0", "little")),
    "R91DEVF0": (37, int.from_bytes(b"R91DEVF0", "little")),
    "R91UTBS0": (37, int.from_bytes(b"R91UTBS0", "little")),
    "R91TAIL0": (37, int.from_bytes(b"R91TAIL0", "little")),
    "R91TASK0": (37, int.from_bytes(b"R91TASK0", "little")),
    "R91VMIL0": (37, int.from_bytes(b"R91VMIL0", "little")),
    "R91INIT0": (37, int.from_bytes(b"R91INIT0", "little")),
    "R91LRET0": (37, int.from_bytes(b"R91LRET0", "little")),
}
R91_TASK_MARKERS = ("R91TASK0", "R91VMIL0", "R91INIT0", "R91LRET0")
R91_PROGRESS_ORDER = (
    "R91BBEG0", "R91BEND0", "R91TIME0", "R91UBC00", "R91VFS00",
    "R91UUID0", "R91MBIN0", "R91PIPE0", "R91PTHR0", "R91SLCT0",
    "R91DOMN0", "R91ACCT0", "R91AUTO0", "R91OSRS0", "R91NETDN",
    "R91VPPRE", "R91VPGOK", "R91TOD00", "R91CONF0", "R91MNTC0",
    "R91MNTOK", "R91MNTER", "R91ROOT0", "R91DEVF0", "R91UTBS0",
    "R91TAIL0", "R91TASK0", "R91VMIL0", "R91INIT0", "R91LRET0",
)
R91_MOUNT_ALTERNATES = {"R91MNTOK": "R91MNTER", "R91MNTER": "R91MNTOK"}
R92_BSD_MARKERS = {
    "R92TPRE0": (37, int.from_bytes(b"R92TPRE0", "little")),
    "R92TOK00": (37, int.from_bytes(b"R92TOK00", "little")),
    "R92UPRE0": (37, int.from_bytes(b"R92UPRE0", "little")),
    "R92UOK00": (37, int.from_bytes(b"R92UOK00", "little")),
    "R92VPRE0": (37, int.from_bytes(b"R92VPRE0", "little")),
    "R92VOK00": (37, int.from_bytes(b"R92VOK00", "little")),
}
R92_PROGRESS_ORDER = tuple(R92_BSD_MARKERS)
R93_BSD_MARKERS = {
    "R93IENT0": (37, int.from_bytes(b"R93IENT0", "little")),
    "R93RPRE0": (37, int.from_bytes(b"R93RPRE0", "little")),
    "R93ROK00": (37, int.from_bytes(b"R93ROK00", "little")),
    "R93WPRE0": (37, int.from_bytes(b"R93WPRE0", "little")),
    "R93WOK00": (37, int.from_bytes(b"R93WOK00", "little")),
    "R93CPRE0": (37, int.from_bytes(b"R93CPRE0", "little")),
    "R93COK00": (37, int.from_bytes(b"R93COK00", "little")),
}
R93_PROGRESS_ORDER = tuple(R93_BSD_MARKERS)
R84_PHASE_MARKERS = {
    "ARMINITE": (5, R84_C_ENTRY_MARKER),
    "R84SET00": (11, R84_SETTER_RETURN_MARKER),
    "PEINITEN": (6, int.from_bytes(b"R84PEIN0", "little")),
    "PEINITRT": (7, int.from_bytes(b"R84PERT0", "little")),
    "ARMVMINI": (8, int.from_bytes(b"R84AVM00", "little")),
    "PANICINI": (9, int.from_bytes(b"R84PAN00", "little")),
    "CONSOLE": (10, int.from_bytes(b"R84CON00", "little")),
    "R84MST00": (13, int.from_bytes(b"R84MST00", "little")),
}
R84_VERSIONED_PHASE_NAMES = frozenset(R84_PHASE_MARKERS) - {"R84SET00", "R84MST00"}
R85_ARM_INIT_MARKERS = {
    **R84_PHASE_MARKERS,
    "R85LRET0": (11, R85_LATE_RETURN_MARKER),
    "R85MSB00": (12, R85_MACHINE_START_MARKER),
    "R85MACH0": (11, R85_MACHINE_RETURN_MARKER),
}
ENTRY_MARKER_LEGACY = 0x5952544E454D5241
TERMINAL_LINK_REGISTER_MAGICS = {
    int.from_bytes(f"Y35ALV0{version}".encode(), "little")
    for version in (4, 5, 6, 7)
}
TERMINAL_FAULT_MAGICS = {
    int.from_bytes(f"Y35ALV0{version}".encode(), "little") for version in (1, 2, 3, 4, 5, 6, 7)
}
Y35A_BOOTSTRAP_PHASES = {
    int.from_bytes(name.encode(), "little"): name
    for name in (
                "R82ARM00", "R84ARM00", "R84LATE0", "R81EAR00", "R81ARM00", "R81MCH00", "R81KBS00",
        "R81THRD0", "R81CPU00", "R81PRBEG", "R81PRG00",
        "R81PRD00", "R81PRNOK", "R81RD001", "R81RD002",
        "R81RD003", "R81RD004", "R81RD005", "R81UCP00",
    )
}
SCTLR_VALUE_SLOT = 57
R82_ARM_ENTRY_PHASE = int.from_bytes(b"R82ARM00", "little")
R68E7_STORE_WINDOW_RECORD = "r68e7-store-witness"
R68E7_STORE_WINDOW_BYTES = 64
R68E7_STORE_WINDOW_BASE_OFFSET = 0x240
R68E7_STORE_VALUE_OFFSETS = {
    "x16": 0,
    "x17": 8,
    "x9": 16,
    "x22": 24,
    "x23": 32,
    "global_readback": 40,
    "snapshot_marker": 48,
    "readback_marker": 56,
}
R68E7_STORE_MARKERS = {
    "PUBLIN00": (6, int.from_bytes(b"R68E7IN0", "little")),
    "PUBLRD00": (7, int.from_bytes(b"R68E7RB0", "little")),
}
R68E7_LOW_STORE_OFFSETS = {
    "x16": 0x828,
    "x17": 0x830,
    "x9": 0x838,
    "x22": 0x840,
    "x23": 0x848,
    "global_readback": 0x850,
}
R68E7_LOW_STAGE_SLOT = 11
R68E7_LOW_STAGE_MARKERS = {
    int.from_bytes(b"R68E7IN0", "little"): "snapshot-complete",
    int.from_bytes(b"R68E7RB0", "little"): "store-readback-complete",
}
R68E7_LOW_C_PHASE_MARKERS = {
    slot: (name, value) for name, (slot, value) in PHASE_MARKERS.items()
}
KVA_ALIAS_MARKER = (63, int.from_bytes(b"R68E7KV0", "little"))
CENTRY_MARKER = int.from_bytes(b"CENTRY00", "little")
PREVIOUS_GENERATION_MARKERS = {
    "FPGVA00": int.from_bytes(b"R68E6GV0", "little"),
    "FPBEFOR0": int.from_bytes(b"R68E6BF0", "little"),
    "FPSTOR00": int.from_bytes(b"R68E6ST0", "little"),
    "PUBLPR00": int.from_bytes(b"R68E6PR0", "little"),
    "PUBLPS00": int.from_bytes(b"R68E6PS0", "little"),
    "PREMMU00": int.from_bytes(b"R68E6PM0", "little"),
    "SCTLRRD0": int.from_bytes(b"R68E6RD0", "little"),
    "FIRST_CPU": int.from_bytes(b"R68E6FS0", "little"),
    "ARMENTRY": int.from_bytes(b"R68E6AR0", "little"),
}
RAW_STAGE_BASE_OFFSET = 0x10000
FULL_READBACK_HEADER_BYTES = 0x40
MINIMAL_REPORT_HEADER_OFFSET = 0x40
MINIMAL_REPORT_RECORDS_OFFSET = 0x100
FRESHNESS_WITNESS_OFFSET = 16
MINIMAL_FRESHNESS_WITNESS_RAW_OFFSET = (
    RAW_STAGE_BASE_OFFSET + MINIMAL_REPORT_HEADER_OFFSET + FRESHNESS_WITNESS_OFFSET
)
EARLY_RECORD_BYTES = 384
DIAGNOSTIC_CARRIER_BYTES = 528
HANDOFF_WITNESS_RECORD = "handoff-witness"
HANDOFF_WITNESS_BYTES = 16
FAULT_PUBLISH_WINDOW_RECORD = "fault-publish-window"
FAULT_PUBLISH_WINDOW_BASE_SLOT = 58
FAULT_PUBLISH_WINDOW_BYTES = 48
FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT = 45
FAULT_POINTER_WINDOW_RECORD = "fault-pointer-window"
FAULT_POINTER_WINDOW_BYTES = 16
ENTRY_PATH_WINDOW_RECORD = "entry-path-window"
ENTRY_PATH_WINDOW_BASE_SLOT = 64
ENTRY_PATH_WINDOW_BYTES = 16
MAPPING_CURSOR_MARKERS = (
    "L1ALLOC0", "VPPRE000", "VPMAP000", "VPCALL00",
    "KVPRE000", "KVAMAP00", "KVCALL00",
)
DIAGNOSTIC_WINDOW_RECORDS = frozenset((
    "early-fault-record",
    "mapping-carrier",
    HANDOFF_WITNESS_RECORD,
    FAULT_PUBLISH_WINDOW_RECORD,
    FAULT_POINTER_WINDOW_RECORD,
    ENTRY_PATH_WINDOW_RECORD,
    R68E7_STORE_WINDOW_RECORD,
))
FAULT_POINTER_VALUE_OFFSET = 8
BOUNDARY_MARKERS = (
    "ARMENTRY",
    "FIRST_CPU",
    "ARMINITE",
    "PEINITEN",
    "PEINITRT",
    "PREMMU00",
    "SCTLRRD0",
    "FPBEFOR0",
    "FPSTOR00",
    "PUBLPR00",
    "PUBLPS00",
    "PTBASE00",
    "PTCOUNT0",
    "PTSHIFT0",
    "ARMRET",
)
RAW_LOOP_STATE_SLOTS = (46, 47)


def disassemble_kernel(kernel: Path) -> str:
    objdump = find_tool("llvm-objdump")
    return subprocess.check_output(
        [
            objdump,
            "--macho",
            "--arch-name=arm64",
            "--section=__TEXT_EXEC,__text",
            "--disassemble",
            "--symbolize-operands",
            str(kernel),
        ],
        text=True,
        stderr=subprocess.STDOUT,
    )


def boundary_marker_spec(name: str) -> tuple[int, int]:
    if name == "ARMENTRY":
        return (4, ENTRY_MARKER)
    if name in ENTRY_PATH_MARKERS:
        return ENTRY_PATH_MARKERS[name]
    if name in PHASE_MARKERS:
        return PHASE_MARKERS[name]
    return HANDOFF_MARKERS[name]


def find_tool(name: str) -> str:
    try:
        path = subprocess.check_output(
            ["xcrun", "--find", name], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if path:
            return path
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    path = shutil.which(name)
    if path:
        return path
    raise RuntimeError(f"tool not found: {name}")


def nm_symbol_addresses(kernel: Path) -> dict[str, int]:
    nm = find_tool("llvm-nm")
    output = subprocess.check_output(
        [nm, "-arch", "arm64", "-n", str(kernel)], text=True, stderr=subprocess.STDOUT
    )
    symbols = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    return symbols


def nm_symbols(kernel: Path) -> set[str]:
    return set(nm_symbol_addresses(kernel))


def fault_pointer_symbol_physical(kernel: Path) -> int:
    layout = parse_macho(kernel.read_bytes())
    symbols = nm_symbol_addresses(kernel)
    if "_native_early_fault_address" not in symbols:
        raise RuntimeError("missing _native_early_fault_address symbol")
    return physical_base_for(layout["base"]) + symbols["_native_early_fault_address"] - layout["base"]


def normalize_disassembly_body(body: str) -> str:
    """Remove llvm-objdump address/encoding columns before instruction checks."""
    normalized = []
    pattern = re.compile(r"^\s*[0-9a-f]{8,16}:\s+(?:(?:[0-9a-f]{2}\s+){4})(.*)$", re.IGNORECASE)
    for line in body.splitlines():
        match = pattern.match(line)
        normalized.append(match.group(1).strip() if match else line.strip())
    return "\n".join(normalized)


def arm_init_body(kernel: Path, output: str | None = None) -> str:
    if output is None:
        output = disassemble_kernel(kernel)
    start = output.find("_arm_init:")
    end = output.find("_arm_init_cpu:", start + 1)
    if start < 0 or end < 0:
        raise RuntimeError("could not isolate _arm_init disassembly")
    return normalize_disassembly_body(output[start:end])


def start_first_cpu_body(kernel: Path, output: str | None = None) -> str:
    if output is None:
        output = disassemble_kernel(kernel)
    start = output.find("_start_first_cpu:")
    end = output.find("\ncommon_start:", start + 1)
    if start < 0 or end < 0:
        raise RuntimeError("could not isolate _start_first_cpu disassembly")
    return normalize_disassembly_body(output[start:end])


def common_start_body(kernel: Path, output: str | None = None) -> str:
    if output is None:
        output = disassemble_kernel(kernel)
    start = output.find("common_start:")
    end = output.find("\narm_init_tramp:", start + 1)
    if start < 0 or end < 0:
        raise RuntimeError("could not isolate common_start disassembly")
    return normalize_disassembly_body(output[start:end])


def start_cpu_body(kernel: Path, output: str | None = None) -> str:
    if output is None:
        output = disassemble_kernel(kernel)
    start = output.find("_start_cpu:")
    end = output.find("\ncommon_start:", start + 1)
    if start < 0 or end < 0:
        raise RuntimeError("could not isolate secondary start_cpu disassembly")
    return normalize_disassembly_body(output[start:end])


def _codeword_materialization_matches(lines: list[str], store: int,
                                       register: str, value: int) -> bool:
    if store < 4:
        return False
    for offset, shift in enumerate((0, 16, 32, 48), start=store - 4):
        half = (value >> shift) & 0xffff
        immediate = rf"(?:0x{half:x}|{half})"
        mnemonic = "mov" if shift == 0 else "movk"
        suffix = "" if shift == 0 else rf",\s*lsl\s*#\s*{shift}"
        pattern = rf"{mnemonic}\s+{register},\s*#\s*{immediate}{suffix}"
        if re.fullmatch(pattern, lines[offset], re.IGNORECASE) is None:
            return False
    return True


def _marker_slot_store_indexes(lines: list[str], name: str, register: str = "x15") -> list[int]:
    slot, _value = HANDOFF_MARKERS[name]
    physical_offset = 0x800 + slot * 8
    pattern = rf"str\s+{register},\s*\[x20,\s*#(?:0x{physical_offset:x}|{physical_offset})\]"
    return [index for index, line in enumerate(lines)
            if re.fullmatch(pattern, line, re.IGNORECASE)]


def _control_transfer_indexes(lines: list[str], start: int, end: int) -> list[int]:
    branch = re.compile(r"(?:b(?:\.[a-z0-9]+)?|bl|br|blr|cbz|cbnz|tbz|tbnz|ret)\b",
                        re.IGNORECASE)
    return [index for index in range(max(start, 0), min(end, len(lines)))
            if branch.match(lines[index])]


def _branch_instruction_indexes(lines: list[str], start: int, end: int) -> list[int]:
    """Return control-flow branches, excluding BL/BLR calls that return normally."""
    branch = re.compile(r"(?:b(?:\.[a-z0-9]+)?|br|cbz|cbnz|tbz|tbnz|ret)\b",
                        re.IGNORECASE)
    return [index for index in range(max(start, 0), min(end, len(lines)))
            if branch.match(lines[index])]

def verify_entry_witness(body: str, *, expected_marker: int | None = None) -> list[str]:
    """Bind the earliest entry codeword to its immediate physical carrier store."""
    lines = [line.strip() for line in body.splitlines()]
    stores = [i for i, line in enumerate(lines)
              if re.fullmatch(r"str\s+x15,\s*\[x16\]", line, re.IGNORECASE)]
    if len(stores) != 1:
        return [f"expected one earliest ARMENTRY store through x16, found {len(stores)}"]
    store = stores[0]
    add_index = store - 5
    if add_index < 0 or re.fullmatch(
        r"add\s+x16,\s*x20,\s*#(?:0x820|2080)", lines[add_index], re.IGNORECASE
    ) is None:
        return ["earliest ARMENTRY codeword must immediately follow x20+0x820 carrier setup"]
    accepted = ((ENTRY_MARKER, R83_ENTRY_MARKER, R84_ENTRY_MARKER) if expected_marker is None
                else (expected_marker,))
    if not any(_codeword_materialization_matches(lines, store, "x15", marker)
               for marker in accepted):
        return ["earliest entry codeword is not fully materialized immediately before its store"]
    if _control_transfer_indexes(lines, 0, store + 1):
        return ["control transfer can bypass the earliest ARMENTRY physical store"]
    return []

def verify_first_cpu_path_witness(
    body: str, *, expected_marker: int | None = None
) -> list[str]:
    failures: list[str] = []
    lines = [line.strip() for line in body.splitlines()]
    vbar = [i for i, line in enumerate(lines)
            if re.search(r"\bmsr\s+VBAR_EL1\b", line, re.IGNORECASE)]
    stores = [i for i, line in enumerate(lines)
              if re.fullmatch(r"str\s+x15,\s*\[x20,\s*#(?:0xa00|2560)\]", line, re.IGNORECASE)]
    if not vbar:
        failures.append("expected early VBAR_EL1 write in cold entry")
    if len(stores) != 1:
        failures.append(f"expected one cold entry slot64 store, found {len(stores)}")
        return failures
    store = stores[0]
    if vbar and store != vbar[0] + 5:
        failures.append("R68E7FS0 materialization and slot64 store must immediately follow early VBAR_EL1")
    preceding = lines[max(0, store - 4):store]
    accepted = ((ENTRY_PATH_MARKERS["FIRST_CPU"][1], R83_FIRST_CPU_MARKER,
                 R84_FIRST_CPU_MARKER)
                if expected_marker is None else (expected_marker,))
    if len(preceding) != 4 or not any(
        _codeword_materialization_matches(lines, store, "x15", marker)
        for marker in accepted
    ):
        failures.append(
            "R68E7FS0 must be fully materialized immediately before slot64 store"
            if expected_marker is None else
            "R83FS00 zero-padded codeword must be fully materialized immediately before slot64 store"
        )
    after_store = (
        r"add\s+x14,\s*x20,\s*#(?:0xa00|2560)",
        r"dsb\s+sy",
        r"dc\s+civac,\s*x14",
        r"dsb\s+sy",
        r"ldr\s+x16,\s*\[x20,\s*#(?:0xa00|2560)\]",
        r"str\s+x16,\s*\[x20,\s*#(?:0xa08|2568)\]",
        r"add\s+x14,\s*x20,\s*#(?:0xa08|2568)",
        r"dsb\s+sy",
        r"dc\s+civac,\s*x14",
        r"dsb\s+sy",
    )
    for offset, pattern in enumerate(after_store, 1):
        index = store + offset
        if index >= len(lines) or not re.fullmatch(pattern, lines[index], re.IGNORECASE):
            failures.append(f"slot64 load-back/cache-persist sequence failed at {pattern}")
            break
    if vbar and _control_transfer_indexes(lines, 0, store + len(after_store) + 1):
        failures.append("control transfer can bypass the R68E7FS0 store or its load-back witness")
    return failures

def verify_secondary_entry_witness(body: str) -> list[str]:
    if re.search(r"\bstr\s+x15,\s*\[x20,\s*#(?:0xa08|2568)\]", body, re.IGNORECASE):
        return ["secondary start_cpu path must not store through const_boot_args+0xa08"]
    return []


def _parse_imm(raw: str) -> int:
    return int(raw, 0) if raw.lower().startswith("0x") else int(raw, 10)


def _record_raw_offset(manifest_data: dict, record: dict) -> int:
    key = "report_offset" if manifest_data.get("transport_mode") == "minimal-boundary" else "offset"
    offset = int(record[key])
    return RAW_STAGE_BASE_OFFSET + offset if manifest_data.get("transport_mode") == "minimal-boundary" else offset


def verify_transport_record_layout(manifest_data: dict) -> list[str]:
    """Reject aliased destination ranges and writes into transport headers."""
    mode = manifest_data.get("transport_mode")
    if mode not in ("full-readback", "minimal-boundary"):
        return []
    offset_key = "report_offset" if mode == "minimal-boundary" else "offset"
    reserved_end = (MINIMAL_REPORT_RECORDS_OFFSET if mode == "minimal-boundary"
                    else FULL_READBACK_HEADER_BYTES)
    limit_key = "report_bytes" if mode == "minimal-boundary" else "staged_bytes"
    try:
        limit = int(manifest_data.get(limit_key, 0))
    except (TypeError, ValueError):
        limit = 0
    ranges = []
    failures = []
    for record in manifest_data.get("records", []):
        name = str(record.get("name", "<unnamed>"))
        try:
            start = int(record[offset_key])
            size = int(record["size"])
            if start < 0 or size <= 0:
                raise ValueError("negative offset or non-positive size")
        except (KeyError, TypeError, ValueError):
            failures.append(f"readback transport range is invalid for {name}")
            continue
        end = start + size
        if start < reserved_end:
            failures.append(
                f"readback transport range for {name} overlaps reserved report head "
                f"0x0..{reserved_end:#x}"
            )
        if limit > 0 and end > limit:
            failures.append(
                f"readback transport range for {name} ends at {end:#x}, beyond "
                f"{limit_key} {limit:#x}"
            )
        ranges.append((name, start, end))
    for index, (left_name, left_start, left_end) in enumerate(ranges):
        for right_name, right_start, right_end in ranges[index + 1:]:
            if left_start < right_end and right_start < left_end:
                failures.append(
                    f"readback transport ranges overlap: {left_name} overlaps {right_name}"
                )
    return failures


def verify_capture_kernel_binding(raw: Path, manifest: Path) -> list[str]:
    """Bind a captured probe header's 64-bit kernel tag to its manifest."""
    manifest_data = json.loads(manifest.read_text())
    mode = manifest_data.get("transport_mode")
    if mode == "minimal-boundary":
        header_offset = RAW_STAGE_BASE_OFFSET + MINIMAL_REPORT_HEADER_OFFSET
        expected_magic = b"Y35ARD02"
    elif mode == "full-readback":
        header_offset = 0
        expected_magic = b"Y35ARD01"
    else:
        return [f"capture kernel binding has unsupported transport_mode {mode!r}"]
    try:
        digest = str(manifest_data["kernel_sha256"])
        if len(digest) != 64:
            raise ValueError("kernel_sha256 must contain 64 hexadecimal characters")
        expected_prefix = bytes.fromhex(digest[:16])
    except (KeyError, TypeError, ValueError) as exc:
        return [f"capture kernel binding has invalid manifest kernel_sha256: {exc}"]
    data = raw.read_bytes()
    if header_offset + 16 > len(data):
        return [f"capture is too short for {expected_magic.decode()} kernel header"]
    magic = data[header_offset:header_offset + 8]
    if magic != expected_magic:
        return [
            f"capture header at {header_offset:#x} is {magic!r}, "
            f"not {expected_magic!r}"
        ]
    observed_prefix = data[header_offset + 8:header_offset + 16]
    if observed_prefix != expected_prefix:
        return [
            "capture kernel SHA-256 prefix "
            f"{observed_prefix.hex()} does not match manifest prefix {expected_prefix.hex()}"
        ]
    return []


def verify_probe_image_binding(
    probe: Path | None, manifest: Path | None, *, required: bool = False
) -> list[str]:
    """Check the supplied probe artifact against the image hash in its manifest."""
    if probe is None:
        if required:
            return ["raw verification requires --probe to bind the probe image to its manifest"]
        return []
    if manifest is None:
        return ["probe image verification requires --manifest"]
    manifest_data = json.loads(manifest.read_text())
    expected = manifest_data.get("image_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return ["readback manifest has no valid image_sha256 for the supplied probe"]
    try:
        bytes.fromhex(expected)
        actual = hashlib.sha256(probe.read_bytes()).hexdigest()
    except (OSError, ValueError) as exc:
        return [f"could not verify probe image SHA-256: {exc}"]
    if actual != expected.lower():
        return [f"manifest image_sha256 {expected} != supplied probe SHA-256 {actual}"]
    return []


def _marker_events(body: str, marker_map=None) -> list[tuple[str, int, int]]:
    """Recover marker constants and carrier slots from final ARM64 text."""
    registers: dict[str, int] = {}
    events: list[tuple[str, int, int]] = []
    if marker_map is None:
        marker_map = PHASE_MARKERS
    values = {value: name for name, (_slot, value) in marker_map.items()}
    for index, line in enumerate(body.splitlines()):
        mov = re.search(r"\bmov\s+(x\d+), #([0-9A-Fa-fx]+)", line)
        if mov:
            registers[mov.group(1)] = _parse_imm(mov.group(2))
        movk = re.search(
            r"\bmovk\s+(x\d+), #([0-9A-Fa-fx]+), lsl #(\d+)", line
        )
        if movk:
            register = movk.group(1)
            shift = int(movk.group(3), 10)
            current = registers.get(register, 0)
            registers[register] = (current & ~(0xFFFF << shift)) | (
                _parse_imm(movk.group(2)) << shift
            )
            continue
            continue
        add = re.search(
            r"\badd\s+(x\d+), (x\d+), #([0-9A-Fa-fx]+)", line
        )
        if add:
            source = registers.get(add.group(2))
            if source is not None:
                registers[add.group(1)] = source + _parse_imm(add.group(3))
        # A later store after a load must not inherit the old constant that
        # used to occupy the destination register. This matters for the
        # high-carrier readback witness (ldr x15, [...]; str x15, [...]).
        load_pair = re.search(r"\bldp\s+(x\d+),\s*(x\d+),", line)
        if load_pair:
            registers.pop(load_pair.group(1), None)
            registers.pop(load_pair.group(2), None)
            continue
        load = re.search(r"\bldr\s+(x\d+),", line)
        if load:
            registers.pop(load.group(1), None)
            continue
        store = re.search(
            r"\bstr\s+(x\d+), \[x\d+, #([0-9A-Fa-fx]+)\]!?", line
        )
        if not store:
            continue
        value = registers.get(store.group(1))
        if value not in values:
            continue
        offset = _parse_imm(store.group(2))
        if offset >= 0x800 and (offset - 0x800) % 8 == 0:
            slot = (offset - 0x800) // 8
        elif offset % 8 == 0:
            slot = offset // 8
        else:
            continue
        events.append((values[value], index, slot))
    return events


def _phase_set_calls(body: str) -> list[tuple[int, int | None]]:
    """Recover x0 values passed to y35a_bootstrap_phase_set from linked text."""
    registers: dict[str, int] = {}
    calls: list[tuple[int, int | None]] = []
    for index, line in enumerate(body.splitlines()):
        mov_imm = re.search(r"\bmov\s+([xw]\d+), #([0-9A-Fa-fx]+)", line)
        if mov_imm:
            dest = "x" + mov_imm.group(1)[1:]
            if mov_imm.group(1).startswith("x"):
                registers[dest] = _parse_imm(mov_imm.group(2))
            else:
                registers.pop(dest, None)
            continue
        mov_reg = re.search(r"\bmov\s+(x\d+), (x\d+)\b", line)
        if mov_reg:
            if mov_reg.group(2) in registers:
                registers[mov_reg.group(1)] = registers[mov_reg.group(2)]
            else:
                registers.pop(mov_reg.group(1), None)
            continue
        movk = re.search(
            r"\bmovk\s+(x\d+), #([0-9A-Fa-fx]+), lsl #(\d+)", line
        )
        if movk:
            register = movk.group(1)
            shift = int(movk.group(3), 10)
            current = registers.get(register, 0)
            registers[register] = (current & ~(0xFFFF << shift)) | (
                _parse_imm(movk.group(2)) << shift
            )
            continue
        add = re.search(
            r"\badd\s+(x\d+), (x\d+), #([0-9A-Fa-fx]+)(?:, lsl #(\d+))?",
            line,
        )
        if add:
            source = registers.get(add.group(2))
            if source is not None:
                shift = int(add.group(4), 10) if add.group(4) else 0
                registers[add.group(1)] = source + (_parse_imm(add.group(3)) << shift)
            else:
                registers.pop(add.group(1), None)
            continue

        call = re.search(r"\bblr?\s+(_[A-Za-z0-9_$]+|x\d+)\b", line)
        if not call:
            # Unsupported instructions that write a GPR invalidate its value.
            # Stores, barriers, compares and control-flow instructions have no
            # GPR destination and leave the tracked values alone.
            dest = re.match(r"\s*([a-z][a-z0-9.]*)\s+([xw]\d+)\b", line)
            if dest and dest.group(1) not in {
                "str", "stur", "stp", "stnp", "dc", "dsb", "dmb", "isb",
                "cmp", "cmn", "tst", "b", "br", "cbz", "cbnz", "tbz",
                "tbnz", "ret", "eret", "nop",
            }:
                register = "x" + dest.group(2)[1:]
                registers.pop(register, None)
            pair = re.match(r"\s*ldp\s+([xw]\d+),\s*([xw]\d+),", line)
            if pair:
                registers.pop("x" + pair.group(1)[1:], None)
                registers.pop("x" + pair.group(2)[1:], None)
            continue
        if call.group(1) == "_y35a_bootstrap_phase_set":
            calls.append((index, registers.get("x0")))
        for register in range(19):
            registers.pop(f"x{register}", None)  # AAPCS64 caller-saved state.
    return calls


def _marker_helper_calls(body: str) -> list[tuple[int, int | None, int | None]]:
    """Recover slot and codeword arguments passed to the external marker helper."""
    registers: dict[str, int] = {}
    calls: list[tuple[int, int | None, int | None]] = []
    for index, line in enumerate(body.splitlines()):
        mov_imm = re.search(r"\bmov\s+([xw]\d+), #([0-9A-Fa-fx]+)", line)
        if mov_imm:
            register = "x" + mov_imm.group(1)[1:]
            registers[register] = _parse_imm(mov_imm.group(2))
            continue
        mov_reg = re.search(r"\bmov\s+(x\d+), (x\d+)\b", line)
        if mov_reg:
            if mov_reg.group(2) in registers:
                registers[mov_reg.group(1)] = registers[mov_reg.group(2)]
            else:
                registers.pop(mov_reg.group(1), None)
            continue
        movk = re.search(r"\bmovk\s+(x\d+), #([0-9A-Fa-fx]+), lsl #(\d+)", line)
        if movk:
            register = movk.group(1)
            shift = int(movk.group(3), 10)
            current = registers.get(register, 0)
            registers[register] = (current & ~(0xFFFF << shift)) | (
                _parse_imm(movk.group(2)) << shift
            )
            continue
        add = re.search(
            r"\badd\s+(x\d+),\s*(x\d+),\s*#([0-9A-Fa-fx]+)(?:,\s*lsl\s*#(\d+))?",
            line,
        )
        if add:
            source = registers.get(add.group(2))
            if source is not None:
                shift = int(add.group(4), 10) if add.group(4) else 0
                registers[add.group(1)] = source + (_parse_imm(add.group(3)) << shift)
            else:
                registers.pop(add.group(1), None)
            continue
        orr = re.match(
            r"\s*orr\s+(x\d+),\s*(x\d+),\s*#([0-9A-Fa-fx]+)", line
        )
        if orr:
            source = registers.get(orr.group(2))
            if source is not None:
                registers[orr.group(1)] = source | _parse_imm(orr.group(3))
            else:
                registers.pop(orr.group(1), None)
            continue
        call = re.search(r"\bblr?\s+(_[A-Za-z0-9_$]+|x\d+)\b", line)
        if call:
            if call.group(1) == "_native_phase_marker_external":
                calls.append((index, registers.get("x0"), registers.get("x1")))
            for register in range(19):
                registers.pop(f"x{register}", None)
            continue
        dest = re.match(r"\s*([a-z][a-z0-9.]*)\s+([xw]\d+)\b", line)
        if dest and dest.group(1) not in {
            "str", "stur", "stp", "stnp", "dc", "dsb", "dmb", "isb",
            "cmp", "cmn", "tst", "b", "br", "cbz", "cbnz", "tbz",
            "tbnz", "ret", "eret", "nop",
        }:
            registers.pop("x" + dest.group(2)[1:], None)
    return calls


def verify_r82_arm_init_cursor(body: str, *, required: bool = False) -> list[str]:
    """Bind R82ARM00 to the first phase-set call before the ARMINITE store."""
    calls = _phase_set_calls(body)
    matches = [(index, value) for index, value in calls
               if value == R82_ARM_ENTRY_PHASE]
    if not matches and not required:
        return []
    if len(matches) != 1:
        return ["missing or duplicate R82ARM00 phase-set call"]

    lines = body.splitlines()
    events = [event for event in _marker_events(body)
              if event[0] == "ARMINITE" and event[2] == 5]
    if len(events) != 1:
        return ["R82ARM00 gate requires exactly one ARMINITE slot-5 carrier store"]
    phase_index = matches[0][0]
    if phase_index >= events[0][1]:
        return ["R82ARM00 cursor must precede the ARMINITE carrier store"]
    for line in lines[:phase_index]:
        mnemonic = line.split(None, 1)[0].lower() if line.split() else ""
        if (mnemonic in {"b", "br", "cbz", "cbnz", "tbz", "tbnz", "ret", "eret"}
                or mnemonic.startswith("b.")):
            return ["branch can bypass R82ARM00 phase-set call"]
    first_bl = next((i for i, line in enumerate(lines)
                     if re.search(r"\bblr?\s+", line)), None)
    if first_bl != phase_index:
        return ["R82ARM00 setter is not the first arm_init call"]

    saved_args = [i for i, line in enumerate(lines[:phase_index])
                  if re.search(r"\bmov\s+x19, x0\b", line)]
    if not saved_args:
        return ["R82ARM00 gate cannot bind x19 to the incoming boot_args pointer"]

    store_index = events[0][1]
    store = re.search(r"\bstr\s+(x\d+), \[(x\d+), #([0-9A-Fa-fx]+)\]",
                      lines[store_index])
    if (store is None or store.group(2) != "x8"
            or _parse_imm(store.group(3)) != 0x828):
        return ["ARMINITE slot-5 store is not based on the incoming boot_args pointer"]
    base_moves = [i for i in range(phase_index + 1, store_index)
                  if re.search(r"\bmov\s+x8, x19\b", lines[i])]
    if not base_moves:
        return ["ARMINITE carrier base is not reloaded from saved boot_args"]
    base_index = base_moves[-1]
    for line in lines[base_index + 1:store_index]:
        dest = re.match(r"\s*([a-z][a-z0-9.]*)\s+(x\d+)\b", line)
        if dest and dest.group(2) == "x8" and dest.group(1) not in {"str", "stur", "stp"}:
            return ["ARMINITE carrier base is overwritten before slot-5 store"]
    address_builds = [i for i in range(base_index + 1, store_index)
                      if re.search(r"\badd\s+x9, x8, #(?:0x828|2088)\b", lines[i])]
    if not address_builds:
        return ["ARMINITE cache-maintenance address is not derived from its carrier slot"]
    clean = next((i for i in range(store_index + 1, min(store_index + 4, len(lines)))
                  if re.search(r"\bdc\s+civac, x9\b", lines[i])), None)
    if clean is None or clean + 1 >= len(lines) or not re.fullmatch(r"dsb\s+sy", lines[clean + 1]):
        return ["ARMINITE slot-5 store lacks its DC CIVAC and DSB completion"]
    if any(re.match(r"\s*(?:mov|movk|add|ldr|ldp|eor|orr|and|sub)\s+x9\b", line)
           for line in lines[address_builds[-1] + 1:clean]):
        return ["ARMINITE cache-maintenance address is overwritten before DC CIVAC"]
    return []


def verify_r83_arm_init_cursor(body: str, *, required: bool = False) -> list[str]:
    """Require R83CIN00's slot-5 write and persistence barrier before R82ARM00."""
    events = _marker_events(
        body, marker_map={"R83CIN00": (5, R83_C_ENTRY_MARKER)}
    )
    calls = [(index, value) for index, value in _phase_set_calls(body)
             if value == R82_ARM_ENTRY_PHASE]
    if not events and not calls and not required:
        return []
    if len(events) != 1:
        return [f"R83 requires exactly one R83CIN00 slot-5 store, found {len(events)}"]
    if len(calls) != 1:
        return [f"R83 requires exactly one R82ARM00 phase-set call, found {len(calls)}"]

    lines = body.splitlines()
    marker_name, store_index, slot = events[0]
    if marker_name != "R83CIN00" or slot != 5:
        return ["R83CIN00 does not own slot 5"]
    store = re.search(
        r"\bstr\s+(x\d+),\s*\[(x\d+),\s*#([0-9A-Fa-fx]+)\]",
        lines[store_index],
    )
    if store is None or _parse_imm(store.group(3)) != 0x828:
        return ["R83CIN00 slot-5 store is not at boot_args+0x828"]
    store_base = store.group(2)
    base_moves = [index for index, line in enumerate(lines[:store_index])
                  if re.fullmatch(rf"mov\s+{re.escape(store_base)},\s*x19", line,
                                  re.IGNORECASE)]
    arg_saves = [index for index, line in enumerate(lines[:store_index])
                 if re.fullmatch(r"mov\s+x19,\s*x0", line, re.IGNORECASE)]
    if not base_moves or not arg_saves or arg_saves[-1] >= base_moves[-1]:
        return ["R83CIN00 carrier base is not derived from incoming boot_args in x0"]
    base_index = base_moves[-1]
    if any(re.match(rf"(?:mov|movk|add|ldr|ldp|eor|orr|and|sub)\s+{re.escape(store_base)}\b",
                    line, re.IGNORECASE)
           for line in lines[base_index + 1:store_index]):
        return ["R83CIN00 carrier base is overwritten before its slot-5 store"]
    cache_addresses = []
    for index in range(max(0, store_index - 5), store_index):
        address = re.fullmatch(
            rf"add\s+(x\d+),\s*{re.escape(store_base)},\s*#(?:0x828|2088)",
            lines[index], re.IGNORECASE,
        )
        if address:
            cache_addresses.append((index, address.group(1)))
    if len(cache_addresses) != 1:
        return ["R83CIN00 clean address is not derived from the slot-5 carrier"]
    cache_register = cache_addresses[0][1]
    clean = next((index for index in range(store_index + 1, min(store_index + 4, len(lines)))
                  if re.fullmatch(
                      rf"dc\s+civac,\s*{re.escape(cache_register)}",
                      lines[index], re.IGNORECASE,
                  )), None)
    if clean is None or clean + 1 >= len(lines) \
            or not re.fullmatch(r"dsb\s+sy", lines[clean + 1], re.IGNORECASE):
        return ["R83CIN00 slot-5 store lacks DC CIVAC followed by DSB SY"]
    cache_index, cache_register = cache_addresses[0]
    if any(re.match(rf"(?:mov|movk|add|ldr|ldp|eor|orr|and|sub)\s+{re.escape(cache_register)}\b",
                    line, re.IGNORECASE)
           for line in lines[cache_index + 1:clean]):
        return ["R83CIN00 DC CIVAC address is overwritten before cache maintenance"]
    phase_index = calls[0][0]
    if clean + 1 >= phase_index:
        return ["R83ARM00 setter begins before the R83CIN00 store and persistence barrier complete"]
    if _branch_instruction_indexes(lines, base_index, phase_index):
        return ["control-flow branch can bypass R83CIN00 or its clean before R82ARM00"]
    return []


def _decode_cbz_target(instruction: int, pc: int) -> int | None:
    """Decode the target of one AArch64 CBZ/CBNZ instruction."""
    if instruction & 0x7E000000 != 0x34000000:
        return None
    immediate = (instruction >> 5) & 0x7FFFF
    if immediate & (1 << 18):
        immediate -= 1 << 19
    return pc + (immediate << 2)


def _instruction_count_before(lines: list[str], line_index: int) -> int:
    """Count disassembled instructions while ignoring labels and blank lines."""
    return sum(
        bool(re.match(r"\s*[a-z][a-z0-9.]*\s+", line, re.IGNORECASE))
        for line in lines[:line_index]
    )


def verify_r83_arm_init_control_flow(
    body: str, kernel: Path, symbol_address: int | None
) -> list[str]:
    """Prove the optional native_phase_args branch rejoins before R83CIN00."""
    if symbol_address is None:
        return ["missing _arm_init address for R83 branch-target validation"]
    lines = body.splitlines()
    events = _marker_events(body, marker_map={"R83CIN00": (5, R83_C_ENTRY_MARKER)})
    calls = [(index, value) for index, value in _phase_set_calls(body)
             if value == R82_ARM_ENTRY_PHASE]
    if len(events) != 1 or len(calls) != 1:
        return ["R83 branch-target validation requires one C-entry marker and one phase setter"]
    store_index = events[0][1]
    phase_index = calls[0][0]
    base_moves = [index for index, line in enumerate(lines[:store_index])
                  if re.fullmatch(r"mov\s+x8,\s*x19", line, re.IGNORECASE)]
    arg_saves = [index for index, line in enumerate(lines[:store_index])
                 if re.fullmatch(r"mov\s+x19,\s*x0", line, re.IGNORECASE)]
    if not base_moves or not arg_saves:
        return ["R83 branch-target validation cannot bind x8 to incoming boot_args"]
    base_index = base_moves[-1]
    prefix_branches = _branch_instruction_indexes(lines, arg_saves[-1] + 1, base_index)
    if len(prefix_branches) > 1:
        return ["unexpected branches precede the R83CIN00 carrier setup"]
    if prefix_branches:
        branch_index = prefix_branches[0]
        branch_line = lines[branch_index]
        prior = lines[branch_index - 1] if branch_index else ""
        fallthrough = lines[branch_index + 1] if branch_index + 1 < len(lines) else ""
        if (not re.match(r"cbnz\s+x8\b", branch_line, re.IGNORECASE)
                or not re.fullmatch(r"ldr\s+x8,\s*\[x\d+,\s*#[0-9A-Fa-fx]+\]", prior,
                                    re.IGNORECASE)
                or not re.fullmatch(r"str\s+x19,\s*\[x\d+,\s*#[0-9A-Fa-fx]+\]", fallthrough,
                                    re.IGNORECASE)):
            return ["R83 pre-marker branch is not the native_phase_args initialization guard"]
        branch_instruction_index = _instruction_count_before(lines, branch_index)
        base_instruction_index = _instruction_count_before(lines, base_index)
        image = kernel.read_bytes()
        layout = parse_macho(image)
        pc = symbol_address + 4 * branch_instruction_index
        segment = next((item for item in layout["segments"]
                        if item["address"] <= pc < item["address"] + item["file_size"]), None)
        if segment is None:
            return ["R83 native_phase_args branch is outside file-backed Mach-O text"]
        file_offset = segment["offset"] + pc - segment["address"]
        instruction = int.from_bytes(image[file_offset:file_offset + 4], "little")
        target = _decode_cbz_target(instruction, pc)
        expected_target = symbol_address + 4 * (base_instruction_index + 1)
        if target != expected_target:
            return ["native_phase_args branch does not rejoin at the R83 marker setup"]
    if _branch_instruction_indexes(lines, base_index, phase_index):
        return ["control-flow branch can bypass R83CIN00 before R82ARM00"]
    return []


def verify_r84_arm_init_progress(body: str, *, required: bool = False) -> list[str]:
    """Bind R84 C-entry snapshots, setter return, and versioned C-stage markers."""
    events = _marker_events(body, marker_map=R84_PHASE_MARKERS)
    if not events and not required:
        return []
    by_name: dict[str, list[tuple[int, int]]] = {}
    for name, index, slot in events:
        by_name.setdefault(name, []).append((index, slot))
    failures = []
    for name, (expected_slot, _value) in R84_PHASE_MARKERS.items():
        matches = by_name.get(name, [])
        if len(matches) != 1:
            failures.append(f"R84 requires exactly one {name} marker, found {len(matches)}")
        elif matches[0][1] != expected_slot:
            failures.append(f"R84 {name} marker stores slot {matches[0][1]}, expected {expected_slot}")

    lines = body.splitlines()
    phase_calls = _phase_set_calls(body)
    entry_calls = [index for index, value in phase_calls if value == R84_ARM_ENTRY_PHASE]
    late_calls = [index for index, value in phase_calls if value == R84_LATE_PHASE]
    if len(entry_calls) != 1 or len(late_calls) != 1:
        failures.append("R84 requires one R84ARM00 entry setter and one R84LATE0 later setter")
    if failures:
        return failures
    entry_setter, late_setter = entry_calls[0], late_calls[0]
    marker_index = {name: values[0][0] for name, values in by_name.items()}

    c_store = marker_index["ARMINITE"]
    store_line = re.search(
        r"\bstr\s+(x\d+),\s*\[(x\d+),\s*#([0-9A-Fa-fx]+)\]",
        lines[c_store],
    )
    if store_line is None or _parse_imm(store_line.group(3)) != 0x828:
        return ["R84CIN00 is not stored at boot_args+0x828"]
    c_clean = next((index for index in range(c_store + 1, min(c_store + 4, len(lines)))
                    if re.fullmatch(r"dc\s+civac,\s*x\d+", lines[index], re.IGNORECASE)), None)
    if c_clean is None or c_clean + 1 >= entry_setter \
            or not re.fullmatch(r"dsb\s+sy", lines[c_clean + 1], re.IGNORECASE):
        return ["R84ARM00 begins before the R84CIN00 slot-5 write is persistent"]

    loads64 = [index for index, line in enumerate(lines)
               if re.fullmatch(r"ldr\s+x\d+,\s*\[x19,\s*#(?:0xa00|2560)\]", line,
                               re.IGNORECASE)]
    loads65 = [index for index, line in enumerate(lines)
               if re.fullmatch(r"ldr\s+x\d+,\s*\[x19,\s*#(?:0xa08|2568)\]", line,
                               re.IGNORECASE)]
    stores29 = [index for index, line in enumerate(lines)
                if re.fullmatch(r"str\s+x\d+,\s*\[x\d+,\s*#(?:0x8e8|2280|0xe8|232)\]!",
                                line, re.IGNORECASE)]
    stores30 = [index for index, line in enumerate(lines)
                if re.fullmatch(r"str\s+x\d+,\s*\[x\d+,\s*#(?:0x8f0|2288|0xf0|240)\]!",
                                line, re.IGNORECASE)]
    if not (len(loads64) == len(loads65) == len(stores29) == len(stores30) == 1):
        return ["R84 must sample slot64/65 and publish snapshots in slots29/30"]
    if not (c_store < loads64[0] < loads65[0] < stores29[0] < stores30[0] < entry_setter):
        return ["R84 slot64/65 C-entry snapshots are out of order or after R84ARM00"]
    snapshot_range = lines[stores29[0] + 1:entry_setter]
    if sum(bool(re.fullmatch(r"dc\s+civac,\s*x\d+", line, re.IGNORECASE))
           for line in snapshot_range) < 2 \
            or sum(bool(re.fullmatch(r"dsb\s+sy", line, re.IGNORECASE))
                   for line in snapshot_range) < 2:
        return ["R84 C-entry snapshots lack two cache cleans and completion barriers"]

    setter_return = marker_index["R84SET00"]
    if not entry_setter < setter_return < marker_index["PEINITEN"]:
        return ["R84SET00 must follow the entry setter and precede PE_init_platform"]
    return_store = re.search(
        r"\bstr\s+(x\d+),\s*\[(x\d+),\s*#([0-9A-Fa-fx]+)\]!?",
        lines[setter_return],
    )
    if return_store is None or _parse_imm(return_store.group(3)) not in (0x858, 2136, 88):
        return ["R84SET00 must own slot11"]
    if _parse_imm(return_store.group(3)) == 88:
        post_reg = return_store.group(2)
    else:
        post_address = next((index for index in range(max(0, setter_return - 5), setter_return)
                             if re.fullmatch(
                                 rf"add\s+(x\d+),\s*{re.escape(return_store.group(2))},\s*#(?:0x858|2136)",
                                 lines[index], re.IGNORECASE)), None)
        if post_address is None:
            return ["R84SET00 clean address is not derived from slot11"]
        post_reg = re.search(r"\badd\s+(x\d+),", lines[post_address], re.IGNORECASE).group(1)
    return_cleans = [index for index in range(setter_return + 1,
                                              min(setter_return + 4, len(lines)))
                     if re.fullmatch(rf"dc\s+civac,\s*{re.escape(post_reg)}",
                                     lines[index], re.IGNORECASE)]
    if (not return_cleans or return_cleans[0] + 1 >= len(lines)
            or not re.fullmatch(r"dsb\s+sy", lines[return_cleans[0] + 1], re.IGNORECASE)):
        return ["R84SET00 lacks a cache clean and DSB SY before later C stages"]
    if not (marker_index["PEINITEN"] < marker_index["PEINITRT"]
            < marker_index["ARMVMINI"] < marker_index["PANICINI"]
            < marker_index["CONSOLE"] < marker_index["R84MST00"] < late_setter):
        return ["R84 C-stage markers and late phase setter are out of order"]
    return []


def verify_r85_machine_startup(body: str, *, required: bool = False) -> list[str]:
    """Require ordered late-setter, machine_startup entry, and return witnesses."""
    base = verify_r84_arm_init_progress(body, required=required)
    if base:
        return base
    events = _marker_events(body, marker_map=R85_ARM_INIT_MARKERS)
    if not events and not required:
        return []
    by_name: dict[str, list[tuple[int, int]]] = {}
    for name, index, slot in events:
        by_name.setdefault(name, []).append((index, slot))
    for name in ("R85LRET0", "R85MSB00", "R85MACH0"):
        hits = by_name.get(name, [])
        expected_slot = R85_ARM_INIT_MARKERS[name][0]
        if len(hits) != 1 or hits[0][1] != expected_slot:
            return [f"R85 requires one {name} marker in slot{expected_slot}"]
    lines = body.splitlines()
    late_calls = [index for index, value in _phase_set_calls(body)
                  if value == R84_LATE_PHASE]
    startup_calls = [index for index, line in enumerate(lines)
                     if re.search(r"\bbl\s+_machine_startup\b", line)]
    if len(late_calls) != 1 or len(startup_calls) != 1:
        return ["R85 requires one R84LATE0 setter and one machine_startup call"]
    indexes = {name: values[0][0] for name, values in by_name.items()}
    if not (indexes["R84MST00"] < late_calls[0] < indexes["R85LRET0"]
            < indexes["R85MSB00"] < startup_calls[0] < indexes["R85MACH0"]):
        return ["R85 late-setter and machine_startup witnesses are out of order"]
    for name in ("R85LRET0", "R85MSB00", "R85MACH0"):
        index = indexes[name]
        clean = next((i for i in range(index + 1, min(index + 4, len(lines)))
                      if re.fullmatch(r"dc\s+civac,\s*x\d+", lines[i], re.IGNORECASE)), None)
        if clean is None or clean + 1 >= len(lines) \
                or not re.fullmatch(r"dsb\s+sy", lines[clean + 1], re.IGNORECASE):
            return [f"R85 {name} lacks DC CIVAC and DSB SY persistence"]
    return []


def _named_symbol_body(disassembly: str, symbol: str) -> str | None:
    marker = symbol + ":"
    start = disassembly.find(marker)
    if start < 0:
        return None
    body_start = start + len(marker)
    end_match = re.search(r"(?m)^_[A-Za-z0-9_$]+:$", disassembly[body_start:])
    end = body_start + end_match.start() if end_match else len(disassembly)
    return normalize_disassembly_body(disassembly[body_start:end])


def verify_r86_startup_disassembly(disassembly: str) -> list[str]:
    """Bind R86 function-entry and kernel-bootstrap return markers to real call order."""
    failures: list[str] = []
    machine_body = _named_symbol_body(disassembly, "_machine_startup")
    bootstrap_body = _named_symbol_body(disassembly, "_kernel_bootstrap")
    helper_body = _named_symbol_body(disassembly, "_native_phase_marker_external")
    if machine_body is None or bootstrap_body is None or helper_body is None:
        missing = [name for name, body in (
            ("_machine_startup", machine_body),
            ("_kernel_bootstrap", bootstrap_body),
            ("_native_phase_marker_external", helper_body),
        ) if body is None]
        return ["R86 linked image is missing marker owner(s): " + ", ".join(missing)]

    machine_events = _marker_helper_calls(machine_body)
    expected_machine = R86_STARTUP_MARKERS["R86MSE00"]
    machine_matches = [event for event in machine_events
                       if event[1:] == expected_machine]
    if len(machine_matches) != 1:
        failures.append(f"R86 requires one R86MSE00 slot14 call in machine_startup, found {len(machine_matches)}")
    phase_call = _call_index(machine_body.splitlines(), "y35a_bootstrap_phase_set")
    if machine_matches and phase_call is not None and machine_matches[0][0] >= phase_call:
        failures.append("R86MSE00 must execute before machine_startup's R81MCH00 phase setter")

    bootstrap_events = _marker_helper_calls(bootstrap_body)
    expected_names = (
        "R86KBE00", "R86VMB00", "R86CSI00", "R86VMI00",
        "R86CON00", "R86SCH00", "R86IPC00",
    )
    marker_indexes: dict[str, int] = {}
    for name in expected_names:
        expected = R86_STARTUP_MARKERS[name]
        matches = [event for event in bootstrap_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R86 requires one {name} slot{expected[0]} call in kernel_bootstrap, found {len(matches)}")
        else:
            marker_indexes[name] = matches[0][0]
    if len(marker_indexes) == len(expected_names):
        call_names = {
            "R86KBE00": None,
            "R86VMB00": "vm_mem_bootstrap",
            "R86CSI00": "cs_init",
            "R86VMI00": "vm_mem_init",
            "R86CON00": "console_init",
            "R86SCH00": "sched_init",
            "R86IPC00": "ipc_init",
        }
        for marker_name, call_name in call_names.items():
            if call_name is None:
                phase = _call_index(bootstrap_body.splitlines(), "y35a_bootstrap_phase_set")
                if phase is not None and marker_indexes[marker_name] >= phase:
                    failures.append("R86KBE00 must precede kernel_bootstrap's R81KBS00 phase setter")
                continue
            call = _call_index(bootstrap_body.splitlines(), call_name)
            if call is None or marker_indexes[marker_name] <= call:
                failures.append(f"{marker_name} must follow {call_name} returning")
        if any(marker_indexes[left] >= marker_indexes[right]
               for left, right in zip(expected_names, expected_names[1:])):
            failures.append("R86 kernel_bootstrap stage markers are out of order")

    helper_lines = helper_body.splitlines()
    scaled = next((re.fullmatch(r"add\s+(x\d+),\s*(x\d+),\s*w\d+,\s*uxtw\s*#3",
                                line, re.IGNORECASE) for line in helper_lines
                   if re.fullmatch(r"add\s+(x\d+),\s*(x\d+),\s*w\d+,\s*uxtw\s*#3",
                                   line, re.IGNORECASE)), None)
    indexed_base = scaled.group(1) if scaled else None
    clean_address = next((match for line in helper_lines
                          if indexed_base and (match := re.fullmatch(
                              r"add\s+(x\d+),\s*" + re.escape(indexed_base)
                              + r",\s*#(?:0x800|2048)", line, re.IGNORECASE))), None)
    store_address = next((match for line in helper_lines
                          if indexed_base and (match := re.fullmatch(
                              r"str\s+x1,\s*\[" + re.escape(indexed_base)
                              + r",\s*#(?:0x800|2048)\]", line, re.IGNORECASE))), None)
    clean_index = next((index for index, line in enumerate(helper_lines)
                        if clean_address and re.fullmatch(
                            rf"dc\s+civac,\s*{re.escape(clean_address.group(1))}",
                            line, re.IGNORECASE)), None)
    if (scaled is None or clean_address is None or store_address is None
            or clean_index is None or clean_index + 1 >= len(helper_lines)
            or not re.fullmatch(r"dsb\s+sy", helper_lines[clean_index + 1], re.IGNORECASE)):
        failures.append("R86 external marker helper must indexed-store the slot and persist it with DC CIVAC/DSB SY")
    return failures


def verify_r87_bootstrap_thread_disassembly(disassembly: str) -> list[str]:
    """Bind R87 startup/thread markers to their linked function call order."""
    failures: list[str] = []
    bootstrap_body = _named_symbol_body(disassembly, "_kernel_bootstrap")
    thread_body = _named_symbol_body(disassembly, "_kernel_bootstrap_thread")
    if bootstrap_body is None or thread_body is None:
        missing = [name for name, body in (
            ("_kernel_bootstrap", bootstrap_body),
            ("_kernel_bootstrap_thread", thread_body),
        ) if body is None]
        return ["R87 linked image is missing marker owner(s): " + ", ".join(missing)]
    bootstrap_events = _marker_helper_calls(bootstrap_body)
    bootstrap_names = (
        "R87PMAP0", "R87FREE0", "R87MACH0", "R87CLK00",
        "R87TASK0", "R87THRD0", "R87KTC00",
    )
    indexes: dict[str, int] = {}
    for name in bootstrap_names:
        expected = R87_STARTUP_MARKERS[name]
        matches = [event for event in bootstrap_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R87 requires one {name} slot{expected[0]} call in kernel_bootstrap, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    stage_calls = {
        "R87FREE0": "mapping_free_prime",
        "R87MACH0": "machine_init",
        "R87CLK00": "clock_init",
        "R87TASK0": "task_init",
        "R87THRD0": "thread_init",
        "R87KTC00": "kernel_thread_create",
    }
    for marker_name, call_name in stage_calls.items():
        if marker_name not in indexes:
            continue
        call = _call_index(bootstrap_body.splitlines(), call_name)
        if call is None or indexes[marker_name] <= call:
            failures.append(f"{marker_name} must follow {call_name} returning")
    if len(indexes) == len(bootstrap_names) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(bootstrap_names, bootstrap_names[1:])
    ):
        failures.append("R87 kernel_bootstrap markers are out of order")
    pmap_index = indexes.get("R87PMAP0")
    mapping_free_call = _call_index(bootstrap_body.splitlines(), "mapping_free_prime")
    if pmap_index is not None and mapping_free_call is not None and pmap_index >= mapping_free_call:
        failures.append("R87PMAP0 must precede mapping_free_prime")

    thread_events = _marker_helper_calls(thread_body)
    for name in ("R87KBT00", "R87CPU00"):
        expected = R87_STARTUP_MARKERS[name]
        matches = [event for event in thread_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R87 requires one {name} slot{expected[0]} call in kernel_bootstrap_thread, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    phase = _call_index(thread_body.splitlines(), "y35a_bootstrap_phase_set")
    if "R87KBT00" in indexes and phase is not None and indexes["R87KBT00"] >= phase:
        failures.append("R87KBT00 must precede kernel_bootstrap_thread's R81THRD0 phase setter")
    current_processor = _call_index(thread_body.splitlines(), "current_processor")
    if ("R87CPU00" in indexes
            and (current_processor is None or indexes["R87CPU00"] <= current_processor)):
        failures.append("R87CPU00 must follow current_processor returning")
    return failures


def verify_r88_bsd_iokit_disassembly(disassembly: str) -> list[str]:
    """Bind PRNG, scheduler, BSD, IOKit, and bsd_init cursor calls to order."""
    failures: list[str] = []
    body = _named_symbol_body(disassembly, "_kernel_bootstrap_thread")
    helper = _named_symbol_body(disassembly, "_native_phase_marker_external")
    if body is None or helper is None:
        missing = [name for name, value in (
            ("_kernel_bootstrap_thread", body),
            ("_native_phase_marker_external", helper),
        ) if value is None]
        return ["R88 linked image is missing marker owner(s): " + ", ".join(missing)]

    events = _marker_helper_calls(body)
    names = tuple(R88_STARTUP_MARKERS)
    indexes: dict[str, int] = {}
    for name in names:
        expected = R88_STARTUP_MARKERS[name]
        matches = [event for event in events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R88 requires one {name} slot{expected[0]} marker, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    if len(indexes) == len(names) and any(
        indexes[left] >= indexes[right] for left, right in zip(names, names[1:])
    ):
        failures.append("R88 bootstrap-thread markers are out of order")

    returned_after = {
        "R88IDLE0": "idle_thread_create",
        "R88SCHED": "sched_startup",
        "R88DAEM0": "thread_daemon_init",
        "R88CALL0": "thread_call_initialize",
        "R88BIND0": "thread_bind",
        "R88IPCT0": "ipc_thread_call_init",
        "R88MAP00": "mapping_adjust",
        "R88CLK00": "clock_service_create",
        "R88DEV00": "device_service_create",
        "R88BSDE0": "bsd_early_init",
        "R88LOCK0": "ml_lockdown_init",
        "R88IOKIT": "PE_init_iokit",
        "R88SPL00": "ml_set_interrupts_enabled",
        "R88SHR00": "vm_shared_region_init",
    }
    for name, function in returned_after.items():
        if name not in indexes:
            continue
        call = _call_index(body.splitlines(), function)
        if call is None or indexes[name] <= call:
            failures.append(f"{name} must follow {function} returning")
    prng_call = _call_index(body.splitlines(), "y35a_prng_bootstrap_init")
    if (prng_call is None or "R88PRBEG" not in indexes or "R88PRNOK" not in indexes
            or indexes["R88PRBEG"] >= prng_call or indexes["R88PRNOK"] <= prng_call):
        failures.append("R88PRBEG/R88PRNOK must bracket y35a_prng_bootstrap_init")
    bsd_init = _call_index(body.splitlines(), "bsd_init")
    if (bsd_init is None or "R88BSDC0" not in indexes or "R88BSDRT" not in indexes
            or indexes["R88BSDC0"] >= bsd_init or indexes["R88BSDRT"] <= bsd_init):
        failures.append("R88BSDC0/R88BSDRT must bracket the bsd_init call")

    helper_lines = helper.splitlines()
    slot_bound = next((re.fullmatch(r"cmp\s+w0,\s*#([0-9A-Fa-fx]+)",
                                    line, re.IGNORECASE)
                       for line in helper_lines
                       if re.fullmatch(r"cmp\s+w0,\s*#([0-9A-Fa-fx]+)",
                                       line, re.IGNORECASE)), None)
    if slot_bound is None or _parse_imm(slot_bound.group(1)) != 47:
        failures.append("R88 external marker helper must bound slots to the 48-word carrier")
    return failures


def verify_r89_bsd_init_disassembly(disassembly: str) -> list[str]:
    """Bind R89 bsd_init, root-mount, and launch-program markers to call order."""
    failures: list[str] = []
    bsd_body = _named_symbol_body(disassembly, "_bsd_init")
    task_body = _named_symbol_body(disassembly, "_bsdinit_task")
    if bsd_body is None or task_body is None:
        missing = [name for name, body in (
            ("_bsd_init", bsd_body), ("_bsdinit_task", task_body)
        ) if body is None]
        return ["R89 linked image is missing marker owner(s): " + ", ".join(missing)]

    bsd_events = _marker_helper_calls(bsd_body)
    bsd_names = tuple(name for name in R89_BSD_MARKERS
                      if name not in ("R89BTASK", "R89VMIL0", "R89INIT0", "R89LRET0"))
    indexes: dict[str, int] = {}
    for name in bsd_names:
        expected = R89_BSD_MARKERS[name]
        matches = [event for event in bsd_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R89 requires one {name} slot{expected[0]} marker in bsd_init, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]

    bsd_calls = {
        "R89THRTL": "throttle_init",
        "R89KMEM0": "kmeminit",
        "R89KAUT0": "kauth_init",
        "R89PROC0": "procinit",
        "R89TTY00": "tty_init",
        "R89DEVF0": "devfs_kernel_mount",
        "R89BSRET": "init_system_override",
    }
    for marker_name, function in bsd_calls.items():
        if marker_name not in indexes:
            continue
        call = _call_index(bsd_body.splitlines(), function)
        if call is None or indexes[marker_name] <= call:
            failures.append(f"{marker_name} must follow {function} returning")
    kauth_call = _call_index(bsd_body.splitlines(), "kauth_init")
    if "R89ARGS0" in indexes and (kauth_call is None or indexes["R89ARGS0"] >= kauth_call):
        failures.append("R89ARGS0 must follow the inline parse_bsd_args body and precede kauth_init")
    task_clear = _call_index(bsd_body.splitlines(), "task_clear_return_wait")
    if "R89UTBS0" in indexes and (task_clear is None or indexes["R89UTBS0"] <= task_clear):
        failures.append("R89UTBS0 must follow the inline bsd_utaskbootstrap body")
    throttle_call = _call_index(bsd_body.splitlines(), "throttle_init")
    if "R89BSDI0" in indexes and (throttle_call is None or indexes["R89BSDI0"] >= throttle_call):
        failures.append("R89BSDI0 must mark bsd_init body entry before throttle_init")
    mount_call = _call_index(bsd_body.splitlines(), "vfs_mountroot")
    if (mount_call is None or "R89MNTC0" not in indexes
            or indexes["R89MNTC0"] >= mount_call):
        failures.append("R89MNTC0 must precede vfs_mountroot")
    for name in ("R89MNTOK", "R89MNTER"):
        if name in indexes and (mount_call is None or indexes[name] <= mount_call):
            failures.append(f"{name} must follow vfs_mountroot returning")
    ordered_bsd_names = tuple(name for name in bsd_names
                              if name not in ("R89MNTOK", "R89MNTER"))
    if all(name in indexes for name in ordered_bsd_names) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(ordered_bsd_names, ordered_bsd_names[1:])
    ):
        failures.append("R89 bsd_init markers are out of order")

    task_events = _marker_helper_calls(task_body)
    task_names = ("R89BTASK", "R89VMIL0", "R89INIT0", "R89LRET0")
    for name in task_names:
        expected = R89_BSD_MARKERS[name]
        matches = [event for event in task_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R89 requires one {name} slot{expected[0]} marker in bsdinit_task, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    task_calls = {
        "R89BTASK": "current_proc",
        "R89VMIL0": "vm_init_before_launchd",
        "R89LRET0": "load_init_program",
    }
    for marker_name, function in task_calls.items():
        if marker_name not in indexes:
            continue
        call = _call_index(task_body.splitlines(), function)
        if call is None or indexes[marker_name] <= call:
            failures.append(f"{marker_name} must follow {function} returning")
    load_call = _call_index(task_body.splitlines(), "load_init_program")
    if "R89INIT0" in indexes and (load_call is None or indexes["R89INIT0"] >= load_call):
        failures.append("R89INIT0 must precede the load_init_program callsite")
    if all(name in indexes for name in task_names) and any(
        indexes[left] >= indexes[right] for left, right in zip(task_names, task_names[1:])
    ):
        failures.append("R89 bsdinit_task markers are out of order")
    return failures


def verify_r90_bsd_root_disassembly(disassembly: str) -> list[str]:
    """Bind R90's post-TTY BSD and root-mount markers to linked call order."""
    failures: list[str] = []
    body = _named_symbol_body(disassembly, "_bsd_init")
    task_body = _named_symbol_body(disassembly, "_bsdinit_task")
    if body is None or task_body is None:
        return ["R90 linked image is missing _bsd_init or _bsdinit_task"]
    task_names = ("R90BTASK", "R90VMIL0", "R90INIT0", "R90LRET0")
    bsd_names = tuple(name for name in R90_BSD_MARKERS if name not in task_names)
    events = _marker_helper_calls(body)
    indexes: dict[str, int] = {}
    for name in bsd_names:
        expected = R90_BSD_MARKERS[name]
        matches = [event for event in events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R90 requires one {name} slot{expected[0]} marker in bsd_init, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    task_events = _marker_helper_calls(task_body)
    for name in task_names:
        expected = R90_BSD_MARKERS[name]
        matches = [event for event in task_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R90 requires one {name} slot{expected[0]} marker in bsdinit_task, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    earlier_tty = [event[0] for event in _marker_helper_calls(body)
                   if event[1:] == R89_BSD_MARKERS["R89TTY00"]]
    if ("R90PNAM0" in indexes and len(earlier_tty) == 1
            and indexes["R90PNAM0"] <= earlier_tty[0]):
        failures.append("R90PNAM0 must follow the prior R89 tty-init checkpoint")
    calls_after = {
        "R90LOCK0": "file_lock_init",
        "R90SUBM0": "kmem_suballoc",
        "R90FPX00": "fpxlog_init",
        "R90VPG00": "vnode_pager_bootstrap",
        "R90TOD00": "inittodr",
        "R90DEVF0": "devfs_kernel_mount",
        "R90BSRET": "init_system_override",
    }
    for name, function in calls_after.items():
        if name not in indexes:
            continue
        call = _call_index(body.splitlines(), function)
        if call is None or indexes[name] <= call:
            failures.append(f"{name} must follow {function} returning")
    mount_call = _call_index(body.splitlines(), "vfs_mountroot")
    if (mount_call is None or "R90MNTC0" not in indexes
            or indexes["R90MNTC0"] >= mount_call):
        failures.append("R90MNTC0 must precede vfs_mountroot")
    for name in ("R90MNTOK", "R90MNTER"):
        if name in indexes and (mount_call is None or indexes[name] <= mount_call):
            failures.append(f"{name} must follow vfs_mountroot returning")
    if ("R90ROOT0" in indexes and "R90MNTOK" in indexes
            and indexes["R90ROOT0"] <= indexes["R90MNTOK"]):
        failures.append("R90ROOT0 must follow the successful root-mount marker")
    task_clear = _call_index(body.splitlines(), "task_clear_return_wait")
    if "R90UTBS0" in indexes and (task_clear is None or indexes["R90UTBS0"] <= task_clear):
        failures.append("R90UTBS0 must follow the inline bsd_utaskbootstrap body")
    ordered_bsd = tuple(name for name in bsd_names
                        if name not in ("R90MNTOK", "R90MNTER"))
    if all(name in indexes for name in ordered_bsd) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(ordered_bsd, ordered_bsd[1:])
    ):
        failures.append("R90 bsd_init markers are out of order")
    task_calls = {
        "R90BTASK": "current_proc",
        "R90VMIL0": "vm_init_before_launchd",
        "R90LRET0": "load_init_program",
    }
    for name, function in task_calls.items():
        if name not in indexes:
            continue
        call = _call_index(task_body.splitlines(), function)
        if call is None or indexes[name] <= call:
            failures.append(f"{name} must follow {function} returning")
    load_call = _call_index(task_body.splitlines(), "load_init_program")
    if "R90INIT0" in indexes and (load_call is None or indexes["R90INIT0"] >= load_call):
        failures.append("R90INIT0 must precede the load_init_program callsite")
    if all(name in indexes for name in task_names) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(task_names, task_names[1:])
    ):
        failures.append("R90 bsdinit_task markers are out of order")
    return failures


def verify_r91_bsd_cursor_disassembly(disassembly: str) -> list[str]:
    """Bind R91's single-slot cursor to the post-FPX BSD/root control flow."""
    failures: list[str] = []
    body = _named_symbol_body(disassembly, "_bsd_init")
    task_body = _named_symbol_body(disassembly, "_bsdinit_task")
    if body is None or task_body is None:
        return ["R91 linked image is missing _bsd_init or _bsdinit_task"]

    bsd_names = tuple(name for name in R91_PROGRESS_ORDER
                      if name not in R91_TASK_MARKERS)
    bsd_events = _marker_helper_calls(body)
    task_events = _marker_helper_calls(task_body)
    indexes: dict[str, int] = {}
    for name in bsd_names:
        expected = R91_BSD_MARKERS[name]
        matches = [event for event in bsd_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(
                f"R91 requires one {name} slot37 cursor marker in bsd_init, found {len(matches)}"
            )
        else:
            indexes[name] = matches[0][0]
    for name in R91_TASK_MARKERS:
        expected = R91_BSD_MARKERS[name]
        matches = [event for event in task_events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(
                f"R91 requires one {name} slot37 cursor marker in bsdinit_task, found {len(matches)}"
            )
        else:
            indexes[name] = matches[0][0]

    prior_fpx = [event[0] for event in bsd_events
                 if event[1:] == R90_BSD_MARKERS["R90FPX00"]]
    if ("R91BBEG0" in indexes and len(prior_fpx) == 1
            and indexes["R91BBEG0"] <= prior_fpx[0]):
        failures.append("R91BBEG0 must follow the R90 fpxlog_init return cursor")
    calls_after = {
        "R91BEND0": "bsd_bufferinit",
        "R91TIME0": "IOKitInitializeTime",
        "R91UBC00": "ubc_init",
        "R91VFS00": "vfsinit",
        "R91UUID0": "proc_uuid_policy_init",
        "R91MBIN0": "mbinit",
        "R91PIPE0": "pipeinit",
        "R91PTHR0": "pthread_init",
        "R91SLCT0": "select_waitq_init",
        "R91DOMN0": "domaininit",
        "R91ACCT0": "acct_init",
        "R91OSRS0": "os_reason_init",
        "R91NETDN": "mptcp_control_register",
        "R91VPGOK": "vnode_pager_bootstrap",
        "R91TOD00": "inittodr",
        # setconf is inlined in this XNU build; IOFindBSDRoot is its final
        # external call before the R91CONF0 post-return cursor.
        "R91CONF0": "IOFindBSDRoot",
        "R91ROOT0": "VFS_ROOT",
        "R91DEVF0": "devfs_kernel_mount",
        "R91TAIL0": "init_system_override",
    }
    for name, function in calls_after.items():
        if name not in indexes:
            continue
        call = _call_index(body.splitlines(), function)
        if call is None or indexes[name] <= call:
            failures.append(f"{name} must follow {function} returning")
    buffer_call = _call_index(body.splitlines(), "bsd_bufferinit")
    if ("R91BBEG0" in indexes and
            (buffer_call is None or indexes["R91BBEG0"] >= buffer_call)):
        failures.append("R91BBEG0 must precede bsd_bufferinit")

    vnode_call = _call_index(body.splitlines(), "vnode_pager_bootstrap")
    if ("R91VPPRE" in indexes and
            (vnode_call is None or indexes["R91VPPRE"] >= vnode_call)):
        failures.append("R91VPPRE must precede vnode_pager_bootstrap")
    mount_call = _call_index(body.splitlines(), "vfs_mountroot")
    if ("R91MNTC0" in indexes and
            (mount_call is None or indexes["R91MNTC0"] >= mount_call)):
        failures.append("R91MNTC0 must precede vfs_mountroot")
    for name in ("R91MNTOK", "R91MNTER"):
        if name in indexes and (mount_call is None or indexes[name] <= mount_call):
            failures.append(f"{name} must follow vfs_mountroot returning")

    ordered_bsd = tuple(name for name in bsd_names
                        if name not in ("R91MNTOK", "R91MNTER"))
    if all(name in indexes for name in ordered_bsd) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(ordered_bsd, ordered_bsd[1:])
    ):
        failures.append("R91 bsd_init cursor markers are out of order")

    task_calls = {
        "R91TASK0": "current_proc",
        "R91VMIL0": "vm_init_before_launchd",
        "R91LRET0": "load_init_program",
    }
    for name, function in task_calls.items():
        if name not in indexes:
            continue
        call = _call_index(task_body.splitlines(), function)
        if call is None or indexes[name] <= call:
            failures.append(f"{name} must follow {function} returning")
    load_call = _call_index(task_body.splitlines(), "load_init_program")
    if "R91INIT0" in indexes and (load_call is None or indexes["R91INIT0"] >= load_call):
        failures.append("R91INIT0 must precede the load_init_program callsite")
    if all(name in indexes for name in R91_TASK_MARKERS) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(R91_TASK_MARKERS, R91_TASK_MARKERS[1:])
    ):
        failures.append("R91 bsdinit_task cursor markers are out of order")
    return failures


def verify_r92_bsd_disassembly(disassembly: str) -> list[str]:
    """Verify R92 pre-call/return cursors around the three earliest opaque calls."""
    failures = verify_r91_bsd_cursor_disassembly(disassembly)
    body = _named_symbol_body(disassembly, "_bsd_init")
    if body is None:
        return failures + ["R92 linked image is missing _bsd_init"]
    lines = body.splitlines()
    events = _marker_helper_calls(body)
    indexes: dict[str, int] = {}
    for name, expected in R92_BSD_MARKERS.items():
        matches = [event for event in events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(f"R92 requires one {name} slot37 marker in bsd_init, found {len(matches)}")
        else:
            indexes[name] = matches[0][0]
    pairs = (
        ("R92TPRE0", "R92TOK00", "IOKitInitializeTime"),
        ("R92UPRE0", "R92UOK00", "ubc_init"),
        ("R92VPRE0", "R92VOK00", "vfsinit"),
    )
    for before, after, function in pairs:
        call = _call_index(lines, function)
        if call is None:
            failures.append(f"R92 missing {function} call")
            continue
        if before in indexes and indexes[before] >= call:
            failures.append(f"{before} must precede {function}")
        if after in indexes and indexes[after] <= call:
            failures.append(f"{after} must follow {function} returning")
    ordered = R92_PROGRESS_ORDER
    if all(name in indexes for name in ordered) and any(
        indexes[left] >= indexes[right] for left, right in zip(ordered, ordered[1:])
    ):
        failures.append("R92 pre-call/return cursor markers are out of order")
    prior = [event[0] for event in events
             if event[1:] == R91_BSD_MARKERS["R91BEND0"]]
    if ("R92TPRE0" in indexes and len(prior) == 1
            and indexes["R92TPRE0"] <= prior[0]):
        failures.append("R92TPRE0 must follow the R91 bsd_bufferinit return cursor")
    return failures


def verify_r93_iokit_time_disassembly(disassembly: str) -> list[str]:
    """Bind R93's nested cursor markers to the actual IOKit time-init calls."""
    failures = verify_r92_bsd_disassembly(disassembly)
    body = _named_symbol_body(disassembly, "_IOKitInitializeTime")
    if body is None:
        return failures + ["R93 linked image is missing _IOKitInitializeTime"]
    lines = body.splitlines()
    events = _marker_helper_calls(body)
    indexes: dict[str, int] = {}
    for name, expected in R93_BSD_MARKERS.items():
        matches = [event for event in events if event[1:] == expected]
        if len(matches) != 1:
            failures.append(
                f"R93 requires one {name} slot37 marker in _IOKitInitializeTime, found {len(matches)}"
            )
        else:
            indexes[name] = matches[0][0]

    def call_index_containing(fragment: str) -> int | None:
        return next((i for i, line in enumerate(lines)
                     if re.search(r"\bbl\s+[^\n]*" + re.escape(fragment), line)), None)

    pairs = (
        ("R93RPRE0", "R93ROK00", "resourceMatching"),
        ("R93WPRE0", "R93WOK00", "waitForService"),
        ("R93CPRE0", "R93COK00", "clock_initialize_calendar"),
    )
    for before, after, fragment in pairs:
        call = call_index_containing(fragment)
        if call is None:
            failures.append(f"R93 missing {fragment} call")
            continue
        if before in indexes and indexes[before] >= call:
            failures.append(f"{before} must precede {fragment}")
        if after in indexes and indexes[after] <= call:
            failures.append(f"{after} must follow {fragment} returning")
    if all(name in indexes for name in R93_PROGRESS_ORDER) and any(
        indexes[left] >= indexes[right]
        for left, right in zip(R93_PROGRESS_ORDER, R93_PROGRESS_ORDER[1:])
    ):
        failures.append("R93 IOKitInitializeTime cursor markers are out of order")
    return failures


def verify_r82_phase_setter(disassembly: str, symbol_address: int | None) -> list[str]:
    """Require the linked setter to publish the named global and clean it."""
    if symbol_address is None:
        return ["missing _y35a_bootstrap_phase symbol for R82 setter validation"]
    body = _named_symbol_body(disassembly, "_y35a_bootstrap_phase_set")
    if body is None:
        return ["missing _y35a_bootstrap_phase_set function body"]
    lines = body.splitlines()
    adrp = []
    add = []
    stores = []
    cleans = []
    barriers = []
    returns = []
    for i, line in enumerate(lines):
        page = re.search(r"\badrp\s+(x\d+),.*;\s*(0x[0-9a-fA-F]+)\s*$", line)
        if page:
            adrp.append((i, page.group(1), int(page.group(2), 16)))
        add_match = re.search(r"\badd\s+(x\d+), (x\d+), #([0-9A-Fa-fx]+)\b", line)
        if add_match:
            add.append((i, add_match.group(1), add_match.group(2), _parse_imm(add_match.group(3))))
        store = re.search(r"\bstr\s+x0, \[(x\d+)\]", line)
        if store:
            stores.append((i, store.group(1)))
        dc = re.search(r"\bdc\s+cvac, (x\d+)\b", line)
        if dc:
            cleans.append((i, dc.group(1)))
        if re.fullmatch(r"dsb\s+sy", line):
            barriers.append(i)
        if re.fullmatch(r"ret(?:\s+x\d+)?", line):
            returns.append(i)
    if not (len(adrp) == len(add) == len(stores) == len(cleans) == len(barriers) == len(returns) == 1):
        return ["R82 phase setter must contain one ADRP/ADD/store/CVAC/DSB/RET sequence"]
    ai, areg, page = adrp[0]
    di, dreg, sreg, offset = add[0]
    si, store_reg = stores[0]
    ci, clean_reg = cleans[0]
    bi, ri = barriers[0], returns[0]
    if not (ai < di < si < ci < bi < ri):
        return ["R82 phase setter publication/clean/barrier/return order is invalid"]
    if areg != dreg or dreg != sreg or sreg != store_reg or store_reg != clean_reg:
        return ["R82 phase setter does not use one address register for the bound field"]
    if page + offset != symbol_address:
        return ["R82 phase setter store address does not resolve to _y35a_bootstrap_phase"]
    if any(re.search(r"\bbl(?:r)?\s+", line) for line in lines):
        return ["R82 phase setter unexpectedly calls another function"]
    return []


def verify_handoff_disassembly(body: str) -> list[str]:
    failures: list[str] = []
    events = _marker_events(body, HANDOFF_MARKERS)
    by_name: dict[str, list[tuple[int, int]]] = {}
    for name, index, slot in events:
        by_name.setdefault(name, []).append((index, slot))
    for name, (expected_slot, _value) in HANDOFF_MARKERS.items():
        matches = by_name.get(name, [])
        if not matches:
            failures.append(f"missing {name} handoff marker")
            continue
        if len(matches) != 1:
            failures.append(f"{name} handoff marker appears {len(matches)} times")
            continue
        if matches[0][1] != expected_slot:
            failures.append(
                f"{name} handoff marker stores slot {matches[0][1]}, expected {expected_slot}"
            )
    if all(name in by_name for name in HANDOFF_MARKERS):
        for earlier, later in zip(HANDOFF_ORDER, HANDOFF_ORDER[1:]):
            if by_name[earlier][0][0] >= by_name[later][0][0]:
                failures.append(
                    f"handoff marker order is invalid: {earlier} before {later}"
                )
    failures.extend(verify_mapping_cursor_registers(body))
    failures.extend(verify_sctlr_isb_boundaries(body))
    return failures


def verify_mapping_cursor_registers(body: str) -> list[str]:
    """Ensure diagnostic markers never overwrite the live x14/x15 map cursors."""
    failures: list[str] = []
    lines = body.splitlines()
    events = _marker_events(body, HANDOFF_MARKERS)
    x14_init = [i for i, line in enumerate(lines)
                if re.search(r"\bmov\s+x14,\s*x22\b", line, re.IGNORECASE)]
    x15_init = [i for i, line in enumerate(lines)
                if re.search(r"\bmov\s+x15,\s*x23\b", line, re.IGNORECASE)]
    if len(x14_init) != 1 or len(x15_init) != 1:
        failures.append("bootstrap mapper must initialize x14=x22 and x15=x23 exactly once")
        return failures
    for name in MAPPING_CURSOR_MARKERS:
        matches = [event for event in events if event[0] == name]
        if len(matches) != 1:
            failures.append(f"expected one {name} mapping diagnostic, found {len(matches)}")
            continue
        _marker, index, slot = matches[0]
        expected_slot, value = HANDOFF_MARKERS[name]
        if index <= max(x14_init[0], x15_init[0]):
            failures.append(f"{name} precedes the live KVA/PA mapping cursor initialization")
        if slot != expected_slot:
            failures.append(f"{name} uses slot {slot}, expected {expected_slot}")
        store = re.fullmatch(
            r"\s*str\s+x16,\s*\[x20,\s*#(?:0x[0-9a-f]+|[0-9]+)\]",
            lines[index], re.IGNORECASE)
        if store is None:
            failures.append(f"{name} must store through x16 to the physical x20 carrier")
            continue
        offset = 0x800 + expected_slot * 8
        if _parse_imm(re.search(r"#(0x[0-9a-f]+|[0-9]+)", lines[index], re.IGNORECASE).group(1)) != offset:
            failures.append(f"{name} stores to the wrong carrier offset")
        if index < 4:
            failures.append(f"{name} has no complete x16 codeword materialization")
            continue
        value_reg = 0
        valid = True
        for pos, shift in zip(range(index - 4, index), (0, 16, 32, 48)):
            line = lines[pos].strip()
            mnemonic = "mov" if shift == 0 else "movk"
            pattern = (rf"{mnemonic}\s+x16,\s*#(0x[0-9a-f]+|[0-9]+)"
                       + ("" if shift == 0 else rf",\s*lsl\s*#{shift}"))
            immediate = re.fullmatch(pattern, line, re.IGNORECASE)
            if immediate is None:
                valid = False
                break
            half = _parse_imm(immediate.group(1))
            value_reg = half if shift == 0 else (value_reg & ~(0xffff << shift)) | (half << shift)
        if not valid or value_reg != value:
            failures.append(f"{name} does not materialize its codeword in scratch x16")
    return failures


def verify_sctlr_isb_boundaries(body: str) -> list[str]:
    """Verify the post-ISB V=P witness precedes the independent KVA alias store."""
    lines = [line.strip() for line in body.splitlines()]
    msr_indexes = [i for i, line in enumerate(lines)
                   if re.search(r"\bmsr\s+SCTLR_EL1\b", line, re.IGNORECASE)]
    if len(msr_indexes) != 1:
        return [f"expected one MSR SCTLR_EL1 instruction, found {len(msr_indexes)}"]
    msr = msr_indexes[0]
    failures: list[str] = []
    pre_store = [
        index for index, line in enumerate(lines)
        if re.fullmatch(r"str\s+x14,\s*\[x20,\s*#(?:0x880|2176)\]", line, re.IGNORECASE)
    ]
    sctpre_store = [
        index for index, line in enumerate(lines)
        if re.fullmatch(r"str\s+x14,\s*\[x20,\s*#(?:0xa10|2576)\]", line, re.IGNORECASE)
        and _codeword_materialization_matches(lines, index, "x14", int.from_bytes(b"SCTPRE00", "little"))
    ]
    if msr == 0:
        failures.append("MSR SCTLR_EL1 has no preceding physical witness")
    elif sctpre_store:
        sctpre = sctpre_store[0]
        if not (sctpre + 3 == msr - 1 and
                re.fullmatch(r"add\s+x14,\s*x20,\s*#(?:0xa10|2576)", lines[sctpre + 1], re.IGNORECASE) and
                re.fullmatch(r"dc\s+civac,\s*x14", lines[sctpre + 2], re.IGNORECASE) and
                re.fullmatch(r"dsb\s+sy", lines[sctpre + 3], re.IGNORECASE)):
            failures.append("SCTPRE00 physical witness is not the final cleaned store before MSR SCTLR_EL1")
    elif not pre_store or pre_store[0] != msr - 1:
        failures.append("PREMMU00 must be the final physical slot16 store before MSR SCTLR_EL1")
    pre_events = [event for event in _marker_events(body, HANDOFF_MARKERS)
                  if event[0] == "PREMMU00"]
    expected_pre_index = pre_store[0] if sctpre_store and pre_store else msr - 1
    if len(pre_events) != 1 or pre_events[0][1] != expected_pre_index or pre_events[0][2] != 16:
        failures.append("PREMMU00 current-generation marker is not adjacent to MSR SCTLR_EL1")
    if msr + 1 >= len(lines) or not re.fullmatch(r"isb(?:\s+sy)?", lines[msr + 1], re.IGNORECASE):
        failures.append("ISB must be the first instruction after MSR SCTLR_EL1")
        return failures

    rd_value = HANDOFF_MARKERS["SCTLRRD0"][1]
    rd_events = _marker_events(body, {"SCTLRRD0": (56, rd_value)})
    if msr + 2 >= len(lines) or not re.fullmatch(r"mrs\s+x11,\s*SCTLR_EL1", lines[msr + 2], re.IGNORECASE):
        failures.append("the first post-ISB instruction must read SCTLR_EL1 into x11")
        return failures

    mrs = msr + 2
    post_store = mrs + 1
    has_sctpost = (
        post_store + 7 < len(lines)
        and _codeword_materialization_matches(
            lines, post_store + 4, "x14", int.from_bytes(b"SCTPOST0", "little")
        )
        and re.fullmatch(r"str\s+x14,\s*\[x20,\s*#(?:0xa20|2592)\]", lines[post_store + 4], re.IGNORECASE)
        and re.fullmatch(r"add\s+x14,\s*x20,\s*#(?:0xa20|2592)", lines[post_store + 5], re.IGNORECASE)
        and re.fullmatch(r"dc\s+civac,\s*x14", lines[post_store + 6], re.IGNORECASE)
        and re.fullmatch(r"dsb\s+sy", lines[post_store + 7], re.IGNORECASE)
    )
    data_store = mrs + 9 if has_sctpost else mrs + 1
    expected = (
        (data_store, r"str\s+x11,\s*\[x20,\s*#(?:0x9c8|2504)\]"),
        (data_store + 1, r"mov\s+x13,\s*#(?:0x3652|13906)"),
        (data_store + 2, r"movk\s+x13,\s*#(?:0x4538|17720),\s*lsl\s*#16"),
        (data_store + 3, r"movk\s+x13,\s*#(?:0x5237|21047),\s*lsl\s*#32"),
        (data_store + 4, r"movk\s+x13,\s*#(?:0x3044|12356),\s*lsl\s*#48"),
        (data_store + 5, r"str\s+x13,\s*\[x20,\s*#(?:0x9c0|2496)\]"),
        (data_store + 6, r"dsb\s+sy"),
        (data_store + 7, r"add\s+x14,\s*x20,\s*#(?:0x9c0|2496)"),
        (data_store + 8, r"dc\s+civac,\s*x14"),
        (data_store + 9, r"add\s+x14,\s*x20,\s*#(?:0x9c8|2504)"),
        (data_store + 10, r"dc\s+civac,\s*x14"),
        (data_store + 11, r"dsb\s+sy"),
        (data_store + 12, r"add\s+x12,\s*x20,\s*x22"),
        (data_store + 13, r"sub\s+x12,\s*x12,\s*x23"),
        (data_store + 14, r"mov\s+x13,\s*#(?:0x3652|13906)"),
        (data_store + 15, r"movk\s+x13,\s*#(?:0x4538|17720),\s*lsl\s*#16"),
        (data_store + 16, r"movk\s+x13,\s*#(?:0x4b37|19255),\s*lsl\s*#32"),
        (data_store + 17, r"movk\s+x13,\s*#(?:0x3056|12374),\s*lsl\s*#48"),
        (data_store + 18, r"str\s+x13,\s*\[x12,\s*#(?:0x9f8|2552)\]"),
        (data_store + 19, r"add\s+x14,\s*x12,\s*#(?:0x9f8|2552)"),
        (data_store + 20, r"dsb\s+sy"),
        (data_store + 21, r"dc\s+civac,\s*x14"),
        (data_store + 22, r"dsb\s+sy"),
    )
    if len(rd_events) != 1 or rd_events[0][1] != data_store + 5 or rd_events[0][2] != 56:
        failures.append("R68E7RD0 must be stored in slot56 after the V=P SCTLR value")
    for index, pattern in expected:
        if index >= len(lines) or not re.fullmatch(pattern, lines[index], re.IGNORECASE):
            failures.append(f"post-SCTLR carrier sequence is invalid at instruction {index - msr}")
    kva_store = data_store + 18
    if kva_store < len(lines) and not _codeword_materialization_matches(
        lines, kva_store, "x13", KVA_ALIAS_MARKER[1]
    ):
        failures.append("KVAON000 does not materialize the R68E7 codeword immediately before the KVA store")
    return failures


def verify_post_mmu_carrier_layout(body: str) -> list[str]:
    """Compatibility name for the complete post-MMU boundary gate."""
    return verify_sctlr_isb_boundaries(body)


def verify_fault_publish_disassembly(body: str) -> list[str]:
    """Bind the R68E7 direct store, immediate load-back, and later table diagnostics."""
    failures: list[str] = []
    lines = [line.strip() for line in body.splitlines()]
    marker_names = ("FPGVA00", "FPBEFOR0", "FPSTOR00", "PUBLPR00", "PUBLPS00")
    stores: dict[str, int] = {}
    for name in marker_names:
        matches = _marker_slot_store_indexes(lines, name)
        if not matches:
            failures.append(f"missing physical {name} marker slot store")
            continue
        store = matches[0]
        stores[name] = store
        current_codeword_stores = [index for index in matches
                                   if _codeword_materialization_matches(
                                       lines, index, "x15", HANDOFF_MARKERS[name][1])]
        if not _codeword_materialization_matches(lines, store, "x15", HANDOFF_MARKERS[name][1]):
            failures.append(f"first store to the {name} slot does not carry the current codeword")
        if len(current_codeword_stores) != 1:
            failures.append(
                f"expected exactly one current {name} codeword/store pair, found {len(current_codeword_stores)}"
            )

    def matches(pattern: str) -> list[int]:
        return [index for index, line in enumerate(lines)
                if re.fullmatch(pattern, line, re.IGNORECASE)]

    global_stores = matches(r"str\s+x17,\s*\[x16\]")
    wrong_stores = matches(r"str\s+x17,\s*\[x9\]")
    pre_candidate_stores = matches(r"str\s+x9,\s*\[x20,\s*#(?:0x968|2408)\]")
    high_stores = {
        "global": matches(r"str\s+x16,\s*\[x20,\s*#(?:0x9d0|2512)\]"),
        "payload": matches(r"str\s+x17,\s*\[x20,\s*#(?:0x9d8|2520)\]"),
        "candidate": matches(r"str\s+x9,\s*\[x20,\s*#(?:0x9e0|2528)\]"),
    }
    if len(global_stores) != 1:
        failures.append(f"expected one direct MMU-off global store through x16, found {len(global_stores)}")
    if wrong_stores:
        failures.append("MMU-off ADRP target must be stored directly through x16; x9 double-translates it")
    if len(pre_candidate_stores) != 1:
        failures.append("expected one pre-store x9 diagnostic at slot45")
    for name, indexes in high_stores.items():
        if len(indexes) != 1:
            failures.append(f"expected one post-store {name} operand witness, found {len(indexes)}")

    physical_alias = matches(r"mov\s+x9,\s*x16")
    legacy_sub = matches(r"sub\s+x9,\s*x16,\s*x22")
    legacy_add = matches(r"add\s+x9,\s*x9,\s*x23")
    if len(physical_alias) != 1 or legacy_sub or legacy_add:
        failures.append("x9 diagnostic must copy the already-physical x16 alias; legacy double conversion is forbidden")

    loadbacks = matches(r"ldr\s+x14,\s*\[x16\]")
    required_names = set(marker_names)
    if (required_names.issubset(stores) and global_stores and pre_candidate_stores
            and physical_alias and all(high_stores.values())):
        fpgva = stores["FPGVA00"]
        before = stores["FPBEFOR0"]
        after = stores["FPSTOR00"]
        publish_start = stores["PUBLPR00"]
        publish_end = stores["PUBLPS00"]
        store = global_stores[0]
        capture = pre_candidate_stores[0]
        high = tuple(indexes[0] for indexes in high_stores.values())
        if len(loadbacks) != 1 or (loadbacks and loadbacks[0] != store + 1):
            failures.append("direct global store must be followed immediately by ldr x14,[x16]")
        readback_data = matches(r"str\s+x14,\s*\[x20,\s*#(?:0xa68|2664)\]")
        primary_readback_data = matches(r"str\s+x14,\s*\[x20,\s*#(?:0x850|2128)\]")
        if len(primary_readback_data) != 1 or (loadbacks and primary_readback_data
                and primary_readback_data[0] != loadbacks[0] + 1):
            failures.append("immediate global-pointer load-back must be saved to primary carrier slot10 at x20+0x850")
        if len(readback_data) != 1 or (primary_readback_data and readback_data
                and readback_data[0] != primary_readback_data[0] + 1):
            failures.append("auxiliary global-pointer read-back must immediately follow primary slot10")
        if not (fpgva < physical_alias[0] < capture < before < store
                < (loadbacks[0] if loadbacks else store) < after
                < publish_start < high[0] < high[1] < high[2] < publish_end):
            failures.append("fault-publish witnesses are not ordered around the direct store")
        if capture != physical_alias[0] + 1:
            failures.append("slot45 x9 candidate must be stored immediately after copying the physical x16 alias")
        if before != store - 1:
            failures.append("FPBEFOR0 must be the final instruction before the direct global store")
        if not (store < after and loadbacks and loadbacks[0] < after):
            failures.append("FPSTOR00 must follow the direct store and its immediate load-back")
        if publish_start != after + 5:
            failures.append("PUBLPR00 must immediately follow FPSTOR00")
        if high != (publish_start + 1, publish_start + 2, publish_start + 3):
            failures.append("post-store operands must be captured consecutively after PUBLPR00")
        if publish_end != publish_start + 8:
            failures.append("PUBLPS00 must immediately follow the three post-store operands")
        adrp = fpgva - 6
        if (adrp < 0 or not re.match(r"adrp\s+x16,", lines[adrp], re.IGNORECASE)
                or adrp + 1 >= len(lines)
                or not re.fullmatch(r"add\s+x16,\s*x16,\s*#(?:0x[0-9a-f]+|[0-9]+)",
                                    lines[adrp + 1], re.IGNORECASE)):
            failures.append("FPGVA00 must follow the adjacent PC-relative ADRP/ADD pair for x16")
        else:
            if any(re.match(r"(?:adrp|add|sub|mov|movk|ldr|ldur|and|orr|eor)\s+x16\b",
                            line, re.IGNORECASE)
                   for line in lines[adrp + 2:store]):
                failures.append("MMU-off ADRP result in x16 was modified before its global store")
        if any(re.match(r"(?:add|sub|mov|movk|ldr|ldur|and|orr|eor)\s+x9\b",
                        line, re.IGNORECASE)
               for line in lines[physical_alias[0] + 1:high[2]]):
            failures.append("captured x9 diagnostic was modified between pre-store calculation and readback")
        if _branch_instruction_indexes(lines, 0, publish_end + 1):
            failures.append("control-flow branch can skip the fault-publish sequence before its markers")
        if _control_transfer_indexes(lines, adrp, publish_end + 1):
            failures.append("control transfer can bypass the R68E7 fault-pointer store or its witnesses")
    return failures


def verify_r68e7_store_window_disassembly(body: str) -> list[str]:
    """Require durable same-instant operands and an immediately captured pointer read-back."""
    lines = [line.strip() for line in body.splitlines()]

    def matching(pattern: str) -> list[int]:
        return [i for i, line in enumerate(lines)
                if re.fullmatch(pattern, line, re.IGNORECASE)]

    offsets = {"x16": 0xa40, "x17": 0xa48, "x9": 0xa50, "x22": 0xa58, "x23": 0xa60}
    failures: list[str] = []
    stores = {}
    for register, offset in offsets.items():
        hits = matching(rf"str\s+{register},\s*\[x20,\s*#(?:0x{offset:x}|{offset})\]")
        if len(hits) != 1:
            failures.append(f"expected one durable R68E7 {register} snapshot at x20+{offset:#x}, found {len(hits)}")
        else:
            stores[register] = hits[0]
    global_stores = matching(r"str\s+x17,\s*\[x16\]")
    loadbacks = matching(r"ldr\s+x14,\s*\[x16\]")
    readback_stores = matching(r"str\s+x14,\s*\[x20,\s*#(?:0xa68|2664)\]")
    markers = {
        "PUBLIN00": (0xa70, R68E7_STORE_MARKERS["PUBLIN00"][1]),
        "PUBLRD00": (0xa78, R68E7_STORE_MARKERS["PUBLRD00"][1]),
    }
    marker_stores = {}
    for name, (offset, value) in markers.items():
        hits = matching(rf"str\s+x15,\s*\[x20,\s*#(?:0x{offset:x}|{offset})\]")
        good = [i for i in hits if _codeword_materialization_matches(lines, i, "x15", value)]
        if len(good) != 1:
            failures.append(f"expected one current {name} generation marker in the R68E7 store window")
        else:
            marker_stores[name] = good[0]

    if len(global_stores) != 1:
        failures.append(f"expected one direct [x16] pointer publication, found {len(global_stores)}")
    if len(loadbacks) != 1 or (global_stores and loadbacks and loadbacks[0] != global_stores[0] + 1):
        failures.append("R68E7 requires the pointer load-back as the very next instruction after str x17,[x16]")
    low_readback_stores = matching(r"str\s+x14,\s*\[x20,\s*#(?:0x850|2128)\]")
    if (len(low_readback_stores) != 1 or (loadbacks and low_readback_stores
            and low_readback_stores[0] != loadbacks[0] + 1)):
        failures.append("the immediate pointer load-back must be copied to primary carrier slot10 at x20+0x850")
    if len(readback_stores) != 1 or (low_readback_stores and readback_stores
            and readback_stores[0] != low_readback_stores[0] + 1):
        failures.append("the auxiliary +0xa68 pointer read-back must immediately follow primary slot10")
    if stores and marker_stores:
        snapshot = marker_stores.get("PUBLIN00")
        readback_marker = marker_stores.get("PUBLRD00")
        if snapshot is not None and not all(index < snapshot for index in stores.values()):
            failures.append("PUBLIN00 must follow the x16/x17/x9/x22/x23 snapshot stores")
        if snapshot is not None and global_stores and snapshot >= global_stores[0]:
            failures.append("PUBLIN00 must be durable before the direct target store")
        if readback_marker is not None and low_readback_stores and readback_marker <= low_readback_stores[0]:
            failures.append("PUBLRD00 must follow the immediate pointer read-back capture")
        if readback_marker is not None and global_stores and readback_marker <= global_stores[0]:
            failures.append("PUBLRD00 cannot precede the direct target store")

    first = min(stores.values(), default=-1)
    readback_marker_store = marker_stores.get("PUBLRD00", -1)
    last = min(readback_marker_store + 4, len(lines) - 1) if readback_marker_store >= 0 else -1
    if first >= 0 and last >= first:
        witness_bases = [i for i in range(first, last + 1)
                         if re.fullmatch(r"add\s+x14,\s*x20,\s*#(?:0xa40|2624)",
                                         lines[i], re.IGNORECASE)]
        witness_cleans = [i for i in range(first, last + 1)
                          if re.fullmatch(r"dc\s+civac,\s*x14", lines[i], re.IGNORECASE)]
        target_cleans = [i for i in range(first, last + 1)
                         if re.fullmatch(r"dc\s+civac,\s*x16", lines[i], re.IGNORECASE)]
        if len(witness_bases) != 3 or len(witness_cleans) != 3:
            failures.append("R68E7 must clean the durable witness cache line before and after each marker publication")
        if len(target_cleans) != 1:
            failures.append("R68E7 must clean the direct global target after its load-back")
        if (len(witness_cleans) == 3 and len(target_cleans) == 1
                and len(global_stores) == 1 and loadbacks and low_readback_stores
                and marker_stores.get("PUBLIN00") is not None
                and marker_stores.get("PUBLRD00") is not None):
            ordered = (witness_cleans[0] < marker_stores["PUBLIN00"]
                       < witness_cleans[1] < global_stores[0]
                       < low_readback_stores[0] < target_cleans[0]
                       < marker_stores["PUBLRD00"] < witness_cleans[2])
            if not ordered:
                failures.append("R68E7 cache-clean barriers and durable markers are out of order")
        for i in range(first, last + 1):
            if re.fullmatch(r"dc\s+civac,\s*x(?:14|16)", lines[i], re.IGNORECASE):
                before = lines[max(first, i - 2):i]
                after = lines[i + 1:i + 2]
                if not any(re.fullmatch(r"dsb\s+sy", line, re.IGNORECASE) for line in before) or not after or not re.fullmatch(r"dsb\s+sy", after[0], re.IGNORECASE):
                    failures.append("each R68E7 publication cache clean must be bracketed by DSB SY")
                    break
    if global_stores and marker_stores.get("PUBLIN00") is not None and marker_stores.get("PUBLRD00") is not None:
        if _control_transfer_indexes(lines, marker_stores["PUBLIN00"], marker_stores["PUBLRD00"] + 1):
            failures.append("control transfer can bypass R68E7 publication or its pointer load-back")
    return failures


def verify_r68e7_low_carrier_disassembly(body: str) -> list[str]:
    """Require decisive register evidence and the staged slot-11 marker in early-fault carrier."""
    lines = [line.strip() for line in body.splitlines()]

    def matching(pattern: str) -> list[int]:
        return [i for i, line in enumerate(lines)
                if re.fullmatch(pattern, line, re.IGNORECASE)]

    stores = {}
    failures: list[str] = []
    for register, offset in R68E7_LOW_STORE_OFFSETS.items():
        pattern = rf"str\s+{'x14' if register == 'global_readback' else register},\s*\[x20,\s*#(?:0x{offset:x}|{offset})\]"
        hits = matching(pattern)
        if len(hits) != 1:
            failures.append(f"expected one primary retained-carrier {register} store at x20+{offset:#x}, found {len(hits)}")
        else:
            stores[register] = hits[0]

    hits = matching(r"str\s+x15,\s*\[x20,\s*#(?:0x858|2136)\]")
    markers = {}
    for i in hits:
        for value, label in R68E7_LOW_STAGE_MARKERS.items():
            if _codeword_materialization_matches(lines, i, "x15", value):
                markers[label] = i
    if len(hits) != 2 or set(markers) != {"snapshot-complete", "store-readback-complete"}:
        failures.append("slot11 must carry exactly one R68E7IN0 then one R68E7RB0 marker")

    direct_stores = matching(r"str\s+x17,\s*\[x16\]")
    loadbacks = matching(r"ldr\s+x14,\s*\[x16\]")
    target_cleans = matching(r"dc\s+civac,\s*x16")
    if len(direct_stores) != 1:
        failures.append(f"expected one direct MMU-off global store, found {len(direct_stores)}")
    if len(loadbacks) != 1 or (direct_stores and loadbacks and loadbacks[0] != direct_stores[0] + 1):
        failures.append("low-carrier experiment must load x16 immediately after the direct global store")
    if len(target_cleans) != 1:
        failures.append("low-carrier experiment must clean the direct global target exactly once")

    snapshot_marker = markers.get("snapshot-complete")
    readback_marker = markers.get("store-readback-complete")

    def clean_sequence_indexes(offset: int, start: int, stop: int) -> list[int]:
        immediate = rf"(?:0x{offset:x}|{offset})"
        patterns = (
            rf"add\s+x14,\s*x20,\s*#{immediate}",
            r"dsb\s+sy",
            r"dc\s+civac,\s*x14",
            r"dsb\s+sy",
        )
        found = []
        for index in range(max(0, start), min(stop, len(lines)) - len(patterns) + 1):
            if all(re.fullmatch(pattern, lines[index + delta], re.IGNORECASE)
                   for delta, pattern in enumerate(patterns)):
                found.append(index)
        return found

    def require_one_clean(offset: int, start: int, stop: int, boundary: str) -> None:
        found = clean_sequence_indexes(offset, start, stop)
        if len(found) != 1:
            failures.append(
                f"R68E7 low carrier must clean x20+{offset:#x} exactly once with DSB SY "
                f"{boundary}; found {len(found)}"
            )

    if stores and snapshot_marker is not None:
        if not all(stores[name] < snapshot_marker for name in ("x16", "x17", "x9", "x22", "x23")):
            failures.append("slot11 snapshot-complete marker must follow all five live register stores")
        if "x23" in stores:
            require_one_clean(0x800, stores["x23"] + 1, snapshot_marker,
                              "before snapshot-complete")
            require_one_clean(0x840, stores["x23"] + 1, snapshot_marker,
                              "before snapshot-complete")
        if direct_stores and snapshot_marker >= direct_stores[0]:
            failures.append("slot11 snapshot-complete marker must precede the direct global store")
        if direct_stores:
            require_one_clean(0x840, snapshot_marker + 1, direct_stores[0],
                              "after snapshot-complete")
    if loadbacks and stores and stores.get("global_readback") is not None:
        if stores["global_readback"] != loadbacks[0] + 1:
            failures.append("immediate global read-back must be persisted in low-carrier slot10")
    if readback_marker is not None:
        if (stores.get("global_readback") is None
                or readback_marker <= stores["global_readback"]
                or not target_cleans or readback_marker <= target_cleans[0]):
            failures.append("slot11 store-readback-complete marker must follow low slot10 and target cache clean")
        if stores.get("global_readback") is not None:
            require_one_clean(0x800, stores["global_readback"] + 1, readback_marker,
                              "before store-readback-complete")
            require_one_clean(0x840, stores["global_readback"] + 1, readback_marker,
                              "before store-readback-complete")
        require_one_clean(0x840, readback_marker + 1, len(lines),
                          "after store-readback-complete")
    if snapshot_marker is not None and readback_marker is not None:
        if readback_marker <= snapshot_marker:
            failures.append("slot11 R68E7 stage markers must preserve snapshot-before-readback order")
        if _control_transfer_indexes(lines, snapshot_marker, readback_marker + 1):
            failures.append("control transfer can bypass the low-carrier store/read-back sequence")
    return failures

def verify_carrier_slot_contract() -> list[str]:
    failures = []
    loop_slots = {
        name: HANDOFF_MARKERS[name][0]
        for name in ("INVPREF0", "INVONE00")
    }
    mapping_slots = {
        name: HANDOFF_MARKERS[name][0]
        for name in ("VPPRE000", "VPCALL00", "KVPRE000", "KVCALL00")
    }
    if set(loop_slots.values()) & set(mapping_slots.values()):
        failures.append("loop-state and mapping carriers share a slot")
    if len(mapping_slots.values()) != len(set(mapping_slots.values())):
        failures.append("mapping carriers are not assigned unique slots")
    if HANDOFF_MARKERS["HDRLOAD0"][0] in loop_slots.values() or HANDOFF_MARKERS["HDRADJ00"][0] in loop_slots.values():
        failures.append("header-adjust markers reuse loop-state slots")
    slot = HANDOFF_MARKERS["SCTLRRD0"][0]
    if slot != 56 or SCTLR_VALUE_SLOT != slot + 1:
        failures.append("SCTLRRD0 and the raw SCTLR_EL1 value must use adjacent slots 56/57")
    other_slots = [slot_value for _name, (slot_value, _value) in PHASE_MARKERS.items()
                   if slot_value == slot]
    other_slots += [slot_value for name, (slot_value, _value) in HANDOFF_MARKERS.items()
                    if name != "SCTLRRD0" and slot_value == slot]
    if other_slots:
        failures.append(f"SCTLRRD0 carrier slot {slot} aliases another marker")
    if slot in RAW_LOOP_STATE_SLOTS or SCTLR_VALUE_SLOT in RAW_LOOP_STATE_SLOTS:
        failures.append("SCTLR readback carrier aliases raw loop state")
    if (SCTLR_VALUE_SLOT + 1) * 8 > DIAGNOSTIC_CARRIER_BYTES:
        failures.append("raw SCTLR_EL1 value exceeds the cleared diagnostic carrier")
    publish_slots = (58, 59, 60, HANDOFF_MARKERS["PUBLPR00"][0], HANDOFF_MARKERS["PUBLPS00"][0])
    if publish_slots != (58, 59, 60, 61, 62):
        failures.append("fault-pointer publication witnesses must occupy slots 58..62")
    if (FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT != HANDOFF_MARKERS["LRADD000"][0]
            or FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT != HANDOFF_MARKERS["PTSHIFT0"][0]):
        failures.append("pre-store x9 candidate must use the temporal slot45 carrier")
    all_slots = [slot for slot, _value in (*PHASE_MARKERS.values(), *HANDOFF_MARKERS.values())]
    if tuple((offset - 0x800) // 8 for offset in R68E7_LOW_STORE_OFFSETS.values()) != (5, 6, 7, 8, 9, 10):
        failures.append("R68E7 low-carrier snapshot must use temporal slots5..10 in register order")
    if R68E7_LOW_STAGE_SLOT != 11 or R68E7_LOW_STAGE_SLOT in all_slots:
        failures.append("R68E7 snapshot/read-back stage marker must own unused slot11")
    phase_slots = {name: slot for name, (slot, _value) in PHASE_MARKERS.items()}
    expected_phase_slots = {
        "ARMINITE": 5, "PEINITEN": 6, "PEINITRT": 7,
        "ARMVMINI": 8, "PANICINI": 9, "CONSOLE": 10,
    }
    if any(phase_slots.get(name) != slot for name, slot in expected_phase_slots.items()):
        failures.append("R68E7 low-carrier temporal fields must align with the existing C-phase marker slots")
    if ENTRY_PATH_MARKERS["FIRST_CPU"][0] != ENTRY_PATH_WINDOW_BASE_SLOT:
        failures.append("first-CPU marker is not at the entry-path-window base")
    if KVA_ALIAS_MARKER[0] != 63 or KVA_ALIAS_MARKER[0] in all_slots:
        failures.append("KVAON000 must exclusively use fault-publish slot63")
    if R68E7_STORE_WINDOW_BYTES != 8 * len(R68E7_STORE_VALUE_OFFSETS):
        failures.append("R68E7 durable operand window must contain exactly eight u64 values")
    if len(set(R68E7_STORE_VALUE_OFFSETS.values())) != len(R68E7_STORE_VALUE_OFFSETS):
        failures.append("R68E7 durable operand fields overlap")
    if ENTRY_PATH_WINDOW_BASE_SLOT + 2 != DIAGNOSTIC_CARRIER_BYTES // 8:
        failures.append("entry-path diagnostic echo must occupy slot65 within the cleared carrier")
    for name in ("PUBLPR00", "PUBLPS00"):
        slot = HANDOFF_MARKERS[name][0]
        if all_slots.count(slot) != 1:
            failures.append(f"{name} carrier slot {slot} aliases another marker")
    return failures


def _call_index(lines: list[str], symbol: str, occurrence: int = 0) -> int | None:
    seen = 0
    pattern = re.compile(rf"\bbl\s+_{re.escape(symbol)}\b")
    for index, line in enumerate(lines):
        if pattern.search(line):
            if seen == occurrence:
                return index
            seen += 1
    return None


def verify_disassembly(
    body: str, *, require_r82_cursor: bool = False,
    require_r83_cursor: bool = False, require_r84_cursor: bool = False,
    require_r85_cursor: bool = False,
) -> list[str]:
    failures: list[str] = []
    lines = body.splitlines()
    events = _marker_events(body)
    r83_events = _marker_events(
        body, marker_map={"R83CIN00": (5, R83_C_ENTRY_MARKER)}
    )
    r84_events = _marker_events(body, marker_map=R84_PHASE_MARKERS)
    r85_events = _marker_events(body, marker_map=R85_ARM_INIT_MARKERS)
    by_name: dict[str, list[tuple[int, int]]] = {}
    for name, index, slot in events:
        by_name.setdefault(name, []).append((index, slot))
    for name, index, slot in r83_events:
        by_name.setdefault(name, []).append((index, slot))
    for name, index, slot in (r85_events if r85_events else r84_events):
        by_name.setdefault(name, []).append((index, slot))

    for name, (expected_slot, _value) in PHASE_MARKERS.items():
        if name in R84_VERSIONED_PHASE_NAMES and (
            require_r84_cursor or require_r85_cursor or r84_events or r85_events
        ):
            continue
        if name == "ARMINITE" and (require_r83_cursor or r83_events):
            continue
        matches = by_name.get(name, [])
        if not matches:
            failures.append(f"missing {name} marker constant/store")
            continue
        if len(matches) != 1:
            failures.append(f"{name} marker appears {len(matches)} times")
            continue
        if matches[0][1] != expected_slot:
            failures.append(
                f"{name} marker stores slot {matches[0][1]}, expected {expected_slot}"
            )

    indices = {name: matches[0][0] for name, matches in by_name.items() if matches}
    for earlier, later in zip(PHASE_ORDER, PHASE_ORDER[1:]):
        if earlier in indices and later in indices and indices[earlier] >= indices[later]:
            failures.append(f"phase marker order is invalid: {earlier} before {later}")

    first_pe = _call_index(lines, "PE_init_platform", 0)
    arm_vm = _call_index(lines, "arm_vm_init")
    panic = _call_index(lines, "panic_init")
    console = _call_index(lines, "PE_create_console")
    calls = {
        "PEINITEN": first_pe,
        "PEINITRT": first_pe,
        "ARMVMINI": arm_vm,
        "PANICINI": panic,
        "CONSOLE": console,
    }
    for name, call in calls.items():
        if call is None:
            failures.append(f"missing {name} boundary call")
            continue
        marker_index = indices.get(name)
        if marker_index is None:
            continue
        if name in ("PEINITEN",):
            if marker_index >= call:
                failures.append(f"{name} marker is not before first PE_init_platform")
        else:
            if marker_index <= call:
                failures.append(f"{name} marker is not after its boundary call")
    if ("ARMINITE" in indices and first_pe is not None
            and indices["ARMINITE"] >= first_pe):
        failures.append("ARMINITE marker is not before first PE_init_platform")
    has_r82_cursor = any(value == R82_ARM_ENTRY_PHASE for _, value in _phase_set_calls(body))
    if require_r82_cursor and (r83_events or r84_events or r85_events):
        failures.append("R82 arm-init contract cannot use the R83CIN00 slot-5 marker")
        failures.extend(verify_r82_arm_init_cursor(body, required=True))
    elif require_r83_cursor and (r84_events or r85_events):
        failures.append("R83 arm-init contract cannot use R84 generation markers")
        failures.extend(verify_r83_arm_init_cursor(body, required=True))
    elif require_r85_cursor or r85_events:
        failures.extend(verify_r85_machine_startup(body, required=require_r85_cursor))
    elif require_r84_cursor or r84_events:
        failures.extend(verify_r84_arm_init_progress(body, required=require_r84_cursor))
    elif require_r83_cursor or r83_events:
        failures.extend(verify_r83_arm_init_cursor(
            body, required=require_r83_cursor,
        ))
    else:
        failures.extend(verify_r82_arm_init_cursor(
            body, required=require_r82_cursor or has_r82_cursor,
        ))
    return failures


def verify_manifest(
    kernel: Path, manifest: Path | None, *, require_r68e7: bool = False,
    require_r83: bool = False, require_r84: bool = False,
) -> list[str]:
    if manifest is None:
        return []
    data = json.loads(manifest.read_text())
    actual = hashlib.sha256(kernel.read_bytes()).hexdigest()
    failures = []
    failures.extend(verify_carrier_slot_contract())
    if data.get("kernel_sha256") != actual:
        failures.append(
            f"manifest kernel_sha256 {data.get('kernel_sha256')} != actual {actual}"
        )
    if require_r68e7:
        try:
            kernel_layout = parse_macho(kernel.read_bytes())
            expected_bases = {
                "kernel_virtual_base": int(kernel_layout["base"]),
                "kernel_physical_base": physical_base_for(int(kernel_layout["base"])),
            }
        except (KeyError, OSError, TypeError, ValueError) as exc:
            failures.append(f"could not derive expected R68E7 BootArgs bases from Mach-O: {exc}")
        else:
            for field, expected in expected_bases.items():
                try:
                    observed = int(data[field], 0)
                except (KeyError, TypeError, ValueError):
                    failures.append(f"R68E7 readback manifest is missing valid {field}")
                    continue
                if observed != expected:
                    failures.append(
                        f"R68E7 manifest {field} {observed:#x} does not match the kernel "
                        f"base {expected:#x}"
                    )
    if not isinstance(data.get("records"), list):
        return ["--manifest must be a readback manifest with a records array"]
    if data.get("transport_mode") not in ("full-readback", "minimal-boundary"):
        return ["readback manifest has no supported transport_mode"]
    failures.extend(verify_transport_record_layout(data))
    records = {record["name"]: record for record in data["records"]}
    named_records = [record.get("name") for record in data["records"]]
    if len(named_records) != len(set(named_records)):
        failures.append("readback manifest record names must be unique")
    if require_r83 or require_r84:
        entry_records = [record for record in data["records"]
                         if record.get("name") == ENTRY_PATH_WINDOW_RECORD]
        if len(entry_records) != 1:
            failures.append(
                f"R83/R84 manifest requires exactly one {ENTRY_PATH_WINDOW_RECORD} record"
            )
        phase_records = [record for record in data["records"]
                         if record.get("name") == "_y35a_bootstrap_phase"]
        if len(phase_records) != 1:
            failures.append("R83/R84 manifest requires exactly one _y35a_bootstrap_phase record")
        else:
            try:
                phase_width = int(phase_records[0]["field_bytes"])
                phase_size = int(phase_records[0]["size"])
            except (KeyError, TypeError, ValueError):
                failures.append("R83/R84 phase record has invalid field width or copy-window size")
            else:
                if phase_width != 8 or phase_size != 16:
                    failures.append("R83/R84 phase record must be an 8-byte field in a 16-byte window")
    phase_symbol = "_y35a_bootstrap_phase"
    phase_record = records.get(phase_symbol)
    image_has_phase_symbol = phase_symbol.encode() in kernel.read_bytes()
    if phase_record is not None or image_has_phase_symbol:
        try:
            linked_symbols = nm_symbol_addresses(kernel)
        except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
            failures.append(f"could not read linked symbols for named-field validation: {exc}")
            linked_symbols = {}
    else:
        linked_symbols = {}
    if phase_symbol in linked_symbols:
        if phase_record is None:
            failures.append("kernel contains _y35a_bootstrap_phase but manifest has no named phase record")
        else:
            try:
                phase_size = int(phase_record["size"])
                phase_width = int(phase_record["field_bytes"])
                phase_physical = int(phase_record["physical"], 0)
                virtual_base = int(data["kernel_virtual_base"], 0)
                physical_base = int(data["kernel_physical_base"], 0)
                kernel_base = int(parse_macho(kernel.read_bytes())["base"])
                expected_phase_physical = physical_base + linked_symbols[phase_symbol] - kernel_base
            except (KeyError, TypeError, ValueError, OSError):
                failures.append("named phase record lacks valid geometry or 8-byte field width")
            else:
                if phase_width != 8 or phase_size != 16:
                    failures.append("named phase record must declare field_bytes=8 and a 16-byte copy window")
                if phase_physical != expected_phase_physical:
                    failures.append(
                        f"named phase record physical {phase_physical:#x} does not match linked symbol "
                        f"{expected_phase_physical:#x}"
                    )
                if virtual_base != kernel_base:
                    failures.append("readback kernel_virtual_base disagrees with linked Mach-O")
    elif phase_record is not None:
        failures.append("manifest contains _y35a_bootstrap_phase but linked kernel symbol is absent")
    physical_ranges = []
    for record in data["records"]:
        try:
            record_name = str(record["name"])
            record_base = int(record["physical"], 0)
            record_size = int(record["size"])
            if record_size <= 0:
                raise ValueError("non-positive range size")
        except (KeyError, TypeError, ValueError):
            failures.append(
                f"readback manifest record has invalid physical range: {record.get('name', '<unnamed>')}"
            )
            continue
        if record_name in DIAGNOSTIC_WINDOW_RECORDS:
            physical_ranges.append((record_name, record_base, record_base + record_size))
    for index, (left_name, left_start, left_end) in enumerate(physical_ranges):
        for right_name, right_start, right_end in physical_ranges[index + 1:]:
            if left_start < right_end and right_start < left_end:
                failures.append(
                    f"readback physical ranges alias: {left_name} overlaps {right_name}"
                )
    early = records.get("early-fault-record")
    if early is not None:
        size = int(early.get("size", 0))
        if size != EARLY_RECORD_BYTES:
            failures.append(f"manifest early-fault-record size is {size}, not {EARLY_RECORD_BYTES}")
        if data["transport_mode"] == "minimal-boundary":
            if int(early.get("report_offset", -1)) != 0x100:
                failures.append("minimal-boundary early-fault-record report_offset is not 0x100")
        elif int(early.get("offset", -1)) != 64:
            failures.append("full-readback early-fault-record offset is not 64")
        same_physical = [
            record for record in data["records"]
            if record.get("physical") == early.get("physical")
        ]
        if len(same_physical) != 1:
            failures.append("readback manifest must contain one canonical carrier record")
        try:
            early_physical = int(early["physical"], 0)
        except (KeyError, TypeError, ValueError):
            failures.append("early-fault-record has no valid physical base")
            early_physical = None
        handoff_records = [
            record for record in data["records"]
            if record.get("name") == HANDOFF_WITNESS_RECORD
        ]
        if len(handoff_records) != 1:
            failures.append(
                f"manifest must contain one {HANDOFF_WITNESS_RECORD} record"
            )
        elif early_physical is not None:
            handoff = handoff_records[0]
            expected_physical = early_physical + HANDOFF_MARKERS["SCTLRRD0"][0] * 8
            try:
                handoff_physical = int(handoff["physical"], 0)
                handoff_size = int(handoff["size"])
            except (KeyError, TypeError, ValueError):
                failures.append("handoff-witness has invalid physical range")
            else:
                if handoff_physical != expected_physical:
                    failures.append(
                        f"handoff-witness physical {handoff_physical:#x} does not cover "
                        f"slots 56/57 at {expected_physical:#x}"
                    )
                if handoff_size != HANDOFF_WITNESS_BYTES:
                    failures.append(
                        f"handoff-witness size is {handoff_size}, not {HANDOFF_WITNESS_BYTES}"
                    )
            try:
                offset_key = (
                    "report_offset"
                    if data["transport_mode"] == "minimal-boundary"
                    else "offset"
                )
                handoff_offset = int(handoff[offset_key])
                if handoff_offset < 0:
                    raise ValueError("negative offset")
                if data["transport_mode"] == "minimal-boundary":
                    report_bytes = int(data.get("report_bytes", 0))
                    if handoff_offset + HANDOFF_WITNESS_BYTES > report_bytes:
                        failures.append("handoff-witness is outside manifest report_bytes")
            except (KeyError, TypeError, ValueError):
                failures.append("handoff-witness has no valid transport offset")
        publish_records = [
            record for record in data["records"]
            if record.get("name") == FAULT_PUBLISH_WINDOW_RECORD
        ]
        if len(publish_records) != 1:
            failures.append(
                f"manifest must contain one {FAULT_PUBLISH_WINDOW_RECORD} record"
            )
        else:
            publish = publish_records[0]
            expected_publish_physical = (
                early_physical + FAULT_PUBLISH_WINDOW_BASE_SLOT * 8
                if early_physical is not None else None
            )
            try:
                publish_physical = int(publish["physical"], 0)
                publish_size = int(publish["size"])
                offset_key = "report_offset" if data["transport_mode"] == "minimal-boundary" else "offset"
                publish_offset = int(publish[offset_key])
            except (KeyError, TypeError, ValueError):
                failures.append("fault-publish-window has invalid physical or transport geometry")
            else:
                if publish_physical != expected_publish_physical:
                    failures.append(
                        f"fault-publish-window physical {publish_physical:#x} does not cover "
                        f"slots 58..63 at {expected_publish_physical:#x}"
                    )
                if publish_size != FAULT_PUBLISH_WINDOW_BYTES:
                    failures.append(
                        f"fault-publish-window size is {publish_size}, not {FAULT_PUBLISH_WINDOW_BYTES}"
                    )
                if data["transport_mode"] == "minimal-boundary":
                    report_bytes = int(data.get("report_bytes", 0))
                    if publish_offset + FAULT_PUBLISH_WINDOW_BYTES > report_bytes:
                        failures.append("fault-publish-window is outside manifest report_bytes")
        path_records = [
            record for record in data["records"]
            if record.get("name") == ENTRY_PATH_WINDOW_RECORD
        ]
        if len(path_records) > 1:
            failures.append(f"manifest has multiple {ENTRY_PATH_WINDOW_RECORD} records")
        elif len(path_records) == 1 and early_physical is not None:
            path_window = path_records[0]
            expected_path_physical = early_physical + ENTRY_PATH_WINDOW_BASE_SLOT * 8
            try:
                path_physical = int(path_window["physical"], 0)
                path_size = int(path_window["size"])
                offset_key = "report_offset" if data["transport_mode"] == "minimal-boundary" else "offset"
                path_offset = int(path_window[offset_key])
            except (KeyError, TypeError, ValueError):
                failures.append("entry-path-window has invalid physical or transport geometry")
            else:
                if path_physical != expected_path_physical:
                    failures.append(
                        f"entry-path-window physical {path_physical:#x} does not cover "
                        f"slots 64/65 at {expected_path_physical:#x}"
                    )
                if path_size != ENTRY_PATH_WINDOW_BYTES:
                    failures.append(
                        f"entry-path-window size is {path_size}, not {ENTRY_PATH_WINDOW_BYTES}"
                    )
                if data["transport_mode"] == "minimal-boundary":
                    report_bytes = int(data.get("report_bytes", 0))
                    if path_offset + ENTRY_PATH_WINDOW_BYTES > report_bytes:
                        failures.append("entry-path-window is outside manifest report_bytes")
        pointer_records = [
            record for record in data["records"]
            if record.get("name") == FAULT_POINTER_WINDOW_RECORD
        ]
        if len(pointer_records) != 1:
            failures.append(f"manifest must contain one {FAULT_POINTER_WINDOW_RECORD} record")
        else:
            pointer = pointer_records[0]
            try:
                pointer_physical = int(pointer["physical"], 0)
                pointer_size = int(pointer["size"])
                _record_raw_offset(data, pointer)
                symbol_physical = int(pointer["symbol_physical"], 0)
                symbol_offset = int(pointer["symbol_offset"])
            except (KeyError, TypeError, ValueError):
                failures.append("fault-pointer-window has invalid symbol or transport geometry")
            else:
                if pointer_size != FAULT_POINTER_WINDOW_BYTES or pointer_physical % 16:
                    failures.append("fault-pointer-window must be one aligned 16-byte range")
                if symbol_offset < 0 or symbol_offset + 8 > pointer_size:
                    failures.append("fault-pointer-window symbol offset is outside its 16-byte range")
                if symbol_physical != pointer_physical + symbol_offset:
                    failures.append("fault-pointer-window symbol address does not match its base and offset")
                try:
                    expected_symbol_physical = fault_pointer_symbol_physical(kernel)
                    if symbol_physical != expected_symbol_physical:
                        failures.append(
                            "fault-pointer-window does not contain the Mach-O _native_early_fault_address "
                            f"({symbol_physical:#x} != {expected_symbol_physical:#x})"
                        )
                except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
                    failures.append(f"could not verify fault-pointer-window symbol: {exc}")
                if pointer_size >= FAULT_POINTER_VALUE_OFFSET + 8 and data["transport_mode"] == "minimal-boundary":
                    if int(pointer.get("report_offset", -1)) + pointer_size > int(data.get("report_bytes", 0)):
                        failures.append("fault-pointer-window is outside manifest report_bytes")
        store_windows = [
            record for record in data["records"]
            if record.get("name") == R68E7_STORE_WINDOW_RECORD
        ]
        if require_r68e7 and len(store_windows) != 1:
            failures.append(f"manifest must contain one {R68E7_STORE_WINDOW_RECORD} record")
        if len(store_windows) > 1:
            failures.append(f"manifest has multiple {R68E7_STORE_WINDOW_RECORD} records")
        elif len(store_windows) == 1 and early_physical is not None:
            store_window = store_windows[0]
            try:
                store_physical = int(store_window["physical"], 0)
                store_size = int(store_window["size"])
                offset_key = "report_offset" if data["transport_mode"] == "minimal-boundary" else "offset"
                store_offset = int(store_window[offset_key])
                if store_offset < 0:
                    raise ValueError("negative offset")
            except (KeyError, TypeError, ValueError):
                failures.append("R68E7 store witness has invalid physical or transport geometry")
            else:
                expected_store_physical = early_physical + R68E7_STORE_WINDOW_BASE_OFFSET
                if store_physical != expected_store_physical:
                    failures.append(
                        f"R68E7 store witness physical {store_physical:#x} does not start at "
                        f"the end of early-fault-record {expected_store_physical:#x}"
                    )
                if store_size != R68E7_STORE_WINDOW_BYTES:
                    failures.append(
                        f"R68E7 store witness size is {store_size}, not {R68E7_STORE_WINDOW_BYTES}"
                    )
                if data["transport_mode"] == "minimal-boundary":
                    report_bytes = int(data.get("report_bytes", 0))
                    if store_offset + R68E7_STORE_WINDOW_BYTES > report_bytes:
                        failures.append("R68E7 store witness is outside manifest report_bytes")
    else:
        failures.append("manifest is missing early-fault-record")
    return failures


def decode_boundary_markers(raw: Path, manifest: Path) -> dict[str, dict[str, object]]:
    """Decode boundary codewords only when the manifest captures their physical words."""
    manifest_data = json.loads(manifest.read_text())
    records = manifest_data.get("records", [])
    early = next((record for record in records
                  if record.get("name") == "early-fault-record"), None)
    if early is None:
        return {name: {"slot": boundary_marker_spec(name)[0],
                       "status": "unavailable", "value": None}
                for name in BOUNDARY_MARKERS}
    try:
        early_physical = int(early["physical"], 0)
    except (KeyError, TypeError, ValueError):
        return {name: {"slot": boundary_marker_spec(name)[0],
                       "status": "unavailable", "value": None}
                for name in BOUNDARY_MARKERS}
    mode = manifest_data.get("transport_mode")
    data = raw.read_bytes()
    record_offset = int(early.get("report_offset" if mode == "minimal-boundary" else "offset", -1))
    if mode == "minimal-boundary":
        record_offset += RAW_STAGE_BASE_OFFSET
    terminal_magic = (int.from_bytes(data[record_offset:record_offset + 8], "little")
                      if record_offset >= 0 and record_offset + 8 <= len(data) else 0)
    decoded: dict[str, dict[str, object]] = {}
    for name in BOUNDARY_MARKERS:
        slot, expected = boundary_marker_spec(name)
        physical = early_physical + slot * 8
        covering = []
        for record in records:
            try:
                record_physical = int(record["physical"], 0)
                record_size = int(record["size"])
            except (KeyError, TypeError, ValueError):
                continue
            if record_physical <= physical and physical + 8 <= record_physical + record_size:
                covering.append(record)
        if len(covering) != 1:
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "status": "unavailable", "value": None,
                             "expected": hex(expected)}
            continue
        record = covering[0]
        try:
            record_physical = int(record["physical"], 0)
            offset_key = "report_offset" if mode == "minimal-boundary" else "offset"
            offset = int(record[offset_key])
            raw_offset = (
                RAW_STAGE_BASE_OFFSET + offset + physical - record_physical
                if mode == "minimal-boundary"
                else offset + physical - record_physical
            )
        except (KeyError, TypeError, ValueError):
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "status": "unavailable", "value": None,
                             "expected": hex(expected)}
            continue
        if raw_offset < 0 or raw_offset + 8 > len(data):
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": "truncated",
                             "value": None, "expected": hex(expected)}
            continue
        value = int.from_bytes(data[raw_offset:raw_offset + 8], "little")
        previous = PREVIOUS_GENERATION_MARKERS.get(name)
        if name == "PREMMU00":
            legacy = int.from_bytes(b"R68E3PM0", "little")
            known = (expected, previous, legacy)
            status = "present" if value in known else "zero" if value == 0 else "other"
            generation = ("current" if value == expected else
                          "previous" if value == previous else
                          "legacy" if value == legacy else
                          "absent" if value == 0 else "unknown")
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": status,
                             "value": hex(value), "expected": hex(expected),
                             "generation": generation}
        elif name == "ARMENTRY":
            if terminal_magic in TERMINAL_LINK_REGISTER_MAGICS:
                decoded[name] = {"slot": slot, "physical": hex(physical),
                                 "raw_offset": hex(raw_offset), "status": "overwritten-by-terminal-link-register",
                                 "value": hex(value), "expected": hex(expected),
                                 "overwritten_by": hex(terminal_magic), "link_register": hex(value)}
                continue
            status = "present" if value in (
                expected, previous, ENTRY_MARKER_LEGACY, R83_ENTRY_MARKER
            ) else "zero" if value == 0 else "other"
            generation = ("current" if value == expected else
                          "previous" if value == previous else
                          "legacy" if value == ENTRY_MARKER_LEGACY else
                          "r83" if value == R83_ENTRY_MARKER else
                          "absent" if value == 0 else "unknown")
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": status,
                             "value": hex(value), "expected": hex(expected),
                             "generation": generation}
        elif name == "FIRST_CPU" and value == R83_FIRST_CPU_MARKER:
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": "present",
                             "value": hex(value), "expected": hex(expected),
                             "generation": "r83"}
        elif name == "FPBEFOR0" and value == HANDOFF_MARKERS["PTBASE00"][1]:
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": "overwritten",
                             "value": hex(value), "expected": hex(expected),
                             "overwritten_by": "PTBASE00"}
        elif name == "FPSTOR00" and value == HANDOFF_MARKERS["PTCOUNT0"][1]:
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": "overwritten",
                             "value": hex(value), "expected": hex(expected),
                             "overwritten_by": "PTCOUNT0"}
        elif name == "ARMRET" and value == CENTRY_MARKER:
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": "present",
                             "value": hex(value), "expected": hex(expected),
                             "generation": "c-entry", "alias": "CENTRY00"}
        else:
            status = "present" if value in (expected, previous) else "zero" if value == 0 else "other"
            generation = ("current" if value == expected else
                          "previous" if value == previous else
                          "absent" if value == 0 else "unknown")
            decoded[name] = {"slot": slot, "physical": hex(physical),
                             "raw_offset": hex(raw_offset), "status": status,
                             "value": hex(value), "expected": hex(expected),
                             "generation": generation}
    return decoded


def decode_y35a_bootstrap_phase(
    kernel: Path, raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode the one-word last-stage cursor by its named readback record."""
    manifest_data = json.loads(manifest.read_text())
    records = [item for item in manifest_data.get("records", [])
               if item.get("name") == "_y35a_bootstrap_phase"]
    if len(records) != 1:
        return {"status": "unavailable", "reason": "expected exactly one named phase record"}
    record = records[0]
    try:
        logical_width = int(record["field_bytes"])
        size = int(record["size"])
        physical = int(record["physical"], 0)
        offset = _record_raw_offset(manifest_data, record)
    except (KeyError, TypeError, ValueError):
        return {"status": "invalid", "reason": "phase record geometry or field width is invalid"}
    if logical_width != 8 or size < 16:
        return {"status": "invalid", "reason": "phase field must be 8 bytes in a 16-byte aligned window"}
    try:
        layout = parse_macho(kernel.read_bytes())
        symbols = nm_symbol_addresses(kernel)
        if "_y35a_bootstrap_phase" not in symbols:
            return {"status": "unavailable", "reason": "kernel symbol is absent"}
        virtual_base = int(manifest_data["kernel_virtual_base"], 0)
        physical_base = int(manifest_data["kernel_physical_base"], 0)
        expected_physical = physical_base + symbols["_y35a_bootstrap_phase"] - layout["base"]
    except (KeyError, OSError, TypeError, ValueError, RuntimeError,
            subprocess.CalledProcessError):
        return {"status": "invalid", "reason": "could not bind phase field to kernel symbol"}
    if virtual_base != layout["base"] or physical != expected_physical:
        return {"status": "invalid", "reason": "phase record physical address does not match the linked symbol"}
    data = raw.read_bytes()
    if offset < 0 or offset + logical_width > len(data):
        return {"status": "truncated", "raw_offset": hex(offset)}
    value = int.from_bytes(data[offset:offset + logical_width], "little")
    label = Y35A_BOOTSTRAP_PHASES.get(value)
    before_value = None
    if baseline is not None:
        before = Path(baseline).read_bytes()
        if offset + logical_width <= len(before):
            before_value = int.from_bytes(before[offset:offset + logical_width], "little")
    status = classify_y35a_bootstrap_phase(value, before_value)
    return {
        "status": status,
        "stage": label,
        "value": hex(value),
        "field_bytes": logical_width,
        "record_size": size,
        "physical": hex(physical),
        "raw_offset": hex(offset),
        "baseline_value": None if before_value is None else hex(before_value),
        "freshness_note": "A changed known codeword supports observing this cursor value in final raw; it does not prove the next stage or completion barrier returned.",
    }


def classify_y35a_bootstrap_phase(value: int, baseline_value: int | None) -> str:
    """Classify a known cursor codeword without inferring later progress."""
    if value == 0:
        return "zero"
    if value not in Y35A_BOOTSTRAP_PHASES:
        return "unknown"
    if baseline_value is None:
        return "present-freshness-unknown"
    return "unchanged" if value == baseline_value else "fresh"


def decode_sctlr_el1(raw: Path, manifest: Path) -> dict[str, object]:
    """Decode the live SCTLR_EL1 value at handoff slot57."""
    manifest_data = json.loads(manifest.read_text())
    record = next((item for item in manifest_data.get("records", [])
                   if item.get("name") == HANDOFF_WITNESS_RECORD), None)
    if record is None:
        return {"status": "unavailable"}
    try:
        size = int(record["size"])
        offset = _record_raw_offset(manifest_data, record)
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable"}
    if size < HANDOFF_WITNESS_BYTES or offset < 0:
        return {"status": "truncated"}
    raw_bytes = raw.read_bytes()
    value_offset = offset + (SCTLR_VALUE_SLOT - HANDOFF_MARKERS["SCTLRRD0"][0]) * 8
    if value_offset + 8 > len(raw_bytes):
        return {"status": "truncated", "raw_offset": hex(value_offset)}
    value = int.from_bytes(raw_bytes[value_offset:value_offset + 8], "little")
    return {"status": "captured" if value else "zero", "value": hex(value),
            "mmu_enabled": bool(value & 1), "data_cache_enabled": bool(value & 4)}


def decode_r68e7_store_window(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode same-instant MMU-off operands and the direct global load-back."""
    manifest_data = json.loads(manifest.read_text())
    records = {record.get("name"): record for record in manifest_data.get("records", [])}
    record = records.get(R68E7_STORE_WINDOW_RECORD)
    early = records.get("early-fault-record")
    pointer = records.get(FAULT_POINTER_WINDOW_RECORD)
    if record is None:
        return {"status": "unavailable", "reason": f"{R68E7_STORE_WINDOW_RECORD} missing"}
    try:
        size = int(record["size"])
        offset = _record_raw_offset(manifest_data, record)
        early_physical = int(early["physical"], 0)
        pointer_raw_offset = _record_raw_offset(manifest_data, pointer)
        pointer_size = int(pointer["size"])
        pointer_symbol_offset = int(pointer["symbol_offset"])
        pointer_symbol_physical = int(pointer["symbol_physical"], 0)
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable", "reason": "R68E7 witness geometry is incomplete"}
    data = raw.read_bytes()
    if (size != R68E7_STORE_WINDOW_BYTES or offset < 0
            or offset + R68E7_STORE_WINDOW_BYTES > len(data)):
        return {"status": "truncated", "raw_offset": hex(offset), "size": size}
    words = [int.from_bytes(data[offset + i * 8:offset + (i + 1) * 8], "little")
             for i in range(8)]
    values = {
        name: words[offset_bytes // 8]
        for name, offset_bytes in R68E7_STORE_VALUE_OFFSETS.items()
    }
    snapshot_value = R68E7_STORE_MARKERS["PUBLIN00"][1]
    readback_value = R68E7_STORE_MARKERS["PUBLRD00"][1]
    snapshot_marker = values["snapshot_marker"]
    readback_marker = values["readback_marker"]
    baseline_words = None
    if baseline is not None:
        baseline_data = baseline.read_bytes()
        if offset + R68E7_STORE_WINDOW_BYTES <= len(baseline_data):
            baseline_words = [int.from_bytes(
                baseline_data[offset + i * 8:offset + (i + 1) * 8], "little"
            ) for i in range(8)]
    baseline_snapshot = baseline_words[6] if baseline_words is not None else None
    baseline_readback = baseline_words[7] if baseline_words is not None else None
    comparison_available = baseline_words is not None
    snapshot_present = snapshot_marker == snapshot_value
    readback_present = readback_marker == readback_value
    snapshot_fresh = (comparison_available and snapshot_present
                      and baseline_snapshot != snapshot_value)
    readback_fresh = (comparison_available and readback_present
                      and baseline_readback != readback_value)
    x16, x17, x9, x22, x23 = (values[name] for name in ("x16", "x17", "x9", "x22", "x23"))
    expected_x9 = (x16 - x22 + x23) & 0xFFFFFFFFFFFFFFFF
    expected_payload = (early_physical + x22 - x23) & 0xFFFFFFFFFFFFFFFF
    x16_matches_symbol = x16 == pointer_symbol_physical
    x9_matches_arithmetic = x9 == expected_x9
    x17_matches_carrier = x17 == expected_payload
    readback_matches_payload = values["global_readback"] == x17
    pointer_value = None
    if (pointer_raw_offset >= 0 and pointer_size >= pointer_symbol_offset + 8
            and pointer_raw_offset + pointer_size <= len(data)):
        pointer_value = int.from_bytes(
            data[pointer_raw_offset + pointer_symbol_offset:
                 pointer_raw_offset + pointer_symbol_offset + 8], "little"
        )
    pointer_matches_payload = pointer_value == x17
    if snapshot_present:
        status = "snapshot-fresh" if snapshot_fresh else "snapshot-marker-not-fresh"
    elif snapshot_marker == 0:
        status = "snapshot-not-observed"
    else:
        status = "snapshot-marker-other"
    if readback_present and readback_fresh:
        status = "store-readback-fresh"
    elif readback_present:
        status = "readback-marker-not-fresh"
    elif readback_marker == 0 and snapshot_fresh:
        status = "snapshot-fresh-store-return-unobserved"
    return {
        "status": status,
        "physical": record.get("physical"),
        "raw_offset": hex(offset),
        "snapshot_marker": hex(snapshot_marker),
        "snapshot_present": snapshot_present,
        "snapshot_fresh": snapshot_fresh,
        "baseline_comparison_available": comparison_available,
        "baseline_snapshot_marker": None if baseline_snapshot is None else hex(baseline_snapshot),
        "readback_marker": hex(readback_marker),
        "readback_present": readback_present,
        "readback_fresh": readback_fresh,
        "baseline_readback_marker": None if baseline_readback is None else hex(baseline_readback),
        "x16_physical_target": hex(x16),
        "expected_global_physical": hex(pointer_symbol_physical),
        "x16_matches_symbol": x16_matches_symbol,
        "x17_payload": hex(x17),
        "expected_payload_from_live_bases": hex(expected_payload),
        "x17_matches_carrier": x17_matches_carrier,
        "x9_candidate": hex(x9),
        "x9_expected_from_live_bases": hex(expected_x9),
        "x9_matches_arithmetic": x9_matches_arithmetic,
        "x22_kva_base": hex(x22),
        "x23_pa_base": hex(x23),
        "global_loadback": hex(values["global_readback"]),
        "loadback_matches_payload": readback_matches_payload,
        "global_pointer_raw_value": None if pointer_value is None else hex(pointer_value),
        "pointer_matches_payload": pointer_matches_payload,
        "global_pointer_capture_scope": (
            "later post-boot readback-probe capture; independent of the same-boot immediate LDR"
        ),
        "registers_match_contract": x16_matches_symbol and x17_matches_carrier and x9_matches_arithmetic,
    }


def decode_r68e7_low_carrier(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode the decisive operands in retained early-fault slots5..10 and stage slot11."""
    manifest_data = json.loads(manifest.read_text())
    records = {record.get("name"): record for record in manifest_data.get("records", [])}
    early = records.get("early-fault-record")
    pointer = records.get(FAULT_POINTER_WINDOW_RECORD)
    if early is None or pointer is None:
        return {"status": "unavailable", "reason": "early-fault record or pointer binding missing"}
    try:
        offset = _record_raw_offset(manifest_data, early)
        size = int(early["size"])
        early_physical = int(early["physical"], 0)
        symbol_offset = int(pointer["symbol_offset"])
        symbol_physical = int(pointer["symbol_physical"], 0)
        pointer_offset = _record_raw_offset(manifest_data, pointer)
        pointer_size = int(pointer["size"])
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable", "reason": "retained-carrier geometry incomplete"}
    if size < 12 * 8 or offset < 0:
        return {"status": "truncated", "reason": "early carrier does not include slots5..11"}
    data = raw.read_bytes()
    if offset + 12 * 8 > len(data):
        return {"status": "truncated", "raw_offset": hex(offset), "size": size}
    slots = [int.from_bytes(data[offset + i * 8:offset + (i + 1) * 8], "little")
             for i in range(12)]
    x16, x17, x9, x22, x23, global_readback = slots[5:11]
    stage_value = slots[R68E7_LOW_STAGE_SLOT]
    stage = R68E7_LOW_STAGE_MARKERS.get(stage_value, "absent" if stage_value == 0 else "other")
    baseline_slots = None
    if baseline is not None:
        before = baseline.read_bytes()
        if offset + 12 * 8 <= len(before):
            baseline_slots = [int.from_bytes(before[offset + i * 8:offset + (i + 1) * 8], "little")
                              for i in range(12)]
    baseline_stage = baseline_slots[R68E7_LOW_STAGE_SLOT] if baseline_slots else None
    stage_fresh = (baseline_slots is not None and stage in R68E7_LOW_STAGE_MARKERS.values()
                   and baseline_stage != stage_value)
    c_phase_candidates = []
    c_phase_overwrites = []
    for slot, value in enumerate(slots[5:11], start=5):
        marker = R68E7_LOW_C_PHASE_MARKERS.get(slot)
        if marker is None or value != marker[1]:
            continue
        observed = {"slot": slot, "marker": marker[0], "value": hex(value), "fresh": None}
        if baseline_slots is not None:
            observed["fresh"] = baseline_slots[slot] != value
            if observed["fresh"]:
                c_phase_overwrites.append(observed)
        c_phase_candidates.append(observed)
    pointer_value = None
    if (pointer_offset >= 0 and pointer_size >= symbol_offset + 8
            and pointer_offset + pointer_size <= len(data)):
        pointer_value = int.from_bytes(data[pointer_offset + symbol_offset:
                                            pointer_offset + symbol_offset + 8], "little")
    snap = stage == "snapshot-complete"
    readback = stage == "store-readback-complete"
    low_payload_available = stage in R68E7_LOW_STAGE_MARKERS.values() and not c_phase_candidates
    try:
        expected_x22 = int(manifest_data["kernel_virtual_base"], 0)
        expected_x23 = int(manifest_data["kernel_physical_base"], 0)
        base_expectations_available = True
    except (KeyError, TypeError, ValueError):
        expected_x22 = expected_x23 = None
        base_expectations_available = False
    expected_x9 = (x16 - x22 + x23) & 0xffffffffffffffff
    expected_payload = (early_physical + x22 - x23) & 0xffffffffffffffff
    x9_mode = manifest_data.get("r68e7_x9_mode", "legacy-base-arithmetic")
    if x9_mode == "direct-physical-alias":
        expected_x9_from_contract = symbol_physical
    else:
        expected_x9_from_contract = (
            (symbol_physical - expected_x22 + expected_x23) & 0xffffffffffffffff
            if base_expectations_available else None
        )
    expected_payload_from_contract = (
        (early_physical + expected_x22 - expected_x23) & 0xffffffffffffffff
        if base_expectations_available else None
    )
    x22_matches_expected_base = base_expectations_available and x22 == expected_x22
    x23_matches_expected_base = base_expectations_available and x23 == expected_x23
    expected_by_slot = {
        5: symbol_physical,
        6: expected_payload_from_contract,
        7: expected_x9_from_contract,
        8: expected_x22,
        9: expected_x23,
        10: expected_payload_from_contract,
    }
    marker_by_slot = {item["slot"]: item for item in c_phase_candidates}
    slot_contract_checks = {}
    for slot, name, value in zip(
        range(5, 11),
        ("x16", "x17", "x9", "x22", "x23", "global_readback"),
        slots[5:11],
    ):
        marker = marker_by_slot.get(slot)
        overwritten = marker is not None and marker.get("fresh") is True
        expected = expected_by_slot[slot]
        slot_contract_checks[name] = {
            "slot": slot,
            "value": hex(value),
            "expected": None if expected is None else hex(expected),
            "overwritten_by_fresh_c_phase_marker": overwritten,
            "marker": marker,
            "matches": overwritten or (expected is not None and value == expected),
        }
    live_payload_fields_match_contract = (
        base_expectations_available
        and all(item["matches"] for item in slot_contract_checks.values())
    )
    registers_match_contract = low_payload_available and live_payload_fields_match_contract
    readback_marker = marker_by_slot.get(10)
    readback_overwritten_by_fresh_c_phase = (
        readback_marker is not None and readback_marker.get("fresh") is True
    )
    readback_matches_expected_payload = (
        expected_payload_from_contract is not None
        and global_readback == expected_payload_from_contract
    )
    loadback_valid_or_overwritten = (
        readback_matches_expected_payload or readback_overwritten_by_fresh_c_phase
    )
    return {
        "status": "readback-present" if readback else "snapshot-present" if snap else "stage-marker-absent",
        "carrier_physical": early.get("physical"),
        "raw_offset": hex(offset),
        "slot_values": {"x16": hex(x16), "x17": hex(x17), "x9": hex(x9),
                        "x22": hex(x22), "x23": hex(x23), "global_readback": hex(global_readback)},
        "expected_x22_kva_base": None if expected_x22 is None else hex(expected_x22),
        "expected_x23_pa_base": None if expected_x23 is None else hex(expected_x23),
        "base_expectations_available": base_expectations_available,
        "x22_matches_expected_base": x22_matches_expected_base,
        "x23_matches_expected_base": x23_matches_expected_base,
        "stage_slot": R68E7_LOW_STAGE_SLOT,
        "stage_value": hex(stage_value),
        "stage": stage,
        "stage_fresh": stage_fresh,
        "baseline_stage_value": None if baseline_stage is None else hex(baseline_stage),
        "low_payload_available": low_payload_available,
        "slot_contract_checks": slot_contract_checks,
        "live_payload_fields_match_contract": live_payload_fields_match_contract,
        "c_phase_overwrites": c_phase_overwrites,
        "c_phase_marker_candidates": c_phase_candidates,
        "x16_matches_global_symbol": x16 == symbol_physical,
        "global_symbol_physical": hex(symbol_physical),
        "x17_matches_early_carrier_payload": x17 == expected_payload,
        "expected_payload_from_physical_bootargs": hex(expected_payload),
        "x9_mode": x9_mode,
        "x9_matches_live_base_arithmetic": x9 == expected_x9,
        "x9_matches_physical_alias": x9 == symbol_physical,
        "expected_x9_from_live_bases": hex(expected_x9),
        "readback_matches_x17": global_readback == x17,
        "readback_matches_expected_payload": readback_matches_expected_payload,
        "readback_overwritten_by_fresh_c_phase": readback_overwritten_by_fresh_c_phase,
        "loadback_valid_or_overwritten": loadback_valid_or_overwritten,
        "expected_payload_from_manifest_bases": (
            None if expected_payload_from_contract is None else hex(expected_payload_from_contract)
        ),
        "global_pointer_raw_value": None if pointer_value is None else hex(pointer_value),
        "pointer_matches_x17": pointer_value == x17,
        "global_pointer_capture_scope": (
            "later post-boot readback-probe capture; independent of the same-boot immediate LDR"
        ),
        "registers_match_contract": registers_match_contract,
        "c_phase_overwrite": (
            "slots5..10 may later be rewritten by ARMINITE/PEINITEN/PEINITRT/ARMVMINI/PANICINI/CONSOLE; "
            "slot11 identifies the last completed R68E7 capture stage"
        ),
    }


def decode_r68e7_alias_witnesses(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Separate post-ISB identity-alias progress from the later KVA-alias store."""
    final_markers = decode_boundary_markers(raw, manifest)
    before_markers = decode_boundary_markers(baseline, manifest) if baseline else {}
    physical = final_markers.get("SCTLRRD0", {})
    before_physical = before_markers.get("SCTLRRD0", {})
    physical_baseline_available = (baseline is not None
                                   and before_physical.get("status") not in ("unavailable", "truncated"))
    physical_fresh = (physical_baseline_available
                      and physical.get("generation") == "current"
                      and before_physical.get("generation") != "current")
    manifest_data = json.loads(manifest.read_text())
    record = next((item for item in manifest_data.get("records", [])
                   if item.get("name") == FAULT_PUBLISH_WINDOW_RECORD), None)
    if record is None:
        return {"status": "unavailable", "reason": f"{FAULT_PUBLISH_WINDOW_RECORD} missing"}
    try:
        offset = _record_raw_offset(manifest_data, record)
        size = int(record["size"])
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable", "reason": "KVA witness geometry is incomplete"}
    data = raw.read_bytes()
    if size < FAULT_PUBLISH_WINDOW_BYTES or offset < 0 or offset + FAULT_PUBLISH_WINDOW_BYTES > len(data):
        return {"status": "truncated", "raw_offset": hex(offset), "size": size}
    kva_value = int.from_bytes(data[offset + 5 * 8:offset + 6 * 8], "little")
    kva_expected = KVA_ALIAS_MARKER[1]
    before_kva = None
    if baseline is not None:
        before_data = baseline.read_bytes()
        if offset + FAULT_PUBLISH_WINDOW_BYTES <= len(before_data):
            before_kva = int.from_bytes(before_data[offset + 5 * 8:offset + 6 * 8], "little")
    kva_present = kva_value == kva_expected
    kva_comparison_available = before_kva is not None
    kva_fresh = (kva_present and kva_comparison_available
                 and before_kva != kva_expected)
    sctlr = decode_sctlr_el1(raw, manifest)
    if not physical_fresh:
        status = "post-isb-vp-witness-not-fresh"
    elif sctlr.get("status") != "captured" or not sctlr.get("mmu_enabled"):
        status = "vp-witness-fresh-mmu-not-proven-on"
    elif kva_fresh:
        status = "mmu-and-both-alias-witnesses-fresh"
    else:
        status = "mmu-and-vp-witness-fresh-kva-witness-absent"
    return {
        "status": status,
        "physical_alias_marker": physical.get("value"),
        "physical_alias_fresh": physical_fresh,
        "sctlr_el1": sctlr,
        "kva_alias_marker": hex(kva_value),
        "kva_alias_expected": hex(kva_expected),
        "kva_alias_present": kva_present,
        "kva_alias_fresh": kva_fresh,
        "kva_baseline_comparison_available": kva_comparison_available,
        "baseline_kva_alias_marker": None if before_kva is None else hex(before_kva),
    }


def decode_entry_path_echo(raw: Path, manifest: Path) -> dict[str, object]:
    """Compare the cold-entry marker with the immediate load-back value."""
    manifest_data = json.loads(manifest.read_text())
    record = next((item for item in manifest_data.get("records", [])
                   if item.get("name") == ENTRY_PATH_WINDOW_RECORD), None)
    if record is None:
        return {"status": "unavailable"}
    try:
        size = int(record["size"])
        offset = _record_raw_offset(manifest_data, record)
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable"}
    if size < ENTRY_PATH_WINDOW_BYTES or offset < 0:
        return {"status": "truncated"}
    data = raw.read_bytes()
    if offset + ENTRY_PATH_WINDOW_BYTES > len(data):
        return {"status": "truncated", "raw_offset": hex(offset)}
    marker = int.from_bytes(data[offset:offset + 8], "little")
    echo = int.from_bytes(data[offset + 8:offset + 16], "little")
    known = {
        ENTRY_PATH_MARKERS["FIRST_CPU"][1]: "R68E7FS0",
        R83_FIRST_CPU_MARKER: "R83FS00 followed by zero",
    }
    expected = marker if marker in known else ENTRY_PATH_MARKERS["FIRST_CPU"][1]
    return {"status": "captured", "marker": hex(marker), "readback": hex(echo),
            "generation": known.get(marker), "expected": hex(expected),
            "marker_matches": marker in known, "readback_matches": echo == expected,
            "roundtrip_matches": marker == echo and marker in known}


def _read_record_word(
    raw_data: bytes, manifest_data: dict, record_name: str,
    relative_offset: int = 0,
) -> tuple[int | None, str, int | None]:
    records = [record for record in manifest_data.get("records", [])
               if record.get("name") == record_name]
    if len(records) != 1:
        return None, "unavailable", None
    record = records[0]
    try:
        record_size = int(record["size"])
        offset = _record_raw_offset(manifest_data, record) + relative_offset
    except (KeyError, TypeError, ValueError):
        return None, "unavailable", None
    if relative_offset < 0 or relative_offset + 8 > record_size:
        return None, "truncated", offset
    if offset < 0 or offset + 8 > len(raw_data):
        return None, "truncated", offset
    return int.from_bytes(raw_data[offset:offset + 8], "little"), "captured", offset


def decode_r83_entry_ladder(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode generation-specific R83 markers through manifest-named records."""
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None

    def observation(name: str, record: str, relative: int, expected: int):
        value, status, raw_offset = _read_record_word(final_data, manifest_data, record, relative)
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, record, relative
            )
        marker_status = ("present" if value == expected else
                         "absent" if value == 0 else
                         status if value is None else "other")
        fresh = (value == expected and before != expected
                 if baseline_data is not None and before_status == "captured"
                 else None)
        return {
            "status": marker_status,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if raw_offset is None else hex(raw_offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": fresh,
        }

    terminal_value, terminal_status, terminal_offset = _read_record_word(
        final_data, manifest_data, "early-fault-record", 0
    )
    baseline_terminal = None
    baseline_early_payload = None
    final_early_payload = None
    if baseline_data is not None:
        baseline_terminal, _, _ = _read_record_word(
            baseline_data, manifest_data, "early-fault-record", 0
        )
        early_records = [record for record in manifest_data.get("records", [])
                         if record.get("name") == "early-fault-record"]
        if len(early_records) == 1:
            try:
                early_record = early_records[0]
                early_offset = _record_raw_offset(manifest_data, early_record)
                if (int(early_record["size"]) >= 5 * 8
                        and early_offset >= 0
                        and early_offset + 4 * 8 <= len(final_data)
                        and early_offset + 4 * 8 <= len(baseline_data)):
                    # Slot 4 is contested: terminal-v7 stores x30 there, while
                    # start_first_cpu writes R83ENT00 there. It cannot make a
                    # repeated terminal flag look fresh by itself.
                    final_early_payload = final_data[early_offset:early_offset + 4 * 8]
                    baseline_early_payload = baseline_data[early_offset:early_offset + 4 * 8]
            except (KeyError, TypeError, ValueError):
                pass
    terminal_v7 = int.from_bytes(b"Y35ALV07", "little")
    terminal_present = terminal_status == "captured" and terminal_value == terminal_v7
    terminal_fresh = (
        terminal_present and final_early_payload is not None
        and final_early_payload != baseline_early_payload
        if baseline_data is not None else None
    )
    entry = observation("entry", "early-fault-record", 4 * 8, R83_ENTRY_MARKER)
    if terminal_present:
        entry.update({
            "status": "overwritten-by-terminal-v7",
            "value": None if terminal_value is None else hex(
                _read_record_word(final_data, manifest_data, "early-fault-record", 4 * 8)[0]
                or 0
            ),
            "fresh": None,
            "freshness_note": "slot 4 is terminal-v7's saved x30; it cannot prove the R83 entry marker",
        })
    c_entry = observation("c_entry", "early-fault-record", 5 * 8, R83_C_ENTRY_MARKER)
    first_cpu_store = observation(
        "first_cpu_store", ENTRY_PATH_WINDOW_RECORD, 0, R83_FIRST_CPU_MARKER
    )
    first_cpu_loadback = observation(
        "first_cpu_loadback", ENTRY_PATH_WINDOW_RECORD, 8, R83_FIRST_CPU_MARKER
    )
    phase_cursor = observation(
        "phase_cursor", "_y35a_bootstrap_phase", 0, R82_ARM_ENTRY_PHASE
    )
    first_cpu_roundtrip = {
        "status": "present" if (
            first_cpu_store["status"] == "present"
            and first_cpu_loadback["status"] == "present"
        ) else "incomplete",
        "fresh": bool(first_cpu_store["fresh"] and first_cpu_loadback["fresh"]),
        "note": "both independently sampled words must match zero-padded R83FS00 and both must differ from baseline",
    }
    terminal = {
        "status": "present" if terminal_present else (
            "absent" if terminal_status == "captured" and terminal_value == 0
            else terminal_status
        ),
        "value": None if terminal_value is None else hex(terminal_value),
        "raw_offset": None if terminal_offset is None else hex(terminal_offset),
        "baseline_value": None if baseline_terminal is None else hex(baseline_terminal),
        "fresh": terminal_fresh,
        "payload_changed": (final_early_payload != baseline_early_payload
                            if final_early_payload is not None else None),
    }
    markers = {
        "entry": entry,
        "c_entry": c_entry,
        "first_cpu_store": first_cpu_store,
        "first_cpu_loadback": first_cpu_loadback,
        "first_cpu_roundtrip": first_cpu_roundtrip,
        "phase_cursor": phase_cursor,
    }
    if terminal_present:
        progress = "terminal-v7-fault" if terminal_fresh else "terminal-v7-freshness-unproven"
    elif phase_cursor["fresh"]:
        progress = "arm-init-phase-setter"
    elif c_entry["fresh"]:
        progress = "arm-init-c-entry"
    elif first_cpu_roundtrip["fresh"]:
        progress = "first-cpu-roundtrip"
    elif entry["fresh"]:
        progress = "start-first-cpu-entry"
    else:
        progress = "no-fresh-r83-marker-observed"
    return {
        "status": "captured" if terminal_status == "captured" else terminal_status,
        "progress": progress,
        "markers": markers,
        "terminal": terminal,
        "limitations": [
            "A missing marker does not prove its instruction was never reached.",
            "R83CIN00 is after the compiler prologue and uses native_phase_args.",
            "R82ARM00 records the last published phase; it does not prove later startup completion.",
        ],
    }


def decode_r84_entry_ladder(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R84's post-setter marker and C-entry snapshot of slots64/65."""
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None

    def observe(record: str, relative: int, expected: int):
        value, status, offset = _read_record_word(
            final_data, manifest_data, record, relative
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, record, relative
            )
        marker_status = ("present" if value == expected else
                         "absent" if value == 0 else
                         status if value is None else "other")
        fresh = (value == expected and before != expected
                 if baseline_data is not None and before_status == "captured"
                 else None)
        return {
            "status": marker_status,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": fresh,
        }

    entry = observe("early-fault-record", 4 * 8, R84_ENTRY_MARKER)
    terminal_info = _terminal_record_freshness(raw, baseline, manifest) if baseline else None
    terminal_value, terminal_status, _ = _read_record_word(
        final_data, manifest_data, "early-fault-record", 0
    )
    terminal_v7 = int.from_bytes(b"Y35ALV07", "little")
    terminal_present = terminal_status == "captured" and terminal_value == terminal_v7
    if terminal_present:
        lr, _, _ = _read_record_word(final_data, manifest_data, "early-fault-record", 4 * 8)
        entry.update({
            "status": "overwritten-by-terminal-v7",
            "value": None if lr is None else hex(lr),
            "fresh": None,
            "freshness_note": "slot4 contains terminal-v7's saved x30, not R84ENT00",
        })

    markers = {
        "entry": entry,
        "first_cpu_store": observe(ENTRY_PATH_WINDOW_RECORD, 0, R84_FIRST_CPU_MARKER),
        "first_cpu_loadback": observe(ENTRY_PATH_WINDOW_RECORD, 8, R84_FIRST_CPU_MARKER),
        "c_entry": observe("early-fault-record", 5 * 8, R84_C_ENTRY_MARKER),
        "setter_return": observe("early-fault-record", 11 * 8, R84_SETTER_RETURN_MARKER),
    }
    for name, (slot, value) in R84_PHASE_MARKERS.items():
        markers[name] = observe("early-fault-record", slot * 8, value)
    markers["phase_cursor"] = {
        **observe("_y35a_bootstrap_phase", 0, R84_ARM_ENTRY_PHASE),
        "stage": None,
    }
    phase_value, phase_status, phase_offset = _read_record_word(
        final_data, manifest_data, "_y35a_bootstrap_phase", 0
    )
    baseline_phase = None
    if baseline_data is not None:
        baseline_phase, _, _ = _read_record_word(
            baseline_data, manifest_data, "_y35a_bootstrap_phase", 0
        )
    phase_label = (
        "R84ARM00" if phase_value == R84_ARM_ENTRY_PHASE else
        "R84LATE0" if phase_value == R84_LATE_PHASE else None
    )
    markers["phase_cursor"].update({
        "status": "present" if phase_label else ("absent" if phase_value == 0 else phase_status),
        "value": None if phase_value is None else hex(phase_value),
        "raw_offset": None if phase_offset is None else hex(phase_offset),
        "baseline_value": None if baseline_phase is None else hex(baseline_phase),
        "fresh": (phase_label is not None and baseline_phase != phase_value
                  if baseline_data is not None else None),
        "stage": phase_label,
    })

    snapshot64 = observe("early-fault-record", 29 * 8, R84_FIRST_CPU_MARKER)
    snapshot65 = observe("early-fault-record", 30 * 8, R84_FIRST_CPU_MARKER)
    snapshot_matches = (snapshot64["status"] == "present"
                        and snapshot65["status"] == "present")
    snapshot_zero = (snapshot64["status"] == "absent"
                     and snapshot65["status"] == "absent")
    snapshot = {
        "slot64_at_c_entry": snapshot64,
        "slot65_at_c_entry": snapshot65,
        "pair_matches_first_cpu": snapshot_matches,
        "pair_was_zero_at_c_entry": snapshot_zero,
        "snapshot_committed": bool(markers["setter_return"]["fresh"]),
        "interpretation": (
            "R84SET00 proves the two C-entry snapshot writes preceded the phase-setter return marker."
            if markers["setter_return"]["fresh"] else
            "Snapshot values are provisional because the post-setter marker is not fresh."
        ),
    }
    first_cpu_roundtrip = (
        markers["first_cpu_store"]["status"] == "present"
        and markers["first_cpu_loadback"]["status"] == "present"
        and markers["first_cpu_store"]["fresh"]
        and markers["first_cpu_loadback"]["fresh"]
    )
    markers["first_cpu_roundtrip"] = {
        "status": "present" if (
            markers["first_cpu_store"]["status"] == "present"
            and markers["first_cpu_loadback"]["status"] == "present"
        ) else "incomplete",
        "fresh": bool(first_cpu_roundtrip),
    }
    if terminal_present:
        progress = "terminal-v7-fault" if terminal_info and terminal_info.get("fresh") else "terminal-v7-freshness-unproven"
    elif markers["phase_cursor"]["stage"] == "R84LATE0" and markers["phase_cursor"]["fresh"]:
        progress = "arm-init-late-phase"
    elif markers["R84MST00"]["fresh"]:
        progress = "arm-init-machine-startup-boundary"
    elif markers["CONSOLE"]["fresh"]:
        progress = "console-create-returned"
    elif markers["PANICINI"]["fresh"]:
        progress = "panic-init-returned"
    elif markers["ARMVMINI"]["fresh"]:
        progress = "arm-vm-init-returned"
    elif markers["PEINITRT"]["fresh"]:
        progress = "pe-init-platform-returned"
    elif markers["PEINITEN"]["fresh"]:
        progress = "pe-init-platform-entered"
    elif markers["setter_return"]["fresh"]:
        progress = "arm-init-phase-setter-return"
    elif markers["phase_cursor"]["fresh"]:
        progress = "arm-init-phase-setter-published"
    elif markers["c_entry"]["fresh"]:
        progress = "arm-init-c-entry"
    elif first_cpu_roundtrip:
        progress = "first-cpu-roundtrip"
    elif markers["entry"]["fresh"]:
        progress = "start-first-cpu-entry"
    else:
        progress = "no-fresh-r84-marker-observed"
    return {
        "status": "captured" if terminal_status == "captured" else terminal_status,
        "progress": progress,
        "markers": markers,
        "snapshot_at_c_entry": snapshot,
        "terminal": terminal_info,
        "limitations": [
            "A missing marker does not prove its instruction was never reached.",
            "Slot64/65 snapshots are taken in arm_init after the compiler prologue.",
            "The post-setter marker distinguishes a call return from a published global value.",
        ],
    }


def decode_r85_machine_startup(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R85's temporal slot11 owner around machine_startup."""
    result = decode_r84_entry_ladder(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None

    def observe(slot: int, expected: int) -> dict[str, object]:
        value, status, offset = _read_record_word(
            final_data, manifest_data, "early-fault-record", slot * 8
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, "early-fault-record", slot * 8
            )
        return {
            "status": ("present" if value == expected else
                       "absent" if value == 0 else
                       status if value is None else "other"),
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": (value == expected and before != expected
                      if baseline_data is not None and before_status == "captured"
                      else None),
        }

    late_return = observe(11, R85_LATE_RETURN_MARKER)
    machine_callsite = observe(12, R85_MACHINE_START_MARKER)
    machine_return = observe(11, R85_MACHINE_RETURN_MARKER)
    machine_returned = bool(machine_return["fresh"])
    callsite_reached = bool(machine_callsite["fresh"] or machine_returned)
    late_returned = bool(late_return["fresh"] or callsite_reached or machine_returned)
    result["markers"]["late_setter_return"] = late_return
    result["markers"]["machine_startup_callsite"] = machine_callsite
    result["markers"]["machine_startup_return"] = machine_return
    result["temporal_slot11_owner"] = (
        "R85MACH0" if machine_return["status"] == "present" else
        "R85LRET0" if late_return["status"] == "present" else
        "R84SET00" if result["markers"]["setter_return"]["status"] == "present" else
        "unknown"
    )
    result["machine_startup_callsite_reached"] = callsite_reached
    result["machine_startup_entry_witnessed"] = machine_returned
    result["machine_startup_returned"] = machine_returned
    # R85MSB00 is stored before BL. A return witness proves entry, but in its
    # absence this experiment does not distinguish function entry from a fault
    # on the call or at the first instruction.
    result["machine_startup_entered"] = True if machine_returned else None
    result["late_setter_returned"] = late_returned
    if machine_returned:
        result["progress"] = "machine-startup-returned"
    elif callsite_reached:
        result["progress"] = "machine-startup-callsite-reached"
    elif late_returned:
        result["progress"] = "late-phase-setter-returned"
    result.setdefault("limitations", []).append(
        "R85MSB00 is emitted immediately before BL and proves only that the callsite was reached; "
        "without R85MACH0 or an in-function witness, machine_startup entry remains unproven."
    )
    return result


def decode_r86_startup(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode direct function-entry and early kernel-bootstrap return witnesses."""
    result = decode_r85_machine_startup(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    markers: dict[str, dict[str, object]] = {}
    for name, (slot, expected) in R86_STARTUP_MARKERS.items():
        value, status, offset = _read_record_word(
            final_data, manifest_data, "early-fault-record", slot * 8
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, "early-fault-record", slot * 8
            )
        markers[name] = {
            "status": ("present" if value == expected else
                       "absent" if value == 0 else
                       status if value is None else "other"),
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": (value == expected and before != expected
                      if baseline_data is not None and before_status == "captured"
                      else None),
            "temporal_owner": "R86 startup cursor; overwrites an earlier handoff witness after this stage",
        }
    result["r86_markers"] = markers
    result["machine_startup_function_entry_witnessed"] = bool(
        markers["R86MSE00"]["fresh"]
    )
    result["kernel_bootstrap_entry_witnessed"] = bool(
        markers["R86KBE00"]["fresh"]
    )
    reached = [name for name in R86_STARTUP_MARKERS
               if markers[name]["fresh"]]
    if reached:
        result["progress"] = reached[-1]
    result.setdefault("limitations", []).append(
        "R86 C-entry markers occur after the function's compiler prologue; they prove body entry, not execution of the first machine instruction."
    )
    return result


def decode_r87_startup(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R87 kernel_bootstrap and kernel_bootstrap_thread milestones."""
    result = decode_r86_startup(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    markers: dict[str, dict[str, object]] = {}
    for name, (slot, expected) in R87_STARTUP_MARKERS.items():
        value, status, offset = _read_record_word(
            final_data, manifest_data, "early-fault-record", slot * 8
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, "early-fault-record", slot * 8
            )
        markers[name] = {
            "status": ("present" if value == expected else
                       "absent" if value == 0 else
                       status if value is None else "other"),
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": (value == expected and before != expected
                      if baseline_data is not None and before_status == "captured"
                      else None),
            "temporal_owner": "R87 bootstrap/thread cursor; overwrites earlier handoff/snapshot values after this stage",
        }
    result["r87_markers"] = markers
    reached = [name for name in R87_STARTUP_MARKERS if markers[name]["fresh"]]
    if reached:
        result["progress"] = reached[-1]
    if markers["R87PMAP0"]["fresh"]:
        # R87PMAP0 is emitted inside kernel_bootstrap after its prologue and
        # after machine_startup's call into kernel_bootstrap. Its verified
        # call order therefore proves both earlier function entries even if
        # R86 slots14/15 still contain the same codewords in the baseline.
        result["machine_startup_function_entry_witnessed"] = True
        result["kernel_bootstrap_entry_witnessed"] = True
        result["entry_witness_inferred_from"] = "fresh R87PMAP0 after kernel_bootstrap entry"
    result["kernel_bootstrap_thread_entry_witnessed"] = bool(
        markers["R87KBT00"]["fresh"]
    )
    result["current_processor_returned"] = bool(markers["R87CPU00"]["fresh"])
    result.setdefault("limitations", []).append(
        "R87KBT00 follows the kernel_bootstrap_thread compiler prologue; it does not prove BSD or launchd startup."
    )
    return result


def decode_r88_bsd_iokit(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R88's kernel-thread, BSD, IOKit and user-bootstrap boundaries."""
    result = decode_r87_startup(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    markers: dict[str, dict[str, object]] = {}
    for name, (slot, expected) in R88_STARTUP_MARKERS.items():
        value, status, offset = _read_record_word(
            final_data, manifest_data, "early-fault-record", slot * 8
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, "early-fault-record", slot * 8
            )
        markers[name] = {
            "status": ("present" if value == expected else
                       "absent" if value == 0 else
                       status if value is None else "other"),
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": (value == expected and before != expected
                      if baseline_data is not None and before_status == "captured"
                      else None),
            "temporal_owner": "R88 bootstrap-thread/BSD cursor; overwrites earlier boot witnesses after this stage",
        }
    result["r88_markers"] = markers
    reached = [name for name in R88_STARTUP_MARKERS if markers[name]["fresh"]]
    later_stage_fresh = any(
        markers[name]["fresh"] for name in tuple(R88_STARTUP_MARKERS)[2:]
    )
    prng_returned = bool(markers["R88PRNOK"]["fresh"] or later_stage_fresh)
    prng_entered = bool(markers["R88PRBEG"]["fresh"] or prng_returned)
    result["machine_startup_function_entry_witnessed"] = bool(
        result.get("machine_startup_function_entry_witnessed") or reached
    )
    result["kernel_bootstrap_entry_witnessed"] = bool(
        result.get("kernel_bootstrap_entry_witnessed") or reached
    )
    result["kernel_bootstrap_thread_entry_witnessed"] = bool(
        result.get("kernel_bootstrap_thread_entry_witnessed") or reached
    )
    result["current_processor_returned"] = bool(
        result.get("current_processor_returned") or reached
    )
    result["entry_witness_inferred_from"] = reached[-1] if reached else None
    result["prng_bootstrap_entered"] = prng_entered
    result["prng_bootstrap_returned"] = prng_returned
    result["bsd_init_callsite_reached"] = bool(markers["R88BSDC0"]["fresh"])
    result["bsd_init_returned"] = bool(markers["R88BSDRT"]["fresh"])
    if reached:
        result["progress"] = reached[-1]
    result.setdefault("limitations", []).append(
        "R88BSDC0 is before the bsd_init call; it does not prove bsd_init entry. R88BSDRT appears only if bsd_init returns."
    )
    return result


def decode_r89_bsd_init(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R89 bsd_init, mountroot, process-1 and init-program cursors."""
    result = decode_r88_bsd_iokit(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    markers: dict[str, dict[str, object]] = {}
    for name, (slot, expected) in R89_BSD_MARKERS.items():
        value, status, offset = _read_record_word(
            final_data, manifest_data, "early-fault-record", slot * 8
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, "early-fault-record", slot * 8
            )
        markers[name] = {
            "status": ("present" if value == expected else
                       "absent" if value == 0 else
                       status if value is None else "other"),
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": (value == expected and before != expected
                      if baseline_data is not None and before_status == "captured"
                      else None),
            "temporal_owner": "R89 bsd/root/launch cursor; reuses the early carrier after R88BSDC0",
        }
    result["r89_markers"] = markers
    result["bsd_init_entry_witnessed"] = bool(markers["R89BSDI0"]["fresh"])
    result["bsd_init_body_completed"] = bool(markers["R89BSRET"]["fresh"])
    r88_bsd_return = result.get("r88_markers", {}).get("R88BSDRT", {}).get("fresh")
    result["bsd_init_returned"] = bool(r88_bsd_return or markers["R89BTASK"]["fresh"])
    result["mountroot_callsite_reached"] = bool(markers["R89MNTC0"]["fresh"])
    result["root_mount_result"] = (
        "mounted" if markers["R89MNTOK"]["fresh"] else
        "returned-error" if markers["R89MNTER"]["fresh"] else "unknown"
    )
    result["root_vnode_ready"] = bool(markers["R89ROOT0"]["fresh"])
    result["bsd_utaskbootstrap_returned"] = bool(markers["R89UTBS0"]["fresh"])
    result["bsdinit_task_entry_witnessed"] = bool(markers["R89BTASK"]["fresh"])
    result["init_program_callsite_reached"] = bool(markers["R89INIT0"]["fresh"])
    result["load_init_program_returned"] = bool(markers["R89LRET0"]["fresh"])
    reached = [name for name in R89_BSD_MARKERS if markers[name]["fresh"]]
    if reached:
        result["progress"] = reached[-1]
        result["machine_startup_function_entry_witnessed"] = True
        result["kernel_bootstrap_entry_witnessed"] = True
        result["kernel_bootstrap_thread_entry_witnessed"] = True
        result["current_processor_returned"] = True
        result["prng_bootstrap_entered"] = True
        result["prng_bootstrap_returned"] = True
        result["entry_witness_inferred_from"] = reached[-1]
    result.setdefault("limitations", []).append(
        "R89INIT0 is immediately before BL load_init_program and does not prove that launchd was entered or displayed UI."
    )
    return result


def decode_r90_bsd_root(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R90's post-TTY BSD initialization and root-mount milestones."""
    result = decode_r89_bsd_init(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    markers: dict[str, dict[str, object]] = {}
    for name, (slot, expected) in R90_BSD_MARKERS.items():
        value, status, offset = _read_record_word(
            final_data, manifest_data, "early-fault-record", slot * 8
        )
        before = None
        before_status = "unavailable"
        if baseline_data is not None:
            before, before_status, _ = _read_record_word(
                baseline_data, manifest_data, "early-fault-record", slot * 8
            )
        markers[name] = {
            "status": ("present" if value == expected else
                       "absent" if value == 0 else
                       status if value is None else "other"),
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": (value == expected and before != expected
                      if baseline_data is not None and before_status == "captured"
                      else None),
            "reached_by_inference": False,
            "temporal_owner": "R90 BSD/root cursor; replaces earlier handoff slots after each stage",
        }
    observed_by_slot: dict[int, tuple[int | None, bool | None]] = {}
    for name, (slot, _) in R90_BSD_MARKERS.items():
        value = markers[name]["value"]
        observed_by_slot[slot] = (
            None if value is None else int(str(value), 16),
            markers[name]["fresh"],
        )
    for name, successor in R90_SLOT_SUCCESSORS.items():
        slot, expected = R90_BSD_MARKERS[name]
        observed, _ = observed_by_slot[slot]
        successor_value = R90_BSD_MARKERS[successor][1]
        if observed == successor_value:
            markers[name]["status"] = "superseded"
            markers[name]["superseded_by"] = successor
            markers[name]["reached_by_inference"] = (
                markers[successor]["fresh"] is True
            )
    for name, alternate in R90_SLOT_ALTERNATES.items():
        slot, _ = R90_BSD_MARKERS[name]
        observed, _ = observed_by_slot[slot]
        if observed == R90_BSD_MARKERS[alternate][1]:
            markers[name]["status"] = "alternative"
            markers[name]["alternative_observed"] = alternate
    result["r90_markers"] = markers
    reached = [name for name in R90_PROGRESS_ORDER if markers[name]["fresh"] is True]
    if reached:
        result["progress"] = reached[-1]
        result["bsd_init_entry_witnessed"] = True
        result["bsd_init_callsite_reached"] = True
        result["root_mount_callsite_reached"] = bool(
            result.get("root_mount_callsite_reached")
            or markers["R90MNTC0"]["fresh"]
            or markers["R90MNTOK"]["fresh"]
            or markers["R90MNTER"]["fresh"]
            or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[9:])
        )
        result["prng_bootstrap_entered"] = True
        result["prng_bootstrap_returned"] = True
        result["machine_startup_function_entry_witnessed"] = True
        result["kernel_bootstrap_entry_witnessed"] = True
        result["kernel_bootstrap_thread_entry_witnessed"] = True
        result["current_processor_returned"] = True
    result["root_mount_result"] = (
        "mounted" if (markers["R90MNTOK"]["fresh"] is True
                      or any(markers[name]["fresh"] is True
                             for name in R90_PROGRESS_ORDER[9:])) else
        "returned-error" if markers["R90MNTER"]["fresh"] is True else
        result.get("root_mount_result", "unknown")
    )
    result["root_vnode_ready"] = bool(
        result.get("root_vnode_ready")
        or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[9:])
    )
    result["bsd_utaskbootstrap_returned"] = bool(
        result.get("bsd_utaskbootstrap_returned")
        or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[11:])
    )
    result["bsd_init_tail_reached"] = bool(
        markers["R90BSRET"]["fresh"] is True
        or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[13:])
    )
    result["bsd_init_body_completed"] = bool(
        result.get("bsd_init_body_completed")
        or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[13:])
    )
    result["bsd_init_returned"] = bool(
        result.get("bsd_init_returned")
        or result.get("r88_markers", {}).get("R88BSDRT", {}).get("fresh")
        or markers["R90BTASK"]["fresh"]
    )
    result["bsdinit_task_entry_witnessed"] = bool(
        result.get("bsdinit_task_entry_witnessed")
        or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[13:])
    )
    result["init_program_callsite_reached"] = bool(
        result.get("init_program_callsite_reached")
        or any(markers[name]["fresh"] is True for name in R90_PROGRESS_ORDER[15:])
    )
    result["load_init_program_returned"] = bool(
        result.get("load_init_program_returned") or markers["R90LRET0"]["fresh"] is True
    )
    result.setdefault("limitations", []).append(
        "R90 markers sharing one slot are temporal owners. An overwritten earlier marker is only inferred from a fresh later codeword when the linked control flow guarantees that order. R90BSRET is a final in-body cursor, not proof that bsd_init returned; R90BTASK or a later bsdinit_task cursor proves that return boundary."
    )
    return result


def decode_r91_bsd_cursor(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R91's latest cursor; earlier values share and are inferred from slot 37."""
    result = decode_r90_bsd_root(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    slot = R91_BSD_MARKERS[R91_PROGRESS_ORDER[0]][0]
    value, status, offset = _read_record_word(
        final_data, manifest_data, "early-fault-record", slot * 8
    )
    before = None
    before_status = "unavailable"
    if baseline_data is not None:
        before, before_status, _ = _read_record_word(
            baseline_data, manifest_data, "early-fault-record", slot * 8
        )
    owner_by_value = {expected: name for name, (_slot, expected) in R91_BSD_MARKERS.items()}
    current = owner_by_value.get(value)
    cursor_fresh = (
        current is not None and before != value
        if baseline_data is not None and before_status == "captured"
        else None
    )
    current_index = R91_PROGRESS_ORDER.index(current) if current is not None else None
    markers: dict[str, dict[str, object]] = {}
    for name in R91_PROGRESS_ORDER:
        _marker_slot, expected = R91_BSD_MARKERS[name]
        direct = value == expected
        marker_status = (
            "present" if direct else
            "absent" if value == 0 else
            "other"
        )
        inferred = False
        superseded_by = None
        if current is not None and not direct:
            name_index = R91_PROGRESS_ORDER.index(name)
            if name in R91_MOUNT_ALTERNATES:
                alternate = R91_MOUNT_ALTERNATES[name]
                if current == alternate:
                    marker_status = "alternative"
                elif current_index is not None and current_index > R91_PROGRESS_ORDER.index("R91ROOT0"):
                    if name == "R91MNTOK":
                        marker_status = "superseded"
                        inferred = cursor_fresh is True
                        superseded_by = current
                    else:
                        marker_status = "alternative"
            elif current_index is not None and current_index > name_index:
                marker_status = "superseded"
                inferred = cursor_fresh is True
                superseded_by = current
            elif current_index is not None and current_index < name_index:
                marker_status = "not-reached"
        markers[name] = {
            "status": marker_status,
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": cursor_fresh is True and direct,
            "reached_by_inference": inferred,
            "superseded_by": superseded_by,
            "temporal_owner": "R91 single-slot cursor; only the final codeword is direct evidence",
        }
    result["r91_markers"] = markers
    result["r91_cursor"] = {
        "slot": slot,
        "value": None if value is None else hex(value),
        "owner": current,
        "status": "present" if current is not None else ("absent" if value == 0 else status),
        "fresh": cursor_fresh is True,
        "raw_offset": None if offset is None else hex(offset),
        "baseline_value": None if before is None else hex(before),
    }
    result["r91_progress"] = current if cursor_fresh is True else None
    if cursor_fresh is True and current is not None and current_index is not None:
        result["progress"] = current
        result["bsd_init_entry_witnessed"] = True
        if current_index >= R91_PROGRESS_ORDER.index("R91MNTC0"):
            result["root_mount_callsite_reached"] = True
        if current == "R91MNTER":
            result["root_mount_result"] = "returned-error"
        elif current_index >= R91_PROGRESS_ORDER.index("R91ROOT0"):
            result["root_mount_result"] = "mounted"
            result["root_vnode_ready"] = True
        if current_index >= R91_PROGRESS_ORDER.index("R91UTBS0"):
            result["bsd_utaskbootstrap_returned"] = True
        if current_index >= R91_PROGRESS_ORDER.index("R91TAIL0"):
            result["bsd_init_tail_reached"] = True
        if current_index >= R91_PROGRESS_ORDER.index("R91TASK0"):
            result["bsd_init_body_completed"] = True
            result["bsd_init_returned"] = True
            result["bsdinit_task_entry_witnessed"] = True
        if current_index >= R91_PROGRESS_ORDER.index("R91INIT0"):
            result["init_program_callsite_reached"] = True
        if current == "R91LRET0":
            result["load_init_program_returned"] = True
    result.setdefault("limitations", []).append(
        "R91 overwrites one cursor slot. Only the fresh final codeword is direct evidence; earlier milestones are inferred from the linked sequential path. R91LRET0 means load_init_program returned and does not prove that launchd or the Apple logo appeared."
    )
    return result


def decode_r92_bsd_cursor(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode R92 early call/return markers layered over the R91 cursor."""
    result = decode_r91_bsd_cursor(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    slot = R92_BSD_MARKERS["R92TPRE0"][0]
    value, status, offset = _read_record_word(
        final_data, manifest_data, "early-fault-record", slot * 8
    )
    before = None
    before_status = "unavailable"
    if baseline_data is not None:
        before, before_status, _ = _read_record_word(
            baseline_data, manifest_data, "early-fault-record", slot * 8
        )
    owner_by_value = {expected: name for name, (_slot, expected) in R92_BSD_MARKERS.items()}
    current = owner_by_value.get(value)
    direct_fresh = (
        current is not None and before != value
        if baseline_data is not None and before_status == "captured"
        else None
    )
    current_index = R92_PROGRESS_ORDER.index(current) if current is not None else None
    later_r91 = result.get("r91_cursor", {}).get("owner") in R91_PROGRESS_ORDER
    later_r91_fresh = bool(
        later_r91 and result.get("r91_cursor", {}).get("fresh") is True
    )
    markers: dict[str, dict[str, object]] = {}
    for name in R92_PROGRESS_ORDER:
        expected = R92_BSD_MARKERS[name][1]
        direct = value == expected
        name_index = R92_PROGRESS_ORDER.index(name)
        if direct:
            marker_status = "present"
            inferred = False
        elif value == 0:
            marker_status = "absent"
            inferred = False
        elif current_index is not None and current_index > name_index:
            marker_status = "superseded"
            inferred = direct_fresh is True
        elif later_r91_fresh:
            marker_status = "superseded"
            inferred = True
        elif current_index is not None and current_index < name_index:
            marker_status = "not-reached"
            inferred = False
        else:
            marker_status = "other"
            inferred = False
        markers[name] = {
            "status": marker_status,
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": direct and direct_fresh is True,
            "reached_by_inference": inferred,
            "superseded_by": current if inferred else None,
        }
    result["r92_markers"] = markers
    result["r92_cursor"] = {
        "slot": slot,
        "owner": current if current is not None else result.get("r91_cursor", {}).get("owner"),
        "value": None if value is None else hex(value),
        "fresh": bool(direct_fresh is True or later_r91_fresh),
        "raw_offset": None if offset is None else hex(offset),
        "baseline_value": None if before is None else hex(before),
    }
    if direct_fresh is True and current is not None:
        result["r92_progress"] = current
    elif later_r91_fresh:
        result["r92_progress"] = result.get("r91_cursor", {}).get("owner")
    else:
        result["r92_progress"] = None
    result["r92_call_returns"] = {
        "IOKitInitializeTime": (
            "returned" if (markers["R92TOK00"]["fresh"]
                           or any(markers[name]["fresh"] or markers[name]["reached_by_inference"]
                                  for name in R92_PROGRESS_ORDER[2:]))
            else "entered" if markers["R92TPRE0"]["fresh"] else "unknown"
        ),
        "ubc_init": (
            "returned" if (markers["R92UOK00"]["fresh"]
                           or any(markers[name]["fresh"] or markers[name]["reached_by_inference"]
                                  for name in R92_PROGRESS_ORDER[4:]))
            else "entered" if markers["R92UPRE0"]["fresh"] else "unknown"
        ),
        "vfsinit": (
            "returned" if (markers["R92VOK00"]["fresh"]
                           or later_r91_fresh
                           or markers["R92VOK00"]["reached_by_inference"])
            else "entered" if markers["R92VPRE0"]["fresh"] else "unknown"
        ),
    }
    result.setdefault("limitations", []).append(
        "R92 pre-call markers prove the callsite was reached; the matching post-call marker or a later fresh sequential cursor supports return. Missing cursors alone do not diagnose a fault."
    )
    return result


def decode_r93_iokit_time(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode nested IOKitInitializeTime progress from the shared slot37 cursor."""
    result = decode_r92_bsd_cursor(raw, manifest, baseline)
    manifest_data = json.loads(manifest.read_text())
    final_data = raw.read_bytes()
    baseline_data = Path(baseline).read_bytes() if baseline is not None else None
    slot = 37
    value, status, offset = _read_record_word(
        final_data, manifest_data, "early-fault-record", slot * 8
    )
    before = None
    before_status = "unavailable"
    if baseline_data is not None:
        before, before_status, _ = _read_record_word(
            baseline_data, manifest_data, "early-fault-record", slot * 8
        )
    current_owner = next(
        (name for name, (_slot, expected) in R93_BSD_MARKERS.items()
         if value == expected),
        None,
    )
    current_fresh = (
        current_owner is not None and before != value
        if baseline_data is not None and before_status == "captured"
        else None
    )
    owner_after_iokit = None
    r92_owner = result.get("r92_cursor", {}).get("owner")
    if r92_owner in R92_PROGRESS_ORDER:
        r92_index = R92_PROGRESS_ORDER.index(r92_owner)
        if r92_index >= R92_PROGRESS_ORDER.index("R92TOK00"):
            owner_after_iokit = r92_owner
    r91_owner = result.get("r91_cursor", {}).get("owner")
    r91_fresh = bool(r91_owner in R91_PROGRESS_ORDER
                     and result.get("r91_cursor", {}).get("fresh") is True)
    later_r92 = bool(owner_after_iokit and result.get("r92_cursor", {}).get("fresh"))
    later = later_r92 or r91_fresh
    current_index = R93_PROGRESS_ORDER.index(current_owner) if current_owner else None
    markers: dict[str, dict[str, object]] = {}
    for name in R93_PROGRESS_ORDER:
        expected = R93_BSD_MARKERS[name][1]
        direct = value == expected
        name_index = R93_PROGRESS_ORDER.index(name)
        if direct:
            marker_status = "present"
            inferred = False
        elif value == 0:
            marker_status = "absent"
            inferred = False
        elif current_index is not None and current_index > name_index:
            marker_status = "superseded"
            inferred = current_fresh is True
        elif later:
            marker_status = "superseded"
            inferred = True
        elif current_index is not None and current_index < name_index:
            marker_status = "not-reached"
            inferred = False
        else:
            marker_status = "other"
            inferred = False
        markers[name] = {
            "status": marker_status,
            "slot": slot,
            "value": None if value is None else hex(value),
            "expected": hex(expected),
            "raw_offset": None if offset is None else hex(offset),
            "baseline_value": None if before is None else hex(before),
            "fresh": direct and current_fresh is True,
            "reached_by_inference": inferred,
            "superseded_by": (current_owner if inferred and current_owner else
                              r92_owner if inferred and later_r92 else
                              r91_owner if inferred and r91_fresh else None),
        }
    result["r93_markers"] = markers
    result["r93_cursor"] = {
        "slot": slot,
        "owner": current_owner or r92_owner or r91_owner,
        "value": None if value is None else hex(value),
        "fresh": bool(current_fresh is True or later),
        "raw_offset": None if offset is None else hex(offset),
        "baseline_value": None if before is None else hex(before),
    }
    progress = current_owner if current_fresh is True else (
        r92_owner if later_r92 else r91_owner if r91_fresh else None
    )
    result["r93_progress"] = progress
    iokit_returned = (
        current_index is not None and current_index >= R93_PROGRESS_ORDER.index("R93WOK00")
        and current_fresh is True
    ) or later
    wait_returned = (
        current_index is not None and current_index >= R93_PROGRESS_ORDER.index("R93WOK00")
        and current_fresh is True
    ) or later
    resource_returned = (
        current_index is not None and current_index >= R93_PROGRESS_ORDER.index("R93ROK00")
        and current_fresh is True
    ) or later
    clock_returned = (
        current_index is not None and current_index >= R93_PROGRESS_ORDER.index("R93COK00")
        and current_fresh is True
    ) or later
    wait_entered = (
        current_index is not None and current_index >= R93_PROGRESS_ORDER.index("R93WPRE0")
        and current_fresh is True
    ) or later
    if later:
        state = "returned"
    elif current_owner == "R93IENT0":
        state = "entered"
    elif current_owner == "R93RPRE0":
        state = "before-resource-matching"
    elif current_owner == "R93ROK00":
        state = "resource-matched"
    elif current_owner == "R93WPRE0":
        state = "inside-waitForService"
    elif current_owner == "R93WOK00":
        state = "waitForService-returned"
    elif current_owner == "R93CPRE0":
        state = "inside-clock-initialization"
    elif current_owner == "R93COK00":
        state = "calendar-initialized"
    else:
        state = "unknown"
    result["r93_iokit_state"] = state
    result["r93_call_returns"] = {
        "IOService::resourceMatching": "returned" if resource_returned else
            "entered" if current_owner == "R93RPRE0" else "unknown",
        "IOService::waitForService": "returned" if wait_returned else
            "entered" if wait_entered else "unknown",
        "clock_initialize_calendar": "returned" if clock_returned else
            "entered" if current_owner == "R93CPRE0" else "unknown",
        "IOKitInitializeTime": "returned" if iokit_returned else
            "entered" if current_owner in R93_PROGRESS_ORDER else "unknown",
    }
    result.setdefault("limitations", []).append(
        "R93 cursor records are sequential direct/inferred milestones; a missing post-call codeword localizes an unclosed interval but does not by itself prove a fault."
    )
    return result


def verify_r83_capture(
    raw: Path | None, manifest: Path | None, baseline: Path | None
) -> list[str]:
    """Validate R83's paired capture layout without requiring later boot phases."""
    if raw is None:
        return []
    if manifest is None or baseline is None:
        return ["R83 raw capture requires both --manifest and a matching --baseline"]
    manifest_data = json.loads(manifest.read_text())
    if manifest_data.get("transport_mode") != "minimal-boundary":
        return ["R83 capture requires the minimal-boundary transport geometry"]
    records = manifest_data.get("records", [])
    named = {name: [record for record in records if record.get("name") == name]
             for name in ("early-fault-record", ENTRY_PATH_WINDOW_RECORD,
                          "_y35a_bootstrap_phase")}
    failures = []
    if any(len(named[name]) != 1 for name in named):
        return ["R83 manifest must contain one early carrier, entry-path-window, and phase record"]
    try:
        early, path, phase = (named[name][0] for name in
                              ("early-fault-record", ENTRY_PATH_WINDOW_RECORD,
                               "_y35a_bootstrap_phase"))
        early_physical = int(early["physical"], 0)
        path_physical = int(path["physical"], 0)
        early_size = int(early["size"])
        path_size = int(path["size"])
        phase_size = int(phase["size"])
        phase_width = int(phase["field_bytes"])
        path_offset = _record_raw_offset(manifest_data, path)
        early_offset = _record_raw_offset(manifest_data, early)
        phase_offset = _record_raw_offset(manifest_data, phase)
        report_bytes = int(manifest_data["report_bytes"])
    except (KeyError, TypeError, ValueError):
        return ["R83 manifest has invalid named-record geometry"]
    if early_size != EARLY_RECORD_BYTES:
        failures.append(f"R83 early-fault-record size is {early_size}, expected {EARLY_RECORD_BYTES}")
    if path_size != ENTRY_PATH_WINDOW_BYTES:
        failures.append(f"R83 entry-path-window size is {path_size}, expected {ENTRY_PATH_WINDOW_BYTES}")
    if path_physical != early_physical + ENTRY_PATH_WINDOW_BASE_SLOT * 8:
        failures.append("R83 entry-path-window does not map physical slots 64/65")
    if phase_width != 8 or phase_size != 16:
        failures.append("R83 phase record must be an 8-byte field in a 16-byte window")
    for name, record, offset, size in (
        ("early-fault-record", early, early_offset, early_size),
        (ENTRY_PATH_WINDOW_RECORD, path, path_offset, path_size),
        ("_y35a_bootstrap_phase", phase, phase_offset, phase_size),
    ):
        try:
            report_offset = int(record["report_offset"])
            stage_offset = int(record["stage_offset"])
            declared_offset = int(record["offset"])
        except (KeyError, TypeError, ValueError):
            failures.append(f"R83 record {name} has incomplete report/stage offsets")
            continue
        if offset != RAW_STAGE_BASE_OFFSET + report_offset:
            failures.append(f"R83 record {name} raw offset disagrees with report_offset")
        if stage_offset != offset or declared_offset != offset:
            failures.append(f"R83 record {name} offset and stage_offset disagree")
        if report_offset < 0 or report_offset + size > report_bytes:
            failures.append(f"R83 record {name} is outside report_bytes")
        if offset < 0 or offset + size > raw.stat().st_size:
            failures.append(f"R83 record {name} is outside the final raw capture")
        if offset < 0 or offset + size > baseline.stat().st_size:
            failures.append(f"R83 record {name} is outside the baseline raw capture")
    if early_offset < 0 or path_offset < 0 or phase_offset < 0:
        failures.append("R83 record has a negative raw offset")
    raw_data = raw.read_bytes()
    baseline_data = baseline.read_bytes()
    counter_offset = MINIMAL_FRESHNESS_WITNESS_RAW_OFFSET
    if counter_offset + 8 > len(raw_data) or counter_offset + 8 > len(baseline_data):
        failures.append("R83 capture is too short for the retained CNTVCT freshness witness")
    else:
        final_counter = int.from_bytes(raw_data[counter_offset:counter_offset + 8], "little")
        baseline_counter = int.from_bytes(
            baseline_data[counter_offset:counter_offset + 8], "little"
        )
        if final_counter == 0 or baseline_counter == 0 or final_counter == baseline_counter:
            failures.append("R83 baseline/final CNTVCT witnesses are not distinct nonzero captures")
    return failures


def _terminal_record_freshness(
    raw: Path, baseline: Path, manifest: Path
) -> dict[str, object]:
    manifest_data = json.loads(manifest.read_text())
    records = [record for record in manifest_data.get("records", [])
               if record.get("name") == "early-fault-record"]
    if len(records) != 1:
        return {"status": "unavailable", "fresh": False}
    record = records[0]
    try:
        offset = _record_raw_offset(manifest_data, record)
        size = int(record["size"])
        final = raw.read_bytes()
        before = baseline.read_bytes()
    except (KeyError, TypeError, ValueError, OSError):
        return {"status": "unavailable", "fresh": False}
    if size < 4 * 8 or offset < 0 or offset + 4 * 8 > min(len(final), len(before)):
        return {"status": "truncated", "fresh": False}
    marker = int.from_bytes(final[offset:offset + 8], "little")
    baseline_marker = int.from_bytes(before[offset:offset + 8], "little")
    terminal = marker in TERMINAL_LINK_REGISTER_MAGICS
    # Slot 4 is not terminal-owned in every run: first_cpu may leave R83ENT00
    # there. Only compare flag plus ELR/ESR/FAR when establishing a new record.
    payload_changed = final[offset:offset + 4 * 8] != before[offset:offset + 4 * 8]
    return {
        "status": "present" if terminal else "absent",
        "marker": hex(marker),
        "baseline_marker": hex(baseline_marker),
        "payload_changed": payload_changed,
        "fresh": bool(terminal and payload_changed),
    }


def verify_fresh_generation_markers(
    raw: Path, baseline: Path, manifest: Path
) -> dict[str, object]:
    """Compare generation witnesses against the pre-boot capture.

    A final codeword is fresh only when that exact codeword was absent in the
    matching baseline. A zero final marker is a valid negative observation,
    not a transport error; callers can still read the baseline/final statuses.
    """
    final = decode_boundary_markers(raw, manifest)
    before = decode_boundary_markers(baseline, manifest)
    markers: dict[str, dict[str, object]] = {}
    failures: list[str] = []
    required = ("ARMENTRY", "PREMMU00", "SCTLRRD0")
    optional = tuple(ENTRY_PATH_MARKERS)

    def current_generation(name: str, observation: dict[str, object]) -> bool:
        if name in PREVIOUS_GENERATION_MARKERS or name in ("ARMENTRY", "PREMMU00"):
            return observation.get("generation") == "current"
        return observation.get("status") == "present"

    for name in (*required, *optional):
        final_status = final.get(name, {}).get("status", "unavailable")
        baseline_status = before.get(name, {}).get("status", "unavailable")
        if (name == "ARMENTRY"
                and final_status == "overwritten-by-terminal-link-register"):
            terminal_freshness = _terminal_record_freshness(raw, baseline, manifest)
            markers[name] = {
                "baseline_status": baseline_status,
                "final_status": final_status,
                "fresh": False,
                "entry_freshness": "unobservable-slot4-owned-by-terminal-link-register",
                "terminal_record_freshness": terminal_freshness,
            }
            if not terminal_freshness.get("fresh"):
                failures.append(
                    "terminal record takes slot4 ownership but has no fresh payload change"
                )
            continue
        if name in ("ARMENTRY", "PREMMU00"):
            fresh = (final.get(name, {}).get("generation") == "current"
                     and before.get(name, {}).get("generation") != "current")
        elif name in PREVIOUS_GENERATION_MARKERS:
            fresh = (current_generation(name, final.get(name, {}))
                     and not current_generation(name, before.get(name, {})))
        else:
            fresh = final_status == "present" and baseline_status != "present"
        markers[name] = {
            "baseline_status": baseline_status,
            "final_status": final_status,
            "fresh": fresh,
        }
        if name in required and baseline_status in ("unavailable", "truncated"):
            failures.append(f"baseline {name} marker is {baseline_status}")
        if name in required and final_status in ("unavailable", "truncated"):
            failures.append(f"final {name} marker is {final_status}")
        baseline_current = (
            current_generation(name, before.get(name, {}))
            if name in PREVIOUS_GENERATION_MARKERS or name in ("ARMENTRY", "PREMMU00")
            else baseline_status == "present"
        )
        if name in required and baseline_current:
            failures.append(f"baseline already contains the current-generation {name} codeword")
        if name in required and not fresh:
            failures.append(f"final {name} is not fresh")
    for name in ("FPBEFOR0", "FPSTOR00", "PUBLPR00", "PUBLPS00",
                 "PTBASE00", "PTCOUNT0", "PTSHIFT0"):
        final_observation = final.get(name, {})
        baseline_observation = before.get(name, {})
        final_status = final_observation.get("status", "unavailable")
        baseline_status = baseline_observation.get("status", "unavailable")
        final_value = final_observation.get("value")
        baseline_value = baseline_observation.get("value")
        final_current = current_generation(name, final_observation)
        baseline_current = current_generation(name, baseline_observation)
        fresh = (final_current
                 and not baseline_current
                 and baseline_status not in ("unavailable", "truncated"))
        markers[name] = {
            "baseline_status": baseline_status,
            "final_status": final_status,
            "baseline_value": baseline_value,
            "final_value": final_value,
            "fresh": fresh,
        }
        if final_current and baseline_current:
            failures.append(f"baseline already contains the current-generation {name} codeword")
        if name in ("FPSTOR00", "PUBLPR00", "PUBLPS00",
                    "PTBASE00", "PTCOUNT0", "PTSHIFT0") and final_current and not fresh:
            failures.append(f"final {name} is not fresh")
    sctlr = decode_sctlr_el1(raw, manifest)
    markers["SCTLR_EL1"] = sctlr
    if sctlr.get("status") != "captured" or not sctlr.get("mmu_enabled"):
        failures.append(f"SCTLR_EL1.M is not proven enabled: {sctlr}")
    records = {record.get("name") for record in json.loads(manifest.read_text()).get("records", [])}
    if R68E7_STORE_WINDOW_RECORD in records:
        primary = decode_r68e7_low_carrier(raw, manifest, baseline)
        markers["R68E7_LOW_CARRIER"] = primary
        if primary.get("stage") not in R68E7_LOW_STAGE_MARKERS.values():
            failures.append(
                f"R68E7 primary low-carrier stage marker is absent: {primary.get('status')}"
            )
        else:
            if not primary.get("stage_fresh"):
                failures.append("R68E7 low-carrier stage marker is absent from baseline or not fresh")
            if primary.get("stage") != "store-readback-complete":
                failures.append("R68E7 direct-store load-back stage was not completed")
            if not primary.get("live_payload_fields_match_contract"):
                failures.append(
                    f"R68E7 low-carrier surviving fields fail their slot contracts: {primary}"
                )
            if (primary.get("stage") == "store-readback-complete"
                    and not primary.get("loadback_valid_or_overwritten")):
                failures.append(
                    "R68E7 same-boot immediate load-back does not match the expected payload"
                )
            if not primary.get("low_payload_available") and not primary.get("c_phase_overwrites"):
                failures.append("R68E7 low-carrier payload is unavailable without a fresh C-phase overwrite")

        # The separate +0xa40 window is retained as an auxiliary cross-check.
        store_window = decode_r68e7_store_window(raw, manifest, baseline)
        markers["R68E7_HIGH_WINDOW_AUX"] = {
            "status": store_window.get("status"),
            "baseline_value": store_window.get("baseline_snapshot_marker"),
            "final_value": store_window.get("snapshot_marker"),
            "snapshot_fresh": store_window.get("snapshot_fresh", False),
            "readback_value": store_window.get("readback_marker"),
            "readback_fresh": store_window.get("readback_fresh", False),
            "authoritative": False,
        }
        alias = decode_r68e7_alias_witnesses(raw, manifest, baseline)
        markers["KVAON000"] = {
            "baseline_value": alias.get("baseline_kva_alias_marker"),
            "final_value": alias.get("kva_alias_marker"),
            "fresh": alias.get("kva_alias_fresh", False),
        }
        if (alias.get("sctlr_el1", {}).get("mmu_enabled")
                and not alias.get("kva_alias_fresh")):
            failures.append("SCTLR.M is set but the separate KVA alias marker is absent or stale")
    return {"markers": markers, "failures": failures}


def decode_fault_publish_operands(raw: Path, manifest: Path) -> dict[str, object]:
    """Return raw ADRP/ADD, payload, candidate PA, and post-store diagnostic-window evidence."""
    manifest_data = json.loads(manifest.read_text())
    early = next((item for item in manifest_data.get("records", [])
                  if item.get("name") == "early-fault-record"), None)
    if early is None:
        return {"status": "unavailable", "reason": "early-fault-record missing"}
    try:
        early_raw_offset = _record_raw_offset(manifest_data, early)
        early_size = int(early.get("size", 0))
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable", "reason": "early-fault-record geometry missing"}
    data = raw.read_bytes()
    if early_size < 8 or early_raw_offset < 0 or early_raw_offset + 8 > len(data):
        return {"status": "truncated", "reason": "early-fault flag unavailable"}
    fault_flag = int.from_bytes(data[early_raw_offset:early_raw_offset + 8], "little")
    if fault_flag != 1:
        if fault_flag != 0:
            return {"status": "invalid", "fault_flag": hex(fault_flag)}
    record = next((item for item in manifest_data.get("records", [])
                   if item.get("name") == FAULT_PUBLISH_WINDOW_RECORD), None)
    if record is None:
        return {"status": "unavailable"}
    try:
        physical = int(record["physical"], 0)
        size = int(record["size"])
        offset = _record_raw_offset(manifest_data, record)
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable"}
    if size < FAULT_PUBLISH_WINDOW_BYTES:
        return {"status": "truncated", "physical": hex(physical), "size": size}
    raw_offset = offset
    if raw_offset < 0 or raw_offset + FAULT_PUBLISH_WINDOW_BYTES > len(data):
        return {"status": "truncated", "physical": hex(physical),
                "raw_offset": hex(raw_offset), "size": size}
    words = [
        int.from_bytes(data[raw_offset + index * 8:raw_offset + (index + 1) * 8], "little")
        for index in range(6)
    ]
    if fault_flag == 0 and not any(words):
        return {"status": "not-applicable", "fault_flag": "0x0"}
    if early_size < 31 * 8 or early_raw_offset < 0 or early_raw_offset + 31 * 8 > len(data):
        return {"status": "truncated", "reason": "boot-args arithmetic witnesses unavailable"}
    x22 = int.from_bytes(data[early_raw_offset + 29 * 8:early_raw_offset + 30 * 8], "little")
    x23 = int.from_bytes(data[early_raw_offset + 30 * 8:early_raw_offset + 31 * 8], "little")
    pointer = next((item for item in manifest_data.get("records", [])
                    if item.get("name") == FAULT_POINTER_WINDOW_RECORD), None)
    if pointer is None:
        return {"status": "unavailable", "reason": "fault-pointer-window missing"}
    pointer_raw_offset = _record_raw_offset(manifest_data, pointer)
    pointer_size = int(pointer.get("size", 0))
    try:
        symbol_offset = int(pointer["symbol_offset"])
        expected_global_physical = int(pointer["symbol_physical"], 0)
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable", "reason": "fault-pointer-window symbol binding missing"}
    if symbol_offset < 0 or symbol_offset + 8 > pointer_size or pointer_raw_offset < 0 or pointer_raw_offset + pointer_size > len(data):
        return {"status": "truncated", "reason": "fault-pointer-window unavailable"}
    published_global_value = int.from_bytes(
        data[pointer_raw_offset + symbol_offset:pointer_raw_offset + symbol_offset + 8],
        "little",
    )
    raw_global = words[0]
    candidate = words[2]
    raw_form = (
        "physical" if raw_global == expected_global_physical
        else "virtual" if candidate == expected_global_physical
        else "other"
    )
    return {
        "status": "captured",
        "fault_flag": hex(fault_flag),
        "physical": hex(physical),
        "raw_offset": hex(raw_offset),
        "raw_global_address": hex(words[0]),
        "fault_payload": hex(words[1]),
        "translated_global_candidate": hex(words[2]),
        "x22_kva_base": hex(x22),
        "x23_pa_base": hex(x23),
        "translated_candidate_matches_formula": candidate == ((raw_global - x22 + x23) & 0xFFFFFFFFFFFFFFFF),
        "formula_qualification": "diagnostic only; slot29/30 freshness is reported separately",
        "global_address_form": raw_form,
        "expected_global_physical": hex(expected_global_physical),
        "global_symbol_offset": symbol_offset,
        "published_global_value": hex(published_global_value),
        "diagnostic_start_marker": "present" if words[3] == HANDOFF_MARKERS["PUBLPR00"][1]
        else "zero" if words[3] == 0 else "other",
        "diagnostic_start_value": hex(words[3]),
        "diagnostic_complete_marker": "present" if words[4] == HANDOFF_MARKERS["PUBLPS00"][1]
        else "zero" if words[4] == 0 else "other",
        "diagnostic_complete_value": hex(words[4]),
        "reserved_slot63_value": hex(words[5]),
    }


def decode_fault_publish_pre_store(
    raw: Path, manifest: Path, baseline: Path | None = None
) -> dict[str, object]:
    """Decode the low-carrier x9 candidate and state whether it was overwritten."""
    manifest_data = json.loads(manifest.read_text())
    early = next((item for item in manifest_data.get("records", [])
                  if item.get("name") == "early-fault-record"), None)
    pointer = next((item for item in manifest_data.get("records", [])
                    if item.get("name") == FAULT_POINTER_WINDOW_RECORD), None)
    if early is None or pointer is None:
        return {"status": "unavailable", "reason": "early-fault or pointer window missing"}
    try:
        offset = _record_raw_offset(manifest_data, early)
        size = int(early["size"])
        early_physical = int(early["physical"], 0)
        expected_global = int(pointer["symbol_physical"], 0)
    except (KeyError, TypeError, ValueError):
        return {"status": "unavailable", "reason": "pre-store witness geometry missing"}
    data = raw.read_bytes()
    required_size = (FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT + 1) * 8
    if size < required_size or offset < 0 or offset + required_size > len(data):
        return {"status": "truncated", "reason": "slot45 or boot-args base witness unavailable"}

    def value_at(blob: bytes, base_offset: int, slot: int) -> int:
        start = base_offset + slot * 8
        return int.from_bytes(blob[start:start + 8], "little")

    marker = value_at(data, offset, 43)
    candidate = value_at(data, offset, FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT)
    x22 = value_at(data, offset, 29)
    x23 = value_at(data, offset, 30)
    marker_status = (
        "current" if marker == HANDOFF_MARKERS["FPBEFOR0"][1]
        else "overwritten-by-PTBASE00" if marker == HANDOFF_MARKERS["PTBASE00"][1]
        else "zero" if marker == 0 else "other"
    )

    candidate_overwritten_by = next(
        (name for name in ("LRADD000", "PTSHIFT0")
         if candidate == HANDOFF_MARKERS[name][1]),
        None,
    )
    if candidate_overwritten_by:
        status = "overwritten"
    elif marker_status == "current":
        status = "captured" if candidate else "zero"
    elif marker_status.startswith("overwritten"):
        status = "marker-overwritten"
    elif marker_status == "zero":
        status = "unmarked"
    else:
        status = "other"

    baseline_base_status = "not-compared"
    baseline_x22 = baseline_x23 = None
    if baseline is not None:
        baseline_data = baseline.read_bytes()
        baseline_offset = _record_raw_offset(manifest_data, early)
        if baseline_offset >= 0 and baseline_offset + 31 * 8 <= len(baseline_data):
            baseline_x22 = value_at(baseline_data, baseline_offset, 29)
            baseline_x23 = value_at(baseline_data, baseline_offset, 30)
            baseline_base_status = (
                "unchanged" if (x22, x23) == (baseline_x22, baseline_x23)
                else "changed"
            )
        else:
            baseline_base_status = "unavailable"

    reconstructed_global = (candidate + x22 - x23) & 0xFFFFFFFFFFFFFFFF
    expected_candidate_if_physical = (expected_global - x22 + x23) & 0xFFFFFFFFFFFFFFFF
    if reconstructed_global == expected_global:
        conditional_form = "physical-if-slot-bases-are-current"
    elif candidate == expected_global:
        conditional_form = "virtual-if-slot-bases-are-current"
    else:
        conditional_form = "other-if-slot-bases-are-current"
    return {
        "status": status,
        "physical": hex(early_physical + FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT * 8),
        "raw_offset": hex(offset + FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT * 8),
        "marker_value": hex(marker),
        "pre_store_marker_status": marker_status,
        "marker_matches_current": marker == HANDOFF_MARKERS["FPBEFOR0"][1],
        "x9_candidate": hex(candidate),
        "candidate_overwritten_by": candidate_overwritten_by,
        "x22_kva_base": hex(x22),
        "x23_pa_base": hex(x23),
        "base_slots_vs_baseline": baseline_base_status,
        "baseline_x22_kva_base": None if baseline_x22 is None else hex(baseline_x22),
        "baseline_x23_pa_base": None if baseline_x23 is None else hex(baseline_x23),
        "reconstructed_x16_conditional": hex(reconstructed_global),
        "expected_global_physical": hex(expected_global),
        "expected_x9_if_x16_is_physical_and_bases_current": hex(expected_candidate_if_physical),
        "conditional_address_form": conditional_form,
        "reconstruction_is_runtime_proof": False,
    }



def verify_raw(
    raw: Path | None, manifest: Path | None, baseline: Path | None = None,
    *, require_r68e7_low_carrier: bool = False,
    require_capture_binding: bool = False,
) -> list[str]:
    if raw is None:
        return []
    if manifest is None:
        return ["raw verification requires the matching readback manifest"]
    manifest_data = json.loads(manifest.read_text())
    records = {record["name"]: record for record in manifest_data.get("records", [])}
    early = records.get("early-fault-record")
    if early is None:
        return ["raw verification manifest is missing early-fault-record"]
    relative = (
        int(early.get("report_offset", 0))
        if manifest_data.get("transport_mode") == "minimal-boundary"
        else int(early.get("offset", -1))
    )
    if relative < 0:
        return ["raw verification manifest has no carrier offset"]
    carrier_offset = (
        relative
        if manifest_data.get("transport_mode") == "full-readback"
        else RAW_STAGE_BASE_OFFSET + relative
    )
    data = raw.read_bytes()
    failures = []
    if require_capture_binding:
        failures.extend(verify_capture_kernel_binding(raw, manifest))
    if len(data) < carrier_offset + EARLY_RECORD_BYTES:
        return [f"raw capture is too short for carrier offset {carrier_offset:#x}"]
    fault = int.from_bytes(data[carrier_offset:carrier_offset + 8], "little")
    if fault not in (0, 1) and fault not in TERMINAL_FAULT_MAGICS:
        failures.append(f"raw early-fault flag is {fault:#x}, not 0 or 1")
    observations = decode_boundary_markers(raw, manifest)
    records = {record.get("name"): record for record in manifest_data.get("records", [])}
    low_carrier = None
    if R68E7_STORE_WINDOW_RECORD in records:
        low_carrier = decode_r68e7_low_carrier(raw, manifest, baseline)
    low_carrier_owns_slots = bool(
        low_carrier
        and low_carrier.get("stage") in R68E7_LOW_STAGE_MARKERS.values()
        and low_carrier.get("stage_fresh")
    )
    low_carrier_proves_store_return = bool(
        low_carrier_owns_slots
        and low_carrier.get("stage") == "store-readback-complete"
        and low_carrier.get("live_payload_fields_match_contract")
        and low_carrier.get("loadback_valid_or_overwritten")
    )
    low_carrier_alias_slots = (
        {slot for slot, _ in R68E7_LOW_C_PHASE_MARKERS.items()}
        if low_carrier_owns_slots else set()
    )
    optional = {"FIRST_CPU", "PUBLPR00", "PUBLPS00"}
    for name, observation in observations.items():
        # During the retained R68E7 pre-MMU snapshot, slots5..10 hold live
        # operands. Nonzero register values in those addresses are not failed
        # C-phase marker codewords; a true marker requires an exact match.
        phase_marker = PHASE_MARKERS.get(name)
        if (phase_marker is not None and phase_marker[0] in low_carrier_alias_slots
                and observation["status"] == "other"):
            continue
        if name in optional and fault == 0:
            continue
        if name in ("FPBEFOR0", "FPSTOR00") and observation["status"] == "overwritten":
            continue
        if (name == "ARMENTRY"
                and observation["status"] == "overwritten-by-terminal-link-register"):
            continue
        if observation["status"] in ("unavailable", "truncated"):
            failures.append(f"raw {name} marker is {observation['status']}")
        elif observation["status"] == "other":
            failures.append(
                f"raw {name} marker is {observation['value']}, expected "
                f"{observation['expected']} or zero"
            )
    armentry = observations.get("ARMENTRY", {})
    armentry_is_fault_lr = armentry.get("status") == "overwritten-by-terminal-link-register"
    if (not armentry_is_fault_lr
            and (armentry.get("status") != "present" or armentry.get("generation") != "current")):
        failures.append(f"raw capture is missing the current ARMENTRY cold-entry witness: {armentry}")
    premmu = observations.get("PREMMU00", {})
    if premmu.get("status") != "present" or premmu.get("generation") != "current":
        failures.append(f"raw PREMMU00 is not the current R68E7 marker: {premmu}")
    post = observations.get("SCTLRRD0", {})
    if post.get("status") != "present":
        failures.append(f"raw SCTLRRD0 post-ISB witness is {post.get('status')}")
    sctlr = decode_sctlr_el1(raw, manifest)
    if sctlr.get("status") != "captured" or not sctlr.get("mmu_enabled"):
        failures.append(f"SCTLR.M is not proven enabled: {sctlr}")

    publish_window = decode_fault_publish_operands(raw, manifest)
    if fault == 1 and publish_window.get("status") != "captured":
        failures.append(f"raw fault-publish-window is {publish_window.get('status')}")
    elif publish_window.get("status") == "captured":
        for field in ("raw_global_address", "fault_payload", "translated_global_candidate"):
            if publish_window[field] == "0x0":
                failures.append(f"raw fault-publish-window {field} is zero")
        if publish_window["diagnostic_start_marker"] != "present":
            failures.append(f"raw PUBLPR00 marker is {publish_window['diagnostic_start_marker']}")
        if publish_window["diagnostic_complete_marker"] == "other":
            failures.append(
                "raw PUBLPS00 marker is unexpected "
                f"{publish_window['diagnostic_complete_value']}"
            )
        if publish_window["global_address_form"] != "physical":
            failures.append(
                "direct MMU-off global address does not match the bound physical symbol "
                f"({publish_window['raw_global_address']} != {publish_window['expected_global_physical']})"
            )
        if publish_window["published_global_value"] != publish_window["fault_payload"]:
            failures.append(
                "fault-pointer readback does not equal the captured publish payload "
                f"({publish_window['published_global_value']} != {publish_window['fault_payload']})"
            )
    store_status = observations.get("FPSTOR00", {}).get("status")
    if publish_window.get("status") != "captured":
        if store_status == "present" and not low_carrier_proves_store_return:
            failures.append("fresh FPSTOR00 proves the direct store returned, but the post-store operand window is missing")
        elif store_status == "overwritten" and not low_carrier_proves_store_return:
            failures.append("FPSTOR00 slot has a later alias, but the post-store operand window is missing")
    if require_r68e7_low_carrier and R68E7_STORE_WINDOW_RECORD in records:
        primary = decode_r68e7_low_carrier(raw, manifest, baseline)
        if primary.get("stage") not in R68E7_LOW_STAGE_MARKERS.values():
            failures.append(f"R68E7 low-carrier stage marker is absent: {primary.get('status')}")
        elif primary.get("stage") != "store-readback-complete":
            failures.append("R68E7 direct-store load-back stage was not completed")
        else:
            if not primary.get("live_payload_fields_match_contract"):
                failures.append(f"R68E7 low-carrier surviving fields violate their slot contracts: {primary}")
            if not primary.get("loadback_valid_or_overwritten"):
                failures.append(
                    f"R68E7 same-boot immediate load-back does not match the expected payload: {primary}"
                )
            if not primary.get("low_payload_available") and not primary.get("c_phase_overwrites"):
                failures.append("R68E7 low-carrier operands are unavailable without a C-phase overwrite witness")
    if R68E7_STORE_WINDOW_RECORD in records:
        # The +0xa40 window remains diagnostic only; its absence cannot negate
        # the retained low-carrier stage witness.
        alias = decode_r68e7_alias_witnesses(raw, manifest, baseline)
        if alias.get("sctlr_el1", {}).get("mmu_enabled") and not alias.get("kva_alias_present"):
            failures.append("SCTLR.M is set but the R68E7 KVA alias witness is absent")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--probe", type=Path,
                        help="probe image whose SHA-256 must match manifest image_sha256")
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--baseline", type=Path,
                        help="matching pre-boot capture for generation-marker freshness comparison")
    parser.add_argument("--require-r82-arm-cursor", action="store_true",
                        help="require an R82ARM00 call before the ARMINITE slot-5 store")
    parser.add_argument("--require-r83-entry-ladder", action="store_true",
                        help="validate R83ENT00/R83FS00/R83CIN00 and decode paired R83 captures")
    parser.add_argument("--require-r84-entry-ladder", action="store_true",
                        help="validate R84 snapshots/setter return and decode paired R84 captures")
    parser.add_argument("--require-r85-machine-startup", action="store_true",
                        help="validate late-setter and machine_startup entry/return markers")
    parser.add_argument("--require-r86-startup-cursor", action="store_true",
                        help="validate direct machine_startup/kernel_bootstrap entry and return cursors")
    parser.add_argument("--require-r87-startup-cursor", action="store_true",
                        help="validate kernel_bootstrap and kernel_bootstrap_thread startup cursors")
    parser.add_argument("--require-r88-bsd-iokit-cursor", action="store_true",
                        help="validate kernel_bootstrap_thread through BSD/IOKit startup cursors")
    parser.add_argument("--require-r89-bsd-init-cursor", action="store_true",
                        help="validate bsd_init, root-mount and launch-program cursors")
    parser.add_argument("--require-r90-root-cursor", action="store_true",
                        help="validate BSD pre-root and vfs_mountroot cursors")
    parser.add_argument("--require-r91-bsd-cursor", action="store_true",
                        help="validate R91's post-FPX single-slot BSD/root cursor")
    parser.add_argument("--require-r92-bsd-cursor", action="store_true",
                        help="validate R92 pre-call and return cursors after bsd_bufferinit")
    parser.add_argument("--require-r93-iokit-cursor", action="store_true",
                        help="validate nested R93 IOKitInitializeTime cursors")
    args = parser.parse_args()

    failures = []
    require_r93 = args.require_r93_iokit_cursor
    if require_r93 and (args.require_r92_bsd_cursor or args.require_r91_bsd_cursor
                        or args.require_r90_root_cursor):
        failures.append("R93 includes R90 through R92 contracts; select only the R93 generation flag")
    if require_r93:
        args.require_r90_root_cursor = True
        args.require_r91_bsd_cursor = True
        args.require_r92_bsd_cursor = True
    require_r92 = args.require_r92_bsd_cursor
    if require_r92 and (args.require_r91_bsd_cursor or args.require_r90_root_cursor) and not require_r93:
        failures.append("R92 includes R90 and R91 contracts; select only the R92 generation flag")
    if require_r92:
        args.require_r90_root_cursor = True
        args.require_r91_bsd_cursor = True
    require_r91 = args.require_r91_bsd_cursor
    if require_r91 and args.require_r90_root_cursor and not require_r92:
        failures.append("R91 includes the R90 contract; select only one generation flag")
    if require_r91:
        args.require_r90_root_cursor = True
    selected_generations = sum((args.require_r82_arm_cursor,
                                args.require_r83_entry_ladder,
                                args.require_r84_entry_ladder or
                                args.require_r85_machine_startup or
                                args.require_r86_startup_cursor or
                                args.require_r87_startup_cursor or
                                args.require_r88_bsd_iokit_cursor or
                                args.require_r89_bsd_init_cursor or
                                args.require_r90_root_cursor))
    if selected_generations > 1:
        failures.append("R82 through R93 generation-specific contracts are mutually exclusive")
    failures.extend(verify_carrier_slot_contract())
    try:
        symbols = nm_symbol_addresses(args.kernel)
        if "_native_early_fault_address" not in symbols:
            failures.append("missing _native_early_fault_address symbol")
        disassembly = disassemble_kernel(args.kernel)
        first_cpu_body = start_first_cpu_body(args.kernel, disassembly)
        if args.require_r83_entry_ladder:
            entry_marker = R83_ENTRY_MARKER
            first_cpu_marker = R83_FIRST_CPU_MARKER
        elif (args.require_r84_entry_ladder or args.require_r85_machine_startup
              or args.require_r86_startup_cursor or args.require_r87_startup_cursor
              or args.require_r88_bsd_iokit_cursor or args.require_r89_bsd_init_cursor
              or args.require_r90_root_cursor):
            entry_marker = R84_ENTRY_MARKER
            first_cpu_marker = R84_FIRST_CPU_MARKER
        elif args.require_r82_arm_cursor:
            entry_marker = ENTRY_MARKER
            first_cpu_marker = ENTRY_PATH_MARKERS["FIRST_CPU"][1]
        else:
            entry_marker = None
            first_cpu_marker = None
        failures.extend(verify_entry_witness(
            first_cpu_body, expected_marker=entry_marker,
        ))
        failures.extend(verify_first_cpu_path_witness(
            first_cpu_body, expected_marker=first_cpu_marker,
        ))
        failures.extend(verify_fault_publish_disassembly(first_cpu_body))
        failures.extend(verify_r68e7_store_window_disassembly(first_cpu_body))
        failures.extend(verify_r68e7_low_carrier_disassembly(first_cpu_body))
        failures.extend(verify_secondary_entry_witness(start_cpu_body(args.kernel, disassembly)))
        handoff_body = first_cpu_body + "\n" + common_start_body(args.kernel, disassembly)
        failures.extend(verify_handoff_disassembly(handoff_body))
        arm_body = arm_init_body(args.kernel, disassembly)
        failures.extend(verify_disassembly(
            arm_body,
            require_r82_cursor=args.require_r82_arm_cursor,
            require_r83_cursor=args.require_r83_entry_ladder,
            require_r84_cursor=(args.require_r84_entry_ladder
                                or args.require_r85_machine_startup
                                or args.require_r86_startup_cursor
                                or args.require_r87_startup_cursor
                                or args.require_r88_bsd_iokit_cursor
                                or args.require_r89_bsd_init_cursor
                                or args.require_r90_root_cursor),
            require_r85_cursor=(args.require_r85_machine_startup
                                or args.require_r86_startup_cursor
                                or args.require_r87_startup_cursor
                                or args.require_r88_bsd_iokit_cursor
                                or args.require_r89_bsd_init_cursor
                                or args.require_r90_root_cursor),
        ))
        if (args.require_r86_startup_cursor or args.require_r87_startup_cursor
                or args.require_r88_bsd_iokit_cursor or args.require_r89_bsd_init_cursor
                or args.require_r90_root_cursor):
            failures.extend(verify_r86_startup_disassembly(disassembly))
        if (args.require_r87_startup_cursor or args.require_r88_bsd_iokit_cursor
                or args.require_r89_bsd_init_cursor or args.require_r90_root_cursor):
            failures.extend(verify_r87_bootstrap_thread_disassembly(disassembly))
        if (args.require_r88_bsd_iokit_cursor or args.require_r89_bsd_init_cursor
                or args.require_r90_root_cursor):
            failures.extend(verify_r88_bsd_iokit_disassembly(disassembly))
        if args.require_r89_bsd_init_cursor:
            failures.extend(verify_r89_bsd_init_disassembly(disassembly))
        if args.require_r90_root_cursor:
            failures.extend(verify_r90_bsd_root_disassembly(disassembly))
        if require_r91:
            failures.extend(verify_r91_bsd_cursor_disassembly(disassembly))
        if require_r92:
            failures.extend(verify_r92_bsd_disassembly(disassembly))
        if require_r93:
            failures.extend(verify_r93_iokit_time_disassembly(disassembly))
        if args.require_r82_arm_cursor:
            failures.extend(verify_r82_phase_setter(
                disassembly, symbols.get("_y35a_bootstrap_phase"),
            ))
        if (args.require_r83_entry_ladder or args.require_r84_entry_ladder
                or args.require_r85_machine_startup or args.require_r86_startup_cursor
                or args.require_r87_startup_cursor or args.require_r88_bsd_iokit_cursor
                or args.require_r89_bsd_init_cursor or args.require_r90_root_cursor):
            failures.extend(verify_r82_phase_setter(
                disassembly, symbols.get("_y35a_bootstrap_phase"),
            ))
        if args.require_r83_entry_ladder:
            failures.extend(verify_r83_arm_init_control_flow(
                arm_body, args.kernel, symbols.get("_arm_init"),
            ))
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        failures.append(str(exc))
    failures.extend(verify_manifest(
        args.kernel, args.manifest, require_r68e7=True,
        require_r83=args.require_r83_entry_ladder,
        require_r84=(args.require_r84_entry_ladder
                     or args.require_r85_machine_startup
                     or args.require_r86_startup_cursor
                     or args.require_r87_startup_cursor
                     or args.require_r88_bsd_iokit_cursor
                     or args.require_r89_bsd_init_cursor
                     or args.require_r90_root_cursor),
    ))
    failures.extend(verify_probe_image_binding(
        args.probe, args.manifest, required=args.raw is not None,
    ))
    if (args.require_r83_entry_ladder or args.require_r84_entry_ladder
            or args.require_r85_machine_startup or args.require_r86_startup_cursor
            or args.require_r87_startup_cursor or args.require_r88_bsd_iokit_cursor
            or args.require_r89_bsd_init_cursor or args.require_r90_root_cursor):
        failures.extend(verify_r83_capture(args.raw, args.manifest, args.baseline))
        if args.raw is not None and args.manifest is not None:
            failures.extend(verify_capture_kernel_binding(args.raw, args.manifest))
    else:
        failures.extend(verify_raw(
            args.raw, args.manifest, args.baseline,
            require_r68e7_low_carrier=True,
            require_capture_binding=True,
        ))
    if args.baseline is not None and args.manifest is not None:
        failures.extend(verify_capture_kernel_binding(args.baseline, args.manifest))
    freshness = None
    if args.raw is not None and args.manifest is not None and args.baseline is None:
        manifest_data = json.loads(args.manifest.read_text())
        if any(record.get("name") == R68E7_STORE_WINDOW_RECORD
               for record in manifest_data.get("records", [])):
            failures.append("R68E7 raw verification requires a matching baseline for freshness")
    if args.baseline is not None and not (
        args.require_r83_entry_ladder or args.require_r84_entry_ladder
        or args.require_r85_machine_startup or args.require_r86_startup_cursor
        or args.require_r87_startup_cursor or args.require_r88_bsd_iokit_cursor
        or args.require_r89_bsd_init_cursor or args.require_r90_root_cursor
    ):
        if args.raw is None or args.manifest is None:
            failures.append("--baseline requires both --raw and --manifest")
        else:
            freshness = verify_fresh_generation_markers(args.raw, args.baseline, args.manifest)
            failures.extend(freshness["failures"])
    store_window = (decode_r68e7_store_window(args.raw, args.manifest, args.baseline)
                    if args.raw is not None and args.manifest is not None else None)
    low_carrier = (decode_r68e7_low_carrier(args.raw, args.manifest, args.baseline)
                   if args.raw is not None and args.manifest is not None else None)
    alias_witnesses = (decode_r68e7_alias_witnesses(args.raw, args.manifest, args.baseline)
                       if args.raw is not None and args.manifest is not None else None)

    report = {"kernel": str(args.kernel), "ok": not failures, "failures": failures}
    if freshness is not None:
        report["freshness"] = freshness["markers"]
    if args.raw is not None and args.manifest is not None:
        report["boundary_markers"] = decode_boundary_markers(args.raw, args.manifest)
        report["y35a_bootstrap_phase"] = decode_y35a_bootstrap_phase(
            args.kernel, args.raw, args.manifest, args.baseline
        )
        report["fault_publish_pre_store"] = decode_fault_publish_pre_store(args.raw, args.manifest, args.baseline)
        report["fault_publish_window"] = decode_fault_publish_operands(args.raw, args.manifest)
        report["entry_path_echo"] = decode_entry_path_echo(args.raw, args.manifest)
        report["sctlr_el1"] = decode_sctlr_el1(args.raw, args.manifest)
        report["r68e7_store_window"] = store_window
        report["r68e7_low_carrier"] = low_carrier
        report["r68e7_alias_witnesses"] = alias_witnesses
        if args.require_r83_entry_ladder:
            report["r83_entry_ladder"] = decode_r83_entry_ladder(
                args.raw, args.manifest, args.baseline
            )
        if (args.require_r84_entry_ladder or args.require_r85_machine_startup
                or args.require_r86_startup_cursor or args.require_r87_startup_cursor
                or args.require_r88_bsd_iokit_cursor or args.require_r89_bsd_init_cursor
                or args.require_r90_root_cursor):
            report["r84_entry_ladder"] = decode_r84_entry_ladder(
                args.raw, args.manifest, args.baseline
            )
        if (args.require_r85_machine_startup or args.require_r86_startup_cursor
                or args.require_r87_startup_cursor or args.require_r88_bsd_iokit_cursor
                or args.require_r89_bsd_init_cursor or args.require_r90_root_cursor):
            report["r85_machine_startup"] = decode_r85_machine_startup(
                args.raw, args.manifest, args.baseline
            )
        if (args.require_r86_startup_cursor or args.require_r87_startup_cursor
                or args.require_r88_bsd_iokit_cursor or args.require_r89_bsd_init_cursor
                or args.require_r90_root_cursor):
            report["r86_startup"] = decode_r86_startup(
                args.raw, args.manifest, args.baseline
            )
        if (args.require_r87_startup_cursor or args.require_r88_bsd_iokit_cursor
                or args.require_r89_bsd_init_cursor or args.require_r90_root_cursor):
            report["r87_startup"] = decode_r87_startup(
                args.raw, args.manifest, args.baseline
            )
        if args.require_r88_bsd_iokit_cursor or args.require_r89_bsd_init_cursor:
            report["r88_startup"] = decode_r88_bsd_iokit(
                args.raw, args.manifest, args.baseline
            )
        if args.require_r89_bsd_init_cursor or args.require_r90_root_cursor:
            report["r89_startup"] = decode_r89_bsd_init(
                args.raw, args.manifest, args.baseline
            )
        if args.require_r90_root_cursor:
            report["r90_startup"] = decode_r90_bsd_root(
                args.raw, args.manifest, args.baseline
            )
        if require_r91:
            report["r91_startup"] = decode_r91_bsd_cursor(
                args.raw, args.manifest, args.baseline
            )
        if require_r92:
            report["r92_startup"] = decode_r92_bsd_cursor(
                args.raw, args.manifest, args.baseline
            )
        if require_r93:
            report["r93_startup"] = decode_r93_iokit_time(
                args.raw, args.manifest, args.baseline
            )
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
