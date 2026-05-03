import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.pipeline import answer_question

tests = [
    "Nhường đường cho xe cấp cứu mà phải vượt đèn đỏ thì có bị phạt nguội không?",
    "Đèn xanh còn 1 giây tôi mới chớm qua vạch nhưng chưa kịp hết ngã tư đã sang đèn đỏ có bị phạt không?"
]

for q in tests:
    print("\n" + "=" * 100)
    print("QUESTION:", q)

    res = answer_question(q)

    print("QUERY_TYPE:", res["query_type"])
    print("RETRIEVED:", res["retrieved_count"])
    print("REWRITE:", res["rewrite"])
    print("\nANSWER:")
    print(res["answer"])

    print("\nSOURCES:")
    for s in res["sources"]:
        print("-", s.get("citation", ""), "|", s.get("fine_text", ""), "|", s.get("graph_concepts", []))
