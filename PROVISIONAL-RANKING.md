# Provisional Mage ranking — November 3, 2026

**Best available model estimate; not a validated in-game ranking.**

Policies are reselected for each encounter from 26 candidates on seeds 1–100; each selected school then runs 500 held-out fights on seeds 20001–20500. Builds pass the extracted tree contract, not server verification. No MythicSim calibration.

Shared baseline: level 60, 500 spell power, 300 Intellect, 120 Spirit, 10% input crit, 11% input hit, 65 mp5, one +3 target at 30 yards. Consumables/evocation enabled, books off. Troll uses the modeled 15-second racial. Four-target cases instead use equal-level targets at 8 yards.

| Encounter | Provisional order by mean DPS |
| --- | --- |
| Single target · 60 seconds | Fire 579.7 > Arcane 517.3 > Frost 441.9 |
| Single target · 120 seconds | Fire 521.4 > Arcane 463.7 > Frost 444.2 |
| Single target · 180 seconds | Fire 467.2 > Arcane 446.1 > Frost 440.7 |
| Single target · 300 seconds | Frost 430.5 > Arcane 394.6 > Fire 392.4 |
| Troll · single target · 120 seconds | Fire 524.4 > Arcane 460.1 > Frost 450.0 |
| Troll · single target · 300 seconds | Frost 433.3 > Arcane 395.0 > Fire 391.9 |
| Four safe targets · 120 seconds | Frost 595.2 > Fire 572.1 > Arcane 552.8 |
| Frost sensitivity · Cone access + shield + 0.143 scaling | Frost 526.3 > Fire 521.4 > Arcane 463.7 |
| Frost sensitivity · Cone access + shield + 0.429 scaling | Frost 580.1 > Fire 521.4 > Arcane 463.7 |

## Interpretation

Use the short/medium single-target cases when choosing a damage spec for those fights, and check the 300-second cases when mana limits matter. The four-target comparison is throughput against safe stationary targets. Keep the existing Frost solo-leveling plan as an authored practical recommendation; this report cannot validate survival or XP/hour.

Arcane versus Frost is encounter-sensitive. Check the combined Frost probes before treating the baseline order as universal. Overlapping sampling intervals are flagged; non-overlap still does not resolve systematic model errors.

## Detailed reproducibility

### Single target · 60 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Fire | 579.73 | 575.90–583.57 | 0.00% | 0.00s |
| Arcane | 517.29 | 513.87–520.70 | 10.77% | 0.00s |
| Frost | 441.88 | 438.98–444.78 | 23.78% | 0.00s |

Selected policies: `{"arcane": {"ab_stacks": 4, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": true, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Single target · 120 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Fire | 521.43 | 517.98–524.88 | 0.00% | 5.10s |
| Arcane | 463.69 | 461.56–465.82 | 11.07% | 0.60s |
| Frost | 444.18 | 442.12–446.24 | 14.81% | 0.00s |

Selected policies: `{"arcane": {"ab_stacks": 3, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": true, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Single target · 180 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Fire | 467.24 | 464.08–470.40 | 0.00% | 32.03s |
| Arcane | 446.10 | 444.40–447.79 | 4.53% | 1.20s |
| Frost | 440.70 | 438.76–442.63 | 5.68% | 0.00s |

Selected policies: `{"arcane": {"ab_stacks": 2, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": true, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Single target · 300 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Frost | 430.54 | 428.98–432.09 | 0.00% | 3.31s |
| Arcane | 394.62 | 392.61–396.63 | 8.34% | 41.45s |
| Fire | 392.37 | 389.94–394.80 | 8.86% | 53.41s |

Selected policies: `{"arcane": {"ab_stacks": 1, "use_wrath": true}, "fire": {"pyro_stacks": 2, "use_fireblast": false, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Troll · single target · 120 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Fire | 524.36 | 520.75–527.98 | 0.00% | 6.33s |
| Arcane | 460.09 | 457.61–462.57 | 12.26% | 0.00s |
| Frost | 450.02 | 447.96–452.09 | 14.18% | 0.00s |

Selected policies: `{"arcane": {"ab_stacks": 2, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": true, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Troll · single target · 300 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Frost | 433.33 | 431.72–434.95 | 0.00% | 4.69s |
| Arcane | 394.95 | 392.89–397.02 | 8.86% | 44.73s |
| Fire | 391.95 | 389.62–394.27 | 9.55% | 58.84s |

Selected policies: `{"arcane": {"ab_stacks": 1, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": false, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Four safe targets · 120 seconds

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Frost | 595.17 | 591.18–599.17 | 0.00% | 22.34s |
| Fire | 572.05 | 567.05–577.05 | 3.88% | 32.31s |
| Arcane | 552.76 | 550.07–555.46 | 7.13% | 51.66s |

Selected policies: `{"arcane": {"ab_stacks": 0, "use_wrath": false}, "fire": {"pyro_stacks": 1, "use_fireblast": false, "use_scorch": false}, "frost": {"barrier_refresh": 60, "use_barrage": false}}`.

### Frost sensitivity · Cone access + shield + 0.143 scaling

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Frost | 526.34 | 523.25–529.43 | 0.00% | 0.00s |
| Fire | 521.43 | 517.98–524.88 | 0.93% | 5.10s |
| Arcane | 463.69 | 461.56–465.82 | 11.90% | 0.60s |

Selected policies: `{"arcane": {"ab_stacks": 3, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": true, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

### Frost sensitivity · Cone access + shield + 0.429 scaling

| School | DPS | 95% sampling interval | Behind leader | Mana downtime |
| --- | ---: | --- | ---: | ---: |
| Frost | 580.13 | 576.00–584.25 | 0.00% | 0.00s |
| Fire | 521.43 | 517.98–524.88 | 10.12% | 5.10s |
| Arcane | 463.69 | 461.56–465.82 | 20.07% | 0.60s |

Selected policies: `{"arcane": {"ab_stacks": 3, "use_wrath": true}, "fire": {"pyro_stacks": 3, "use_fireblast": true, "use_scorch": true}, "frost": {"barrier_refresh": 60, "use_barrage": true}}`.

## Existing 35-case sensitivity matrix

These retain the original baseline-trained policies and 200 held-out fights per school; they are separate from the encounter-specific searches above. Their counts are not confidence estimates.

| Case | Order by mean DPS |
| --- | --- |
| baseline | Fire > Arcane > Frost |
| short_60 | Fire > Arcane > Frost |
| 180_seconds | Fire > Frost > Arcane |
| long_300 | Frost > Fire > Arcane |
| low_sp | Fire > Arcane > Frost |
| high_sp | Fire > Arcane > Frost |
| melee_access | Fire > Frost > Arcane |
| shield_breaks_immediately | Fire > Arcane > Frost |
| shield_survives | Fire > Arcane > Frost |
| lance_coef_0143 | Fire > Frost > Arcane |
| lance_coef_0429 | Fire > Frost > Arcane |
| no_partial_resist | Fire > Arcane > Frost |
| no_miss_floor | Fire > Arcane > Frost |
| wrath_coef_085 | Fire > Arcane > Frost |
| wrath_coef_115 | Fire > Arcane > Frost |
| fof_boss_disabled | Fire > Arcane > Frost |
| cone_outside_order | Fire > Frost > Arcane |
| unlimited_mana | Fire > Arcane > Frost |
| shared_cooldown_base8 | Fire > Arcane > Frost |
| cold_snap_resets_shared | Fire > Arcane > Frost |
| periodic_crits | Fire > Arcane > Frost |
| travel_one_second | Fire > Arcane > Frost |
| aura_at_impact | Fire > Arcane > Frost |
| aoe_four_safe_targets | Frost > Fire > Arcane |
| aoe_periodic_ignite | Frost > Fire > Arcane |
| aoe_periodic_no_ignite | Frost > Fire > Arcane |
| level20_safe_target | Fire > Arcane > Frost |
| level40_safe_pack | Arcane > Fire > Frost |
| race_human | Fire > Arcane > Frost |
| race_gnome | Fire > Arcane > Frost |
| race_orc | Fire > Arcane > Frost |
| race_undead | Fire > Arcane > Frost |
| race_skyborne | Fire > Arcane > Frost |
| race_troll | Fire > Arcane > Frost |
| troll_cache_10s | Fire > Arcane > Frost |

## Limits

- Provisional ranking of implemented presets and finite policies, not validated in-game performance or a global talent optimum.
- 95% intervals cover Monte Carlo sampling only; they exclude coefficients, proc timing, talent prerequisites, rotation search and survival uncertainty.
- Identical gear and encounter settings within each comparison; school-specific builds/policies differ. Race-neutral and Troll cases are separate.
- No incoming damage, movement, deaths, immunities, party XP sharing or realistic leveling survival. No practical leveling winner is inferred.
- Combined Frost cases are deliberately favorable sensitivity probes, not measured parameters, expected values, or a probability distribution.
- Archive leader counts are descriptive coverage of selected cases, not independent observations or probabilities. No cross-scenario average tier list.

All inputs, build allocations, candidate scores, spell breakdowns and mana diagnostics are in `provisional-rankings.json`; provenance hashes detect stale mechanics or archives. `python ranking_report.py` regenerates both artifacts. `--check` checks freshness and derived content; `--recompute-check` repeats the seeded search and evaluation.

Evidence remains pinned in `lab-state.json` and `MAGE-NOV2-COVERAGE.md`. The official November 2 supplement and dated extraction index were rechecked; upstream remains a331552. No new mechanic numbers were substituted for this ranking pass.
