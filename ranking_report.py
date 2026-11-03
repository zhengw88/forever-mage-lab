"""Best available model ranking; never certifies a live-game spec winner.

Generate with python ranking_report.py. --check checks provenance, derived ranks,
coverage, and Markdown freshness; --recompute-check also repeats all seeded fights.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from current_talents import errors
from sim_report import summary, policies, INPUTS as SIM_INPUTS
from sim_engine import config
ROOT = Path(__file__).resolve().parent
INPUTS = list(dict.fromkeys(SIM_INPUTS + ['current_talents.py', 'current-experiments.json', 'ranking_report.py']))
TRAIN_FIGHTS, EVAL_FIGHTS, EVAL_SEED = 100, 500, 20001
CASES = [
    ('single_60', 'Single target · 60 seconds', {'seconds':60}),
    ('single_120', 'Single target · 120 seconds', {}),
    ('single_180', 'Single target · 180 seconds', {'seconds':180}),
    ('single_300', 'Single target · 300 seconds', {'seconds':300}),
    ('troll_120', 'Troll · single target · 120 seconds', {'race':'troll'}),
    ('troll_300', 'Troll · single target · 300 seconds', {'race':'troll','seconds':300}),
    ('aoe_four', 'Four safe targets · 120 seconds', {'targets':4,'distance':8,'target_level_delta':0}),
    ('frost_combined_0143', 'Frost sensitivity · Cone access + shield + 0.143 scaling', {'distance':8,'shield_lifetime':60,'ice_lance_coef':.143}),
    ('frost_combined_0429', 'Frost sensitivity · Cone access + shield + 0.429 scaling', {'distance':8,'shield_lifetime':60,'ice_lance_coef':.429}),
]
LIMITS = [
    'Provisional ranking of implemented presets and finite policies, not validated in-game performance or a global talent optimum.',
    '95% intervals cover Monte Carlo sampling only; they exclude coefficients, proc timing, talent prerequisites, rotation search and survival uncertainty.',
    'Identical gear and encounter settings within each comparison; school-specific builds/policies differ. Race-neutral and Troll cases are separate.',
    'No incoming damage, movement, deaths, immunities, party XP sharing or realistic leveling survival. No practical leveling winner is inferred.',
    'Combined Frost cases are deliberately favorable sensitivity probes, not measured parameters, expected values, or a probability distribution.',
    'Archive leader counts are descriptive coverage of selected cases, not independent observations or probabilities. No cross-scenario average tier list.',
]

def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS}

def rank_rows(rows):
    if len(rows)!=3 or {r['school'] for r in rows}!={'arcane','fire','frost'}:
        raise ValueError('exactly one row for each school required')
    for row in rows:
        mean=row['mean_dps'];interval=row['ci95_sampling']
        if not math.isfinite(mean) or mean<=0 or len(interval)!=2 or not all(math.isfinite(x) for x in interval) or not interval[0]<=mean<=interval[1]:
            raise ValueError('positive finite DPS and a valid sampling interval required')
    ordered=sorted(rows,key=lambda r:(-r['mean_dps'],r['school']))
    lead=ordered[0]
    return [dict(school=r['school'],rank=1+sum(x['mean_dps']>r['mean_dps'] for x in ordered),
                 mean_dps=r['mean_dps'],ci95_sampling=r['ci95_sampling'],
                 behind_leader_percent=100*(1-r['mean_dps']/lead['mean_dps']),
                 leader_interval_overlap=max(lead['ci95_sampling'][0],r['ci95_sampling'][0])<=min(lead['ci95_sampling'][1],r['ci95_sampling'][1])) for r in ordered]

def load_archive():
    data=json.loads((ROOT/'current-experiments.json').read_text())
    for p,h in data['input_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:
            raise ValueError('stale source archive: '+p+'; run python sim_report.py')
    return data

def generate():
    archive=load_archive();cases=[]
    for key,label,overrides in CASES:
        selected={};search={};results=[]
        for school,candidates in policies().items():
            scores=[summary(school,overrides,TRAIN_FIGHTS,1,p) for p in candidates]
            best=max(scores,key=lambda r:r['mean_dps']);selected[school]=best['rotation']
            search[school]=[dict(policy=r['rotation'],training_mean_dps=r['mean_dps']) for r in scores]
            result=summary(school,overrides,EVAL_FIGHTS,EVAL_SEED,selected[school])
            assert not errors(result['talents'],require_full=True)
            results.append(result)
        cases.append(dict(name=key,label=label,options=config(dict(overrides,seed=EVAL_SEED)),
                          search=search,selected_policies=selected,results=results,ranking=rank_rows(results)))
        print('Evaluated',key,flush=True)
    sensitivity=[dict(name=s['name'],options=s['options'],ranking=rank_rows(s['results'])) for s in archive['scenarios']]
    return dict(schema=1,status='provisional',model_current=False,certified_rankings_blocked=True,
                generated_date='2026-11-03',mechanics_commit='d26f7eaf1a3fd7d3d5f67c697962bd18ca416359',
                source_hotfix='2026-10-30',official_notes_date='2026-11-02',input_sha256=hashes(),
                method=dict(objective='mean DPS',training_seeds=[1,TRAIN_FIGHTS],evaluation_seeds=[EVAL_SEED,EVAL_SEED+EVAL_FIGHTS-1],
                            candidates_per_case={s:len(p) for s,p in policies().items()},
                            note='Reselect policies independently for each encounter, then evaluate on disjoint held-out seeds. Three fixed, source-contract legal 51-point builds; no talent search.'),
                limitations=LIMITS,cases=cases,archive_sensitivity=sensitivity)

def markdown(data):
    out=['# Provisional Mage ranking — November 3, 2026','',
         '**Best available model estimate; not a validated in-game ranking.**','',
         'Policies are reselected for each encounter from 26 candidates on seeds 1–100; each selected school then runs 500 held-out fights on seeds 20001–20500. Builds pass the extracted tree contract, not server verification. No MythicSim calibration.','',
         'Shared baseline: level 60, 500 spell power, 300 Intellect, 120 Spirit, 10% input crit, 11% input hit, 65 mp5, one +3 target at 30 yards. Consumables/evocation enabled, books off. Troll uses the modeled 15-second racial. Four-target cases instead use equal-level targets at 8 yards.','',
         '| Encounter | Provisional order by mean DPS |','| --- | --- |']
    for c in data['cases']:
        out.append('| '+c['label']+' | '+' > '.join(f"{r['school'].title()} {r['mean_dps']:.1f}" for r in c['ranking'])+' |')
    out+=['','## Interpretation','',
          'Use the short/medium single-target cases when choosing a damage spec for those fights, and check the 300-second cases when mana limits matter. The four-target comparison is throughput against safe stationary targets. Keep the existing Frost solo-leveling plan as an authored practical recommendation; this report cannot validate survival or XP/hour.','',
          'Arcane versus Frost is encounter-sensitive. Check the combined Frost probes before treating the baseline order as universal. Overlapping sampling intervals are flagged; non-overlap still does not resolve systematic model errors.','',
          '## Detailed reproducibility','']
    for c in data['cases']:
        out+=['### '+c['label'],'','| School | DPS | 95% sampling interval | Behind leader | Mana downtime |','| --- | ---: | --- | ---: | ---: |']
        rows={r['school']:r for r in c['results']}
        for rank in c['ranking']:
            r=rows[rank['school']];lo,hi=r['ci95_sampling']
            out.append(f"| {r['school'].title()} | {r['mean_dps']:.2f} | {lo:.2f}–{hi:.2f} | {rank['behind_leader_percent']:.2f}% | {r['mean_mana_downtime']:.2f}s |")
        out+=['','Selected policies: `'+json.dumps(c['selected_policies'],sort_keys=True)+'`.','']
    out+=['## Existing 35-case sensitivity matrix','',
          'These retain the original baseline-trained policies and 200 held-out fights per school; they are separate from the encounter-specific searches above. Their counts are not confidence estimates.','',
          '| Case | Order by mean DPS |','| --- | --- |']
    for s in data['archive_sensitivity']:out.append('| '+s['name']+' | '+' > '.join(r['school'].title() for r in s['ranking'])+' |')
    out+=['','## Limits','']+['- '+x for x in data['limitations']]+['',
         'All inputs, build allocations, candidate scores, spell breakdowns and mana diagnostics are in `provisional-rankings.json`; provenance hashes detect stale mechanics or archives. `python ranking_report.py` regenerates both artifacts. `--check` checks freshness and derived content; `--recompute-check` repeats the seeded search and evaluation.','',
         'Evidence remains pinned in `lab-state.json` and `MAGE-NOV2-COVERAGE.md`. The official November 2 supplement and dated extraction index were rechecked; upstream remains a331552. No new mechanic numbers were substituted for this ranking pass.','']
    return '\n'.join(out)

def validate(data):
    assert data['status']=='provisional' and data['model_current'] is False and data['certified_rankings_blocked'] is True
    assert data['input_sha256']==hashes(),'stale provisional ranking inputs; regenerate'
    assert [(c['name'],c['label']) for c in data['cases']]==[(k,l) for k,l,_ in CASES]
    archive=load_archive()
    assert data['archive_sensitivity']==[dict(name=s['name'],options=s['options'],ranking=rank_rows(s['results'])) for s in archive['scenarios']]
    for c,(_,_,overrides) in zip(data['cases'],CASES):
        assert c['options']==config(dict(overrides,seed=EVAL_SEED))
        assert c['ranking']==rank_rows(c['results'])
        for row in c['results']:
            assert row['fights']==EVAL_FIGHTS and row['seed_start']==EVAL_SEED
            assert not errors(row['talents'],require_full=True)
            assert row['rotation']==c['selected_policies'][row['school']]
            assert row['rotation']==max(c['search'][row['school']],key=lambda r:r['training_mean_dps'])['policy']
            assert math.isclose(sum(row['damage_by_spell_dps'].values()),row['mean_dps'],rel_tol=1e-10)
    assert (ROOT/'PROVISIONAL-RANKING.md').read_text()==markdown(data),'stale Markdown ranking'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--recompute-check',action='store_true');a=p.parse_args()
    path=ROOT/'provisional-rankings.json'
    if a.check or a.recompute_check:
        data=json.loads(path.read_text());validate(data)
        if a.recompute_check:assert data==generate(),'seeded ranking changed'
        print('PASS: provisional ranking provenance, cases, derived ranks and Markdown'+(' and full recomputation' if a.recompute_check else ''))
    else:
        data=generate();path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');(ROOT/'PROVISIONAL-RANKING.md').write_text(markdown(data));validate(data)
