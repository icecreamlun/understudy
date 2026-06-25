from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autoskill_agent import core


class AutoSkillAgentTests(unittest.TestCase):
    def test_full_demo_flow_generates_registered_skill_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = core.init_demo(root, force=True)
            candidate = core.observe(root)
            manifest = core.approve_candidate(root, approved_by="test")
            result = core.run_registered_skill(root, approve=True)

            self.assertEqual(candidate["id"], "fde-intake-skill")
            self.assertEqual(manifest["id"], "fde-intake-skill")
            self.assertTrue(result["wrote"])
            self.assertTrue(paths.completed_csv.exists())
            self.assertTrue((paths.skills_dir / "fde-intake-skill" / "SKILL.md").exists())
            self.assertTrue((paths.skills_dir / "registry.json").exists())

            completed_rows = core.read_csv_rows(paths.completed_csv)
            umbrella = next(row for row in completed_rows if row["email_id"] == "email-004")
            self.assertEqual(umbrella["request_type"], "field_mapping")
            self.assertEqual(umbrella["owner"], "Ravi")
            self.assertEqual(umbrella["due_date"], "2026-06-21")

    def test_preview_does_not_write_completed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = core.init_demo(root, force=True)
            core.observe(root)
            core.approve_candidate(root, approved_by="test")
            result = core.run_registered_skill(root, approve=False)

            self.assertFalse(result["wrote"])
            self.assertFalse(paths.completed_csv.exists())
            self.assertGreater(len(result["preview"]), 0)


if __name__ == "__main__":
    unittest.main()

