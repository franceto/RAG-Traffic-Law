import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rewrite.query_type_classifier import classify_query_type

tests = [
    "Xe ô tô chuyển làn đường không đúng nơi cho phép phạt bao nhiêu",
    "Nhường đường cho xe cấp cứu mà phải vượt đèn đỏ thì có bị phạt nguội không?",
    "Đèn xanh còn 1 giây tôi mới chớm qua vạch nhưng chưa kịp hết ngã tư đã sang đèn đỏ có bị phạt không?",
    "Giấy phép lái xe tích hợp trên VNeID có giá trị thay thế bằng lái cứng khi bị kiểm tra không?",
    "Cảnh sát giao thông được quyền giữ xe mình trong bao lâu nếu mình vi phạm?"
]

for q in tests:
    print(q)
    print("=>", classify_query_type(q))
    print()
