// Host-only test doubles. These classes never enter an arm64 driver object.
#include <cassert>
#include <initializer_list>
#include "ArmCpu4903Support.h"

static int liveDescriptors, liveMaps, createCalls, mapCalls, failCreate, failMap;
struct Descriptor;
struct Map { Descriptor *owner; void release(); };
struct Descriptor {
    int refs = 1;
    static Descriptor *withPhysicalAddress(unsigned long long, unsigned long long, unsigned) {
        if (++createCalls == failCreate) { return nullptr; }
        ++liveDescriptors;
        return new Descriptor;
    }
    Map *map(unsigned) {
        if (++mapCalls == failMap) { return nullptr; }
        ++refs; ++liveMaps;
        return new Map{this};
    }
    void release() { if (--refs == 0) { --liveDescriptors; delete this; } }
};
void Map::release() { owner->release(); --liveMaps; delete this; }

int main() {
    for (unsigned smp : {0U, 1U}) {
        for (unsigned remote : {0U, 1U}) {
            const auto result = armcpu4903BootPolicy(0, 0, 0, 1, 0, 0, smp, remote, 1);
            assert((result == ArmCpu4903BootOK) == (!smp && !remote));
        }
    }
    assert(armcpu4903BootPolicy(0, 0, 0, 1, 0, 0x80000000ULL, 0, 0, 1) == ArmCpu4903BootOK);
    for (unsigned cpu = 1; cpu < 8; ++cpu) {
        assert(armcpu4903BootPolicy(cpu, cpu, 0, 1, 0, 0, 0, 0, 1) == ArmCpu4903RejectCPU);
    }
    for (auto affinity : {1ULL, 0x100ULL, 0x10000ULL, 0x100000000ULL}) {
        assert(armcpu4903BootPolicy(0, 0, 0, 1, 0, affinity, 0, 0, 1) == ArmCpu4903RejectAffinity);
    }
    assert(armcpu4903BootPolicy(0, 0, 0, 4, 3, 0, 0, 0, 1) == ArmCpu4903RequireSingleCPU);
    assert(armcpu4903BootPolicy(0, 0, 0, 1, 1, 0, 0, 0, 1) == ArmCpu4903RequireSingleCPU);
    assert(armcpu4903BootPolicy(0, 0, 1, 1, 0, 0, 0, 0, 1) == ArmCpu4903RejectCPU);
    assert(armcpu4903BootPolicy(0, -1, 0, 1, 0, 0, 0, 0, 1) == ArmCpu4903RejectCPU);
    assert(armcpu4903BootPolicy(0, 0, 0, 1, 0, 0, 0, 0, 0) == ArmCpu4903RequireSingleCPU);
    assert(armcpu4903BootPolicy(0, 0, 0, 1, 0, 0, 0, 0, 4) == ArmCpu4903RequireSingleCPU);
    for (int allocationFailure = 0; allocationFailure <= 2; ++allocationFailure) {
        for (int mappingFailure = 0; mappingFailure <= 2; ++mappingFailure) {
            createCalls = mapCalls = 0;
            failCreate = allocationFailure; failMap = mappingFailure;
            Map *first = nullptr, *second = nullptr;
            bool ok = armcpu4903MapPair<Descriptor>(1, 4096, 2, 8192, 0U, 0U, first, second);
            assert(ok == (allocationFailure == 0 && mappingFailure == 0));
            if (ok) {
                assert(first && second && liveMaps == 2 && liveDescriptors == 2);
                // Refuse reinitialization without consuming or replacing existing owners.
                assert(!armcpu4903MapPair<Descriptor>(1, 4096, 2, 8192, 0U, 0U, first, second));
            } else { assert(!first && !second); }
            armcpu4903ReleaseMaps(first, second);
            armcpu4903ReleaseMaps(first, second);
            assert(!first && !second && liveMaps == 0 && liveDescriptors == 0);
        }
    }
}
