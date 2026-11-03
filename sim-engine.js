/* Independent JavaScript port of sim_engine.py. See SIMULATION.md for assumptions. */
'use strict';
function createMageSim(DATA, tree, presets, DEFAULTS) {
  const talents = createCurrentTalents(tree), nodes = Object.fromEntries(tree.talents.map(n=>[n.key,n]));
  const BUILDS=presets.builds, FIRE=['fire','frostfire'], FROST=['frost','frostfire'];
  const GATED={arcaneblast:'arcaneblast',arcanewrath:'arcanewrath',icelance:'icelance',pyroblast:'pyroblast',blastwave:'blastwave',icebarrier:'icebarrier'};
  const AOE=['blizzard','flamestrike','coneofcold','arcaneexplosion','blastwave'];
  const sum=a=>a.reduce((x,y)=>x+y,0);
  function config(input={}) {
    if (!input || Array.isArray(input) || typeof input!=='object' || Object.keys(input).some(k=>!Object.hasOwn(DEFAULTS,k))) throw Error('unknown simulation options');
    const o={...DEFAULTS,...input};
    for(const [k,v] of Object.entries(o)) if(typeof v!==typeof DEFAULTS[k] || (typeof v==='number'&&(!Number.isFinite(v)||v<0))) throw Error('invalid option: '+k);
    if(!Number.isInteger(o.level)||o.level<1||o.level>60)throw Error('level 1..60');
    if(o.seconds<=0||o.seconds>1800||!Number.isInteger(o.targets)||o.targets<1||o.targets>20)throw Error('invalid encounter size');
    if(![0,1,2,3].includes(o.target_level_delta))throw Error('target level delta 0..3');
    for(const k of ['partial_resist','miss_floor','crit','hit','berserking_haste'])if(o[k]>1)throw Error(k+' must be a fraction');
    if(!['none','human','gnome','orc','undead','troll','skyborne'].includes(o.race))throw Error('unsupported race');
    if(!['complete','impact'].includes(o.ab_apply)||!['inside','outside'].includes(o.winter_order))throw Error('invalid timing policy');
    if(!['auto','frostbolt','fireball','frostfirebolt','arcanemissiles'].includes(o.filler))throw Error('unsupported filler');
    if(![0,1,2,3,4].includes(o.ab_stacks)||![1,2,3].includes(o.pyro_stacks))throw Error('invalid rotation threshold');
    if(o.wand_speed<=0||o.drink_mps<=0||o.barrier_refresh<30)throw Error('invalid recovery/cooldown option');
    if(!Number.isInteger(o.seed)||o.seed>4294967295)throw Error('seed must be uint32');
    return o;
  }
  function levelBuild(school,level) {
    const desired=BUILDS[school],out={},keys=Object.keys(desired);
    const order=[...keys].sort((a,b)=>(Number(nodes[a].tree.toLowerCase()!==school)-Number(nodes[b].tree.toLowerCase()!==school))||nodes[a].required_points-nodes[b].required_points||keys.indexOf(a)-keys.indexOf(b));
    for(let i=0;i<Math.max(0,level-9);i++)for(const k of order)if((out[k]||0)<desired[k]){const c={...out,[k]:(out[k]||0)+1};if(!talents.errors(c,level).length){Object.assign(out,c);break;}}
    return out;
  }
  class Fight {
    constructor(school,options={},build=null) {
      if(!Object.hasOwn(BUILDS,school))throw Error('unknown school');
      this.school=school;this.o=config(options);const o=this.o;
      this.build=build===null?levelBuild(school,o.level):{...build};const problems=talents.errors(this.build,o.level);if(problems.length)throw Error(problems.join('; '));
      this.r=k=>this.build[k]||0;this.rng=o.seed;this.time=0;this.queue=[];this.seq=0;this.castid=0;
      this.aura={};this.cd={};this.parts={};this.casts={};this.trace=[];this.seen=new Set();
      this.ab=0;this.fof=0;this.hu=0;this.cc=false;this.comb=-1;this.comb_crits=0;
      this.intel=o.intellect*(1+.02*this.r('arcanemind'));this.spirit=o.spirit*(o.race==='human'?1.1:1);
      this.base_mana=DATA.base_mana[o.level-1];this.pool=(this.base_mana+Math.min(20,this.intel)+15*Math.max(0,this.intel-20))*(o.race==='gnome'?1.05:1);
      this.mana=this.pool;this.spent=0;this.restored=0;this.wait=0;this.last_spend=-10;this.evos=0;this.gem=0;
      this.gems=[[58,1000,1200],[48,775,925],[38,550,650],[28,375,425]].filter(x=>o.level>=x[0]).map(x=>x.slice(1));
      this.targets=Array.from({length:o.targets},()=>({hp:o.target_hp,fv:0,fv_until:0,wc:0,wc_until:0,frozen_until:0,dots:{},ignite:null}));
      this.spells={};
      for(const [k,rows] of Object.entries(DATA.spells)){const available=rows.filter(r=>r.level<=o.level&&(o.books||!r.book));if(available.length&&(!GATED[k]||this.r(GATED[k]))){const row={...available.at(-1)};row.base=Math.floor(row.base+row.growth*Math.max(0,Math.min(o.level,row.max_level)-row.spell_level));this.spells[k]=row;}}
      this.schedule(0,'act',{});this.schedule(2,'regen',{});
    }
    random(){this.rng=(Math.imul(1664525,this.rng)+1013904223)>>>0;return this.rng/4294967296;}
    schedule(t,kind,data){this.queue.push([t,++this.seq,kind,data]);}
    log(kind,data={}){if(this.o.trace&&this.trace.length<20000)this.trace.push({at:this.time,kind,...data});}
    up(k){return (this.aura[k]||0)>this.time;}
    ready(k){return (this.cd[k]||0)<=this.time;}
    alive(i){return this.o.target_hp===0||this.targets[i].hp>0;}
    gain(n){const accepted=Math.min(n,this.pool-this.mana);this.mana+=accepted;this.restored+=accepted;}
    power(){return (this.o.sp+(this.up('ab')?.12*this.intel*this.ab:0))*(this.up('orc')?1.1:1);}
    haste(){return (this.o.race==='skyborne'?1.02:1)*(this.up('troll')?1+this.o.berserking_haste:1);}
    crit(k,school,frozen){let c=this.o.crit+(this.intel-this.o.intellect)*DATA.crit_per_int[this.o.level-1]+.01*this.r('arcaneinstability')+(this.o.race==='human'?.01:0);
      if(FIRE.includes(school))c+=.02*this.r('criticalmass')+(this.comb>=0?.1*this.comb:0);
      if(school==='arcane')c+=.02*this.r('arcaneimpact');
      if(['fireblast','scorch','arcaneblast','icelance'].includes(k))c+=.02*this.r('incineration');
      if(k==='flamestrike')c+=.05*this.r('improvedflamestrike');if(frozen)c+=[0,.17,.34,.50][this.r('shatter')];return Math.min(1,c);
    }
    multiplier(school,i,periodic=false){const t=this.targets[i];let bonus=.01*this.r('arcaneinstability')+(this.up('ap')?.3:0);
      if(FIRE.includes(school)){const count=['fireball','pyroblast','impact'].filter(k=>(t.dots[k]?.until||0)>this.time).length+Number(t.fv_until>this.time)+Number(t.ignite!==null);bonus+=.01*this.r('firepower')*Math.min(4,count);}
      const barrier=(this.up('barrier')?.15:0)+(this.up('shield')?.05:0);if(FROST.includes(school))bonus+=barrier;let mult=1+bonus;
      if(FROST.includes(school)&&this.o.barrier_multiplicative&&barrier)mult=(1+bonus-barrier)*(this.up('barrier')?1.15:1)*(this.up('shield')?1.05:1);
      if(FIRE.includes(school)&&t.fv_until>this.time)mult*=1+.03*t.fv;
      if(this.up('gnome')&&!periodic)mult*=1.1;return mult*(1-this.o.partial_resist);
    }
    deal(amount,key,i){if(!this.alive(i))return;if(this.o.target_hp>0){amount=Math.min(amount,this.targets[i].hp);this.targets[i].hp-=amount;}this.parts[key]=(this.parts[key]||0)+amount;this.log('damage',{spell:key,target:i,amount});}
    in_range(k){if(k==='icebarrier')return true;let r=['fireball','pyroblast','frostfirebolt'].includes(k)?35:30;
      if(['coneofcold','arcaneexplosion','blastwave'].includes(k))r=10;if(k==='coneofcold')r*=1+.1*this.r('arcticreach');
      if(k==='fireblast')r=20+[0,8,15][this.r('improvedfireblast')];
      else if(['frostbolt','icelance','blizzard'].includes(k))r*=1+.1*this.r('arcticreach');
      else if(this.spells[k]&&FIRE.includes(this.spells[k].school))r+=3*this.r('flamethrowing');
      else if(this.spells[k]?.school==='arcane')r+=3*this.r('arcanegeometry');return this.o.distance<=r;
    }
    usable(k){return !!this.spells[k]&&this.ready(k)&&this.in_range(k);}
    choose(){const o=this.o,t=this.targets.find(x=>o.target_hp===0||x.hp>0)||this.targets[0];
      if(this.usable('icebarrier')&&!this.up('barrier_policy'))return 'icebarrier';
      if(this.school==='arcane'&&this.usable('arcaneblast')&&(this.up('ab')?this.ab:0)<o.ab_stacks)return 'arcaneblast';
      if(o.targets>1){if(this.usable('coneofcold')&&o.use_cone&&(t.wc>=3||this.school==='frost'))return 'coneofcold';if(this.school==='fire'&&this.usable('flamestrike')&&(t.dots.flamestrike?.until||0)<=this.time+3)return 'flamestrike';if(this.usable('blastwave'))return 'blastwave';if(this.school==='arcane'&&this.usable('arcaneexplosion'))return 'arcaneexplosion';if(this.usable('blizzard'))return 'blizzard';}
      if(this.usable('arcanewrath')&&o.use_wrath)return 'arcanewrath';
      if(this.school==='fire'&&o.use_scorch&&this.r('improvedscorch')&&this.usable('scorch')&&(t.fv<5||t.fv_until<this.time+4))return 'scorch';
      if(this.usable('icelance')&&this.up('fof')&&this.fof)return 'icelance';
      if(this.usable('coneofcold')&&o.use_cone&&t.wc_until>this.time&&t.wc>=5)return 'coneofcold';
      if(this.usable('pyroblast')&&this.up('hu')&&this.hu>=o.pyro_stacks)return 'pyroblast';
      if(this.school==='fire'&&o.use_fireblast&&this.r('heatingup')&&this.usable('fireblast'))return 'fireblast';
      if(o.use_barrage&&this.up('mb')&&this.usable('arcanemissiles'))return 'arcanemissiles';
      const filler=o.filler!=='auto'?o.filler:{arcane:'arcanemissiles',fire:'fireball',frost:'frostbolt'}[this.school];if(this.usable(filler))return filler;
      return ['frostbolt','fireball','arcanemissiles'].find(k=>this.usable(k))||null;
    }
    act(){const o=this.o,r=this.r;
      if(!this.up('fof'))this.fof=0;if(!this.up('hu'))this.hu=0;if(!this.up('ab'))this.ab=0;
      if(o.cooldowns){if(r('arcanepower')&&this.ready('ap')){this.aura.ap=this.time+15;this.cd.ap=this.time+180;}
        if(r('combustion')&&this.ready('comb')&&this.comb<0){this.comb=0;this.comb_crits=0;this.cd.comb=this.time+180;}
        const race=o.race;if(['gnome','orc','troll','skyborne'].includes(race)&&this.ready('racial')){this.aura[race]=this.time+{gnome:8,orc:15,troll:o.berserking_duration,skyborne:15}[race];this.cd.racial=this.time+(race==='troll'?180:120);}}
      if(o.consumables){if(o.level>=49&&this.ready('potion')&&this.pool-this.mana>=2250){this.gain(1350+900*this.random());this.cd.potion=this.time+120;this.log('potion',{mana:this.mana});}
        const gems=this.gems;if(this.gem<gems.length&&this.ready('gem')&&this.pool-this.mana>=gems[this.gem][1]){const [lo,hi]=gems[this.gem];this.gain(lo+(hi-lo)*this.random());this.gem++;this.cd.gem=this.time+120;}}
      if(o.cooldowns&&r('coldsnap')&&this.ready('coldsnap')&&this.fof&&!this.ready('icelance')){for(const spell of ['icelance','coneofcold','icebarrier'])this.cd[spell]=this.time;if(o.cold_snap_resets_fireblast)this.cd.fireblast=this.time;this.cd.coldsnap=this.time+600;this.log('cold_snap');}
      const k=this.choose();if(k===null){this.wait+=Math.min(1,o.seconds-this.time);this.schedule(this.time+1,'act',{});return;}
      const row=this.spells[k],school=row.school,mb=k==='arcanemissiles'&&this.up('mb'),basecost=k==='arcaneblast'?.15*this.base_mana:row.mana;
      let cost=basecost*(k==='arcaneblast'?1+this.ab:1)*(FROST.includes(school)?1-.05*r('frostchanneling'):1);cost*=1+(this.up('ap')?.3:0);if(this.up('gnome')&&k!=='icebarrier')cost*=.9;
      if(mb||(this.cc&&k!=='icebarrier'))cost=0;
      if(cost>this.mana&&!o.unlimited_mana){if(o.evocation&&o.level>=20&&this.ready('evo')&&this.mana<this.pool*.25){this.aura.evo=this.time+8;this.cd.evo=this.time+480;this.evos++;this.log('evocation',{mana:this.mana});this.schedule(this.time+8,'act',{});return;}
        const dt=Math.max(o.wand_speed,.5-this.time);this.wait+=Math.min(dt,o.seconds-this.time);this.schedule(this.time+dt,'wand',{});this.schedule(this.time+dt,'act',{});return;}
      if(cost&&!o.unlimited_mana){this.mana-=cost;this.spent+=cost;this.last_spend=this.time;}
      if(this.cc&&!mb&&k!=='icebarrier')this.cc=false;if(mb)this.aura.mb=0;
      let cast=row.cast;if(k==='frostbolt')cast=Math.max(0,cast-.1*r('improvedfrostbolt'));if(['fireball','frostfirebolt','arcanewrath'].includes(k))cast=Math.max(0,cast-.1*r('accelerant'));
      const pom=!!(o.cooldowns&&r('presenceofmind')&&this.ready('pom')&&cast>0&&cast<10);
      if(k==='pyroblast'){cast*=1-.25*this.hu;if(!pom){this.hu=0;this.aura.hu=0;}}
      if(pom){cast=0;this.cd.pom=this.time+180;}
      const haste=this.haste(),duration=(row.channel?row.channel/(mb?2:1):cast)/haste,frozen=!!(this.fof&&this.up('fof'));
      if(k!=='icebarrier'&&this.fof)this.fof--;this.castid++;this.casts[k]=(this.casts[k]||0)+1;
      const ctx={key:k,id:this.castid,sp:this.power(),frozen,basecost},cd=k==='fireblast'?Math.max(0,row.cd-r('improvedfireblast')):row.cd;
      this.cd[k]=this.time+(cast?duration:0)+cd;
      if(['icelance','fireblast'].includes(k)){const ready=this.time+(o.shared_blast_lance_base?8:cd);this.cd.icelance=this.cd.fireblast=ready;}
      this.log('cast',{spell:k,cast_id:this.castid,duration,cost,mana:this.mana,ab:this.ab,fof:this.fof,hu:this.hu});
      if(k==='icebarrier'){this.aura.barrier=this.time+60;this.aura.shield=this.time+Math.min(60,o.shield_lifetime);this.aura.barrier_policy=this.time+o.barrier_refresh;}
      else {if(k==='arcaneblast'&&o.ab_apply==='complete')this.schedule(this.time+duration,'ab',{});
        if(row.channel){for(let i=0;i<row.ticks;i++)this.schedule(this.time+duration*(i+1)/row.ticks,'hit',ctx);}
        else this.schedule(this.time+duration+(cast?o.travel_seconds:0),'hit',ctx);}
      this.schedule(this.time+Math.max(1,1.5/haste,duration),'act',{});
    }
    hit(c){const k=c.key,row=this.spells[k],school=row.school,o=this.o,r=this.r;if(k==='arcaneblast'&&o.ab_apply==='impact')this.apply_ab();
      let ids=this.targets.map((_,i)=>i).filter(i=>this.alive(i));if(!AOE.includes(k))ids=ids.slice(0,1);
      for(const i of ids){const target=this.targets[i];if(target.wc_until<=this.time)target.wc=0;if(target.fv_until<=this.time)target.fv=0;const wc=target.wc;
        if(k==='coneofcold'&&o.cone_consume_on_miss)target.wc=0;
        const hit=Math.min(1-o.miss_floor,[.96,.95,.94,.83][o.target_level_delta]+o.hit+.02*r('precision'));if(this.random()>=hit){this.log('miss',{spell:k,target:i});continue;}
        const frozen=c.frozen||target.frozen_until>this.time,cancrit=k!=='blizzard'||o.periodic_crit,crit=cancrit&&this.random()<this.crit(k,school,frozen);
        let sp=o.snapshot_sp?c.sp:this.power();if(k==='arcanewrath')sp+=.05*this.pool;
        const coef=k==='icelance'?o.ice_lance_coef:k==='arcanewrath'?o.wrath_coef:row.coef,base=row.base*(1+row.variance*(this.random()-.5));let damage=base+coef*sp;
        if(k==='coneofcold'){damage=o.winter_order==='inside'?(damage+.07*wc*sp)*(1+.2*wc):damage*(1+.2*wc)+.07*wc*sp;damage*=1+[0,.12,.23,.35][r('improvedconeofcold')];target.wc=0;}
        if(k==='icelance'&&frozen)damage*=4;
        const bonus=.5*(1+.2*(school==='arcane'?r('arcanemind'):FROST.includes(school)?r('iceshards'):0));damage*=this.multiplier(school,i,k==='blizzard')*(crit?1+bonus:1);this.deal(damage,k,i);
        if(this.comb>=0&&FIRE.includes(school)){this.comb=Math.min(10,this.comb+1);if(crit)this.comb_crits++;if(this.comb_crits>=3)this.comb=-1;}
        if(crit&&(FIRE.includes(school)||FROST.includes(school)))this.gain(.1*r('masterofelements')*c.basecost/(row.channel?row.ticks:1));
        if(crit&&FIRE.includes(school)&&r('ignite'))this.add_ignite(i,damage*.08*r('ignite'));
        if(['fireball','frostfirebolt','fireblast','scorch'].includes(k)&&r('heatingup')){const add=Number(crit)+Number(k==='fireblast');if(add){if(!this.up('hu'))this.hu=0;if(!this.hu||o.heating_refresh)this.aura.hu=this.time+20;this.hu=Math.min(3,this.hu+add);}}
        if(k==='scorch'&&r('improvedscorch')&&this.random()<[0,.33,.66,1][r('improvedscorch')]){target.fv=Math.min(5,target.fv+1);target.fv_until=this.time+30;}
        if((k==='frostbolt'||(k==='icelance'&&c.frozen))&&r('winterschill')&&this.random()<.2*r('winterschill')){target.wc=Math.min(5,target.wc+1);target.wc_until=this.time+o.winter_duration;}
        const chill=['frostbolt','frostfirebolt','coneofcold'].includes(k)||(k==='blizzard'&&r('improvedblizzard'));
        if(chill&&i<4){if(r('fingersoffrost')&&(o.target_level_delta<3||o.fof_on_boss)&&this.random()<.15){this.fof=r('fingersoffrost');this.aura.fof=this.time+15;}if(r('frostbite')&&o.target_level_delta<3&&this.random()<.05*r('frostbite'))target.frozen_until=this.time+5;}
        if(FIRE.includes(school)&&r('impact')&&o.target_level_delta<3&&this.random()<[0,.03,.07,.10][r('impact')])target.dots.impact={until:this.time+2};
        if(row.dot){const d=row.dot,token=c.id;target.dots[k]={until:this.time+d.period*d.ticks,token};const amount=(d.base+d.coef*sp)*this.multiplier(school,i,true);for(let j=0;j<d.ticks;j++)this.schedule(this.time+d.period*(j+1),'dot',{key:k,target:i,token,amount,crit:this.crit(k,school,false),bonus,school});}
        if(!this.seen.has(c.id)){this.seen.add(c.id);if(r('arcaneconcentration')&&this.random()<.02*r('arcaneconcentration'))this.cc=true;
          const chance=['arcaneblast','arcanewrath','fireball','frostbolt','frostfirebolt'].includes(k)?(k==='arcaneblast'?.2:.1)*r('missilebarrage'):0;if(chance&&this.random()<chance)this.aura.mb=this.time+o.barrage_duration;}
        if(o.race==='undead'&&this.ready('grave')&&this.random()<.3){this.deal(.05*o.max_hp*(1-o.partial_resist),'touch_of_the_grave',i);this.cd.grave=this.time+15;}
      }
    }
    apply_ab(){if(!this.up('ab')){this.ab=0;this.aura.ab=this.time+18;}this.ab=Math.min(4,this.ab+1);this.log('blast_aura',{stacks:this.ab,expires_at:this.aura.ab});}
    add_ignite(i,amount){const old=this.targets[i].ignite,bank=(old?old.bank:0)+amount,next=old&&old.next>this.time?old.next:this.time+2,token=this.seq+1;this.targets[i].ignite={bank,next,ticks:2,token};this.schedule(next,'ignite',{target:i,token});}
    run(){let end=this.o.seconds,killed=false;while(this.queue.length){this.queue.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);const [t,_,kind,c]=this.queue.shift();if(t>end)break;this.time=t;
        if(kind==='act'&&t<end)this.act();else if(kind==='ab')this.apply_ab();else if(kind==='hit')this.hit(c);
        else if(kind==='wand'){let i=this.targets.findIndex((_,i)=>this.alive(i));if(i<0)i=0;this.deal(this.o.wand_dps*this.o.wand_speed*[1,1.13,1.25][this.r('wandspecialization')],'wand',i);}
        else if(kind==='regen'){const spirit=6.25+this.spirit/8,fraction=(this.aura.evo??-1)>=this.time?16:this.time-this.last_spend>=5?1:Math.min(1,(this.o.level>=34?.5:0)+[0,.17,.33,.5][this.r('arcanemeditation')]);this.gain(2*(spirit*fraction+this.o.mp5/5)*(this.up('skyborne')?1.5:1));this.schedule(t+2,'regen',{});}
        else if(kind==='dot'){const dot=this.targets[c.target].dots[c.key]||{};if(dot.token===c.token){const crit=this.o.periodic_crit&&this.random()<c.crit;this.deal(c.amount*(crit?1+c.bonus:1),c.key+'_dot',c.target);if(this.comb>=0&&FIRE.includes(c.school)&&this.o.combustion_periodic)this.comb=Math.min(10,this.comb+1);}}
        else if(kind==='ignite'){const dot=this.targets[c.target].ignite;if(dot&&dot.token===c.token){const amount=dot.bank/dot.ticks;this.deal(amount,'ignite',c.target);dot.bank-=amount;dot.ticks--;if(this.comb>=0&&this.o.combustion_periodic)this.comb=Math.min(10,this.comb+1);if(dot.ticks){dot.next=t+2;this.schedule(t+2,'ignite',c);}else this.targets[c.target].ignite=null;}}
        if(this.o.target_hp&&this.targets.every(x=>x.hp<=0)){killed=true;end=t;break;}}
      const total=sum(Object.values(this.parts)),duration=Math.max(end,1e-9),drink=(this.pool-this.mana)/this.o.drink_mps,cycle=duration+this.o.walk_seconds+drink,xp=this.o.xp_per_target*this.o.targets*(this.o.dungeon?1+this.o.dungeon_xp_bonus:1);
      return {school:this.school,model:'70707-experimental-event-sim',model_current:false,options:this.o,talents:this.build,damage:total,dps:total/duration,elapsed:duration,killed,damage_by_spell:this.parts,casts:this.casts,mana_spent:this.spent,mana_restored:this.restored,mana_end:this.mana,max_mana:this.pool,mana_downtime:this.wait,evocations:this.evos,recovery_seconds:drink,safe_target_xp_per_hour:killed?3600*xp/cycle:null,trace:this.trace};
    }
  }
  return {Fight,config,levelBuild,simulate:(school,options={},build=null)=>new Fight(school,options,build).run()};
}
if(typeof module!=='undefined'&&module.exports){var createCurrentTalents = data=>require('./current-talents.js');module.exports=createMageSim(require('./sim-data.json'),require('./current-talents.json'),require('./current-builds.json'),require('./sim-defaults.json'));}
