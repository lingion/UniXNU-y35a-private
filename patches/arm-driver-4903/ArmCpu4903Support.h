// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef ARMCPU_4903_SUPPORT_H
#define ARMCPU_4903_SUPPORT_H

// This is a policy check, not a replacement for any XNU topology helper.
enum ArmCpu4903BootResult {
    ArmCpu4903BootOK = 0,
    ArmCpu4903RejectCPU = 1,
    ArmCpu4903RejectSMP = 2,
    ArmCpu4903RequireSingleCPU = 3,
    ArmCpu4903RejectAffinity = 4
};

static inline ArmCpu4903BootResult armcpu4903BootPolicy(
    unsigned physical, int logical, int boot, unsigned count, int maximum,
    unsigned long long mpidr, unsigned smp, unsigned remote, unsigned requestedCPUs)
{
    if (physical != 0 || logical != 0 || boot != 0) { return ArmCpu4903RejectCPU; }
    if (smp != 0 || remote != 0) { return ArmCpu4903RejectSMP; }
    if (requestedCPUs != 1 || count != 1 || maximum != 0) { return ArmCpu4903RequireSingleCPU; }
    if ((mpidr & 0xff00ffffffULL) != 0) { return ArmCpu4903RejectAffinity; }
    return ArmCpu4903BootOK;
}

// Operate on owned raw pointers returned by the real 4903 IOKit factories.
// Templates allow host failure injection without copying any IOKit ABI types.
template <class Map> static void armcpu4903ReleaseMaps(Map *&first, Map *&second)
{
    if (second != nullptr) { second->release(); second = nullptr; }
    if (first != nullptr) { first->release(); first = nullptr; }
}

template <class Descriptor, class Map, class Direction, class Options>
static bool armcpu4903MapPair(unsigned long long firstAddress, unsigned long long firstSize,
                             unsigned long long secondAddress, unsigned long long secondSize,
                             Direction direction, Options options, Map *&first, Map *&second)
{
    if (first != nullptr || second != nullptr) { return false; }
    Descriptor *firstMemory = Descriptor::withPhysicalAddress(firstAddress, firstSize, direction);
    if (firstMemory == nullptr) { return false; }
    Descriptor *secondMemory = Descriptor::withPhysicalAddress(secondAddress, secondSize, direction);
    if (secondMemory == nullptr) { firstMemory->release(); return false; }
    Map *firstMap = firstMemory->map(options);
    Map *secondMap = firstMap != nullptr ? secondMemory->map(options) : nullptr;
    // A successful IOMemoryMap retains its descriptor in setMemoryDescriptor().
    firstMemory->release();
    secondMemory->release();
    if (firstMap == nullptr || secondMap == nullptr) {
        armcpu4903ReleaseMaps(firstMap, secondMap);
        return false;
    }
    first = firstMap;
    second = secondMap;
    return true;
}
#endif
