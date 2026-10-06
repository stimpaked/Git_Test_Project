"""기능 명세를 읽어 36번의 조정(우선순위 상향·R1 이동)과 공수·용량 가정을 적용한 최종 데이터를 만든다."""
import os, re, sys, collections, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

AREAS = collections.OrderedDict([
    ('ACC', ('계정·인증·권한', '공통')), ('CNS', ('약관·동의·개인정보', '공통')), ('NTF', ('알림', '공통')),
    ('FIL', ('파일·미디어', '공통')), ('SCH', ('스케줄러·배치', '공통')), ('SUP', ('고객지원', '공통')),
    ('OPS', ('운영·플랫폼', '공통')), ('ADM', ('백오피스 공통', '공통')),
    ('LOC', ('동네', '고유')), ('PRD', ('글', '고유')), ('DSC', ('탐색', '고유')), ('CHT', ('채팅·약속', '고유')),
    ('TRD', ('거래', '고유')), ('RVW', ('후기·매너', '고유')), ('SAF', ('신고·제재·안전', '고유')),
    ('USR', ('프로필·사용자', '고유')),
])

cands = load_cands()
feats, srcs, excl = load_spec()          # 34번 갭 조치까지 반영된 명세 (우선순위·릴리스는 v0 값)
for f, d in feats.items():
    d['area'] = f.split('-')[1]
    d['srcs'] = srcs.get(f, [])

# 35번 개선(기능 신규 외 인수조건 보강) 이력
CHG35 = {
    'F-RVW-008': '35 신규(R35-01); R35-10 인수조건 보강',
    'F-CHT-013': '35 신규(R35-02)',
    'F-SAF-010': '35 신규(R35-03)',
    'F-NTF-008': '35 신규(R35-05)',
    'F-SUP-009': '35 보강(R35-04): 본인 확인 체크리스트',
    'F-ACC-011': '35 보강(R35-06): 최소 보존 정보 기간 명시',
    'F-NTF-001': '35 보강(R35-07): 로그아웃·탈퇴 시 토큰 즉시 해제',
}
CHG34 = {
    'F-SCH-003': '34 수정(GAP-01): 화면 SCR-A18 연결',
    'F-SUP-011': '34 신규(GAP-02)',
    'F-ADM-003': '34 수정(GAP-03): 액터에 A-04·A-05 추가',
}

# 36번 조정
PRI_UP = ['F-CNS-005', 'F-OPS-013', 'F-ACC-008']                       # 의존성 때문에 Should -> Must
CUT_TO_R1 = ['F-ACC-015', 'F-NTF-006', 'F-SUP-002', 'F-OPS-005', 'F-OPS-010', 'F-ADM-003', 'F-ADM-004',
             'F-LOC-006', 'F-LOC-004', 'F-PRD-002', 'F-PRD-007', 'F-PRD-010', 'F-DSC-004', 'F-CHT-007',
             'F-CHT-008', 'F-CHT-010', 'F-CHT-013', 'F-TRD-008', 'F-RVW-002', 'F-RVW-005', 'F-RVW-006',
             'F-SAF-006', 'F-SAF-012', 'F-USR-002', 'F-USR-006', 'F-SUP-011']
KEEP_SHOULD = ['F-SUP-008', 'F-TRD-004', 'F-RVW-003', 'F-SAF-010', 'F-PRD-006', 'F-TRD-006']
final = copy.deepcopy(feats)
orig_pri = {f: d['pri'] for f, d in feats.items()}
orig_rel = {f: d['rel'] for f, d in feats.items()}
for f in PRI_UP:
    final[f]['pri'] = 'M'
for f in CUT_TO_R1:
    final[f]['rel'] = 'R1'
final['F-SUP-008']['gate'] = 'law'       # 오픈소스 라이선스 고지 의무

W = {'S': 1, 'M': 2, 'L': 5}
CAP_RAW = 5 * 12 * 5 * 0.7              # 210
BUFFER = 0.10
CAP = CAP_RAW * (1 - BUFFER)            # 189


def days(fs):
    return sum(W[d['eff']] for d in fs)


def name(f):
    return final[f]['name']


def md(s):
    return s.replace('|', '/')
