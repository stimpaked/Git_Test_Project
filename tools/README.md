# tools

문서 체계를 검사하고 생성물을 만드는 도구다. Python 3 표준 라이브러리만 쓴다.

| 명령 | 하는 일 |
|---|---|
| `python3 tools/build.py` | `tools/data/interfaces.csv`와 `docs/단계_정의.md`에서 `docs/단계_인터페이스.md`와 각 템플릿의 문서 정보 블록을 만든다 |
| `python3 tools/verify.py [--only TP,GD,DR,CV,IR,SET] [--quiet]` | 템플릿·가이드·결정 로그·변환 분석서·인터페이스 표·세트 구성을 검사한다. 실패가 있으면 종료 코드 1 |
| `python3 tools/check_deliverable.py <산출물> <템플릿>` | 산출물이 템플릿 구조와 공통 규칙을 지켰는지 검사한다 |
| `python3 tools/check_chain.py <산출물1> <산출물2> ...` | 산출물 묶음에서 다른 산출물의 ID를 참조한 곳이 실제로 정의되어 있는지 검사하고, 통합·정규화 산출물이 있으면 후보 풀이 빠짐없이 한 번씩 쓰였는지 검사한다 |

검사 ID와 뜻은 `docs/규칙_*.md`의 검사 표가 정한다. 문서를 고친 뒤에는 `build.py`, `verify.py` 순서로 돌린다.

| 파일 | 내용 |
|---|---|
| `lib.py` | 경로, 마크다운 표 읽기, 단계 정의·인터페이스 표 읽기 |
| `checks.py` | 검사 구현 |
| `data/interfaces.csv` | 인터페이스 표 원본 (`docs/규칙_인터페이스표.md`) |
| `data/sample_terms.txt` | 샘플 고유 단어 (CM-17) |
| `data/dr_exempt.txt` | 규칙 확정 전 결정 로그 항목 면제 목록 (DR-13) |
| `tools-decision-log.md` | 도구의 결정 로그와 알려진 한계 |

구현하지 못한 검사와 알려진 한계는 `tools/tools-decision-log.md` A절에 있다.
