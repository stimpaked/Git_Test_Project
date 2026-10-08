"""문서 체계 검사 실행기.

사용: python3 tools/verify.py [--only TP,GD,DR,CV,IR,SET] [--quiet]
실패가 하나라도 있으면 종료 코드 1. 경고와 정보는 종료 코드에 영향이 없다.
산출물 검사는 tools/check_deliverable.py를 쓴다.
"""
import argparse
import sys

import checks

GROUPS = {
    "TP": checks.check_templates,
    "GD": checks.check_guides,
    "DR": checks.check_logs,
    "CV": checks.check_conversions,
    "IR": checks.check_interfaces,
    "SET": checks.check_sets,
}


def report(results, quiet=False):
    order = {"실패": 0, "경고": 1, "정보": 2}
    results = sorted(results, key=lambda r: (order[r[1]], r[0], r[2]))
    for cid, level, where, msg in results:
        if quiet and level == "정보":
            continue
        print(f"[{level}] {cid} {where} — {msg}")
    n = {k: sum(1 for r in results if r[1] == k) for k in order}
    print(f"\n실패 {n['실패']} · 경고 {n['경고']} · 정보 {n['정보']}")
    return 1 if n["실패"] else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="쉼표로 구분한 검사 묶음 (TP,GD,DR,CV,IR,SET)")
    ap.add_argument("--quiet", action="store_true", help="정보 줄을 숨긴다")
    a = ap.parse_args()
    want = [x for x in a.only.split(",") if x] or list(GROUPS)
    results = []
    for g in want:
        results += GROUPS[g]()
    return report(results, a.quiet)


if __name__ == "__main__":
    sys.exit(main())
