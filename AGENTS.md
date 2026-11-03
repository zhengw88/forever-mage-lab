# Personal Mage simulator maintenance

This fork belongs to **zhengw88**. Work only in `zhengw88/forever-mage-lab`.
Do not use another GitHub account or change upstream repositories. Verify the
active account before writes. Preserve the upstream MIT license and game-art notice.

The goal is an independently reproducible comparison of Fire, Arcane, and Frost,
including leveling and AoE. MythicSim rankings are not inputs, acceptance tests,
or calibration targets. Inherited code is a historical baseline, not current truth.

Read `lab-state.json` and `REBUILD.md` first. Keep game build, hotfix date,
source retrieval date, observed facts, assumptions, and implemented mechanics
separate. Community client extraction is evidence, not server validation.
Do not mark a pending migration as implemented just because a source was read.

For each update:

1. Check official Forever patch notes and the dated client/hotfix evidence in
   `lab-state.json`. Compare upstream commits without overwriting personal changes.
2. Record the exact source, old/new values, affected files, and unresolved behavior.
   Never silently reinterpret old talent share links under a new tree.
3. Implement Python and JavaScript changes together, with targeted mechanic tests.
   Regenerate fixtures from Python only after checking the formula independently.
4. Run `python lab.py validate`, and `python tests/page_check.py` for UI changes.
   Run cast-by-cast checks and sensitivity cases for affected rotations. Numerical
   agreement between two ports does not demonstrate agreement with the game.
5. Compare all three schools at the same gear, buffs, fight duration, target,
   rank availability and assumptions. Report build legality, spell breakdowns,
   mana downtime, seeds, Monte Carlo sampling error and sensitivity to unknowns.
6. Keep certified in-game rankings blocked until the migration register is complete
   and validation supports them. The owner explicitly authorized a best-effort
   provisional ranking on November 3, 2026: label it as a model estimate, retain
   uncertainty and scenario dependence, and never mark the model validated merely
   to publish that estimate. Update the ledger, reports and generated page.
7. Make a focused branch and pull request into this fork. Explain what changed,
   source evidence, test results and remaining limits. Do not auto-merge or deploy.

Daily maintenance should notify the owner only for material changes or a blocker.
Never request passwords or verification codes in chat. Use secure authentication
if the authorized personal account needs to sign in again.
