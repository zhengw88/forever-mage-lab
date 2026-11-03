"""Hand-calculated boundary cases, independent of legacy engine fixtures."""
import json
from pathlib import Path
import subprocess
import unittest
import patch_rules as r


class PatchRulesTests(unittest.TestCase):
    def test_stack_expiration_and_port_parity(self):
        cases = [([], 0, 300, 1000), ([0], 0, 300, 1000),
                 ([0, 4, 8, 12, 16], 17.999, 300, 1000),
                 ([0, 4, 8, 12, 16], 18, 300, 1000),
                 ([0, 4, 18], 18, 300, 1000), ([0, 4], 5, 0, 0)]
        expected = [(0, None, 0, 150), (1, 18, 36, 300), (4, 18, 144, 750),
                    (0, None, 0, 150), (1, 36, 36, 300), (2, 18, 0, 0)]
        snapshots = [r.arcane_blast_snapshot(*case) for case in cases]
        for actual, want in zip(snapshots, expected):
            self.assertEqual(tuple(actual[k] for k in ('stacks', 'expires_at', 'spell_damage_bonus', 'mana_cost')), want)
            self.assertEqual(actual['cast_seconds'], 1.5)
        output = subprocess.check_output(['node', 'patch-rules.test.js'], cwd=Path(__file__).parent, text=True)
        self.assertEqual(snapshots, json.loads(output))

    def test_talent_ranks_and_scope(self):
        self.assertEqual([r.precision_hit(n) for n in range(4)], [0, .02, .04, .06])
        for spell in ('fireball', 'frostfire', 'arcaneWrath'):
            self.assertEqual(r.accelerant_cast_seconds(spell, 3.5, 5), 3)
            self.assertEqual(r.accelerant_cast_seconds(spell, 3.5, 0), 3.5)
        self.assertEqual(r.accelerant_cast_seconds('frostbolt', 3, 5), 3)
        self.assertEqual(r.accelerant_cast_seconds('arcaneBlast', 1.5, 5), 1.5)

    def test_invalid_inputs_rejected(self):
        for bad in (-1, 1.5, 4, float('inf'), float('nan'), True):
            with self.assertRaises(ValueError):
                r.precision_hit(bad)
        for bad in (-1, 1.5, 6, float('inf'), float('nan'), True):
            with self.assertRaises(ValueError):
                r.accelerant_cast_seconds('fireball', 3, bad)
        for args in (([1, 0], 2, 300, 1000), ([2], 1, 300, 1000), ([-1], 0, 300, 1000),
                     ([], float('nan'), 300, 1000), ([], 0, -1, 1000)):
            with self.assertRaises(ValueError):
                r.arcane_blast_snapshot(*args)


if __name__ == '__main__':
    unittest.main()
