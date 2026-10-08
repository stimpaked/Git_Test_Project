"""산출물 묶음의 ID 참조 검사: 참조한 ID가 어느 산출물에든 정의되어 있는지 본다.

사용: python3 tools/check_chain.py <산출물1.md> <산출물2.md> ...
- 정의: 표 키 주석 `<!-- 표: 키 | 정의 ID: 접두어 -->` 아래 표의 첫 칸이 `접두어-숫자`로 시작하는 값
- 참조: 산출물 어디에서든 정의된 접두어와 같은 접두어로 쓰인 `접두어-숫자`
- 정의된 접두어에 한해서만 본다. 01~03번처럼 템플릿이 없는 단계의 ID는 검사하지 못한다.
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
    res.append(("CH-K02", "정보", "전체", f"산출물 {len(paths)}개, 정의된 ID {len(defined)}개, 접두어 {len(prefixes)}개"))
    return res


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    return report(check_chain(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
