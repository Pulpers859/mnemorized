from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import Settings, get_settings  # noqa: E402
from tools.ingest_medical_knowledge import embed_text, require_settings, rpc, serialize_vector  # noqa: E402


DEFAULT_CASES = [
    {"query": "DKA insulin potassium fluids anion gap beta hydroxybutyrate", "expected_source": "tintin-endocrine"},
    {"query": "thyroid storm treatment beta blocker propylthiouracil iodine glucocorticoids", "expected_source": "tintin-endocrine"},
    {"query": "adrenal crisis emergency hydrocortisone dextrose saline hyperkalemia", "expected_source": "tintin-endocrine"},
    {"query": "ATLS primary survey airway breathing circulation hemorrhage control", "expected_source": "tintin-trauma"},
    {"query": "blunt abdominal trauma FAST exam spleen laceration exploratory laparotomy", "expected_source": "tintin-trauma"},
    {"query": "penetrating chest wound hemothorax chest tube thoracotomy", "expected_source": "tintin-trauma"},
    {"query": "ACLS cardiac arrest pulseless ventricular tachycardia defibrillation epinephrine", "expected_source": "tintin-resuscitation"},
    {"query": "hemorrhagic shock massive transfusion protocol permissive hypotension", "expected_source": "tintin-resuscitation"},
    {"query": "STEMI acute myocardial infarction troponin PCI thrombolytics", "expected_source": "tintin-cardiovascular"},
    {"query": "atrial fibrillation rate control rhythm control anticoagulation", "expected_source": "tintin-cardiovascular"},
    {"query": "asthma exacerbation albuterol ipratropium magnesium intubation", "expected_source": "tintin-pulm"},
    {"query": "pulmonary embolism d-dimer CT angiography heparin thrombolysis", "expected_source": "tintin-pulm"},
    {"query": "sepsis septic shock lactate broad spectrum antibiotics fluid resuscitation", "expected_source": "tintin-id"},
    {"query": "bacterial meningitis lumbar puncture empiric antibiotics dexamethasone", "expected_source": "tintin-id"},
    {"query": "acute ischemic stroke tPA thrombolysis NIHSS door to needle time", "expected_source": "tintin-neuro"},
    {"query": "status epilepticus benzodiazepine lorazepam phenytoin refractory seizure", "expected_source": "tintin-neuro"},
    {"query": "upper GI bleed melena hematemesis PPI octreotide endoscopy", "expected_source": "tintin-gi"},
    {"query": "acute pancreatitis lipase Ranson criteria NPO IV fluids", "expected_source": "tintin-gi"},
    {"query": "ectopic pregnancy beta hCG transvaginal ultrasound methotrexate ruptured", "expected_source": "tintin-obgyn"},
    {"query": "preeclampsia magnesium sulfate delivery blood pressure proteinuria", "expected_source": "tintin-obgyn"},
    {"query": "hyperkalemia ECG changes calcium gluconate insulin kayexalate dialysis", "expected_source": "tintin-renal-gu"},
    {"query": "testicular torsion acute scrotum doppler salvage detorsion orchiopexy", "expected_source": "tintin-renal-gu"},
    {"query": "pediatric febrile seizure child fever management evaluation", "expected_source": "tintin-peds"},
    {"query": "sickle cell crisis vaso-occlusive pain acute chest syndrome transfusion", "expected_source": "tintin-heme-onc"},
    {"query": "hypothermia rewarming active core frostbite cold exposure", "expected_source": "tintin-environmental-injuries"},
    {"query": "snake bite envenomation antivenom crotalidae wound management", "expected_source": "tintin-environmental-injuries"},
    {"query": "hip fracture dislocation femoral neck reduction splint", "expected_source": "tintin-ortho"},
    {"query": "procedural sedation ketamine propofol fasting guidelines monitoring", "expected_source": "tintin-analgesia-anesthesia"},
    {"query": "laceration repair suture technique wound closure irrigation", "expected_source": "tintin-wound-management"},
    {"query": "rapid sequence intubation RSI cricothyrotomy surgical airway", "expected_source": "tintin-resuscitation-procedures"},
    {"query": "suicidal ideation risk assessment safety plan psychiatric hold", "expected_source": "tintin-psychosocial"},
    {"query": "retinal detachment acute vision loss globe rupture chemical burn eye", "expected_source": "tintin-eent"},
    {"query": "Stevens-Johnson syndrome toxic epidermal necrolysis drug reaction mucocutaneous", "expected_source": "tintin-dermatology"},
]


def load_cases(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return DEFAULT_CASES
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("QA cases file must contain a JSON list.")
    cases: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("query"):
            raise SystemExit("Each QA case must be an object with a query.")
        cases.append({
            "query": str(item["query"]),
            "expected_source": str(item.get("expected_source") or ""),
        })
    return cases


def run_case(
    client: httpx.Client,
    settings: Settings,
    case: dict[str, str],
    *,
    top_k: int,
) -> dict[str, object]:
    embedding = embed_text(client, settings, case["query"])
    rows = rpc(
        client,
        settings,
        "match_medical_knowledge_chunks",
        {
            "p_query_embedding": serialize_vector(embedding),
            "p_query_text": case["query"],
            "p_match_count": top_k,
            "p_min_similarity": 0.0,
        },
    )
    if not isinstance(rows, list):
        raise RuntimeError("match_medical_knowledge_chunks returned a non-list payload.")

    hits = [
        {
            "source_key": row.get("source_key"),
            "source_title": row.get("title"),
            "page_start": row.get("page_start"),
            "page_end": row.get("page_end"),
            "similarity": row.get("similarity"),
            "keyword_rank": row.get("keyword_rank"),
        }
        for row in rows
        if isinstance(row, dict)
    ]
    expected = case.get("expected_source")
    top_source = hits[0]["source_key"] if hits else None
    expected_in_hits = bool(expected and any(hit["source_key"] == expected for hit in hits))
    return {
        "query": case["query"],
        "expected_source": expected or None,
        "top_source": top_source,
        "pass": bool(hits and (not expected or expected_in_hits)),
        "hits": hits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run private medical knowledge retrieval QA.")
    parser.add_argument("--cases", type=Path, default=None, help="Optional JSON list of query cases.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of matches to request per query.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    if args.top_k < 1 or args.top_k > 20:
        raise SystemExit("--top-k must be between 1 and 20.")

    settings = get_settings()
    require_settings(settings)
    cases = load_cases(args.cases)

    results = []
    with httpx.Client() as client:
        for case in cases:
            results.append(run_case(client, settings, case, top_k=args.top_k))

    passed = sum(1 for result in results if result["pass"])
    summary = {
        "passed": passed,
        "total": len(results),
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Retrieval QA: {passed}/{len(results)} passed")
        for result in results:
            status = "PASS" if result["pass"] else "FAIL"
            print(f"\n[{status}] {result['query']}")
            print(f"  expected: {result['expected_source'] or '(none)'}")
            print(f"  top:      {result['top_source'] or '(none)'}")
            for hit in result["hits"]:
                pages = f"p{hit['page_start']}" if hit["page_start"] == hit["page_end"] else f"p{hit['page_start']}-{hit['page_end']}"
                print(
                    "  - "
                    f"{hit['source_key']} {pages} "
                    f"similarity={float(hit['similarity'] or 0):.3f} "
                    f"keyword={float(hit['keyword_rank'] or 0):.3f}"
                )

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
