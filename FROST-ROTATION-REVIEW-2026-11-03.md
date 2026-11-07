# Frost rotation review — November 3, 2026

Practical guidance for the personal day-one companion, with separate exploratory
level-60 candidates. This does not certify a rotation, change the talent point
order, or update the displayed three-school ranking. `model_current` remains
false. No MythicSim results were used.

## What to use in game

Follow the [day-one priority guide](leveling.html#frost-rotation), adding steps only
when their spells/talents unlock. The 12/0/39 leveling allocation has Ice Barrier
at 40 and Missile Barrage at 46–47; it does **not** have Arcane Blast.

Prepare with Barrier when affordable, pull with Frostbolt, use useful empowered
Ice Lances, and cash in Winter's Chill with Cone only when safe. Use free Barrage
channels when stationary time and target health justify them. For sustained
mana-limited fights, try saving expensive five-stack Cones for Clearcasting.
Control, survival and finishing a kill can override a damage-only priority.

Do not routinely cancel a useful cast on every proc, wait idle for Lance's shared
cooldown, or move into danger just to land Cone. Keep empowered Lance available:
its unresolved scaling makes a stationary-model recommendation to omit it unsafe.
A last-charge Frostbolt/Lance “ghost” interaction has not been server validated.
Cold Snap's best damage schedule and a precise Blizzard target-count breakpoint
were not optimized. Defensive resets and safe channels take precedence while
learning.

## Source evidence and freshness

Reviewed November 3 UTC against the November 2 official supplement and dated
70707 / October 30 hotfix-cache extraction. Extracted tooltips are not server
validation. References are attached to individual claims below.

| Source | Relevant evidence | Consequence |
| --- | --- | --- |
| [Blizzard November 2 notes, post 9](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-november-2/2360696/9) | Barrage is consumed at channel start; enhanced Missiles preserve Clearcasting; Missiles can trigger Clearcasting. Low-rank Blizzard retains a proc penalty when learned more than 12 levels below the caster. | Consider the free channel and a subsequent expensive spell; do not assume full procs from old Blizzard ranks. The optimal ordering of simultaneous procs is unresolved. |
| [Ice Barrier extraction](https://wowforevertalents.com/mage/talents/ice-barrier/) | One-minute 15% Frost aura, another 5% while shielded; 30-second cooldown. | Maintain the aura; refresh earlier if defense warrants the mana/global cost. |
| [Winter's Chill extraction](https://wowforevertalents.com/mage/talents/winter-s-chill/) | Five-stack limit; each stack strengthens Cone, which consumes stacks. | Test five-stack Cone with range and mana accounted for. Obsolete Frost Blast references are not recommendations to use that removed spell. |
| [Ice Lance extraction](https://wowforevertalents.com/mage/talents/ice-lance/) and [Fingers of Frost](https://wowforevertalents.com/mage/talents/fingers-of-frost/) | Lance has an eight-second shared Fire Blast cooldown and frozen-target bonus; Fingers supplies limited charges. | Use empowered instants meaningfully; a slow alone is not a freeze. Exact scaling and charge timing need logs. |
| [Arcane Blast extraction](https://wowforevertalents.com/mage/talents/arcane-blast/) | Stacks add spell power based on Intellect and increase Blast cost; expiration is 18 seconds from the initial application. | Test modest stacks; additional casts do not restart the window. |
| [Missile Barrage extraction](https://wowforevertalents.com/mage/talents/missile-barrage/) | Free Missiles with half channel time; two talent ranks. | Use only after buying the talent and when a channel is practical. |
| [Dated patch/cache comparison](https://wowforevertalents.com/patch-notes/) and [70707 extraction changelog](https://foreverdb.net/changelog/1.60.1.70707) | Latest listed November 2 changes; the China-only 70753 build does not establish a new Mage contract beyond the October 30 cache. | Keep build and hotfix evidence separate. |

A [hotfix tracker](https://1mw.io/en/news) reported a 59-change batch at November 3
01:10 UTC (November 2 Pacific). Its linked Raidbots page did not expose a readable
Mage-specific diff during review. No mechanics were inferred from the batch count.
See also the [21-bullet November 2 coverage audit](MAGE-NOV2-COVERAGE.md).

## Exploratory method

The preceding research used temporary Python subclasses of the existing
`sim_engine.Fight`, changing only the spell-selection priority. The production
Python and JavaScript engines were not changed. The initial no-Blast policy was
checked against the production output for 20 seeds before probing alternatives.
These exploratory scripts were not promoted into the maintained simulator; this
report preserves the method and qualitative candidates, not a new reproducible
ranking release. The published ranking archive remains the reproducible baseline.

The expanded probe fixed the legal 17/3/31 Frost research preset, with Arcane Blast
and Missile Barrage but no Improved Cone of Cold. Each fight used level 60 Troll,
500 spell power, 300 Intellect, 120 Spirit, 10% base crit, 11% bonus hit, 65 mp5,
one target three levels higher, full initial mana, consumables/Evocation/cooldowns
enabled, 6% partial resistance, a 1% miss floor and 10 seconds of shield life.
No movement, incoming attacks, latency, pushback or prepull casting was modeled.
The default Cold Snap behavior was inherited, not independently optimized.

Search dimensions: 0/1/2/4 Blast stacks; Barrage on/off; Barrier refresh 30/60
seconds; empowered Lance on/off; and, in range, Cone off/three stacks/five stacks/
five plus Clearcasting/five plus Fingers of Frost. This gives 32 ranged and 160
close-range policies at each of 120 and 300 seconds. Fifty training seeds
(101–150) selected the top three and the best per Cone category; selected policies
were evaluated on 400 disjoint seeds (40001–40400). This is a finite policy search,
not exhaustive talent or rotation optimization. Sampling precision cannot remove
mechanical uncertainty or selection bias.

Policy order was Barrier, eligible Cone, empowered Lance if enabled, Barrage
Missiles, Blast below the target stack count, then Frostbolt. In particular, the
probe does **not** prove that casting Barrage Missiles before an already eligible
Clearcasting Cone is optimal.

| Encounter | Candidate from the limited probe |
| --- | --- |
| 120 seconds, 30 yards | Two Blast stacks per window, Barrage and Frostbolt |
| 120 seconds, 8 yards | One Blast stack, five-stack Cone |
| 300 seconds, 30 yards | One Blast stack to limit mana pressure |
| 300 seconds, 8 yards | One Blast stack, five-stack Cone mainly on Clearcasting |

Barrier refresh at 60 seconds beat 30 seconds under the assumed shield life;
that does not measure defensive value or long-lived shields. Four-stack cycling
was weak in these mana-limited cases. The exact in-game choice needs the player's
gear, movement, target lifetime and damage taken.

Ice Lance sensitivity was decisive: keeping the same 120-second ranged two-stack
policy, 400 separate seeds (50001–50400) compared using/skipping empowered Lance
at coefficients 0, 0.143 and 0.429. Skipping won at zero; using won at the positive
values. Those positive coefficients were hypothetical sensitivity inputs, **not**
verified current spell coefficients. No numerical DPS recommendation is published
from this probe.

## What the live simulator currently supports

The new Blast/Cone candidates are **not selectable live policies**. Its production
Frost baseline does not cast Arcane Blast, even though the research preset buys
that talent. Its existing published Frost ranking search is narrower than this
probe. Do not read the displayed three-school rankings as incorporating these
new Frost candidates, and do not apply the 17/3/31 results to 12/0/39 leveling.

Use the day-one form to load the exact leveling allocation, compare matched gear
and target settings, and inspect kill time, mana and recovery. Validate useful
changes over comparable real pulls including drinking, deaths and travel. Moving
the new policies into the interactive simulator will require paired Python/JS
implementation, cast-by-cast parity, matched three-school reruns and evidence
review; that is still open.


## November 6 evidence follow-up

The official Arcane Blast duration correction matches the modeled 18 seconds.
It does not establish pre-fix server performance or a new ranking. Numerical
results retain their original inputs and dates; no talent-order optimization is
claimed. See [the source review and remaining limits](CURRENT-MECHANICS.md#november-6-mage-hotfix-review-november-7-utc).
