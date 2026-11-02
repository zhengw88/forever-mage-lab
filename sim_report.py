"""Reproducible matched experiments, finite policy search and sensitivity archive."""
import argparse, hashlib, json, math, statistics
from pathlib import Path
from sim_engine import simulate, DEFAULTS, config
ROOT=Path(__file__).resolve().parent
INPUTS=['sim_engine.py','sim-data.json','sim-defaults.json','current-builds.json','current-talents.json','sim_report.py']

def summary(school,options,fights=200,seed=10001,policy=None):
    rows=[simulate(school,dict(options,**(policy or {}),seed=(seed+i)&0xffffffff,trace=False)) for i in range(fights)]
    values=[r['dps'] for r in rows];mean=statistics.mean(values);se=statistics.stdev(values)/math.sqrt(fights)
    parts={k:statistics.mean(r['damage_by_spell'].get(k,0)/r['elapsed'] for r in rows) for k in sorted(set().union(*(r['damage_by_spell'] for r in rows)))}
    return dict(school=school,mean_dps=mean,standard_error=se,ci95_sampling=[mean-1.96*se,mean+1.96*se],fights=fights,seed_start=seed,
                mean_mana_downtime=statistics.mean(r['mana_downtime'] for r in rows),mean_evocations=statistics.mean(r['evocations'] for r in rows),
                mean_mana_end=statistics.mean(r['mana_end'] for r in rows),mean_mana_spent=statistics.mean(r['mana_spent'] for r in rows),
                mean_recovery_seconds=statistics.mean(r['recovery_seconds'] for r in rows),
                mean_kill_seconds=statistics.mean(r['elapsed'] for r in rows) if all(r['killed'] for r in rows) else None,damage_by_spell_dps=parts,talents=rows[0]['talents'],
                rotation=policy or {},killed_fraction=statistics.mean(int(r['killed']) for r in rows),
                safe_target_xp_per_hour=statistics.mean(r['safe_target_xp_per_hour'] for r in rows) if all(r['killed'] for r in rows) else None)

def experiment(options=None,fights=200,seed=10001,policies=None):
    if type(fights) is not int or not 2<=fights<=10000:raise ValueError('fights must be 2..10000')
    options=config(dict(options or {},seed=seed));policies=policies or {}
    return dict(model='70707-experimental-event-sim',model_current=False,rankings_blocked=True,options=options,
        uncertainty='95% intervals measure sampling only. Spell coefficients, server ordering, hit/resistance, survival and rotation quality are not validated.',
        results=[summary(s,options,fights,seed,policies.get(s)) for s in ('arcane','fire','frost')])

def policies():
    return {'arcane':[dict(ab_stacks=n,use_wrath=w) for n in range(5) for w in (False,True)],
            'fire':[dict(use_fireblast=f,use_scorch=s,pyro_stacks=p) for f in (False,True) for s in (False,True) for p in (1,2,3)],
            'frost':[dict(use_barrage=b,barrier_refresh=r) for b in (False,True) for r in (30,60)]}

def archive():
    chosen={};search={}
    for school,candidates in policies().items():
        scores=[summary(school,{},60,1,p) for p in candidates];best=max(scores,key=lambda r:r['mean_dps']);chosen[school]=best['rotation']
        search[school]=dict(training_seeds=[1,60],candidates=[dict(policy=r['rotation'],training_dps=r['mean_dps']) for r in scores],selected=chosen[school])
    scenarios=[('baseline',{}),('short_60',{'seconds':60}),('180_seconds',{'seconds':180}),('long_300',{'seconds':300}),
       ('low_sp',{'sp':300}),('high_sp',{'sp':800}),('melee_access',{'distance':8}),('shield_breaks_immediately',{'shield_lifetime':0}),('shield_survives',{'shield_lifetime':60}),
       ('lance_coef_0143',{'ice_lance_coef':.143}),('lance_coef_0429',{'ice_lance_coef':.429}),('no_partial_resist',{'partial_resist':0}),
       ('no_miss_floor',{'miss_floor':0}),('wrath_coef_085',{'wrath_coef':.85}),('wrath_coef_115',{'wrath_coef':1.15}),
       ('fof_boss_disabled',{'fof_on_boss':False}),('cone_outside_order',{'distance':8,'winter_order':'outside'}),('unlimited_mana',{'unlimited_mana':True}),
       ('periodic_crits',{'periodic_crit':True}),('travel_one_second',{'travel_seconds':1}),('aura_at_impact',{'travel_seconds':1,'ab_apply':'impact'}),
       ('aoe_four_safe_targets',{'targets':4,'distance':8,'target_level_delta':0}),
       ('level20_safe_target',{'level':20,'sp':30,'intellect':60,'spirit':40,'crit':.05,'hit':0,'mp5':0,'target_hp':800,'target_level_delta':0,'distance':20,'xp_per_target':150}),
       ('level40_safe_pack',{'level':40,'sp':150,'intellect':150,'spirit':80,'crit':.07,'hit':0,'mp5':15,'targets':3,'target_hp':2000,'target_level_delta':0,'distance':8,'xp_per_target':250})]
    scenarios += [('race_'+race,{'race':race}) for race in ('human','gnome','orc','undead','skyborne','troll')]+[('troll_cache_10s',{'race':'troll','berserking_duration':10})]
    return dict(schema=1,generated_utc='2026-11-02',source_hotfix='2026-10-30',rankings_blocked=True,model_current=False,
       input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},
       search=dict(note='Finite policy search, not global talent/rotation optimization. Selected using 60 training seeds; comparisons use 200 disjoint held-out seeds. Policies stay fixed across sensitivity scenarios.',schools=search),
       scenarios=[dict(name=name,**experiment(o,200,10001,chosen)) for name,o in scenarios])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'current-experiments.json');a=p.parse_args()
    payload=json.dumps(archive(),indent=2,allow_nan=False)+'\n'
    if a.check:
        assert a.output.read_text()==payload,'stale experiment archive';print('PASS: generated experiment archive is current')
    else:a.output.write_text(payload);print('Wrote',a.output)
