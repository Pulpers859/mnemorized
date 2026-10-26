"""Materialize explicit offline cue choices; never infer semantic admission.

Run from the repository root with ``python -m tools.chapter_cue_sparse``.
Source pointers and exact unchanged reuse are sparse; semantic changes are not.
Outputs remain in the local packet until independent main-agent integration.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from tools.chapter_cue_prior_matches import chapter_key, find_prior_matches

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"body", "table", "heading", "heading_and_body", "table_and_body",
         "chapter_title", "box_title", "figure_label"}
CHOICE_FIELDS = {"term", "decision", "prior", "cue", "attempted_cue", "cue_scope",
                 "reason", "association_status", "association_comparison",
                 "change_origin", "draft_history", "earlier_holds_remain_open"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2)+"\n", encoding="utf-8")


def context(packet, chapter, root=ROOT):
    root = root.resolve()
    packet = (root / packet).resolve()
    require(packet.is_relative_to(root), "Packet must remain inside root")
    manifest = read(packet / "manifest.json")
    require(chapter in manifest["chapters"], "Chapter absent from manifest")
    require(chapter_key(manifest["prior_before"]) <= chapter_key(chapter), "Future prior cutoff")
    return packet, manifest, root


def materialize_inventory(packet, chapter, root=ROOT):
    packet, manifest, root = context(packet, chapter, root)
    chapter_info = manifest["chapters"][chapter]
    raw_path = packet / f"author/inventory{chapter}.json"
    raw = read(raw_path)
    require(str(raw["chapter_id"]) == chapter, "Wrong inventory chapter")
    require(set(raw) <= {"chapter_id", "terms", "excluded_non_terms", "limits"}, "Unknown inventory field")
    cache, hashes = {}, {}
    for page in chapter_info["regions"]:
        path = packet / f"source/gi-{int(page)}.json"
        cache[int(page)] = read(path)
        hashes[page] = digest(path)

    def locations(at):
        require(isinstance(at, list) and bool(at), "Missing source pointers")
        result = []
        for pair in at:
            require(isinstance(pair, list) and len(pair) == 2 and
                    all(isinstance(x, int) and not isinstance(x, bool) for x in pair), "Invalid source pointer")
            page, index = pair
            require(page in cache and 0 <= index < len(cache[page]["spans"]), "Source pointer out of range")
            span = cache[page]["spans"][index]
            x, y = span["bbox"][:2]
            require(any(a <= x < c and b <= y < d for a, b, c, d in chapter_info["regions"][str(page)]), "Source pointer outside chapter ownership")
            result.append({"page": page, "span_index": index, **span})
        require(len({s["page"] for s in result}) == 1, "A hit must stay on one page")
        require(len(at) == len({tuple(p) for p in at}), "Duplicate span pointer")
        return result

    terms, keywords, seen_terms, seen_hits = [], [], set(), set()
    offset = manifest["source"]["printed_page_offset"]
    for item in raw["terms"]:
        require(set(item) <= {"term", "kind", "hits"}, "Unknown term field; metadata belongs to code")
        name = item["term"]
        require(isinstance(name, str) and name.strip() and name.casefold() not in seen_terms, "Duplicate or blank inventory term")
        require(item["kind"] in KINDS and bool(item["hits"]), "Invalid source kind/hits")
        seen_terms.add(name.casefold())
        evidence = []
        for hit in item["hits"]:
            require(set(hit) <= {"at", "emphasis", "head", "note"}, "Unknown hit field")
            locs = locations(hit["at"])
            page = locs[0]["page"]
            head = hit.get("head", name)
            key = head.casefold(), page
            require(head.strip() and hit["emphasis"].strip() and key not in seen_hits, f"Duplicate/blank keyword mapping: {name}/{head}/{page}")
            seen_hits.add(key)
            keywords.append({"term": head, "entry_term": name, "pdf_page": page,
                             "page": page+offset, "emphasis": hit["emphasis"], "wording_note": hit.get("note", "")})
            evidence.extend(locs)
        terms.append({"term": name, "pdf_page": evidence[0]["page"], "source_match": item["kind"], "source_locations": evidence})
    require(bool(terms), "Empty inventory")
    excluded = []
    for item in raw["excluded_non_terms"]:
        require(set(item) <= {"at", "reason"} and item["reason"].strip(), "Invalid exclusion")
        locs = locations(item["at"])
        excluded.append({"pdf_page": locs[0]["page"], "description": "Native source span(s) " + ", ".join(f"{s['page']}:{s['span_index']}" for s in locs), "reason": item["reason"]})
    pages = sorted(cache)
    source = {**manifest["source"], "pdf_pages": pages,
              "printed_pages": [p+offset for p in pages], "regions": chapter_info["regions"]}
    annotations = sum(1 for p in cache.values() for a in p["annotations"] if a[0] == 8)
    return {"chapter_id": chapter, "title": chapter_info["title"], "source": source,
            "input_sha256": digest(raw_path), "manifest_sha256": digest(packet/"manifest.json"),
            "source_cache_sha256": hashes, "terms": terms,
            "keyword_screen": {"method": "Author-selected lexical heads/native span IDs; source metadata copied by code, independent source/semantic review required.",
                "items": keywords, "excluded_non_terms": excluded,
                "highlight_annotation_check": {"checked": True, "highlight_annotations_found": annotations,
                    "note": "Native annotation arrays checked; flattened highlights remain uncertain."}},
            "limits": raw.get("limits", "Selected lexical screening, not exhaustive vocabulary or clinical coverage.")}


def prepare(packet, chapter, root=ROOT):
    packet, manifest, root = context(packet, chapter, root)
    require(not (packet/f"author/decisions{chapter}.json").exists(), "Preserve decisions before changing their inventory/prior freeze")
    inventory = materialize_inventory(packet, chapter, root)
    query = packet / f"materialized/query{chapter}.json"
    write(query, {"chapter_id": chapter, "entries": [{"term": t["term"], "decision": "hold"} for t in inventory["terms"]]})
    report = find_prior_matches(query, before=manifest["prior_before"], limit=1, root=root)
    report["warning"] = "Query holds are uncurated lookup placeholders, NOT author hold decisions. Exact matches are leads, not admission."
    write(packet/f"prior-compact{chapter}.json", report)
    frozen = {p.relative_to(root).as_posix(): digest(p) for p in (root/"docs").glob("chapter-*-cue-audit.json")
              if chapter_key(read(p)["chapter_id"]) < chapter_key(manifest["prior_before"])}
    freeze_path = packet/"prior-freeze.json"
    if freeze_path.exists():
        require(read(freeze_path) == frozen, "Prior corpus changed during preparation")
    else:
        write(freeze_path, frozen)
    write(packet/f"materialized/inventory{chapter}.json", inventory)
    return inventory


def build(packet, chapter, root=ROOT):
    packet, manifest, root = context(packet, chapter, root)
    inventory = materialize_inventory(packet, chapter, root)
    require(inventory == read(packet/f"materialized/inventory{chapter}.json"), "Inventory/source evidence changed after freeze")
    choices = read(packet/f"author/decisions{chapter}.json")
    require(set(choices) <= {"chapter_id", "inventory_sha256", "reuse", "aliases", "changes", "resolved_holds"}, "Unknown decision field")
    require(isinstance(choices.get("aliases", []), list), "Aliases must be an array")
    require(str(choices["chapter_id"]) == chapter and choices["inventory_sha256"] == inventory["input_sha256"], "Wrong decision inventory freeze")
    frozen = read(packet/"prior-freeze.json")

    def prior(reference, selected=True):
        relative, fragment = reference.split("#", 1)
        require(relative in frozen, "Prior outside frozen corpus")
        path = (root/relative).resolve()
        require(path.parent == root/"docs" and digest(path) == frozen[relative], "Changed/invalid prior file")
        matches = [e for e in read(path)["entries"] if fragment.casefold() in {str(e.get("term", "")).casefold(), str(e.get("id", "")).casefold()}]
        require(len(matches) == 1, "Prior fragment must resolve uniquely")
        record = matches[0]
        if selected:
            require(record.get("decision") in {"retain_candidate", "reuse_candidate"}
                    and record.get("selection_status") not in {"hold", "rejected", "restricted"}
                    and record.get("status") not in {"hold", "rejected", "restricted"}, "Cannot copy unselected/restricted prior")
        return record

    decisions = {}
    for row in choices["reuse"]:
        require(isinstance(row, list) and len(row) == 2, "Reuse is [exact term, exact selected reference]")
        name, reference = row
        record = prior(reference)
        require(name.casefold() == record["term"].casefold(), "Changed term/scope requires explicit semantic choice")
        require(record.get("cue") and record.get("cue_scope"), "Prior lacks inheritable cue/scope")
        require(name not in decisions, "Duplicate decision")
        decisions[name] = {"term": name, "decision": "reuse_candidate", "prior": reference,
            "cue": record["cue"], "cue_scope": record["cue_scope"],
            "reason": "Author explicitly reselected the exact same-term cue and scope without semantic changes.",
            "association_status": "unchanged_repeat", "change_origin": "existing_candidate_recount",
            "association_comparison": f"Same bridge, depiction and encoded scope as {reference}; explicitly reviewed unchanged reuse, not new creative yield."}
    def alias_decision(row):
        # Copy only frozen selected content, never an inferred alias match.
        require(isinstance(row, dict) and set(row) == {"term", "prior", "reason", "association_comparison"},
                "Alias requires explicit term, prior, reason and comparison only")
        name, reference = row["term"], row["prior"]
        require(isinstance(name, str) and name.strip(), "Blank alias decision")
        require(isinstance(reference, str) and reference.startswith("docs/") and "#" in reference,
                "Alias requires frozen canonical prior")
        for field in ("reason", "association_comparison"):
            require(isinstance(row[field], str) and row[field].strip(), f"Missing alias {field}")
        record = prior(reference)
        require(record.get("cue") and isinstance(record.get("cue_scope"), str) and record["cue_scope"].strip(),
                "Alias prior lacks inheritable cue/scope")
        return {**row, "decision": "reuse_candidate", "cue": record["cue"], "cue_scope": record["cue_scope"],
            "association_status": "unchanged_repeat", "change_origin": "existing_candidate_recount"}

    for row in choices.get("aliases", []):
        item = alias_decision(row)
        require(item["term"] not in decisions, "Duplicate alias decision")
        decisions[item["term"]] = item
    for item in choices["changes"]:
        require(not set(item)-CHOICE_FIELDS, "Unknown semantic field/source override")
        name = item["term"]
        require(name not in decisions, "Duplicate decision")
        require(item["decision"] != "reuse_candidate" or str(item.get("prior", "")).startswith("docs/"), "Reuse candidate requires an actual frozen selected prior")
        if str(item.get("prior", "")).startswith("docs/"):
            record = prior(item["prior"], selected=item["decision"] == "reuse_candidate")
            if record.get("decision") in {"retain_candidate", "reuse_candidate"} and item["association_status"] == "unchanged_repeat":
                require(item.get("cue") == record.get("cue"),
                        "Unchanged selected-prior reuse must preserve cue/scope exactly; declare an actual semantic variant otherwise")
                prior_scope = record.get("cue_scope")
                require(prior_scope is None or isinstance(prior_scope, str), "Invalid legacy scope type")
                if prior_scope and prior_scope.strip():
                    require(item.get("cue_scope") == prior_scope, "Unchanged selected-prior reuse must preserve cue/scope exactly")
                else:
                    # Missing legacy scope needs an authored decision, not invented creative yield.
                    item["legacy_scope_supplied"] = True
        decisions[name] = dict(item)
    require(set(decisions) == {t["term"] for t in inventory["terms"]}, "Decisions must explicitly cover every term exactly once")
    local_maps = {chapter: {name.casefold(): item for name, item in decisions.items()}}

    def validate_local(reference, trail):
        prefix, separator, name = reference.partition("#")
        target_chapter = prefix.removeprefix("local:")
        require(separator and name and target_chapter in manifest["chapters"], "Invalid local prior")
        node = target_chapter, name.casefold()
        require(node not in trail, "Circular local prior")
        if target_chapter not in local_maps:
            other = read(packet/f"author/decisions{target_chapter}.json")
            require(isinstance(other.get("aliases", []), list), "Aliases must be an array")
            records = ([{"term": row[0], "decision": "reuse_candidate", "prior": row[1]} for row in other["reuse"]]
                       + [alias_decision(row) for row in other.get("aliases", [])] + other["changes"])
            require(len(records) == len({e["term"].casefold() for e in records}), "Duplicate local source decisions")
            local_maps[target_chapter] = {e["term"].casefold(): e for e in records}
        target = local_maps[target_chapter].get(name.casefold())
        require(target and target.get("decision") in {"retain_candidate", "reuse_candidate"}, "Local prior must name an actual selected choice")
        following = target.get("prior", "")
        if following.startswith("local:"):
            validate_local(following, trail | {node})

    entries = []
    for term in inventory["terms"]:
        item = decisions[term["term"]]
        if item.get("prior", "").startswith("local:"):
            validate_local(item["prior"], {(chapter, term["term"].casefold())})
        status, association = item["decision"], item["association_status"]
        require(status in {"retain_candidate", "reuse_candidate", "hold"}, "Invalid decision")
        require(association in {"new_association", "meaningful_variant", "unchanged_repeat", "hold"} and (status == "hold") == (association == "hold"), "Contradictory association/selection")
        for field in ("cue_scope", "reason", "association_comparison"):
            require(isinstance(item.get(field), str) and item[field].strip(), f"Missing semantic {field}")
        require(bool(item.get("attempted_cue") if status == "hold" else item.get("cue")), "Missing actual cue/attempt")
        origin = item.setdefault("change_origin", {"unchanged_repeat": "existing_candidate_recount", "meaningful_variant": "new_revision"}.get(association, "new_proposal"))
        require(origin in {"new_proposal", "new_revision", "reconsidered_attempt", "existing_candidate_recount"}, "Invalid origin")
        if association == "unchanged_repeat":
            require(origin in {"existing_candidate_recount", "reconsidered_attempt"}, "Repeat is not new invention")
        if association == "meaningful_variant":
            require(origin in {"new_revision", "reconsidered_attempt"}, "Variant needs revision provenance")
        item.setdefault("prior", "offline_unresolved_attempt" if status == "hold" else "new_offline_proposal")
        if status == "hold":
            item["cue"] = None
        entries.append({"term": term["term"], "pdf_page": term["pdf_page"],
            "page": term["pdf_page"]+manifest["source"]["printed_page_offset"], "source_match": term["source_match"],
            "source_refs": [list(pair) for pair in dict.fromkeys((s["page"], s["span_index"]) for s in term["source_locations"])],
            **item, "tested": False, "selection_status": "hold" if status == "hold" else "candidate"})
    dc = Counter(e["decision"] for e in entries)
    for resolution in choices.get("resolved_holds", []):
        require(resolution["term"] in decisions and decisions[resolution["term"]]["decision"] != "hold"
                and resolution["resolution"].strip(), "Invalid local hold resolution")
    bank = {"schema_version": 1, "chapter_id": chapter, "title": inventory["title"],
        "review_date": manifest["review_date"], "keyword_screen_date": manifest["review_date"],
        "source": inventory["source"], "production_admitted": False,
        "scope": "Offline lexical cues only; no clinical facts, instructions, recall or rendering claims.",
        "counts": {"selected_terms": len(entries), "new_candidates": dc["retain_candidate"], "reused_candidates": dc["reuse_candidate"], "holds": dc["hold"]},
        "association_counts": dict(Counter(e["association_status"] for e in entries)),
        "change_origin_counts": dict(Counter(e["change_origin"] for e in entries)),
        "entries": entries, "keyword_screen": inventory["keyword_screen"], "resolved_holds": choices.get("resolved_holds", []),
        "review_status": "Author materialization; independent review pending", "evidence": {"render": [], "recall": [], "clinical_claim_validation": []},
        "spend": {"anthropic_calls": 0, "other_paid_provider_calls": 0, "image_renders": 0},
        "local_packet": packet.relative_to(root).as_posix(), "limits": inventory["limits"],
        "sparse_provenance": {"inventory_sha256": inventory["input_sha256"], "decisions_sha256": digest(packet/f"author/decisions{chapter}.json"),
                              "tool_sha256": digest(Path(__file__)), "manifest_sha256": inventory["manifest_sha256"],
                              "prior_freeze_sha256": digest(packet/"prior-freeze.json"),
                              "source_cache_sha256": inventory["source_cache_sha256"], "exact_unchanged_reuse_rows": len(choices["reuse"]), "explicit_semantic_rows": len(choices["changes"])}}
    if "aliases" in choices:
        bank["sparse_provenance"]["explicit_alias_adoption_rows"] = len(choices["aliases"])
    return bank


def render(bank):
    cell = lambda x: str(x or "No selected cue").replace("|", "/").replace("\n", " ")
    lines = [f"# Chapter {bank['chapter_id']}: {bank['title']}", "", bank["review_status"], "",
             "All untested/nonproduction. Counts are association occurrences, not unique library additions.", "",
             "| Term | Cue Or Attempt | Encoded Scope | Association |", "| --- | --- | --- | --- |"]
    lines.extend("| "+" | ".join(cell(v) for v in (e["term"], e.get("cue") or e.get("attempted_cue"), e["cue_scope"], e["association_status"]))+" |" for e in bank["entries"])
    return "\n".join(lines)+"\n"


def integrate_reviewed(packet, root=ROOT):
    """Main-only integration of a hash-bound independent review; no Git/APIs."""
    root = root.resolve()
    packet = (root/packet).resolve()
    require(packet.is_relative_to(root), "Packet must remain inside root")
    approval = read(packet/"main-approval.json")
    manifest = read(packet/"manifest.json")
    require(set(approval["chapters"]) == set(manifest["chapters"]), "Approve the complete declared packet")
    require(approval["source_and_conceptual_review"] is True and approval["scope"].strip(), "Independent main review required")
    report = (root/approval["report"]).resolve()
    require(report.parent == root/"docs" and report.is_file(), "Durable review report required")
    chapters = sorted(approval["chapters"], key=chapter_key)
    ledger_path = root/"docs/tintinalli-chapter-cue-ledger.json"
    ledger = read(ledger_path)
    require(ledger["next_chapter"]["chapter_id"] == chapters[0], "Do not skip unfinished chapters")
    require(chapter_key(approval["next_chapter"]["chapter_id"]) > chapter_key(chapters[-1]), "Invalid next chapter")
    outputs, rows = {}, []
    existing = {r["chapter_id"] for r in ledger["subsequent_chapter_reviews"]}
    for chapter in chapters:
        path = packet/f"materialized/chapter-{chapter}-cue-audit.json"
        require(digest(path) == approval["chapters"][chapter], "Unreviewed materialized bank")
        bank = read(path)
        require(bank == build(packet, chapter, root), "Unreviewed source/author delta")
        target = root/f"docs/chapter-{chapter}-cue-audit.json"
        md = target.with_suffix(".md")
        require(chapter not in existing and not target.exists() and not md.exists(), "Do not overwrite an integrated chapter")
        bank["review_status"] = "Independent main source/cue review and repair delta closed; untested/nonproduction"
        bank["main_integration_review"] = {"date": approval["date"], "source_and_conceptual_review": True,
            "scope": approval["scope"], "counts": bank["counts"], "keyword_items": len(bank["keyword_screen"]["items"]),
            "materialized_sha256": approval["chapters"][chapter], "report": approval["report"]}
        outputs[target] = json.dumps(bank, ensure_ascii=True, indent=2)+"\n"
        outputs[md] = render(bank)+f"\n[Independent findings and limits]({report.name}).\n"
        rows.append({"chapter_id": chapter, "title": bank["title"], "record": target.relative_to(root).as_posix(),
            "report": md.relative_to(root).as_posix(), **bank["counts"], "independent_source_and_conceptual_review": True,
            "exhaustive_vocabulary_review": False, "empirical_validation": False,
            "keyword_items_screened": len(bank["keyword_screen"]["items"]), "association_occurrences": bank["association_counts"],
            "change_origin_occurrences": bank["change_origin_counts"], "counts_not_unique_library_growth": True})
    ledger["subsequent_chapter_reviews"].extend(rows)
    ledger["next_chapter"] = approval["next_chapter"]
    outputs[ledger_path] = json.dumps(ledger, ensure_ascii=False, indent=2)+"\n"
    index = root/"docs/tintinalli-chapter-cues.md"
    lines = ["", f"## Chapters {chapters[0]}-{chapters[-1]}: Sparse Authoring Trial", "",
             f"[Independent findings, examples and efficiency limits]({report.name}).", "",
             "| Chapter | Topic | Terms | Different Bridges | Variants | Repeats | Held | Keyword Mappings |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        c = row["association_occurrences"]
        lines.append(f"| {row['chapter_id']} | [{row['title']}]({Path(row['report']).name}) | {row['selected_terms']} | {c.get('new_association',0)} | {c.get('meaningful_variant',0)} | {c.get('unchanged_repeat',0)} | {c.get('hold',0)} | {row['keyword_items_screened']} |")
    lines.extend(["", "Association occurrences, not unique growth or empirical validation. Earlier holds preserved separately; all candidates untested/nonproduction. No paid provider calls or AI image renders.", ""])
    outputs[index] = index.read_text(encoding="utf-8")+"\n".join(lines)
    # Validate every chapter and all metadata before changing the integration checkout.
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--chapter", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--build", action="store_true")
    args = parser.parse_args()
    packet, _, _ = context(args.packet, args.chapter)
    result = prepare(packet, args.chapter) if args.prepare else build(packet, args.chapter)
    if args.build:
        target = packet/f"materialized/chapter-{args.chapter}-cue-audit.json"
        write(target, result)
        target.with_suffix(".md").write_text(render(result), encoding="utf-8")
    print(json.dumps({"chapter": args.chapter, "terms": len(result.get("terms", result.get("entries", []))), "mode": "prepare" if args.prepare else "build"}))
