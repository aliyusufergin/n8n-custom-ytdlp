"""Offline acceptance tests through the updater command's JSON interface."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.lock_path = Path(temporary.name) / "lock.json"
        self.lock = json.loads((ROOT / "build-inputs.lock.json").read_text())
        self.lock["n8n"]["version"] = "2.38.7"
        self.lock_path.write_text(json.dumps(self.lock))

    def invoke(self, trigger: str, now: str = "2026-09-12T06:17:59Z") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/updater.py"),
             "--lock", str(self.lock_path), "--trigger", trigger, "--now", now],
            capture_output=True, text=True, timeout=10,
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
        self.assertEqual(plan["new_lock"], self.lock)
        self.assertEqual(plan["notices"], [])

    def test_manual_and_push_build_with_unchanged_inputs(self) -> None:
        for trigger in ("manual", "push"):
            with self.subTest(trigger=trigger):
                plan = self.command(trigger)
                self.assertIs(plan["build"], True)
                self.assertEqual(plan["reason"], f"{trigger} trigger")
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
