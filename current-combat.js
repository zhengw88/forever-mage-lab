'use strict';
// Port of current_combat.py. Explicit outcome replay, not a complete DPS simulator.
function createCurrentCombat(talents, rules) {
  const fireEffects = new Set(['ignite','improvedscorch','fireball','pyroblast','impact']);
  const barrageTriggers = new Set(['arcaneblast','arcanewrath','fireball','frostbolt','frostfirebolt']);
  const heatingTriggers = new Set(['fireball','frostfirebolt','fireblast','scorch']);
  function number(value,name) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) throw new Error(name+' must be finite and nonnegative');
    return value;
  }
  function replay(build, events, options) {
    const problems = talents.errors(build); if (problems.length) throw new Error(problems.join('; '));
    if (!['refresh','initial'].includes(options.heating_refresh)) throw new Error('select heating_refresh');
    if (!['cast','hit'].includes(options.cone_consumption)) throw new Error('select cone_consumption');
    number(options.intellect,'intellect'); number(options.base_mana,'base mana');
    const applications = [], output = []; let effects = {};
    let heating=0, heatingUntil=0, wc=0, barrageUntil=0, barrierUntil=0, shieldUntil=0, lanceReady=0, fireblastReady=0, previous=-1;
    let shieldAmount=null, wardAmount=0, wardUntil=0;
    const p = key => build[key] || 0;
    for (const event of events) {
      const now = number(event.at,'event time');
      if (now < previous) throw new Error('events must be chronological; equal times use input order');
      previous=now;
      if (now >= heatingUntil) heating=0;
      effects=Object.fromEntries(Object.entries(effects).filter(([,v]) => v > now));
      const kind=event.kind; let detail={};
      const requireTalent = key => {if (!p(key)) throw new Error('talent required: '+key);};
      const flag = key => {if (typeof event[key] !== 'boolean') throw new Error(key+' must be boolean'); return event[key];};
      const roll = () => {const v=number(event.roll,'proc roll'); if(v>=1) throw new Error('proc roll must be below 1'); return v;};
      const expiry = () => {const v=number(event.expires_at,'expiry'); if(v<=now) throw new Error('expiry must follow event'); return v;};
      if (kind==='blast_aura') {requireTalent('arcaneblast'); applications.push(now);}
      else if (kind==='barrage_roll') {
        requireTalent('missilebarrage'); const spell=event.spell, value=roll(), until=expiry();
        const chance=barrageTriggers.has(spell) ? (spell==='arcaneblast'?0.2:0.1)*p('missilebarrage') : 0;
        const triggered=value<chance; if(triggered) barrageUntil=until;
        detail={chance,triggered};
      } else if (kind==='missiles_cast') {
        const empowered=now<barrageUntil;
        detail={empowered,channel_seconds:empowered?2.5:5,mana_multiplier:empowered?0:1,
          tick_offsets:Array.from({length:5},(_,i)=>(i+1)*(empowered?0.5:1))};
        barrageUntil=0;
      } else if (kind==='fire_hit') {
        const spell=event.spell,crit=flag('crit'),periodic=flag('periodic');
        if(!heatingTriggers.has(spell) && !['pyroblast','ignite','flamestrike'].includes(spell)) throw new Error('unsupported fire hit');
        if(spell==='flamestrike'){const damage=number(event.damage,'Flamestrike damage');detail={ignite_bank_added:crit?damage*.08*p('ignite'):0};}
        const added=!periodic && heatingTriggers.has(spell) ? Number(crit)+Number(spell==='fireblast') : 0;
        if(p('heatingup') && added) {
          if(heating===0 || options.heating_refresh==='refresh') heatingUntil=now+20;
          heating=Math.min(3,heating+added);
        }
      } else if(kind==='pyro_cast') {
        requireTalent('pyroblast'); const pom=flag('presence_of_mind'); if(pom) requireTalent('presenceofmind');
        detail={cast_seconds:pom?0:6*(1-0.25*heating),consumed:pom?0:heating};
        if(!pom) {heating=0;heatingUntil=0;}
      } else if(kind==='effect_apply') {
        const effect=event.effect,owner=event.owner,until=expiry();
        if((!fireEffects.has(effect)&&effect!=='frostfirebolt') || !['self','other'].includes(owner)) throw new Error('unsupported effect or owner');
        if(owner==='self'&&fireEffects.has(effect)) effects[effect]=until;
      } else if(kind==='frost_hit') {
        requireTalent('winterschill'); const spell=event.spell, empowered=flag('fingers_empowered'),value=roll();
        if(!['frostbolt','icelance','coneofcold','frostfirebolt'].includes(spell)) throw new Error('unsupported frost hit; Frost Blast is not trained');
        if(spell==='icelance') {requireTalent('icelance');if(empowered) requireTalent('fingersoffrost');}
        const eligible=spell==='frostbolt'||(spell==='icelance'&&empowered), triggered=eligible&&value<0.2*p('winterschill');
        if(triggered) wc=Math.min(5,wc+1);detail={triggered};
      } else if(kind==='winter_expire') wc=0;
      else if(kind==='cone') {
        const hit=flag('hit'),inRange=flag('in_range');
        const used=inRange&&(hit||options.cone_consumption==='cast')?wc:0;
        detail={landed:hit&&inRange,stacks_used:used,damage_taken_multiplier:1+(hit&&inRange?0.2*wc:0),extra_sp_coefficient:hit&&inRange?0.07*wc:0};
        if(used) wc=0;
      } else if(kind==='fireblast_cast') {
        if(now<fireblastReady)throw new Error('Fire Blast shared cooldown');
        lanceReady=fireblastReady=now+8-p('improvedfireblast');
      } else if(kind==='lance_cast') {
        requireTalent('icelance');const frozen=flag('frozen');if(now<lanceReady) throw new Error('Ice Lance cooldown');
        lanceReady=fireblastReady=now+8;detail={damage_multiplier:frozen?4:1};
      } else if(kind==='barrier_apply') {
        requireTalent('icebarrier');barrierUntil=now+60;shieldUntil=now+60;
        shieldAmount=Object.hasOwn(event,'base_absorb')?number(event.base_absorb,'base absorb')*(1+.1*p('frostwarding')):null;
        if(shieldAmount===0)shieldUntil=0;
      } else if(kind==='ward_apply') {
        wardAmount=number(event.base_absorb,'base absorb')*(1+.1*p('frostwarding'));wardUntil=expiry();
      } else if(kind==='incoming_damage') {
        const amount=number(event.damage,'incoming damage'),school=event.school;
        if(!['physical','arcane','fire','frost','nature','shadow','holy'].includes(school))throw Error('single incoming school required');
        const wardActive=school==='frost'&&now<wardUntil&&wardAmount>0,barrierActive=now<shieldUntil;
        if(barrierActive&&shieldAmount===null)throw Error('supply base_absorb before replaying incoming damage');
        if(wardActive&&barrierActive&&!['ward_first','barrier_first'].includes(event.absorb_order))throw Error('explicit absorb_order required for overlapping shields');
        const negated=wardActive&&roll()<.1*p('frostwarding');let remaining=negated?0:amount,wardAbsorbed=0,barrierAbsorbed=0;
        if(!negated){
          const order=event.absorb_order==='barrier_first'?['barrier','ward']:['ward','barrier'];
          for(const shield of order){
            if(shield==='ward'&&wardActive){wardAbsorbed=Math.min(wardAmount,remaining);wardAmount-=wardAbsorbed;remaining-=wardAbsorbed;}
            else if(shield==='barrier'&&barrierActive){barrierAbsorbed=Math.min(shieldAmount,remaining);shieldAmount-=barrierAbsorbed;remaining-=barrierAbsorbed;}
          }
          if(barrierActive&&shieldAmount===0)shieldUntil=0;
        }
        detail={negated,reflected_damage:0,ward_absorbed:wardAbsorbed,barrier_absorbed:barrierAbsorbed,damage_taken:remaining};
      } else if(kind==='shield_break') {shieldUntil=0;shieldAmount=0;}
      else if(kind!=='observe') throw new Error('unknown event kind');
      const blast=rules.arcaneBlastSnapshot(applications,now,options.intellect,options.base_mana);
      output.push({at:now,kind,detail,blast,precision_hit:rules.precisionHit(p('precision')),
        resilience_armor:.25*p('arcaneresilience')*options.intellect,armor_spell_multiplier:1+.15*p('frostwarding'),absorb_multiplier:1+.1*p('frostwarding'),barrier_remaining:now<shieldUntil?shieldAmount:0,ward_remaining:now<wardUntil?wardAmount:0,
        wrath_cast_seconds:rules.accelerantCastSeconds('arcaneWrath',3.5,p('accelerant')),
        heating_stacks:heating,heating_expires_at:heating?heatingUntil:null,
        fire_effects:Object.keys(effects).sort(),fire_power_multiplier:1+0.01*p('firepower')*Math.min(4,Object.keys(effects).length),
        winter_stacks:wc,lance_ready_at:lanceReady,fireblast_ready_at:fireblastReady,
        barrier_damage_bonus:(now<barrierUntil?0.15:0)+(now<shieldUntil?0.05:0),barrage_active:now<barrageUntil});
    }
    return {schema:1,model:'current-mechanics-replay',model_current:false,options:JSON.parse(JSON.stringify(options)),
      talents:JSON.parse(JSON.stringify(build)),events:output,caveat:'Explicit outcome replay, not DPS or a spec ranking. See CURRENT-MECHANICS.md.'};
  }
  return {replay};
}
if(typeof module!=='undefined' && module.exports)
  module.exports=createCurrentCombat(require('./current-talents.js'),require('./patch-rules.js'));
