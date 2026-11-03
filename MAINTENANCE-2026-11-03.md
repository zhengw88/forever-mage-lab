# November 3 maintenance review

This change is based on personal foundation commit `f3d7a2f4364552dd75e10377b4e79117731f16ac`.
Upstream remains `a3315522e2f1b085b6118d62891bc5db4ac6101e` after a fresh fetch.
Only the authenticated personal account `zhengw88` is used. No upstream writes,
merge or deployment are part of this review.

## Evidence

- [Blizzard supplement](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-november-2/2360696): titled November 2, posted November 3 at 03:20 UTC, reviewed November 3. This consolidates work since October 15; it is not a newly extracted client build.
- [Dated hotfix extraction](https://wowforevertalents.com/patch-notes/): now includes a November 2 announced-change audit and China-only 70753 comparison. It reports the same talent trees as the October 30 hotfix cache; no new Mage numeric delta established. The Mage model remains pinned to 70707/October 30.
- [Client comparison](https://foreverdb.net/changelog/1.60.1.70707): extracted October 31 against 70658. No newer snapshot found.
- [Improved Fire Blast extraction](https://wowforevertalents.com/mage/talents/improved-fire-blast/): two ranks reduce Fire Blast by one/two seconds. It does not establish how the shared category inherits the reduction.
- [Official hotfix index](https://worldofwarcraft.blizzard.com/en-us/content-update-notes): generic October 30 entry lists other WoW products; not imported as Forever rules.

## First maintenance pass

Previously, Fire Blast and Ice Lance used independent timers. Both Python and
JavaScript now block either spell after casting the other. Untalented duration
is eight seconds. The replay layer adds an explicit `fireblast_cast` event;
`fire_hit` remains an outcome event, not proof of a legal cast.

The official supplement also corroborates existing Missile Barrage channel-start
consumption, preservation of simultaneous Clearcasting and Missiles eligibility
for Clearcasting. Regression tests cover these without changing their formulas.

The source ledger, spell evidence, generated data, replay fixtures, experiment
archive and day-one guide are refreshed. Historical engines, share links and
historical outputs are preserved. No MythicSim result was used.

## Hypotheses retained

The default shared timer inherits the triggering spell's duration: eight seconds
for Lance, six/seven/eight for Fire Blast according to its talent. The alternate
`shared_blast_lance_base=true` assumes an unreduced eight-second category.
Cold Snap resets Frost timers only by default; `cold_snap_resets_fireblast=true`
tests a category-wide reset. Neither interaction is certified server behavior.

The notes identify Flamestrike/Ignite behavior beyond the initial hit, proc-root
diminishing returns, corrected racial base stats and higher-level creature health
changes. Exact proc scope, DR parameters and replacement tables are not established.
The follow-up below implements conditional Flamestrike eligibility; other missing values remain pending rather than guessed. Low-rank Blizzard proc penalties
also need quantified evidence; this scheduler uses the highest available rank.

## First-pass matched comparisons

All three use level 60, 120 seconds, one +3-level target at 30 yards, 500 spell
power, 300 Intellect, 120 Spirit, 10% input crit, 11% input hit and 65 mp5.
Race is none; identical consumable, resistance, book and timing settings apply.
Three 51-point presets pass the versioned tree's conservative legality contract.
That contract still needs in-game prerequisite validation. Training seeds 1–60
select from 26 finite policies; held-out seeds 10001–10200 evaluate each school.

| School | Mean research DPS | 95% sampling interval | Mean mana downtime |
| --- | ---: | --- | ---: |
| Arcane | 462.27 | 458.60–465.94 | 0.76s |
| Fire | 524.14 | 518.57–529.71 | 4.70s |
| Frost | 444.36 | 441.04–447.69 | 0.00s |

All 93 school/scenario result records from the prior 31-scenario archive remain
numerically unchanged: these preset policies do not alternate Fire Blast and
Lance. The regenerated archive adds two matched cases, for 33 total scenarios.
The fixed-eight-second category probe moves Fire to 515.59 DPS (510.42–520.76),
about 1.63% below its baseline; Arcane/Frost are unchanged. The Cold Snap probe
has no throughput impact on these presets. Spell breakdowns, mana use and full
inputs are stored in `current-experiments.json`.

**These are model diagnostics, not current spec rankings.** Sampling intervals
exclude mechanic, coefficient, talent legality, survival and rotation uncertainty.
Complete current rank/coefficient extraction and combat-log validation remain
blockers. No claim that Fire or Arcane beats Frost in the game is supported yet.

## Validation

- `python lab.py validate`: PASS. Includes 3 primitive, 10 talent/replay and 17 simulator test groups; 51 seeded Python/JavaScript full traces; 51 sequential guide allocations; fresh data/replay/experiment artifacts; 24 historical builder groups; 63 raid, 2,425 option, 569 weight, 771 leveling and 423 AoE checks; provenance and blocked-ranking guard.
- `python build_personal_site.py` and `python tests/current_page_check.py`: PASS at 390, 800 and 1280 pixels, including exact guide/build handoff and Python-checked kill/recovery results.
- `python tests/page_check.py`: 29/31. Same two documented historical baseline failures: keyboard focus under the sticky panel at 390px and panel-height changes at 800px. No historical UI source was changed.
- `git diff --check`: PASS. Prior 93 scenario result records remain equal; all generated archive input hashes match.

The optional external AoE assumption register remains absent/skipped, as before.
Local validation used Python 3.12 and Playwright 1.51.0 / Chromium 134.


## Follow-up: all Mage bullets

`MAGE-NOV2-COVERAGE.md` maps all 21 Mage bullets to implementation and tests,
including the client-only Iceknife visual change. Added paired defensive replay
for Arcane Resilience and Frost Warding, using dated extraction values and explicit
shield capacity/hit inputs. Both schedulers now report passive defensive statistics.
They still do not simulate incoming damage or survival.

Flamestrike's later critical ticks can now add Ignite, with no recursive proc or
double application of damage multipliers. Noncritical ticks, stale ticks and dead
targets cannot create Ignite. Repeated direct hits and independent target banks
are regression-tested. Periodic critical capability remains a hypothesis; the
new paired AoE cases test both Ignite interpretations with identical inputs.

The refreshed extraction index now reports China-only client 70753 dated November
2, with talent trees matching the October 30 cache. This updates the earlier
source-review statement; it does not justify relabeling the incomplete spell data
as a complete 70753 snapshot.

The follow-up archive contains 35 matched scenarios. All 99 result records from
its 33-scenario predecessor are unchanged, including the single-target baseline.
The two new four-target cases use 120 seconds, distance 8, equal-level safe targets,
and otherwise baseline gear/settings. They enable periodic criticals in all
three schools, then toggle only Flamestrike periodic Ignite eligibility. Both
use the same fixed policies and held-out seeds 10001–10200.

| School | Periodic Ignite enabled: DPS (sampling 95%) | Disabled: DPS (sampling 95%) | Mana downtime, both |
| --- | --- | --- | --- |
| Arcane | 464.79 (460.82–468.76) | 464.79 (460.82–468.76) | 48.31s |
| Fire | 654.60 (645.59–663.61) | 638.31 (629.40–647.21) | 25.83s |
| Frost | 758.74 (746.87–770.60) | 758.74 (746.87–770.60) | 21.38s |

Fire's +2.55% difference is a model sensitivity, not a measured live buff. These
runs also enable Blizzard periodic criticals through the shared research option;
the table cannot establish which school wins in game. Complete per-spell damage,
mana usage, talents and settings are in the generated archive.

### Follow-up validation

- PASS `python lab.py validate`: 3 primitive groups, 14 talent/replay groups,
  20 scheduler groups including 57 full cross-language traces, 51 guide point
  allocations, all historical numerical suites, fresh generated artifacts and
  blocked-ranking/provenance guards. Optional external AoE assumption-register
  check remains skipped because that file is absent upstream.
- PASS `python build_personal_site.py`; coverage ledger included in its artifact.
- PASS `python tests/current_page_check.py`: 390/800/1280px, guide handoff,
  recovery/kill metrics, timeout handling and historical-share redirect.
- `python tests/page_check.py`: 29/31, same documented baseline failures for
  keyboard focus at 390px and panel-height changes at 800px. No historical UI
  source changed; these failures remain open.
- PASS `git diff --check`. All prior 99 school/scenario result records unchanged.

No merge or deployment. Current rankings remain blocked.
