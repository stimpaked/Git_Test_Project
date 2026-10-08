"""생성 도구: 인터페이스 표(CSV)와 단계 정의에서 생성물을 만든다.

- docs/단계_인터페이스.md  (읽기용 문서, IR-11)
- templates/*_template.md 의 문서 정보 블록 (TP-04, IR-12)

사용: python3 tools/build.py
"""
import re
import sys

from lib import (DOCS, TEMPLATES, TERM, load_interfaces, parse_steps, read)

GEN_START = "<!-- 생성 시작: 문서 정보 (도구가 단계 정의와 인터페이스 표에서 생성한다. 직접 수정하지 않는다) -->"
GEN_END = "<!-- 생성 끝 -->"


def _step_label(nn, steps):
    return f"{nn} {steps[nn]['name']}" if nn in steps else nn


def connections_for(nn):
    """단계 nn의 입력과 쓰이는 곳을 CSV에서 모은다."""
    _, rows = load_interfaces()
    inputs, forward, feedback, ext = {}, set(), set(), []
    for r in rows:
        sender, recv_step, direction = r[1], r[2], r[7]
        s_step = sender[:2] if sender[:2].isdigit() else None
        if recv_step == nn:
            if sender.startswith("EXT:"):
                if sender[4:] not in ext:
                    ext.append(sender[4:])
            elif s_step:
                fields = inputs.setdefault(s_step, [])
                if "." in sender:
                    f = sender.split(".", 2)[2]
                    if f not in fields:
                        fields.append(f)
        if s_step == nn and recv_step != TERM:
            (feedback if direction == "환류" else forward).add(recv_step)
    return inputs, ext, sorted(forward), sorted(feedback)


def gen_block(nn):
    steps, groups = parse_steps()
    inputs, ext, forward, feedback = connections_for(nn)
    s = steps[nn]
    in_parts = []
    for k in sorted(inputs):
        label = _step_label(k, steps)
        if inputs[k]:
            label += "(필드: " + ", ".join(inputs[k]) + ")"
        in_parts.append(label)
    in_parts += ext
    used = ", ".join(_step_label(k, steps) for k in forward)
    if feedback:
        used += (". " if used else "") + "환류: " + ", ".join(_step_label(k, steps) for k in feedback)
    lines = [
        GEN_START,
        "| 구분 | 내용 |",
        "|---|---|",
        f"| 단계 | {nn} / 36 — {s['group']}. {groups[s['group']]} |",
        f"| 목적 | {s['purpose']} |",
        f"| 입력 | {', '.join(in_parts) if in_parts else '연결 미작성'} |",
        f"| 이 산출물이 쓰이는 곳 | {used if used else '연결 미작성'} |",
        GEN_END,
    ]
    return "\n".join(lines)


def current_block(text):
    a = text.find("<!-- 생성 시작")
    b = text.find(GEN_END)
    if a < 0 or b < 0:
        return None
    return text[a:b + len(GEN_END)]


def gen_interface_doc():
    steps, _ = parse_steps()
    header, rows = load_interfaces()
    out = ["# 단계 인터페이스", "",
           "> **자동 생성 문서.** `tools/data/interfaces.csv`와 `docs/단계_정의.md`에서 `tools/build.py`가 만든다. 직접 고치지 않는다(`docs/규칙_인터페이스표.md` IR-11).",
           "", "## 1. 단계별 요약", "",
           "| 번호 | 이름 | 입력 | 이 산출물이 쓰이는 곳 |", "|---|---|---|---|"]
    for nn in sorted(steps):
        inputs, ext, forward, feedback = connections_for(nn)
        ins = [_step_label(k, steps) for k in sorted(inputs)] + [f"{e}(외부 입력)" for e in ext]
        used = ", ".join(_step_label(k, steps) for k in forward)
        if feedback:
            used += (". " if used else "") + "환류: " + ", ".join(_step_label(k, steps) for k in feedback)
        out.append(f"| {nn} | {steps[nn]['name']} | {', '.join(ins) if ins else '연결 미작성'} | {used if used else '연결 미작성'} |")
    out += ["", "## 2. 연결 전체 목록", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
    prov = [r for r in rows if re.fullmatch(r"\d\d", r[1]) or re.fullmatch(r"\d\d", r[3])]
    out += ["", "## 3. 집계", "", "| 항목 | 줄 수 |", "|---|---|",
            f"| 연결 전체 | {len(rows)} |",
            f"| 문서 수준 잠정 연결 | {len(prov)} |",
            f"| 환류 | {sum(1 for r in rows if r[7] == '환류')} |",
            f"| 외부 입력 | {sum(1 for r in rows if r[1].startswith('EXT:'))} |",
            f"| {TERM} | {sum(1 for r in rows if r[2] == TERM)} |", ""]
    return "\n".join(out)


def main():
    (DOCS / "단계_인터페이스.md").write_text(gen_interface_doc(), encoding="utf-8")
    print("생성: docs/단계_인터페이스.md")
    for p in sorted(TEMPLATES.glob("*_template.md")):
        nn = p.name[:2]
        text = read(p)
        cur = current_block(text)
        if cur is None:
            print(f"건너뜀: {p.name} (생성 블록 표시 없음)")
            continue
        new = text.replace(cur, gen_block(nn), 1)
        if new != text:
            p.write_text(new, encoding="utf-8")
            print(f"갱신: templates/{p.name}")
        else:
            print(f"변경 없음: templates/{p.name}")


if __name__ == "__main__":
    sys.exit(main())
