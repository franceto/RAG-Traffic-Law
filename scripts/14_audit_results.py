import pandas as pd
import re
import unicodedata
from src.rewrite.vehicle_detector import detect_vehicle_group

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def norm(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def detect_query_vehicle(q):
    return detect_vehicle_group(q)

def detect_source_vehicle(citation, content):
    txt = norm(str(citation) + " " + str(content))

    if re.search(r"(?<!\w)dieu 6(?!\w)", txt):
        return "car"
    if re.search(r"(?<!\w)dieu 7(?!\w)", txt):
        return "motorbike"
    if re.search(r"(?<!\w)dieu 8(?!\w)", txt):
        return "special_vehicle"
    if re.search(r"(?<!\w)dieu 9(?!\w)", txt):
        return "bicycle"
    if re.search(r"(?<!\w)dieu 10(?!\w)", txt):
        return "pedestrian"

    return "unknown"

def is_penalty_question(q):
    qn = norm(q)
    keys = [
        "phat bao nhieu", "muc phat", "muc xu phat", "phat tien",
        "bao nhieu tien", "mat bao nhieu", "may trieu", "may lit",
        "bi phat", "xu phat"
    ]
    return any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", qn) for k in keys)

def is_ambiguous_or_exception(qtype):
    return qtype in ["ambiguous_scenario", "exception_question"]

def as_bool(x):
    return str(x).lower() in ["true", "1", "yes"]

def audit_row(r):
    reasons = []

    if as_bool(r.get("needs_clarification", False)):
        return ""

    q = str(r["question"])
    qn = norm(q)
    qtype = str(r.get("query_type", ""))

    if qtype == "non_violation_question":
        return ""

    citation = str(r.get("top_citation", ""))
    fine = str(r.get("top_fine", ""))
    content = str(r.get("top_content", ""))
    retrieved_count = int(r.get("retrieved_count", 0))

    q_vehicle = detect_query_vehicle(q)
    s_vehicle = detect_source_vehicle(citation, content)

    if retrieved_count == 0:
        reasons.append("NO_RETRIEVAL_TRUE")

    if q_vehicle != "unknown" and s_vehicle != "unknown" and q_vehicle != s_vehicle:
        reasons.append(f"VEHICLE_MISMATCH:{s_vehicle}->{q_vehicle}")

    if qtype not in ["ambiguous_scenario", "exception_question", "rule_question"] and "den xanh" in qn and fine and fine != "nan":
        reasons.append("GREEN_LIGHT_HAS_FINE")

    if qtype not in ["ambiguous_scenario", "exception_question", "rule_question"] and is_penalty_question(q) and q_vehicle == "unknown" and retrieved_count > 0:
        if any(x in norm(citation + " " + content) for x in ["dieu 6", "dieu 7", "dieu 8", "dieu 9", "dieu 10"]):
            reasons.append("MISSING_VEHICLE_BUT_SELECTED_SPECIFIC_VEHICLE")

    if qtype not in ["ambiguous_scenario", "exception_question", "rule_question"] and is_penalty_question(q) and retrieved_count > 0 and (not fine or fine == "nan"):
        if "tich thu" not in norm(content) and "tru diem" not in norm(content):
            reasons.append("PENALTY_QUERY_NO_FINE")

    if qtype == "rule_question" and fine and fine != "nan":
        reasons.append("RULE_QUESTION_RETURNED_FINE")

    if is_ambiguous_or_exception(qtype) and fine and fine != "nan":
        reasons.append("AMBIGUOUS_OR_EXCEPTION_RETURNED_FINE_SOURCE")

    return ";".join(reasons)

df = pd.read_csv("logs/user_100_results.csv", encoding="utf-8-sig")
df["audit_reason"] = df.apply(audit_row, axis=1)

bad = df[df["audit_reason"].fillna("") != ""]
clarify = df[df["needs_clarification"].astype(str).str.lower() == "true"]

print("TOTAL:", len(df))
print("NEEDS_CLARIFICATION:", len(clarify))
print("AUDIT_FAIL:", len(bad))

print("\nREASON COUNTS:")
print(bad["audit_reason"].value_counts())

if len(clarify):
    print("\nCLARIFICATION CASES:")
    for _, r in clarify.iterrows():
        print("\n" + "="*100)
        print("IDX:", r["idx"])
        print("Q:", r["question"])
        print("QUERY_TYPE:", r["query_type"])
        print("ANSWER:", str(r["answer"])[:300])

if len(bad):
    print("\nAUDIT FAIL CASES:")
    for _, r in bad.iterrows():
        print("\n" + "="*100)
        print("IDX:", r["idx"])
        print("Q:", r["question"])
        print("QUERY_TYPE:", r["query_type"])
        print("AUDIT:", r["audit_reason"])
        print("TOP:", r["top_citation"])
        print("FINE:", r["top_fine"])

bad.to_csv("logs/user_100_audit_fail.csv", index=False, encoding="utf-8-sig")
clarify.to_csv("logs/user_100_clarification.csv", index=False, encoding="utf-8-sig")

print("\nSAVED: logs/user_100_audit_fail.csv")
print("SAVED: logs/user_100_clarification.csv")