"""Local browser acceptance checks for the personal research page."""
import functools, http.server, json, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
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
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   page.locator('[name=fights]').fill('10');page.get_by_role('button',name='Run all three schools').click()
   page.get_by_text('Experiment complete. Current rankings remain blocked.',exact=True).wait_for()
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
   page.close();print(f'PASS personal research page at {width}px: run, input rejection, sharing, sensitivity, layout, console')
  page=browser.new_page();page.goto(url+'#b-123');page.wait_for_url('**/historical.html#b-123');assert 'HISTORICAL MODEL' in page.locator('body').inner_text();page.close()
  browser.close();print('PASS historical share redirect')
finally:server.shutdown()
