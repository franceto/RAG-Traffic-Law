from src.retrieval.bm25_search import search_bm25

VEHICLE_QUERIES = [
    ("car", "Ô tô", "Xe ô tô", "Điều 6"),
    ("motorbike", "Xe máy", "Xe máy", "Điều 7"),
    ("special_vehicle", "Xe máy chuyên dùng", "Xe máy chuyên dùng", "Điều 8"),
    ("bicycle", "Xe đạp / xe thô sơ", "Xe đạp", "Điều 9"),
    ("pedestrian", "Người đi bộ", "Người đi bộ", "Điều 10")
]

def clean_text(text):
    return " ".join(str(text or "").split())

def strip_vn(text):
    text = str(text or "").lower()
    table = str.maketrans(
        "áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ",
        "aaaaaaaaaaaaaaaaadeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyy"
    )
    return text.translate(table)

def norm(text):
    text = strip_vn(text)
    for ch in ',.;:()[]{}"“”!?/\\|-_':
        text = text.replace(ch, " ")
    return " ".join(text.split())

def citation_has_article(row, article):
    return article in str(row.get("citation", ""))

def source_vehicle(row):
    citation = str(row.get("citation", ""))

    if "Điều 6" in citation:
        return "car"
    if "Điều 7" in citation:
        return "motorbike"
    if "Điều 8" in citation:
        return "special_vehicle"
    if "Điều 9" in citation:
        return "bicycle"
    if "Điều 10" in citation:
        return "pedestrian"

    return row.get("vehicle_group", "")

def detect_concepts(question):
    q = norm(question)
    concepts = set()

    if any(x in q for x in ["vuot den", "den do", "den vang", "den tin hieu", "den giao thong"]):
        concepts.add("traffic_light")

    if any(x in q for x in ["nong do con", "ruou", "bia", "hoi tho", "miligam", "0 4", "0 40"]):
        concepts.add("alcohol")

    if any(x in q for x in ["canh sat giao thong", "csgt", "nguoi dieu khien giao thong", "nguoi kiem soat giao thong", "hieu lenh"]):
        concepts.add("traffic_controller")

    if any(x in q for x in ["dung xe", "do xe", "dau xe"]):
        concepts.add("parking")

    if any(x in q for x in ["khoang cach", "va cham"]):
        concepts.add("distance_collision")

    if any(x in q for x in ["nhuong duong cho nguoi di bo", "nguoi di bo tai vach", "nguoi di bo qua duong", "vach ke duong"]):
        concepts.add("yield_pedestrian")

    if any(x in q for x in ["cao toc"]):
        concepts.add("highway")

    if any(x in q for x in ["brt", "xe buyt nhanh", "lan duong danh rieng"]):
        concepts.add("bus_lane")

    if any(x in q for x in ["mu bao hiem", "khong doi mu"]):
        concepts.add("helmet")

    if any(x in q for x in ["bam coi", "su dung coi", "coi", "22h", "22 gio", "5h", "05 gio"]):
        concepts.add("horn_time")

    if any(x in q for x in ["giay phep lai xe", "bang lai", "quen bang"]):
        concepts.add("license")

    return concepts

def canonical_queries(question):
    concepts = detect_concepts(question)
    qs = [question]

    if "traffic_light" in concepts:
        qs.insert(0, "không chấp hành hiệu lệnh của đèn tín hiệu giao thông")

    if "alcohol" in concepts:
        qs.insert(0, "nồng độ cồn vượt quá 0,4 miligam trên 1 lít khí thở")
        qs.insert(0, "trong hơi thở có nồng độ cồn vượt quá 0,4 miligam trên 1 lít khí thở")

    if "traffic_controller" in concepts:
        qs.insert(0, "không chấp hành hiệu lệnh của người điều khiển giao thông")
        qs.insert(0, "không chấp hành hiệu lệnh của người kiểm soát giao thông")

    if "parking" in concepts:
        qs.insert(0, "dừng xe đỗ xe không đúng nơi quy định")

    if "distance_collision" in concepts:
        qs.insert(0, "không giữ khoảng cách an toàn để xảy ra va chạm")

    if "highway" in concepts:
        qs.insert(0, "đi vào đường cao tốc")

    if "bus_lane" in concepts:
        qs.insert(0, "đi vào làn đường dành riêng cho xe buýt nhanh")

    if "helmet" in concepts:
        qs.insert(0, "không đội mũ bảo hiểm")

    if "license" in concepts:
        qs.insert(0, "không mang theo giấy phép lái xe")
        qs.insert(0, "không xuất trình được giấy phép lái xe")

    return list(dict.fromkeys(qs))

def content_supports(question, row):
    concepts = detect_concepts(question)
    c = norm(row.get("content", ""))

    if "traffic_light" in concepts:
        if not any(x in c for x in ["den tin hieu", "den giao thong", "khong chap hanh hieu lenh cua den"]):
            return False

    if "alcohol" in concepts:
        if "nong do con" not in c:
            return False
        q = norm(question)
        if any(x in q for x in ["0 4", "0 40", "vuot qua 0 4"]):
            if not any(x in c for x in ["vuot qua 0 4", "vuot qua 0 40"]):
                return False

    if "traffic_controller" in concepts:
        if not any(x in c for x in ["nguoi dieu khien giao thong", "nguoi kiem soat giao thong", "hieu lenh cua nguoi"]):
            return False

    if "parking" in concepts:
        if not any(x in c for x in ["dung xe", "do xe", "dau xe"]):
            return False

    if "distance_collision" in concepts:
        if not any(x in c for x in ["khoang cach", "va cham"]):
            return False

    if "yield_pedestrian" in concepts:
        if not any(x in c for x in ["nguoi di bo", "nhuong duong", "vach ke duong"]):
            return False

    if "highway" in concepts:
        if "cao toc" not in c:
            return False

    if "bus_lane" in concepts:
        if not any(x in c for x in ["xe buyt nhanh", "lan duong danh rieng", "duong danh rieng"]):
            return False

    if "helmet" in concepts:
        if "mu bao hiem" not in c:
            return False

    if "horn_time" in concepts:
        if not any(x in c for x in ["su dung coi", "bam coi", "22 gio", "05 gio", "5 gio"]):
            return False

    if "license" in concepts:
        if not any(x in c for x in ["giay phep lai xe", "khong xuat trinh", "khong mang theo"]):
            return False

    return True

def valid_vehicle(row, vehicle_key, article):
    if not citation_has_article(row, article):
        return False

    sv = source_vehicle(row)
    if sv and sv != vehicle_key:
        return False

    return True

def rank_bonus(question, row):
    c = norm(row.get("content", ""))
    q = norm(question)
    score = 0

    if "vuot qua 0 4" in q and "vuot qua 0 4" in c:
        score += 100

    if "den do" in q and "den tin hieu" in c:
        score += 50

    if "canh sat giao thong" in q and "nguoi kiem soat giao thong" in c:
        score += 50

    if "canh sat giao thong" in q and "nguoi dieu khien giao thong" in c:
        score += 50

    if "va cham" in q and "va cham" in c:
        score += 40

    return score

def search_vehicle(question, vehicle_key, vehicle_name, prefix, article):
    candidates = []

    for cq in canonical_queries(question):
        q = f"{prefix} {cq}"

        for row in search_bm25(q, top_k=20):
            if not row.get("citation"):
                continue

            if not row.get("fine_text"):
                continue

            if not valid_vehicle(row, vehicle_key, article):
                continue

            if not content_supports(question, row):
                continue

            item = dict(row)
            item["score"] = float(row.get("score", 0)) + rank_bonus(question, row)
            item["source_query"] = q
            candidates.append(item)

    if not candidates:
        return None

    candidates = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    top = candidates[0]

    return {
        "vehicle_key": vehicle_key,
        "vehicle_name": vehicle_name,
        "query": top.get("source_query", ""),
        "vehicle_group": vehicle_key,
        "citation": clean_text(top.get("citation", "")),
        "fine_text": clean_text(top.get("fine_text", "")),
        "content": clean_text(top.get("content", "")),
        "source": top
    }

def multi_vehicle_allowed(question):
    q = norm(question)

    if "den xanh" in q and not any(x in q for x in ["sang den do", "den do", "chom qua vach", "chua kip"]):
        return False

    concepts = detect_concepts(question)

    allowed = {
        "traffic_light",
        "alcohol",
        "traffic_controller",
        "parking",
        "distance_collision",
        "yield_pedestrian",
        "horn_time",
        "helmet"
    }

    return bool(concepts & allowed)

def build_multi_vehicle_results(question):
    if not multi_vehicle_allowed(question):
        return []

    rows = []

    for vehicle_key, vehicle_name, prefix, article in VEHICLE_QUERIES:
        item = search_vehicle(question, vehicle_key, vehicle_name, prefix, article)
        if item:
            rows.append(item)

    unique = []
    seen = set()

    for r in rows:
        key = (r["vehicle_key"], r["citation"])
        if key not in seen:
            unique.append(r)
            seen.add(key)

    return unique

def generate_multi_vehicle_answer(question, rows):
    if not rows:
        return (
            "Bạn cần cho biết loại phương tiện để xác định đúng mức phạt, "
            "ví dụ: ô tô, xe máy, xe máy chuyên dùng, xe đạp hoặc người đi bộ. "
            "Cùng một hành vi có thể có mức phạt khác nhau theo từng loại phương tiện."
        )

    lines = []
    lines.append("Bạn chưa nói rõ loại phương tiện, nên tôi chưa thể kết luận một mức phạt duy nhất.")
    lines.append("")
    lines.append("Dưới đây là các mức tham khảo theo từng loại phương tiện tìm được trong dữ liệu:")
    lines.append("")

    for r in rows:
        fine = r["fine_text"] if r["fine_text"] else "Nguồn liên quan chưa nêu rõ mức phạt"
        lines.append(f"- {r['vehicle_name']}: {fine}.")
        lines.append(f"  Căn cứ: {r['citation']}.")

    lines.append("")
    lines.append("Bạn hãy cho biết chính xác phương tiện là ô tô, xe máy, xe máy chuyên dùng, xe đạp hay người đi bộ để tôi chốt đúng một căn cứ pháp lý.")

    return "\n".join(lines)

def multi_vehicle_answer(question):
    rows = build_multi_vehicle_results(question)
    answer = generate_multi_vehicle_answer(question, rows)

    sources = []

    for r in rows:
        src = dict(r["source"])
        src["multi_vehicle_name"] = r["vehicle_name"]
        src["vehicle_group"] = r["vehicle_key"]
        sources.append(src)

    return answer, sources, rows
