"""문서 체계 검사. 각 함수는 (검사 ID, 수준, 위치, 메시지) 목록을 돌려준다.

수준: 실패 / 경고 / 정보. 검사 ID와 뜻은 docs/규칙_*.md 마지막 절의 검사 표를 따른다.
"""
import re
import subprocess
from collections import Counter

from lib import (DATA, CONVERSIONS, DOCS, GUIDES, LOGS_DIR, ROOT, TEMPLATES, TERM, load_interfaces,
                 parse_steps, parse_tables, parse_value_tables, read, rel, sample_terms, IF_HEADER)
from build import GEN_END, current_block, gen_block

F, W, I = "실패", "경고", "정보"


def out(cid, level, where, msg):
    return (cid, level, where, msg)


def _lines_nonblank(text):
    return [l for l in text.split("\n") if l.strip()]


def _templates():
    return sorted(TEMPLATES.glob("*_template.md"))


def template_info():
    """모든 템플릿의 표 정보. {nn: (path, text, entries, lines, tbls)}"""
    info = {}
    for p in _templates():
        text = read(p)
        entries, lines, tbls = parse_value_tables(text)
        info[p.name[:2]] = (p, text, entries, lines, tbls)
    return info


def field_keys():
    keys = {}
    for nn, (p, _t, entries, _l, _b) in template_info().items():
        for e in entries:
            for f in e["fields"]:
                keys[f"{nn}.{e['key']}.{f}"] = (nn, e["key"])
    return keys


# ---------------------------------------------------------------- 템플릿 (TP)

HINT_KINDS = ("자유 서술", "선택지", "ID 참조", "날짜", "숫자", "자명함", "형식", "링크", "파일 경로")
COND_RE = re.compile(r"이면|일 때|인 경우|할 때|라면|경우에는")
ID_PREFIX_RE = re.compile(r"(?<![A-Za-z])([A-Z]{1,3})-")
VER_LINE_RE = re.compile(r"^템플릿 v\d+\.\d+ · 산출물 v\{\{.+?\}\} · 상태 \{\{.+?\}\} · 작성일 \{\{.+?\}\}$")


def check_templates():
    res = []
    steps, _ = parse_steps()
    terms = sample_terms()
    seen_fields = {}
    for nn, (p, text, entries, lines, tbls) in template_info().items():
        w = rel(p)
        # K01 구성과 순서
        pos = {}
        for i, l in enumerate(lines):
            if i == 0 and l.startswith("# "):
                pos["제목"] = i
            if l.startswith("<!-- 생성 시작"):
                pos["생성 블록"] = i
            if l.startswith("**템플릿 변경 이력**"):
                pos["변경 이력"] = i
            if VER_LINE_RE.match(l):
                pos["버전 줄"] = i
            if l.startswith("## 완료 체크"):
                pos["완료 체크"] = i
        if entries:
            pos["값 표"] = entries[0]["line"]
        order = ["제목", "생성 블록", "변경 이력", "버전 줄", "값 표", "완료 체크"]
        miss = [k for k in order if k not in pos]
        if miss:
            res.append(out("TP-K01", F, w, "빠진 구성: " + ", ".join(miss)))
        else:
            seq = [pos[k] for k in order]
            if seq != sorted(seq):
                res.append(out("TP-K01", F, w, "구성 순서가 TP-03과 다르다"))
            tail = lines[pos["완료 체크"] + 1:]
            if not any(l.startswith("- [ ]") for l in tail):
                res.append(out("TP-K01", F, w, "완료 체크 항목이 없다"))
        if not any(l.startswith("| v") for l in lines):
            res.append(out("TP-K01", F, w, "템플릿 변경 이력 표에 행이 없다"))
        # 표 키 유일성, 필드 키 유일성
        keys = Counter(e["key"] for e in entries)
        for k, c in keys.items():
            if c > 1:
                res.append(out("TP-K06", F, w, f"표 키 중복: {k}"))
        for e in entries:
            if not re.fullmatch(r"[0-9A-Za-z_가-힣]+", e["key"]):
                res.append(out("TP-K06", F, w, f"표 키 형식 오류: {e['key']}"))
            for f in e["fields"]:
                fk = f"{nn}.{e['key']}.{f}"
                if fk in seen_fields:
                    res.append(out("TP-K06", F, w, f"필드 키 중복: {fk}"))
                seen_fields[fk] = w
        # 표별 검사
        for e in entries:
            where = f"{w} 표:{e['key']}"
            if e["table"] is None:
                res.append(out("TP-K02", F, where, "표 키 주석 아래에 표가 없다"))
                continue
            if e["kind"] == "attribute":
                if e["table"]["header"] != ["항목", "힌트", "내용", "근거"]:
                    res.append(out("TP-K02", F, where, f"속성 표 열 오류: {e['table']['header']}"))
            else:
                if e["table"]["header"][-1] != "근거":
                    res.append(out("TP-K02", F, where, "목록 표의 마지막 열이 `근거`가 아니다"))
                if not e["hint_table"]:
                    res.append(out("TP-K02", F, where, "열 힌트 표가 없다"))
                else:
                    hcols = [r[0] for r in e["hint_table"]["rows"]]
                    if hcols != e["table"]["header"]:
                        res.append(out("TP-K02", F, where, "열 힌트 표의 열 이름이 목록 표와 다르다"))
            if not e["has_ji"]:
                res.append(out("TP-K05", F, where, "지속 지침 한 줄이 없다"))
            hint_items = e["hints"].items()
            for name, h in hint_items:
                if not h:
                    res.append(out("TP-K03", F, where, f"힌트가 비었다: {name}"))
                elif not h.startswith(HINT_KINDS):
                    res.append(out("TP-K03", F, where, f"힌트가 값의 종류로 시작하지 않는다: {name}"))
                if h and COND_RE.search(h):
                    res.append(out("TP-K04", W, where, f"힌트에 조건 표현이 있다: {name}"))
            if e["kind"] == "list":
                for col in e["table"]["header"]:
                    if col not in e["hints"]:
                        res.append(out("TP-K03", F, where, f"열 힌트가 없다: {col}"))
        # K07 정의 ID 참조 순서
        defined = [(e["prefix"], e["section"]) for e in entries if e["prefix"] != "없음"]
        sec_order = sorted({e["section"] for e in entries})
        for e in entries:
            later = {pf for pf, sec in defined if sec > e["section"]}
            nxt = [s for s in sec_order if s > e["section"]]
            end = nxt[0] if nxt else len(lines)
            seg = "\n".join(lines[e["section"]:end])
            used = set(ID_PREFIX_RE.findall(seg))
            for pf in sorted(used & later):
                res.append(out("TP-K07", F, f"{w} 표:{e['key']}", f"뒤 표가 정의하는 ID `{pf}-`를 앞 표가 참조한다"))
        # K08 샘플 단어
        for t in terms:
            if t in text:
                res.append(out("TP-K08", W, w, f"샘플 고유 단어: {t}"))
        # K12 생성 블록
        cur = current_block(text)
        if cur is None:
            res.append(out("TP-K12", F, w, "생성 블록이 없다"))
        elif nn not in steps:
            res.append(out("TP-K12", F, w, f"단계 정의에 {nn}번이 없다"))
        elif cur != gen_block(nn):
            res.append(out("TP-K12", F, w, "생성 블록이 단계 정의·인터페이스 표와 다르다 (python3 tools/build.py)"))
    return res


# ---------------------------------------------------------------- 가이드 (GD)

COMMON_SECS = ["읽는 순서와 진행", "템플릿을 따라 쓰는 방법", "칸을 닫는 판단", "이전 단계 산출물을 쓰는 법",
               "예시와 샘플을 만났을 때", "완료 전 점검", "흔한 실수"]
STEP_SECS = ["입력을 읽는 법", "작성 절차", "항목별 해설", "누락 점검", "`미정`·`해당 없음` 판단", "흔한 실수"]
LIMIT_COMMON, LIMIT_STEP = 150, 200
EX_PREFIX = "예시(형식 시연, 값이 아님):"


def _guide_files():
    files = [(DOCS / "산출물_작성_guide.md", True)]
    files += [(p, False) for p in sorted(GUIDES.glob("*_guide.md"))]
    return files


def check_guides():
    res = []
    info = template_info()
    terms = sample_terms()
    for p, common in _guide_files():
        w = rel(p)
        text = read(p)
        lines = text.split("\n")
        secs = [re.sub(r"^\d+\.\s*", "", l[3:]).strip() for l in lines if l.startswith("## ")]
        want = COMMON_SECS if common else STEP_SECS
        if secs != want:
            res.append(out("GD-K01", F, w, f"절 구성이 규칙과 다르다: {secs}"))
        limit = LIMIT_COMMON if common else LIMIT_STEP
        n = len(_lines_nonblank(text))
        res.append(out("GD-K03", F if n > limit else I, w, f"{n}줄 (잠정 상한 {limit})"))
        in_code = False
        for i, l in enumerate(lines):
            if l.startswith("```"):
                in_code = not in_code
            s = re.sub(r"^[\s>\-*]+", "", l)
            if not in_code and s.startswith("예시") and not s.startswith(EX_PREFIX):
                res.append(out("GD-K04", F, f"{w}:{i + 1}", "예시가 `예시(형식 시연, 값이 아님):`으로 시작하지 않는다"))
        for t in terms:
            if t in text:
                res.append(out("GD-K05", W, w, f"샘플 고유 단어: {t}"))
        if common:
            continue
        nn = p.name[:2]
        if nn not in info:
            res.append(out("GD-K02", F, w, f"템플릿 {nn}번이 없다"))
            continue
        _p, ttext, entries, _l, _b = info[nn]
        marks = re.findall(r"<!--\s*해설:\s*(\S+)\s*-->", text)
        tkeys = [e["key"] for e in entries]
        for k in tkeys:
            if k not in marks:
                res.append(out("GD-K02", F, w, f"템플릿 표 `{k}`의 해설이 없다"))
        for k in marks:
            if k not in tkeys:
                res.append(out("GD-K02", F, w, f"템플릿에 없는 표의 해설: {k}"))
        for i, l in enumerate(lines):
            m = re.match(r"<!--\s*해설:\s*(\S+)\s*-->", l)
            if m and not (i + 1 < len(lines) and lines[i + 1].startswith("### ")):
                res.append(out("GD-K02", F, f"{w}:{i + 1}", "해설 주석 바로 아래에 소제목이 없다"))
        m = re.search(r"대상 템플릿 v(\d+\.\d+)", text)
        tv = re.search(r"^템플릿 v(\d+\.\d+)", ttext, re.M)
        if not m:
            res.append(out("GD-K06", W, w, "머리말에 `대상 템플릿 vX.Y`가 없다"))
        elif tv and m.group(1) != tv.group(1):
            res.append(out("GD-K06", W, w, f"대상 템플릿 v{m.group(1)}이 현재 템플릿 v{tv.group(1)}과 다르다"))
        if any("목적" in s for s in secs):
            res.append(out("GD-K07", F, w, "단계 가이드에 목적 절이 있다"))
    return res


# ---------------------------------------------------------------- 결정 로그 (DR)

ENTRY_RE = re.compile(r"^### (\S+) · (.*)$")
ID_RE = re.compile(r"^DL-(SD|ST|CM|DR|TP|GD|CV|IR|CG|TL|SYS|\d\d)-(\d{3})$")
REQUIRED = ["날짜", "대상", "결정 주체", "배경", "검토한 대안", "결정", "이유", "영향", "상태"]
SUBJECTS = ["사용자 결정", "사용자 승인", "유지보수자 판단"]


def log_files():
    files = sorted(DOCS.glob("*_decision-log.md")) + sorted(LOGS_DIR.glob("*_decision-log.md"))
    tool = ROOT / "tools" / "tools-decision-log.md"
    if tool.exists():
        files.append(tool)
    tmp = DOCS / "결정로그_체계.md"
    if tmp.exists():
        files.append(tmp)
    return files


def parse_log(text):
    """로그의 항목을 읽는다. 반환: [{id, title, fields, body, line}]"""
    lines = text.split("\n")
    entries, cur = [], None
    for i, l in enumerate(lines):
        m = ENTRY_RE.match(l)
        if m:
            cur = {"id": m.group(1), "title": m.group(2), "fields": {}, "body": [], "line": i + 1}
            entries.append(cur)
            continue
        if l.startswith("## ") or l.strip() == "---":
            cur = None if l.startswith("## ") else cur
        if cur is not None:
            cur["body"].append(l)
            fm = re.match(r"^- \*\*(.+?):\*\*\s*(.*)$", l)
            if fm:
                cur["fields"][fm.group(1)] = fm.group(2).strip()
    for e in entries:
        e["text"] = "\n".join(e["body"]).strip()
    return entries


def _expand_ids(s):
    """`DL-GD-001~006`, `DL-SYS-008, 010~014` 같은 표기를 ID 목록으로 푼다."""
    ids = []
    for m in re.finditer(r"DL-([A-Z0-9]+)-(\d{3})(?:\s*~\s*(?:DL-[A-Z0-9]+-)?(\d{3}))?((?:\s*,\s*\d{3}(?:\s*~\s*\d{3})?)*)", s):
        code, a, b, rest = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        ids += [f"DL-{code}-{n:03d}" for n in range(a, int(b) + 1)] if b else [f"DL-{code}-{a:03d}"]
        for mm in re.finditer(r"(\d{3})(?:\s*~\s*(\d{3}))?", rest):
            x, y = int(mm.group(1)), mm.group(2)
            ids += [f"DL-{code}-{n:03d}" for n in range(x, int(y) + 1)] if y else [f"DL-{code}-{x:03d}"]
    return ids


def exempt_ids():
    """규칙이 확정되기 전에 쓴 항목의 ID (DR-13). 칸이 모자라도 경고로만 본다."""
    p = DATA / "dr_exempt.txt"
    if not p.exists():
        return set()
    return {l.strip() for l in read(p).split("\n") if l.strip() and not l.startswith("#")}


def check_logs():
    res = []
    exempt = exempt_ids()
    exempt_missing = {}
    all_entries = {}
    per_file = {}
    for p in log_files():
        w = rel(p)
        entries = parse_log(read(p))
        per_file[w] = entries
        legacy = "임시 형식" in read(p)
        for e in entries:
            ew = f"{w}:{e['line']} {e['id']}"
            moved = "이동됨" in e["fields"].get("상태", "")
            all_entries.setdefault(e["id"], []).append((w, e, moved))
            if not ID_RE.match(e["id"]):
                res.append(out("DR-K02", F, ew, "항목 ID 형식 오류"))
            status = e["fields"].get("상태", "")
            subject = e["fields"].get("결정 주체", "")
            for f in REQUIRED:
                if not e["fields"].get(f):
                    if e["id"] in exempt or (legacy and f in ("날짜", "결정 주체")):
                        exempt_missing[w] = exempt_missing.get(w, 0) + 1
                        continue
                    res.append(out("DR-K01", F, ew, f"칸이 없거나 비었다: {f}"))
            if subject and subject.split(" ")[0] not in SUBJECTS and subject not in SUBJECTS:
                if not any(subject.startswith(s) for s in SUBJECTS):
                    res.append(out("DR-K01", F, ew, f"결정 주체 값 오류: {subject}"))
            if status and not re.match(r"^(유효|보류|검토 대기|대체됨\(→ ?DL-[A-Z0-9]+-\d{3}\))", status):
                res.append(out("DR-K01", F, ew, f"상태 값 오류: {status}"))
    for i, lst in all_entries.items():
        originals = [x for x in lst if not x[2]]
        if len(originals) > 1:
            res.append(out("DR-K02", F, i, "ID가 여러 로그에 중복: " + ", ".join(x[0] for x in originals)))
        if len(lst) > 1 and not originals:
            res.append(out("DR-K02", F, i, "이동됨 표시만 있고 원본이 없다"))
    for w, n in sorted(exempt_missing.items()):
        res.append(out("DR-K01", I, w, f"면제 항목(DR-13)에서 비어 있는 칸 {n}개"))
    ids = set(all_entries)
    for w, entries in per_file.items():
        for e in entries:
            st = e["fields"].get("상태", "")
            for m in re.finditer(r"대체됨\(→ ?(DL-[A-Z0-9]+-\d{3})\)", st):
                if m.group(1) not in ids:
                    res.append(out("DR-K03", F, f"{w} {e['id']}", f"대체한 ID가 없다: {m.group(1)}"))
            mv = re.search(r"이동됨 → ?`?([^\s`)]+)", st)
            if mv:
                target = mv.group(1)
                hits = [x for x in all_entries[e["id"]] if not x[2] and (x[0].endswith(target) or target in x[0])]
                if not hits:
                    res.append(out("DR-K06", F, f"{w} {e['id']}", f"이동 대상 {target}에 같은 ID 항목이 없다"))
    # K05 변경 이력의 결정 ID
    for p in sorted(list(DOCS.glob("*.md")) + list(GUIDES.glob("*.md")) + list(TEMPLATES.glob("*.md"))):
        if p.name.endswith("_outdated.md"):
            continue
        lines = read(p).split("\n")
        for t in parse_tables(lines):
            if t["header"][:4] == ["버전", "날짜", "요약", "결정 ID"]:
                for r in t["rows"]:
                    cell = r[3] if len(r) > 3 else ""
                    if cell.startswith("해당 없음"):
                        continue
                    found = _expand_ids(cell)
                    if not found:
                        res.append(out("DR-K05", F, f"{rel(p)} {r[0]}", f"결정 ID를 읽을 수 없다: {cell}"))
                    for x in found:
                        if x not in ids:
                            res.append(out("DR-K05", F, f"{rel(p)} {r[0]}", f"로그에 없는 결정 ID: {x}"))
    pend = [(w, e["id"]) for w, es in per_file.items() for e in es if e["fields"].get("상태", "").startswith("검토 대기")]
    res.append(out("DR-K07", I, "전체", f"`검토 대기` 항목 {len(pend)}개"))
    res += check_log_immutable(per_file)
    return res


def _git_show(path):
    try:
        return subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", check=True).stdout
    except Exception:
        return None


def check_log_immutable(per_file):
    res = []
    for w, entries in per_file.items():
        old = _git_show(w)
        if old is None:
            continue
        olds = {e["id"]: e for e in parse_log(old) if "이동됨" not in e["fields"].get("상태", "") or True}
        for e in entries:
            o = olds.get(e["id"])
            if o is None:
                continue

            def norm(x):
                f = dict(x["fields"])
                for k in ("상태", "결정 주체"):
                    f.pop(k, None)
                if "날짜" not in x["fields"]:
                    f.pop("날짜", None)
                return x["title"], f
            ot, of = norm(o)
            nt, nf = norm(e)
            if "날짜" not in o["fields"]:
                nf.pop("날짜", None)
            if ot != nt or of != nf:
                res.append(out("DR-K04", F, f"{w} {e['id']}", "과거 항목의 내용이 바뀌었다(상태 칸과 이동 표시만 허용)"))
    return res


# ---------------------------------------------------------------- 변환 분석서 (CV)

CLASSES = ["구조 유지", "일반화 필요", "값이라 제거", "순서 오류라 수정", "다른 곳이 담당"]
PROBLEMS = ["없음", "도메인 편향", "순서 오류", "기타 오류"]
STATUSES = ["초안", "검토", "승인"]
HEADER_KEYS = ["단계", "기준 단계 정의", "변환 입력 샘플", "대상 템플릿", "변환일", "상태"]
CONFIG_NAMES = ["제목", "버전 줄", "문서 정보", "생성 블록", "지속 지침", "완료 체크", "변경 이력", "관계 도식", "선택 블록", "힌트"]


def check_conversions():
    res = []
    info = template_info()
    fkeys = field_keys()
    for p in sorted(CONVERSIONS.glob("*_conversion.md")):
        w = rel(p)
        nn = p.name[:2]
        text = read(p)
        lines = text.split("\n")
        tbls = parse_tables(lines)
        head = next((t for t in tbls if t["header"] == ["칸", "내용"]), None)
        hv = {r[0]: r[1] for r in head["rows"]} if head else {}
        for k in HEADER_KEYS:
            if not hv.get(k):
                res.append(out("CV-K01", F, w, f"머리말 칸이 없거나 비었다: {k}"))
        status = hv.get("상태", "")
        if status and status not in STATUSES:
            res.append(out("CV-K01", F, w, f"상태 값 오류: {status}"))
        if hv.get("변환일") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", hv["변환일"]):
            res.append(out("CV-K01", F, w, "변환일 형식 오류"))
        sa = next((t for t in tbls if t["header"][:3] == ["ID", "샘플 요소", "분류"]), None)
        om = [t for t in tbls if t["header"][:2] == ["ID", "발견 내용"]]
        dt = [t for t in tbls if t["header"][:2] == ["ID", "도메인"]]
        if nn not in info:
            res.append(out("CV-K03", F, w, f"템플릿 {nn}번이 없다"))
            continue
        _p, _tt, entries, _l, _b = info[nn]
        tkeys = {e["key"] for e in entries}
        covered_tables, covered_fields = set(), set()
        # 선택 블록 이름
        selects = re.findall(r"^#+ \[선택\]\s*[\d\-.]*\s*(.+)$", _tt, re.M)

        def refs(cell):
            for m in re.finditer(r"표:(\S+?)(?=[,\s]|$)", cell):
                covered_tables.add(m.group(1).rstrip(".,"))
            for fk in fkeys:
                if fk.startswith(nn + ".") and fk in cell:
                    covered_fields.add(fk)
            for m in re.finditer(r"(\d\d\.\S+?\.[^~,/]+?)\s*~\s*(\d\d\.\S+?\.[^~,/]+?)(?=\s*(?:[,/]|$))", cell):
                a, b = m.group(1).strip(), m.group(2).strip()
                if a in fkeys and b in fkeys and fkeys[a] == fkeys[b]:
                    ks = [k for k in fkeys if fkeys[k] == fkeys[a]]
                    covered_fields.update(ks[ks.index(a):ks.index(b) + 1])
        if sa:
            for r in sa["rows"]:
                rid = r[0]
                if len(r) < 6:
                    res.append(out("CV-K02", F, f"{w} {rid}", "칸 수가 모자란다"))
                    continue
                if r[2] not in CLASSES:
                    res.append(out("CV-K02", F, f"{w} {rid}", f"분류 값 오류: {r[2]}"))
                if r[3] not in PROBLEMS:
                    res.append(out("CV-K02", F, f"{w} {rid}", f"샘플 문제 값 오류: {r[3]}"))
                el = r[1].strip()
                if not el or re.fullmatch(r"`?[\w./가-힣 ()_-]+\.md`?", el):
                    res.append(out("CV-K07", F, f"{w} {rid}", "샘플 요소가 발췌가 아니라 파일 이름이다"))
                corr = r[5]
                refs(corr)
                if corr.startswith("해당 없음"):
                    continue
                for tok in [x.strip() for x in re.split(r"\s*(?:/|,|~)\s*", corr) if x.strip()]:
                    m = re.match(r"표:(\S+)$", tok)
                    if m:
                        if m.group(1) not in tkeys:
                            res.append(out("CV-K03", F, f"{w} {rid}", f"없는 표 키: {m.group(1)}"))
                    elif tok.startswith("구성:"):
                        name = tok[3:].strip()
                        if not any(name.startswith(c) for c in CONFIG_NAMES) and not any(name.startswith(s) for s in selects):
                            res.append(out("CV-K03", F, f"{w} {rid}", f"알 수 없는 구성 요소: {name}"))
                    elif re.match(r"^\d\d\.", tok):
                        if tok not in fkeys:
                            res.append(out("CV-K03", F, f"{w} {rid}", f"없는 필드 키: {tok}"))
                    elif r[2] != "다른 곳이 담당":
                        res.append(out("CV-K03", F, f"{w} {rid}", f"템플릿 대응을 확인할 수 없다: {tok}"))
        else:
            res.append(out("CV-K02", F, w, "샘플 해부 표가 없다"))
        domains = set()
        for t in om:
            for r in t["rows"]:
                if len(r) >= 4:
                    refs(r[3])
                    m = re.match(r"도메인 대입:\s*(.+)$", r[2])
                    if m:
                        domains.add(m.group(1).strip())
        if len(domains) < 2:
            res.append(out("CV-K05", F, w, f"도메인 대입이 서로 다른 도메인 {len(domains)}개뿐이다"))
        # K04 덮임
        for e in entries:
            fields = [f"{nn}.{e['key']}.{f}" for f in e["fields"]]
            if e["key"] in covered_tables:
                continue
            miss = [f for f in fields if f not in covered_fields]
            if len(miss) == len(fields):
                res.append(out("CV-K04", F, w, f"표 `{e['key']}`가 어느 줄에도 대응하지 않는다"))
            else:
                for f in miss:
                    res.append(out("CV-K04", F, w, f"필드가 어느 줄에도 대응하지 않는다: {f}"))
        # K06 도메인 교체 시험
        dtrows = [r for t in dt for r in t["rows"]]
        if status == "승인":
            doms = {}
            for r in dtrows:
                doms.setdefault(r[1], set()).add(r[2])
            ok = [d for d, s in doms.items() if {"샘플 단어 누출", "칸 부족·의미 어긋남", "빈칸 규칙 위반"} <= s]
            if len(ok) < 2:
                res.append(out("CV-K06", F, w, "승인인데 세 확인 항목을 갖춘 도메인이 2개 미만이다"))
        else:
            res.append(out("CV-K06", I, w, f"상태 `{status}` — 도메인 교체 시험은 5단계에서 한다"))
    return res


# ---------------------------------------------------------------- 인터페이스 표 (IR)

METHODS = ["축(행·열)", "참조(ID)", "집계", "판단 입력", "제약", "근거 인용"]


def check_interfaces():
    res = []
    w = "tools/data/interfaces.csv"
    raw = (ROOT / w).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        res.append(out("IR-K01", F, w, "BOM이 있다"))
    header, rows = load_interfaces()
    if header != IF_HEADER:
        res.append(out("IR-K01", F, w, f"열 이름이 규칙과 다르다: {header}"))
    fkeys = field_keys()
    steps, _ = parse_steps()
    seen, ext_names, ids_prev = set(), set(), None
    n_prov = n_fb = 0
    senders = set()
    for ln, r in enumerate(rows, start=2):
        where = f"{w}:{ln}"
        if len(r) != 9:
            res.append(out("IR-K01", F, where, f"칸이 {len(r)}개다"))
            continue
        cid, snd, recv, rfield, method, desc, req, direction, basis = r
        if any(not c.strip() for c in r):
            res.append(out("IR-K01", F, where, "빈 칸이 있다"))
        term = recv == TERM
        if term:
            if (rfield, method, req, direction) != ("해당 없음",) * 4:
                res.append(out("IR-K01", F, where, f"`{TERM}` 줄은 받는 쪽·방식·필수·방향을 `해당 없음`으로 닫는다"))
        else:
            if method not in METHODS:
                res.append(out("IR-K01", F, where, f"쓰이는 방식 값 오류: {method}"))
            if req not in ("예", "아니오"):
                res.append(out("IR-K01", F, where, f"필수 값 오류: {req}"))
            if direction not in ("순행", "환류"):
                res.append(out("IR-K01", F, where, f"방향 값 오류: {direction}"))
        # K02
        is_ext = snd.startswith("EXT:")
        m = re.fullmatch(r"IF-(\d\d|EX)-(\d{3})", cid)
        s_step = snd[:2] if snd[:2].isdigit() else None
        if not m:
            res.append(out("IR-K02", F, where, f"연결 ID 형식 오류: {cid}"))
        elif is_ext and m.group(1) != "EX":
            res.append(out("IR-K02", F, where, "외부 입력은 IF-EX-nnn이어야 한다"))
        elif not is_ext and m.group(1) != s_step:
            res.append(out("IR-K02", F, where, "연결 ID의 단계 번호가 보내는 단계와 다르다"))
        if cid in seen:
            res.append(out("IR-K02", F, where, f"연결 ID 중복: {cid}"))
        seen.add(cid)
        if ids_prev and cid < ids_prev:
            res.append(out("IR-K02", F, where, "연결 ID 오름차순이 아니다"))
        ids_prev = cid
        # K03
        if is_ext:
            name = snd[4:]
            if not re.fullmatch(r"[0-9A-Za-z_가-힣]+", name):
                res.append(out("IR-K03", F, where, f"외부 입력 이름 형식 오류: {name}"))
            if name in ext_names:
                res.append(out("IR-K08", F, where, f"외부 입력 이름 중복: {name}"))
            ext_names.add(name)
        elif re.fullmatch(r"\d\d", snd):
            n_prov += 1
            if snd not in steps:
                res.append(out("IR-K03", F, where, f"없는 단계: {snd}"))
        else:
            if snd not in fkeys:
                res.append(out("IR-K03", F, where, f"없는 필드 키: {snd}"))
            else:
                senders.add(snd)
        # K04
        if not term:
            if recv not in steps:
                res.append(out("IR-K04", F, where, f"없는 받는 단계: {recv}"))
            if re.match(r"^\d\d\.", rfield):
                if rfield not in fkeys:
                    res.append(out("IR-K04", F, where, f"없는 받는 쪽 필드 키: {rfield}"))
                elif rfield[:2] != recv:
                    res.append(out("IR-K04", F, where, "받는 쪽 필드 키의 단계 번호가 받는 단계와 다르다"))
            elif re.fullmatch(r"\d\d", rfield):
                n_prov += 1
            elif not rfield.startswith("용도:"):
                res.append(out("IR-K04", F, where, f"받는 쪽 칸이 필드 키·`NN`·`용도:`가 아니다: {rfield}"))
        # K05
        if not term:
            if is_ext:
                if direction != "순행":
                    res.append(out("IR-K05", F, where, "외부 입력의 방향은 순행이다"))
            elif s_step:
                if s_step == recv:
                    res.append(out("IR-K05", F, where, "같은 단계 안의 연결이다"))
                elif direction != ("순행" if int(s_step) < int(recv) else "환류"):
                    res.append(out("IR-K05", F, where, "방향이 번호 비교와 다르다"))
            if direction == "환류":
                n_fb += 1
        # K06
        key = (snd, recv, rfield)
        res_key = ("IR-K06", key)
        if res_key in seen:
            res.append(out("IR-K06", F, where, f"같은 연결이 중복된다: {key}"))
        seen.add(res_key)
    # K07
    sent = {r[1] for r in rows if len(r) == 9}
    for fk in fkeys:
        if fk not in sent:
            res.append(out("IR-K07", F, "tools/data/interfaces.csv", f"보내는 필드로 나오지 않는 필드: {fk}"))
    # K09
    from build import gen_interface_doc
    p = DOCS / "단계_인터페이스.md"
    if not p.exists() or read(p) != gen_interface_doc():
        res.append(out("IR-K09", F, "docs/단계_인터페이스.md", "재생성한 문서와 다르다 (python3 tools/build.py)"))
    res.append(out("IR-K10", I, w, f"문서 수준 잠정 값 {n_prov}칸, 환류 {n_fb}줄"))
    return res


# ---------------------------------------------------------------- 산출물 (CM, TP)

def check_deliverable(path, template_path):
    """산출물 한 개를 템플릿과 대조한다."""
    res = []
    w = rel(path)
    text = read(path)
    ttext = read(template_path)
    lines = text.split("\n")
    # TP-K09, K10
    if "{{" in text:
        res.append(out("TP-K09", F, w, "`{{`가 남아 있다"))
    bad = [("<!-- 생성", "생성 블록"), ("템플릿 변경 이력", "템플릿 변경 이력"), ("> 작성 지침", "작성 지침"),
           ("[선택]", "`[선택]` 표시")]
    for pat, name in bad:
        if pat in text:
            res.append(out("TP-K10", F, w, f"{name}가 남아 있다"))
    entries, _l, tbls = parse_value_tables(text)
    for e in entries:
        if e["hint_table"]:
            res.append(out("TP-K10", F, w, f"표:{e['key']} 위에 열 힌트 표가 남아 있다"))
        if e["table"] and "힌트" in e["table"]["header"]:
            res.append(out("TP-K10", F, w, f"표:{e['key']}에 힌트 열이 남아 있다"))
    # TP-K13 구조
    tentries, _tl, _tt = parse_value_tables(ttext)
    tk = [e["key"] for e in tentries]
    dk = [e["key"] for e in entries]
    if tk != dk:
        res.append(out("TP-K13", F, w, f"표 키 순서가 템플릿과 다르다: 템플릿 {tk}, 산출물 {dk}"))
    first = lines[0] if lines else ""
    if first != ttext.split("\n")[0]:
        res.append(out("TP-K13", F, w, "제목이 템플릿과 다르다"))
    tmap = {e["key"]: e for e in tentries}
    for e in entries:
        t = tmap.get(e["key"])
        if not t or not e["table"]:
            continue
        if t["kind"] == "attribute":
            if e["table"]["header"] != ["항목", "내용", "근거"]:
                res.append(out("TP-K13", F, w, f"표:{e['key']} 열이 `항목/내용/근거`가 아니다"))
            if [r[0] for r in e["table"]["rows"]] != t["fields"]:
                res.append(out("TP-K13", F, w, f"표:{e['key']} 항목 이름이 템플릿과 다르다"))
        elif e["table"]["header"] != t["table"]["header"]:
            res.append(out("TP-K13", F, w, f"표:{e['key']} 열 이름이 템플릿과 다르다"))
        # CM-K01~03
        for r in e["table"]["rows"]:
            for ci, c in enumerate(r):
                col = e["table"]["header"][ci] if ci < len(e["table"]["header"]) else "?"
                if not c.strip():
                    res.append(out("CM-K01", F, f"{w} 표:{e['key']}", f"빈 칸: {r[0]} / {col}"))
                    continue
                if c.startswith("미정") and not all(k in c for k in ("확인처", "담당", "기한")):
                    res.append(out("CM-K02", F, f"{w} 표:{e['key']}", f"`미정`에 확인처·담당·기한이 없다: {r[0]}"))
                if c.startswith("해당 없음") and len(c.replace("해당 없음", "").strip(" ():,")) < 2:
                    res.append(out("CM-K02", F, f"{w} 표:{e['key']}", f"`해당 없음`에 사유가 없다: {r[0]}"))
            if e["table"]["header"][-1] == "근거" and r and not r[-1].strip():
                res.append(out("CM-K03", F, f"{w} 표:{e['key']}", f"근거가 비었다: {r[0]}"))
        # TP-K11
        if t["hints"]:
            for r in e["table"]["rows"]:
                for c in r[1:]:
                    for h in t["hints"].values():
                        if len(c) >= 12 and c in h:
                            res.append(out("TP-K11", W, f"{w} 표:{e['key']}", f"값이 힌트의 예시와 같다: {c[:30]}"))
    res += check_evidence(entries, w)
    for t in terms_in(text):
        res.append(out("CM-K07", W, w, f"샘플 고유 단어: {t}"))
    return res


SRC_TYPES = ("조사", "내부 자료", "일반 지식(미검증)", "가정")
REF_RE = re.compile(r"^(\d\d[ .]|[A-Z]{1,3}-\d)")


def check_evidence(entries, w):
    """CM-K04 근거 칸의 형식, CM-K06 미정 개수와 미검증 후보 비율."""
    res = []
    n_undecided = rows = weak = 0
    for e in entries:
        t = e["table"]
        if not t or t["header"][-1] != "근거":
            continue
        for r in t["rows"]:
            for c in r[:-1]:
                if c.startswith("미정"):
                    n_undecided += 1
            cell = r[-1].strip()
            if not cell or cell.startswith(("미정", "해당 없음")):
                continue
            rows += 1
            kinds = []
            for seg in [x.strip() for x in cell.split(";") if x.strip()]:
                tp = next((s for s in SRC_TYPES if seg.startswith(s + ":")), None)
                if tp:
                    kinds.append(tp)
                elif REF_RE.match(seg):
                    kinds.append("참조")
                else:
                    res.append(out("CM-K04", F, f"{w} 표:{e['key']}", f"근거가 출처 유형이나 참조로 시작하지 않는다: {r[0]} / {seg[:30]}"))
            if kinds and all(k in ("일반 지식(미검증)", "가정") for k in kinds):
                weak += 1
    ratio = f"{weak}/{rows}" if rows else "0/0"
    res.append(out("CM-K06", I, w, f"`미정` {n_undecided}칸, 근거가 모두 일반 지식·가정인 행 {ratio}"))
    return res


def terms_in(text):
    return [t for t in sample_terms() if t in text]


# ---------------------------------------------------------------- 세트 구성 (정의서 9절)

def check_sets():
    """단계 세트(템플릿·가이드·변환 분석서·결정 로그)가 같은 이름으로 모두 있는지 본다."""
    res = []
    steps, _ = parse_steps()
    kinds = [(TEMPLATES, "_template.md"), (GUIDES, "_guide.md"), (CONVERSIONS, "_conversion.md"),
             (LOGS_DIR, "_decision-log.md")]
    stems = {}
    for d, suf in kinds:
        for p in d.glob("*" + suf):
            stems.setdefault(p.name[: -len(suf)], set()).add(suf)
    for stem, have in sorted(stems.items()):
        nn = stem[:2]
        if nn not in steps:
            res.append(out("SET-K01", F, stem, f"단계 정의에 {nn}번이 없다"))
        for _d, suf in kinds:
            if suf not in have:
                res.append(out("SET-K01", F, stem, f"세트에 `{suf}` 파일이 없다"))
    res.append(out("SET-K02", I, "전체", f"단계 세트 {len(stems)}개 / 36"))
    return res
