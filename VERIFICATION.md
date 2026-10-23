# Verification

Target: Linux x86_64, GraalVM CE 25.0.2, musl, TLC source commit
606dfa48298a1b36c4ee4625c705041c35bd7393.

The same source-built JAR is used for the JVM baseline and native build.

| Case | Expected result |
| --- | --- |
| Counter, 2 workers, WF liveness and standard modules | Exit 0; 5 generated / 4 distinct states |
| Invalid invariant | Exit 12; counterexample |
| Invalid eventual property | Exit 13; cyclic counterexample |
| Simulation, 10 traces, depth 20 | Exit 0 |
| DFID, 1 worker | Exit 0 |
| Upstream Bakery, 2 processes, bounded numbers, mutual exclusion | Exit 0; 1183 generated / 668 distinct states |

Bakery uses an included safety configuration, with no upstream test-only
`_POSSIBLE` counters or postcondition. See `tests/Bakery.cfg`.

The native executable is additionally checked using `file`, `readelf`, `ldd`,
and by running Counter in a `FROM scratch` container as UID 1000, with a
writable `/tmp` and model directory. No JRE, JAR, libc shared object, or dynamic
loader is copied into the runtime image.

All six cases passed for both JVM and native execution, with matching exit codes and state counts.
JFR recording also produced a nonempty recording file.

Logs are included in the build kit. These checks cover the listed behaviors;
they do not establish compatibility for every TLC feature or arbitrary Java
extensions. See README.ja.md for scope and limitations.
