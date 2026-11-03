"""Local browser acceptance checks for the personal research page."""
import functools, http.server, json, threading, sys, statistics, math
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim_engine import simulate
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'_site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/'
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width in (390,800,1280):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(url);page.get_by_role('button',name='Run all three schools').wait_for()
   ranking=json.loads((ROOT/'provisional-rankings.json').read_text())
   assert page.locator('#ranking-scenario').input_value()=='troll_120'
   for case in ranking['cases']:
    page.locator('#ranking-scenario').select_option(case['name'])
    assert page.locator('#ranking-result tr').count()==4
    for index,row in enumerate(case['ranking']):
     assert page.locator('#ranking-result tr').nth(index+1).locator('td').first.inner_text()==f"{row['rank']}. {row['school'].title()}"
    assert 'Low confidence in live-game ordering' in page.locator('#ranking-uncertainty').inner_text()
    if case['name']=='troll_300':assert 'arcane/fire' in page.locator('#ranking-uncertainty').inner_text()
   page.locator('#ranking-scenario').select_option('troll_120')
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   page.locator('[name=fights]').fill('10');page.get_by_role('button',name='Run all three schools').click()
   page.get_by_text('Experiment complete. Certified rankings remain blocked.',exact=True).wait_for()
   assert page.locator('.result').count()==3
   assert '120s' in page.locator('#result-context').inner_text()
   page.get_by_text('Assumptions, rotations and versioned builds',exact=True).click()
   page.locator('#overrides').fill('{"unknown_option":1}');page.get_by_role('button',name='Run all three schools').click()
   assert 'unknown simulation options' in page.locator('#error').inner_text()
   page.locator('#overrides').fill('{"ice_lance_coef":0.143}')
   page.get_by_role('button',name='Share settings').click();shared=page.url
   assert '#experiment-v1:' in shared
   page.reload();page.get_by_role('button',name='Run all three schools').wait_for()
   assert json.loads(page.locator('#overrides').input_value())=={'ice_lance_coef':.143}
   assert page.locator('[name=fights]').input_value()=='10'
   page.locator('#scenario').select_option('long_300');assert 'frost' in page.locator('#scenario-result').inner_text()
   assert page.locator('a#archive-link').get_attribute('href')=='historical.html'
   assert not errors,errors
   page.screenshot(path=str(ROOT.parent/f'personal-current-{width}.png'),full_page=True)
   page.goto(url+'leveling.html');page.get_by_text('Level 10: Improved Frostbolt → 1/5',exact=True).wait_for()
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   page.locator('#level').fill('1');assert 'first normal talent point' in page.locator('#milestone').inner_text()
   page.locator('#level').fill('40');assert 'Ice Barrier → 1/1' in page.locator('#point').inner_text()
   page.locator('#level').fill('60');assert 'Improved Cone of Cold → 2/3' in page.locator('#point').inner_text()
   page.locator('#level').fill('20')
   for key,value in dict(sp=30,intellect=60,spirit=40,crit=5,target_hp=800,drink_mps=20).items():page.locator('[name='+key+']').fill(str(value))
   page.get_by_role('button',name='Open lab with my leveling build').click()
   page.get_by_role('button',name='Run all three schools').wait_for()
   assert page.locator('[name=level]').input_value()=='20'
   assert 'icelance=1' in page.locator('#build-frost').input_value()
   page.locator('[name=fights]').fill('10');page.get_by_role('button',name='Run all three schools').click()
   page.get_by_text('Experiment complete. Certified rankings remain blocked.',exact=True).wait_for()
   assert 'Mean kill time:' in page.locator('.result.frost').inner_text()
   assert 'Modeled full-refill recovery:' in page.locator('.result.frost').inner_text()
   with page.expect_download() as event:page.get_by_role('button',name='Download results').click()
   payload=json.loads(Path(event.value.path()).read_text());row=next(r for r in payload['results'] if r['school']=='frost')
   expected=[simulate('frost',dict(payload['options'],seed=10001+i),row['talents']) for i in range(10)]
   for key,field in [('mean_kill_seconds','elapsed'),('mean_mana_spent','mana_spent'),('mean_recovery_seconds','recovery_seconds')]:
    assert math.isclose(row[key],statistics.mean(r[field] for r in expected),abs_tol=1e-8),(key,row[key])
   page.locator('[name=target_hp]').fill('100000000');page.locator('[name=seconds]').fill('1')
   page.get_by_role('button',name='Run all three schools').click();page.get_by_text('Experiment complete. Certified rankings remain blocked.',exact=True).wait_for()
   assert 'not available — some trials timed out' in page.locator('.result.frost').inner_text()
   assert not errors,errors
   page.close();print(f'PASS at {width}px: research page, day-one guide, milestones, exact build handoff, Python-checked kill/recovery metrics, timeout handling')
  page=browser.new_page();page.goto(url+'#b-123');page.wait_for_url('**/historical.html#b-123');assert 'HISTORICAL MODEL' in page.locator('body').inner_text();page.close()
  browser.close();print('PASS historical share redirect')
finally:server.shutdown()
