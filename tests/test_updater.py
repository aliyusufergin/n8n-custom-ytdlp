"""Offline acceptance tests through the updater command's JSON interface."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
RECORDINGS = ROOT / "tests/fixtures/upstream"
DOWNLOAD = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download"
# The nightly that releases/latest named when the recording was made.
RECORDED_NIGHTLY: dict = {
    "tag": "2026.09.16.232951",
    "sha256": {
        "yt-dlp_musllinux": "6abd8a1a90ec74ac4803d7d60732ab39fff5f6c71833b38c163e1a08f581dd43",
        "yt-dlp_musllinux_aarch64": "13e82c4ed4bc8cda3ed279c3e7ba9aa184ec614afce745c582ae78edb5b9bb36",
    },
}
PREVIOUS_NIGHTLY: dict = {
    "tag": "2026.08.30.232658",
    "sha256": {
        "yt-dlp_musllinux": "a70990ba6858c4215aeab7f629290079b9575713079bcb7da4368ff1d55c5021",
        "yt-dlp_musllinux_aarch64": "6b1e6b9ad1b6a4dfd9a45c916ddbc2ccebb6936d480a75fceb3d78bd3b46f757",
    },
}


class UpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.lock_path = Path(temporary.name) / "lock.json"
        self.lock = json.loads((ROOT / "build-inputs.lock.json").read_text())
        self.lock["n8n"]["version"] = "2.38.7"
        self.lock["yt_dlp"] = RECORDED_NIGHTLY
        self.lock_path.write_text(json.dumps(self.lock))
        self.upstream = Path(temporary.name) / "upstream"
        self.replay("yt-dlp-nightly-2026.09.16.232951")

    def replay(self, recording: str) -> None:
        """Answer upstream requests from exactly one recording."""
        shutil.rmtree(self.upstream, ignore_errors=True)
        shutil.copytree(RECORDINGS / recording, self.upstream)

    def recorded(self, url: str) -> Path:
        return self.upstream / quote(url, safe="")

    def invoke(self, trigger: str, now: str = "2026-09-12T06:17:59Z") -> subprocess.CompletedProcess:
        # A dead proxy makes any accidental live request fail instead of reaching upstream.
        env = {name: value for name, value in os.environ.items()
               if name.lower() not in ("github_token", "no_proxy")}
        env.update(http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9")
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/updater.py"),
             "--lock", str(self.lock_path), "--trigger", trigger, "--now", now,
             "--replay", str(self.upstream)],
            capture_output=True, text=True, timeout=10, env=env,
        )

    def command(self, trigger: str, now: str = "2026-09-12T06:17:59Z") -> dict:
        result = self.invoke(trigger, now)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_scheduled_unchanged_inputs_skip_build(self) -> None:
        plan = self.command("scheduled")
        self.assertIs(plan["build"], False)
        self.assertEqual(plan["reason"], "build inputs unchanged")
        self.assertIsNone(plan["change_summary"])
        self.assertEqual(plan["new_lock"], self.lock)
        self.assertEqual(plan["notices"], [])

    def test_scheduled_new_nightly_plans_a_build_with_verified_checksums(self) -> None:
        self.lock["yt_dlp"] = PREVIOUS_NIGHTLY
        self.lock_path.write_text(json.dumps(self.lock))
        plan = self.command("scheduled")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["reason"], "build inputs changed")
        self.assertEqual(plan["change_summary"], "yt-dlp 2026.08.30.232658 → 2026.09.16.232951")
        self.assertEqual(plan["new_lock"], {**self.lock, "yt_dlp": RECORDED_NIGHTLY})
        self.assertEqual(plan["floating_tags"], ["2", "2.38", "2.38.7"])

    def test_bad_checksum_signature_fails_without_a_plan(self) -> None:
        sums = self.recorded(f"{DOWNLOAD}/2026.09.16.232951/SHA2-256SUMS")
        signature = self.recorded(f"{DOWNLOAD}/2026.09.16.232951/SHA2-256SUMS.sig")
        other_signature = (RECORDINGS / "yt-dlp-nightly-2025.08.30.232839" / quote(
            f"{DOWNLOAD}/2025.08.30.232839/SHA2-256SUMS.sig", safe="")).read_bytes()
        tampered = sums.read_bytes().replace(
            RECORDED_NIGHTLY["sha256"]["yt-dlp_musllinux"].encode(),
            PREVIOUS_NIGHTLY["sha256"]["yt-dlp_musllinux"].encode())
        self.assertNotEqual(tampered, sums.read_bytes())
        for case, response, contents in (("another nightly's signature", signature, other_signature),
                                         ("tampered checksum list", sums, tampered)):
            with self.subTest(case=case):
                self.replay("yt-dlp-nightly-2026.09.16.232951")
                response.write_bytes(contents)
                result = self.invoke("manual")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("SHA2-256SUMS signature", result.stderr)

    def test_nightly_missing_a_musllinux_asset_fails_without_a_plan(self) -> None:
        # The last nightly before musllinux builds: validly signed, but without either asset.
        self.replay("yt-dlp-nightly-2025.08.30.232839")
        result = self.invoke("manual")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("yt-dlp nightly 2025.08.30.232839 has no yt-dlp_musllinux asset", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unrecorded_response_fails_instead_of_using_the_network(self) -> None:
        url = f"{DOWNLOAD}/2026.09.16.232951/SHA2-256SUMS.sig"
        self.recorded(url).unlink()
        result = self.invoke("manual")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(f"no recorded response for {url}", result.stderr)

    def test_manual_and_push_build_with_unchanged_inputs(self) -> None:
        for trigger in ("manual", "push"):
            with self.subTest(trigger=trigger):
                plan = self.command(trigger)
                self.assertIs(plan["build"], True)
                self.assertEqual(plan["reason"], f"{trigger} trigger")
                self.assertEqual(plan["change_summary"], "n8n 2.38.7 rebuild")
                self.assertEqual(plan["new_lock"], self.lock)

    def test_tags_follow_locked_version_and_run_utc_minute(self) -> None:
        for version, floating_tags in (
            ("2.38.7", ["2", "2.38", "2.38.7"]),
            ("2.9.0", ["2", "2.9", "2.9.0"]),
        ):
            with self.subTest(version=version):
                self.lock["n8n"]["version"] = version
                self.lock_path.write_text(json.dumps(self.lock))
                plan = self.command("manual", "2026-01-01T01:17:59+03:00")
                self.assertEqual(plan["floating_tags"], floating_tags)
                self.assertEqual(plan["build_tag"], f"{version}-20251231-2217")
                self.assertRegex(plan["build_tag"],
                                 r"^[0-9]+\.[0-9]+\.[0-9]+-[0-9]{8}-[0-9]{4}$")

    def test_scheduled_plan_also_contains_tags(self) -> None:
        plan = self.command("scheduled")
        self.assertEqual(plan["floating_tags"], ["2", "2.38", "2.38.7"])
        self.assertEqual(plan["build_tag"], "2.38.7-20260912-0617")

    def test_pull_request_plans_a_build_for_testing(self) -> None:
        plan = self.command("pull_request")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["reason"], "pull_request trigger")

    def test_rejects_ambiguous_or_invalid_run_time(self) -> None:
        for now in ("2026-09-12T06:17:00", "not-a-time"):
            with self.subTest(now=now):
                result = self.invoke("manual", now)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("--now", result.stderr)

    def test_rejects_versions_that_cannot_form_build_tags(self) -> None:
        for version in ("2.38.7-beta.1", "2.38", "latest", "2.38.x", None):
            with self.subTest(version=version):
                self.lock["n8n"]["version"] = version
                self.lock_path.write_text(json.dumps(self.lock))
                result = self.invoke("manual")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("n8n version", result.stderr)

    def test_manual_plan_rejects_n8n_3_before_requesting_a_build(self) -> None:
        self.lock["n8n"]["version"] = "3.0.0"
        self.lock_path.write_text(json.dumps(self.lock))
        result = self.invoke("manual")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("major 2", result.stderr)

    def test_planning_preserves_last_published_result_and_lock_file(self) -> None:
        self.lock["published"] = {
            "build_tag": "2.38.7-20260911-0617",
            "image_digest": "sha256:" + "a" * 64,
        }
        self.lock_path.write_text(json.dumps(self.lock))
        original = self.lock_path.read_bytes()
        plan = self.command("manual")
        self.assertEqual(plan["new_lock"], self.lock)
        self.assertEqual(self.lock_path.read_bytes(), original)
        self.assertEqual(plan["build_tag"], "2.38.7-20260912-0617")

    def test_invalid_lock_or_trigger_fails_without_a_plan(self) -> None:
        for contents, trigger in (("{", "manual"), ("{}", "manual"),
                                  (json.dumps(self.lock), "unknown")):
            with self.subTest(contents=contents, trigger=trigger):
                self.lock_path.write_text(contents)
                result = self.invoke(trigger)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)
        self.lock_path.unlink()
        result = self.invoke("scheduled")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("cannot read lock file", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
