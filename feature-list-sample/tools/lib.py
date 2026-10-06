"""공통 도구: 경로, 1~30번 문서의 후보(Q-, CF-) 읽기, 기능 명세(feature_spec.txt) 읽기."""
import re, glob, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # feature-list-sample/ (문서가 있는 폴더)
SPEC = os.path.join(HERE, 'feature_spec.txt')     # 기능 명세 데이터


def read(name_prefix):
    f = glob.glob(os.path.join(ROOT, name_prefix + '_*.md'))
    assert len(f) == 1, (name_prefix, f)
    return open(f[0], encoding='utf-8').read()


def load_cands():
    cands = collections.OrderedDict()
    for f in sorted(glob.glob(os.path.join(ROOT, '[0-3][0-9]_*.md'))):
        n = int(os.path.basename(f)[:2])
        if n < 9 or n > 30:
            continue
        for line in open(f, encoding='utf-8'):
            m = re.match(r'\|\s*((?:Q-\d{3})|(?:CF-\d{2}-\d{2}))\s*\|(.*)', line)
            if not m:
                continue
            cid = m.group(1)
            cells = [c.strip() for c in m.group(2).strip().rstrip('|').split('|')]
            if cid.startswith('Q-') and n == 9:
                name, tag = cells[1], cells[2]
            elif cid.startswith('Q-'):
                name, tag = cells[2], cells[3]
            else:
                name, tag = cells[1], cells[2]
            cands[cid] = dict(file=os.path.basename(f), step=n, name=name, tag=tag)
    return cands


def load_spec():
    txt = open(SPEC, encoding='utf-8').read()
    head, rest = txt.split('###SOURCES')
    src_txt, exc_txt = rest.split('###EXCLUDED')
    lines = [l for l in head.strip().split('\n')]
    cols = lines[0].split('|')
    feats = collections.OrderedDict()
    for l in lines[1:]:
        p = l.split('|')
        assert len(p) == len(cols), (len(p), len(cols), l)
        d = dict(zip(cols, p))
        for k in ('actors', 'stages', 'scr', 'basis', 'uses', 'deps'):
            d[k] = [] if d[k] == '-' else d[k].split(',')
        assert d['id'] not in feats, d['id']
        feats[d['id']] = d
    srcs = {}
    for l in src_txt.strip().split('\n'):
        k, v = l.split(':', 1)
        assert k.strip() in feats, k
        srcs[k.strip()] = v.split()
    excl = {}
    for l in exc_txt.strip().split('\n'):
        k, v = l.split(':', 1)
        excl[k.strip()] = v.strip()
    return feats, srcs, excl
