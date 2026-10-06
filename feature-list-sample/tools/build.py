"""문서 31~36번과 00_README.md를 기능 명세(feature_spec.txt)에서 다시 만든다.

사용법:  python3 tools/build.py        (feature-list-sample/ 안에서든 저장소 루트에서든 동일)

- 읽는 것: 1~30번 문서(사람이 쓴 문서), tools/feature_spec.txt(기능 146개의 명세 데이터)
- 쓰는 것: 31, 32, 33, 34, 35, 36번 문서와 00_README.md  (※ 이 파일들은 직접 고치지 말고 이 도구의 데이터를 고친다)
- 순서: 31~34·36 → 35 → README  (README가 앞 문서들의 머리말 표를 읽어 가기 때문)
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gen_docs  # noqa: E402  (31, 32, 33, 34, 36번 생성 함수)
import gen35  # noqa: E402  (35번 생성 함수)

gen_docs.gen31()
gen_docs.gen32()
no_caller = gen_docs.gen33()
gen_docs.gen34()
summary = gen_docs.gen36(no_caller)
gen35.gen35()
runpy.run_path(os.path.join(HERE, 'gen_readme.py'))   # 00_README.md

print('생성 완료: 31~36번, 00_README.md')
print('MVP', summary['mvp'], '기능 /', summary['mvp_days'], '인일, Must', summary['must'],
      '/ R1', summary['r1'], '/ Later', summary['later'])
