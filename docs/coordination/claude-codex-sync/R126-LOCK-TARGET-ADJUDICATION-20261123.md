# R126 lock-target adjudication

Kernel `f5c78154a9e6e4ea5fd55f670a25373bb8ddaa247ff469d2a5def07a0624f806`; boot `db30afea476dadedd5ec554f5ad2d9bbbf0af2bbadd84d7c16a8d272ef6e7f7`; final raw `0b618577727a0de265f31e2a1351f39e0f7b3e53da215349326496b3d43ea4f2`.

Fresh final contains `RNDLKEN0`, but not `RNDLOCK0` or `RNDLCNT0`. The target-pointer check proves entry into `lck_mtx_lock()` for the PRNG mutex. It does not prove whether the stop is in mutex verification, preemption checking, current-thread lookup, atomic acquisition, or another instruction before the next cursor.
