from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autoskill_agent import skillgen
from autoskill_agent.section_a_integration import run_section_a_skillgen_demo


class SectionAIntegrationTests(unittest.TestCase):
    def test_runs_section_a_candidate_through_section_b_skillgen(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        events_path = repo_root / "tests" / "fixtures" / "cash_recon_events.jsonl"
        workbook_path = repo_root / "skillforge_finance_demo_cash_recon.xlsx"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_section_a_skillgen_demo(
                root,
                events_path=events_path,
                workbook_path=workbook_path,
                force=True,
                execute=True,
            )

            paths = skillgen.paths(root)
            candidates = skillgen.read_section_a_candidates(root)

            self.assertEqual(result["status"], "executed")
            self.assertEqual(result["candidate"]["candidate_id"], "cand_daily_cash_recon_001")
            self.assertEqual(candidates[0]["contract_version"], "section_a.skill_candidate.v1")
            self.assertTrue((paths.events_dir / "workflow_episodes.jsonl").exists())
            self.assertEqual(result["install"]["status"], "installed")
            self.assertEqual(result["install"]["skill_id"], "daily_cash_reconciliation")
            self.assertGreaterEqual(len(result["matches"]), 1)
            self.assertEqual(result["execution"]["validation"]["status"], "passed")
            self.assertTrue((paths.drafts_dir / "cash_recon_2026_06_15_reply.eml").exists())
            self.assertTrue(
                (paths.workbooks_dir / "generated" / "skillforge_finance_demo_cash_recon_2026_06_15_reconciled.xlsx").exists()
            )

    def test_explicit_relative_inputs_can_target_separate_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_section_a_skillgen_demo(
                Path(temp_dir),
                events_path=Path("tests/fixtures/cash_recon_events.jsonl"),
                workbook_path=Path("skillforge_finance_demo_cash_recon.xlsx"),
                force=True,
                execute=False,
            )

            self.assertEqual(result["status"], "preview_ready")
            self.assertEqual(result["candidate"]["candidate_id"], "cand_daily_cash_recon_001")


if __name__ == "__main__":
    unittest.main()
