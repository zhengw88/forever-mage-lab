# Current mechanics research layer

Snapshot: client **1.60.1.70707**, hotfix cache **30 October 2026**, retrieved
**2 November 2026 UTC**. This layer is separate from the historical DPS engines.
It does not establish a Fire, Arcane or Frost winner.

## Runnable pieces

```sh
python lab.py builds
python current_model_test.py
python generate_current_replay.py
python generate_current_replay.py --check
python lab.py validate
```

`current-talents.json` records all 53 talent names, rank limits, tier thresholds,
prerequisite edges and per-node source URLs. `current_talents.py` and
`current-talents.js` check rank limits, lower-tier points, prerequisite ranks and
the level-based budget. `current-builds.json` contains three 51-point research
candidates: Arcane 31/17/3, Fire 17/31/3, Frost 17/3/31. They pass the published
contract. They are not optimized builds or independently server-verified builds.
Multi-rank prerequisites conservatively require full ranks; the source pages
name the prerequisite, without exposing every server-side rank condition.

The new codec uses `#mage-70707-20261030:key=rank,...`, keyed by talent identity,
not screen position. Both ports reject a different version, duplicate keys,
unknown/removed talents and historical `#b-` strings. This is a library/CLI
format, not a working link into the historical webpage. The existing webpage
and old digit codec remain historical; new fragments are not wired into its UI.

`current_combat.py` and `current-combat.js` replay **explicit combat outcomes**
through the same state transitions. The replay integrates the previously
isolated Blast, Precision and Accelerant helpers with:

- Barrage trigger eligibility, rank-scaled probability and one-channel consumption;
- Heating Up from direct crits and Fire Blast, three-stack cap, expiration,
  Pyroblast cast-time reduction and Preservation under Presence of Mind;
- unique personal Fire effects, mixed-school exclusion and Fire Power's cap;
- Winter's Chill eligible hits, stack cap, next-Cone consumption and range;
- Ice Lance's eight-second cooldown and frozen multiplier;
- Ice Barrier's one-minute offensive aura and separate shield break.

A custom input object has `talents`, `options`, and `events`. Run it with
`python lab.py replay INPUT.json --output OUTPUT.json`. Example objects are in
`current-replay-cases.json` under `cases`. The generated
`current-replay-report.json` includes the three builds, identical hand-checkable
Intellect/base-mana inputs, explicit outcomes and source-code hashes.

These are mechanic fixtures, **not legal cast schedules or gear comparisons**.
For example, repeated Fire Blast hit events exercise the stack cap without
waiting for its cooldown. The reducer does not choose casts, schedule the GCD,
roll hit/crit, compute damage, spend mana or optimize rotations. Arcane Missiles
uses the level-60 five-missile channel. No DPS, sampling CI or spec ranking can
be inferred from these traces. Cast scheduling, mana, other passives, racials,
leveling and AoE integration are still unfinished work.

## Source decisions and unresolved behavior

Primary official evidence:
[Blizzard development notes](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-october-26/2360696).
The 15 October Mage section explains Wrath, Pyroblast/Presence of Mind and the
five qualifying personal Fire effects. Later client/cache evidence overrides
older notes for Blast, Barrage, Critical Mass, Ice Lance and Winter's Chill.

Current extraction:
[Talents Forever Mage tree](https://wowforevertalents.com/mage/),
[spellbook](https://wowforevertalents.com/abilities/mage/), and
[patch history](https://wowforevertalents.com/patch-notes/).
All 53 individual talent pages were checked for rank/tier/prerequisite facts.
The [70707 client comparison](https://foreverdb.net/changelog/1.60.1.70707)
independently reports the removed talents, Barrage/Resilience changes and
Accelerant. These are first-hand community extractions, not our own extraction
or server combat logs. No external simulator rankings or calibration are used.

| Area | Implemented fact | Explicit limit |
| --- | --- | --- |
| Blast | 12% Intellect per stack, four stacks, 18 seconds from first application, 100% extra cost per stack | `blast_aura` supplies application time; cast/impact ordering is not guessed |
| Barrage | Blast 20%/rank, other listed spells 10%/rank; Missiles cannot proc itself in this snapshot | Caller supplies proc roll and expiration; trigger phase and duration need validation |
| Heating Up | Fire Blast damage adds a stack, direct crit adds another, cap three, Pyro consumes unless PoM | `heating_refresh` must select refresh-on-gain or initial-expiry; a hit event is not a missed cast |
| Fire Power | 1%/rank per unique personal effect, at most four counted; Frostfire excluded as a contributor | Caller supplies actual personal effect applications/expirations; Ignite damage/rolling and Scorch stacks are not modeled |
| Winter's Chill | 20% Cone damage taken and 0.07 extra SP coefficient per stack, cap five | `cone_consumption` must select cast or landed-hit consumption; caller supplies expiration; formula ordering remains open |
| Ice Lance | Eight-second cooldown and 4x damage against frozen targets | Caller supplies frozen state; Fingers charge generation/spending and boss behavior remain open |
| Barrier | 0.15 offensive bonus persists after shield loss; 0.05 shield component ends on break | Output is an additive sum of tooltip bonuses, not a verified combined damage multiplier; stacking order remains open |

Equal-time events are processed in input order, expiration happens at the exact
boundary, and invalid/backward times fail. This is an explicit replay contract,
not proof that the server uses that ordering. Tests cover both Heating Up expiry
interpretations and both Cone miss-consumption interpretations. They produce
different states; uncertainty is not hidden in a single default.

`current-spell-evidence.json` records the current highest-rank Blast and Wrath
facts, separately from coefficient evidence. A follow-up primary extraction at
[Ladderly](https://ladderly.gg/forever/ranks?class=mage&spell=arcane-wrath) reports
Wrath coefficient 1 for build **70532**. That supplies a candidate value, but
70707/hotfix coverage has not been independently established here. It is retained
with its older build date, not promoted into a fully current spell snapshot.

## Validation and next work

Nine test groups independently check known outcomes and Python/JavaScript parity:
51-point budgets, tier/prerequisite failures, old-link rejection, Blast cap and
expiry, one-use Barrage, Fire Blast/PoM interaction, personal effects, Frost
range/consumption/shield behavior, and invalid event rejection. Expected values
are hand-derived (e.g. four Blast stacks at Intellect 300 give 144 spell damage;
five Winter stacks give 2x damage-taken factor and 0.35 extra coefficient).
The generated traces are produced only after these checks, and validation fails
if their hashes or outputs become stale.

Next: pin the remaining spell ranks and coefficients with hotfix coverage;
implement cast scheduling, resource recovery, hit/crit/proc RNG and damage
application using this event layer; validate server timing against logs; then
optimize and compare the three legal builds at identical gear, buffs, target,
ranks, encounter durations and uncertainty settings. Historical output cannot
become current merely by editing the ledger: `lab.py compare` explicitly requires
`--historical` until a separately validated current engine is wired in.
