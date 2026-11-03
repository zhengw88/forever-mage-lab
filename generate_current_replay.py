"""Generate reviewed mechanics traces; --check verifies committed artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
from current_combat import replay
from current_talents import encode, errors

ROOT=Path(__file__).resolve().parent
INPUTS=['current-replay-cases.json','current-talents.json','current_talents.py','current-talents.js',
        'current_combat.py','current-combat.js','patch_rules.py','patch-rules.js','patch-rules.json']


def generate():
    request=json.loads((ROOT/'current-replay-cases.json').read_text())
    results={}
    for school,case in request['cases'].items():
        assert not errors(case['talents'],require_full=True)
        results[school]=dict(share_fragment=encode(case['talents']),**replay(case['talents'],case['events'],case['options']))
    return dict(schema=1,version=request['version'],purpose=request['purpose'],model_current=False,
                input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},results=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    path=ROOT/'current-replay-report.json'
    text=json.dumps(generate(),indent=2,allow_nan=False)+'\n'
    if args.check:
        if not path.exists() or path.read_text()!=text:
            raise SystemExit('Stale current-replay-report.json; run python generate_current_replay.py')
        print('PASS: committed mechanic traces match their versioned inputs')
    else:
        path.write_text(text)
        print('Generated current-replay-report.json (not a DPS ranking)')
