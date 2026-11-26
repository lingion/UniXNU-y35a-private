# R122 PRNG read_random adjudication

Run: `/Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r122-prng-readrandom-paired-run-20261123-01/`
Device: `efff9d92` / `lk2nd-msm8916`; RAM-only; `persistent_writes=false`; returned to fastboot.

Inputs:

- kernel `c7b312feece848994716bf1ed14a3069be8b8baf2cb518038536d482734ed719`
- boot `e4dc7483984eaae3623fb2e9575274fe46a8d9a0f67e16d267fd169ecbd88819`
- regular probe `e3206b55eaa060152d967290c8b1ff7a19bcf08f6b2471d915178b589ca17f35`
- clear probe `9451252290e92c185e02a92a73834d2c675200d1549f5508bd8a0a9424029925`

Raw evidence:

- preclear `b33bd0f0953a15e5cc40fc9d18a714e93169abce52b6b4b128e71b0a95624164`
- baseline `dc4c515927ab54f7ca1ab625676896c9ce45012400bbb783d8d7343e047754c1`
- candidate `628b1f8304c221b4e036d31133816c40209fa20fff6a77ea3be71eb8ca3738c8`
- final `8373c53baa32a3b361fbdb6f8776f2ed9eea37100efdd64e27d4076eb640bb4f`

Fresh final contains `RNDENTR0` and does not contain `RNDLOCK0`, `RNDGEN00`, or `RNDRETN0`.

**CONFIRMED boundary:** `read_random()` entry was reached; the next cursor after `lck_mtx_lock(prng.lock.mutex)` was not reached. This localizes the stop to the lock call or its immediate entry path. It does not prove deadlock, fault class, or scheduler state.

Next MVE: add `RNDBEFLK0` immediately before the mutex call and retain `RNDLOCK0` after it, then rebuild and repeat the same paired experiment.
