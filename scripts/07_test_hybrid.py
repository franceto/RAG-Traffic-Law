import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval.hybrid_retriever import retrieve

tests = [
    "Xe ô tô chở người trên buồng lái quá số lượng quy định phạt bao nhiêu",
    "Xe ô tô chuyển làn đường không đúng nơi cho phép phạt bao nhiêu",
    "Xe ô tô không tuân thủ quy định nhường đường tại nơi đường bộ giao nhau phạt bao nhiêu",
    "Nếu va chạm tai nạn giao thông giữa 2 xe máy mà xe máy 1 chạy đi trốn thì phạt bao nhiêu",
    "Xe máy vượt đèn xanh có bị phạt không"
]

for q in tests:
    print("\n" + "=" * 100)
    print("QUESTION:", q)
    out = retrieve(q, top_k=5)

    print("LEGAL QUERIES:")
    for x in out["rewrite"]["legal_queries"]:
        print("-", x)

    print("\nRESULTS:")
    for i, r in enumerate(out["results"], 1):
        print("\nTOP", i)
        print("SCORE:", r["score"])
        print("CITATION:", r["citation"])
        print("FINE:", r["fine_text"])
        print("SOURCE_QUERY:", r["source_query"])
        print("CONTENT:", r["content"][:350].replace("\n", " "))
