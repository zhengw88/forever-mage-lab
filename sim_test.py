"""Mechanic expectations, conservation and seeded cross-language regression tests."""
import json, math, subprocess, unittest
from pathlib import Path
from sim_engine import Fight, simulate, config, level_build, DEFAULTS, DATA
from current_talents import errors
ROOT=Path(__file__).resolve().parent

def equal(a,b,path=''):
    if isinstance(a,dict):
        assert a.keys()==b.keys(),path
        for k in a:equal(a[k],b[k],path+'/'+k)
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+'/'+str(i))
    elif type(a) in (float,int):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(path,a,b)
    else:assert a==b,(path,a,b)

class SimulationTests(unittest.TestCase):
    def test_legal_level_builds(self):
        for school in ('arcane','fire','frost'):
            for level in range(1,61):
                build=level_build(school,level)
                self.assertFalse(errors(build,level));self.assertEqual(sum(build.values()),max(0,level-9))
    def test_blast_stack_timer_and_cost(self):
        f=Fight('arcane',{'cooldowns':False,'consumables':False,'trace':True,'ab_stacks':4})
        f.act();self.assertAlmostEqual(f.spent,.15*1213)
        f.apply_ab();f.time=2;f.apply_ab();self.assertEqual(f.aura['ab'],18)
        f.act();self.assertAlmostEqual(f.trace[-1]['cost'],.15*1213*3)
        for _ in range(9):f.apply_ab()
        self.assertEqual(f.ab,4);f.time=18;f.apply_ab();self.assertEqual(f.ab,1);self.assertEqual(f.aura['ab'],36)
    def test_single_fireball_hand_formula(self):
        f=Fight('fire',{'seconds':3.5,'sp':100,'crit':0,'hit':1,'miss_floor':0,'partial_resist':0,'cooldowns':False},build={})
        f.random=lambda:.5
        r=f.run();spell=f.spells['fireball']
        self.assertAlmostEqual(r['damage'],spell['base']+spell['coef']*100)
        self.assertEqual(r['casts'],{'fireball':1});self.assertEqual(r['damage_by_spell'].keys(),{'fireball'})
    def test_wrath_mana_scaling(self):
        f=Fight('arcane',{'sp':100,'crit':0,'partial_resist':0,'hit':1,'miss_floor':0,'cooldowns':False})
        f.random=lambda:.5
        row=f.spells['arcanewrath'];f.hit(dict(key='arcanewrath',id=1,sp=100,frozen=False,basecost=row['mana']))
        self.assertAlmostEqual(f.parts['arcanewrath'],(row['base']+100+.05*f.pool)*1.03)
    def test_missiles_channel_timing(self):
        f=Fight('arcane',{'seconds':2.5,'filler':'arcanemissiles','ab_stacks':0,'use_wrath':False,'cooldowns':False,'trace':True,'hit':1,'miss_floor':0})
        f.aura['mb']=15;f.run()
        self.assertEqual(f.trace[0]['duration'],2.5);self.assertEqual(f.trace[0]['cost'],0)
        self.assertEqual([e['at'] for e in f.trace if e['kind']=='damage'],[.5,1,1.5,2,2.5]);self.assertFalse(f.up('mb'))
    def test_ignite_rollover_conserves_bank(self):
        f=Fight('fire',{'seconds':10});f.queue=[];f.add_ignite(0,100);f.time=1;f.add_ignite(0,60)
        r=f.run();self.assertEqual(r['damage_by_spell'],{'ignite':160});self.assertIsNone(f.targets[0]['ignite'])
    def test_flamestrike_later_ticks_and_targets(self):
        # Two targets, two later critical ticks each: 4 * 150 damage, 40% = 240 Ignite.
        for enabled, periodic, key, expected in [(True,True,'flamestrike',240),(False,True,'flamestrike',0),
                (True,False,'flamestrike',0),(True,True,'fireball',0)]:
            o=dict(seconds=8,targets=2,periodic_crit=periodic,flamestrike_periodic_ignite=enabled,trace=True)
            f=Fight('fire',o);f.queue=[]
            for i in range(2):
                f.targets[i]['dots'][key]=dict(token=7,until=4)
                for at in (1,3):f.schedule(at,'dot',dict(key=key,target=i,token=7,amount=100,crit=1,bonus=.5,school='fire'))
                # Stale overwritten tick must not trigger Ignite or damage.
                f.schedule(2,'dot',dict(key=key,target=i,token=6,amount=999,crit=1,bonus=.5,school='fire'))
            result=f.run();self.assertAlmostEqual(result['damage_by_spell'].get('ignite',0),expected)
            script="""const {Fight}=require('./sim-engine.js');const f=new Fight('fire',JSON.parse(process.argv[1])),key=process.argv[2];f.queue=[];
            for(let i=0;i<2;i++){f.targets[i].dots[key]={token:7,until:4};for(const at of [1,3])f.schedule(at,'dot',{key,target:i,token:7,amount:100,crit:1,bonus:.5,school:'fire'});f.schedule(2,'dot',{key,target:i,token:6,amount:999,crit:1,bonus:.5,school:'fire'});}
            console.log(JSON.stringify(f.run()));"""
            equal(result,json.loads(subprocess.check_output(['node','-e',script,json.dumps(o),key],cwd=ROOT)))
        # A dead target must neither take periodic damage nor create an Ignite bank.
        f=Fight('fire',dict(seconds=5,targets=2,target_hp=100,periodic_crit=True));f.queue=[];f.targets[0]['hp']=0
        f.targets[0]['dots']['flamestrike']=dict(token=1)
        f.schedule(1,'dot',dict(key='flamestrike',target=0,token=1,amount=100,crit=1,bonus=.5,school='fire'))
        self.assertEqual(f.run()['damage'],0);self.assertIsNone(f.targets[0]['ignite'])

    def test_flamestrike_repeated_direct_hits(self):
        o=dict(seconds=12,targets=2,sp=0,crit=1,hit=1,miss_floor=0,partial_resist=0,cooldowns=False)
        f=Fight('fire',o);f.queue=[];f.random=lambda:.5
        hit=dict(key='flamestrike',sp=0,frozen=False,basecost=f.spells['flamestrike']['mana'])
        for i in range(2):f.time=i*5;f.hit(dict(hit,id=i+1))
        self.assertGreater(f.parts['flamestrike'],0)
        # Per-target banks include BOTH direct instances, independent of periodic crits.
        self.assertAlmostEqual(sum(t['ignite']['bank'] for t in f.targets),.4*f.parts['flamestrike'])
        script="""const {Fight}=require('./sim-engine.js');const f=new Fight('fire',JSON.parse(process.argv[1]));f.queue=[];f.random=()=>.5;
        for(let i=0;i<2;i++){f.time=i*5;f.hit({key:'flamestrike',sp:0,frozen:false,basecost:f.spells.flamestrike.mana,id:i+1});}
        console.log(JSON.stringify({damage:f.parts.flamestrike,bank:f.targets.reduce((n,t)=>n+t.ignite.bank,0)}));"""
        equal(dict(damage=f.parts['flamestrike'],bank=sum(t['ignite']['bank'] for t in f.targets)),json.loads(subprocess.check_output(['node','-e',script,json.dumps(o)],cwd=ROOT)))

    def test_removed_spell_and_defensive_stats(self):
        self.assertNotIn('frostblast',DATA['spells'])
        build=dict(arcaneresilience=3,frostwarding=2)
        result=simulate('frost',dict(seconds=1,intellect=300),build)
        self.assertEqual(result['defensive_stats'],dict(resilience_armor=225,armor_spell_multiplier=1.3,absorb_multiplier=1.2,ward_negate_chance=.2))
        script="console.log(JSON.stringify(require('./sim-engine.js').simulate('frost',{seconds:1,intellect:300},{arcaneresilience:3,frostwarding:2})))"
        equal(result,json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT)))

    def test_cone_order_and_consumption(self):
        f=Fight('frost',{'sp':100,'crit':0,'hit':1,'miss_floor':0,'partial_resist':0,'cooldowns':False});f.random=lambda:.9
        row=f.spells['coneofcold'];target=f.targets[0];target.update(wc=5,wc_until=15)
        f.hit(dict(key='coneofcold',id=1,sp=100,frozen=False,basecost=row['mana']))
        expected=(row['base']*(1+row['variance']*.4)+row['coef']*100+.07*5*100)*2
        self.assertAlmostEqual(f.parts['coneofcold'],expected);self.assertEqual(target['wc'],0)
        f.time=0;f.aura.update(barrier=60,shield=10);self.assertAlmostEqual(f.multiplier('frost',0),1.20)
        f.time=10;self.assertAlmostEqual(f.multiplier('frost',0),1.15);f.time=60;self.assertEqual(f.multiplier('frost',0),1)
    def test_cooldowns_and_mana_conservation(self):
        for school in ('arcane','fire','frost'):
            r=simulate(school,dict(seconds=300,seed=34,trace=True,cooldowns=False,intellect=10,spirit=0,mp5=0,consumables=False,evocation=False))
            self.assertGreater(r['mana_downtime'],0);self.assertGreaterEqual(r['mana_end'],0)
            self.assertAlmostEqual(r['max_mana']+r['mana_restored']-r['mana_spent'],r['mana_end'])
            self.assertAlmostEqual(sum(r['damage_by_spell'].values()),r['damage'])
            for key,cd in [('icelance',8),('fireblast',6)]:
                times=[e['at'] for e in r['trace'] if e['kind']=='cast' and e['spell']==key]
                self.assertTrue(all(b-a>=cd-1e-9 for a,b in zip(times,times[1:])))
    def test_heating_pom_and_barrage_consumption(self):
        for pom in (False,True):
            f=Fight('arcane',{'cooldowns':pom,'use_wrath':False,'ab_stacks':0,'trace':True})
            f.hu=3;f.aura['hu']=20;f.act()
            self.assertEqual(f.trace[0]['spell'],'pyroblast');self.assertEqual(f.hu,3 if pom else 0)
        f=Fight('arcane',{'cooldowns':False,'use_wrath':False,'ab_stacks':0})
        f.cc=True;f.aura['mb']=15;f.act();self.assertTrue(f.cc);self.assertFalse(f.up('mb'))
    def test_shared_cooldown_boundaries_and_ports(self):
        cases=[]
        for school in ('fire','frost'):
            for first in ('fireblast','icelance'):
                if first=='icelance' and school=='fire':continue
                for base in (False,True):
                    f=Fight(school,{'cooldowns':False,'shared_blast_lance_base':base})
                    f.choose=lambda:first;f.act()
                    expected=6 if first=='fireblast' and school=='fire' and not base else 8
                    self.assertEqual([f.cd[k] for k in ('fireblast','icelance')],[expected,expected])
                    f.time=expected-.001
                    self.assertFalse(f.ready('fireblast'));self.assertFalse(f.ready('icelance'))
                    f.time=expected
                    self.assertTrue(f.ready('fireblast'));self.assertTrue(f.ready('icelance'))
                    cases.append(dict(school=school,first=first,base=base,expected=expected))
        script="""const {Fight}=require('./sim-engine.js');let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(s).map(c=>{const f=new Fight(c.school,{cooldowns:false,shared_blast_lance_base:c.base});f.choose=()=>c.first;f.act();f.time=c.expected-.001;const before=[f.ready('fireblast'),f.ready('icelance')];f.time=c.expected;return [f.cd.fireblast,f.cd.icelance,before,[f.ready('fireblast'),f.ready('icelance')]];}))));"""
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(cases).encode(),cwd=ROOT))
        self.assertEqual(actual,[[c['expected'],c['expected'],[False,False],[True,True]] for c in cases])

    def test_cold_snap_shared_reset_hypotheses(self):
        for shared in (False,True):
            f=Fight('frost',{'cold_snap_resets_fireblast':shared});f.time=1
            f.fof=1;f.aura['fof']=15;f.cd.update(icelance=8,fireblast=8)
            f.choose=lambda:None;f.act()
            self.assertTrue(f.ready('icelance'));self.assertEqual(f.ready('fireblast'),shared)
            self.assertEqual(f.cd['coldsnap'],601)
        script="""const {Fight}=require('./sim-engine.js');console.log(JSON.stringify([false,true].map(shared=>{const f=new Fight('frost',{cold_snap_resets_fireblast:shared});f.time=1;f.fof=1;f.aura.fof=15;Object.assign(f.cd,{icelance:8,fireblast:8});f.choose=()=>null;f.act();return [f.ready('icelance'),f.ready('fireblast'),f.cd.coldsnap];})));"""
        self.assertEqual(json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT)),[[True,False,601],[True,True,601]])

    def test_missiles_clearcasting_proc_and_preservation(self):
        f=Fight('arcane',{'cooldowns':False,'use_wrath':False,'ab_stacks':0,'hit':1,'miss_floor':0})
        f.cc=True;f.aura['mb']=15;f.act()
        self.assertTrue(f.cc);self.assertFalse(f.up('mb'));self.assertEqual(f.spent,0)
        f.time=2.5;f.act();self.assertFalse(f.cc);self.assertEqual(f.spent,0)
        f.random=lambda:0
        f.hit(dict(key='arcanemissiles',id=100,sp=0,frozen=False,basecost=f.spells['arcanemissiles']['mana']))
        self.assertTrue(f.cc)

    def test_range_travel_and_book_availability(self):
        f=Fight('frost',{'distance':30});self.assertFalse(f.in_range('coneofcold'))
        self.assertEqual(f.spells['frostbolt']['rank'],10);self.assertEqual(Fight('frost',{'books':True}).spells['frostbolt']['rank'],11)
        self.assertEqual(simulate('fire',{'seconds':3.5,'travel_seconds':1,'cooldowns':False},build={})['damage'],0)
    def test_leveling_xp_only_on_kill_and_dungeon(self):
        o=dict(level=20,seconds=120,target_hp=100,target_level_delta=0,sp=1000,consumables=False)
        a=simulate('fire',o);b=simulate('fire',dict(o,dungeon=True))
        self.assertTrue(a['killed']);self.assertAlmostEqual(b['safe_target_xp_per_hour']/a['safe_target_xp_per_hour'],1.2)
        self.assertIsNone(simulate('fire',dict(o,target_hp=10000000))['safe_target_xp_per_hour'])
        self.assertEqual(len(Fight('fire',{'level':50}).gems),3)
    def test_reject_invalid_input(self):
        for o in [{'seconds':0},{'level':61},{'crit':1.1},{'seed':-1},{'sp':float('nan')},{'foo':1},{'books':1},{'ab_stacks':5},{'targets':1.5}]:
            with self.assertRaises(ValueError):config(o)
    def test_generated_defaults_and_data(self):
        self.assertEqual(DEFAULTS,json.loads((ROOT/'sim-defaults.json').read_text()))
        before=(ROOT/'sim-data.json').read_bytes();subprocess.run(['python','make_sim_data.py'],cwd=ROOT,check=True)
        self.assertEqual(before,(ROOT/'sim-data.json').read_bytes())
    def test_seeded_javascript_parity(self):
        cases=[]
        for school in ('arcane','fire','frost'):
            for options in [{'targets':4,'distance':8,'periodic_crit':True},{'targets':4,'distance':8,'periodic_crit':True,'flamestrike_periodic_ignite':False},{'shared_blast_lance_base':True},{'cold_snap_resets_fireblast':True},{},{'seconds':300,'seed':13},{'targets':4,'distance':8,'seed':3},{'race':'human'},{'race':'gnome'},{'race':'orc'},{'race':'undead'},{'race':'troll'},{'race':'skyborne'},{'level':20,'target_hp':1000,'target_level_delta':0},{'level':40,'targets':3,'distance':8,'target_hp':3000,'target_level_delta':0},{'unlimited_mana':True,'periodic_crit':True,'snapshot_sp':False,'ab_apply':'impact','seed':42},{'ice_lance_coef':.429,'shield_lifetime':60,'winter_order':'outside','distance':8},{'cooldowns':False,'distance':100},{'seconds':3.5,'travel_seconds':1}]:
                cases.append(dict(school=school,options=dict(options,trace=True)))
        script="const sim=require('./sim-engine.js');let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(s).map(c=>sim.simulate(c.school,c.options)))));"
        js=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(cases).encode(),cwd=ROOT))
        for i,(case,actual) in enumerate(zip(cases,js)):equal(simulate(**case),actual,str(i))
        self.assertEqual(simulate('arcane'),simulate('arcane'))

if __name__=='__main__':unittest.main(verbosity=2)
