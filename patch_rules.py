"""Late-October mechanic primitives; not yet integrated with the historical engines.

Applications are explicit aura events. The caller must supply their timing;
this module does not assume whether a server applies them on cast or impact.
"""
import json
import math
from pathlib import Path

RULES = json.loads(Path(__file__).with_name('patch-rules.json').read_text())


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return value


def rank(value, maximum):
    number(value, 'rank')
    if value != int(value) or value > maximum:
        raise ValueError('rank outside talent limits')
    return int(value)


def arcane_blast_snapshot(applications, now, intellect, base_mana):
    """Reconstruct active stacks and the NEXT cast's unmodified base mana cost.

    The aura expires at its boundary; later stacks never refresh that boundary.
    Mana talents, cooldowns, hit rolls and the GCD belong to the combat engine.
    """
    for value, name in ((now, 'now'), (intellect, 'intellect'), (base_mana, 'base_mana')):
        number(value, name)
    cfg = RULES['arcane_blast']
    stacks, expiry, previous = 0, None, -1
    for time in applications:
        number(time, 'application time')
        if time < previous or time > now:
            raise ValueError('application times must be ordered and no later than now')
        previous = time
        if expiry is None or time >= expiry:
            stacks, expiry = 0, time + cfg['duration_seconds']
        stacks = min(cfg['max_stacks'], stacks + 1)
    if expiry is not None and now >= expiry:
        stacks, expiry = 0, None
    return dict(stacks=stacks, expires_at=expiry,
                spell_damage_bonus=intellect * cfg['intellect_fraction_per_stack'] * stacks,
                mana_cost=base_mana * cfg['base_mana_fraction'] * (1 + stacks * cfg['cost_increase_per_stack']),
                cast_seconds=cfg['cast_seconds'])


def precision_hit(rank_value):
    return RULES['precision']['hit_fraction_per_rank'] * rank(rank_value, RULES['precision']['max_rank'])


def accelerant_cast_seconds(spell, base_seconds, rank_value):
    number(base_seconds, 'base cast seconds')
    cfg = RULES['accelerant']
    points = rank(rank_value, cfg['max_rank'])
    return max(0, base_seconds - cfg['seconds_per_rank'] * points) if spell in cfg['spells'] else base_seconds
