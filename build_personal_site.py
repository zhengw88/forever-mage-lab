"""Build an isolated personal Pages artifact. Does not publish or modify upstream."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
out=ROOT/'_site';out.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'current.html',out/'index.html')
shutil.copyfile(ROOT/'index.html',out/'historical.html')
for name in ('leveling.html','leveling-plan.json','current-app.js','sim-engine.js','sim-worker.js','sim-data.json','sim-defaults.json','current-talents.js','current-talents.json','current-builds.json','current-experiments.json','lab-state.json','CURRENT-MECHANICS.md','SIMULATION.md','LICENSE'):
    shutil.copyfile(ROOT/name,out/name)
(out/'.nojekyll').write_text('')
print('Built personal site in',out)
