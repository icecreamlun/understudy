from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autoskill_agent import skillgen


class SkillGenerationTests(unittest.TestCase):
    def test_installs_skill_bundle_from_pattern_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skillgen.bootstrap_demo(root, force=True)
            review = skillgen.create_review_session(root, "cand_daily_cash_recon_001")
            feedback = skillgen.default_human_feedback(root, review["review_session_id"])
            submit = skillgen.submit_feedback(root, review["review_session_id"], feedback)
            install = skillgen.install_skill(root, review["review_session_id"])

            self.assertEqual(submit["status"], "ok")
            self.assertEqual(install["status"], "installed")

            skill_dir = Path(install["skill_dir"])
            self.assertTrue((skill_dir / "skill.yaml").exists())
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "policy.yaml").exists())
            self.assertTrue((skill_dir / "examples" / "episode_001.json").exists())
            self.assertTrue((skill_dir / "tests" / "validation_cases.json").exists())
            self.assertTrue((skill_dir / "audit_schema.json").exists())

            yaml_text = (skill_dir / "skill.yaml").read_text(encoding="utf-8")
            skill_json = skillgen.read_json(skill_dir / "skill.json")
            self.assertIn('schema_version: "skill.workflow.v1"', yaml_text)
            self.assertIn('skill_id: "daily_cash_reconciliation"', yaml_text)
            self.assertIn("triggers:", yaml_text)
            self.assertIn("workflow:", yaml_text)
            self.assertIn("expected_outcome:", yaml_text)
            self.assertIn('type: "human_approval"', yaml_text)
            self.assertIn("network: false", yaml_text)
            self.assertIn("send_email: false", yaml_text)
            self.assertEqual(skill_json["schema_version"], "skill.workflow.v1")
            self.assertEqual(skill_json["source_candidate"]["contract_version"], "section_a.skill_candidate.v1")
            self.assertEqual(skill_json["triggers"][0]["conditions"][0]["field"], "email.subject")
            self.assertEqual(skill_json["triggers"][0]["conditions"][0]["operator"], "starts_with")
            self.assertEqual(skill_json["workflow"]["steps"][0]["order"], 1)
            approval_steps = [step for step in skill_json["workflow"]["steps"] if step["type"] == "human_approval"]
            write_steps = [step for step in skill_json["workflow"]["steps"] if step.get("action_type") == "write_xlsx_update"]
            self.assertEqual(len(approval_steps), 1)
            self.assertEqual(len(write_steps), 1)
            self.assertLess(approval_steps[0]["order"], write_steps[0]["order"])
            self.assertIn("summary", skill_json["workflow"]["expected_outcome"])

    def test_reads_section_a_skill_candidates_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skillgen.bootstrap_demo(root, force=True)

            candidates = skillgen.read_section_a_candidates(root)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["contract_version"], "section_a.skill_candidate.v1")

            review = skillgen.create_review_session(root, "cand_daily_cash_recon_001")
            self.assertEqual(review["source_contract_version"], "section_a.skill_candidate.v1")
            self.assertEqual(review["suggested"]["trigger"]["conditions"][0]["type"], "subject_prefix")
            self.assertEqual(review["suggested"]["inputs"][1]["path"], "workspace/workbooks/cash_recon.xlsx")
            self.assertGreater(len(review["suggested"]["workflow_steps"]), 7)

    def test_merges_valid_model_plan_into_review_suggestions(self) -> None:
        candidate = skillgen.default_section_a_skill_candidate()
        review = skillgen.build_section_a_review("review_cand_daily_cash_recon_001", candidate)
        model_steps = [dict(step) for step in review["suggested"]["workflow_steps"]]
        model_steps[0]["title"] = "Parse inbound bank file"
        model_steps[0]["summary"] = "Read and normalize the bank file rows for reconciliation."
        plan = {
            "description": "Model-refined local cash reconciliation workflow.",
            "workflow_steps": model_steps,
            "expected_outcome": {
                "summary": "Creates a reconciled spreadsheet and local draft reply.",
                "files_created": [
                    "workspace/workbooks/generated/skillforge_finance_demo_cash_recon_{event_date}_reconciled.xlsx",
                    "workspace/mail/drafts/{skill_id}_{event_date}_reply.eml",
                ],
                "files_modified": [
                    "workspace/workbooks/skillforge_finance_demo_cash_recon.skill_updates.jsonl",
                    "workspace/events/events.jsonl",
                ],
                "side_effects": ["Email remains a draft and is not sent"],
            },
            "validation_rules": ["model confirms approval gate"],
        }

        suggested, applied, warnings = skillgen.merge_model_plan_into_suggested(review["suggested"], plan)

        self.assertIn("workflow_steps", applied)
        self.assertIn("expected_outcome", applied)
        self.assertEqual(suggested["description"], "Model-refined local cash reconciliation workflow.")
        self.assertEqual(suggested["workflow_steps"][0]["title"], "Parse inbound bank file")
        self.assertIn("model_confirms_approval_gate", suggested["validation_rules"])
        self.assertFalse([warning for warning in warnings if "failed" in warning])

    def test_invalid_model_plan_falls_back_to_deterministic_steps(self) -> None:
        candidate = skillgen.default_section_a_skill_candidate()
        review = skillgen.build_section_a_review("review_cand_daily_cash_recon_001", candidate)
        plan = {
            "workflow_steps": [
                {
                    "id": "write_without_approval",
                    "order": 1,
                    "title": "Write without approval",
                    "type": "write_output",
                    "summary": "Unsafe write.",
                    "inputs": [],
                    "outputs": ["reconciled_spreadsheet"],
                    "action_type": "write_xlsx_update",
                }
            ],
            "expected_outcome": {},
            "validation_rules": [],
        }

        suggested, _applied, warnings = skillgen.merge_model_plan_into_suggested(review["suggested"], plan)

        self.assertEqual(suggested["workflow_steps"], review["suggested"]["workflow_steps"])
        self.assertTrue(any("too few" in warning or "approval-before-write" in warning for warning in warnings))

    def test_section_a_review_does_not_mutate_legacy_candidate_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skillgen.bootstrap_demo(root, force=True)
            candidate_path = skillgen.candidate_path_for(root, "cand_daily_cash_recon_001")
            legacy_before = skillgen.read_json(candidate_path)

            review = skillgen.create_review_session(root, "cand_daily_cash_recon_001")
            feedback = skillgen.default_human_feedback(root, review["review_session_id"])
            skillgen.submit_feedback(root, review["review_session_id"], feedback)
            skillgen.install_skill(root, review["review_session_id"])

            legacy_after = skillgen.read_json(candidate_path)
            self.assertEqual(legacy_after, legacy_before)

    def test_matches_previews_executes_and_tracks_skillops(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = skillgen.run_full_skillgen_demo(root, force=True)

            self.assertEqual(result["install"]["status"], "installed")
            self.assertGreaterEqual(len(result["matches"]), 1)
            self.assertIsNotNone(result["preview"])
            self.assertIsNotNone(result["execution"])
            self.assertFalse(result["execution"]["network_used"])
            self.assertFalse(result["execution"]["email_sent"])
            self.assertEqual(result["execution"]["validation"]["status"], "passed")
            self.assertIn("workbook_created", result["execution"]["outputs"])

            paths = skillgen.paths(root)
            self.assertTrue((paths.drafts_dir / "cash_recon_2026_06_15_reply.eml").exists())
            self.assertTrue((paths.workbooks_dir / "cash_recon.skill_updates.jsonl").exists())
            self.assertTrue((paths.workbooks_dir / "generated" / "cash_recon_2026_06_15_reconciled.xlsx").exists())
            self.assertGreaterEqual(result["skillops"]["skills"][0]["runs"], 1)
            self.assertTrue(result["skillops"]["recommendations"])

    def test_candidate_validation_reports_missing_fields(self) -> None:
        validation = skillgen.validate_candidate({"candidate_id": "bad"})
        self.assertEqual(validation["status"], "needs_more_evidence")
        self.assertIn("suggested_inputs", validation["missing_fields"])


if __name__ == "__main__":
    unittest.main()
