"""Replay explicit combat outcomes through current mechanics, without inventing DPS.

This event reducer is the shared integration seam for a future cast scheduler and
combat-log checks. It is NOT a rotation optimizer or complete combat simulator.
Aura application, proc rolls, personal effects and unresolved ordering are inputs.
"""
import copy
from current_talents import errors
from patch_rules import arcane_blast_snapshot, accelerant_cast_seconds, precision_hit, number

FIRE_EFFECTS = {'ignite', 'improvedscorch', 'fireball', 'pyroblast', 'impact'}
BARRAGE_TRIGGERS = {'arcaneblast', 'arcanewrath', 'fireball', 'frostbolt', 'frostfirebolt'}
HEATING_TRIGGERS = {'fireball', 'frostfirebolt', 'fireblast', 'scorch'}


def replay(build, events, options):
    problems = errors(build)
    if problems:
        raise ValueError('; '.join(problems))
    if options.get('heating_refresh') not in ('refresh', 'initial'):
        raise ValueError('select heating_refresh: refresh or initial; server behavior unvalidated')
    if options.get('cone_consumption') not in ('cast', 'hit'):
        raise ValueError('select cone_consumption: cast or hit; miss behavior unvalidated')
    for key in ('intellect', 'base_mana'):
        number(options.get(key), key)
    applications, effects, output = [], {}, []
    heating, heating_until, wc, barrage_until, barrier_until, shield_until = 0, 0, 0, 0, 0, 0
    lance_ready, previous = 0, -1
    p = lambda key: build.get(key, 0)
    for event in events:
        now = number(event.get('at'), 'event time')
        if now < previous:
            raise ValueError('events must be chronological; equal times use input order')
        previous = now
        if now >= heating_until:
            heating = 0
        effects = {k: v for k, v in effects.items() if v > now}
        kind = event.get('kind')
        detail = {}
        def require(key):
            if not p(key):
                raise ValueError('talent required: ' + key)
        def flag(key):
            value = event.get(key)
            if type(value) is not bool:
                raise ValueError(key + ' must be boolean')
            return value
        def roll():
            value = number(event.get('roll'), 'proc roll')
            if value >= 1:
                raise ValueError('proc roll must be below 1')
            return value
        def expiry():
            value = number(event.get('expires_at'), 'expiry')
            if value <= now:
                raise ValueError('expiry must follow event')
            return value
        if kind == 'blast_aura':
            require('arcaneblast')
            applications.append(now)
        elif kind == 'barrage_roll':
            require('missilebarrage')
            spell, value, until = event.get('spell'), roll(), expiry()
            chance = ((0.2 if spell == 'arcaneblast' else 0.1) * p('missilebarrage')
                      if spell in BARRAGE_TRIGGERS else 0)
            triggered = value < chance
            if triggered:
                barrage_until = until
            detail = dict(chance=chance, triggered=triggered)
        elif kind == 'missiles_cast':
            empowered = now < barrage_until
            detail = dict(empowered=empowered, channel_seconds=2.5 if empowered else 5,
                          mana_multiplier=0 if empowered else 1,
                          tick_offsets=[(i+1)*(0.5 if empowered else 1) for i in range(5)])
            barrage_until = 0
        elif kind == 'fire_hit':
            spell, crit, periodic = event.get('spell'), flag('crit'), flag('periodic')
            if spell not in HEATING_TRIGGERS | {'pyroblast', 'ignite'}:
                raise ValueError('unsupported fire hit')
            added = (int(crit) + int(spell == 'fireblast')) if not periodic and spell in HEATING_TRIGGERS else 0
            if p('heatingup') and added:
                if heating == 0 or options['heating_refresh'] == 'refresh':
                    heating_until = now + 20
                heating = min(3, heating + added)
        elif kind == 'pyro_cast':
            require('pyroblast')
            pom = flag('presence_of_mind')
            if pom:
                require('presenceofmind')
            detail = dict(cast_seconds=0 if pom else 6 * (1 - 0.25 * heating), consumed=0 if pom else heating)
            if not pom:
                heating, heating_until = 0, 0
        elif kind == 'effect_apply':
            effect, owner, until = event.get('effect'), event.get('owner'), expiry()
            if effect not in FIRE_EFFECTS | {'frostfirebolt'} or owner not in ('self', 'other'):
                raise ValueError('unsupported effect or owner')
            if owner == 'self' and effect in FIRE_EFFECTS:
                effects[effect] = until
        elif kind == 'frost_hit':
            require('winterschill')
            spell, empowered, value = event.get('spell'), flag('fingers_empowered'), roll()
            if spell not in ('frostbolt', 'icelance', 'coneofcold', 'frostfirebolt'):
                raise ValueError('unsupported frost hit; Frost Blast is not trained')
            if spell == 'icelance':
                require('icelance')
                if empowered:
                    require('fingersoffrost')
            eligible = spell == 'frostbolt' or (spell == 'icelance' and empowered)
            triggered = eligible and value < 0.2 * p('winterschill')
            if triggered:
                wc = min(5, wc + 1)
            detail = dict(triggered=triggered)
        elif kind == 'winter_expire':
            # Exact duration is unresolved; caller supplies observed expiration.
            wc = 0
        elif kind == 'cone':
            hit, in_range = flag('hit'), flag('in_range')
            used = wc if in_range and (hit or options['cone_consumption'] == 'cast') else 0
            detail = dict(landed=hit and in_range, stacks_used=used,
                          damage_taken_multiplier=1 + (0.2 * wc if hit and in_range else 0),
                          extra_sp_coefficient=0.07 * wc if hit and in_range else 0)
            if used:
                wc = 0
        elif kind == 'lance_cast':
            require('icelance')
            frozen = flag('frozen')
            if now < lance_ready:
                raise ValueError('Ice Lance cooldown')
            lance_ready = now + 8
            detail = dict(damage_multiplier=4 if frozen else 1)
        elif kind == 'barrier_apply':
            require('icebarrier')
            # An aura application, not a cast: refresh legality is caller-owned.
            barrier_until, shield_until = now + 60, now + 60
        elif kind == 'shield_break':
            shield_until = 0
        elif kind != 'observe':
            raise ValueError('unknown event kind')
        blast = arcane_blast_snapshot(applications, now, options['intellect'], options['base_mana'])
        output.append(dict(at=now, kind=kind, detail=detail, blast=blast,
                           precision_hit=precision_hit(p('precision')),
                           wrath_cast_seconds=accelerant_cast_seconds('arcaneWrath', 3.5, p('accelerant')),
                           heating_stacks=heating, heating_expires_at=heating_until if heating else None,
                           fire_effects=sorted(effects), fire_power_multiplier=1 + 0.01*p('firepower')*min(4,len(effects)),
                           winter_stacks=wc, lance_ready_at=lance_ready,
                           barrier_damage_bonus=(0.15 if now < barrier_until else 0) + (0.05 if now < shield_until else 0),
                           barrage_active=now < barrage_until))
    return dict(schema=1, model='current-mechanics-replay', model_current=False,
                options=copy.deepcopy(options), talents=copy.deepcopy(build), events=output,
                caveat='Explicit outcome replay, not DPS or a spec ranking. See CURRENT-MECHANICS.md.')
