"""Ranking arithmetic and certification guard; no hard-coded preferred school."""
import copy
import json
import unittest
import subprocess
from sim_engine import simulate
from sim_test import equal
from ranking_report import rank_rows, validate, ROOT

def row(school,mean,lo,hi):return dict(school=school,mean_dps=mean,ci95_sampling=[lo,hi])

class Rankings(unittest.TestCase):
    def test_order_gaps_ties_and_interval_overlap(self):
        rows=[row('arcane',80,79,81),row('frost',100,99,101),row('fire',95,94,100)]
        ranked=rank_rows(rows)
        self.assertEqual([r['school'] for r in ranked],['frost','fire','arcane'])
        self.assertAlmostEqual(ranked[1]['behind_leader_percent'],5)
        self.assertTrue(ranked[1]['leader_interval_overlap']);self.assertFalse(ranked[2]['leader_interval_overlap'])
        rows[0]=row('arcane',100,99,101)
        self.assertEqual([r['rank'] for r in rank_rows(rows)],[1,1,3])
        self.assertEqual(rank_rows(list(reversed(rows))),rank_rows(rows))

    def test_malformed_inputs(self):
        good=[row('arcane',80,79,81),row('frost',100,99,101),row('fire',95,94,100)]
        for bad in [good[:2],good[:2]+[good[0]],good[:2]+[row('fire',float('nan'),0,1)],good[:2]+[row('fire',0,0,1)],good[:2]+[row('fire',4,5,3)]]:
            with self.assertRaises(ValueError):rank_rows(bad)

    def test_selected_policy_cast_traces_in_both_engines(self):
        data=json.loads((ROOT/'provisional-rankings.json').read_text());cases=[]
        for case in data['cases']:
            for row in case['results']:
                cases.append(dict(school=row['school'],options=dict(case['options'],**row['rotation'],trace=True),build=row['talents']))
        script="const sim=require('./sim-engine.js');const cases=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(JSON.stringify(cases.map(c=>sim.simulate(c.school,c.options,c.build))));"
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(cases).encode(),cwd=ROOT))
        for case,js in zip(cases,actual):equal(simulate(**case),js,case['school'])
        self.assertEqual(len(actual),27)

    def test_report_guards_and_freshness(self):
        data=json.loads((ROOT/'provisional-rankings.json').read_text());validate(data)
        for key,value in [('status','validated'),('model_current',True),('certified_rankings_blocked',False)]:
            bad=copy.deepcopy(data);bad[key]=value
            with self.assertRaises(AssertionError):validate(bad)
        bad=copy.deepcopy(data);bad['cases'][0]['ranking'].reverse()
        with self.assertRaises(AssertionError):validate(bad)
        bad=copy.deepcopy(data);bad['input_sha256']['sim_engine.py']='stale'
        with self.assertRaises(AssertionError):validate(bad)

if __name__=='__main__':unittest.main(verbosity=2)
