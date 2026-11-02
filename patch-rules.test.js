'use strict';
const assert = require('node:assert/strict');
const r = require('./patch-rules.js');
const snapshots = [
  r.arcaneBlastSnapshot([], 0, 300, 1000),
  r.arcaneBlastSnapshot([0], 0, 300, 1000),
  r.arcaneBlastSnapshot([0, 4, 8, 12, 16], 17.999, 300, 1000),
  r.arcaneBlastSnapshot([0, 4, 8, 12, 16], 18, 300, 1000),
  r.arcaneBlastSnapshot([0, 4, 18], 18, 300, 1000),
  r.arcaneBlastSnapshot([0, 4], 5, 0, 0),
];
assert.deepEqual(snapshots.map(x => [x.stacks, x.expires_at, x.spell_damage_bonus, x.mana_cost]),
  [[0, null, 0, 150], [1, 18, 36, 300], [4, 18, 144, 750],
   [0, null, 0, 150], [1, 36, 36, 300], [2, 18, 0, 0]]);
assert.ok(snapshots.every(x => x.cast_seconds === 1.5));
assert.deepEqual([0,1,2,3].map(r.precisionHit), [0,0.02,0.04,0.06]);
for (const spell of ['fireball', 'frostfire', 'arcaneWrath']) {
  assert.equal(r.accelerantCastSeconds(spell, 3.5, 5), 3);
  assert.equal(r.accelerantCastSeconds(spell, 3.5, 0), 3.5);
}
assert.equal(r.accelerantCastSeconds('arcaneBlast', 1.5, 5), 1.5);
assert.equal(r.accelerantCastSeconds('frostbolt', 3, 5), 3);
for (const bad of [-1, 1.5, 4, Infinity, NaN, true]) assert.throws(() => r.precisionHit(bad));
for (const bad of [-1, 1.5, 6, Infinity, NaN, true]) assert.throws(() => r.accelerantCastSeconds('fireball', 3, bad));
for (const args of [[[1,0],2,300,1000], [[2],1,300,1000], [[-1],0,300,1000], [[],NaN,300,1000], [[],0,-1,1000]])
  assert.throws(() => r.arcaneBlastSnapshot(...args));
console.log(JSON.stringify(snapshots));
