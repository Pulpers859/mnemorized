"""Adversarial, synthetic offline ledger tests; no backend/provider imports."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import copy
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.first_pass_evaluation import (
    CAPS, CONSTITUTION, Invalid, Ledger, REPO, RUBRIC, decode_json, digest, parse_audit,
)


def block(scores=(30, 20, 15, 15, 10, 10), gates="none", missing=(), decision="PASS", cap=100):
    return "\n".join((
        f"OVERALL_SCORE: {min(sum(scores), cap)}",
        f"DECISION: {decision}",
        "CATEGORY_SCORES: " + " ".join(f"{k}:{v}" for k, v in zip("ABCDEF", scores)),
        f"RAW_SUM: {sum(scores)}",
        f"GATES_TRIGGERED: {gates}",
        f"ANCHORS_PRESENT: {3 - len(missing)}/3",
        "MISSING_ANCHORS: " + (", ".join(map(str, missing)) or "none"),
        "TOP_ISSUES: none" if not missing else "TOP_ISSUES: required shape absent",
        "REPAIR: none" if not missing else "REPAIR: restore the absent shape",
    ))


class AuditParserTests(unittest.TestCase):
    def test_canonical_perfect(self):
        self.assertEqual(parse_audit(block(), [1, 2, 3])["score"], 100)

    def test_all_gate_caps_and_strict_decisions(self):
        cases = [
            ((20, 20, 15, 15, 10, 10), "G1(1 missing) cap79", (1,), "REPAIR", 79),
            ((10, 20, 15, 15, 10, 10), "G1(2 missing) cap70", (1, 2), "REGENERATE", 70),
            ((0, 20, 15, 15, 10, 10), "G1(3 missing) cap55", (1, 2, 3), "REGENERATE", 55),
            ((30, 20, 15, 9, 10, 10), "G2 cap88", (), "REPAIR", 88),
            ((30, 20, 15, 10, 10, 10), "G3 cap85", (), "REPAIR", 85),
            ((30, 20, 15, 15, 10, 4), "G4 cap80", (), "REPAIR", 80),
            ((30, 20, 15, 15, 0, 10), "G5 cap75", (), "REPAIR", 75),
            ((30, 12, 15, 15, 10, 10), "G6 cap90", (), "PASS_WITH_TEXT_RISK", 90),
        ]
        for scores, gates, missing, decision, cap in cases:
            with self.subTest(gates=gates):
                result = parse_audit(block(scores, gates, missing, decision, cap), [1, 2, 3])
                self.assertEqual(result["score"], cap)
                self.assertNotEqual(result["decision"], "PASS")

    def test_malformed_and_inflated_audits_fail_closed(self):
        good = block()
        bad = [
            "OVERALL_SCORE: 100\nDECISION: PASS", "```\n" + good + "\n```",
            good + "\nDECISION: PASS", good.replace("RAW_SUM: 100", "RAW_SUM: 99"),
            good.replace("A:30", "A:31"), good.replace("A:30", "A:NaN"),
            good.replace("A:30", "A:-1"), good.replace("A:30", "A:30.0"),
            good.replace("100", "Infinity"), good.replace("PASS", "PASS-ish"),
            good.replace("3/3", "3/2"), good.replace("3/3", "2/3"),
            good.replace("MISSING_ANCHORS: none", "MISSING_ANCHORS: 1, 1"),
            good.replace("GATES_TRIGGERED: none", "GATES_TRIGGERED: G7 cap90"),
            good.replace("GATES_TRIGGERED: none", "GATES_TRIGGERED: G5 cap100"),
            good.replace("GATES_TRIGGERED: none", "GATES_TRIGGERED: G5 cap75; G5 cap75"),
            good.replace("GATES_TRIGGERED: none", "GATES_TRIGGERED: G1(0 missing) cap79"),
            block((30, 20, 15, 15, 10, 10), "G6 cap90", (), "PASS", 90),
            block((30, 20, 15, 15, 10, 10), "G5 cap75", (), "REPAIR", 75),
            block((20, 20, 15, 15, 10, 10), "none", (1,), "REPAIR", 79),
            block((10, 20, 15, 15, 10, 10), "G1(2 missing) cap70", (1, 2), "REPAIR", 70),
            block((30, 20, 15, 9, 10, 10), "G2 cap88; G3 cap85", (), "REPAIR", 85),
        ]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(Invalid):
                    parse_audit(text, [1, 2, 3])

    def test_lower_score_and_stricter_decision_are_preserved(self):
        result = parse_audit(block(decision="REGENERATE"), [1, 2, 3])
        self.assertEqual(result["decision"], "REGENERATE")

    def test_multiple_caps_use_lowest(self):
        result = parse_audit(block((20, 12, 15, 15, 0, 10),
                                  "G1(1 missing) cap79; G5 cap75; G6 cap90", (1,), "REPAIR", 75), [1, 2, 3])
        self.assertEqual(result["score"], 72)

    def test_duplicate_json_and_nonfinite_numbers_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(text=text), self.assertRaises(Invalid):
                decode_json(text)

    def test_current_canonical_document_caps(self):
        text = (REPO / RUBRIC).read_text(encoding="utf-8")
        for gate, cap in CAPS.items():
            self.assertRegex(text, rf"\| {gate} \|[^\n]+\| {cap} \|")
        self.assertIn("OVERALL >= 96", text.replace("\u2265", ">="))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.data = self.repo / "Troubleshooting Prompts"
        self.data.mkdir()
        for name in (RUBRIC, CONSTITUTION, "docs/visual-mnemonic-prompt-contract.md",
                     "docs/visual-metaphor-library.txt", "frontend/pages/forge.html",
                     "frontend/scripts/forge-pipeline.js", "backend/app/main.py",
                     "tools/first_pass_evaluation.py", "tools/visual_qa_pack.py"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic source " + name, encoding="utf-8")
        self.cohort = {
            "before_any_generation": True, "generator": "image-engine",
            "auditors": ["reviewer-one", "reviewer-two"], "prior_topic_prompts": [],
            "novelty_review": "Synthetic fixture history checked",
            "topics": [{"id": name, "prompt": f"Full synthetic evaluation topic {name}",
                        "expected_anchor_count": 3,
                        "novel": True, "full_topic": True, "novelty_basis": "Not in fixture history"}
                       for name in ("a", "b", "c")],
        }
        self.ledger = Ledger(self.data / "trial.sqlite3", repo=self.repo)
        self.frozen = self.ledger.freeze(self.write_json("cohort.json", self.cohort))

    def write(self, name, data):
        path = self.data / name
        path.write_bytes(data)
        return path

    def write_json(self, name, data):
        return self.write(name, json.dumps(data).encode("utf-8"))

    def registration(self, topic="a", status="PASS"):
        bundle = {"_format": "mnemorized-forge-bundle-v1",
                  "topic": next(t["prompt"] for t in self.cohort["topics"] if t["id"] == topic),
                  "story": {"voLines": [{"n": n, "visual": f"Synthetic shape {n}"} for n in (1, 2, 3)]},
                  "image_prompts": {"prompt2": "Synthetic full-scene exported prompt"}}
        bundle["story"]["required_concepts"] = ["Synthetic coverage"]
        source = {"source_key": "fixture", "page_start": 1}
        bundle["quality_gate_data"] = {"verdict": "ready_for_review", "evidence_status": "matched",
                                       "evidence": [source], "missing_from_generation": [], "ungrounded_concepts": []}
        story_sha = digest(json.dumps({"topic": bundle["topic"], "story": bundle["story"]},
                                     ensure_ascii=False, separators=(",", ":")).encode())
        bundle["visual_preflight"] = {
            "version": "visual-preflight-v1", "status": "ready" if status == "PASS" else "blocked",
            "repair_count": 0, "input_story_sha256": story_sha, "story_sha256": story_sha,
            "prompt_sha256": digest(bundle["image_prompts"]["prompt2"].encode()), "clinical_text_preserved": True,
            "attempts": [{"round": 0, "story_sha256": story_sha, "review": {
                "clinical_status": "supported", "clinical_findings": [],
                "anchors": [{"n": n, "status": "ready", "risks": [], "source_refs": [source],
                             "relationship_quote": f"Synthetic shape {n}", "why": "Synthetic relation"} for n in (1, 2, 3)],
                "scene": {"status": "ready", "issues": []}}}]}
        bundle_path = self.write_json(topic + "-bundle.json", bundle)
        prompt_path = self.write(topic + "-prompt.txt", bundle["image_prompts"]["prompt2"].encode())
        preflight = {"status": status, "reason": "Synthetic preflight result", "full_scene": True,
                     "before_render": True, "bundle_sha256": digest(bundle_path.read_bytes()),
                     "prompt_sha256": digest(prompt_path.read_bytes()),
                     "topic_sha256": digest(bundle["topic"].encode()),
                     "pipeline_sha256": self.frozen["pipeline_sha256"]}
        return {"bundle": bundle_path, "prompt": prompt_path,
                "preflight": self.write_json(topic + "-preflight.json", preflight)}

    def first(self, topic="a"):
        self.ledger.record("register", topic, **self.registration(topic))
        self.image = self.write(topic + "-first.png", b"synthetic image bytes")
        return self.ledger.record("first-image", topic, image=self.image, first_render=True)

    def v2_bundle(self, clinical=True, visual_rounds=0, field="narration"):
        args = self.registration()
        bundle = json.loads(args["bundle"].read_text())
        story = bundle["story"]
        story["opening"] = "Synthetic continuous room"
        story["review_script"] = "Original synthetic review"
        for anchor in story["voLines"]:
            anchor.update(anchor=f"Synthetic fact {anchor['n']}", narration="Original synthetic statement",
                          hook="Synthetic association")

        def sha(value):
            return digest(json.dumps({"topic": bundle["topic"], "story": value}, ensure_ascii=False,
                                     separators=(",", ":")).encode())

        report = bundle["visual_preflight"]
        report.update(version="visual-preflight-v2", original_story_sha256=sha(story),
                      clinical_repair_count=int(clinical), clinical_attempts=[], repair_count=visual_rounds,
                      visual_repair_requests=visual_rounds, repair_failures=[])
        source = {"source_key": "fixture", "page_start": 1}
        if clinical:
            n = None if field == "review_script" else 1
            owner = story if n is None else story["voLines"][0]
            before = owner[field]
            owner[field] = "Corrected synthetic statement"
            report["clinical_attempts"] = [{
                "before_sha256": report["original_story_sha256"], "after_sha256": sha(story),
                "review": {"clinical_status": "needs_repair", "anchors": [], "scene": None,
                           "clinical_findings": [{"n": n, "field": field, "issue": "Synthetic factual correction",
                                                  "source_refs": [source]}]},
                "repairs": [{"anchor": n, "field": field, "before": before, "after": owner[field]}]}]
        report["input_story_sha256"] = sha(story)
        template = deepcopy(report["attempts"][0]["review"])
        report["attempts"] = []
        for index in range(visual_rounds + 1):
            review = deepcopy(template)
            for row, anchor in zip(review["anchors"], story["voLines"]):
                row["relationship_quote"] = anchor["visual"]
            attempt = {"round": index, "story_sha256": sha(story), "review": review,
                       "signals": {"errors": [], "risks": []}}
            report["attempts"].append(attempt)
            if index < visual_rounds:
                review["anchors"][0].update(status="repair", risks=["Synthetic relationship needs clarification"])
                before = story["voLines"][0]["visual"]
                after = f"Revised synthetic shape {index}"
                attempt["repairs"] = [{"n": 1, "before": before, "after": after}]
                story["voLines"][0]["visual"] = after
        report["story_sha256"] = sha(story)
        return bundle

    def register_v2(self, bundle):
        return self.ledger.record("register", "a", before_render=True,
                                  bundle=self.write_json("v2-bundle.json", bundle),
                                  prompt=self.write("v2-prompt.txt", bundle["image_prompts"]["prompt2"].encode()))

    def test_v2_without_clinical_repair_and_with_two_visual_repairs(self):
        result = self.register_v2(self.v2_bundle(clinical=False, visual_rounds=2))
        row = result["topics"][0]
        self.assertEqual(row["preflight_version"], "visual-preflight-v2")
        self.assertEqual(row["clinical_repair_count"], 0)
        self.assertEqual(row["preflight_repair_count"], 2)

    def test_v2_clinical_then_two_visual_repairs_still_requires_both_pixel_audits(self):
        self.register_v2(self.v2_bundle(visual_rounds=2))
        self.image = self.write("first.png", b"first actual image")
        self.ledger.record("first-image", "a", image=self.image, first_render=True)
        self.assertEqual(self.audit()["end_to_end"]["passed"], 0)
        result = self.audit("reviewer-two")
        self.assertEqual(result["topics"][0]["clinical_repair_count"], 1)
        self.assertEqual(result["end_to_end"], {"passed": 1, "denominator": 3, "rate": 1 / 3})

    def test_v2_all_three_permitted_clinical_field_types(self):
        from tools.first_pass_evaluation import exported_preflight
        for field in ("anchor", "narration", "review_script"):
            with self.subTest(field=field):
                bundle = self.v2_bundle(field=field)
                self.assertEqual(exported_preflight(bundle, bundle["image_prompts"]["prompt2"]), ("PASS", 0))

    def test_v2_clinical_history_rejects_weak_overrides(self):
        mutations = [
            lambda r: r.update(clinical_repair_count=True),
            lambda r: r.update(clinical_repair_count=2),
            lambda r: r.update(clinical_attempts=[]),
            lambda r: r.update(original_story_sha256="0" * 64),
            lambda r: r.update(input_story_sha256="0" * 64),
            lambda r: r["clinical_attempts"][0].update(before_sha256="0" * 64),
            lambda r: r["clinical_attempts"][0].update(after_sha256="0" * 64),
            lambda r: r["clinical_attempts"][0]["review"].update(clinical_status="source_gap"),
            lambda r: r["clinical_attempts"][0]["review"].update(clinical_status="supported"),
            lambda r: r["clinical_attempts"][0]["review"].update(clinical_findings=[]),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0].update(issue=""),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0].update(source_refs=[]),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0]["source_refs"][0].update(source_key="absent-source"),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0]["source_refs"][0].update(page_start=True),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0].update(n=99),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0].update(n=True),
            lambda r: r["clinical_attempts"][0]["review"]["clinical_findings"][0].update(n=None),
            lambda r: r["clinical_attempts"][0].update(repairs=[]),
            lambda r: r["clinical_attempts"][0]["repairs"][0].update(anchor=True),
            lambda r: r["clinical_attempts"][0]["repairs"][0].update(anchor=2),
            lambda r: r["clinical_attempts"][0]["repairs"][0].update(before="falsified original statement"),
            lambda r: r["clinical_attempts"][0]["repairs"][0].update(after="falsified corrected statement"),
            lambda r: r["clinical_attempts"][0]["repairs"][0].update(extra="hidden field"),
            lambda r: r["clinical_attempts"][0]["repairs"].append(deepcopy(r["clinical_attempts"][0]["repairs"][0])),
            lambda r: r["attempts"][0]["review"].update(clinical_status="needs_repair"),
            lambda r: r["attempts"][0]["review"].update(anchors=[]),
            lambda r: r["attempts"][0]["review"].update(scene=None),
            lambda r: r.update(version="visual-preflight-v1"),
        ]
        for index, mutate in enumerate(mutations):
            bundle = self.v2_bundle()
            mutate(bundle["visual_preflight"])
            with self.subTest(index=index), self.assertRaises(Invalid):
                self.register_v2(bundle)
        self.assertEqual(self.ledger.report()["event_count"], 1)

    def test_v2_cannot_patch_visual_hook_or_coverage_contract(self):
        for field in ("visual", "hook", "required_concepts", "opening"):
            bundle = self.v2_bundle()
            attempt = bundle["visual_preflight"]["clinical_attempts"][0]
            attempt["review"]["clinical_findings"][0]["field"] = field
            attempt["repairs"][0]["field"] = field
            with self.subTest(field=field), self.assertRaises(Invalid):
                self.register_v2(bundle)

    def test_v2_unrecorded_forbidden_changes_fail_reconstructed_original_hash(self):
        for field in ("hook", "required_concepts", "opening", "visual"):
            bundle = self.v2_bundle()
            story = bundle["story"]
            if field == "required_concepts":
                story[field] = ["Changed coverage"]
            elif field == "opening":
                story[field] = "Changed room architecture"
            else:
                story["voLines"][0][field] = "Changed synthetic description"
            changed_hash = digest(json.dumps({"topic": bundle["topic"], "story": story}, ensure_ascii=False,
                                             separators=(",", ":")).encode())
            report = bundle["visual_preflight"]
            report.update(story_sha256=changed_hash, input_story_sha256=changed_hash)
            report["attempts"][0]["story_sha256"] = changed_hash
            report["attempts"][0]["review"]["anchors"][0]["relationship_quote"] = story["voLines"][0]["visual"]
            report["clinical_attempts"][0]["after_sha256"] = changed_hash
            with self.subTest(field=field), self.assertRaisesRegex(Invalid, "unselected fields"):
                self.register_v2(bundle)

    def test_v2_no_clinical_repair_requires_original_to_equal_input(self):
        bundle = self.v2_bundle(clinical=False)
        bundle["visual_preflight"]["original_story_sha256"] = "0" * 64
        with self.assertRaisesRegex(Invalid, "Unrecorded clinical repair"):
            self.register_v2(bundle)

    def test_v2_rejected_patch_consumes_request_but_not_applied_round(self):
        bundle = self.v2_bundle(visual_rounds=1)
        bundle["visual_preflight"].update(visual_repair_requests=2,
                                         repair_failures=[{"request": 1, "error": "Rejected invalid format"}])
        result = self.register_v2(bundle)
        row = result["topics"][0]
        self.assertEqual(row["preflight_repair_count"], 1)
        self.assertEqual(row["visual_repair_requests"], 2)
        self.assertEqual(row["repair_failure_count"], 1)

    def test_v2_request_budget_rejects_missing_unaccounted_and_overbudget_records(self):
        mutations = [
            lambda r: r.pop("visual_repair_requests"),
            lambda r: r.pop("repair_failures"),
            lambda r: r.update(visual_repair_requests=True),
            lambda r: r.update(visual_repair_requests=3),
            lambda r: r.update(visual_repair_requests=0),
            lambda r: r.update(visual_repair_requests=2),
            lambda r: r.update(repair_failures=[{"request": 1, "error": "Rejected"}]),
            lambda r: r.update(visual_repair_requests=2, repair_failures=[{"request": 2, "error": "Rejected"}]),
            lambda r: r.update(visual_repair_requests=2, repair_failures=[{"request": 0, "error": "Rejected"}]),
            lambda r: r.update(visual_repair_requests=2, repair_failures=[{"request": True, "error": "Rejected"}]),
            lambda r: r.update(visual_repair_requests=2, repair_failures=[{"request": 1, "error": ""}]),
            lambda r: r.update(visual_repair_requests=2, repair_failures=[{"request": 1, "error": "Rejected"}] * 2),
            lambda r: r.update(visual_repair_requests=2, repair_failures=[{"request": 1, "error": "Rejected", "ignored": True}]),
        ]
        for index, mutate in enumerate(mutations):
            bundle = self.v2_bundle(visual_rounds=1)
            mutate(bundle["visual_preflight"])
            with self.subTest(index=index), self.assertRaises(Invalid):
                self.register_v2(bundle)

    def test_v2_deterministic_blocking_signals_are_valid_repair_targets(self):
        bundle = self.v2_bundle(visual_rounds=1)
        first = bundle["visual_preflight"]["attempts"][0]
        first["review"]["anchors"][0].update(status="ready", risks=[])
        first["signals"]["risks"] = [{"n": 1, "message": "Synthetic format constraint", "blocking": True}]
        self.assertEqual(self.register_v2(bundle)["topics"][0]["preflight_status"], "PASS")

    def test_v2_final_blocking_signals_or_errors_cannot_be_overridden_by_ready_review(self):
        for signals in ({"errors": ["Invalid structure"], "risks": []},
                        {"errors": [], "risks": [{"n": 1, "message": "Invalid visual", "blocking": True}]},
                        {"errors": [], "risks": [{"n": 1, "message": "Invalid visual", "blocking": "true"}]},
                        {"errors": [], "risks": [{"n": True, "message": "Unknown anchor"}]}):
            bundle = self.v2_bundle()
            bundle["visual_preflight"]["attempts"][-1]["signals"] = signals
            with self.subTest(signals=signals), self.assertRaises(Invalid):
                self.register_v2(bundle)

    def test_v2_two_failed_requests_remain_blocked_without_applied_repairs(self):
        bundle = self.v2_bundle(clinical=False)
        bundle["visual_preflight"].update(status="blocked", visual_repair_requests=2,
                                         repair_failures=[{"request": 1, "error": "Rejected format"},
                                                          {"request": 2, "error": "Rejected format again"}])
        row = self.register_v2(bundle)["topics"][0]
        self.assertEqual(row["status"], "blocked")
        self.assertEqual(row["preflight_repair_count"], 0)
        self.assertEqual(row["repair_failure_count"], 2)
        self.assertFalse(row["end_to_end_pass"])
        with self.assertRaises(Invalid):
            self.ledger.record("first-image", "a", image=self.write("first.png", b"image"), first_render=True)

    def test_v2_visual_history_cannot_hide_late_clinical_changes_or_partial_rereview(self):
        mutations = [
            lambda r: r["attempts"][0].pop("repairs"),
            lambda r: r["attempts"][0]["repairs"][0].update(field="narration"),
            lambda r: r["attempts"][0]["repairs"][0].update(before="different original visual"),
            lambda r: r["attempts"][0]["repairs"][0].update(after="different repaired visual"),
            lambda r: r["attempts"][0]["review"].update(anchors=[]),
            lambda r: r["attempts"][0]["review"].update(clinical_status="source_gap"),
            lambda r: r["attempts"][0]["review"]["anchors"][0].update(status="ready", risks=[]),
            lambda r: r["attempts"][0]["review"]["anchors"][0].update(source_refs=[]),
            lambda r: r["attempts"][-1].update(repairs=[{"n": 1, "before": "x", "after": "y"}]),
        ]
        for index, mutate in enumerate(mutations):
            bundle = self.v2_bundle(visual_rounds=2)
            mutate(bundle["visual_preflight"])
            with self.subTest(index=index), self.assertRaises(Invalid):
                self.register_v2(bundle)

    def test_blocked_baseline_stays_zero_of_three_and_byte_identical(self):
        for topic in ("a", "b", "c"):
            self.ledger.record("blocked", topic, reason="Original pipeline failed before render")
        before = self.ledger.path.read_bytes()
        head = self.ledger.report()["head_sha256"]
        with self.assertRaises(Invalid):
            self.register_v2(self.v2_bundle())
        result = self.ledger.report()
        self.assertEqual(result["end_to_end"], {"passed": 0, "denominator": 3, "rate": 0.0})
        self.assertEqual(result["first_render"], {"passed": 0, "denominator": 0, "rate": None})
        self.assertEqual(result["head_sha256"], head)
        self.assertEqual(before, self.ledger.path.read_bytes())
        with closing(self.ledger.connect(readonly=True)) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("INSERT INTO events VALUES (999, '{}', '', '')")

    def envelope(self, reviewer="reviewer-one", audit_block=None, missing=()):
        return {"auditor": reviewer, "image_sha256": digest(self.image.read_bytes()),
                "rubric_sha256": self.frozen["sources"][RUBRIC],
                "constitution_sha256": self.frozen["sources"][CONSTITUTION],
                "viewed_image": True, "independent": True, "consulted_other_audit": False,
                "canonical_audit": audit_block or block(),
                "anchor_evidence": [{"anchor": n, "status": "absent" if n in missing else "present",
                                     "location": "left foreground", "observation": "Synthetic visible shape"}
                                    for n in (1, 2, 3)]}

    def audit(self, reviewer="reviewer-one", envelope=None):
        return self.ledger.record("audit", "a", auditor=reviewer,
                                  audit=self.write_json(reviewer + ".json", envelope or self.envelope(reviewer)))

    def test_all_frozen_topics_stay_in_denominator(self):
        self.first()
        self.audit()
        self.audit("reviewer-two")
        self.ledger.record("blocked", "b", reason="Synthetic upstream gate blocked")
        result = self.ledger.report()
        self.assertEqual(result["first_render"], {"passed": 1, "denominator": 1, "rate": 1.0})
        self.assertEqual(result["end_to_end"]["denominator"], 3)
        self.assertEqual(result["end_to_end"]["passed"], 1)
        self.assertEqual([x["status"] for x in result["topics"]], ["pass", "blocked", "missing_registration"])

    def test_no_images_has_null_render_rate_not_vacuous_pass(self):
        result = self.ledger.report()
        self.assertIsNone(result["first_render"]["rate"])
        self.assertEqual(result["end_to_end"]["rate"], 0)

    def test_freeze_cannot_be_replaced(self):
        with self.assertRaises(FileExistsError):
            self.ledger.freeze(self.write_json("cohort.json", self.cohort))

    def test_cohort_rejects_nonprospective_duplicate_old_or_nonfull_topics(self):
        mutations = [
            lambda c: c.update(before_any_generation=False),
            lambda c: c.update(topics=[]),
            lambda c: c["topics"][0].update(full_topic=False),
            lambda c: c["topics"][0].update(novel=False),
            lambda c: c["topics"][1].update(prompt="  FULL SYNTHETIC evaluation topic a  "),
            lambda c: c["topics"][1].update(id="a"),
            lambda c: c.update(prior_topic_prompts=[c["topics"][0]["prompt"].upper()]),
            lambda c: c.update(auditors=["REVIEWER-ONE", " reviewer-one "]),
            lambda c: c.update(generator="reviewer-one"),
        ]
        for index, mutate in enumerate(mutations):
            candidate = copy.deepcopy(self.cohort)
            mutate(candidate)
            with self.subTest(index=index), self.assertRaises(Invalid):
                Ledger(self.data / f"bad-{index}.sqlite3", self.repo).freeze(self.write_json("bad.json", candidate))

    def test_rejects_unknown_topic_and_pre_registration_images(self):
        image = self.write("image.png", b"image")
        for topic in ("a", "new-topic"):
            with self.subTest(topic=topic), self.assertRaises(Invalid):
                self.ledger.record("first-image", topic, image=image, first_render=True)

    def test_registration_is_exact_and_single_use(self):
        registration = self.registration()
        self.write("a-prompt.txt", b"focused subset or repaired prompt")
        with self.assertRaises(Invalid):
            self.ledger.record("register", "a", **registration)
        self.ledger.record("register", "a", **self.registration())
        with self.assertRaises(Invalid):
            self.ledger.record("register", "a", **self.registration())

    def test_preflight_binds_each_artifact_and_pipeline(self):
        for key in ("bundle_sha256", "prompt_sha256", "topic_sha256", "pipeline_sha256", "full_scene", "before_render"):
            args = self.registration()
            preflight = json.loads(args["preflight"].read_text())
            preflight[key] = False
            args["preflight"] = self.write_json("wrong-preflight.json", preflight)
            with self.subTest(key=key), self.assertRaises(Invalid):
                self.ledger.record("register", "a", **args)

    def test_direct_export_registration_without_extra_receipt(self):
        args = self.registration()
        args.pop("preflight")
        with self.assertRaises(Invalid):
            self.ledger.record("register", "a", **args)
        result = self.ledger.record("register", "a", before_render=True, **args)
        self.assertEqual(result["topics"][0]["preflight_status"], "PASS")

    def test_structured_preflight_failures_do_not_register(self):
        mutations = [
            lambda b: b.pop("quality_gate_data"),
            lambda b: b["quality_gate_data"].update(verdict="needs_review"),
            lambda b: b["quality_gate_data"].update(evidence=[]),
            lambda b: b["quality_gate_data"].pop("ungrounded_concepts"),
            lambda b: b["visual_preflight"].update(version="unknown"),
            lambda b: b["visual_preflight"].update(status="reviewing"),
            lambda b: b["visual_preflight"].update(story_sha256="0" * 64),
            lambda b: b["visual_preflight"].update(prompt_sha256="0" * 64),
            lambda b: b["visual_preflight"].update(input_story_sha256="0" * 64),
            lambda b: b["visual_preflight"].update(clinical_text_preserved=False),
            lambda b: b["visual_preflight"].update(repair_count=True),
            lambda b: b["visual_preflight"].update(attempts=[]),
            lambda b: b["visual_preflight"]["attempts"][0]["review"].update(clinical_status="source_gap"),
            lambda b: b["visual_preflight"]["attempts"][0]["review"].update(anchors=[]),
            lambda b: b["visual_preflight"]["attempts"][0]["review"]["anchors"][0].update(source_refs=[]),
            lambda b: b["visual_preflight"]["attempts"][0]["review"]["anchors"][0].update(relationship_quote="not in visual"),
            lambda b: b["visual_preflight"]["attempts"][0]["review"].update(scene={"status": "repair", "issues": []}),
            lambda b: b.update(generated_images={"final": "data:image/png;base64,existing"}),
            lambda b: b["story"]["voLines"].pop(),
        ]
        for index, mutate in enumerate(mutations):
            args = self.registration()
            args.pop("preflight")
            bundle = json.loads(args["bundle"].read_text())
            mutate(bundle)
            args["bundle"] = self.write_json("changed-bundle.json", bundle)
            with self.subTest(index=index), self.assertRaises(Invalid):
                self.ledger.record("register", "a", before_render=True, **args)
        self.assertEqual(self.ledger.report()["event_count"], 1)

    def test_fingerprint_excludes_evaluation_docs_tests_but_tracks_new_forge_script(self):
        fingerprint = self.ledger.sources()
        for name in ("docs/first-pass-evaluation.md", "tests/test_first_pass_evaluation.py",
                     "tools/first_pass_evaluation.py"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("evaluation-only edit")
        self.assertEqual(self.ledger.sources(), fingerprint)
        (self.repo / "frontend/scripts/forge-visual-preflight.js").write_text("new production source")
        self.assertNotEqual(self.ledger.sources(), fingerprint)

    def test_pipeline_drift_including_new_source_blocks_registration(self):
        (self.repo / "backend/app/new_module.py").write_text("new source")
        with self.assertRaisesRegex(Invalid, "Pipeline changed"):
            self.ledger.record("register", "a", **self.registration())

    def test_constitution_drift_blocks_first_image(self):
        self.ledger.record("register", "a", **self.registration())
        (self.repo / CONSTITUTION).write_text("changed constitution")
        with self.assertRaisesRegex(Invalid, "Pipeline changed"):
            self.ledger.record("first-image", "a", image=self.write("image.png", b"image"), first_render=True)

    def test_blocked_preflight_or_topic_cannot_be_rescued(self):
        self.ledger.record("register", "a", **self.registration(status="BLOCKED"))
        with self.assertRaises(Invalid):
            self.ledger.record("first-image", "a", image=self.write("image.png", b"image"), first_render=True)
        self.ledger.record("blocked", "b", reason="Failed before export")
        with self.assertRaises(Invalid):
            self.ledger.record("register", "b", **self.registration("b"))
        self.assertEqual(self.ledger.report()["end_to_end"]["denominator"], 3)

    def test_first_image_is_immutable_even_after_input_mutates(self):
        self.first()
        original = digest(self.image.read_bytes())
        self.image.write_bytes(b"replacement image")
        with self.assertRaises(Invalid):
            self.ledger.record("first-image", "a", image=self.image, first_render=True)
        self.assertEqual(self.ledger.report()["topics"][0]["first_image_sha256"], original)

    def test_concurrent_first_image_writers_only_one_wins(self):
        self.ledger.record("register", "a", **self.registration())
        image = self.write("image.png", b"image")

        def record(_):
            try:
                self.ledger.record("first-image", "a", image=image, first_render=True)
                return True
            except Invalid:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(record, range(2))), 1)

    def test_missing_second_audit_cannot_pass(self):
        self.first()
        result = self.audit()
        self.assertEqual(result["topics"][0]["status"], "missing_audit")
        self.assertEqual(result["end_to_end"]["passed"], 0)

    def test_strictest_audit_governs_without_averaging(self):
        self.first()
        self.audit()
        bad = block((20, 20, 15, 15, 10, 10), "G1(1 missing) cap79", (1,), "REPAIR", 79)
        result = self.audit("reviewer-two", self.envelope("reviewer-two", bad, (1,)))
        self.assertEqual(result["topics"][0]["strictest_score"], 79)
        self.assertEqual(result["topics"][0]["strictest_decision"], "REPAIR")
        self.assertEqual(result["first_render"]["passed"], 0)

    def test_repair_image_never_replaces_failed_first(self):
        self.first()
        bad = block((30, 20, 15, 15, 10, 10), decision="REGENERATE")
        self.audit(envelope=self.envelope(audit_block=bad))
        self.audit("reviewer-two")
        original = self.ledger.report()["topics"][0]["first_image_sha256"]
        result = self.ledger.record("attempt", "a", attempt_kind="repaired", reason="Later repair",
                                    image=self.write("repair.png", b"better image"),
                                    prompt=self.write("repair.txt", b"changed prompt"))
        self.assertEqual(result["topics"][0]["first_image_sha256"], original)
        self.assertEqual(result["first_render"]["passed"], 0)
        self.assertEqual(result["topics"][0]["attempts"], 1)
        with self.assertRaises(Invalid):
            self.audit()

    def test_failed_attempt_separates_render_quality_from_end_to_end(self):
        self.ledger.record("register", "a", **self.registration())
        self.ledger.record("attempt", "a", attempt_kind="render_failed", reason="No image returned")
        self.image = self.write("first.png", b"first actual image")
        self.ledger.record("first-image", "a", image=self.image, first_render=True)
        self.audit()
        result = self.audit("reviewer-two")
        self.assertEqual(result["first_render"]["passed"], 1)
        self.assertEqual(result["end_to_end"]["passed"], 0)

    def test_later_failure_does_not_rewrite_primary_outcome(self):
        self.first()
        self.audit()
        self.audit("reviewer-two")
        result = self.ledger.record("attempt", "a", attempt_kind="render_failed", reason="Unrelated later repair failed")
        self.assertEqual(result["end_to_end"]["passed"], 1)

    def test_malformed_audit_retained_and_not_replaceable(self):
        self.first()
        path = self.write("malformed.json", b'{"canonical_audit":"PASS","canonical_audit":"PASS"}')
        result = self.ledger.record("audit", "a", auditor="reviewer-one", audit=path)
        self.assertEqual(result["topics"][0]["status"], "invalid_audit")
        with self.assertRaises(Invalid):
            self.audit()
        self.audit("reviewer-two")
        self.assertEqual(self.ledger.report()["first_render"]["passed"], 0)

    def test_wrong_image_rubric_identity_and_unexamined_evidence_never_pass(self):
        mutations = [
            lambda e: e.update(image_sha256="0" * 64),
            lambda e: e.update(rubric_sha256="0" * 64),
            lambda e: e.update(constitution_sha256="0" * 64),
            lambda e: e.update(auditor="reviewer-two"),
            lambda e: e.update(viewed_image=False),
            lambda e: e.update(independent="true"),
            lambda e: e.update(consulted_other_audit=True),
            lambda e: e.update(anchor_evidence=[]),
            lambda e: e["anchor_evidence"][0].update(status="absent"),
            lambda e: e["anchor_evidence"][0].update(location=""),
            lambda e: e["anchor_evidence"][0].update(anchor=True),
            lambda e: e["anchor_evidence"][0].update(anchor=2),
        ]
        self.first()
        from tools.first_pass_evaluation import validate_audit
        with closing(self.ledger.connect()) as db:
            registration = self.ledger.read(db)[1]["payload"]
        for index, mutate in enumerate(mutations):
            envelope = self.envelope()
            mutate(envelope)
            if index == 3:
                result = self.audit(envelope=envelope)
                self.assertEqual(result["topics"][0]["status"], "invalid_audit")
                continue
            with self.subTest(index=index), self.assertRaises(Invalid):
                validate_audit(envelope, self.frozen, registration, digest(self.image.read_bytes()))

    def test_paths_cannot_escape_run_root(self):
        outside = self.repo / "outside.json"
        outside.write_text("{}")
        for path in (outside, self.data / ".." / "outside.json"):
            with self.subTest(path=path), self.assertRaises(Invalid):
                self.ledger.artifact(path)
        with self.assertRaises(Invalid):
            Ledger(outside, self.repo)

    def test_symlink_escape_rejected_when_supported(self):
        outside = self.repo / "outside"
        outside.mkdir()
        link = self.data / "escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable on this platform")
        with self.assertRaises(Invalid):
            Ledger(link / "ledger.sqlite3", self.repo)

    def test_sql_update_delete_prohibited_and_raw_tampering_detected(self):
        with closing(self.ledger.connect()) as db, db:
            for statement in ("DELETE FROM events", "UPDATE events SET body='{}'"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                    db.execute(statement)
            db.execute("DROP TRIGGER no_update")
            db.execute("UPDATE events SET body='{}'")
        with self.assertRaisesRegex(Invalid, "hash mismatch"):
            self.ledger.report()


if __name__ == "__main__":
    unittest.main()
