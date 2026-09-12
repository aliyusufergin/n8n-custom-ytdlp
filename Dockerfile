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

FROM ${N8N_IMAGE}
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
