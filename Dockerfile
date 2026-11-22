# check=skip=InvalidDefaultArgInFrom
# Image references are required digest-pinned arguments from the lock file.
ARG N8N_IMAGE
ARG FFMPEG_IMAGE

FROM ${FFMPEG_IMAGE} AS ffmpeg

FROM ${N8N_IMAGE} AS yt-dlp
USER root
ARG TARGETARCH
ARG YT_DLP_TAG
ARG YT_DLP_SHA256_AMD64
ARG YT_DLP_SHA256_ARM64
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) asset=yt-dlp_musllinux; checksum="$YT_DLP_SHA256_AMD64" ;; \
      arm64) asset=yt-dlp_musllinux_aarch64; checksum="$YT_DLP_SHA256_ARM64" ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    wget -O /yt-dlp "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/$YT_DLP_TAG/$asset"; \
    printf '%s  /yt-dlp\n' "$checksum" | sha256sum -c -; \
    chmod 0755 /yt-dlp
RUN mkdir /n8n-files && chown 1000:1000 /n8n-files

# The custom image. Its target name lets the AI variant below build on it.
FROM ${N8N_IMAGE} AS custom
COPY --from=yt-dlp /yt-dlp /usr/local/bin/yt-dlp
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
COPY yt-dlp.conf /etc/yt-dlp.conf
COPY --from=yt-dlp --chown=1000:1000 /n8n-files/ /home/node/.n8n-files/

ARG N8N_VERSION
ARG N8N_DIGEST
ARG RUNNERS_DIGEST
ARG YT_DLP_TAG
ARG YT_DLP_SHA256_AMD64
ARG YT_DLP_SHA256_ARM64
ARG FFMPEG_VERSION
ARG FFMPEG_DIGEST
ARG BUILD_TAG
ARG REVISION
ARG CREATED
LABEL org.opencontainers.image.source="https://github.com/aliyusufergin/n8n-custom-ytdlp" \
      org.opencontainers.image.revision="$REVISION" \
      org.opencontainers.image.created="$CREATED" \
      org.opencontainers.image.version="$BUILD_TAG" \
      io.github.aliyusufergin.n8n-ytdlp.build-tag="$BUILD_TAG" \
      io.github.aliyusufergin.n8n-ytdlp.n8n.version="$N8N_VERSION" \
      io.github.aliyusufergin.n8n-ytdlp.n8n.digest="$N8N_DIGEST" \
      io.github.aliyusufergin.n8n-ytdlp.runners.digest="$RUNNERS_DIGEST" \
      io.github.aliyusufergin.n8n-ytdlp.yt-dlp.tag="$YT_DLP_TAG" \
      io.github.aliyusufergin.n8n-ytdlp.yt-dlp.sha256.amd64="$YT_DLP_SHA256_AMD64" \
      io.github.aliyusufergin.n8n-ytdlp.yt-dlp.sha256.arm64="$YT_DLP_SHA256_ARM64" \
      io.github.aliyusufergin.n8n-ytdlp.ffmpeg.version="$FFMPEG_VERSION" \
      io.github.aliyusufergin.n8n-ytdlp.ffmpeg.digest="$FFMPEG_DIGEST"

# The AI variant's tools: static musl builds checked against the lock's sha256.
FROM ${N8N_IMAGE} AS ai-tools
USER root
ARG TARGETARCH
ARG CODEX_VERSION
ARG CODEX_SHA256_AMD64
ARG CODEX_SHA256_ARM64
ARG AGY_VERSION
ARG AGY_SHA256_AMD64
ARG AGY_SHA256_ARM64
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) codex=x86_64-unknown-linux-musl; codex_sum="$CODEX_SHA256_AMD64"; \
             agy=x64_musl; agy_sum="$AGY_SHA256_AMD64" ;; \
      arm64) codex=aarch64-unknown-linux-musl; codex_sum="$CODEX_SHA256_ARM64"; \
             agy=arm64_musl; agy_sum="$AGY_SHA256_ARM64" ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    mkdir /tools /state /state/.codex /state/.gemini; \
    wget -O /codex.tar.gz "https://github.com/openai/codex/releases/download/rust-v$CODEX_VERSION/codex-$codex.tar.gz"; \
    printf '%s  /codex.tar.gz\n' "$codex_sum" | sha256sum -c -; \
    tar -xzf /codex.tar.gz -C /tools; \
    mv "/tools/codex-$codex" /tools/codex; \
    wget -O /agy.tar.gz "https://github.com/google-antigravity/antigravity-cli/releases/download/$AGY_VERSION/agy_cli_linux_$agy.tar.gz"; \
    printf '%s  /agy.tar.gz\n' "$agy_sum" | sha256sum -c -; \
    tar -xzf /agy.tar.gz -C /tools; \
    mv /tools/antigravity /tools/agy; \
    test "$(ls /tools)" = "$(printf 'agy\ncodex')"; \
    chown 0:0 /tools/codex /tools/agy; \
    chmod 0755 /tools/codex /tools/agy; \
    chown 1000:1000 /state/.codex /state/.gemini

# The AI variant: the custom image plus codex and agy. Sign-in state lives in the two
# node-owned folders, which deployments mount as volumes.
FROM custom AS ai-variant
COPY --from=ai-tools /tools/ /usr/local/bin/
COPY --from=ai-tools --chown=1000:1000 /state/ /home/node/
# The lock pins agy; its background self-update must not replace or fight the pinned binary.
ENV AGY_CLI_DISABLE_AUTO_UPDATE=true
ARG CODEX_VERSION
ARG CODEX_SHA256_AMD64
ARG CODEX_SHA256_ARM64
ARG AGY_VERSION
ARG AGY_SHA256_AMD64
ARG AGY_SHA256_ARM64
LABEL io.github.aliyusufergin.n8n-ytdlp.codex.version="$CODEX_VERSION" \
      io.github.aliyusufergin.n8n-ytdlp.codex.sha256.amd64="$CODEX_SHA256_AMD64" \
      io.github.aliyusufergin.n8n-ytdlp.codex.sha256.arm64="$CODEX_SHA256_ARM64" \
      io.github.aliyusufergin.n8n-ytdlp.agy.version="$AGY_VERSION" \
      io.github.aliyusufergin.n8n-ytdlp.agy.sha256.amd64="$AGY_SHA256_AMD64" \
      io.github.aliyusufergin.n8n-ytdlp.agy.sha256.arm64="$AGY_SHA256_ARM64"
