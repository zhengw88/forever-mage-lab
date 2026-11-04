# Best-pass interpretation — November 3, 2026

**Provisional and conditional on the implemented model.** The request now explicitly
authorizes a useful best estimate while keeping certification blocked. No new spell
numbers, rankings from other simulators, or tuning targets were imported.

## What I would choose from these results

- Short/medium stationary single-target endgame fights (60–180 seconds): **Fire** is
  the current model's leading candidate. The short-fight baseline has no reliable
  reason to claim Frost always wins.
- Long mana-limited single-target fights (300 seconds): **Frost** leads. Arcane and
  Fire are close behind each other; their sampling intervals overlap. Their exact
  second/third placement is less useful than Frost's modeled mana endurance.
- Four equal-level safe targets at 8 yards: **Frost > Fire > Arcane** by mean DPS,
  with only about 4% between Frost and Fire. This is not a dungeon or leveling
  survival ranking and is sensitive to the limited AoE policies implemented.
- Mostly solo day-one questing: retain the existing **Frost leveling plan** as a
  practical authored choice. This calculation cannot measure control, deaths,
  travel, contested mobs or group efficiency, so it does not prove an XP/hour winner.

## Troll results

Same level-60 gear, single +3 target, 30 yards, enabled consumables/evocation,
100 training seeds per policy, 500 separate evaluation seeds. DPS rounded below;
full precision, spell breakdowns and mana diagnostics are in the generated JSON.

| Encounter | Best-pass order | 95% sampling intervals |
| --- | --- | --- |
| 120 seconds | Fire 524; Arcane 460; Frost 450 | Fire 520.75–527.98; Arcane 457.61–462.57; Frost 447.96–452.09 |
| 300 seconds | Frost 433; Arcane 395 ≈ Fire 392 | Frost 431.72–434.95; Arcane 392.89–397.02; Fire 389.62–394.27 |

The tests use 15-second Berserking. The separate existing archive retains the
10-second older extracted-tooltip alternative. The November 3 build 70755 racial extraction now corroborates 15 seconds (see CURRENT-MECHANICS.md). Neither in-game racial timing nor all baseline
stats are independently server-validated.

## Why this is not a universal tier list

With 8-yard Cone access, a 60-second shield and Ice Lance coefficient 0.143,
Frost reaches 526 DPS versus Fire 521, with overlapping sampling intervals.
At coefficient 0.429 under those same favorable assumptions it reaches 580.
These combined probes are deliberately chosen hypotheses, not confidence bounds
or a claim that the shield survives an actual encounter. They show a plausible
mechanism for the baseline order to change, without assigning a probability.

The encounter-specific search also improves Arcane's 300-second policy to one
Blast stack and its AoE policy to no Blast/Wrath; carrying the 120-second policy
into those fights understated its available modeled performance. The three talent
presets remain fixed. Policy selection uses training means; the selected policy
can underperform another candidate on unseen seeds. Sampling intervals do not
include that selection uncertainty or missing mechanics.

## Artifacts and validation

`provisional-rankings.json` and `PROVISIONAL-RANKING.md` contain nine new searches
and all 35 existing fixed-policy sensitivity cases. The research page presents
the estimates with Troll/120 seconds selected initially. No historical result or
mechanic engine changed. All comparisons use matched gear and encounter inputs
within each case. The certification and historical release guards stay active.

Source review: the November 2 official supplement and dated extraction index were
rechecked; no new numerical Mage delta was adopted. Upstream remains a331552.
The prior mechanics PR passed both GitHub checks before this ranking branch.
Validation details for this branch are recorded in its PR. No merge or deployment.
