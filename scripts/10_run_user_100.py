import os
os.environ["ENABLE_LLM_REWRITE"] = "0"

import sys
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.pipeline import answer_question

RAW_PATH = ROOT / "tests" / "user_100_raw.txt"
OUT_PATH = ROOT / "logs" / "user_100_results.csv"

def load_questions():
    text = RAW_PATH.read_text(encoding="utf-8-sig")
    lines = [x.strip() for x in text.splitlines()]
    return [x for x in lines if x and len(x) >= 10]

def clean(s):
    return " ".join(str(s or "").split())

def is_money_question(q):
    q = q.lower()
    keys = [
        "bao nhiêu", "mấy triệu", "mấy lít", "mất bao nhiêu",
        "mức phạt", "phạt tiền", "bao nhiêu tiền"
    ]
    return any(k in q for k in keys)

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

def top_content(res):
    sources = res.get("sources", [])
    if not sources:
        return ""
    return clean(sources[0].get("content", ""))

def suspect_reason(q, res):
    reasons = []

    count = res.get("retrieved_count", 0)
    answer = clean(res.get("answer", ""))
    citation = top_citation(res)
    fine = top_fine(res)
    content = top_content(res)
    query_type = res.get("query_type", "")
    needs_clarification = res.get("needs_clarification", False)

    if needs_clarification:
        return ""

    if count == 0 and query_type != "non_violation_question":
        reasons.append("NO_RETRIEVAL_TRUE")

    if count > 0 and not citation:
        reasons.append("NO_CITATION_TOP1")

    strict_fine_types = ["penalty_single_hop", "general_question"]

    if query_type in strict_fine_types and is_money_question(q) and count > 0 and not fine:
        if "tịch thu" not in content.lower() and "trừ điểm" not in content.lower():
            reasons.append("NO_FINE_TOP1_FOR_MONEY_QUERY")

    if "chưa tìm thấy căn cứ" in answer.lower() and query_type not in ["exception_question", "ambiguous_scenario", "non_violation_question"]:
        reasons.append("NO_ANSWER")

    return ";".join(reasons)

def run():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions()
    rows = []

    print("TOTAL QUESTIONS:", len(questions))
    print("ENABLE_LLM_REWRITE:", os.environ.get("ENABLE_LLM_REWRITE"))

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q}")

        res = answer_question(q)
        sources = res.get("sources", [])
        top = sources[0] if sources else {}

        rows.append({
            "idx": i,
            "question": q,
            "query_type": res.get("query_type", ""),
            "vehicle_group": res.get("vehicle_group", ""),
            "needs_clarification": res.get("needs_clarification", False),
            "clarification_fields": "|".join(res.get("clarification_fields", [])),
            "answer": clean(res.get("answer", "")),
            "retrieved_count": res.get("retrieved_count", 0),
            "top_citation": clean(top.get("citation", "")),
            "top_fine": clean(top.get("fine_text", "")),
            "top_content": clean(top.get("content", ""))[:700],
            "legal_queries": " || ".join(res.get("rewrite", {}).get("legal_queries", [])),
            "suspect_reason": suspect_reason(q, res)
        })

    with OUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    needs_clarification = sum(1 for r in rows if str(r["needs_clarification"]).lower() == "true")
    no_retrieval_true = sum(
        1 for r in rows
        if int(r["retrieved_count"]) == 0
        and str(r["needs_clarification"]).lower() != "true"
        and r["query_type"] != "non_violation_question"
    )
    suspect = sum(1 for r in rows if r["suspect_reason"])
    answered = len(rows) - needs_clarification - no_retrieval_true

    print("\nSUMMARY")
    print("TOTAL:", len(rows))
    print("ANSWERED:", answered)
    print("NEEDS_CLARIFICATION:", needs_clarification)
    print("NO_RETRIEVAL_TRUE:", no_retrieval_true)
    print("SUSPECT:", suspect)
    print("CSV:", OUT_PATH)

    print("\nCLARIFICATION CASES")
    for r in rows:
        if str(r["needs_clarification"]).lower() == "true":
            print("\n" + "=" * 100)
            print("IDX:", r["idx"])
            print("Q:", r["question"])
            print("QUERY_TYPE:", r["query_type"])
            print("ANSWER:", r["answer"])

    print("\nSUSPECT CASES")
    for r in rows:
        if r["suspect_reason"]:
            print("\n" + "=" * 100)
            print("IDX:", r["idx"])
            print("Q:", r["question"])
            print("QUERY_TYPE:", r["query_type"])
            print("REASON:", r["suspect_reason"])
            print("TOP:", r["top_citation"])
            print("FINE:", r["top_fine"])

if __name__ == "__main__":
    run()
