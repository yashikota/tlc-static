# syntax=docker/dockerfile:1
# Builds a fully static Linux TLC. The host needs only Docker:
#   docker build --output out .                 # release archive + logs
#   docker build --target runtime -t tlc-static .  # FROM scratch image
# The toolchain is chosen from the build platform's CPU (amd64 or arm64).

ARG TLA_REV=090e85c31a6d7fb3d34a33a9f1a46310cdc2aa7f

FROM ghcr.io/graalvm/native-image-community@sha256:bd08fee5f6effb210e829f434e5b5341d9b5b321ddc47363a241853723c810eb AS toolchain-amd64
ENV TLC_TOOLCHAIN=ghcr.io/graalvm/native-image-community@sha256:bd08fee5f6effb210e829f434e5b5341d9b5b321ddc47363a241853723c810eb
RUN microdnf install -y python3 binutils && microdnf clean all

FROM bellsoft/liberica-native-image-kit-container@sha256:b531f62a40ca4217df6f39b2f7c171f4503406f3ea1273ef450e6f96b8a6afa2 AS toolchain-arm64
ENV TLC_TOOLCHAIN=bellsoft/liberica-native-image-kit-container@sha256:b531f62a40ca4217df6f39b2f7c171f4503406f3ea1273ef450e6f96b8a6afa2
# python3 pulls in a newer zlib; keep its static library in step for linking.
RUN apk add --no-cache python3 binutils zlib-static

# Fetch pinned sources with a small, separate image.
FROM alpine:3.22@sha256:2e0b81d60597f449baa56dc25d355367869d2dca4cd57e866f1e2b52af3eb55f AS source
ARG TLA_REV
RUN apk add --no-cache git curl
WORKDIR /src
RUN git init upstream \
 && git -C upstream remote add origin https://github.com/tlaplus/tlaplus.git \
 && git -C upstream fetch --depth 1 origin "$TLA_REV" \
 && git -C upstream checkout --detach FETCH_HEAD \
 && rm -rf upstream/.git \
 && mkdir tools \
 && for jar in ant ant-launcher; do \
      curl -fsSL "https://repo.maven.apache.org/maven2/org/apache/ant/$jar/1.10.15/$jar-1.10.15.jar" -o "tools/$jar.jar"; \
    done \
 && printf '%s\n' \
      '763acda4a69588c9ea8817a952851ff0c2fc4bffa1d081c2565dc407f29d5794  tools/ant.jar' \
      '5c8551990307a032336d98ddaed549a39a689f07d4d4c6b950601bf22b3d6a1b  tools/ant-launcher.jar' \
    | sha256sum -c - \
 && curl -fsSL https://raw.githubusercontent.com/ifduyue/musl/v1.2.5/COPYRIGHT -o tools/musl-COPYRIGHT

FROM toolchain-${TARGETARCH} AS build
ARG TARGETARCH
ARG SOURCE_COMMIT=local
WORKDIR /work
COPY --from=source /src/ ./
COPY configure.py verify.py README.md VERIFICATION.md LICENSE TLAplus-LICENSE.txt ./
COPY ci/ ci/
COPY tests/ tests/
RUN GITHUB_SHA="$SOURCE_COMMIT" python3 ci/build.py --target "linux-$TARGETARCH" \
 && mv "dist/tlc-linux-$TARGETARCH" /stage

# Minimal image: just the static binary and its licenses.
FROM scratch AS runtime
COPY --from=build /stage/tlc /tlc
COPY --from=build /stage/LICENSE /stage/TLAplus-LICENSE.txt /stage/THIRD-PARTY-NOTICES.txt /licenses/
WORKDIR /models
USER 1000:1000
ENTRYPOINT ["/tlc"]

# Default target: export the release archive and build logs.
FROM scratch AS export
COPY --from=build /work/release/ /release/
COPY --from=build /work/ci-logs/ /ci-logs/
