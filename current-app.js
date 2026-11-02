'use strict';
(async()=>{
 const $=id=>document.getElementById(id),schools=['arcane','fire','frost'],form=$('form');let worker,lastResult,talents,archive;
 const fmt=x=>Number(x).toLocaleString(undefined,{maximumFractionDigits:1});
 function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
 function error(e){$('error').textContent=e.message||String(e);$('status').textContent='Experiment could not run.';$('run').disabled=false;}
 if(/^#(?:b-|race-|lvl-)/.test(location.hash)){location.replace('historical.html'+location.hash);return;}
 for(const school of schools){const label=el('label',school[0].toUpperCase()+school.slice(1)+' build fragment');const input=el('input');input.id='build-'+school;input.placeholder='Default level-adjusted preset';label.append(input);$('builds').append(label);}
 function request(){
  const f=new FormData(form),options={};for(const [k,v]of f)if(k!=='fights')options[k]=k==='race'?v:Number(v);
  options.crit/=100;options.hit/=100;const extra=JSON.parse($('overrides').value);
  if(!extra||Array.isArray(extra)||typeof extra!=='object')throw Error('Overrides must be a JSON object');
  if(Object.hasOwn(extra,'seed')||Object.hasOwn(extra,'trace'))throw Error('Use the seed field; trace is available through the CLI.');
  Object.assign(options,extra);window.mageSim.config(options);
  const builds={};for(const school of schools){const text=$('build-'+school).value.trim();if(text){builds[school]=talents.decode(text);const issues=talents.errors(builds[school],options.level,true);if(issues.length)throw Error(school+': '+issues.join('; '));}}
  return {options,fights:Number(f.get('fights')),builds};
 }
 function show(result){
  lastResult=result;$('results').replaceChildren();$('download').disabled=false;
  $('result-context').textContent=`${result.fights} fights per school · ${result.options.seconds}s · level ${result.options.level} · ${result.options.targets} target(s) · seed ${result.seed_start}. 95% intervals measure sampling only.`;
  for(const r of result.results){const card=el('article',undefined,'result '+r.school);card.append(el('h3',r.school[0].toUpperCase()+r.school.slice(1)),el('div',fmt(r.mean_dps)+' DPS','dps'),el('p',`95% sampling interval: ${fmt(r.ci95_sampling[0])}–${fmt(r.ci95_sampling[1])}`,'unit'),el('p',`Mana downtime: ${fmt(r.mean_mana_downtime)}s · Evocations: ${fmt(r.mean_evocations)}`,'unit'));
   if(result.options.target_hp>0){card.append(el('p',`Targets cleared: ${fmt(100*r.killed_fraction)}% of fights.`,'unit'),el('p',`Mean kill time: ${r.mean_kill_seconds===null?'not available — some trials timed out':fmt(r.mean_kill_seconds)+'s'}. Mana spent: ${fmt(r.mean_mana_spent)}.`,'unit'),el('p',`Modeled full-refill recovery: ${fmt(r.mean_recovery_seconds)}s. Safe stationary target; every trial starts at full mana.`,'unit'));}
   const d=el('details');d.append(el('summary','Spell breakdown & legal build'));const table=el('table');const head=el('tr');head.append(el('th','Spell'),el('th','DPS'));table.append(head);for(const [k,v]of Object.entries(r.damage_by_spell_dps).sort((a,b)=>b[1]-a[1])){const tr=el('tr');tr.append(el('td',k),el('td',fmt(v)));table.append(tr);}d.append(table,el('p',`${Object.values(r.talents).reduce((a,b)=>a+b,0)} points under the extracted tree contract.`),el('pre',talents.encode(r.talents)));card.append(d);$('results').append(card);
  }
 }
 form.addEventListener('submit',e=>{e.preventDefault();if(!form.reportValidity())return;try{const req=request();$('error').textContent='';$('run').disabled=true;$('status').textContent='Running seeded fights locally…';if(worker)worker.terminate();worker=new Worker('sim-worker.js');worker.onerror=e=>error(e);worker.onmessage=({data})=>{if(data.error)error(Error(data.error));else if(data.progress)$('status').textContent=data.progress;else if(data.result){show(data.result);$('run').disabled=false;$('status').textContent='Experiment complete. Current rankings remain blocked.';worker.terminate();worker=null;}};worker.postMessage(req);}catch(e){error(e);}});
 $('share').onclick=()=>{try{request();const fields=Object.fromEntries(new FormData(form));const state={version:1,fields,overrides:$('overrides').value,builds:Object.fromEntries(schools.map(s=>[s,$('build-'+s).value]))};location.hash='experiment-v1:'+encodeURIComponent(JSON.stringify(state));$('status').textContent='Share this address: it contains your settings and build versions.';}catch(e){error(e);}};
 $('download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(lastResult,null,2)+'\n'],{type:'application/json'}));const a=el('a');a.href=url;a.download='personal-mage-experiment.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 try{
  const [data,tree,builds,defaults,report]=await Promise.all(['sim-data.json','current-talents.json','current-builds.json','sim-defaults.json','current-experiments.json'].map(async p=>{const r=await fetch(p);if(!r.ok)throw Error('Cannot load '+p);return r.json();}));
  talents=createCurrentTalents(tree);window.mageSim=createMageSim(data,tree,builds,defaults);archive=report;
  for(const s of archive.scenarios){const o=el('option',s.name.replaceAll('_',' '));o.value=s.name;$('scenario').append(o);}
  $('scenario').onchange=()=>{const s=archive.scenarios.find(s=>s.name===$('scenario').value);$('scenario-result').replaceChildren();if(!s)return;const table=el('table');const h=el('tr');for(const t of ['School','Mean DPS','95% sampling interval'])h.append(el('th',t));table.append(h);for(const r of s.results){const row=el('tr');row.append(el('td',r.school),el('td',fmt(r.mean_dps)),el('td',r.ci95_sampling.map(fmt).join('–')));table.append(row);}$('scenario-result').append(table,el('p',`Shared overrides: ${JSON.stringify(Object.fromEntries(Object.entries(s.options).filter(([k,v])=>v!==defaults[k])))}`,'summary-note'));};
  if(location.hash.startsWith('#experiment-v1:')){const s=JSON.parse(decodeURIComponent(location.hash.slice(15)));if(s.version!==1)throw Error('Unsupported experiment version');for(const [k,v]of Object.entries(s.fields||{})){const field=form.elements.namedItem(k);if(field)field.value=String(v);}$('overrides').value=s.overrides||'{}';for(const school of schools)$('build-'+school).value=s.builds?.[school]||'';request();}
  else if(location.hash.startsWith('#mage-')){const b=talents.decode(location.hash);const totals={};for(const n of tree.talents)totals[n.tree.toLowerCase()]=(totals[n.tree.toLowerCase()]||0)+(b[n.key]||0);const school=schools.reduce((a,b)=>totals[a]>=totals[b]?a:b);$('build-'+school).value=location.hash;}
  else if(location.hash)throw Error('Unknown share version; historical builds are never reinterpreted.');
  $('run').disabled=false;$('run').textContent='Run all three schools';$('share').disabled=false;$('status').textContent='Model loaded. Ready to run locally in your browser.';
 }catch(e){error(e);$('run').disabled=true;}
})();
