"""Independent event simulation for the versioned research snapshot.

No historical optimizer or third-party simulation code is called. Defaults are
explicit hypotheses, not a current ranking certification; see SIMULATION.md.
"""
import heapq
import json
import math
from pathlib import Path
from current_talents import errors, NODES

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'sim-data.json').read_text())
BUILDS=json.loads((ROOT/'current-builds.json').read_text())['builds']
DEFAULTS=dict(level=60,seconds=120,sp=500,intellect=300,spirit=120,crit=.10,hit=.11,mp5=65,
              race='none',distance=30,targets=1,target_hp=0,target_level_delta=3,max_hp=4000,
              books=False,unlimited_mana=False,consumables=True,evocation=True,cooldowns=True,
              partial_resist=.06,miss_floor=.01,ice_lance_coef=0,wrath_coef=1,fof_on_boss=True,
              travel_seconds=0,shield_lifetime=10,barrier_refresh=60,barrier_multiplicative=False,
              winter_duration=15,winter_order='inside',cone_consume_on_miss=False,
              heating_refresh=True,barrage_duration=15,berserking_duration=15,berserking_haste=.10,
              shared_blast_lance_base=False,cold_snap_resets_fireblast=False,
              periodic_crit=False,flamestrike_periodic_ignite=True,combustion_periodic=True,snapshot_sp=True,ab_apply='complete',
              ab_stacks=2,use_wrath=True,use_barrage=True,use_fireblast=True,use_scorch=True,
              pyro_stacks=3,use_cone=True,filler='auto',wand_dps=60,wand_speed=1.5,
              walk_seconds=8,drink_mps=100,xp_per_target=300,dungeon=False,dungeon_xp_bonus=.20,
              seed=1,trace=False)
GATED={'arcaneblast':'arcaneblast','arcanewrath':'arcanewrath','icelance':'icelance','pyroblast':'pyroblast','blastwave':'blastwave','icebarrier':'icebarrier'}
AOE={'blizzard','flamestrike','coneofcold','arcaneexplosion','blastwave'}
FIRE={'fire','frostfire'};FROST={'frost','frostfire'}


def config(options):
    if not isinstance(options,dict) or set(options)-set(DEFAULTS):raise ValueError('unknown simulation options')
    o=dict(DEFAULTS,**options)
    for k,v in o.items():
        if type(DEFAULTS[k]) is bool:
            if type(v) is not bool:raise ValueError(k+' must be boolean')
        elif isinstance(DEFAULTS[k],(int,float)):
            if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError(k+' must be finite and nonnegative')
        elif not isinstance(v,str):raise ValueError(k+' must be text')
    if not 1<=o['level']<=60 or int(o['level'])!=o['level']:raise ValueError('level 1..60')
    if not 0<o['seconds']<=1800 or not 1<=o['targets']<=20 or int(o['targets'])!=o['targets']:raise ValueError('invalid encounter size')
    if o['target_level_delta'] not in (0,1,2,3):raise ValueError('target level delta 0..3')
    for k in ('partial_resist','miss_floor','crit','hit','berserking_haste'):
        if o[k]>1:raise ValueError(k+' must be a fraction')
    if o['race'] not in ('none','human','gnome','skyborne','orc','undead','troll'):raise ValueError('unsupported race')
    if o['ab_apply'] not in ('complete','impact') or o['winter_order'] not in ('inside','outside'):raise ValueError('invalid timing policy')
    if o['filler'] not in ('auto','frostbolt','fireball','frostfirebolt','arcanemissiles'):raise ValueError('unsupported filler')
    if o['ab_stacks'] not in (0,1,2,3,4) or o['pyro_stacks'] not in (1,2,3):raise ValueError('invalid rotation threshold')
    if o['wand_speed']<=0 or o['drink_mps']<=0 or o['barrier_refresh']<30:raise ValueError('invalid recovery/cooldown option')
    if o['seed']!=int(o['seed']) or o['seed']>4294967295:raise ValueError('seed must be uint32')
    return o


def level_build(school,level):
    desired=BUILDS[school];out={}
    order=sorted(desired,key=lambda k:(NODES[k]['tree'].lower()!=school,NODES[k]['required_points'],list(desired).index(k)))
    for _ in range(max(0,level-9)):
        for k in order:
            if out.get(k,0)<desired[k]:
                candidate=dict(out);candidate[k]=candidate.get(k,0)+1
                if not errors(candidate,level):out=candidate;break
        else:break
    return out


class Fight:
    def __init__(self,school,options=None,build=None):
        if school not in BUILDS:raise ValueError('unknown school')
        self.school=school;self.o=config({} if options is None else options);o=self.o
        self.build=level_build(school,int(o['level'])) if build is None else dict(build)
        problems=errors(self.build,int(o['level']))
        if problems:raise ValueError('; '.join(problems))
        self.r=lambda k:self.build.get(k,0)
        self.rng=int(o['seed']);self.time=0.;self.queue=[];self.seq=0;self.castid=0
        self.aura={};self.cd={};self.parts={};self.casts={};self.trace=[];self.seen=set()
        self.ab=0;self.fof=0;self.hu=0;self.cc=False;self.comb=-1;self.comb_crits=0
        self.intel=o['intellect']*(1+.02*self.r('arcanemind'))
        self.spirit=o['spirit']*(1.1 if o['race']=='human' else 1)
        self.base_mana=DATA['base_mana'][int(o['level'])-1]
        self.pool=(self.base_mana+min(20,self.intel)+15*max(0,self.intel-20))*(1.05 if o['race']=='gnome' else 1)
        self.mana=self.pool;self.spent=0.;self.restored=0.;self.wait=0.;self.last_spend=-10.;self.evos=0;self.gem=0;self.gems=[(lo,hi) for level,lo,hi in [(58,1000,1200),(48,775,925),(38,550,650),(28,375,425)] if o['level']>=level]
        self.targets=[dict(hp=o['target_hp'],fv=0,fv_until=0,wc=0,wc_until=0,frozen_until=0,dots={},ignite=None) for _ in range(int(o['targets']))]
        self.spells={}
        for k,rows in DATA['spells'].items():
            available=[r for r in rows if r['level']<=o['level'] and (o['books'] or not r['book'])]
            if available and (k not in GATED or self.r(GATED[k])):
                row=dict(available[-1]);row['base']=math.floor(row['base']+row['growth']*max(0,min(o['level'],row['max_level'])-row['spell_level']))
                self.spells[k]=row
        self.schedule(0,'act',{});self.schedule(2,'regen',{})

    def random(self):
        self.rng=(1664525*self.rng+1013904223)&0xffffffff
        return self.rng/4294967296

    def schedule(self,t,kind,data):
        self.seq+=1;heapq.heappush(self.queue,(t,self.seq,kind,data))

    def log(self,kind,**data):
        if self.o['trace'] and len(self.trace)<20000:self.trace.append(dict(at=self.time,kind=kind,**data))

    def up(self,k):return self.aura.get(k,0)>self.time
    def ready(self,k):return self.cd.get(k,0)<=self.time
    def alive(self,i):return self.o['target_hp']==0 or self.targets[i]['hp']>0
    def gain(self,n):
        accepted=min(n,self.pool-self.mana);self.mana+=accepted;self.restored+=accepted

    def power(self):
        sp=self.o['sp']+(.12*self.intel*self.ab if self.up('ab') else 0)
        return sp*(1.1 if self.up('orc') else 1)

    def haste(self):return (1.02 if self.o['race']=='skyborne' else 1)*(1+self.o['berserking_haste'] if self.up('troll') else 1)

    def crit(self,k,school,frozen):
        c=self.o['crit']+(self.intel-self.o['intellect'])*DATA['crit_per_int'][int(self.o['level'])-1]+.01*self.r('arcaneinstability')+(.01 if self.o['race']=='human' else 0)
        if school in FIRE:c+=.02*self.r('criticalmass')+(.1*self.comb if self.comb>=0 else 0)
        if school=='arcane':c+=.02*self.r('arcaneimpact')
        if k in ('fireblast','scorch','arcaneblast','icelance'):c+=.02*self.r('incineration')
        if k=='flamestrike':c+=.05*self.r('improvedflamestrike')
        if frozen:c+=[0,.17,.34,.50][self.r('shatter')]
        return min(1,c)

    def multiplier(self,school,target,periodic=False):
        t=self.targets[target];bonus=.01*self.r('arcaneinstability')+(.3 if self.up('ap') else 0)
        if school in FIRE:
            count=sum(t['dots'].get(k,{}).get('until',0)>self.time for k in ('fireball','pyroblast','impact'))+int(t['fv_until']>self.time)+int(t['ignite'] is not None)
            bonus+=.01*self.r('firepower')*min(4,count)
        barrier=(.15 if self.up('barrier') else 0)+(.05 if self.up('shield') else 0)
        if school in FROST:bonus+=barrier
        mult=1+bonus
        if school in FROST and self.o['barrier_multiplicative'] and barrier:
            mult=(1+bonus-barrier)*(1.15 if self.up('barrier') else 1)*(1.05 if self.up('shield') else 1)
        if school in FIRE and t['fv_until']>self.time:mult*=1+.03*t['fv']
        if self.up('gnome') and not periodic:mult*=1.1
        return mult*(1-self.o['partial_resist'])

    def deal(self,amount,key,i):
        if not self.alive(i):return
        if self.o['target_hp']>0:amount=min(amount,self.targets[i]['hp']);self.targets[i]['hp']-=amount
        self.parts[key]=self.parts.get(key,0)+amount;self.log('damage',spell=key,target=i,amount=amount)

    def in_range(self,k):
        if k=='icebarrier':return True
        r=35 if k in ('fireball','pyroblast','frostfirebolt') else 30
        if k in ('coneofcold','arcaneexplosion','blastwave'):r=10
        if k=='coneofcold':r*=1+.1*self.r('arcticreach')
        if k=='fireblast':r=20+[0,8,15][self.r('improvedfireblast')]
        elif k in ('frostbolt','icelance','blizzard'):r*=1+.1*self.r('arcticreach')
        elif k in self.spells and self.spells[k]['school'] in FIRE:r+=3*self.r('flamethrowing')
        elif k in self.spells and self.spells[k]['school']=='arcane':r+=3*self.r('arcanegeometry')
        return self.o['distance']<=r

    def usable(self,k):return k in self.spells and self.ready(k) and self.in_range(k)

    def choose(self):
        o=self.o;t=next((x for x in self.targets if o['target_hp']==0 or x['hp']>0),self.targets[0])
        if self.usable('icebarrier') and not self.up('barrier_policy'):return 'icebarrier'
        if self.school=='arcane' and self.usable('arcaneblast') and (self.ab if self.up('ab') else 0)<o['ab_stacks']:return 'arcaneblast'
        if o['targets']>1:
            if self.usable('coneofcold') and o['use_cone'] and (t['wc']>=3 or self.school=='frost'):return 'coneofcold'
            if self.school=='fire' and self.usable('flamestrike') and t['dots'].get('flamestrike',{}).get('until',0)<=self.time+3:return 'flamestrike'
            if self.usable('blastwave'):return 'blastwave'
            if self.school=='arcane' and self.usable('arcaneexplosion'):return 'arcaneexplosion'
            if self.usable('blizzard'):return 'blizzard'
        if self.usable('arcanewrath') and o['use_wrath']:return 'arcanewrath'
        if self.school=='fire' and o['use_scorch'] and self.r('improvedscorch') and self.usable('scorch') and (t['fv']<5 or t['fv_until']<self.time+4):return 'scorch'
        if self.usable('icelance') and self.up('fof') and self.fof:return 'icelance'
        if self.usable('coneofcold') and o['use_cone'] and t['wc_until']>self.time and t['wc']>=5:return 'coneofcold'
        if self.usable('pyroblast') and self.up('hu') and self.hu>=o['pyro_stacks']:return 'pyroblast'
        if self.school=='fire' and o['use_fireblast'] and self.r('heatingup') and self.usable('fireblast'):return 'fireblast'
        if o['use_barrage'] and self.up('mb') and self.usable('arcanemissiles'):return 'arcanemissiles'
        filler=o['filler'] if o['filler']!='auto' else {'arcane':'arcanemissiles','fire':'fireball','frost':'frostbolt'}[self.school]
        if self.usable(filler):return filler
        return next((k for k in ('frostbolt','fireball','arcanemissiles') if self.usable(k)),None)

    def act(self):
        o=self.o;r=self.r
        if not self.up('fof'):self.fof=0
        if not self.up('hu'):self.hu=0
        if not self.up('ab'):self.ab=0
        if o['cooldowns']:
            if r('arcanepower') and self.ready('ap'):self.aura['ap']=self.time+15;self.cd['ap']=self.time+180
            if r('combustion') and self.ready('comb') and self.comb<0:self.comb=0;self.comb_crits=0;self.cd['comb']=self.time+180
            race=o['race']
            if race in ('gnome','orc','troll','skyborne') and self.ready('racial'):
                self.aura[race]=self.time+({'gnome':8,'orc':15,'troll':o['berserking_duration'],'skyborne':15}[race]);self.cd['racial']=self.time+(180 if race=='troll' else 120)
        if o['consumables']:
            if o['level']>=49 and self.ready('potion') and self.pool-self.mana>=2250:self.gain(1350+900*self.random());self.cd['potion']=self.time+120;self.log('potion',mana=self.mana)
            gems=self.gems
            if self.gem<len(gems) and self.ready('gem') and self.pool-self.mana>=gems[self.gem][1]:
                lo,hi=gems[self.gem];self.gain(lo+(hi-lo)*self.random());self.gem+=1;self.cd['gem']=self.time+120
        if o['cooldowns'] and r('coldsnap') and self.ready('coldsnap') and self.fof and not self.ready('icelance'):
            for spell in ('icelance','coneofcold','icebarrier'):self.cd[spell]=self.time
            if o['cold_snap_resets_fireblast']:self.cd['fireblast']=self.time
            self.cd['coldsnap']=self.time+600;self.log('cold_snap')
        k=self.choose()
        if k is None:
            self.wait+=min(1,o['seconds']-self.time);self.schedule(self.time+1,'act',{});return
        row=self.spells[k];school=row['school'];mb=k=='arcanemissiles' and self.up('mb')
        basecost=.15*self.base_mana if k=='arcaneblast' else row['mana']
        cost=basecost*(1+self.ab if k=='arcaneblast' else 1)*(1-.05*r('frostchanneling') if school in FROST else 1)
        cost*=1+(.3 if self.up('ap') else 0)
        if self.up('gnome') and k!='icebarrier':cost*=.9
        free=mb or (self.cc and k!='icebarrier')
        if free:cost=0
        if cost>self.mana and not o['unlimited_mana']:
            if o['evocation'] and o['level']>=20 and self.ready('evo') and self.mana<self.pool*.25:
                self.aura['evo']=self.time+8;self.cd['evo']=self.time+480;self.evos+=1;self.log('evocation',mana=self.mana);self.schedule(self.time+8,'act',{});return
            dt=max(o['wand_speed'],.5-self.time)
            self.wait+=min(dt,o['seconds']-self.time)
            self.schedule(self.time+dt,'wand',{});self.schedule(self.time+dt,'act',{});return
        if cost and not o['unlimited_mana']:self.mana-=cost;self.spent+=cost;self.last_spend=self.time
        if self.cc and not mb and k!='icebarrier':self.cc=False
        if mb:self.aura['mb']=0
        cast=row['cast']
        if k=='frostbolt':cast=max(0,cast-.1*r('improvedfrostbolt'))
        if k in ('fireball','frostfirebolt','arcanewrath'):cast=max(0,cast-.1*r('accelerant'))
        pom=bool(o['cooldowns'] and r('presenceofmind') and self.ready('pom') and 0<cast<10)
        if k=='pyroblast':
            cast*=1-.25*self.hu
            if not pom:self.hu=0;self.aura['hu']=0
        if pom:cast=0;self.cd['pom']=self.time+180
        haste=self.haste();duration=(row['channel']/(2 if mb else 1) if row['channel'] else cast)/haste
        frozen=bool(self.fof and self.up('fof'))
        if k!='icebarrier' and self.fof:self.fof-=1
        self.castid+=1;self.casts[k]=self.casts.get(k,0)+1
        ctx=dict(key=k,id=self.castid,sp=self.power(),frozen=frozen,basecost=basecost)
        cd=max(0,row['cd']-r('improvedfireblast')) if k=='fireblast' else row['cd']
        self.cd[k]=self.time+(duration if cast else 0)+cd
        if k in ('icelance','fireblast'):
            # Sharing is official; talent/category duration needs server validation.
            ready=self.time+(8 if o['shared_blast_lance_base'] else cd)
            self.cd['icelance']=self.cd['fireblast']=ready
        self.log('cast',spell=k,cast_id=self.castid,duration=duration,cost=cost,mana=self.mana,ab=self.ab,fof=self.fof,hu=self.hu)
        if k=='icebarrier':
            self.aura['barrier']=self.time+60;self.aura['shield']=self.time+min(60,o['shield_lifetime']);self.aura['barrier_policy']=self.time+o['barrier_refresh']
        else:
            if k=='arcaneblast' and o['ab_apply']=='complete':self.schedule(self.time+duration,'ab',{})
            if row['channel']:
                for i in range(row['ticks']):self.schedule(self.time+duration*(i+1)/row['ticks'],'hit',ctx)
            else:self.schedule(self.time+duration+(o['travel_seconds'] if cast else 0),'hit',ctx)
        self.schedule(self.time+max(1,1.5/haste,duration),'act',{})

    def hit(self,c):
        k=c['key'];row=self.spells[k];school=row['school'];o=self.o;r=self.r
        if k=='arcaneblast' and o['ab_apply']=='impact':self.apply_ab()
        ids=[i for i in range(len(self.targets)) if self.alive(i)]
        if k not in AOE:ids=ids[:1]
        for i in ids:
            target=self.targets[i]
            if target['wc_until']<=self.time:target['wc']=0
            if target['fv_until']<=self.time:target['fv']=0
            wc=target['wc']
            if k=='coneofcold' and o['cone_consume_on_miss']:target['wc']=0
            hit=min(1-o['miss_floor'],[.96,.95,.94,.83][int(o['target_level_delta'])]+o['hit']+.02*r('precision'))
            if self.random()>=hit:self.log('miss',spell=k,target=i);continue
            frozen=c['frozen'] or target['frozen_until']>self.time
            cancrit=k!='blizzard' or o['periodic_crit'];crit=cancrit and self.random()<self.crit(k,school,frozen)
            sp=c['sp'] if o['snapshot_sp'] else self.power()
            if k=='arcanewrath':sp+=.05*self.pool
            coef=o['ice_lance_coef'] if k=='icelance' else o['wrath_coef'] if k=='arcanewrath' else row['coef']
            base=row['base']*(1+row['variance']*(self.random()-.5))
            damage=base+coef*sp
            if k=='coneofcold':
                damage=((damage+.07*wc*sp)*(1+.2*wc) if o['winter_order']=='inside' else damage*(1+.2*wc)+.07*wc*sp)
                damage*=1+[0,.12,.23,.35][r('improvedconeofcold')];target['wc']=0
            if k=='icelance' and frozen:damage*=4
            bonus=.5*(1+.2*(r('arcanemind') if school=='arcane' else r('iceshards') if school in FROST else 0))
            damage*=self.multiplier(school,i,k=='blizzard')*(1+bonus if crit else 1)
            self.deal(damage,k,i)
            if self.comb>=0 and school in FIRE:
                self.comb=min(10,self.comb+1)
                if crit:self.comb_crits+=1
                if self.comb_crits>=3:self.comb=-1
            if crit and school in FIRE|FROST:self.gain(.1*r('masterofelements')*c['basecost']/(row['ticks'] if row['channel'] else 1))
            if crit and school in FIRE and r('ignite'):self.add_ignite(i,damage*.08*r('ignite'))
            if k in ('fireball','frostfirebolt','fireblast','scorch') and r('heatingup'):
                add=int(crit)+int(k=='fireblast')
                if add:
                    if not self.up('hu'):self.hu=0
                    if not self.hu or o['heating_refresh']:self.aura['hu']=self.time+20
                    self.hu=min(3,self.hu+add)
            if k=='scorch' and r('improvedscorch') and self.random()<[0,.33,.66,1][r('improvedscorch')]:target['fv']=min(5,target['fv']+1);target['fv_until']=self.time+30
            if (k=='frostbolt' or (k=='icelance' and c['frozen'])) and r('winterschill') and self.random()<.2*r('winterschill'):target['wc']=min(5,target['wc']+1);target['wc_until']=self.time+o['winter_duration']
            chill=k in ('frostbolt','frostfirebolt','coneofcold') or (k=='blizzard' and r('improvedblizzard'))
            if chill and i<4:
                if r('fingersoffrost') and (o['target_level_delta']<3 or o['fof_on_boss']) and self.random()<.15:self.fof=r('fingersoffrost');self.aura['fof']=self.time+15
                if r('frostbite') and o['target_level_delta']<3 and self.random()<.05*r('frostbite'):target['frozen_until']=self.time+5
            if school in FIRE and r('impact') and o['target_level_delta']<3 and self.random()<[0,.03,.07,.10][r('impact')]:target['dots']['impact']=dict(until=self.time+2)
            if 'dot' in row:
                d=row['dot'];token=c['id'];target['dots'][k]=dict(until=self.time+d['period']*d['ticks'],token=token)
                amount=(d['base']+d['coef']*sp)*self.multiplier(school,i,True)
                for j in range(d['ticks']):self.schedule(self.time+d['period']*(j+1),'dot',dict(key=k,target=i,token=token,amount=amount,crit=self.crit(k,school,False),bonus=bonus,school=school))
            if c['id'] not in self.seen:
                self.seen.add(c['id'])
                if r('arcaneconcentration') and self.random()<.02*r('arcaneconcentration'):self.cc=True
                chance=(.2 if k=='arcaneblast' else .1)*r('missilebarrage') if k in ('arcaneblast','arcanewrath','fireball','frostbolt','frostfirebolt') else 0
                if chance and self.random()<chance:self.aura['mb']=self.time+o['barrage_duration']
            if o['race']=='undead' and self.ready('grave') and self.random()<.3:
                self.deal(.05*o['max_hp']*(1-o['partial_resist']),'touch_of_the_grave',i);self.cd['grave']=self.time+15

    def apply_ab(self):
        if not self.up('ab'):self.ab=0;self.aura['ab']=self.time+18
        self.ab=min(4,self.ab+1);self.log('blast_aura',stacks=self.ab,expires_at=self.aura['ab'])

    def add_ignite(self,i,amount):
        old=self.targets[i]['ignite'];bank=(old['bank'] if old else 0)+amount
        nxt=old['next'] if old and old['next']>self.time else self.time+2
        token=self.seq+1;self.targets[i]['ignite']=dict(bank=bank,next=nxt,ticks=2,token=token)
        self.schedule(nxt,'ignite',dict(target=i,token=token))

    def run(self):
        end=self.o['seconds'];killed=False
        while self.queue:
            t,_,kind,c=heapq.heappop(self.queue)
            if t>end:break
            self.time=t
            if kind=='act' and t<end:self.act()
            elif kind=='ab':self.apply_ab()
            elif kind=='hit':self.hit(c)
            elif kind=='wand':
                i=next((i for i in range(len(self.targets)) if self.alive(i)),0)
                self.deal(self.o['wand_dps']*self.o['wand_speed']*[1,1.13,1.25][self.r('wandspecialization')],'wand',i)
            elif kind=='regen':
                spirit=6.25+self.spirit/8
                fraction=16 if self.aura.get('evo',-1)>=self.time else 1 if self.time-self.last_spend>=5 else min(1,(.5 if self.o['level']>=34 else 0)+[0,.17,.33,.5][self.r('arcanemeditation')])
                mana=2*(spirit*fraction+self.o['mp5']/5)*(1.5 if self.up('skyborne') else 1)
                self.gain(mana);self.schedule(t+2,'regen',{})
            elif kind=='dot':
                dot=self.targets[c['target']]['dots'].get(c['key'],{})
                if dot.get('token')==c['token'] and self.alive(c['target']):
                    crit=self.o['periodic_crit'] and self.random()<c['crit']
                    damage=c['amount']*(1+c['bonus'] if crit else 1)
                    self.deal(damage,c['key']+'_dot',c['target'])
                    # Later Flamestrike damage is eligible; periodic crit capability remains a hypothesis.
                    if crit and c['key']=='flamestrike' and self.o['flamestrike_periodic_ignite'] and self.r('ignite') and self.alive(c['target']):
                        self.add_ignite(c['target'],damage*.08*self.r('ignite'))
                    if self.comb>=0 and c['school'] in FIRE and self.o['combustion_periodic']:self.comb=min(10,self.comb+1)
            elif kind=='ignite':
                dot=self.targets[c['target']]['ignite']
                if dot and dot['token']==c['token']:
                    amount=dot['bank']/dot['ticks'];self.deal(amount,'ignite',c['target']);dot['bank']-=amount;dot['ticks']-=1
                    if self.comb>=0 and self.o['combustion_periodic']:self.comb=min(10,self.comb+1)
                    if dot['ticks']:dot['next']=t+2;self.schedule(t+2,'ignite',c)
                    else:self.targets[c['target']]['ignite']=None
            if self.o['target_hp'] and all(x['hp']<=0 for x in self.targets):killed=True;end=t;break
        total=sum(self.parts.values());duration=max(end,1e-9)
        drink=(self.pool-self.mana)/self.o['drink_mps']
        cycle=duration+self.o['walk_seconds']+drink
        xp=self.o['xp_per_target']*self.o['targets']*(1+self.o['dungeon_xp_bonus'] if self.o['dungeon'] else 1)
        return dict(school=self.school,model='70707-experimental-event-sim',model_current=False,options=self.o,talents=self.build,
                    defensive_stats=dict(resilience_armor=.25*self.r('arcaneresilience')*self.intel,armor_spell_multiplier=1+.15*self.r('frostwarding'),absorb_multiplier=1+.1*self.r('frostwarding'),ward_negate_chance=.1*self.r('frostwarding')),
                    damage=total,dps=total/duration,elapsed=duration,killed=killed,damage_by_spell=self.parts,casts=self.casts,
                    mana_spent=self.spent,mana_restored=self.restored,mana_end=self.mana,max_mana=self.pool,mana_downtime=self.wait,evocations=self.evos,
                    recovery_seconds=drink,safe_target_xp_per_hour=3600*xp/cycle if killed else None,trace=self.trace)


def simulate(school,options=None,build=None):return Fight(school,{} if options is None else options,build).run()
