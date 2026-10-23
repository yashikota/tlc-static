# tlc-static

**TLA+ TLC as a single executable. No Java needed.**

## Quick start

1. Download your file from **[Releases](https://github.com/yashikota/tlc-static/releases/latest)**.
2. Unpack it.
3. Run:

```sh
./tlc -workers 2 -config Model.cfg Model.tla
```

Windows:

```powershell
.\tlc.exe -workers 2 -config Model.cfg Model.tla
```

Try the bundled example:

```sh
./tlc -Xmx512m -workers 2 -fpmem 0.1 -noGenerateSpecTE examples/Counter.tla
```

## Which file?

| You have | Download |
| --- | --- |
| Linux x86_64 | `tlc-linux-amd64.tar.gz` |
| Linux ARM64 | `tlc-linux-arm64.tar.gz` |
| Mac (Apple Silicon) | `tlc-macos-arm64.tar.gz` |
| Windows x64 | `tlc-windows-amd64.zip` |
| Windows ARM64 | `tlc-windows-arm64-emulated.zip` |

- Intel Macs are not supported.
- Windows ARM64 runs the x64 binary through emulation.

## Good to know

- Linux binaries are **fully static**. They run anywhere, even in an empty `FROM scratch` container.
- macOS and Windows binaries use normal system libraries.
- Standard TLA+ modules are built in.
- Java overrides and CommunityModules JARs are **not** supported.
- TLC needs write access to the current folder (it writes `states/`).
- The macOS binary is not signed. You may need to allow it in System Settings.

## Run with Docker

Build a tiny image and check a model in the current folder:

```sh
docker build --target runtime -t tlc-static .
docker run --rm --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,mode=1777 \
  -v "$PWD:/models" tlc-static -workers 2 Model.tla
```

`--user` lets TLC write into your folder.

## Build it yourself

You only need **Docker**.

```sh
docker build --output out .
```

- Output: `out/release/tlc-linux-<arch>.tar.gz`
- Logs: `out/ci-logs/`
- The CPU of your machine picks the target (amd64 or arm64).
- Give Docker about 8 GB of memory.

macOS and Windows binaries cannot be built in Docker. GitHub Actions builds them on native runners.

## Release

Push a tag:

```sh
git tag v0.1.2
git push origin v0.1.2
```

GitHub Actions then:

1. Builds every target.
2. Tests each one against the JVM build.
3. Publishes the release only if everything passes.

## How it is tested

- Six TLC runs must match the JVM: safety, liveness, both kinds of violation, simulation, DFID, and the Bakery algorithm.
- Linux: no dynamic loader, no shared libraries, and a run inside `FROM scratch`.
- Details: [VERIFICATION.md](VERIFICATION.md).

## Pinned inputs

- TLA+ source: `606dfa48298a1b36c4ee4625c705041c35bd7393` (no patches)
- Linux amd64: GraalVM CE 25.0.2 + musl (image digest pinned)
- Linux arm64: Liberica NIK 25 + musl (image digest pinned)
- macOS / Windows: GraalVM CE 25.0.2
- Ant 1.10.15 (SHA-256 checked)
- GitHub Actions pinned by commit SHA

## Not included or not tested

- Only `tlc2.TLC`. No Toolbox, SANY CLI, or PlusCal CLI.
- Not tested: distributed TLC, REPL, email, checkpoint recovery, very large models.
- Builds are not bit-for-bit reproducible (upstream embeds the build time).

## License

- Build scripts: [MIT](LICENSE)
- TLA+: [TLAplus-LICENSE.txt](TLAplus-LICENSE.txt)
- Bundled dependencies: see `licenses/` in each archive.
