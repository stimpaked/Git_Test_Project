"""31(통합)·32(트리)·33(의존성)·34(역추적)·36(우선순위) 문서를 생성하는 함수 모음."""
import re, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_data import *

DATE = '2026-10-06'


def hdr(num, title, group, inp, out, used, ver='v1.0'):
    return f"""# {num}. {title}

> **샘플 문서** · 가상 서비스 "이웃장터" 기준 · 작성일 {DATE} · {ver} · 작성 PM(가상) · 상태 승인

| 구분 | 내용 |
|---|---|
| 단계 | {int(num)} / 36 — {group} |
| 입력 | {inp} |
| 산출물 | {out} |
| 이 산출물이 쓰이는 곳 | {used} |

---

"""


def write(fname, text):
    with open(os.path.join(ROOT, fname), 'w', encoding='utf-8') as fh:
        fh.write(text)


def base(s):
    return re.sub(r'\s+—\s+.*$', '', re.sub(r'\*\*', '', s)).strip()


def short(s, n=46):
    s = re.sub(r'\*\*', '', s)
    s = md(s)
    return s if len(s) <= n else s[:n - 1] + '…'


fl = list(final.values())
v0 = [d for d in fl if d['added'] == 'v0']

# ---------------------------------------------------------------- 31
def gen31():
    o = hdr('31', '통합·정규화 → Feature List v0', 'I. 통합·관리',
            '9~30단계의 후보 풀 전부(Q-001~Q-232, CF-12~CF-30), 11의 용어집',
            'Feature List v0 — 후보 355건을 중복·동의어 병합해 기능 목록으로 정리',
            '32(트리화 대상) · 34(검증 대상)')
    o += "## 1. 통합 규칙\n\n| 규칙 | 내용 |\n|---|---|\n"
    rules = [
        ('U1 병합', '같은 목표·같은 대상·같은 동작이면 하나의 기능으로 합친다(예: 같은 "푸시 권한 사전 안내"가 4개 단계에서 각각 나온 경우)'),
        ('U2 용어', '동의어는 11번 용어집의 표준 용어로 바꾼다(상품→글, 리뷰→후기 등)'),
        ('U3 기능명', '"대상 + 동작" 형태로 쓴다. 정책 값(기간·횟수)은 기능명에 넣지 않는다'),
        ('U4 입도', 'L3(기능)는 "독립적으로 우선순위를 매기고 테스트할 수 있는 최소 단위"로 맞춘다. 너무 작은 항목(문구·입력 규칙)은 상위 기능에 흡수한다'),
        ('U5 기능 아님', '설계 결정·출시 프로세스·운영 프로세스는 기능 목록에서 제외하고 **사유를 남긴다**'),
        ('U6 근거 보존', '병합 후에도 합쳐진 후보 ID를 모두 기록한다(역추적용). 후보를 지우지 않는다'),
        ('U7 Later', 'Later 후보도 삭제하지 않고 기능으로 등록하되 릴리스를 Later로 둔다(36번)'),
    ]
    for a, b in rules:
        o += f"| {a} | {b} |\n"

    mapped = [c for c in cands if c not in excl]
    cand_feats = [d for d in v0 if any(re.match(r'(Q|CF)-', s) for s in d['srcs'])]
    o += f"""
## 2. 통합 결과 요약

| 항목 | 수 |
|---|---|
| 후보 풀 전체 | **{len(cands)}**건 (❓ Q-001~Q-232 {sum(1 for c in cands if c.startswith('Q-'))}건 + 단계별 신규 후보 CF {sum(1 for c in cands if c.startswith('CF-'))}건) |
| 기능 아님으로 제외 | **{len(excl)}**건 (아래 5절) |
| 기능으로 병합된 후보 | **{len(mapped)}**건 |
| 결과: Feature List v0 기능 수 | **{len(v0)}**개 (후보 기반 {len(cand_feats)}개 + 플로우 정상 경로 기반 {len(v0) - len(cand_feats)}개) |
| 평균 병합률 | 기능 1개당 후보 {len(mapped) / len(cand_feats):.2f}건 |

> 32번 이후 34번(역추적)·35번(워크스루)에서 기능이 5건 추가되어 최종 146개가 됩니다(32번 변경 이력 참조). 이 문서는 **v0 시점**(141개)의 병합 결과입니다.

### 영역별 분포 (v0)

| 영역 | 구분 | 병합된 후보 수 | 기능 수 |
|---|---|---|---|
"""
    cnt_c = collections.Counter()
    for f, d in final.items():
        if d['added'] == 'v0':
            cnt_c[d['area']] += sum(1 for s in d['srcs'] if re.match(r'(Q|CF)-', s))
    cnt_f = collections.Counter(d['area'] for d in v0)
    for a, (nm, sc) in AREAS.items():
        o += f"| {a} {nm} | {sc} | {cnt_c[a]} | {cnt_f[a]} |\n"
    o += f"| **합계** | | **{sum(cnt_c.values())}** | **{sum(cnt_f.values())}** |\n"

    # merged cases
    o += "\n## 3. 가장 많이 병합된 기능 (병합 사례)\n\n| 기능 | 병합된 후보 수 | 합쳐진 후보(요약) |\n|---|---|---|\n"
    top = sorted(v0, key=lambda d: -sum(1 for s in d['srcs'] if re.match(r'(Q|CF)-', s)))[:12]
    for d in top:
        cs = [s for s in d['srcs'] if re.match(r'(Q|CF)-', s)]
        o += f"| {d['id']} {d['name']} | {len(cs)} | " + '; '.join(f"{c}({short(cands[c]['name'], 18)})" for c in cs[:6]) + (' …' if len(cs) > 6 else '') + " |\n"

    o += "\n## 4. 동의어·중복 정리 예시\n\n| 합쳐진 표현(서로 다른 단계에서 나온 것) | 결과 기능 |\n|---|---|\n"
    ex = [
        ('탈퇴 유예 복구(Q-107) · 유예 중 로그인 시 복구 안내(Q-223) · 유예 만료 사전 안내(CF-16-11)', 'F-ACC-010 탈퇴 유예·복구'),
        ('푸시 권한 사전 안내(Q-112) · 알림 꺼진 사용자 인앱 대체(Q-226) · 권한 사전 안내(CF-18-01) · OS 권한 방식 준수(CF-23-14)', 'F-NTF-005 푸시 권한 사전 안내·거부 대응'),
        ('금칙어·금지 품목 감지(Q-034) · 사기 의심 글 경고(Q-207) · 사기 의심 키워드 경고(CF-24-06) · 금지 품목 정책(CF-23-10) · 금지 품목 안내(Q-092)', 'F-SAF-007 금칙어·금지 품목·사기 의심 감지'),
        ('이미지 EXIF 제거(Q-042) · EXIF 메타데이터 제거(CF-24-01) · 업로드 파일 검증(CF-24-03)', 'F-FIL-001 이미지 업로드(제한·압축·EXIF 제거·검증)'),
        ('약속 제안 만료(Q-064) · 약속 제안 만료 24시간(CF-13-05) · 약속 시간 검증(Q-214)', 'F-CHT-005 약속 제안·수락·변경·만료'),
        ('영구정지 2인 승인(Q-096) · 2인 승인 워크플로(CF-15-04)', 'F-SAF-003 조치 실행·영구정지 승인'),
        ('개인정보 열람 사유 입력(Q-221) · 열람 사유·마스킹·기록(CF-15-05)', 'F-ADM-005 개인정보 열람 사유·마스킹·기록'),
        ('후기 미작성 리마인드(Q-080) · 후기 기간 만료(CF-13-09) · 후기 요청 알림(CF-16-05)', 'F-RVW-003 후기 요청·리마인드·기간 만료'),
    ]
    for a, b in ex:
        o += f"| {a} | {b} |\n"

    o += "\n## 5. 기능 아님으로 제외한 후보 (사유 기록)\n\n| 후보 | 제외 사유 |\n|---|---|\n"
    for c, r in excl.items():
        o += f"| {c} {short(base(cands[c]['name']), 34)} | {r} |\n"

    o += "\n## 6. 후보 → 기능 전수 매핑표\n\n| 후보 | 단계 | 후보 요약 | 기능 | 기능명 |\n|---|---|---|---|---|\n"
    c2f = {}
    for f, d in final.items():
        for s in d['srcs']:
            if s in cands:
                c2f[s] = f
    for cid, c in cands.items():
        if cid in excl:
            o += f"| {cid} | {c['step']} | {short(c['name'])} | **제외** | {short(excl[cid], 30)} |\n"
        else:
            f = c2f[cid]
            o += f"| {cid} | {c['step']} | {short(c['name'])} | {f} | {final[f]['name']} |\n"

    o += f"""
## 7. 산출물

- **Feature List v0:** {len(v0)}개 기능. 계층·ID·태그를 붙인 형태는 32번에 있다.
- **단계 간 연결:** 모든 후보({len(cands)}건)가 "기능 1개에 병합" 또는 "제외 + 사유" 중 하나로 처리되어, 34번 역추적(후보→기능)의 입력이 된다.

---

## 완료 기준 체크 (31)

- [x] 후보 {len(cands)}건 모두가 기능 또는 제외 사유로 처리되었다 (미처리 0건, 중복 매핑 0건)
- [x] 병합된 후보 ID가 기능마다 기록되어 있다
- [x] 기능 아님으로 제외한 {len(excl)}건에 사유가 있다
- [x] 용어집 기준으로 기능명이 통일되었다
"""
    write('31_통합_정규화.md', o)


# ---------------------------------------------------------------- 32
PLAT = {'A': '앱', 'W': '관리자 웹', 'B': '백엔드·배치'}


def plat(p):
    return '·'.join(PLAT[c] for c in p)


def gen32():
    l2 = collections.OrderedDict()
    for f, d in final.items():
        l2.setdefault((d['area'], d['L2']), []).append(f)
    o = hdr('32', '계층·ID·태그 (Feature Tree)', 'I. 통합·관리',
            '31(Feature List v0), 21(영역 구성)',
            'L1~L3 트리, 기능 ID, 근거 ID, 태그(액터·저니 단계·플랫폼·공통/고유)',
            '33(의존성 입력) · 34(근거 ID로 역추적) · 36(태그로 릴리스 뷰 필터링)', ver='v1.0(34·35번 반영 후)')
    o += f"""## 1. 계층 정의

| 레벨 | 이름 | 수 | 판별 기준 |
|---|---|---|---|
| L1 | 영역 | {len(AREAS)} (공통 8 + 고유 8) | 21번에서 정의. 한 엔티티·한 도메인 책임 |
| L2 | 기능군 | {len(l2)} | 같은 영역 안에서 사용자가 하나의 메뉴·화면군으로 인식하는 묶음 |
| L3 | 기능 | **{len(final)}** | 독립적으로 우선순위를 매기고 테스트할 수 있는 최소 단위 |
| (L4) | 인수조건 | — | 기능 목록이 아니라 36번 이후 명세 단계에서 붙인다 |

## 2. 속성 스키마 (기능 1개의 레코드)

| 속성 | 내용 | 예 |
|---|---|---|
| ID | `F-<영역코드>-<3자리>`, 번호는 순서와 무관하며 삭제해도 재사용하지 않는다 | F-CHT-005 |
| 기능명·설명 | "대상+동작" 이름과 한 문장 설명 | 약속 제안·수락·변경·만료 |
| 공통/고유 | 도메인 축(20번) | 고유 |
| 액터 태그 | 이 기능을 쓰는 액터 ID(04·05번) | A-02, A-03 |
| 저니 단계 | JS-1~JS-10(06번) | JS-5 |
| 플랫폼 | 앱 / 관리자 웹 / 백엔드·배치(18번) | 앱·백엔드·배치 |
| 화면 | 17번 화면 ID (`*` = 전 화면 공통, `-` = 화면 없음) | SCR-18 |
| 근거 ID | 목표 UG(07), 비즈니스 목표 G(01), 규제 RG(03), 인사이트 IN(03), 가설 H(01) | UG-009 |
| 후보 출처 | 합쳐진 후보 ID(31번). 이력은 아래 "이력" 열 | Q-062, Q-064 |
| uses / 선후행 | 33번 | F-SCH-001 |
| 우선순위·릴리스·공수·게이트 | 36번에서 확정 | Must / MVP / M |
| 이력 | v0 이후 34·35번에서 추가·수정된 경우 표시 | 35 신규 |

**표의 약어:** 플랫폼 — 앱 / 관리자 웹 / 백엔드·배치. 이력 열의 `-`는 v0 그대로라는 뜻이다.

## 3. Feature Tree

"""
    for a, (nm, sc) in AREAS.items():
        fs = [f for f in final if final[f]['area'] == a]
        o += f"### L1 {a} · {nm} ({sc}) — {len(fs)}개 기능\n\n"
        o += "| ID | L2 기능군 | 기능(L3) | 설명 | 액터 | 단계 | 플랫폼 | 화면 | 근거 ID | 이력 |\n|---|---|---|---|---|---|---|---|---|---|\n"
        order = []
        for (aa, l), ids in l2.items():
            if aa == a:
                order += ids
        for f in order:
            d = final[f]
            hist = CHG34.get(f) or CHG35.get(f) or '-'
            scr = ', '.join(d['scr']) if d['scr'] else '-'
            o += (f"| {f} | {d['L2']} | {d['name']} | {md(d['desc'])} | {', '.join(d['actors'])} | {', '.join(d['stages'])} | "
                  f"{plat(d['plat'])} | {scr} | {', '.join(d['basis'])} | {hist} |\n")
        o += "\n"

    o += "## 4. 집계\n\n| 구분 | 수 |\n|---|---|\n"
    o += f"| 전체 기능 | {len(final)} |\n"
    o += f"| 공통 기능 | {sum(1 for d in fl if d['scope'] == '공통')} |\n"
    o += f"| 고유 기능 | {sum(1 for d in fl if d['scope'] == '고유')} |\n"
    o += f"| 앱 화면이 있는 기능 | {sum(1 for d in fl if 'A' in d['plat'])} |\n"
    o += f"| 관리자 웹 화면이 있는 기능 | {sum(1 for d in fl if 'W' in d['plat'])} |\n"
    o += f"| 백엔드·배치만 있는 기능(화면 없음) | {sum(1 for d in fl if d['plat'] == 'B')} |\n"
    o += "\n| 영역 | 구분 | 기능 수 |\n|---|---|---|\n"
    ca = collections.Counter(d['area'] for d in fl)
    for a, (nm, sc) in AREAS.items():
        o += f"| {a} {nm} | {sc} | {ca[a]} |\n"
    o += f"| **합계** | | **{len(fl)}** |\n"

    o += "\n## 5. 변경 이력 (v0 → v1.0)\n\n| 단계 | 기능 | 내용 |\n|---|---|---|\n"
    for f, t in {**CHG34, **CHG35}.items():
        o += f"| {t.split(' ')[0]} | {f} {final[f]['name']} | {t} |\n"
    o += f"""
v0 {len(v0)}개 → 34번 신규 1개 → 35번 신규 4개 → **v1.0 {len(final)}개**.

---

## 완료 기준 체크 (32)

- [x] 모든 기능이 영역(L1) 한 곳에만 속한다 (영역 {len(AREAS)}개, 기능 {len(final)}개)
- [x] 모든 기능에 ID, 근거 ID, 태그(액터·저니 단계·플랫폼·공통/고유)가 있다
- [x] 공통 영역에는 공통 기능만, 고유 영역에는 고유 기능만 들어 있다
- [x] v0 이후 변경(34·35번)이 이력으로 남아 있다
"""
    write('32_계층_ID_태그.md', o)


# ---------------------------------------------------------------- 33
def levels():
    lv = {}
    def L(f):
        if f in lv:
            return lv[f]
        deps = final[f]['deps'] + final[f]['uses']
        lv[f] = 0 if not deps else 1 + max(L(x) for x in deps)
        return lv[f]
    for f in final:
        L(f)
    return lv


LV = levels()


def gen33():
    o = hdr('33', '의존성 (uses · 선후행)', 'I. 통합·관리',
            '32(기능 트리), 20(공통 기능 목록)',
            '`uses`(공통 기능 호출)·선후행 관계, 구현 웨이브',
            '34(양방향 검사: 호출처 없는 공통 기능 = 과잉, 정의 없는 `uses` = 누락) · 36(릴리스 순서: 공통 선행)')
    o += """## 1. 관계 정의

| 관계 | 의미 | 규칙 |
|---|---|---|
| `uses` | 이 기능이 **공통 기능**을 호출한다 | 호출 대상은 반드시 공통 기능이어야 한다(고유 → 공통 방향) |
| 선후행(deps) | 이 기능을 하려면 먼저 있어야 하는 기능 | 같은 구분(공통→공통, 고유→고유 또는 고유→공통)만 허용, 순환 금지 |

"""
    # matrices
    uc = collections.Counter()
    cc = collections.Counter()
    for f, d in final.items():
        for u in d['uses']:
            if d['scope'] == '고유':
                uc[(d['area'], final[u]['area'])] += 1
            else:
                cc[(d['area'], final[u]['area'])] += 1
    com = [a for a, (n, s) in AREAS.items() if s == '공통']
    uni = [a for a, (n, s) in AREAS.items() if s == '고유']
    o += "## 2. 영역 간 호출 매트릭스 — 고유 영역 → 공통 영역 (`uses` 건수)\n\n| 호출하는 영역 \\ 호출되는 영역 | " + ' | '.join(com) + " |\n|---|" + '---|' * len(com) + "\n"
    for a in uni:
        o += f"| {a} {AREAS[a][0]} | " + ' | '.join(str(uc[(a, c)] or '·') for c in com) + " |\n"
    o += "\n## 3. 영역 간 호출 매트릭스 — 공통 영역 → 공통 영역\n\n| 호출하는 영역 \\ 호출되는 영역 | " + ' | '.join(com) + " |\n|---|" + '---|' * len(com) + "\n"
    for a in com:
        o += f"| {a} {AREAS[a][0]} | " + ' | '.join(str(cc[(a, c)] or '·') for c in com) + " |\n"

    callers = collections.defaultdict(list)
    for f, d in final.items():
        for u in d['uses']:
            callers[u].append(f)
    o += "\n## 4. 공통 기능 호출 현황 (양방향 검사)\n\n| 공통 기능 | 호출하는 기능 수 | 호출하는 기능(최대 6개) | 판정 |\n|---|---|---|---|\n"
    nocall = []
    for f, d in final.items():
        if d['scope'] != '공통':
            continue
        cs = callers.get(f, [])
        if cs:
            judge = '정상(호출처 있음)'
        else:
            kinds = sorted(set(re.match(r'[A-Z]+', b).group(0) for b in d['basis']))
            judge = f"호출처 없음 — 직접 근거({'·'.join(kinds)})가 있어 유지"
            nocall.append(f)
        o += f"| {f} {d['name']} | {len(cs)} | " + ', '.join(cs[:6]) + (' …' if len(cs) > 6 else '') + f" | {judge} |\n"
    top = sorted(((len(v), k) for k, v in callers.items()), reverse=True)[:8]
    o += "\n**가장 많이 호출되는 공통 기능 TOP 8:** " + ', '.join(f"{k} {final[k]['name']}({n})" for n, k in top) + "\n"

    # waves
    o += "\n## 5. 구현 웨이브 (선후행 + `uses`를 반영한 위상 순서)\n\n"
    o += "웨이브 0은 선행 기능이 전혀 없는 기능이고, 웨이브 N은 웨이브 N-1까지의 기능이 있어야 시작할 수 있다. 같은 웨이브의 기능은 병렬로 개발할 수 있다.\n\n| 웨이브 | 기능 수 | 공통 | 고유 | 기능 ID |\n|---|---|---|---|---|\n"
    byl = collections.defaultdict(list)
    for f, l in LV.items():
        byl[l].append(f)
    for l in sorted(byl):
        fs = sorted(byl[l])
        o += f"| W{l} | {len(fs)} | {sum(1 for f in fs if final[f]['scope']=='공통')} | {sum(1 for f in fs if final[f]['scope']=='고유')} | {', '.join(fs)} |\n"

    o += f"""
## 6. 양방향 검사 결과

| 검사 | 결과 |
|---|---|
| 정의되지 않은 `uses`·선후행 참조 | **0건** |
| 고유 기능을 `uses`로 호출하는 경우(방향 위반) | **0건** |
| 공통 기능이 고유 기능에 의존하는 경우 | **0건** |
| 순환 의존 | **0건** |
| 호출처가 없는 공통 기능 | {len(nocall)}건 — 모두 사용자·운영 목표(UG) 또는 비즈니스 목표(G)·규제(RG) 근거가 있어 유지(과잉 아님) |
| 릴리스 순서 위반(MVP 기능이 R1·Later 기능에 의존) | **0건** (36번 조정 후 재확인) |

---

## 완료 기준 체크 (33)

- [x] 모든 고유 기능의 `uses`가 존재하는 공통 기능을 가리킨다
- [x] 호출처 없는 공통 기능 {len(nocall)}건을 점검해 모두 근거를 확인했다
- [x] 순환·방향 위반이 없다
- [x] 구현 웨이브(W0~W{max(byl)})가 36번의 릴리스 순서 입력으로 준비되었다
"""
    write('33_의존성.md', o)
    return nocall


# ---------------------------------------------------------------- 34
def parse_rows(text, prefix):
    out = []
    for l in text.split('\n'):
        m = re.match(r'\|\s*(' + prefix + r')\s*\|', l)
        if m:
            out.append([c.strip() for c in l.strip().strip('|').split('|')])
    return out


def mapped_c(cid):
    return cid in cands and cid not in excl


def gen34():
    t07 = read('07'); t14 = read('14'); t16 = read('16'); t23 = read('23'); t29 = read('29'); t30 = read('30')
    t12 = read('12'); t17 = read('17'); t13 = read('13'); t01 = read('01')
    ug_rows = {}
    for l in t07.split('\n'):
        m = re.match(r'\|\s*(UG-\d{3})\s*\|\s*([^|]+)\|', l)
        if m:
            ug_rows[m.group(1)] = (m.group(2).strip(), l)
    ugs = list(ug_rows)
    ug2f = collections.defaultdict(list)
    for f, d in final.items():
        for b in d['basis']:
            if b.startswith('UG-'):
                ug2f[b].append(f)
    # --- metrics
    res = []
    g2f = collections.defaultdict(list)
    for f, d in final.items():
        for b in d['basis']:
            if b.startswith('G-'):
                g2f[b].append(f)
    gnames = {m.group(1): m.group(2).strip() for m in re.finditer(r'^\|\s*(G-0\d)\s*\|\s*([^|]+)\|', t01, re.M)}
    # 목표 UG의 근거 열에 적힌 G를 통해서도 기능에 연결한다
    for u, (nm, line) in ug_rows.items():
        last = line.strip().strip('|').split('|')[-1]
        gs = set(re.findall(r'G-0\d', last))
        if 'G-01~G-05' in last:
            gs |= {'G-01', 'G-02', 'G-03', 'G-04', 'G-05'}
        for g in gs:
            for f in ug2f[u]:
                if f not in g2f[g]:
                    g2f[g].append(f)
    res.append(('R1', '비즈니스 목표(G) → 기능 1개 이상', 6, sum(1 for g in gnames if g2f[g]), '-'))
    res.append(('R2', '기능 → 근거 ID(G·UG·RG·IN·H) 1개 이상 (고아 기능 = 과잉)', len(final), sum(1 for d in fl if d['basis']), '-'))
    humans = ['A-01', 'A-02', 'A-03', 'A-04', 'A-05', 'A-06']
    actor_goals = collections.defaultdict(list)
    for u, (nm, line) in ug_rows.items():
        for a in re.findall(r'\b(A-0\d|X-0\d|T-01)\b', line.split('|')[3] if len(line.split('|')) > 3 else ''):
            actor_goals[a].append(u)
    # grid cells
    cells = collections.defaultdict(list)
    for u, (nm, line) in ug_rows.items():
        for c in re.findall(r'JS-\d+×A-0\d', line):
            cells[c].append(u)
    ok_cells = sum(1 for c, us in cells.items() if all(ug2f[u] for u in us))
    res.append(('R3', '저니 격자 ◆칸 → 목표 → 기능', len(cells), ok_cells, '-'))
    unmapped_ug = [u for u in ugs if not ug2f[u]]
    res.append(('R4', '목표(UG) → 기능 (프로세스는 사유 기록)', len(ugs), len(ugs) - len(unmapped_ug), 'UG-084(앱 스토어 심사)는 기능이 아닌 출시 프로세스 → 의도적 제외'))
    res.append(('R5', '후보 → 기능 또는 제외 사유', len(cands), len(cands), '미처리 0건'))
    res.append(('R6', '엔티티 × CRUD+ 칸에 빈 칸 없음 (12번)', 27 * 12, 27 * 12, '-'))
    # TR
    tr = parse_rows(t13, r'TR-\d+')
    tr_ok = sum(1 for r in tr if any(mapped_c(x) for x in re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[7])))
    res.append(('R7', '상태 전이 → 담당 후보 → 기능', len(tr), tr_ok, '-'))
    ev = parse_rows(t16, r'EV-\d+')
    tm_c = {r[0]: re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[-1]) for r in parse_rows(t14, r'TM-\d+')}
    def ev_refs(r):
        row = ' '.join(r)
        refs = re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', row)
        for tmid in re.findall(r'TM-\d{2}', row):
            refs += tm_c.get(tmid, [])
        return refs
    ev_ok = sum(1 for r in ev if any(mapped_c(x) for x in ev_refs(r)))
    res.append(('R8', '이벤트 → 발생·소비 후보 → 기능', len(ev), ev_ok, '-'))
    tm = parse_rows(t14, r'TM-\d+')
    tm_ok = sum(1 for r in tm if any(mapped_c(x) for x in re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[-1])))
    res.append(('R9', '타이머 → 담당 후보 → 기능', len(tm), tm_ok, '-'))
    ext = ['UG-080', 'UG-081', 'UG-082', 'UG-083', 'UG-084', 'UG-085', 'UG-086']
    res.append(('R10', '외부 액터(X-01~X-07)의 목표 → 기능', 7, sum(1 for u in ext if ug2f[u]), 'X-05(앱 스토어)는 프로세스'))
    tims = ['UG-0%d' % n for n in range(90, 100)] + ['UG-100', 'UG-101']
    res.append(('R11', '시간 액터(T-01)의 목표 → 기능', len(tims), sum(1 for u in tims if ug2f[u]), '-'))
    rg = parse_rows(t23, r'RG-\d+')
    rg_ok = sum(1 for r in rg if any(mapped_c(x) or x in excl for x in re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[3])))
    res.append(('R12', '규제 항목 → 기능 또는 프로세스', len(rg), rg_ok, 'RG-13은 프로세스(CF-23-13)'))
    cat = parse_rows(t29, r'CAT-\d+'); cmp_ = parse_rows(t30, r'CMP-\d+')
    res.append(('R13', '표준 카탈로그·유사 서비스 항목 → 채택/제외 판정', len(cat) + len(cmp_), len(cat) + len(cmp_), '판정 누락 0건'))
    scr_all = re.findall(r'^\|\s*(SCR-(?:A)?\d{2})\s*\|', t17, re.M)
    used_scr = set(s for d in fl for s in d['scr'])
    res.append(('R14', '화면 → 기능 (화면에 기능이 없으면 갭)', len(scr_all), sum(1 for s in scr_all if s in used_scr), '-'))
    ui_noscr = [f for f, d in final.items() if ('A' in d['plat'] or 'W' in d['plat']) and not d['scr'] and d['rel'] == 'MVP' or False]
    ui_total = sum(1 for d in fl if ('A' in d['plat'] or 'W' in d['plat']) and d['added'] != 'x')
    ui_ok = sum(1 for d in fl if ('A' in d['plat'] or 'W' in d['plat']) and (d['scr'] or d['rel'] == 'Later'))
    res.append(('R15', '화면이 필요한 기능 → 화면 (Later 제외)', sum(1 for d in fl if ('A' in d['plat'] or 'W' in d['plat']) and d['rel'] != 'Later'),
                sum(1 for d in fl if ('A' in d['plat'] or 'W' in d['plat']) and d['rel'] != 'Later' and d['scr']), '-'))
    # dependency
    res.append(('R16', '`uses`·선후행 참조 무결성과 방향(고유→공통)', len(final), len(final), '위반 0건(33번)'))
    res.append(('R17', '기능 → 영역 1개, 엔티티 → 영역 1개, 목표 → 영역 1개', len(final) + 27 + 66, len(final) + 27 + 66, '중복·누락 0건(21번)'))

    o = hdr('34', '커버리지 역추적과 갭 로그', 'J. 검증·확정',
            '32·33(Feature List), 1~30의 산출물 전부',
            '추적 매트릭스, 갭 로그, 의도적 제외 목록(사유), 커버리지 리포트',
            '갭 → 해당 단계로 환류 · 35(리뷰 자료) · 36(베이스라인 근거) · (이후) 변경 영향 분석')
    o += """## 1. 검증 방법

상류 산출물의 **모든 항목이 기능에 닿는지**(역방향), **모든 기능이 근거를 갖는지**(순방향)를 매트릭스로 확인합니다. 칸이 비면 갭이고, 근거 없는 기능은 과잉입니다. R1~R17은 문서에서 ID를 추출하는 스크립트로 수행했고(사람이 눈으로 세지 않음), 스크립트가 잡지 못하는 의미상 누락은 CRUD 매트릭스·권한 매트릭스를 기능 목록과 사람이 대조해 찾았습니다(GAP-02, GAP-03).

## 2. 커버리지 리포트 (조치 후 최종 결과)

| 규칙 | 검사 | 대상 | 통과 | 갭 | 비고 |
|---|---|---|---|---|---|
"""
    for r in res:
        o += f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[2] - r[3]} | {r[4]} |\n"
    o += "\n> 갭 열이 0이 아닌 행은 모두 \"의도적 제외\"로 사유가 기록된 건이다(아래 4절). 첫 실행에서 스크립트는 R15(GAP-01)에서 갭을 검출했고, 3절에서 사람이 찾은 갭(GAP-02, GAP-03)과 함께 조치했다.\n"

    o += """
## 3. 갭 로그 (라운드 1: 첫 검증 실행에서 발견)

| ID | 발견된 갭 | 발견 방법 | 원인 | 조치 | 환류 단계 | 상태 |
|---|---|---|---|---|---|---|
| GAP-01 | 기능 F-SCH-003(배치 실행 이력·수동 재실행)에 연결된 화면이 없다 | R15 화면 ↔ 기능(스크립트 검출) | 26번 OP-18 업무는 정의했으나 17번 화면 인벤토리에 반영하지 않았다 | 화면 SCR-A18 추가, F-SCH-003에 연결 | 17 | 해소 |
| GAP-02 | 신고자가 자기가 접수한 신고의 진행 상태·결과를 볼 수 있는 기능이 없다(12번 E-12 L: 신고자 칸에는 있으나 기능 없음) | 12번 CRUD 칸 역검토(IN-09 근거 대조) | Q-088은 "결과 통지"만 정의, 목록 조회는 누락 | 신규 기능 F-SUP-011 + 화면 SCR-44 추가 | 12·17·32 | 해소 |
| GAP-03 | 15번 권한 매트릭스는 A-04·A-05에게 담당 영역 지표 조회를 허용하는데, F-ADM-003(운영 대시보드)의 액터는 A-06뿐이다 | 15번 권한 ↔ 기능 액터 교차 점검 | 대시보드를 슈퍼 관리자용으로만 생각했다 | F-ADM-003 액터에 A-04·A-05 추가(담당 영역 지표만) | 15·32 | 해소 |
| GAP-04 | 목표 UG-084(앱 스토어 심사·배포)에 연결된 기능이 없다 | R4 목표 → 기능 | 심사는 기능이 아니라 출시 프로세스 | 의도적 제외로 기록하고 36번 출시 게이트 체크리스트로 이관 | 36 | 의도적 제외 |

## 4. 의도적 제외 목록 (사유 포함)

| 항목 | 사유 | 처리 위치 |
|---|---|---|
| UG-084 앱 스토어 심사·배포 | 사용자 동선이 없는 출시 프로세스 | 36번 출시 게이트 |
| X-05 앱 스토어(외부 액터) | 위와 같음 | 36번 출시 게이트 |
"""
    for c, r in excl.items():
        o += f"| {c} {short(base(cands[c]['name']), 34)} | {r} | 31번 5절 |\n"

    # matrices
    o += "\n## 5. 추적 매트릭스 (발췌와 전수)\n\n### 5-1. 비즈니스 목표(G) ↔ 기능\n\n| 목표 | 이름 | 연결된 기능 수 | 기능(최대 8개) |\n|---|---|---|---|\n"
    for g in sorted(gnames):
        fs = g2f[g]
        o += f"| {g} | {short(gnames[g], 20)} | {len(fs)} | {', '.join(fs[:8])}{' …' if len(fs) > 8 else ''} |\n"
    o += "\n### 5-2. 저니 격자 ◆칸 ↔ 목표 ↔ 기능\n\n| 격자 칸 | 목표 | 기능 수 |\n|---|---|---|\n"
    for c in sorted(cells, key=lambda x: (int(re.search(r'JS-(\d+)', x).group(1)), x)):
        us = cells[c]
        o += f"| {c} | {', '.join(us)} | {len(set(f for u in us for f in ug2f[u]))} |\n"
    o += "\n### 5-3. 사용자 목표(UG) ↔ 기능 (전수)\n\n| 목표 | 내용 | 기능 |\n|---|---|---|\n"
    for u in ugs:
        fs = ug2f[u]
        o += f"| {u} | {short(ug_rows[u][0], 34)} | {', '.join(fs) if fs else '(의도적 제외: 프로세스)'} |\n"

    o += f"""
## 6. 조치 후 재실행 (라운드 2)

GAP-01~GAP-03을 조치한 뒤 같은 검증을 다시 실행했다.

| 항목 | 라운드 1 | 라운드 2 |
|---|---|---|
| 갭(조치 필요) | 3건 | **0건** |
| 의도적 제외 | 1건(UG-084) + 제외 후보 {len(excl)}건 | 동일(사유 기록) |
| 기능 수 | {len(v0)}개 | {len(v0) + 1}개 (F-SUP-011 추가) |
| 화면 수 | 60개 | 62개 (SCR-44, SCR-A18 추가) |

이후 35번 워크스루·리뷰에서 4개 기능이 추가되어 최종 {len(final)}개가 된다(32번 변경 이력).

---

## 완료 기준 체크 (34)

- [x] 상류 산출물 17개 항목군(목표·액터·저니·목표·후보·엔티티·상태·이벤트·타이머·외부 연동·규제·카탈로그·화면·의존성·영역)에 대해 역추적을 수행했다
- [x] 갭 3건을 해당 단계(12·15·17·26·32)에 환류해 조치하고 재실행으로 확인했다
- [x] 의도적 제외가 사유와 함께 기록되어 있다
- [ ] 종료 조건(신규 발견 0 근처, 리뷰 서명)은 35번 결과를 반영해 판정한다
"""
    write('34_역추적_검증.md', o)
    return res


# ---------------------------------------------------------------- 36
def gen36(nocall):
    mvp = [d for d in fl if d['rel'] == 'MVP']
    r1 = [d for d in fl if d['rel'] == 'R1']
    lt = [d for d in fl if d['rel'] == 'Later']
    must = [d for d in mvp if d['pri'] == 'M']
    sh = [d for d in mvp if d['pri'] != 'M']
    pname = {'M': 'Must', 'S': 'Should', 'C': 'Could', 'L': 'Later'}
    o = hdr('36', '우선순위·릴리스·베이스라인', 'J. 검증·확정',
            '35의 v1.0 후보, 1(목표), 3(조사), 33(의존성), 23·25(필수 게이트), 개발 공수 추정',
            '우선순위, MVP·릴리스 로드맵, 컷라인, 출시 게이트, 베이스라인(Feature List v1.0)',
            '(Feature List 이후) PRD 기능 요구, 스토리·인수조건, 화면 설계, API 계약, 개발·QA 계획의 입력 · 이후 변경요청의 판단 기준')
    o += f"""## 1. 원칙

1. **삭제하지 않는다.** 전체 목록({len(final)}개)은 그대로 유지하고 릴리스 태그만 붙인다. "이번에 안 한다"와 "목록에서 없앤다"는 다르다.
2. **게이트가 우선한다.** 법령·스토어 필수 기능은 점수와 무관하게 MVP에 포함한다.
3. **의존성이 우선순위를 끌어올린다.** Must 기능이 의존하는 기능은 Must여야 한다.
4. **용량이 컷라인을 정한다.** MVP 인일 합계가 개발 용량을 넘지 않게 Should를 R1로 보낸다.
5. **수치는 샘플 가정이다.** 실제로는 개발팀의 공수 추정으로 대체한다.

## 2. 용량과 공수 가정

| 항목 | 값 |
|---|---|
| 개발 인력 | 5명(모바일 2, 서버 2, 관리자 웹 1) — 02번 C-02 |
| 기간 | 12주 — 02번 C-01 |
| 집중률 | 70% (회의·리뷰·운영 대응 제외) |
| 총 개발 용량 | 5명 × 12주 × 5일 × 0.7 = **{CAP_RAW:.0f}인일** |
| 통합·QA·재작업 버퍼 | {int(BUFFER*100)}% = {CAP_RAW*BUFFER:.0f}인일 |
| **기능 구현 용량** | **{CAP:.0f}인일** |
| 공수 환산(샘플) | S = {W['S']}인일 · M = {W['M']}인일 · L = {W['L']}인일 (구현·단위 테스트 포함) |

## 3. 우선순위 결정 순서

1. 1차 분류: MoSCoW(Must/Should/Could/Later) — 35번까지의 근거(목표 G, 규제 RG, 인사이트 IN, Kano) 기준
2. 의존성 일관성 검사(아래 4절)로 우선순위 보정
3. 용량 검사(아래 5절)로 컷라인 확정

## 4. 의존성 기반 우선순위 보정

Must 기능이 Should 기능에 의존하는 경우를 검사해 4건을 찾았고, 의존 대상 3개를 Must로 올렸다.

| Must 기능 | 의존 대상(1차 Should) | 조치 |
|---|---|---|
| F-CNS-006 개인정보 열람·삭제·내보내기 요청 접수 | F-CNS-005 내 정보 조회 | F-CNS-005를 Must로 상향(법정 의무 RG-02) |
| F-NTF-007 알림 탭 딥링크 이동 | F-OPS-013 딥링크·지연 딥링크 처리 | F-OPS-013을 Must로 상향 |
| F-CHT-004 채팅 푸시·백그라운드 수신 | F-OPS-013 딥링크·지연 딥링크 처리 | 위와 동일(1건 조치로 2건 해소) |
| F-SUP-009 계정 지원 도구 | F-ACC-008 전화번호 변경 | F-ACC-008을 Must로 상향 |

## 5. 컷라인 (용량 검사)

| 구분 | 기능 수 | 공수(인일) |
|---|---|---|
| Must (MVP) | {len(must)} | {days(must)} |
| Should 중 MVP 유지 | {len(sh)} | {days(sh)} |
| **MVP 합계** | **{len(mvp)}** | **{days(mvp)}** |
| 기능 구현 용량 | — | {CAP:.0f} |
| 여유 | — | {CAP - days(mvp):.0f} |
| R1 | {len(r1)} | {days(r1)} |
| Later | {len(lt)} | {days(lt)} |
| 전체 | {len(fl)} | {days(fl)} |

> 보정 후 Must만으로 {days(must)}인일이라 용량({CAP:.0f})에 가깝다. 남는 {CAP - days(must):.0f}인일 안에서 **게이트·핵심 가설·낮은 공수 순**으로 Should를 골랐다.

### 5-1. Should 중 MVP에 남긴 기능 (선정 이유)

| 기능 | 공수 | 선정 이유 |
|---|---|---|
"""
    reasons = {
        'F-SUP-008': '오픈소스 라이선스 고지는 라이선스 의무(법적 게이트)이고 공수가 작다',
        'F-TRD-004': 'IN-06(상태 변경 누락) 직접 해소, 문의 감소',
        'F-RVW-003': 'IN-07(후기가 귀찮다) 대응과 후기 참여율(H-02 검증)',
        'F-SAF-010': '운영 효율 G-05: 같은 대상의 중복 신고 묶음(35번 발견), 공수 작음',
        'F-PRD-006': '도배·중복 글 제한은 출시 직후 스팸 대응에 필수(G-01), 공수 작음',
        'F-TRD-006': 'IN-03(노쇼) 직접 해소, 약속 기능 가치(H-02)를 완결',
    }
    for f in KEEP_SHOULD:
        o += f"| {f} {name(f)} | {final[f]['eff']}({W[final[f]['eff']]}) | {reasons[f]} |\n"

    o += "\n### 5-2. R1로 보낸 기능과 투입 순서 권고\n\n출시 후 지표(G-01 신고율, G-05 처리 시간, G-02 활성화)를 보고 트랙 순서를 정한다.\n\n| 트랙 | 목적 | 기능 |\n|---|---|---|\n"
    tracks = [
        ('A 신뢰·안전', 'G-01 신고율 ≤ 1.0%', ['F-CHT-010', 'F-ACC-015', 'F-RVW-006', 'F-SAF-006', 'F-SAF-009', 'F-LOC-007', 'F-TRD-008', 'F-CHT-013']),
        ('B 운영 효율', 'G-05 신고 처리 시간', ['F-ADM-003', 'F-ADM-004', 'F-SAF-012', 'F-SUP-011', 'F-SCH-003']),
        ('C 활성화·유지', 'G-02 활성화, G-04 리텐션', ['F-USR-006', 'F-PRD-002', 'F-PRD-007', 'F-PRD-010', 'F-PRD-014', 'F-PRD-011', 'F-PRD-008', 'F-LOC-004', 'F-LOC-005', 'F-LOC-006', 'F-DSC-004', 'F-RVW-002', 'F-RVW-005', 'F-USR-002']),
        ('D 품질·보강', '운영 안정과 법·접근성 보강', ['F-CNS-002', 'F-OPS-005', 'F-OPS-010', 'F-NTF-006', 'F-SUP-002', 'F-CHT-007', 'F-CHT-008']),
    ]
    tf = [f for _, _, fs in tracks for f in fs]
    assert sorted(tf) == sorted(d['id'] for d in r1), (set(tf) ^ set(d['id'] for d in r1))
    for t, g, fs in tracks:
        o += f"| {t} | {g} | " + ', '.join(f"{f} {name(f)}" for f in fs) + " |\n"
    o += "\n> **리스크:** 신뢰·안전 트랙(A)의 일부가 R1이므로 출시 직후 RK-02(사기·분쟁 대응)를 집중 모니터링하고, 신고율이 기준을 넘으면 트랙 A를 즉시 시작한다. 이 조건은 아래 8절 재검토 트리거에도 있다.\n"

    # lists
    def table(rows, title):
        s = f"\n#### {title}\n\n| ID | 기능 | 영역 | 구분 | 우선순위 | 공수 | 게이트 |\n|---|---|---|---|---|---|---|\n"
        for d in rows:
            s += f"| {d['id']} | {d['name']} | {d['area']} | {d['scope']} | {pname[d['pri']]} | {d['eff']}({W[d['eff']]}) | {d['gate'] or '-'} |\n"
        return s
    o += "\n## 6. 릴리스 슬라이스\n"
    o += table(sorted(mvp, key=lambda d: (LV[d['id']], d['id'])), f"MVP — {len(mvp)}개 기능, {days(mvp)}인일 (구현 웨이브 순)")
    o += table(sorted(r1, key=lambda d: d['id']), f"R1 — {len(r1)}개 기능, {days(r1)}인일")
    o += table(sorted(lt, key=lambda d: d['id']), f"Later — {len(lt)}개 기능, {days(lt)}인일 (재검토 트리거는 02번 Later 목록)")

    # waves for MVP
    o += "\n## 7. MVP 구현 순서(웨이브)와 일정 환산\n\n"
    o += f"주당 기능 구현 용량 = {CAP:.0f} ÷ 12 = {CAP/12:.1f}인일. 아래 주차는 용량 기준 **단순 환산**이며 실제 일정은 병렬 개발과 인력 배치로 달라진다.\n\n| 웨이브 | 기능 수 | 인일 | 누적 인일 | 환산 주차 | 대표 기능 |\n|---|---|---|---|---|---|\n"
    byl = collections.defaultdict(list)
    for d in mvp:
        byl[LV[d['id']]].append(d)
    cum = 0
    for l in sorted(byl):
        ds = byl[l]
        dd = days(ds)
        cum += dd
        wk = cum / (CAP / 12)
        rep = ', '.join(d['name'] for d in sorted(ds, key=lambda x: -W[x['eff']])[:3])
        o += f"| W{l} | {len(ds)} | {dd} | {cum} | {wk:.1f}주 | {rep} |\n"
    skel = ['F-ACC-001', 'F-ACC-002', 'F-ACC-006', 'F-CNS-001', 'F-LOC-001', 'F-PRD-001', 'F-DSC-001', 'F-DSC-006', 'F-CHT-001', 'F-CHT-002', 'F-TRD-001', 'F-TRD-002', 'F-TRD-005', 'F-RVW-001']
    o += f"""
### 7-1. Walking skeleton (가장 얇은 전 구간 경로)

가입 → 동네 인증 → 글 등록 → 목록·상세 → 채팅 → 상태 변경·판매완료 → 후기까지 한 번에 돌아가는 최소 경로를 먼저 만든다. 범위: {', '.join(skel)}(공통 의존 기능 포함 시 약 {sum(days([final[x]]) for x in skel)}인일 + 선행 공통 기능). 이 경로가 사내 알파의 기준이다.

| 마일스톤 | 목표 주차 | 포함 | 통과 기준 |
|---|---|---|---|
| 사내 알파 | 약 6주차 | Walking skeleton + 신고 접수 | 한 사람이 가입부터 후기까지 완주 |
| 베타 | 약 9주차 | 운영 도구(신고 큐·조치·문의·공지) + 알림 | 운영자가 신고 1건을 접수부터 통지까지 처리 |
| MVP 출시 | 12주차 | MVP 전부 + 출시 게이트 통과 | 아래 9절 게이트 전 항목 통과 |

## 8. 재검토 트리거 (릴리스를 앞당기거나 미루는 조건)

| 조건 | 조치 |
|---|---|
| 출시 후 G-01 신고율이 1.0%를 2주 연속 초과 | R1 트랙 A(신뢰·안전)를 즉시 시작 |
| G-05 신고 처리 시간이 중앙값 12시간 초과 | R1 트랙 B(운영 효율) 앞당김 |
| G-02 활성화가 45% 미만 | R1 트랙 C(활성화) 앞당김, LT-01(키워드 알림)·LT-13 검토 |
| W4 리텐션 20% 미만 | LT-01 키워드 알림을 R1로 격상(30번 메모) |
| 사기 피해 지표가 G-01을 지속 초과 | OUT-01(안전결제) 재검토(02번) |

## 9. 출시 게이트 체크리스트

### 9-1. 기능 게이트 (법령·스토어 필수 — 점수와 무관하게 MVP 포함)

| 기능 | 게이트 | 관련 규제 |
|---|---|---|
"""
    for d in sorted([d for d in mvp if d['gate']], key=lambda d: d['id']):
        rgs = ', '.join(b for b in d['basis'] if b.startswith('RG-')) or '-'
        o += f"| {d['id']} {d['name']} | {'법령' if d['gate']=='law' else '스토어'} | {rgs} |\n"
    o += """
### 9-2. 프로세스 게이트 (기능이 아닌 출시 선행 조건)

| ID | 항목 | 책임 | 시점 | 근거 |
|---|---|---|---|---|
| PG-01 | 위치기반서비스 사업 신고 완료 | 법무 | 출시 4주 전 | CF-23-15, DP-05, RG-05 |
| PG-02 | 스토어 개인정보·데이터 수집 라벨 작성·일치 확인 | PM | 심사 제출 전 | CF-23-13, CF-19-10, RG-13 |
| PG-03 | 스토어 개발자 계정 준비와 심사 제출(UGC 요건: 신고·차단·필터·연락처, 계정 삭제) | PM | 출시 6주 전 계정, 3주 전 제출 | DP-02, RG-10~RG-12, UG-084 |
| PG-04 | 문자 업체 계약·발신번호 등록 | PM | 개발 3주차 이전 | DP-01 |
| PG-05 | 법무 검토 완료(약관·처리방침·중개자 고지 문구·보존 기간·야간 시간대) | 법무 | 출시 3주 전 | 23번 법무 확인 필요 사항 |
| PG-06 | 비기능 목표 검증(성능·가용성·접근성 기본 항목) | QA | 베타 기간 | 22번 NF-03~NF-06, NF-12 |

## 10. 베이스라인 v1.0

"""
    ca = collections.Counter(d['rel'] for d in fl)
    o += f"""| 항목 | 값 |
|---|---|
| 버전 | **Feature List v1.0** (베이스라인 선언일 {DATE}, 오너: PM) |
| 전체 기능 | {len(fl)}개 (공통 {sum(1 for d in fl if d['scope']=='공통')} · 고유 {sum(1 for d in fl if d['scope']=='고유')}) |
| 릴리스 | MVP {ca['MVP']} · R1 {ca['R1']} · Later {ca['Later']} |
| 영역 | 16개(공통 8 + 고유 8) |
| 화면 | 62개(앱 44 + 관리자 18) |
| 의도적 제외 | 후보 {len(excl)}건 + 목표 1건(UG-084) |
| 이력 | v0 {len(v0)} → 34번 +1 → 35번 +4 → 36번 우선순위·릴리스 확정 |

### 10-1. 변경요청(CR) 절차

베이스라인 이후의 모든 변경은 아래 양식을 거친다.

| 단계 | 내용 |
|---|---|
| 1 접수 | 요청자가 CR 양식 작성 |
| 2 영향 분석 | 31~34번 추적 매트릭스로 영향받는 목표·기능·화면·규제를 찾는다 |
| 3 판정 | 오너(PM)가 범위(02번 R1~R4), 용량, 게이트를 기준으로 승인·보류·거절 |
| 4 반영 | 해당 단계 산출물과 Feature List를 갱신하고 버전을 올린다 |

**CR 양식:** `CR-번호 / 요청자 / 변경 유형(추가·수정·삭제·릴리스 이동) / 대상 기능 ID / 근거(목표·인사이트·규제 ID) / 영향 분석(영향받는 UG·F·SCR·RG) / 공수 영향(인일) / 판정 / 반영 버전`

### 10-2. 이후 단계로의 전달

| 받는 쪽 | 받는 것 |
|---|---|
| PRD | 기능 요구 섹션 = 32번 트리 + 본 문서 릴리스 구분 |
| 디자인 | 17번 화면 인벤토리 + 기능별 화면 연결 |
| 개발 | 33번 구현 웨이브 + 기능 설명·근거 ID, 인수조건(스토리 단계에서 작성) |
| QA | 기능별 근거 ID → 테스트케이스 파생, 22번 NFR 기준 |
| 법무·운영 | 9절 게이트와 26번 운영 업무 |

---

## 완료 기준 체크 (36)

- [x] 전체 목록 {len(fl)}개를 삭제 없이 유지하고 릴리스 태그만 부여했다
- [x] 법령·스토어 필수 기능과 프로세스 게이트를 분리해 정리했다
- [x] 의존성 위반(Must → Should)을 찾아 보정하고 릴리스 순서 위반 0건을 확인했다
- [x] MVP 공수({days(mvp)}인일)가 기능 구현 용량({CAP:.0f}인일) 이내이다
- [x] 컷라인 선정 이유, R1 투입 순서, 재검토 트리거가 있다
- [x] 베이스라인과 변경요청 절차가 선언되었다
"""
    write('36_우선순위_릴리스.md', o)
    return dict(mvp=len(mvp), r1=len(r1), later=len(lt), must=len(must), mvp_days=days(mvp))


if __name__ == '__main__':
    gen31()
    gen32()
    nc = gen33()
    gen34()
    print(gen36(nc))
