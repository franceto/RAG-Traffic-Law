import re
import unicodedata

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def has_phrase(q, phrase):
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", q) is not None

def has_any(q, phrases):
    return any(has_phrase(q, p) for p in phrases)

def detect_vehicle_group(query):
    q = normalize(query)

    if has_any(q, ["xe may chuyen dung", "may keo", "xe chuyen dung"]):
        return "special_vehicle"

    if has_any(q, ["lan duong danh rieng cho xe buyt", "brt"]):
        return "unknown"

    if has_any(q, ["xe may", "mo to", "moto", "xe gan may", "lead", "wave", "sh", "vision"]):
        return "motorbike"

    if has_any(q, ["xe dap dien", "xe dap", "xe tho so"]):
        return "bicycle"

    if has_any(q, ["o to", "oto", "xe hoi", "xe con", "xe tai", "xe khach", "xe buyt"]):
        return "car"

    if has_any(q, ["nhuong duong cho nguoi di bo", "nguoi di bo tai vach", "nguoi di bo qua duong"]):
        return "unknown"

    if has_any(q, ["nguoi di bo", "di bo"]):
        return "pedestrian"

    return "unknown"

def is_penalty_like_query(query):
    q = normalize(query)
    keys = [
        "phat bao nhieu",
        "muc phat",
        "muc xu phat",
        "phat tien",
        "bao nhieu tien",
        "mat bao nhieu",
        "may trieu",
        "may lit",
        "bi phat",
        "xu phat",
        "bi xu phat",
        "bi bat",
        "bi xu ly",
        "xu ly nhu the nao",
        "phat khong"
    ]
    return has_any(q, keys)

def needs_vehicle_clarification(query, query_type):
    if query_type not in ["penalty_single_hop", "general_question"]:
        return False

    if not is_penalty_like_query(query):
        return False

    return detect_vehicle_group(query) == "unknown"

def vehicle_clarification_answer():
    return (
        "Bạn cần cho biết loại phương tiện để xác định đúng mức phạt, "
        "ví dụ: ô tô, xe máy, xe máy chuyên dùng, xe đạp hoặc người đi bộ. "
        "Cùng một hành vi có thể có mức phạt khác nhau theo từng loại phương tiện."
    )