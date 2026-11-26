# R123 read_random adjudication

Kernel `20f20a3f2e3769a5b9dc4e6cde568a9459d133e0b40ae5ca9bd2db2d72f471be`; boot `3575905528bbab17c9b32557c117004800b50ed1ad86d82441a757b550f578f7`; final raw `a75e99749a265c299d455ba45c06ef349f0ddf06dcc016e9e37a43c6943c9613`.

Fresh final contains `RNDENTR0`, but not `RNDLOCK0`, `RNDGEN00`, or `RNDRETN0`. Preclear and baseline external windows were zero; device returned fastboot with `persistent_writes=false`.

CONFIRMED boundary: `read_random()` entry reached, and the post-lock cursor was absent. This does not prove deadlock or a fault class.
