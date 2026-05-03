import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval.bm25_search import search_bm25

tests = [
    "Xe ô tô chở người trên buồng lái quá số lượng quy định phạt bao nhiêu",
    "Xe ô tô chuyển làn đường không đúng nơi cho phép phạt bao nhiêu",
    "Xe ô tô không tuân thủ quy định nhường đường tại nơi đường bộ giao nhau phạt bao nhiêu",
    "Xe ô tô sử dụng còi từ 22 giờ đến 5 giờ trong khu đông dân cư phạt bao nhiêu",
]

for q in tests:
    print("\n" + "=" * 100)
    print("QUESTION:", q)

    for i, r in enumerate(search_bm25(q, top_k=4), 1):
        print("\nTOP", i)
        print("SCORE:", r["score"])
        print("CITATION:", r["citation"])
        print("FINE:", r["fine_text"])
        print("CONTENT:", r["content"][:350].replace("\n", " "))
