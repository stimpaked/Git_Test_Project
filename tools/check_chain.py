"""산출물 묶음의 ID 참조 검사: 참조한 ID가 어느 산출물에든 정의되어 있는지 본다.

사용: python3 tools/check_chain.py <산출물1.md> <산출물2.md> ...
- 정의: 표 키 주석 `<!-- 표: 키 | 정의 ID: 접두어 -->` 아래 표의 첫 칸이 `접두어-숫자`로 시작하는 값
- 참조: 산출물 어디에서든 정의된 접두어와 같은 접두어로 쓰인 `접두어-숫자`
- 정의된 접두어에 한해서만 본다. 01~03번처럼 템플릿이 없는 단계의 ID는 검사하지 못한다.
- 후보 전수 소진(CH-K03~05): 통합·정규화 산출물(표 `기능목록`의 `병합 후보`, 표 `제외목록`의 `후보 ID`)이 있으면, 나머지 산출물의 후보 표(헤더에 `구분`과 `후보 문장` 또는 `기능 후보`가 있는 값 표)의 모든 후보 ID가 두 곳 중 정확히 한 번 나오는지 본다.
실패가 있으면 종료 코드 1.
"""
import re
import sys

from lib import KEY_RE, parse_value_tables, read, rel
from verify import report

ID_TOKEN = re.compile(r"(?<![A-Za-z가-힣])([A-Z]{1,3})-(\d+)(?!\d)")


def collect(path):
    text = read(path)
    entries, _lines, _t = parse_value_tables(text)
    defined, prefixes = set(), set()
    for e in entries:
        if e["prefix"] == "없음" or not e["table"]:
            continue
        pf = e["prefix"]
        prefixes.add(pf)
        for r in e["table"]["rows"]:
            m = re.match(rf"^{re.escape(pf)}-(\d+)", r[0].strip())
            if m:
                defined.add(f"{pf}-{m.group(1)}")
    return text, defined, prefixes


def check_chain(paths):
    res = []
    docs = {p: collect(p) for p in paths}
    defined = set().union(*[d[1] for d in docs.values()]) if docs else set()
    prefixes = set().union(*[d[2] for d in docs.values()]) if docs else set()
    for p, (text, _d, _p) in docs.items():
        seen = set()
        for i, line in enumerate(text.split("\n"), start=1):
            if KEY_RE.search(line) or line.startswith("> 지속 지침"):
                continue
            for m in ID_TOKEN.finditer(line):
                pf, num = m.group(1), m.group(2)
                tok = f"{pf}-{num}"
                if pf in prefixes and tok not in defined and (p, tok) not in seen:
                    seen.add((p, tok))
                    res.append(("CH-K01", "실패", f"{rel(p)}:{i}", f"정의되지 않은 ID를 참조한다: {tok}"))
    res += check_exhaust(paths)
    res.append(("CH-K02", "정보", "전체", f"산출물 {len(paths)}개, 정의된 ID {len(defined)}개, 접두어 {len(prefixes)}개"))
    return res


def _cells(e, col):
    t = e["table"]
    if not t or col not in t["header"]:
        return []
    i = t["header"].index(col)
    return [r[i].strip() for r in t["rows"] if len(r) > i]


def _pool_ids(entry):
    t = entry["table"]
    if not t:
        return []
    h = t["header"]
    if "구분" not in h or not ("후보 문장" in h or "기능 후보" in h) or h[0] not in ("ID", "후보 ID"):
        return []
    return [r[0].strip() for r in t["rows"] if r and re.match(r"^[A-Za-z]{1,4}-[\w-]+$", r[0].strip())]


def check_exhaust(paths):
    res = []
    merged, excluded, pool, src = [], [], {}, None
    for p in paths:
        entries, _l, _t = parse_value_tables(read(p))
        keys = {e["key"] for e in entries}
        if "기능목록" in keys and "제외목록" in keys and src is None:
            src = p
            for e in entries:
                if e["key"] == "기능목록":
                    for c in _cells(e, "병합 후보"):
                        merged += [x.strip() for x in c.split(",") if x.strip()]
                elif e["key"] == "제외목록":
                    excluded += [c for c in _cells(e, "후보 ID") if c]
            continue
        for e in entries:
            for i in _pool_ids(e):
                pool.setdefault(i, []).append(f"{rel(p)}:{e['key']}")
    if src is None:
        return res
    skip = {"해당 없음", "미정"}
    used = [x for x in merged + excluded if not any(x.startswith(k) for k in skip)]
    cnt = {}
    for x in used:
        cnt[x] = cnt.get(x, 0) + 1
    for i, where in sorted(pool.items()):
        if i not in cnt:
            res.append(("CH-K03", "실패", rel(src), f"후보가 기능 목록에도 기능 아님 목록에도 없다: {i} ({where[0]})"))
    for i, n in sorted(cnt.items()):
        if n > 1:
            res.append(("CH-K04", "실패", rel(src), f"후보가 {n}번 나온다: {i}"))
        elif i not in pool:
            res.append(("CH-K05", "실패", rel(src), f"후보 풀에 없는 ID다: {i}"))
    res.append(("CH-K06", "정보", rel(src), f"후보 풀 {len(pool)}개, 소진 {len(cnt)}개"))
    return res


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    return report(check_chain(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
