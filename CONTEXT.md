# n8n-custom-ytdlp

A publicly published Docker image: the official n8n 2.x image plus nightly yt-dlp and ffmpeg, rebuilt automatically when its upstreams change, so any Compose deployment can run yt-dlp from n8n workflows without extra setup.

## Language

### The image

**Custom image**:
The image this repository publishes as `aliyusufergin/n8n-ytdlp`: the upstream n8n image with yt-dlp nightly and ffmpeg/ffprobe added and n8n's own behaviour left unchanged.
_Avoid_: fork, our n8n, build

**Upstream n8n image**:
The official `n8nio/n8n` image of the n8n version a custom image is built on.
_Avoid_: base image (n8n's own base is a different image)

**Stable track**:
The n8n release line that n8n marks as its GitHub "latest release"; the custom image follows only this line, and only while its major version is 2.
_Avoid_: latest, newest version, highest version

**yt-dlp nightly**:
A release from yt-dlp's nightly channel (`yt-dlp/yt-dlp-nightly-builds`), identified by its timestamp tag.
_Avoid_: yt-dlp latest, yt-dlp stable

**n8n files folder**:
`/home/node/.n8n-files`, the only folder n8n's file nodes may read or write by default, and the place workflows put downloaded media.
_Avoid_: downloads folder, media dir

**Companion runners image**:
An unmodified copy of n8n's `n8nio/runners` image, published as `aliyusufergin/n8n-ytdlp-runners` under the same tags as the custom image so deployments using external task runners keep versions paired.
_Avoid_: runners fork, custom runners

**AI variant**:
The image this repository publishes as `aliyusufergin/n8n-ytdlp-ai`: the custom image plus OpenAI's Codex CLI (`codex`) and Google's Antigravity CLI (`agy`), with node-owned sign-in folders that deployments mount as volumes. It has its own build tags and is published without moving the custom image.
_Avoid_: AI image, codex image, full image

**Sign-in folder**:
`/home/node/.codex` or `/home/node/.gemini`, where codex or agy keeps a subscription sign-in; each is a deployment's volume so the sign-in survives image updates.
_Avoid_: config dir, auth volume

### Publishing

**Build inputs**:
The exact upstream versions and digests (upstream n8n image, yt-dlp nightly, ffmpeg) that one custom image is built from.
_Avoid_: dependencies, versions

**Floating tag**:
A tag such as `2`, `2.38` or `2.38.7` that moves to the newest custom image matching it.
_Avoid_: latest, channel

**Build tag**:
A tag that names exactly one custom image and is never moved or overwritten.
_Avoid_: immutable version, release tag

### Consumers

**Deployment**:
Any Docker Compose setup that runs the custom image; the custom image assumes nothing about a particular deployment.
_Avoid_: server, production, install

**Deployment setting**:
Configuration that only a deployment decides, such as enabling the Execute Command node; it lives in the deployment's Compose file, never in the custom image.
_Avoid_: image config, default
