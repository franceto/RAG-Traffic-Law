import os
os.environ["ENABLE_LLM_REWRITE"] = "0"

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.pipeline import answer_question

tests = [
    "Mức xử phạt đối với hành vi vượt đèn đỏ theo Nghị định 168 là bao nhiêu?",
    "Mức phạt tiền đối với lỗi vi phạm nồng độ cồn vượt quá 0.4 miligam/1 lít khí thở là bao nhiêu?",
    "Không chấp hành hiệu lệnh của cảnh sát giao thông bị phạt bao nhiêu?",
    "Dừng xe, đỗ xe không đúng nơi quy định bị xử phạt như thế nào?",
    "Mức phạt đối với lỗi không giữ khoảng cách an toàn gây va chạm?"
]

for q in tests:
    print("\n" + "=" * 100)
    print("QUESTION:", q)

    res = answer_question(q)

    print("QUERY_TYPE:", res.get("query_type"))
    print("NEEDS_CLARIFICATION:", res.get("needs_clarification"))
    print("RETRIEVED:", res.get("retrieved_count"))
    print("\nANSWER:")
    print(res.get("answer"))

    print("\nSOURCES:")
    for s in res.get("sources", [])[:10]:
        print("-", s.get("multi_vehicle_name", ""), "|", s.get("citation", ""), "|", s.get("fine_text", ""))
