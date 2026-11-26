# R124 read_random lock-entry adjudication

Kernel `1a109d55b236e9351675e953f005297ecd2e8c942d81c6c3895b356bf84e4cdc`; boot `14832172476c8600fc509abe1292f3a282085205416a06ab8a5360976b4f66b5`; final raw `0b618577727a0de265f31e2a1351f39e0f7b3e53da215349326496b3d43ea4f2`.

Fresh final contains `RNDENTR0` and `RNDBEFL0`, but not `RNDLOCK0`. This confirms execution reached the immediate pre-call point and entered `read_random`; the stop is inside `lck_mtx_lock()` or its call entry.
