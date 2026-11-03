'use strict';
// Same sourced primitives as patch_rules.py. Not connected to the old calculators.
// A browser caller can supply the same JSON to createPatchRules; Node loads it here.
function createPatchRules(rules) {
  function number(value, name) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0)
      throw new Error(name + ' must be a finite nonnegative number');
    return value;
  }
  function rank(value, maximum) {
    number(value, 'rank');
    if (!Number.isInteger(value) || value > maximum) throw new Error('rank outside talent limits');
    return value;
  }
  function arcaneBlastSnapshot(applications, now, intellect, baseMana) {
    number(now, 'now'); number(intellect, 'intellect'); number(baseMana, 'base mana');
    const cfg = rules.arcane_blast;
    let stacks = 0, expiry = null, previous = -1;
    for (const time of applications) {
      number(time, 'application time');
      if (time < previous || time > now) throw new Error('application times must be ordered and no later than now');
      previous = time;
      if (expiry === null || time >= expiry) { stacks = 0; expiry = time + cfg.duration_seconds; }
      stacks = Math.min(cfg.max_stacks, stacks + 1);
    }
    if (expiry !== null && now >= expiry) { stacks = 0; expiry = null; }
    return {stacks, expires_at: expiry,
      spell_damage_bonus: intellect * cfg.intellect_fraction_per_stack * stacks,
      mana_cost: baseMana * cfg.base_mana_fraction * (1 + stacks * cfg.cost_increase_per_stack),
      cast_seconds: cfg.cast_seconds};
  }
  function precisionHit(value) {
    return rules.precision.hit_fraction_per_rank * rank(value, rules.precision.max_rank);
  }
  function accelerantCastSeconds(spell, base, value) {
    number(base, 'base cast seconds');
    const cfg = rules.accelerant, points = rank(value, cfg.max_rank);
    return cfg.spells.includes(spell) ? Math.max(0, base - cfg.seconds_per_rank * points) : base;
  }
  return {arcaneBlastSnapshot, precisionHit, accelerantCastSeconds};
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = createPatchRules(require('./patch-rules.json'));
}
