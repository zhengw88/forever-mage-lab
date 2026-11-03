"""Build an isolated personal Pages artifact. Does not publish or modify upstream."""
from pathlib import Path
import shutil
import hashlib
ROOT=Path(__file__).resolve().parent
out=ROOT/'_site';out.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'current.html',out/'index.html')
shutil.copyfile(ROOT/'index.html',out/'historical.html')
for name in ('leveling.html','leveling-plan.json','current-app.js','sim-engine.js','sim-worker.js','sim-data.json','sim-defaults.json','current-talents.js','current-talents.json','current-builds.json','current-experiments.json','provisional-rankings.json','PROVISIONAL-RANKING.md','RANKING-REVIEW-2026-11-03.md','lab-state.json','CURRENT-MECHANICS.md','MAGE-NOV2-COVERAGE.md','SIMULATION.md','LICENSE'):
    shutil.copyfile(ROOT/name,out/name)
(out/'.nojekyll').write_text('')
# One release key covers HTML loaders, worker imports and fetched model data.
# Returning visitors must not combine a new page with cached old scripts/JSON.
assets=sorted(p for p in out.iterdir() if p.suffix in ('.js','.json'))
release=hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in assets)).hexdigest()[:16]
for page in list(out.glob('*.html'))+list(out.glob('*.js')):
    text=page.read_text()
    for asset in assets:
        for quote in ('"', "'"):
            text=text.replace(quote+asset.name+quote,quote+asset.name+'?v='+release+quote)
    page.write_text(text)
print('Built personal site in',out)
