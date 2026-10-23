#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p dist/licenses/tlaplus
cp upstream/LICENSE dist/licenses/tlaplus/LICENSE
cp upstream/tlatools/org.lamport.tlatools/lib/jline/jline-LICENSE.txt dist/licenses/
cp upstream/tlatools/org.lamport.tlatools/lib/gson/gson-LICENSE dist/licenses/
cp upstream/tlatools/org.lamport.tlatools/src/org/apache/commons/math3/CommonsMath-{LICENSE,NOTICE}.txt dist/licenses/
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" --entrypoint /bin/sh \
 ghcr.io/graalvm/native-image-community:25-muslib@sha256:bd08fee5f6effb210e829f434e5b5341d9b5b321ddc47363a241853723c810eb \
 -c 'set -eu; mkdir -p /work/dist/licenses/graalvm; cp -rL "$JAVA_HOME/legal/." /work/dist/licenses/graalvm/; cp -r /usr/share/licenses/gcc /work/dist/licenses/gcc'
curl -fL https://raw.githubusercontent.com/ifduyue/musl/v1.2.5/COPYRIGHT -o dist/licenses/musl-COPYRIGHT
cp README.ja.md dist/
mkdir -p dist/examples
cp tests/*.tla tests/*.cfg dist/examples/
cp VERIFICATION.md dist/
(cd dist && sha256sum tlc > SHA256SUMS)
tar -czf dist/tlc-static-linux-x86_64.tar.gz -C dist tlc SHA256SUMS README.ja.md VERIFICATION.md licenses examples
tar --exclude=tests/states -czf dist/tlc-static-build-kit.tar.gz build.sh configure.py verify.py package.sh Dockerfile.scratch .dockerignore README.ja.md VERIFICATION.md tests native-config native-build.log ant-build.log verification verification-jvm scratch-test.log static-linkage.log
(cd dist && sha256sum tlc-static-linux-x86_64.tar.gz tlc-static-build-kit.tar.gz > ARCHIVE-SHA256SUMS)
