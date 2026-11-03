"""Versioned combat data. Preserve older evidence rather than pretending it is current."""
import ast
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
raw=json.loads((ROOT/'data/mage_spells.json').read_text())['records']
keep={'Frostbolt','Fireball','Frostfire Bolt','Scorch','Arcane Missiles','Fire Blast','Arcane Blast','Ice Lance','Pyroblast','Blast Wave','Cone of Cold','Blizzard','Flamestrike','Arcane Explosion','Ice Barrier'}
spells={}
for r in raw:
 if r['spell'] not in keep:continue
 k=re.sub('[^a-z]','',r['spell'].lower());v=lambda key,default=0:r.get(key,{}).get('value',default)
 d=r.get('damage',{});dv=lambda key,default=0:d.get(key,{}).get('value',default)
 row=dict(rank=r['rank'],id=r['id'],level=v('level_learned'),cast=v('cast_ms')/1000,mana=v('mana_cost') or 0,cd=v('cooldown_ms')/1000,school=v('school','frost'),base=dv('base_avg_at_learn'),growth=dv('per_level'),max_level=v('max_level') or v('spell_level'),spell_level=v('spell_level'),coef=dv('sp_coefficient'),variance=dv('variance'),ticks=dv('ticks',1),period=dv('period_ms',1000)/1000,channel=v('channel_ms')/1000,book=r['rank']>(10 if k=='frostbolt' else 11 if k=='fireball' else 7 if k=='arcanemissiles' else 99),source='inherited-client-69893')
 if 'dot' in r:
  dot=r['dot'];row['dot']={key:dot.get(field,{}).get('value',0) for key,field in [('base','base_avg_at_learn'),('coef','sp_coefficient'),('ticks','ticks'),('period','period_ms')]};row['dot']['period']/=1000
 if k=='arcanemissiles': row['ticks']=round(row['channel']) or 5;row['period']=1
 if k=='icebarrier':row.update(base=v('absorb_at_learn'),growth=v('absorb_per_level'),coef=.1,source='70707-hotfix-tooltip')
 if k=='arcaneblast':
  row.update(cast=1.5,coef=.429,base=row['base']*.6,growth=row['growth']*.6,source='69893-baseline-plus-official-40-percent-reduction-and-70707-tooltip')
 if k=='icelance':row.update(cd=8,source='69893-rank-values-plus-70707-hotfix-cooldown')
 spells.setdefault(k,[]).append(row)
for r in spells['arcaneblast']:
 if r['rank']==5:r.update(base=236,growth=0,variance=36/236,source='70707-hotfix-tooltip; coefficient candidate from 70425 client comparison')
spells['arcanewrath']=[]
for rank,(level,base,mana) in enumerate([(25,120,140),(36,187,220),(48,300,305),(60,451,395)],1):
 spells['arcanewrath'].append(dict(rank=rank,id=0,level=level,cast=3.5,mana=mana,cd=6,school='arcane',base=base,growth=0,max_level=level,spell_level=level,coef=1,variance=.2,ticks=1,period=1,channel=0,book=False,source='70532-client-extraction; 70707 rank-4 tooltip cross-check; lower-rank growth unverified'))
# Recover only literal arrays; do not import the historical engine or any calibration code.
tree=ast.parse((ROOT/'models/character.py').read_text())
arrays={}
for n in tree.body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('BASE_MANA','CRIT_PER_INT'):
  arrays[n.targets[0].id.lower()]=ast.literal_eval(n.value)
out=dict(schema=1,version='70707-20261030-experimental',spells=spells,**arrays,sources={
 'inherited-client-69893':{'file':'data/mage_spells.json','build':'1.60.1.69893','status':'historical extraction; unchanged values are an explicit hypothesis'},
 'current_tooltips':{'url':'https://wowforevertalents.com/abilities/mage/','build':'1.60.1.70707','hotfix':'2026-10-30'},
 'coefficient_check':{'url':'https://wowforeverhelper.com/spells/mage','build':'1.60.1.70532','status':'direct client extraction; later server coefficients unverified'},
 'blast_reduction':{'url':'https://foreverdb.net/article/build-1-60-1-70425-game-files','build':'1.60.1.70425','fact':'Blast coefficient 0.429; previous 0.714'},
 'racials':{'url':'https://wowforevertalents.com/racials/','build':'1.60.1.70707'},
 'official':{'url':'https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-october-26/2360696','status':'announced rules distinguished from cache'}},
 caveats=['Not a fully verified current spell snapshot. No simulator rankings are imported.', 'Ice Lance client coefficient zero is the default; alternative coefficients are sensitivity inputs, not calibration.', 'Lower-rank growth, mana regeneration, hit/resistance and server proc ordering remain assumptions.', 'Safe-target leveling and AoE throughput do not simulate player survival, pathing or group XP sharing.'])
(ROOT/'sim-data.json').write_text(json.dumps(out,indent=2)+'\n')
