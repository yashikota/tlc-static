# Release verification

Each native build uses TLA+ source commit 606dfa48298a1b36c4ee4625c705041c35bd7393.
The same JAR is tested on the JVM before building the native executable.

| Case | Required result |
| --- | --- |
| Counter, 2 workers, WF liveness, standard modules | Exit 0; 5 generated / 4 distinct states |
| Invalid invariant | Exit 12; counterexample |
| Invalid eventual property | Exit 13; cyclic counterexample |
| Simulation, 10 traces, depth 20 | Exit 0 |
| DFID, 1 worker | Exit 0 |
| Bakery, 2 processes, bounded numbers, mutual exclusion | Exit 0; 1183 generated / 668 distinct states |

Bakery uses the included safety configuration, without test-only `_POSSIBLE`
counters or postconditions. Each build must pass all cases, and JVM/native
results must match, before it can be uploaded for publication.

Linux amd64 and arm64 must additionally have no ELF INTERP or NEEDED entries,
and must run Counter in a FROM scratch container with writable /tmp and a
mounted model directory. Linux builds run entirely inside Docker. No JVM, libc shared library, or dynamic loader is
copied into that image. macOS dependencies are recorded with otool; Windows
imports are recorded with dumpbin. These two operating systems use system
libraries and are not described as fully static.

Windows ARM64 is a compatibility package of the same AMD64 executable, tested
with all six cases on a Windows 11 ARM64 runner under x64 emulation. It is not
ARM64-native. The compatibility package includes those extra verification logs.

GitHub Actions publishes a release only after all native builds and the ARM64
Windows compatibility job succeed. Release archives include logs from their
build, source/toolchain metadata, licenses, and example models. Failed jobs
upload their available logs as Actions artifacts.

These tests verify the listed behaviors and do not prove every TLC feature or
arbitrary Java extensions work. See README.md for limitations.
