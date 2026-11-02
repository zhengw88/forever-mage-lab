#!/usr/bin/env python3
"""Version-aware local runner. No external simulation service is used."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'models'))
sys.path.insert(0, str(ROOT / 'analysis'))


def state():
    return json.loads((ROOT / 'lab-state.json').read_text())


def current_allowed(s):
    return (s.get('model_current') is True
            and bool(s.get('changes'))
            and all(c.get('implementation') == 'validated' for c in s['changes']))


def report(fights, seed, seconds):
    import raid_model as model
    from raid_check import check
    options = dict(model.DEFAULTS, fightLength=seconds)
    rows = []
    for sid in ('frost-mb', 'fire-mb', 'arcane', 'arcane-fire'):
        spec = model.spec_by_id(sid)
        errors = model.build_errors(spec['talents'])
        if errors:
            raise ValueError(f'Illegal baseline build {sid}: {errors}')
        result, mean, se, parts, diagnostics = check(
            options, spec['talents'], fights=fights, seed=seed)
        rows.append(dict(id=sid, name=spec['name'], talents=spec['talents'],
                         expected_dps=result['total'], simulated_dps=mean,
                         standard_error=se, sampling_ci95=[mean - 1.96 * se, mean + 1.96 * se],
                         damage_by_spell=parts, diagnostics=diagnostics))
    paths = ['lab.py', 'lab-state.json', 'models/raid_model.py',
             'analysis/raid_check.py', 'data/mage_spells.json', 'data/talents.json']
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                             cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    s = state()
    return dict(schema=1, model=s['model'], model_current=current_allowed(s),
                caveat='Historical baseline; no current Fire/Arcane/Frost ranking. '
                       'Confidence intervals quantify sampling error only.',
                commit=commit, tracked_worktree_dirty=dirty, input_sha256=hashes,
                fights=fights, seed=seed, options=options,
                results=sorted(rows, key=lambda row: -row['simulated_dps']))


def validate():
    subprocess.run([sys.executable, 'patch_rules_test.py'], cwd=ROOT, check=True)
    # Test the release guard independently of the ledger's current state.
    assert not current_allowed({'model_current': True, 'changes': []})
    assert not current_allowed({'model_current': True, 'changes': [{'implementation': 'pending'}]})
    assert not current_allowed({'model_current': False, 'changes': [{'implementation': 'validated'}]})
    assert current_allowed({'model_current': True, 'changes': [{'implementation': 'validated'}]})
    s = state()
    for change in s['changes']:
        assert change['sources'] and all(k in s['sources'] for k in change['sources'])
    a, b = report(3, 7, 60), report(3, 7, 60)
    assert a == b, 'Seeded simulation is not reproducible'
    for row in a['results']:
        assert math.isfinite(row['simulated_dps']) and row['simulated_dps'] > 0
        assert abs(sum(row['damage_by_spell'].values()) - row['simulated_dps']) < 1e-6
    for filename in ('builder_test.js', 'parity_test.js', 'raid_options_test.js',
                     'weights_test.js', 'leveling_parity_test.js'):
        subprocess.run(['node', str(ROOT / 'tests' / filename)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'tests/aoe_test.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'src/build.py'], cwd=ROOT, check=True)
    assert 'HISTORICAL MODEL' in (ROOT / 'index.html').read_text()
    print('PASS: provenance, version guard, seeded runs, damage totals, numerical suites and page build.')
    print('Browser checks are separate: python tests/page_check.py; see REBUILD.md for baseline failures.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('validate')
    compare = commands.add_parser('compare')
    compare.add_argument('--historical', action='store_true', help='Explicitly allow the old baseline rules')
    compare.add_argument('--fights', type=int, default=1000)
    compare.add_argument('--seed', type=int, default=1)
    compare.add_argument('--seconds', type=float, default=300)
    compare.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'status':
        print(json.dumps(state(), indent=2))
    elif args.command == 'validate':
        validate()
    else:
        if not current_allowed(state()) and not args.historical:
            parser.error('Current mechanics migration is incomplete. Use --historical only for baseline research.')
        if args.fights < 2 or not math.isfinite(args.seconds) or args.seconds <= 0:
            parser.error('--fights must be >= 2 and --seconds must be finite and positive')
        payload = json.dumps(report(args.fights, args.seed, args.seconds), indent=2, allow_nan=False) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload)
            print(f'Wrote {args.output}')
        else:
            print(payload, end='')


if __name__ == '__main__':
    main()
