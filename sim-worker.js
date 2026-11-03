'use strict';
importScripts('current-talents.js','sim-engine.js');
let sim;
self.onmessage=async({data})=>{
 try {
  if(!sim){const [d,t,b,o]=await Promise.all(['sim-data.json','current-talents.json','current-builds.json','sim-defaults.json'].map(async p=>{const r=await fetch(p);if(!r.ok)throw Error('Cannot load '+p);return r.json();}));sim=createMageSim(d,t,b,o);}
  const {options,fights,builds}=data,results=[];
  if(!Number.isInteger(fights)||fights<2||fights>1000)throw Error('Fights must be 2..1000');
  for(const school of ['arcane','fire','frost']){
   const rows=[];for(let i=0;i<fights;i++)rows.push(sim.simulate(school,{...options,seed:(options.seed+i)>>>0,trace:false},builds[school]||null));
   const mean=key=>rows.reduce((s,r)=>s+r[key],0)/fights,dps=mean('dps'),se=Math.sqrt(rows.reduce((s,r)=>s+(r.dps-dps)**2,0)/(fights-1)/fights);
   const parts={};for(const r of rows)for(const [k,v]of Object.entries(r.damage_by_spell))parts[k]=(parts[k]||0)+v/r.elapsed/fights;
   results.push({school,mean_dps:dps,standard_error:se,ci95_sampling:[dps-1.96*se,dps+1.96*se],mean_mana_downtime:mean('mana_downtime'),mean_evocations:mean('evocations'),mean_mana_end:mean('mana_end'),mean_mana_spent:mean('mana_spent'),mean_recovery_seconds:mean('recovery_seconds'),mean_kill_seconds:rows.every(r=>r.killed)?mean('elapsed'):null,damage_by_spell_dps:parts,talents:rows[0].talents,killed_fraction:mean('killed'),safe_target_xp_per_hour:rows.every(r=>r.killed)?mean('safe_target_xp_per_hour'):null});
   self.postMessage({progress:school+' complete'});
  }
  self.postMessage({result:{model:'70707-experimental-event-sim',model_current:false,rankings_blocked:true,options:sim.config(options),fights,seed_start:options.seed,results,uncertainty:'Sampling intervals exclude mechanic and rotation uncertainty.'}});
 }catch(e){self.postMessage({error:e.message});}
};
