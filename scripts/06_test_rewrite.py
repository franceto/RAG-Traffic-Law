import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rewrite.query_rewriter import rewrite_query

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
    res = rewrite_query(q)

    print("VEHICLE:", res["vehicle_group"])

    print("\nLEGAL QUERIES:")
    for x in res["legal_queries"]:
        print("-", x)

    print("\nTOP MAPPING:")
    for c in res["mapping_candidates"][:3]:
        print("-", c["citation"], "|", c["legal_phrase"][:120])
