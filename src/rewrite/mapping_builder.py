import json
import re
import unicodedata
from collections import Counter
from src.config.settings import settings

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def tokens(text):
    stop = {
        "va", "hoac", "la", "thi", "bi", "co", "duoc",
        "phat", "tien", "tu", "den", "dong",
        "nguoi", "dieu", "khien", "xe",
        "thuc", "hien", "mot", "trong", "cac",
        "hanh", "vi", "pham", "sau", "day",
        "quy", "dinh", "doi", "voi"
    }
    return [t for t in normalize(text).split() if len(t) >= 2 and t not in stop]

def extract_violation_phrase(row):
    content = row.get("content", "")
    point = row.get("point", "")

    if point:
        m = re.search(rf"{re.escape(point)}\)\s*(.+)", content, flags=re.S)
        phrase = m.group(1).strip() if m else content.strip()
    else:
        phrase = content.strip()

    phrase = re.sub(r"\s+", " ", phrase)
    phrase = phrase.strip(" ;.")
    return phrase

def keywords_of(text, top_n=14):
    cnt = Counter(tokens(text))
    return [w for w, _ in cnt.most_common(top_n)]

def condition_tags(text):
    n = normalize(text)
    tags = []

    rules = {
        "duong_cao_toc": ["cao toc"],
        "tai_nan_giao_thong": ["tai nan", "va cham"],
        "bo_chay_hien_truong": ["khong dung lai", "khong giu nguyen hien truong", "khong tro giup", "bo chay"],
        "noi_giao_nhau": ["giao nhau"],
        "den_tin_hieu": ["den tin hieu", "den do", "den vang", "den xanh"],
        "toc_do": ["toc do", "km h"],
        "dung_do": ["dung xe", "do xe", "dau xe"],
        "chuyen_lan": ["chuyen lan"],
        "nhuong_duong": ["nhuong duong"],
        "coi_den": ["coi", "den chieu xa"],
        "giay_to": ["giay phep", "dang ky xe", "chung nhan"],
        "mu_bao_hiem": ["mu bao hiem"],
        "nong_do_con": ["nong do con"]
    }

    for tag, kws in rules.items():
        if any(k in n for k in kws):
            tags.append(tag)

    return tags

def is_penalty_entry(row):
    if row.get("topic") != "traffic_violation_penalty":
        return False

    if not row.get("fine_text"):
        return False

    if not row.get("vehicle_group"):
        return False

    phrase = extract_violation_phrase(row)
    if len(phrase) < 15:
        return False

    return True

def build_mapping():
    with settings.chunk_file.open("r", encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]

    entries = []

    for row in rows:
        if not is_penalty_entry(row):
            continue

        phrase = extract_violation_phrase(row)

        entries.append({
            "id": f'{row.get("doc_id", "")}|{row.get("article", "")}|{row.get("clause", "")}|{row.get("point", "")}',
            "citation": row.get("citation", ""),
            "doc_id": row.get("doc_id", ""),
            "article": row.get("article", ""),
            "clause": row.get("clause", ""),
            "point": row.get("point", ""),
            "vehicle_group": row.get("vehicle_group", ""),
            "fine_text": " ".join(str(row.get("fine_text", "")).split()),
            "legal_phrase": phrase,
            "normalized_phrase": normalize(phrase),
            "keywords": keywords_of(phrase),
            "condition_tags": condition_tags(phrase)
        })

    mapping = {
        "description": "Penalty-focused mapping dictionary built from legal_chunks.jsonl",
        "source_chunk_file": str(settings.chunk_file),
        "total_entries": len(entries),
        "vehicle_aliases": {
            "car": ["ô tô", "oto", "xe hơi", "xe con", "xe tải", "xe khách"],
            "motorbike": ["xe máy", "mô tô", "moto", "xe gắn máy", "sh", "wave", "vision"],
            "bicycle": ["xe đạp", "xe đạp điện"],
            "pedestrian": ["người đi bộ", "đi bộ"]
        },
        "colloquial_aliases": {
            "vượt đèn đỏ": ["không chấp hành hiệu lệnh của đèn tín hiệu giao thông"],
            "vượt đèn vàng": ["không chấp hành hiệu lệnh của đèn tín hiệu giao thông"],
            "bắn tốc độ": ["điều khiển xe chạy quá tốc độ quy định"],
            "chạy quá tốc độ": ["điều khiển xe chạy quá tốc độ quy định"],
            "đi ngược chiều": ["đi ngược chiều của đường một chiều", "đường có biển cấm đi ngược chiều"],
            "không đội nón": ["không đội mũ bảo hiểm"],
            "không cài quai nón": ["không cài quai đúng quy cách"],
            "quên bằng lái": ["giấy phép lái xe"],
            "cà vẹt": ["chứng nhận đăng ký xe", "giấy đăng ký xe"],
            "chạy đi trốn sau va chạm": ["có liên quan trực tiếp đến vụ tai nạn giao thông mà không dừng lại", "không giữ nguyên hiện trường", "không trợ giúp người bị nạn"],
            "bỏ chạy sau tai nạn": ["có liên quan trực tiếp đến vụ tai nạn giao thông mà không dừng lại", "không giữ nguyên hiện trường", "không trợ giúp người bị nạn"]
        },
        "entries": entries
    }

    out = settings.indexes_dir / "mapping_dictionary.json"
    settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print("SAVED:", out)
    print("TOTAL_ENTRIES:", len(entries))

if __name__ == "__main__":
    build_mapping()
