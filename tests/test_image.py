"""Candidate-image acceptance tests; only Docker's public interface is used."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import unittest
import uuid


class ImageTests(unittest.TestCase):
    image: str
    lock: dict

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

    def test_system_yt_dlp_config(self):
        self.assertEqual(self.command("cat", "/etc/yt-dlp.conf"), "--js-runtimes node")

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
    args, tests = parser.parse_known_args()
    ImageTests.image = args.image
    ImageTests.lock = json.loads(args.lock.read_text())
    unittest.main(argv=[__file__, *tests], verbosity=2)
