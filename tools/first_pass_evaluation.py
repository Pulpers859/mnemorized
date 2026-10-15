#!/usr/bin/env python3
"""Offline, append-only first-pass evaluation ledger. No generation or network I/O."""

from __future__ import annotations

import argparse
import base64
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import unicodedata


REPO = Path(__file__).resolve().parents[1]
RUBRIC = "docs/image-scoring-rubric.md"
CONSTITUTION = "docs/gemini-constitution.txt"
WEIGHTS = dict(zip("ABCDEF", (30, 20, 15, 15, 10, 10)))
CAPS = {"G2": 88, "G3": 85, "G4": 80, "G5": 75, "G6": 90}
RANK = {"PASS": 0, "PASS_WITH_TEXT_RISK": 1, "REPAIR": 2, "REGENERATE": 3}
FIELDS = ("OVERALL_SCORE", "DECISION", "CATEGORY_SCORES", "RAW_SUM",
          "GATES_TRIGGERED", "ANCHORS_PRESENT", "MISSING_ANCHORS", "TOP_ISSUES", "REPAIR")


class Invalid(ValueError):
    """A ledger operation or audit failed closed."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def decode_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise Invalid(f"Non-finite JSON number: {value}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)


def normalized(value):
    require(isinstance(value, str) and value.strip(), "Expected nonempty text")
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def integer(text):
    require(isinstance(text, str) and re.fullmatch(r"\d{1,3}", text), "Expected integer")
    return int(text)


def parse_audit(text, anchor_ids):
    """Parse the canonical nine-line block, without score-only fallback."""
    require(isinstance(text, str), "Audit block must be text")
    lines = text.strip().splitlines()
    require(len(lines) == len(FIELDS), "Expected exactly nine canonical audit lines")
    fields = {}
    for name, line in zip(FIELDS, lines):
        key, separator, value = line.partition(":")
        require(separator and key == name and value.strip(), f"Expected {name}")
        fields[key] = value.strip()
    match = re.fullmatch(r"A:(\d+) B:(\d+) C:(\d+) D:(\d+) E:(\d+) F:(\d+)",
                         fields["CATEGORY_SCORES"])
    require(match, "Malformed category scores")
    scores = dict(zip(WEIGHTS, map(int, match.groups())))
    require(all(0 <= scores[k] <= cap for k, cap in WEIGHTS.items()), "Category out of range")
    raw = integer(fields["RAW_SUM"])
    overall = integer(fields["OVERALL_SCORE"])
    require(raw == sum(scores.values()), "RAW_SUM disagrees with category arithmetic")
    present = re.fullmatch(r"(\d+)/(\d+)", fields["ANCHORS_PRESENT"])
    require(present, "Malformed anchor count")
    count, total = map(int, present.groups())
    require(total == len(anchor_ids) and 0 <= count <= total, "Wrong anchor denominator")
    missing_text = fields["MISSING_ANCHORS"]
    require(missing_text == "none" or re.fullmatch(r"\d+(?:,\s*\d+)*", missing_text),
            "Malformed missing anchor list")
    missing = [] if missing_text == "none" else [int(x) for x in missing_text.split(",")]
    require(len(set(missing)) == len(missing) and set(missing) <= set(anchor_ids),
            "Duplicate or unknown missing anchors")
    require(len(missing) == total - count, "Anchor counts contradict missing list")
    gates = {}
    if fields["GATES_TRIGGERED"] != "none":
        for item in fields["GATES_TRIGGERED"].split(";"):
            gate = re.fullmatch(r"(G[1-6])(?:\((\d+) missing\))? cap(\d+)", item.strip())
            require(gate, "Malformed or unknown gate")
            key, number, cap = gate.groups()
            require(key not in gates, "Duplicate gate")
            if key == "G1":
                require(number is not None and int(number) == len(missing) > 0, "G1 count mismatch")
                expected = 79 if len(missing) == 1 else 70 if len(missing) == 2 else 55
            else:
                require(number is None, "Only G1 takes a missing count")
                expected = CAPS[key]
            require(int(cap) == expected, "Incorrect canonical gate cap")
            gates[key] = expected
    require(bool(missing) == ("G1" in gates), "Missing anchors require G1")
    require(scores["A"] <= max(0, 30 - 10 * len(missing)), "Missing anchor deduction omitted")
    # Gate-implied minimum deductions cannot be erased by an inflated category score.
    for gate, category, deduction in (("G2", "D", 6), ("G3", "D", 5),
                                      ("G4", "F", 6), ("G5", "E", 10), ("G6", "B", 8)):
        if gate in gates:
            require(scores[category] <= WEIGHTS[category] - deduction, "Gate deduction omitted")
    if "G2" in gates and "G3" in gates:
        require(scores["D"] <= 4, "Combined text deductions omitted")
    require(overall == min([raw, *gates.values()]), "OVERALL_SCORE disagrees with caps/arithmetic")
    if overall < 70 or len(missing) >= 2:
        decision = "REGENERATE"
    elif overall >= 96 and not set(gates) & {"G1", "G2", "G5"}:
        decision = "PASS"
    elif overall >= 90 and not set(gates) & {"G1", "G5"} and set(gates) & {"G2", "G3", "G6"}:
        decision = "PASS_WITH_TEXT_RISK"
    else:
        decision = "REPAIR"
    reported = fields["DECISION"]
    require(reported in RANK, "Unknown decision")
    require(RANK[reported] >= RANK[decision], "Decision is more permissive than arithmetic")
    return {"score": overall, "decision": reported, "gates": sorted(gates), "missing": missing}


def validate_audit(envelope, frozen, registration, image_sha):
    require(isinstance(envelope, dict), "Audit envelope must be an object")
    require(envelope.get("image_sha256") == image_sha, "Audit belongs to another image")
    for field, path in (("rubric_sha256", RUBRIC), ("constitution_sha256", CONSTITUTION)):
        require(envelope.get(field) == frozen["sources"][path], f"Wrong {field}")
    require(envelope.get("viewed_image") is True and envelope.get("independent") is True
            and envelope.get("consulted_other_audit") is False, "Independent pixel review not attested")
    result = parse_audit(envelope.get("canonical_audit"), registration["anchor_ids"])
    evidence = envelope.get("anchor_evidence")
    require(isinstance(evidence, list) and len(evidence) == len(registration["anchor_ids"]),
            "Per-anchor pixel evidence required")
    seen = set()
    for item in evidence:
        require(isinstance(item, dict), "Malformed anchor evidence")
        number = item.get("anchor")
        require(type(number) is int and number in registration["anchor_ids"] and number not in seen,
                "Unknown/duplicate evidence anchor")
        seen.add(number)
        expected = "absent" if number in result["missing"] else "present"
        require(item.get("status") == expected, "Pixel evidence contradicts anchor count")
        normalized(item.get("observation"))
        normalized(item.get("location"))
    return result


def pipeline_hash(sources):
    return digest(canonical({key: value for key, value in sources.items() if not key.startswith("docs/")}))


def story_hash(topic, story):
    # Preserve the exported JS key order for JSON.stringify({topic, story}).
    return digest(json.dumps({"topic": topic, "story": story}, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8"))


def source_refs(refs, evidence):
    require(isinstance(refs, list) and refs, "Missing source references")
    for ref in refs:
        require(isinstance(ref, dict) and isinstance(ref.get("source_key"), str)
                and ref["source_key"].strip() and type(ref.get("page_start")) is int
                and any(isinstance(e, dict) and e.get("source_key") == ref["source_key"]
                        and type(e.get("page_start")) is int and e["page_start"] == ref["page_start"]
                        for e in evidence), "Unknown repair/review source")


def full_review(review, story, evidence):
    """A supported rereview must cover the entire reconstructed story."""
    require(isinstance(review, dict) and review.get("clinical_status") == "supported"
            and review.get("clinical_findings") == [], "Full supported rereview required")
    rows = review.get("anchors")
    require(isinstance(rows, list) and len(rows) == len(story["voLines"]), "Incomplete rereview anchors")
    affected = set()
    for row, anchor in zip(rows, story["voLines"]):
        require(isinstance(row, dict) and type(row.get("n")) is int and row["n"] == anchor["n"]
                and row.get("status") in ("ready", "repair") and isinstance(row.get("risks"), list),
                "Malformed rereview anchor")
        normalized(row.get("why"))
        source_refs(row.get("source_refs"), evidence)
        if row["status"] == "ready":
            quote = row.get("relationship_quote")
            require(not row["risks"] and isinstance(quote, str) and len(quote.split()) >= 3
                    and quote in anchor.get("visual", ""), "Ungrounded ready rereview anchor")
        else:
            require(row["risks"], "Visual repair has no risks")
            for risk in row["risks"]:
                normalized(risk)
            affected.add(anchor["n"])
    scene = review.get("scene")
    require(isinstance(scene, dict) and scene.get("status") in ("ready", "repair")
            and isinstance(scene.get("issues"), list), "Missing complete scene rereview")
    require((scene["status"] == "ready") == (not scene["issues"]), "Contradictory scene rereview")
    ids = {anchor["n"] for anchor in story["voLines"]}
    for issue in scene["issues"]:
        require(isinstance(issue, dict), "Malformed scene issue")
        normalized(issue.get("reason"))
        numbers = issue.get("anchors")
        require(isinstance(numbers, list) and numbers
                and all(type(n) is int and n in ids for n in numbers), "Unknown scene issue anchor")
        affected.update(numbers)
    return affected


def validate_v2_history(bundle, review, evidence):
    """Reverse only permitted edits; each reconstructed boundary must match its hash."""
    topic = bundle["topic"]
    story = deepcopy(bundle["story"])
    attempts = review["attempts"]
    for index in range(len(attempts) - 1, -1, -1):
        attempt = attempts[index]
        require(story_hash(topic, story) == attempt["story_sha256"], "Visual repair story hash mismatch")
        affected = full_review(attempt["review"], story, evidence)
        signals = attempt.get("signals")
        require(isinstance(signals, dict) and signals.get("errors") == []
                and isinstance(signals.get("risks"), list), "Missing or failed structural preflight signals")
        ids = {a["n"] for a in story["voLines"]}
        for risk in signals["risks"]:
            require(isinstance(risk, dict) and type(risk.get("n")) is int and risk["n"] in ids,
                    "Unknown structural risk anchor")
            normalized(risk.get("message"))
            require("blocking" not in risk or type(risk["blocking"]) is bool, "Malformed blocking signal")
            if risk.get("blocking") is True:
                affected.add(risk["n"])
        if index == len(attempts) - 1:
            require(not affected and not attempt.get("repairs"), "Final rereview is not fully ready")
        else:
            require(affected == repaired_ids, "Visual repair targets do not match reviewed issues")
        if index:
            patches = attempts[index - 1].get("repairs")
            require(isinstance(patches, list) and patches, "Missing visual repair history")
            repaired_ids = set()
            anchors = {a["n"]: a for a in story["voLines"]}
            for patch in patches:
                require(isinstance(patch, dict) and set(patch) == {"n", "before", "after"},
                        "Malformed visual-only repair")
                n = patch["n"]
                require(type(n) is int and n in anchors and n not in repaired_ids, "Invalid visual repair anchor")
                repaired_ids.add(n)
                normalized(patch["before"])
                normalized(patch["after"])
                require(anchors[n].get("visual") == patch["after"], "Visual repair after-value mismatch")
                anchors[n]["visual"] = patch["before"]
    require(story_hash(topic, story) == review["input_story_sha256"], "Post-clinical input hash mismatch")
    original = review.get("original_story_sha256")
    require(isinstance(original, str) and re.fullmatch(r"[0-9a-f]{64}", original), "Missing original story hash")
    if review["clinical_repair_count"] == 0:
        require(original == review["input_story_sha256"], "Unrecorded clinical repair")
        return
    attempt = review["clinical_attempts"][0]
    require(isinstance(attempt, dict) and attempt.get("before_sha256") == original
            and attempt.get("after_sha256") == review["input_story_sha256"], "Clinical repair hash boundary mismatch")
    clinical = attempt.get("review")
    require(isinstance(clinical, dict) and clinical.get("clinical_status") == "needs_repair",
            "Only source-supported needs_repair permits a clinical patch")
    findings = clinical.get("clinical_findings")
    require(isinstance(findings, list) and findings, "Missing targeted clinical findings")
    anchors = {a["n"]: a for a in story["voLines"]}
    targets = set()
    for finding in findings:
        require(isinstance(finding, dict), "Malformed clinical finding")
        n, field = finding.get("n"), finding.get("field")
        require("n" in finding and ((n is None and field == "review_script") or
                (type(n) is int and n in anchors and field in ("anchor", "narration"))),
                "Clinical patch targets a forbidden field")
        normalized(finding.get("issue"))
        source_refs(finding.get("source_refs"), evidence)
        targets.add((n, field))
    patches = attempt.get("repairs")
    require(isinstance(patches, list) and len(patches) == len(targets), "Clinical repairs do not cover findings")
    seen = set()
    for patch in patches:
        require(isinstance(patch, dict) and set(patch) == {"anchor", "field", "before", "after"},
                "Malformed clinical repair")
        n, field = patch["anchor"], patch["field"]
        require((n is None or type(n) is int) and isinstance(field, str), "Malformed clinical repair target")
        target = (n, field)
        require(target in targets and target not in seen, "Unselected or duplicate clinical repair")
        seen.add(target)
        normalized(patch["before"])
        normalized(patch["after"])
        owner = story if n is None else anchors[n]
        require(owner.get(field) == patch["after"], "Clinical repair after-value mismatch")
        owner[field] = patch["before"]
    require(story_hash(topic, story) == original, "Clinical patch changed unselected fields or falsified before-values")


def visual_request_budget(review):
    requests, failures, applied = (review.get("visual_repair_requests"), review.get("repair_failures"),
                                   review.get("repair_count"))
    require(type(requests) is int and 0 <= requests <= 2 and type(applied) is int and 0 <= applied <= requests
            and isinstance(failures, list), "Invalid visual repair request budget")
    previous = 0
    for failure in failures:
        require(isinstance(failure, dict) and set(failure) == {"request", "error"}
                and type(failure["request"]) is int and previous < failure["request"] <= requests,
                "Invalid or duplicate failed repair request")
        normalized(failure["error"])
        previous = failure["request"]
    require(applied + len(failures) <= requests, "Failed repairs exceed request budget")
    if review.get("status") == "ready":
        require(applied + len(failures) == requests, "Ready report has an unaccounted repair request")
        require(not failures or previous < requests, "Final failed repair request cannot clear preflight")


def exported_preflight(bundle, prompt):
    """Validate the structured Forge receipt, not the clinical truth of its claims."""
    gate, review = bundle.get("quality_gate_data"), bundle.get("visual_preflight")
    require(isinstance(gate, dict) and isinstance(review, dict), "Structured Forge gate/preflight required")
    version = review.get("version")
    require(version in ("visual-preflight-v1", "visual-preflight-v2"), "Unknown visual preflight version")
    if version == "visual-preflight-v2":
        clinical_count, clinical_attempts = review.get("clinical_repair_count"), review.get("clinical_attempts")
        require(type(clinical_count) is int and clinical_count in (0, 1)
                and isinstance(clinical_attempts, list) and len(clinical_attempts) == clinical_count,
                "Invalid bounded clinical repair history")
        visual_request_budget(review)
    else:
        require(not {"clinical_repair_count", "clinical_attempts", "original_story_sha256",
                     "visual_repair_requests", "repair_failures"} & review.keys(),
                "V2 clinical history cannot be relabeled as v1")
    require(review.get("status") in ("ready", "blocked"), "Preflight incomplete")
    if review["status"] == "blocked":
        return "BLOCKED", review.get("repair_count", 0)
    require(gate.get("verdict") == "ready_for_review" and gate.get("evidence_status") == "matched",
            "Medical evidence did not clear")
    evidence = gate.get("evidence")
    require(isinstance(evidence, list) and evidence, "Missing source evidence")
    for key in ("missing_from_generation", "ungrounded_concepts"):
        require(gate.get(key) == [], f"Missing or uncleared {key}")
    story = bundle["story"]
    require(isinstance(story.get("required_concepts"), list) and story["required_concepts"],
            "Missing independent clinical coverage contract")
    require(review.get("story_sha256") == story_hash(bundle["topic"], story), "Preflight story binding mismatch")
    require(review.get("prompt_sha256") == digest(prompt.encode("utf-8")), "Preflight prompt binding mismatch")
    require(review.get("clinical_text_preserved") is True, "Clinical preservation not attested")
    count, attempts = review.get("repair_count"), review.get("attempts")
    require(type(count) is int and 0 <= count <= 2 and isinstance(attempts, list)
            and len(attempts) == count + 1 and all(isinstance(a, dict) for a in attempts),
            "Invalid bounded preflight attempt history")
    require(review.get("input_story_sha256") == attempts[0].get("story_sha256"), "Input story binding mismatch")
    require(attempts[-1].get("story_sha256") == review["story_sha256"], "Final story binding mismatch")
    for index, attempt in enumerate(attempts):
        require(type(attempt.get("round")) is int and attempt["round"] == index
                and isinstance(attempt.get("story_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", attempt["story_sha256"]),
                "Invalid preflight attempt sequence")
        clinical = attempt.get("review")
        require(isinstance(clinical, dict) and clinical.get("clinical_status") == "supported"
                and clinical.get("clinical_findings") == [], "Uncleared clinical review")
    final = attempts[-1]["review"]
    rows = final.get("anchors")
    require(isinstance(rows, list) and len(rows) == len(story["voLines"]), "Incomplete preflight anchor review")
    for row, anchor in zip(rows, story["voLines"]):
        require(row.get("n") == anchor["n"] and row.get("status") == "ready" and row.get("risks") == [],
                "Anchor preflight not ready")
        quote = row.get("relationship_quote")
        require(isinstance(quote, str) and len(quote.split()) >= 3 and quote in anchor.get("visual", ""),
                "Anchor relationship quote not grounded in VISUAL")
        normalized(row.get("why"))
        refs = row.get("source_refs")
        require(isinstance(refs, list) and refs, "Anchor lacks source references")
        for ref in refs:
            require(ref.get("source_key") and any(isinstance(e, dict) and e.get("source_key") == ref["source_key"]
                    and e.get("page_start") == ref.get("page_start") for e in evidence), "Unknown anchor source")
    require(final.get("scene") == {"status": "ready", "issues": []}, "Scene preflight not ready")
    if version == "visual-preflight-v2":
        validate_v2_history(bundle, review, evidence)
    return "PASS", count


class Ledger:
    def __init__(self, path, repo=REPO):
        self.repo = Path(repo).resolve()
        self.data_root = (self.repo / "Troubleshooting Prompts").resolve()
        require(self.data_root.is_relative_to(self.repo), "Run-data root escapes repository")
        self.path = self.inside(path)

    def inside(self, path):
        result = Path(path).resolve()
        require(result.is_relative_to(self.data_root) and result != self.data_root,
                "All run data must be under Troubleshooting Prompts")
        return result

    def artifact(self, path):
        data = self.inside(path).read_bytes()
        require(data, "Empty artifact")
        return {"sha256": digest(data), "base64": base64.b64encode(data).decode("ascii")}

    @staticmethod
    def unpack(artifact):
        data = base64.b64decode(artifact["base64"], validate=True)
        require(digest(data) == artifact["sha256"], "Artifact hash mismatch")
        return data

    def sources(self):
        paths = {RUBRIC, CONSTITUTION, "frontend/pages/forge.html"}
        for folder, pattern in (("frontend/scripts", "*.js"), ("backend/app", "*.py")):
            paths.update(p.relative_to(self.repo).as_posix() for p in (self.repo / folder).rglob(pattern))
        result = {}
        for name in sorted(paths):
            path = (self.repo / name).resolve()
            require(path.is_relative_to(self.repo), "Source symlink escapes repository")
            result[name] = digest(path.read_bytes())
        return result

    def connect(self, readonly=False):
        require(self.path.is_file(), "Freeze a cohort first")
        if readonly:
            return sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=10)
        return sqlite3.connect(self.path, timeout=10)

    def freeze(self, cohort_path):
        cohort = decode_json(self.unpack(self.artifact(cohort_path)))
        require(isinstance(cohort, dict), "Cohort must be an object")
        normalized(cohort.get("novelty_review"))
        require(cohort.get("before_any_generation") is True, "Prospective freeze not attested")
        reviewers = cohort.get("auditors")
        require(isinstance(reviewers, list) and len(reviewers) == 2, "Freeze exactly two auditors")
        identities = [normalized(x) for x in reviewers]
        generator = normalized(cohort.get("generator"))
        require(len(set(identities + [generator])) == 3, "Auditors must be distinct and external")
        prior = cohort.get("prior_topic_prompts")
        require(isinstance(prior, list), "Supply reviewed prior_topic_prompts (possibly empty)")
        known = {normalized(x) for x in prior}
        topics = cohort.get("topics")
        require(isinstance(topics, list) and topics, "Cannot freeze an empty cohort")
        ids = set()
        for topic in topics:
            require(isinstance(topic, dict), "Malformed topic")
            name = topic.get("id")
            require(isinstance(name, str) and re.fullmatch(r"[a-zA-Z0-9_-]+", name)
                    and name not in ids, "Invalid/duplicate topic id")
            ids.add(name)
            prompt = normalized(topic.get("prompt"))
            require(prompt not in known, "Duplicate or previously used topic prompt")
            known.add(prompt)
            require(topic.get("novel") is True and topic.get("full_topic") is True,
                    "Novel full-topic prompt not attested")
            if "expected_anchor_count" in topic:
                require(type(topic["expected_anchor_count"]) is int and topic["expected_anchor_count"] > 0,
                        "Expected anchor count must be a positive integer")
            normalized(topic.get("novelty_basis"))
        sources = self.sources()
        frozen = {"schema": 1, "cohort": cohort, "sources": sources,
                  "pipeline_sha256": pipeline_hash(sources)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidental replacement of an existing cohort.
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(self.connect()) as db, db:
            db.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, "
                       "previous TEXT NOT NULL, sha256 TEXT NOT NULL)")
            for action in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER no_{action.lower()} BEFORE {action} ON events "
                           "BEGIN SELECT RAISE(ABORT, 'append-only ledger'); END")
            self.append(db, [], "freeze", None, frozen)
        return frozen

    @staticmethod
    def append(db, events, kind, topic, payload):
        event = {"seq": len(events) + 1, "time": datetime.now(timezone.utc).isoformat(),
                 "kind": kind, "topic": topic, "payload": payload}
        previous = events[-1]["sha256"] if events else "0" * 64
        body = canonical(event).decode("utf-8")
        sha = digest(previous.encode("ascii") + body.encode("utf-8"))
        db.execute("INSERT INTO events VALUES (?, ?, ?, ?)", (event["seq"], body, previous, sha))

    def read(self, db):
        events = []
        previous = "0" * 64
        for seq, body, prev, sha in db.execute("SELECT seq, body, previous, sha256 FROM events ORDER BY seq"):
            require(seq == len(events) + 1 and prev == previous, "Broken event chain")
            require(digest(prev.encode("ascii") + body.encode("utf-8")) == sha, "Event hash mismatch")
            event = decode_json(body)
            require(event["seq"] == seq, "Event sequence mismatch")
            for artifact in event["payload"].get("artifacts", {}).values():
                self.unpack(artifact)
            event["sha256"] = sha
            events.append(event)
            previous = sha
        require(events and events[0]["kind"] == "freeze", "Missing frozen cohort")
        frozen = events[0]["payload"]
        require(frozen["schema"] == 1 and pipeline_hash(frozen["sources"]) == frozen["pipeline_sha256"],
                "Invalid pipeline fingerprint")
        return events

    def record(self, kind, topic, **arguments):
        with closing(self.connect()) as db, db:
            # Serialize validation + append, including competing first-image writers.
            db.execute("BEGIN IMMEDIATE")
            events = self.read(db)
            frozen = events[0]["payload"]
            topics = {x["id"]: x for x in frozen["cohort"]["topics"]}
            require(topic in topics, "Topic was not prospectively frozen")
            history = [e for e in events if e["topic"] == topic]
            registrations = [e["payload"] for e in history if e["kind"] == "register"]
            first = [e["payload"] for e in history if e["kind"] == "first-image"]
            blocks = [e for e in history if e["kind"] == "blocked"]
            payload = {"artifacts": {}}
            if kind == "register":
                require(not registrations and not blocks, "Registration/blocked result is already frozen")
                require(self.sources() == frozen["sources"], "Pipeline changed since cohort freeze")
                for key in ("bundle", "prompt"):
                    payload["artifacts"][key] = self.artifact(arguments[key])
                bundle = decode_json(self.unpack(payload["artifacts"]["bundle"]))
                prompt = self.unpack(payload["artifacts"]["prompt"]).decode("utf-8-sig")
                require(isinstance(bundle, dict) and bundle.get("_format") == "mnemorized-forge-bundle-v1",
                        "Expected exported Forge v1 bundle")
                require(bundle.get("topic") == topics[topic]["prompt"], "Bundle topic must equal full frozen prompt")
                require(prompt.strip() and prompt == bundle.get("image_prompts", {}).get("prompt2"),
                        "Prompt must exactly match exported full-scene prompt2")
                anchors = bundle.get("story", {}).get("voLines")
                require(isinstance(anchors, list) and anchors, "Export has no anchors")
                anchor_ids = [a.get("n") for a in anchors if isinstance(a, dict)]
                require(len(anchor_ids) == len(anchors) and all(type(n) is int and n > 0 for n in anchor_ids)
                        and len(set(anchor_ids)) == len(anchor_ids), "Invalid exported anchor ids")
                if "expected_anchor_count" in topics[topic]:
                    require(len(anchor_ids) == topics[topic]["expected_anchor_count"],
                            "Export does not match the prospectively frozen anchor count")
                require(not any((bundle.get("generated_images") or {}).values()), "Bundle already contains a render")
                status, repair_count = exported_preflight(bundle, prompt)
                preflight = {"status": status, "reason": "Structured exported Forge preflight",
                             "bundle_sha256": payload["artifacts"]["bundle"]["sha256"],
                             "prompt_sha256": payload["artifacts"]["prompt"]["sha256"],
                             "topic_sha256": digest(topics[topic]["prompt"].encode("utf-8")),
                             "pipeline_sha256": frozen["pipeline_sha256"], "full_scene": True,
                             "before_render": arguments.get("before_render") is True}
                if arguments.get("preflight"):
                    payload["artifacts"]["preflight"] = self.artifact(arguments["preflight"])
                    preflight = decode_json(self.unpack(payload["artifacts"]["preflight"]))
                require(isinstance(preflight, dict) and preflight.get("status") == status,
                        "Preflight requires PASS or BLOCKED")
                for key in ("bundle", "prompt"):
                    require(preflight.get(key + "_sha256") == payload["artifacts"][key]["sha256"],
                            f"Preflight does not bind {key}")
                require(preflight.get("topic_sha256") == digest(topics[topic]["prompt"].encode("utf-8")),
                        "Preflight does not bind topic")
                require(preflight.get("pipeline_sha256") == frozen["pipeline_sha256"], "Preflight pipeline mismatch")
                require(preflight.get("full_scene") is True and preflight.get("before_render") is True,
                        "Full scene / before-render preflight attestation required")
                normalized(preflight.get("reason"))
                payload.update(anchor_ids=anchor_ids, preflight_status=preflight["status"], repair_count=repair_count,
                               preflight_version=bundle["visual_preflight"]["version"],
                               clinical_repair_count=bundle["visual_preflight"].get("clinical_repair_count", 0),
                               visual_repair_requests=bundle["visual_preflight"].get("visual_repair_requests"),
                               repair_failure_count=len(bundle["visual_preflight"].get("repair_failures", [])))
            elif kind == "first-image":
                require(registrations and not first and not blocks, "Register first; first image cannot be replaced")
                require(registrations[0]["preflight_status"] == "PASS", "Preflight blocked")
                require(self.sources() == frozen["sources"], "Pipeline changed before first image")
                require(arguments.get("first_render") is True, "First actual render attestation required")
                payload["artifacts"]["image"] = self.artifact(arguments["image"])
            elif kind == "audit":
                require(first, "Record first image before auditing")
                reviewer = normalized(arguments["auditor"])
                require(reviewer in [normalized(x) for x in frozen["cohort"]["auditors"]], "Unregistered auditor")
                require(not any(e["kind"] == "audit" and e["payload"]["auditor"] == reviewer for e in history),
                        "Auditor slot cannot be overwritten, even after an invalid audit")
                payload["auditor"] = reviewer
                payload["artifacts"]["audit"] = self.artifact(arguments["audit"])
                # Invalid submissions are retained, consume their slot, and cannot pass.
                try:
                    envelope = decode_json(self.unpack(payload["artifacts"]["audit"]))
                    require(normalized(envelope.get("auditor")) == reviewer, "Auditor identity mismatch")
                    validate_audit(envelope, frozen, registrations[0], first[0]["artifacts"]["image"]["sha256"])
                    payload["validation_error"] = None
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    payload["validation_error"] = str(exc)
            elif kind == "attempt":
                require(registrations, "Register before recording attempts")
                attempt_kind = arguments["attempt_kind"]
                require(attempt_kind in ("render_failed", "repaired", "additional"), "Unknown attempt kind")
                normalized(arguments["reason"])
                payload.update(attempt_kind=attempt_kind, reason=arguments["reason"])
                if attempt_kind != "render_failed":
                    require(first, "First image must be recorded before later images")
                    for key in ("image", "prompt"):
                        require(arguments.get(key), f"Later attempts require {key}")
                        payload["artifacts"][key] = self.artifact(arguments[key])
                else:
                    require(not arguments.get("image"), "A failed render must not hide an image")
            elif kind == "blocked":
                require(not blocks, "Blocked outcome cannot be overwritten")
                normalized(arguments["reason"])
                payload["reason"] = arguments["reason"]
            else:
                raise Invalid("Unknown event kind")
            self.append(db, events, kind, topic, payload)
        return self.report()

    def report(self):
        with closing(self.connect(readonly=True)) as db:
            events = self.read(db)
        frozen = events[0]["payload"]
        rows = []
        for topic in frozen["cohort"]["topics"]:
            history = [e for e in events if e["topic"] == topic["id"]]
            by_kind = {kind: [e["payload"] for e in history if e["kind"] == kind]
                       for kind in ("register", "first-image", "audit", "attempt", "blocked")}
            first = by_kind["first-image"]
            image_sha = first[0]["artifacts"]["image"]["sha256"] if first else None
            audits, errors = [], []
            for audit in by_kind["audit"]:
                try:
                    require(audit["validation_error"] is None, audit["validation_error"])
                    envelope = decode_json(self.unpack(audit["artifacts"]["audit"]))
                    audits.append(validate_audit(envelope, frozen, by_kind["register"][0], image_sha))
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    errors.append(str(exc))
            score = min((a["score"] for a in audits), default=None)
            decision = max((a["decision"] for a in audits), key=RANK.get, default=None)
            passed = len(audits) == 2 and not errors and decision == "PASS" and score >= 96
            blocked = bool(by_kind["blocked"]) or any(r["preflight_status"] != "PASS" for r in by_kind["register"])
            first_seq = next((e["seq"] for e in history if e["kind"] == "first-image"), float("inf"))
            failed_attempts = any(e["kind"] == "attempt" and e["seq"] < first_seq
                                  and e["payload"]["attempt_kind"] == "render_failed" for e in history)
            end_to_end = passed and not blocked and not failed_attempts
            status = ("blocked" if blocked else "missing_registration" if not by_kind["register"] else
                      "missing_image" if not first else "invalid_audit" if errors else
                      "missing_audit" if len(audits) != 2 else "pass" if passed else "fail")
            rows.append({"id": topic["id"], "status": status, "first_image_sha256": image_sha,
                         "strictest_score": score, "strictest_decision": decision,
                         "gates": sorted({g for a in audits for g in a["gates"]}),
                         "valid_audits": len(audits), "audit_errors": errors,
                         "preflight_status": by_kind["register"][0]["preflight_status"] if by_kind["register"] else None,
                         "preflight_repair_count": by_kind["register"][0]["repair_count"] if by_kind["register"] else None,
                         "preflight_version": by_kind["register"][0].get("preflight_version", "visual-preflight-v1") if by_kind["register"] else None,
                         "clinical_repair_count": by_kind["register"][0].get("clinical_repair_count", 0) if by_kind["register"] else None,
                         "visual_repair_requests": by_kind["register"][0].get("visual_repair_requests") if by_kind["register"] else None,
                         "repair_failure_count": by_kind["register"][0].get("repair_failure_count", 0) if by_kind["register"] else None,
                         "failed_render_before_first_image": failed_attempts,
                         "first_render_pass": passed, "end_to_end_pass": end_to_end,
                         "attempts": len(by_kind["attempt"]),
                         "blocked_reasons": [x["reason"] for x in by_kind["blocked"]]})

        def metric(numerator, denominator):
            return {"passed": numerator, "denominator": denominator,
                    "rate": numerator / denominator if denominator else None}

        first_passes = sum(row["first_render_pass"] for row in rows)
        return {"schema": 1, "cohort_denominator": len(rows), "pipeline_sha256": frozen["pipeline_sha256"],
                "rubric_sha256": frozen["sources"][RUBRIC],
                "constitution_sha256": frozen["sources"][CONSTITUTION],
                "event_count": len(events), "head_sha256": events[-1]["sha256"],
                "first_render": metric(first_passes, sum(bool(row["first_image_sha256"]) for row in rows)),
                "first_render_cohort": metric(first_passes, len(rows)),
                "end_to_end": metric(sum(row["end_to_end_pass"] for row in rows), len(rows)),
                "topics": rows,
                "caveat": "Descriptive pilot only, not a reliability claim. Novelty, provenance, pixel inspection "
                          "and reviewer independence are attestations; local storage is not tamper-proof."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--cohort", required=True, type=Path)
    sub.add_parser("report")
    for name in ("register", "first-image", "audit", "attempt", "blocked"):
        command = sub.add_parser(name)
        command.add_argument("--topic", required=True)
        if name == "register":
            for key in ("bundle", "prompt"):
                command.add_argument("--" + key, required=True, type=Path)
            command.add_argument("--preflight", type=Path, help="Optional additional bound preflight receipt")
            command.add_argument("--before-render", action="store_true")
        elif name == "first-image":
            command.add_argument("--image", required=True, type=Path)
            command.add_argument("--first-render", action="store_true", required=True)
        elif name == "audit":
            command.add_argument("--auditor", required=True)
            command.add_argument("--audit", required=True, type=Path)
        elif name == "attempt":
            command.add_argument("--attempt-kind", required=True, choices=("render_failed", "repaired", "additional"))
            command.add_argument("--reason", required=True)
            command.add_argument("--image", type=Path)
            command.add_argument("--prompt", type=Path)
        else:
            command.add_argument("--reason", required=True)
    args = vars(parser.parse_args(argv))
    try:
        ledger = Ledger(args.pop("ledger"))
        command = args.pop("command")
        if command == "freeze":
            ledger.freeze(args["cohort"])
            result = ledger.report()
        elif command == "report":
            result = ledger.report()
        else:
            result = ledger.record(command, args.pop("topic"), **args)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, AttributeError) as exc:
        parser.exit(2, f"Ledger error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
