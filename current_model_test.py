"""Hand-derived mechanic boundaries, legality failures and cross-language parity."""
import json
import subprocess
import unittest
from pathlib import Path
import current_talents as talents
from current_combat import replay

ROOT = Path(__file__).resolve().parent
BUILDS = json.loads((ROOT/'current-builds.json').read_text())['builds']
OPTIONS = dict(intellect=300, base_mana=1000, heating_refresh='refresh', cone_consumption='hit')


def js(module, method, *args):
    script = "const m=require('./'+process.argv[1]); const a=JSON.parse(require('fs').readFileSync(0,'utf8')); try {process.stdout.write(JSON.stringify({ok:true,value:m[process.argv[2]](...a)}));} catch(e) {process.stdout.write(JSON.stringify({ok:false}));}"
    result = subprocess.run(['node','-e',script,module,method], input=json.dumps(args),
                            text=True,capture_output=True,cwd=ROOT,check=True)
    return json.loads(result.stdout)


class Talents(unittest.TestCase):
    def test_snapshot_and_builds(self):
        self.assertEqual(len(talents.NODES),53)
        self.assertEqual([sum(n['tree']==t for n in talents.NODES.values()) for t in ('Arcane','Fire','Frost')],[18,17,18])
        for key, build in BUILDS.items():
            with self.subTest(key=key):
                self.assertEqual(talents.errors(build,require_full=True),[])
                self.assertEqual(sum(build.values()),51)
                self.assertEqual(js('current-talents.js','errors',build,60,True)['value'],[])
                link=talents.encode(build)
                self.assertEqual(talents.decode(link),build)
                self.assertEqual(js('current-talents.js','encode',build)['value'],link)
                self.assertEqual(js('current-talents.js','decode',link)['value'],build)

    def test_rank_budget_tier_and_prerequisite(self):
        invalid=[{'arcanefocus':0},{'piercingice':1},{'precision':4},{'missilebarrage':3},
                 {'precision':True},{'precision':-1},{'precision':'3'},
                 {'arcaneblast':1},dict(BUILDS['fire'],arcaneresilience=1),
                 dict(BUILDS['arcane'],arcaneblast=0),dict(BUILDS['fire'],pyroblast=0),
                 dict(BUILDS['frost'],coldsnap=0)]
        for build in invalid:
            self.assertTrue(talents.errors(build),build)
            self.assertTrue(js('current-talents.js','errors',build)['value'],build)
        # Spending on a row must not unlock that same row.
        self.assertTrue(talents.errors({'improvedchanneling':4,'arcaneconcentration':5}))
        self.assertTrue(talents.errors({'precision':1},level=9))
        self.assertEqual(talents.errors({},level=9,require_full=True),[])
        self.assertTrue(talents.errors({},level=61))

    def test_versioned_links_reject_ambiguous_inputs(self):
        bad=['#b-'+'0'*54,'#mage-70707-20261031:precision=3',talents.PREFIX+'precision=3,precision=2',
             talents.PREFIX+'precision=03',talents.PREFIX+'precision=3.0',talents.PREFIX+'precision=0',
             talents.PREFIX+'__proto__=1',talents.PREFIX+'arcanefocus=1',talents.PREFIX+'precision=3,']
        for link in bad:
            with self.assertRaises(ValueError):talents.decode(link)
            self.assertFalse(js('current-talents.js','decode',link)['ok'])


class Mechanics(unittest.TestCase):
    def run_replay(self, school, events, **options):
        result=replay(BUILDS[school],events,dict(OPTIONS,**options))
        port=js('current-combat.js','replay',BUILDS[school],events,dict(OPTIONS,**options))
        self.assertTrue(port['ok'])
        self.assertEqual(result,port['value'])
        return result['events']

    def test_arcane_cycle(self):
        events=[dict(at=t,kind='blast_aura') for t in (0,4,8,12,16)]
        events += [dict(at=17,kind='barrage_roll',spell='arcanemissiles',roll=0,expires_at=30),
                   dict(at=17,kind='barrage_roll',spell='arcaneblast',roll=0.39,expires_at=30),
                   dict(at=17,kind='missiles_cast'),dict(at=18,kind='observe'),
                   dict(at=20,kind='missiles_cast'),dict(at=21,kind='blast_aura')]
        rows=self.run_replay('arcane',events)
        self.assertEqual([r['blast']['mana_cost'] for r in rows[:5]],[300,450,600,750,750])
        self.assertEqual(rows[4]['blast']['spell_damage_bonus'],144)
        self.assertEqual(rows[4]['blast']['expires_at'],18)
        self.assertFalse(rows[5]['detail']['triggered'])
        self.assertTrue(rows[6]['detail']['triggered'])
        self.assertEqual(rows[7]['detail'],dict(empowered=True,channel_seconds=2.5,mana_multiplier=0,tick_offsets=[0.5,1,1.5,2,2.5]))
        self.assertEqual(rows[8]['blast']['stacks'],0)
        self.assertEqual(rows[9]['detail']['channel_seconds'],5)
        self.assertEqual(rows[10]['blast']['expires_at'],39)
        self.assertEqual(rows[0]['wrath_cast_seconds'],3)
        self.assertEqual(rows[0]['precision_hit'],0.06)

    def test_heating_up_and_pom(self):
        events=[dict(at=0,kind='fire_hit',spell='fireblast',crit=True,periodic=False),
                dict(at=1,kind='fire_hit',spell='fireblast',crit=False,periodic=False),
                dict(at=2,kind='fire_hit',spell='ignite',crit=True,periodic=True),
                dict(at=3,kind='pyro_cast',presence_of_mind=True),
                dict(at=4,kind='pyro_cast',presence_of_mind=False)]
        rows=self.run_replay('arcane',events)
        self.assertEqual([r['heating_stacks'] for r in rows],[2,3,3,3,0])
        self.assertEqual(rows[3]['detail'],dict(cast_seconds=0,consumed=0))
        self.assertEqual(rows[4]['detail'],dict(cast_seconds=1.5,consumed=3))
        # Both timing interpretations are explicit, with exactly-on-boundary expiry.
        events=events[:2]+[dict(at=20,kind='observe'),dict(at=21,kind='observe')]
        a=self.run_replay('arcane',events)
        b=self.run_replay('arcane',events,heating_refresh='initial')
        self.assertEqual([r['heating_stacks'] for r in a[-2:]],[3,0])
        self.assertEqual([r['heating_stacks'] for r in b[-2:]],[0,0])

    def test_personal_effects_and_cap(self):
        effects=['fireball','ignite','improvedscorch','pyroblast','impact']
        events=[dict(at=0,kind='effect_apply',effect=e,owner='self',expires_at=10) for e in effects]
        events += [dict(at=0,kind='effect_apply',effect='frostfirebolt',owner='self',expires_at=20),
                   dict(at=0,kind='effect_apply',effect='fireball',owner='other',expires_at=20),
                   dict(at=10,kind='observe')]
        rows=self.run_replay('fire',events)
        self.assertAlmostEqual(rows[0]['fire_power_multiplier'],1.03)
        self.assertAlmostEqual(rows[4]['fire_power_multiplier'],1.12)
        self.assertEqual(rows[6]['fire_effects'],sorted(effects))
        self.assertEqual(rows[-1]['fire_power_multiplier'],1)

    def test_frost_consumption_range_and_shield(self):
        events=[dict(at=0,kind='barrier_apply'),dict(at=0,kind='lance_cast',frozen=True)]
        events += [dict(at=t,kind='frost_hit',spell='frostbolt',fingers_empowered=False,roll=0.99) for t in range(1,7)]
        events += [dict(at=7,kind='cone',hit=True,in_range=False),dict(at=8,kind='cone',hit=False,in_range=True),
                   dict(at=8,kind='lance_cast',frozen=False),dict(at=9,kind='cone',hit=True,in_range=True),
                   dict(at=10,kind='shield_break'),dict(at=60,kind='observe')]
        rows=self.run_replay('frost',events)
        self.assertEqual(rows[7]['winter_stacks'],5)
        self.assertEqual(rows[8]['winter_stacks'],5)
        self.assertEqual(rows[9]['winter_stacks'],5)
        self.assertEqual(rows[11]['detail']['damage_taken_multiplier'],2)
        self.assertAlmostEqual(rows[11]['detail']['extra_sp_coefficient'],0.35)
        self.assertEqual(rows[11]['winter_stacks'],0)
        self.assertEqual(rows[1]['detail']['damage_multiplier'],4)
        self.assertEqual(rows[10]['detail']['damage_multiplier'],1)
        self.assertEqual([rows[i]['barrier_damage_bonus'] for i in (0,12,13)],[0.2,0.15,0])
        alternate=self.run_replay('frost',events,cone_consumption='cast')
        self.assertEqual(alternate[9]['winter_stacks'],0)
        self.assertEqual(alternate[11]['detail']['damage_taken_multiplier'],1)

    def test_eligible_winter_triggers_and_expiry(self):
        events=[dict(at=i,kind='frost_hit',spell=s,fingers_empowered=f,roll=0) for i,(s,f) in enumerate([
            ('icelance',False),('icelance',True),('coneofcold',False),('frostfirebolt',False)])]
        events.append(dict(at=15,kind='winter_expire'))
        rows=self.run_replay('frost',events)
        self.assertEqual([r['winter_stacks'] for r in rows],[0,1,1,1,0])

    def test_invalid_replays_fail_in_both_ports(self):
        cases=[('frost',[dict(at=0,kind='lance_cast',frozen=True),dict(at=7.999,kind='lance_cast',frozen=True)]),
               ('fire',[dict(at=0,kind='barrier_apply')]),('fire',[dict(at=-1,kind='observe')]),
               ('arcane',[dict(at=1,kind='observe'),dict(at=0,kind='observe')]),
               ('fire',[dict(at=0,kind='fire_hit',spell='fireblast',crit=1,periodic=False)]),
               ('arcane',[dict(at=0,kind='barrage_roll',spell='arcaneblast',roll=1,expires_at=10)]),
               ('frost',[dict(at=0,kind='frost_hit',spell='frostblast',fingers_empowered=False,roll=0)]),
               ('frost',[dict(at=0,kind='unknown')])]
        for school,events in cases:
            with self.assertRaises(ValueError):replay(BUILDS[school],events,OPTIONS)
            self.assertFalse(js('current-combat.js','replay',BUILDS[school],events,OPTIONS)['ok'])
        with self.assertRaises(ValueError):replay(BUILDS['arcane'],[],dict(intellect=300,base_mana=1000))


if __name__=='__main__':unittest.main()
