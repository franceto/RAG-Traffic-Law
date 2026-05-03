
import re
import unicodedata

def normalize(text):
    text = str(text or "").lower()
    text = text.replace("\u0111", "d").replace("\u0110", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def has_any(q, terms):
    return any(t in q for t in terms)

def is_green_light_question(query):
    q = normalize(query)

    green_terms = [
        "den xanh",
        "den tin hieu xanh",
        "tin hieu mau xanh",
        "den tin hieu mau xanh",
        "mau xanh"
    ]

    exception_terms = [
        "sang den do",
        "den do",
        "den vang",
        "chom qua vach",
        "chua kip",
        "het nga tu"
    ]

    return has_any(q, green_terms) and not has_any(q, exception_terms)

def classify_query_type(query):
    q = normalize(query)

    if is_green_light_question(query):
        return "non_violation_question"

    ambiguous_terms = [
        "den xanh con",
        "chom qua vach",
        "chua kip",
        "den tin hieu hong",
        "ca 3 mau",
        "bien bao bi cay che",
        "bi che khuat",
        "co bi coi la",
        "co duoc coi la",
        "tinh huong",
        "khong co cho tranh",
        "duong tac",
        "tat may",
        "dung chan day",
        "nam ngu",
        "dang do dung noi quy dinh",
        "gia do",
        "treo tren gia do"
    ]

    emergency_terms = [
        "xe cap cuu",
        "xe uu tien",
        "xe chua chay",
        "xe cong an",
        "xe quan su",
        "doan xe uu tien",
        "nhuong duong cho xe cap cuu",
        "nhuong duong cho xe uu tien"
    ]

    exception_terms = [
        "mien tru",
        "mien phat",
        "bat kha khang",
        "cap cuu",
        "tinh the cap thiet",
        "chu xe",
        "cho ban muon xe",
        "phat nguoi",
        "camera hanh trinh"
    ]

    penalty_terms = [
        "phat bao nhieu",
        "muc phat",
        "muc xu phat",
        "phat tien",
        "bao nhieu tien",
        "mat bao nhieu",
        "may trieu",
        "may lit",
        "xu phat",
        "bi phat",
        "phat khong",
        "bi bat",
        "mat tien",
        "bi xu ly",
        "xu ly nhu the nao",
        "bi xu phat",
        "che bien so",
        "khong doi mu",
        "lang lach",
        "danh vong"
    ]

    rule_terms = [
        "quy dinh",
        "duoc quyen",
        "co gia tri",
        "thay the",
        "trong bao lau",
        "thi lai",
        "giu xe",
        "bien ban",
        "khong ky bien ban",
        "vneid",
        "tich hop",
        "khac nhau",
        "nop phat",
        "tinh them tien lai"
    ]

    if has_any(q, ambiguous_terms):
        return "ambiguous_scenario"

    if "cap cuu" in q and has_any(q, ["vuot den do", "den do", "mien tru", "mien phat", "phat nguoi"]):
        return "exception_question"

    if has_any(q, emergency_terms) and has_any(q, exception_terms + ["vuot den do", "den do", "phat nguoi"]):
        return "exception_question"

    if has_any(q, ["camera hanh trinh", "phat nguoi", "cho ban muon xe", "chu xe"]) and not has_any(q, ["che bien so"]):
        return "exception_question"

    if has_any(q, penalty_terms):
        return "penalty_single_hop"

    if has_any(q, rule_terms):
        return "rule_question"

    return "general_question"
