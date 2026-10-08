"""산출물 검사: 산출물이 템플릿과 공통 규칙을 지켰는지 본다.

사용: python3 tools/check_deliverable.py <산출물.md> <템플릿.md>
실패가 있으면 종료 코드 1.
CM-K04~K06(출처 유형·근거 등급·미검증 비율)은 템플릿에 출처 유형을 담는 칸이 없어 아직 검사하지 못한다(수정목록 C21).
"""
import sys

import checks
from verify import report


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    return report(checks.check_deliverable(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    sys.exit(main())
