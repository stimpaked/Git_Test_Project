"""문서 사이의 ID 연결과 문서에 적은 숫자가 서로 맞는지 검사한다.

사용법:  python3 tools/verify.py
- 모든 검사가 통과하면 종료 코드 0, 하나라도 실패하면 1을 돌려준다.
- 문서를 고치거나 기능 명세(feature_spec.txt)를 바꾼 뒤 항상 실행한다.
"""
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_data import *  # noqa: E402,F401,F403  (final, cands, feats, srcs, excl, AREAS, read, ROOT ...)

results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))


def rows(text, prefix):
    out = []
    for line in text.split('\n'):
        if re.match(r'\|\s*(' + prefix + r')\s*\|', line):
            out.append([c.strip() for c in line.strip().strip('|').split('|')])
    return out


TXT = {os.path.basename(f)[:2]: open(f, encoding='utf-8').read() for f in sorted(glob.glob(os.path.join(ROOT, '[0-3][0-9]_*.md')))}
ALL = '\n'.join(TXT.values())
PROCESS_UG = {'UG-084'}            # 기능이 아니라 출시 프로세스라서 기능에 연결하지 않는 목표(34번 GAP-04)

# ---------------------------------------------------------------- 1. 후보 → 기능
mapping = collections.defaultdict(list)
for f, ss in srcs.items():
    for s in ss:
        mapping[s].append(f)
unmapped = [c for c in cands if c not in mapping and c not in excl]
dup = [c for c in cands if len(mapping.get(c, [])) > 1]
unknown = [s for s in mapping if re.match(r'(Q|CF)-', s) and s not in cands]
overlap = [c for c in excl if c in mapping]
check('후보 → 기능 또는 제외 사유 (미처리 0)', not unmapped, unmapped)
check('후보 중복 매핑 없음', not dup, dup)
check('명세가 가리키는 후보가 모두 실제 존재', not unknown, unknown)
check('제외 후보가 기능에도 매핑되지 않음', not overlap, overlap)
check('모든 기능에 출처(후보·플로우·검증 발견)가 있음', all(srcs.get(f) for f in final), [f for f in final if not srcs.get(f)])

# ---------------------------------------------------------------- 2. 기능 구조
bad_ref, bad_dir = [], []
for f, d in final.items():
    for x in d['uses'] + d['deps']:
        if x not in final:
            bad_ref.append((f, x))
    for x in d['uses']:
        if x in final and final[x]['scope'] != '공통':
            bad_dir.append((f, x))
    if d['scope'] == '공통':
        for x in d['uses'] + d['deps']:
            if x in final and final[x]['scope'] == '고유':
                bad_dir.append((f, x))
check('uses·선후행 참조가 모두 존재', not bad_ref, bad_ref)
check('uses 대상은 공통 기능, 공통 기능은 고유 기능에 의존하지 않음', not bad_dir, bad_dir)

state = {}
cycle = []


def dfs(n, path):
    state[n] = 1
    for x in final[n]['deps'] + final[n]['uses']:
        if x not in final:
            continue
        if state.get(x) == 1:
            cycle.append(path + [n, x])
        elif x not in state:
            dfs(x, path + [n])
    state[n] = 2


for n in final:
    if n not in state:
        dfs(n, [])
check('순환 의존 없음', not cycle, cycle[:1])
check('공통 영역에는 공통 기능, 고유 영역에는 고유 기능만', all(d['scope'] == AREAS[d['area']][1] for d in final.values()),
      [f for f, d in final.items() if d['scope'] != AREAS[d['area']][1]])

rank = {'MVP': 0, 'R1': 1, 'Later': 2}
prank = {'M': 0, 'S': 1, 'C': 2, 'L': 3}
rel_bad = [(f, x) for f, d in final.items() for x in d['deps'] + d['uses'] if rank[final[x]['rel']] > rank[d['rel']]]
pri_bad = [(f, x) for f, d in final.items() if d['rel'] == 'MVP' for x in d['deps'] + d['uses']
           if prank[final[x]['pri']] > prank[d['pri']]]
check('릴리스 순서 위반 없음(MVP가 R1·Later에 의존하지 않음)', not rel_bad, rel_bad)
check('우선순위 의존성 위반 없음(Must가 Should에 의존하지 않음)', not pri_bad, pri_bad)
mvp_days = days([d for d in final.values() if d['rel'] == 'MVP'])
check(f'MVP 공수({mvp_days}인일) ≤ 기능 구현 용량({CAP:.0f}인일)', mvp_days <= CAP)

# ---------------------------------------------------------------- 3. 목표·액터·저니
ugs = re.findall(r'^\|\s*(UG-\d{3})\s*\|', TXT['07'], re.M)
basis = set(b for d in final.values() for b in d['basis'])
no_feature = [u for u in ugs if u not in basis and u not in PROCESS_UG]
check(f'목표 UG {len(ugs)}개 → 기능 (프로세스 {len(PROCESS_UG)}건 제외)', not no_feature, no_feature)
check('비즈니스 목표 G-01~G-06 → 기능', all(g in basis for g in ['G-01', 'G-02', 'G-03', 'G-04', 'G-05', 'G-06']))

active = set()
for line in [l for l in TXT['06'].split('\n') if re.match(r'\|\s*\*\*JS-\d+', l)]:
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    js = re.search(r'JS-\d+', cells[0]).group(0)
    for a, c in zip(['A-01', 'A-02', 'A-03', 'A-04', 'A-05', 'A-06'], cells[1:7]):
        if c.startswith('◆'):
            active.add(f'{js}×{a}')
        elif not (c.startswith('N/A:') and len(c[4:].strip()) >= 4):   # 사유가 "동일" 같은 한두 글자면 실패
            check(f'06번 {js}×{a} 칸은 ◆ 또는 사유 있는 N/A', False, c)
refs07 = set(re.findall(r'JS-\d+×A-0\d', TXT['07']))
check(f'저니 격자 ◆칸 {len(active)}개가 07번 목표에 연결', active == refs07, sorted(active ^ refs07))

# 21번 영역 배정
sec = TXT['21'].split('## 3. 목표(UG) 배정')[1].split('## 4.')[0]
assigned = []
for line in sec.split('\n'):
    if line.startswith('|') and 'UG-' in line and not line.split('|')[1].strip().startswith('영역'):
        assigned += ['UG-' + n for n in re.findall(r'\b(\d{3})\b', line.split('|')[2])]
area_ug = [u for u in assigned if u not in PROCESS_UG]
check('21번 목표 영역 배정: 누락·중복 없음(프로세스 목표는 영역 없음 표기)', sorted(area_ug) == sorted(u for u in ugs if u not in PROCESS_UG) and PROCESS_UG <= set(assigned),
      sorted(set(ugs) - set(assigned)))
sec2 = TXT['21'].split('## 2. 엔티티 배정 검사')[1].split('## 3.')[0]
ec = collections.Counter(re.findall(r'E-(\d{2})', sec2))
check('21번 엔티티 27개가 정확히 한 영역에 배정', len(ec) == 27 and all(v == 1 for v in ec.values()))

# ---------------------------------------------------------------- 4. 화면
scr = re.findall(r'^\|\s*(SCR-(?:A)?\d{2})\s*\|', TXT['17'], re.M)
used = set(s for d in final.values() for s in d['scr'])
check(f'화면 {len(scr)}개 → 기능', not [s for s in scr if s not in used], [s for s in scr if s not in used])
check('기능이 가리키는 화면이 모두 존재', not [(f, s) for f, d in final.items() for s in d['scr'] if s not in scr and s != '*'])
ui = [f for f, d in final.items() if ('A' in d['plat'] or 'W' in d['plat']) and d['rel'] != 'Later' and not d['scr']]
check('화면이 필요한 기능(Later 제외)에 화면이 연결', not ui, ui)

# ---------------------------------------------------------------- 5. 상류 문서의 후보 참조 (상태·이벤트·타이머·규제)
def known(c):
    return c in cands and c not in excl


tr = rows(TXT['13'], r'TR-\d+')
check(f'상태 전이 {len(tr)}건 → 담당 후보 → 기능', all(any(known(x) for x in re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[7])) for r in tr))
tm = rows(TXT['14'], r'TM-\d+')
tm_c = {r[0]: re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[-1]) for r in tm}
check(f'타이머 {len(tm)}건 → 담당 후보 → 기능', all(any(known(x) for x in tm_c[r[0]]) for r in tm))
ev = rows(TXT['16'], r'EV-\d+')


def ev_refs(r):
    row = ' '.join(r)
    out = re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', row)
    for t in re.findall(r'TM-\d{2}', row):
        out += tm_c.get(t, [])
    return out


check(f'이벤트 {len(ev)}건 → 발생·소비 후보 → 기능', all(any(known(x) for x in ev_refs(r)) for r in ev))
rg = rows(TXT['23'], r'RG-\d+')
check(f'규제 {len(rg)}건 → 기능 또는 프로세스', all(any(known(x) or x in excl for x in re.findall(r'(?:Q-\d{3}|CF-\d{2}-\d{2})', r[3])) for r in rg))

# ---------------------------------------------------------------- 6. 문서에 적은 숫자
def has(doc, s):
    return s in TXT[doc]


t13 = collections.Counter(re.split(r'[·,]', r[4])[0] for r in tr)
check('13번 집계 숫자', has('13', f"사용자 {t13['사용자']} · 운영 {t13['운영']} · 시간 {t13['시간']} · 시스템 {t13['시스템']}") and len(tr) == 65)
nf = rows(TXT['22'], r'NF-\d+')
c22 = collections.Counter(r[3].split(' ')[0] for r in nf)
check('22번 집계 숫자', has('22', f"NFR {len(nf)}개 — 승격 {c22['승격']}, 기준 {c22['기준']}, 설계 {c22['설계']}"))
cat = rows(TXT['29'], r'CAT-\d+')
c29 = collections.Counter(r[2].replace('*', '') for r in cat)
adopt = sum(v for k, v in c29.items() if k.startswith('채택'))
check('29번 판정 분포 숫자', has('29', f"채택 계열 {adopt}") and has('29', f"제외 {c29['제외']} · N/A {c29['N/A']} · Later {c29['Later']} · 갭 {c29['갭']}") and len(cat) == 104)
cmp_ = rows(TXT['30'], r'CMP-\d+')
c30 = collections.Counter(r[4].replace('*', '') for r in cmp_)
check('30번 판정 요약 숫자', has('30', f"채택 {c30['채택']} · 제외 {c30['제외']}") and has('30', f"Later {c30['Later']}") and has('30', f"갭 {c30['갭']}") and len(cmp_) == 34)
ent12 = [r for r in rows(TXT['12'], r'E-\d+ [^|]+') if len(r) == 13]
check('12번 CRUD 매트릭스 27행 × 12열에 빈 칸 없음', len(ent12) == 27 and all(c for r in ent12 for c in r))
t08 = TXT['08']
check('08번 집계(공통 22 · 고유 26 · 시스템 19 = 67)', len(ugs) == 67 and '| 공통 | 22 |' in t08 and '| 고유 | 26 |' in t08 and '| 시스템 | 19 |' in t08)
m09 = re.findall(r'^\|\s*(UG-\d{3})\s*\|\s*([^|]+)\|', TXT['09'], re.M)
check('09번 목표→플로우 매핑이 07번 목표 전체와 일치', sorted(x[0] for x in m09) == sorted(ugs))
for doc, pre, n in [('11', r'E-\d+', 27), ('15', r'\d+', 28), ('16', r'EV-\d+', 26), ('24', r'TH-\d+', 18), ('26', r'OP-\d+', 20),
                    ('27', r'MN-\d+', 14), ('28', r'AE-\d+', 24), ('14', r'TM-\d+', 22), ('03', r'IN-\d+', 10)]:
    got = len(rows(TXT[doc], pre))
    check(f'{doc}번 항목 수 {n}', got == n, got)

# ---------------------------------------------------------------- 7. 문서 전체의 ID 참조
defined = collections.defaultdict(set)
pat_def = re.compile(r'^\|\s*(?:\*\*)?([A-Z][A-Za-z]*(?:-[A-Z]?\d+)+(?:-\d+)?)(?:\*\*)?\s*\|', re.M)
for k, t in TXT.items():
    for m in pat_def.finditer(t):
        defined[m.group(1)].add(k)
ref_pat = re.compile(r'\b((?:Q|CF|UG|TM|TR|EV|SCR|E|RG|IN|LT|OUT|G|H|RK|AS|C|DP|P|CMP|CAT|OP|MN|AE|TH|NF|OWN|SHR|DLG|APR|BLK|FL|JS|A|X|T|COM|PS)-(?:A)?\d+(?:-\d+)?)\b')
dangling = sorted(r for r in set(ref_pat.findall(ALL)) if r not in defined and not re.fullmatch(r'CF-\d{2}', r))
check('문서가 참조하는 ID가 모두 어딘가에 정의됨', not dangling, dangling[:10])
f_ids = set(re.findall(r'\bF-[A-Z]{3}-\d{3}\b', ALL))
check('문서가 참조하는 기능 ID가 모두 명세에 있음', f_ids <= set(final), sorted(f_ids - set(final)))

# ---------------------------------------------------------------- 8. 다이어그램 기본 문법
bad_mm = []
for k, t in TXT.items():
    for m in re.finditer(r'```mermaid\n(.*?)```', t, re.S):
        b = m.group(1)
        head = b.strip().split('\n')[0].split()[0]
        if head not in ('flowchart', 'stateDiagram-v2', 'erDiagram') or \
                len(re.findall(r'^\s*subgraph\b', b, re.M)) != len(re.findall(r'^\s*end\s*$', b, re.M)):
            bad_mm.append(k)
check('Mermaid 블록의 머리말·subgraph/end 짝', not bad_mm, bad_mm)

# ---------------------------------------------------------------- 결과
width = max(len(n) for n, _, _ in results)
fail = 0
for n, ok, d in results:
    print(('PASS  ' if ok else 'FAIL  ') + n + ('' if ok else f'  → {d}'))
    fail += 0 if ok else 1
print(f"\n{len(results) - fail}/{len(results)} 통과" + ('' if not fail else f', {fail}건 실패'))
sys.exit(1 if fail else 0)
