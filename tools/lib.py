"""공통 도구: 경로, 마크다운 표 파싱, 단계 정의·인터페이스 표 읽기."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TEMPLATES = ROOT / "templates"
GUIDES = ROOT / "guides"
CONVERSIONS = ROOT / "conversions"
LOGS_DIR = ROOT / "decision-logs"
DATA = ROOT / "tools" / "data"

TERM = "최종 소비자 없음"
KEY_RE = re.compile(r"<!--\s*표:\s*(\S+)\s*\|\s*정의 ID:\s*(\S+)\s*-->")
SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")


def read(path):
    return Path(path).read_text(encoding="utf-8")


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def parse_tables(lines):
    """마크다운 표를 모두 찾는다. 각 표는 {start, end, header, rows}."""
    tables = []
    i = 0
    while i < len(lines) - 1:
        if lines[i].startswith("|") and SEP_RE.match(lines[i + 1].strip()):
            header = split_row(lines[i])
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            tables.append({"start": i, "end": j, "header": header, "rows": rows})
            i = j
        else:
            i += 1
    return tables


def parse_value_tables(text):
    """표 키 주석이 붙은 값 표를 모두 찾는다."""
    lines = text.split("\n")
    tbls = parse_tables(lines)
    by_start = {t["start"]: t for t in tbls}
    heads = [i for i, l in enumerate(lines) if l.startswith("## ")]
    out = []
    for i, l in enumerate(lines):
        m = KEY_RE.search(l)
        if not m:
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        t = by_start.get(j)
        sec = max([h for h in heads if h < i], default=-1)
        entry = {"key": m.group(1), "prefix": m.group(2), "line": i, "table": t, "section": sec,
                 "hint_table": None, "has_ji": False, "kind": None, "fields": [], "hints": {}}
        for k in range(sec + 1, i):
            if lines[k].startswith("> 지속 지침:"):
                entry["has_ji"] = True
        hts = [x for x in tbls if sec < x["start"] < i and x["header"] == ["열", "힌트"]]
        if hts:
            entry["hint_table"] = hts[-1]
        if t:
            if t["header"][:2] == ["항목", "힌트"]:
                entry["kind"] = "attribute"
                entry["fields"] = [r[0] for r in t["rows"]]
                entry["hints"] = {r[0]: (r[1] if len(r) > 1 else "") for r in t["rows"]}
            else:
                entry["kind"] = "list"
                entry["fields"] = list(t["header"])
                if entry["hint_table"]:
                    entry["hints"] = {r[0]: (r[1] if len(r) > 1 else "") for r in entry["hint_table"]["rows"]}
        out.append(entry)
    return out, lines, tbls


def sample_terms():
    p = DATA / "sample_terms.txt"
    if not p.exists():
        return []
    return [l.strip() for l in read(p).split("\n") if l.strip() and not l.startswith("#")]


def parse_steps():
    """단계 정의에서 단계 36개와 그룹 이름을 읽는다."""
    lines = read(DOCS / "단계_정의.md").split("\n")
    steps, groups = {}, {}
    for t in parse_tables(lines):
        if t["header"][:3] == ["번호", "이름", "그룹"]:
            for r in t["rows"]:
                steps[r[0]] = {"name": r[1], "group": r[2], "purpose": r[3]}
        if t["header"][:2] == ["그룹", "이름"]:
            for r in t["rows"]:
                groups[r[0]] = r[1]
    return steps, groups


IF_HEADER = ["연결 ID", "보내는 필드", "받는 단계", "받는 쪽 필드 또는 용도", "쓰이는 방식",
             "한 줄 설명", "필수", "방향", "근거"]


def load_interfaces():
    p = DATA / "interfaces.csv"
    with open(p, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [r for r in reader]
    return header, rows
