# November 2 Mage coverage

Audited 2026-11-03 against [Blizzard post 9](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-november-2/2360696/9).
Scope: all 21 Mage bullets in that supplement. Implemented means executable
source-contract behavior, **not server validation**. Rankings remain blocked.

| Change | Executable coverage | Verification |
| --- | --- | --- |
| Iceknife root visual | Non-numerical client change; no visual or stun modeled | Recorded here; weapon procs outside scheduler scope |
| Frost Blast removal | Absent from current spellbook | `test_removed_spell_and_defensive_stats` |
| Barrage consumed on channel start | Both schedulers | `test_missiles_channel_timing` |
| Barrage row 2 | Versioned talent tree | `test_november_talent_contract` |
| Resilience row/ranks/armor | Talent tree; both replays and scheduler passive statistics | `test_defensive_rank_values_and_negation_boundaries` |
| Clearcasting preserved with Barrage | Both schedulers | `test_missiles_clearcasting_proc_and_preservation` |
| Missiles can proc Clearcasting | Both schedulers; first landed missile per channel hypothesis | Same test; proc cadence needs logs |
| Arcane Focus removal | Current tree rejects old key | `test_rank_budget_tier_and_prerequisite` |
| Blast cost/buff/duration | Both schedulers and replay primitives | `test_blast_stack_timer_and_cost`, primitive tests |
| Later Flamestrike Ignite eligibility | Repeated direct hits and later critical ticks in both schedulers; explicit outcomes in replay | `test_flamestrike_repeated_direct_hits`, `test_flamestrike_later_ticks_and_targets`, explicit replay test |
| Incineration ranks | Tree and all eligible crit calculations | Talent contract and full traces |
| Accelerant rename/Wrath casting | Tree, primitives, schedulers and replay | Primitive and full-trace tests |
| Critical Mass ranks | Tree and Fire crit calculations | Talent contract and full traces |
| Improved Fire Blast row 3 | Versioned tree | Talent contract |
| Piercing Ice removal | Current tree rejects old key | Talent legality tests |
| Barrier offensive buffs | Both schedulers and replay | `test_frost_consumption_range_and_shield`, `test_cone_order_and_consumption` |
| Frost Warding absorption | Both replay ports; scheduler reports passive multiplier | `test_barrier_absorption_and_overlap` |
| Warding negation replaces reflection | Both replay ports; chance boundaries, no shield depletion, zero reflected damage | Defensive rank/overlap tests |
| Precision rename/all-school hit | Tree, primitives, both schedulers and replay | Primitive and legality tests |
| Lance cooldown/frozen bonus | Both schedulers and replay; shared Fire Blast timer | Shared-cooldown boundary and replay tests |
| Winter's Chill Cone bonus | Both schedulers and replay | Cone/order/consumption tests |

## New evidence and scope

[Frost Warding extraction](https://wowforevertalents.com/mage/talents/frost-warding/)
reports 10/20% additional absorb capacity and 10/20% Frost Ward negation chance,
plus 15/30% armor-spell armor/resistance bonuses.
[Arcane Resilience extraction](https://wowforevertalents.com/mage/talents/arcane-resilience/)
reports armor equal to 25/50/75% of Intellect. Both pages identify client 70707
and the October 30 cache, retrieved November 3. These are community extractions,
not independently reproduced client dumps or combat-log validation.

[Ignite extraction](https://wowforevertalents.com/mage/talents/ignite/) retains
8% critical damage per talent rank. The official Flamestrike fix does not spell
out periodic critical capability. `periodic_crit` remains false by default;
`flamestrike_periodic_ignite` defaults true and only matters for critical ticks.
The alternative false setting tests an interpretation limited to later direct
instances. Neither interpretation is certified. Other periodic spells are unchanged.
Ignite does not recursively trigger itself or reapply damage multipliers.

Defense replay requires observed **base** shield capacity and post-mitigation
incoming damage. It multiplies capacity once, accepts explicit proc rolls and
requires absorb order when Barrier and Ward overlap. Negation is evaluated
before depletion under either supplied order; server ordering still needs logs.
Expirations and exact depletion remove only the shield component of Barrier's
bonus; its minute-long offensive aura survives. Missing capacity is rejected
when incoming damage is requested. Resilience reports armor, not invented damage
reduction. Replay Intellect must already include buffs/talents; the scheduler
uses its computed Intellect. `armor_spell_multiplier` applies to both armor and
resistances granted by Frost/Ice Armor, not total character armor or resistance.

The throughput scheduler still assumes safe targets and models Barrier survival
as an input duration. Defense replay does **not** make its leveling XP/hour a
survival prediction. Full current spell/rank coefficients, server proc timing,
prerequisites, root DR parameters and racial/creature stat tables remain blockers.
The shared-system proc-root change is tracked separately in `lab-state.json`;
no unverified DR timer was silently assigned. No MythicSim calibration is used.
