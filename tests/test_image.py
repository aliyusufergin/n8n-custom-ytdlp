"""Candidate-image acceptance tests; only Docker's public interface is used."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]


class ImageTests(unittest.TestCase):
    image: str
    lock: dict
    youtube_network = "bridge"

    def image_config(self, image: str) -> dict:
        return json.loads(subprocess.check_output(
            ["docker", "image", "inspect", image], text=True, timeout=30,
        ))[0]["Config"]

    def command(self, *args: str) -> str:
        result = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--entrypoint", args[0],
             self.image, *args[1:]],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def test_yt_dlp_version(self):
        self.assertEqual(self.command("yt-dlp", "--version"), self.lock["yt_dlp"]["tag"])

    def test_n8n_version(self):
        self.assertEqual(self.command("n8n", "--version"), self.lock["n8n"]["version"])

    def test_upstream_contract(self):
        upstream = self.image_config(f'n8nio/n8n@{self.lock["n8n"]["image_digest"]}')
        candidate = self.image_config(self.image)
        for field in ("User", "WorkingDir", "Entrypoint", "Cmd", "ExposedPorts",
                      "Volumes", "Healthcheck"):
            with self.subTest(field=field):
                self.assertEqual(candidate.get(field), upstream.get(field))
        self.assertEqual(sorted(candidate.get("Env") or []), sorted(upstream.get("Env") or []))

    def test_tool_permissions_and_no_extra_runtimes(self):
        self.assertEqual(self.command("id", "-un"), "node")
        self.command("sh", "-ec", """
            for tool in yt-dlp ffmpeg ffprobe; do
                path=$(command -v "$tool")
                test -x "$path"
                test "$(stat -c '%u:%g' "$path")" = 0:0
                test ! -w "$path"
            done
            for tool in ffplay python python3 pip pip3 deno apk apt-get; do
                if command -v "$tool"; then exit 1; fi
            done
        """)

    def test_ffmpeg_versions(self):
        for tool in ("ffmpeg", "ffprobe"):
            with self.subTest(tool=tool):
                version_line = self.command(tool, "-version").splitlines()[0]
                self.assertEqual(version_line.split()[2], self.lock["ffmpeg"]["version"])

    def test_yt_dlp_wiring(self):
        result = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--user", "node",
             "--entrypoint", "yt-dlp", self.image, "--verbose"],
            capture_output=True, text=True, timeout=120,
        )
        diagnostics = result.stdout + result.stderr
        # No URL is intentional: yt-dlp reports tool detection before this usage error.
        self.assertEqual(result.returncode, 2, diagnostics)
        self.assertIn("You must provide at least one URL", diagnostics)
        node_version = self.command("node", "--version").removeprefix("v")
        self.assertRegex(diagnostics,
                         rf"(?m)^\[debug\] JS runtimes: .*\bnode-{re.escape(node_version)}(?:,|$)")
        for tool in ("ffmpeg", "ffprobe"):
            with self.subTest(tool=tool):
                self.assertRegex(
                    diagnostics,
                    rf"(?m)^\[debug\] exe versions: .*\b{tool} "
                    rf"{re.escape(self.lock['ffmpeg']['version'])}(?:[ ,(]|$)",
                )

    def test_offline_ffmpeg(self):
        result = json.loads(self.command("sh", "-ec", """
            cd /home/node/.n8n-files
            ffmpeg -hide_banner -loglevel error -nostdin -f lavfi \
                -i testsrc2=size=96x64:rate=10 -t 2 -an -c:v mpeg4 video.mp4
            ffmpeg -hide_banner -loglevel error -nostdin -f lavfi \
                -i sine=frequency=440:sample_rate=16000 -t 2 -vn -c:a pcm_s16le audio.wav
            ffmpeg -hide_banner -loglevel error -nostdin -i video.mp4 -i audio.wav \
                -map 0:v:0 -map 1:a:0 -c copy merged.mkv
            ffmpeg -hide_banner -loglevel error -nostdin -i merged.mkv \
                -map 0:v:0 -map 0:a:0 -c:v ffv1 -c:a flac converted.mkv
            ffprobe -v error -show_streams -show_format -of json converted.mkv
        """))
        streams = {stream["codec_type"]: stream for stream in result["streams"]}
        self.assertEqual(len(result["streams"]), 2)
        self.assertEqual(set(streams), {"video", "audio"})
        self.assertEqual(streams["video"]["codec_name"], "ffv1")
        self.assertEqual((streams["video"]["width"], streams["video"]["height"]), (96, 64))
        self.assertEqual(streams["audio"]["codec_name"], "flac")
        self.assertEqual(streams["audio"]["sample_rate"], "16000")
        self.assertAlmostEqual(float(result["format"]["duration"]), 2, delta=0.15)

    def test_n8n_files_folder(self):
        details = self.command("node", "-e", """
            const fs = require('node:fs');
            const path = '/home/node/.n8n-files';
            const stat = fs.statSync(path);
            console.log(JSON.stringify({directory: stat.isDirectory(), uid: stat.uid,
                gid: stat.gid, entries: fs.readdirSync(path)}));
        """)
        self.assertEqual(json.loads(details), {
            "directory": True, "uid": 1000, "gid": 1000, "entries": [],
        })

    def test_n8n_files_fresh_volume_writable(self):
        volume = "n8n-ytdlp-files-" + uuid.uuid4().hex
        subprocess.run(["docker", "volume", "create", volume],
                       check=True, capture_output=True, text=True, timeout=30)
        self.addCleanup(subprocess.run, ["docker", "volume", "rm", volume],
                        check=True, capture_output=True, text=True, timeout=30)
        name = "n8n-ytdlp-files-" + uuid.uuid4().hex
        # Clean up the container before the volume, including after a run timeout.
        self.addCleanup(subprocess.run, ["docker", "rm", "--force", "--volumes", name],
                        capture_output=True, text=True, timeout=30)
        result = subprocess.run(
            ["docker", "run", "--rm", "--name", name, "--network", "none",
             "--user", "node", "--mount",
             f"type=volume,src={volume},dst=/home/node/.n8n-files",
             "--entrypoint", "node", self.image, "-e", """
                const fs = require('node:fs');
                const path = '/home/node/.n8n-files/volume-test.txt';
                fs.writeFileSync(path, 'written by node', {flag: 'wx'});
                console.log(fs.readFileSync(path, 'utf8'));
                fs.unlinkSync(path);
             """], capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "written by node")

    def execute_media_workflow(self, *container_options: str) -> subprocess.CompletedProcess:
        name = "n8n-ytdlp-workflow-" + uuid.uuid4().hex
        self.addCleanup(subprocess.run, ["docker", "rm", "--force", "--volumes", name],
                        check=True, capture_output=True, text=True, timeout=30)
        subprocess.run(
            ["docker", "run", "--detach", "--name", name, "--network", "none",
             *container_options,
             "--mount", f"type=bind,src={ROOT / 'tests/fixtures'},dst=/fixtures,readonly",
             "--entrypoint", "sleep", self.image, "600"],
            check=True, capture_output=True, text=True, timeout=30,
        )
        imported = subprocess.run(
            ["docker", "exec", name, "n8n", "import:workflow",
             "--input=/fixtures/media-workflow.json"],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)
        return subprocess.run(
            ["docker", "exec", name, "n8n", "execute", "--id=media-acceptance",
             "--rawOutput"], capture_output=True, text=True, timeout=120,
        )

    def test_execute_command_unavailable_by_default(self):
        executed = self.execute_media_workflow()
        diagnostics = executed.stdout + executed.stderr
        self.assertNotEqual(executed.returncode, 0, diagnostics)
        self.assertIn("Unrecognized node type: n8n-nodes-base.executeCommand", diagnostics)

    def test_execute_command_workflow(self):
        compose = json.loads(subprocess.check_output(
            ["docker", "compose", "-f", str(ROOT / "examples/compose.yaml"),
             "config", "--format", "json"], text=True, timeout=30,
        ))
        excluded = compose["services"]["n8n"]["environment"]["NODES_EXCLUDE"]
        self.assertEqual(json.loads(excluded), ["n8n-nodes-base.localFileTrigger"])
        executed = self.execute_media_workflow("--env", f"NODES_EXCLUDE={excluded}")
        self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
        # n8n prints startup diagnostics before its pretty-printed raw JSON result.
        start = executed.stdout.find("{\n")
        self.assertGreaterEqual(start, 0, executed.stdout)
        result, _ = json.JSONDecoder().raw_decode(executed.stdout[start:])
        self.assertEqual(result["status"], "success", result)
        nodes = result["data"]["resultData"]["runData"]
        command = nodes["Generate media"][0]["data"]["main"][0][0]["json"]
        self.assertEqual(command["exitCode"], 0)
        self.assertEqual(command["stdout"].splitlines(),
                         ["node", self.lock["yt_dlp"]["tag"]])
        read = nodes["Read media"][0]["data"]["main"][0][0]["binary"]["data"]
        self.assertEqual(read["fileName"], "workflow.wav")
        self.assertEqual(read["fileExtension"], "wav")
        self.assertGreater(read["bytes"], 16000)
        self.assertTrue(read["data"])

    def test_youtube_download(self):
        name = "n8n-ytdlp-youtube-" + uuid.uuid4().hex
        try:
            try:
                downloaded = subprocess.run(
                    ["docker", "run", "--rm", "--name", name,
                     "--network", self.youtube_network, "--entrypoint", "sh",
                     self.image, "-ec", """
                        cd /home/node/.n8n-files
                        yt-dlp --verbose --no-playlist --no-progress \
                            --socket-timeout 10 --retries 0 --extractor-retries 0 \
                            --fragment-retries 0 -f 'worstvideo+worstaudio' \
                            --merge-output-format mkv -o 'youtube.%(ext)s' \
                            'https://www.youtube.com/watch?v=jNQXAC9IVRw' >&2
                        ffprobe -v error -show_streams -show_format -of json youtube.mkv
                     """], capture_output=True, text=True, timeout=180,
                )
                self.assertEqual(downloaded.returncode, 0,
                                 (downloaded.stdout + downloaded.stderr)[-6000:])
                media = json.loads(downloaded.stdout)
                self.assertEqual(len(media["streams"]), 2)
                self.assertEqual({stream["codec_type"] for stream in media["streams"]},
                                 {"video", "audio"})
                self.assertGreater(float(media["format"]["duration"]), 0)
                print("YouTube download: separate video and audio merged successfully.",
                      file=sys.stderr)
            finally:
                # docker run --rm cleans up normally; also remove it after a timeout.
                subprocess.run(["docker", "rm", "--force", "--volumes", name],
                               capture_output=True, text=True, timeout=30)
        except Exception as error:
            # This entire external-service probe, including timeouts/cleanup, is advisory.
            print(f"WARNING: YouTube download failed (non-blocking): {error}", file=sys.stderr)

    def test_build_labels(self):
        labels = self.image_config(self.image)["Labels"]
        prefix = "io.github.aliyusufergin.n8n-ytdlp."
        expected = {
            "n8n.version": self.lock["n8n"]["version"],
            "n8n.digest": self.lock["n8n"]["image_digest"],
            "runners.digest": self.lock["n8n"]["runners_digest"],
            "yt-dlp.tag": self.lock["yt_dlp"]["tag"],
            "yt-dlp.sha256.amd64": self.lock["yt_dlp"]["sha256"]["yt-dlp_musllinux"],
            "yt-dlp.sha256.arm64": self.lock["yt_dlp"]["sha256"]["yt-dlp_musllinux_aarch64"],
            "ffmpeg.version": self.lock["ffmpeg"]["version"],
            "ffmpeg.digest": self.lock["ffmpeg"]["image_digest"],
        }
        for name, value in expected.items():
            with self.subTest(label=name):
                self.assertEqual(labels.get(prefix + name), value)
        build_tag = labels.get(prefix + "build-tag", "")
        self.assertRegex(build_tag, r"^[0-9]+\.[0-9]+\.[0-9]+-[0-9]{8}-[0-9]{4}$")
        self.assertEqual(build_tag.split("-")[0], self.lock["n8n"]["version"])
        self.assertEqual(labels.get("org.opencontainers.image.version"), build_tag)
        self.assertEqual(labels.get("org.opencontainers.image.source"),
                         "https://github.com/aliyusufergin/n8n-custom-ytdlp")
        self.assertRegex(labels.get("org.opencontainers.image.revision", ""), r"^[0-9a-f]{40}$")
        created = labels.get("org.opencontainers.image.created", "")
        self.assertEqual(datetime.fromisoformat(created.replace("Z", "+00:00")).utcoffset(),
                         timezone.utc.utcoffset(None))

    def test_default_readiness(self):
        name = "n8n-ytdlp-test-" + uuid.uuid4().hex
        self.addCleanup(subprocess.run, ["docker", "rm", "--force", "--volumes", name],
                        check=True, capture_output=True, text=True, timeout=30)
        subprocess.run(
            ["docker", "run", "--detach", "--name", name, "--network", "none", self.image],
            check=True, capture_output=True, text=True, timeout=30,
        )
        # Probe from inside the container so no host ports or external network are needed.
        probe = """
            require('node:http').get('http://127.0.0.1:5678/healthz/readiness',
                {timeout: 1000}, response => {
                    console.log(response.statusCode);
                    response.resume();
                    process.exitCode = response.statusCode === 200 ? 0 : 1;
                }).on('timeout', function () { this.destroy(); })
                  .on('error', () => { process.exitCode = 1; });
        """
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            result = subprocess.run(["docker", "exec", name, "node", "-e", probe],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip() == "200":
                return
            running = subprocess.check_output(
                ["docker", "inspect", "--format", "{{.State.Running}}", name],
                text=True, timeout=10,
            ).strip()
            if running != "true":
                break
            time.sleep(1)
        logs = subprocess.run(["docker", "logs", name], capture_output=True,
                              text=True, timeout=10)
        self.fail("n8n did not become ready with default settings:\n" + logs.stdout + logs.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Candidate image already loaded in Docker")
    parser.add_argument("lock", type=Path, help="JSON build inputs for this image")
    parser.add_argument("--youtube-network", choices=("bridge", "none"), default="bridge",
                        help="Use none to reproduce a warning-only YouTube network failure")
    args, tests = parser.parse_known_args()
    ImageTests.image = args.image
    ImageTests.lock = json.loads(args.lock.read_text())
    ImageTests.youtube_network = args.youtube_network
    unittest.main(argv=[__file__, *tests], verbosity=2)
