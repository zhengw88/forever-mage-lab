# Rebuild status

Personal fork initialized on 2 November 2026 from upstream commit
`a3315522e2f1b085b6118d62891bc5db4ac6101e` (v1.3).
The original Python engines, JavaScript ports, source data, tests, and history are
preserved. This is a runnable foundation; the late-October mechanics migration is
**not complete**, and no current spec winner is claimed.

## What runs today

`python lab.py compare --historical --fights 1000 --seed 1 --seconds 300`
runs the lab's own expected-value optimizer and its cast-by-cast simulator for
Frost with Barrage, Fire with Arcane Blast, Arcane, and Arcane with Ignite.
It does not call another simulator or download rankings. JSON includes every
encounter option, talent allocation, input hashes, revision, damage breakdown,
mean DPS and a normal-approximation 95% confidence interval for sampling error.
That interval does not include uncertainty in mechanics or rotation quality.

`python lab.py compare` refuses to describe these historical engines as current.
The direct upstream scripts remain available for research; their numerical
outputs are historical too. Baseline presets are not optimized for the new tree.

## Migration order and acceptance checks

1. **Game data and talents.** Pin a complete spell/talent snapshot and hotfix
   layer. Replace removed talents, update rank limits and prerequisites, add
   Precision and Accelerant, and implement explicit share-link versioning.
   Validate 51-point builds for each school before comparing damage.
2. **Arcane.** Replace damage-consumed Blast stacks with the timed Intellect
   spell-power buff; add Wrath and the latest Barrage triggers. Test the fourth
   stack, expiration from the first application, mana cost at each stack,
   proc generation, channel timing and mana recovery.
3. **Fire.** Track personal fire effects for Fire Power, Fire Blast's Heating Up
   contribution and cooldown, Pyroblast consumption, Scorch and Ignite upkeep.
   Test crit/noncrit and simultaneous periodic damage cases separately.
4. **Frost.** Enforce Ice Lance's cooldown; remove old Winter's Chill crit;
   implement Cone of Cold consumption and range, and Ice Barrier's damage buffs.
   Test shield breaks, buff expiration, frozen multipliers and charge spending.
5. **Shared systems.** Revalidate racial effects, mana regen, hit/resistance,
   spell ranks and travel time. Keep uncertain rules as sensitivity switches.
   Update leveling wand timing and distinguish dungeon XP from open-world XP.
6. **Re-optimize and validate.** Compare 60/120/180/300-second encounters,
   identical gear and buffs, several gear levels, ranged/melee access, shield
   survival, and both mana-limited and unlimited-mana diagnostics. Re-run
   leveling and AoE separately; raid winners do not imply leveling winners.

A separate current research layer now loads all 53 talent nodes with source URLs,
checks three 51-point candidate builds, and provides a versioned keyed build codec.
Python and JavaScript event replay connect the Blast/Precision/Accelerant helpers
to Barrage, Heating Up, personal Fire effects, Winter's Chill, Ice Lance and Barrier
state. See `CURRENT-MECHANICS.md` for commands, evidence and unresolved behavior.

A new experimental layer now runs full cast schedules in `sim_engine.py` and
`sim-engine.js`: damage, mana, procs, cooldowns, rank selection and multi-target
throughput. `python lab.py experiment` compares all three schools with matched
settings. `current-experiments.json` contains a finite policy search and 33
sensitivity scenarios evaluated on held-out seeds. `current.html` runs the
JavaScript model in a local worker and exposes versioned build/settings links.
See `SIMULATION.md` for reproducibility, coverage and explicit hypotheses.

This advances the migration but does not certify current rankings. The full
70707 spell snapshot, server behavior, wider rotation/talent optimization and
realistic leveling survival remain unresolved. All mechanic entries remain
partial. The original page and its engines remain a labeled historical archive.

The owner explicitly requested a personal deployment in the current session.
Only `zhengw88/forever-mage-lab` may be published; no upstream write or automatic
PR merge is authorized. Subsequent routine maintenance must not auto-deploy.

## Updating the fork

```sh
git clone https://github.com/zhengw88/forever-mage-lab.git
cd forever-mage-lab
git remote add upstream https://github.com/opitaru-sys/forever-mage-lab.git
git fetch upstream
git log --oneline HEAD..upstream/main
git switch -c update/game-build-DATE
```

Review upstream changes before merging; do not reset this fork to upstream.
Follow `AGENTS.md` for maintenance. Open PRs against **this fork**, not upstream.

## Validation and known baseline limits

Python 3.12+ and Node 22+ are sufficient for numerical checks; no third-party
simulation dependency is required. `python lab.py validate` runs the existing
parity, option, weights, talent-builder and AoE checks, checks the current-version
guard and seeded reproducibility, tests the new mechanic primitives, and rebuilds
the page. The AoE suite skips an optional assumption-register check because that
external sibling-project file was never included upstream.

Browser testing additionally needs Python Playwright and Chromium:

```sh
python -m pip install playwright==1.51.0
python -m playwright install chromium
python tests/page_check.py
```

The previous audit found two failures on untouched upstream code as well as its
review copy: phone keyboard focus under the sticky talent panel at 390px and
talent-panel height changes at 800px. Numerical parity checks passed. These UI
failures remain open; do not relabel a partial UI suite as fully passing.

## Attribution

The original work and historical findings are preserved in `UPSTREAM.md` and
the repository history. The MIT license remains unchanged. Blizzard's icon art
is not covered by that license. Original source assumptions borrowed from other
sims still require independent review; the new runner does not remove that debt.
