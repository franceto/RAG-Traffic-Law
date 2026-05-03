import sys
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.pipeline import answer_question

def clean(s):
    return " ".join(str(s or "").split())

def top_citation(res):
    sources = res.get("sources", [])
    if not sources:
        return ""
    return clean(sources[0].get("citation", ""))

def top_fine(res):
    sources = res.get("sources", [])
    if not sources:
        return ""
    return clean(sources[0].get("fine_text", ""))

def run():
    cases_path = ROOT / "tests" / "benchmark_cases.json"
    out_path = ROOT / "logs" / "benchmark_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cases = json.loads(cases_path.read_text(encoding="utf-8-sig"))
    rows = []

    citation_ok = 0
    fine_ok = 0
    retrieval_ok = 0

    for c in cases:
        q = c["question"]
        res = answer_question(q)

        got_citation = top_citation(res)
        got_fine = top_fine(res)
        got_count = res.get("retrieved_count", 0)

        exp_citation = clean(c.get("expected_citation", ""))
        exp_fine = clean(c.get("expected_fine", ""))
        exp_count = c.get("expected_retrieved_count", None)

        c_ok = got_citation == exp_citation
        f_ok = got_fine == exp_fine

        if exp_count is None:
            r_ok = got_count > 0
        else:
            r_ok = got_count == exp_count

        citation_ok += int(c_ok)
        fine_ok += int(f_ok)
        retrieval_ok += int(r_ok)

        rows.append({
            "id": c["id"],
            "question": q,
            "expected_citation": exp_citation,
            "got_citation": got_citation,
            "citation_ok": c_ok,
            "expected_fine": exp_fine,
            "got_fine": got_fine,
            "fine_ok": f_ok,
            "expected_retrieved_count": "" if exp_count is None else exp_count,
            "got_retrieved_count": got_count,
            "retrieval_ok": r_ok,
            "answer": clean(res.get("answer", ""))
        })

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total = len(cases)
    print("SUMMARY")
    print("TOTAL:", total)
    print(f"CITATION: {citation_ok}/{total}")
    print(f"FINE: {fine_ok}/{total}")
    print(f"RETRIEVAL: {retrieval_ok}/{total}")
    print("CSV:", out_path)

    fails = [r for r in rows if not (r["citation_ok"] and r["fine_ok"] and r["retrieval_ok"])]

    if fails:
        print("\nFAILED CASES")
        for r in fails:
            print("\n" + "=" * 100)
            print("ID:", r["id"])
            print("Q:", r["question"])
            print("EXPECTED CITATION:", r["expected_citation"])
            print("GOT CITATION:", r["got_citation"])
            print("EXPECTED FINE:", r["expected_fine"])
            print("GOT FINE:", r["got_fine"])
            print("EXPECTED COUNT:", r["expected_retrieved_count"])
            print("GOT COUNT:", r["got_retrieved_count"])

if __name__ == "__main__":
    run()
