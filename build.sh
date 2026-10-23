#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
IMAGE=ghcr.io/graalvm/native-image-community:25-muslib@sha256:bd08fee5f6effb210e829f434e5b5341d9b5b321ddc47363a241853723c810eb
REV=606dfa48298a1b36c4ee4625c705041c35bd7393
mkdir -p tools dist native-config
if [[ ! -d upstream/.git ]]; then
  git init upstream
  git -C upstream remote add origin https://github.com/tlaplus/tlaplus.git
  git -C upstream fetch --depth 1 origin "$REV"
  git -C upstream checkout --detach FETCH_HEAD
fi
[[ $(git -C upstream rev-parse HEAD) == "$REV" ]]
curl -fL https://repo.maven.apache.org/maven2/org/apache/ant/ant/1.10.15/ant-1.10.15.jar -o tools/ant.jar
curl -fL https://repo.maven.apache.org/maven2/org/apache/ant/ant-launcher/1.10.15/ant-launcher-1.10.15.jar -o tools/ant-launcher.jar
sha256sum -c <<'SUMS'
763acda4a69588c9ea8817a952851ff0c2fc4bffa1d081c2565dc407f29d5794  tools/ant.jar
5c8551990307a032336d98ddaed549a39a689f07d4d4c6b950601bf22b3d6a1b  tools/ant-launcher.jar
SUMS
docker pull "$IMAGE"
DOCKER_ARGS=(--rm --user "$(id -u):$(id -g)" -v "$PWD:/work")
docker run "${DOCKER_ARGS[@]}" -w /work/upstream/tlatools/org.lamport.tlatools --entrypoint java "$IMAGE" \
  -cp '/work/tools/*' org.apache.tools.ant.Main -f customBuild.xml \
  -Dgit.revision="$REV" -Dgit.shortRevision="${REV:0:7}" -Dgit.branch=master \
  compile compile-test dist 2>&1 | tee ant-build.log
cp upstream/tlatools/org.lamport.tlatools/dist/tla2tools.jar dist/
python3 configure.py
docker run "${DOCKER_ARGS[@]}" -w /work --entrypoint native-image "$IMAGE" \
  --no-fallback --static --libc=musl --enable-monitoring=jfr -march=compatibility \
  -J-Xmx6g --parallelism=2 -H:ConfigurationFileDirectories=/work/native-config \
  -cp /work/dist/tla2tools.jar -o /work/dist/tlc tlc2.TLC 2>&1 | tee native-build.log
./verify.py docker run "${DOCKER_ARGS[@]}" -w /work/tests --entrypoint java "$IMAGE" -Xmx512m -cp /work/dist/tla2tools.jar tlc2.TLC
mkdir -p verification-jvm
cp -r verification/. verification-jvm/
./verify.py
file dist/tlc > static-linkage.log
readelf -l dist/tlc >> static-linkage.log
readelf -d dist/tlc >> static-linkage.log
if readelf -l dist/tlc | grep -q INTERP; then exit 1; fi
if readelf -d dist/tlc | grep -q NEEDED; then exit 1; fi
BUILDX_CONFIG="${BUILDX_CONFIG:-$PWD/.buildx}" docker build -f Dockerfile.scratch -t tlc-static:local . > scratch-build.log 2>&1
docker run --rm --tmpfs /tmp:rw,mode=1777 -v "$PWD/tests:/models" tlc-static:local \
  -Xmx512m -workers 2 -fpmem 0.1 -noGenerateSpecTE Counter.tla > scratch-test.log 2>&1
./package.sh
