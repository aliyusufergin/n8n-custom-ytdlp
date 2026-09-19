"""Offline acceptance tests through the updater command's JSON interface."""

import hashlib
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
N8N_LATEST = "https://api.github.com/repos/n8n-io/n8n/releases/latest"
REGISTRY = "https://registry-1.docker.io/v2"
FFMPEG_REPOSITORY = f"{REGISTRY}/mwader/static-ffmpeg"
# What --record saves for a Docker tag that does not exist (yet).
UNKNOWN_TAG = {"status": 404, "headers": {}}
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
# Stable-track releases and their Docker Hub index digests, as recorded.
N8N_2_38_7: dict = {
    "version": "2.38.7",
    "image_digest": "sha256:a8c95f75c6fdf65f5f2b7a7b354744eaa1c62bb911b5c00af6499c3f38e4cd32",
    "runners_digest": "sha256:82167390e7c3b58ccb30147c9f642997b3074233f1d4bf44fdc1d8a59266b27f",
}
N8N_2_39_8: dict = {
    "version": "2.39.8",
    "image_digest": "sha256:b73045abaddb40cb4024e86eea1b1f69093501a7339f685a4cd486b7743d23ae",
    "runners_digest": "sha256:66dccaedd817cca16a20763239652363ee814a396829027155b460b9f45cd8e3",
}
# The highest X.Y.Z tag of mwader/static-ffmpeg and its Docker Hub index digest, as recorded.
FFMPEG_9_0_1: dict = {
    "version": "9.0.1",
    "image_digest": "sha256:54e55b0cb8f672870fc38ceb2e6c411855cb3b39c505f5f3b2505ee01ed5f2b7",
}
FFMPEG_8_1_2: dict = {
    "version": "8.1.2",
    "image_digest": "sha256:33f770f812cbfc3de96c547157fc9faf8bd95a36481753439ffa761045167585",
}
FFMPEG_9_0_1_INDEX = f"{FFMPEG_REPOSITORY}/manifests/{FFMPEG_9_0_1['image_digest']}"


class UpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.lock_path = Path(temporary.name) / "lock.json"
        self.lock = json.loads((ROOT / "build-inputs.lock.json").read_text())
        self.lock["n8n"] = dict(N8N_2_38_7)
        self.lock["yt_dlp"] = RECORDED_NIGHTLY
        self.lock["ffmpeg"] = FFMPEG_9_0_1
        self.lock_path.write_text(json.dumps(self.lock))
        self.upstream = Path(temporary.name) / "upstream"
        self.replay()

    def replay(self, n8n: str = "n8n-2.38.7", yt_dlp: str = "yt-dlp-nightly-2026.09.16.232951",
               ffmpeg: str = "ffmpeg-9.0.1") -> None:
        """Answer upstream requests from exactly one n8n, one yt-dlp and one ffmpeg recording."""
        shutil.rmtree(self.upstream, ignore_errors=True)
        for recording in (n8n, yt_dlp, ffmpeg):
            shutil.copytree(RECORDINGS / recording, self.upstream, dirs_exist_ok=True)

    def recorded(self, url: str, recording: Path | None = None) -> Path:
        return (recording or self.upstream) / quote(url, safe="")

    def mark_latest(self, tag: str) -> None:
        """Let the recorded latest release carry another tag, e.g. a future n8n@3.0.0."""
        latest = self.recorded(N8N_LATEST)
        latest.write_text(json.dumps({**json.loads(latest.read_bytes()), "tag_name": tag}))

    def recorded_ffmpeg_index(self) -> dict:
        """Return the recorded index of mwader/static-ffmpeg:9.0.1."""
        return json.loads(self.recorded(FFMPEG_9_0_1_INDEX).read_bytes())

    def list_ffmpeg_tags(self, *tags: str) -> None:
        """Let the recorded tag list of mwader/static-ffmpeg also name tags."""
        response = self.recorded(f"{FFMPEG_REPOSITORY}/tags/list")
        tag_list = json.loads(response.read_bytes())
        response.write_text(json.dumps({**tag_list, "tags": [*tag_list["tags"], *tags]}))

    def push_ffmpeg(self, tag: str, index: dict) -> str:
        """Let the recorded registry serve index under tag, as a push would; return its digest."""
        body = json.dumps(index).encode()
        digest = f"sha256:{hashlib.sha256(body).hexdigest()}"
        self.recorded(f"HEAD {FFMPEG_REPOSITORY}/manifests/{tag}").write_text(
            json.dumps({"status": 200, "headers": {"docker-content-digest": digest}}))
        self.recorded(f"{FFMPEG_REPOSITORY}/manifests/{digest}").write_bytes(body)
        return digest

    def assert_fails_without_plan(self, result: subprocess.CompletedProcess, message: str) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

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

    def test_scheduled_stable_track_update_plans_a_build(self) -> None:
        self.replay(n8n="n8n-2.39.8")
        plan = self.command("scheduled")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["reason"], "build inputs changed")
        self.assertEqual(plan["change_summary"], "n8n 2.38.7 → 2.39.8")
        self.assertEqual(plan["new_lock"], {**self.lock, "n8n": N8N_2_39_8})
        self.assertEqual(plan["floating_tags"], ["2", "2.39", "2.39.8"])
        self.assertEqual(plan["build_tag"], "2.39.8-20260912-0617")
        self.assertEqual(plan["notices"], [])

    def test_changed_upstream_digest_under_the_same_version_plans_a_build(self) -> None:
        for field in ("image_digest", "runners_digest"):
            with self.subTest(field=field):
                # The lock still holds the digest n8n pushed before re-pushing the same tag.
                self.lock["n8n"] = {**N8N_2_38_7, field: "sha256:" + "0" * 64}
                self.lock_path.write_text(json.dumps(self.lock))
                plan = self.command("scheduled")
                self.assertIs(plan["build"], True)
                self.assertEqual(plan["reason"], "build inputs changed")
                self.assertEqual(plan["change_summary"], "n8n 2.38.7 republished")
                self.assertEqual(plan["new_lock"], {**self.lock, "n8n": N8N_2_38_7})

    def test_scheduled_new_ffmpeg_version_plans_a_build(self) -> None:
        self.lock["ffmpeg"] = FFMPEG_8_1_2
        self.lock_path.write_text(json.dumps(self.lock))
        plan = self.command("scheduled")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["reason"], "build inputs changed")
        self.assertEqual(plan["change_summary"], "ffmpeg 8.1.2 → 9.0.1")
        self.assertEqual(plan["new_lock"], {**self.lock, "ffmpeg": FFMPEG_9_0_1})
        self.assertEqual(plan["floating_tags"], ["2", "2.38", "2.38.7"])

    def test_changed_ffmpeg_digest_under_the_same_version_plans_a_build(self) -> None:
        # The lock still holds the digest mwader pushed before re-pushing the same tag.
        self.lock["ffmpeg"] = {**FFMPEG_9_0_1, "image_digest": "sha256:" + "0" * 64}
        self.lock_path.write_text(json.dumps(self.lock))
        plan = self.command("scheduled")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["reason"], "build inputs changed")
        self.assertEqual(plan["change_summary"], "ffmpeg 9.0.1 republished")
        self.assertEqual(plan["new_lock"], {**self.lock, "ffmpeg": FFMPEG_9_0_1})

    def test_new_ffmpeg_major_is_followed_from_its_first_release(self) -> None:
        # FFmpeg names a line's first release X.Y and its patches X.Y.Z, e.g. 9.0 before 9.0.1.
        self.list_ffmpeg_tags("9.0.10", "10.0", "10.0-amd64", "10.0-arm64")
        digest = self.push_ffmpeg("10.0", self.recorded_ffmpeg_index())
        plan = self.command("scheduled")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["change_summary"], "ffmpeg 9.0.1 → 10.0")
        self.assertEqual(plan["new_lock"]["ffmpeg"], {"version": "10.0", "image_digest": digest})
        with self.subTest("its first patch release follows"):
            self.list_ffmpeg_tags("10.0.1")
            digest = self.push_ffmpeg("10.0.1", {**self.recorded_ffmpeg_index(), "annotations": {}})
            plan = self.command("scheduled")
            self.assertEqual(plan["change_summary"], "ffmpeg 9.0.1 → 10.0.1")
            self.assertEqual(plan["new_lock"]["ffmpeg"], {"version": "10.0.1", "image_digest": digest})

    def test_ffmpeg_tags_that_name_no_release_are_ignored(self) -> None:
        # The recorded list already holds tags such as 9.0.1-arm64, 7.0-2, latest and test-latest.
        self.list_ffmpeg_tags("11", "11.0-1", "11.0-arm64", "11.0.0-amd64", "v11.0.0", "latest-11")
        plan = self.command("scheduled")
        self.assertIs(plan["build"], False)
        self.assertEqual(plan["new_lock"], self.lock)

    def test_ffmpeg_index_missing_a_platform_fails_without_a_plan(self) -> None:
        for platform in ("linux/amd64", "linux/arm64"):
            with self.subTest(platform=platform):
                self.replay()
                index = self.recorded_ffmpeg_index()
                index["manifests"] = [manifest for manifest in index["manifests"]
                                      if manifest["platform"]["architecture"] != platform.split("/")[1]]
                self.push_ffmpeg("9.0.1", index)
                self.assert_fails_without_plan(
                    self.invoke("scheduled"), f"mwader/static-ffmpeg:9.0.1 index has no {platform}")
        with self.subTest("single-platform manifest instead of an index"):
            self.replay()
            self.push_ffmpeg("9.0.1", {
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "config": self.recorded_ffmpeg_index()["manifests"][0],
                "layers": [],
            })
            self.assert_fails_without_plan(
                self.invoke("scheduled"), "mwader/static-ffmpeg:9.0.1 index has no linux/amd64")

    def test_ffmpeg_index_that_does_not_match_its_digest_fails_without_a_plan(self) -> None:
        self.lock["ffmpeg"] = FFMPEG_8_1_2
        self.lock_path.write_text(json.dumps(self.lock))
        # The same index, re-serialized, is no longer the index its digest names.
        self.recorded(FFMPEG_9_0_1_INDEX).write_text(json.dumps(self.recorded_ffmpeg_index()))
        self.assert_fails_without_plan(
            self.invoke("scheduled"), "mwader/static-ffmpeg:9.0.1 index does not match its digest")

    def test_listed_ffmpeg_tag_without_an_index_fails_without_a_plan(self) -> None:
        self.recorded(f"HEAD {FFMPEG_REPOSITORY}/manifests/9.0.1").write_text(json.dumps(UNKNOWN_TAG))
        self.assert_fails_without_plan(self.invoke("scheduled"), "mwader/static-ffmpeg:9.0.1")

    def test_latest_release_marker_is_followed_even_when_flagged_prerelease(self) -> None:
        self.replay(n8n="n8n-2.39.8")
        latest = self.recorded(N8N_LATEST)
        release = json.loads(latest.read_bytes())
        self.assertIs(release["prerelease"], False)
        latest.write_text(json.dumps({**release, "prerelease": True}))
        plan = self.command("scheduled")
        self.assertEqual(plan["new_lock"]["n8n"], N8N_2_39_8)

    def test_unflagged_beta_line_patch_is_ignored_while_the_marker_names_the_stable_track(self) -> None:
        # On 2026-09-07 the marker named n8n@2.37.11, while beta-line n8n@2.38.1 had
        # prerelease=false, so "the highest non-prerelease release" was a beta (ADR 0002).
        self.lock["n8n"] = {
            "version": "2.37.10",
            "image_digest": "sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec",
            "runners_digest": "sha256:63bda67eac04e5a2a42683730e0d43deed7e463a92f5bfca2090d0189a909c42",
        }
        self.lock_path.write_text(json.dumps(self.lock))
        self.replay(n8n="n8n-2.37.11")
        plan = self.command("scheduled")
        self.assertEqual(plan["change_summary"], "n8n 2.37.10 → 2.37.11")
        self.assertEqual(plan["new_lock"]["n8n"], {
            "version": "2.37.11",
            "image_digest": "sha256:27b67c39bb1722317e2a6729b31f16282406d3341520793d47431082218d15bb",
            "runners_digest": "sha256:06cadb62f8da9a01318aaa9e70caab57570208ef450e68b5cf6e832698fcdef9",
        })
        self.assertEqual(plan["floating_tags"], ["2", "2.37", "2.37.11"])

    def test_newly_marked_version_without_a_docker_tag_is_skipped_until_a_later_run(self) -> None:
        for repository in ("n8nio/n8n", "n8nio/runners"):
            with self.subTest(repository=repository):
                self.replay(n8n="n8n-2.39.8")
                self.recorded(f"HEAD {REGISTRY}/{repository}/manifests/2.39.8").write_text(
                    json.dumps(UNKNOWN_TAG))
                result = self.invoke("scheduled")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"{repository}:2.39.8", result.stderr)
                plan = json.loads(result.stdout)
                self.assertIs(plan["build"], False)
                self.assertEqual(plan["new_lock"], self.lock)
                self.assertEqual(plan["floating_tags"], ["2", "2.38", "2.38.7"])

    def test_missing_docker_tag_of_the_locked_version_fails_without_a_plan(self) -> None:
        for repository in ("n8nio/n8n", "n8nio/runners"):
            with self.subTest(repository=repository):
                self.replay()
                self.recorded(f"HEAD {REGISTRY}/{repository}/manifests/2.38.7").write_text(
                    json.dumps(UNKNOWN_TAG))
                self.assert_fails_without_plan(self.invoke("scheduled"), f"{repository}:2.38.7")

    def test_n8n_3_marker_keeps_the_locked_version_when_its_minor_has_no_later_patch(self) -> None:
        for marker in ("n8n@3.0.0", "n8n@3.1.2"):
            with self.subTest(marker=marker):
                self.replay()
                self.mark_latest(marker)
                plan = self.command("scheduled")
                self.assertIs(plan["build"], False)
                self.assertEqual(plan["new_lock"], self.lock)
                self.assertEqual(plan["floating_tags"], ["2", "2.38", "2.38.7"])
                # notify.py opens at most one issue per key, so every 3.x marker shares one.
                [notice] = plan["notices"]
                self.assertEqual(notice["key"], "n8n-3")
                self.assertEqual(notice["title"], "n8n 3.x available")
                self.assertIn("2.38", notice["body"])

    def test_n8n_3_marker_follows_later_patches_of_the_locked_minor(self) -> None:
        self.lock["n8n"] = {
            "version": "2.38.5",
            "image_digest": "sha256:f98bb7c2e0818412e414d456ab31ef48be2dc5ce5d1e6fae7ae171fbb6923093",
            "runners_digest": "sha256:427170bc670beff179e3bf20ddf4c5210a6cbb623f01bb7bc17fbcd425d34067",
        }
        self.lock_path.write_text(json.dumps(self.lock))
        self.mark_latest("n8n@3.0.0")
        plan = self.command("scheduled")
        self.assertIs(plan["build"], True)
        self.assertEqual(plan["change_summary"], "n8n 2.38.5 → 2.38.7")
        self.assertEqual(plan["new_lock"], {**self.lock, "n8n": N8N_2_38_7})
        self.assertEqual(plan["floating_tags"], ["2", "2.38", "2.38.7"])
        self.assertEqual([notice["key"] for notice in plan["notices"]], ["n8n-3"])
        with self.subTest("later patch not pushed yet"):
            self.recorded(f"HEAD {REGISTRY}/n8nio/n8n/manifests/2.38.7").write_text(json.dumps(UNKNOWN_TAG))
            result = self.invoke("scheduled")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertIs(plan["build"], False)
            self.assertEqual(plan["new_lock"], self.lock)
            self.assertEqual([notice["key"] for notice in plan["notices"]], ["n8n-3"])

    def test_bad_checksum_signature_fails_without_a_plan(self) -> None:
        sums = self.recorded(f"{DOWNLOAD}/2026.09.16.232951/SHA2-256SUMS")
        signature = self.recorded(f"{DOWNLOAD}/2026.09.16.232951/SHA2-256SUMS.sig")
        other_signature = self.recorded(f"{DOWNLOAD}/2025.08.30.232839/SHA2-256SUMS.sig",
                                        RECORDINGS / "yt-dlp-nightly-2025.08.30.232839").read_bytes()
        tampered = sums.read_bytes().replace(
            RECORDED_NIGHTLY["sha256"]["yt-dlp_musllinux"].encode(),
            PREVIOUS_NIGHTLY["sha256"]["yt-dlp_musllinux"].encode())
        self.assertNotEqual(tampered, sums.read_bytes())
        for case, response, contents in (("another nightly's signature", signature, other_signature),
                                         ("tampered checksum list", sums, tampered)):
            with self.subTest(case=case):
                self.replay()
                response.write_bytes(contents)
                self.assert_fails_without_plan(self.invoke("manual"), "SHA2-256SUMS signature")

    def test_nightly_missing_a_musllinux_asset_fails_without_a_plan(self) -> None:
        # The last nightly before musllinux builds: validly signed, but without either asset.
        self.replay(yt_dlp="yt-dlp-nightly-2025.08.30.232839")
        self.assert_fails_without_plan(
            self.invoke("manual"), "yt-dlp nightly 2025.08.30.232839 has no yt-dlp_musllinux asset")

    def test_unrecorded_response_fails_instead_of_using_the_network(self) -> None:
        url = f"{DOWNLOAD}/2026.09.16.232951/SHA2-256SUMS.sig"
        self.recorded(url).unlink()
        self.assert_fails_without_plan(self.invoke("manual"), f"no recorded response for {url}")

    def test_manual_and_push_build_with_unchanged_inputs(self) -> None:
        for trigger in ("manual", "push"):
            with self.subTest(trigger=trigger):
                plan = self.command(trigger)
                self.assertIs(plan["build"], True)
                self.assertEqual(plan["reason"], f"{trigger} trigger")
                self.assertEqual(plan["change_summary"], "n8n 2.38.7 rebuild")
                self.assertEqual(plan["new_lock"], self.lock)

    def test_tags_follow_planned_version_and_run_utc_minute(self) -> None:
        for version, floating_tags in (
            ("2.38.7", ["2", "2.38", "2.38.7"]),
            ("2.39.8", ["2", "2.39", "2.39.8"]),
        ):
            with self.subTest(version=version):
                self.replay(n8n=f"n8n-{version}")
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
