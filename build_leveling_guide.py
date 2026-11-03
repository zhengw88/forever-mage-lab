"""Validate every leveling point and render the practical guide from one plan."""
import argparse, html, json, subprocess
from pathlib import Path
from current_talents import errors, NODES
ROOT=Path(__file__).resolve().parent

def build():
    plan=json.loads((ROOT/'leveling-plan.json').read_text());points=[];allocation={};level=10;rows=[]
    for s in plan['segments']:
        assert s['start']==level
        for n in range(s['start'],s['end']+1):
            k=s['talent'];allocation[k]=allocation.get(k,0)+1
            assert not errors(allocation,n,True),(n,errors(allocation,n,True))
            points.append(dict(level=n,key=k,name=NODES[k]['name'],rank=allocation[k],max_rank=NODES[k]['max_rank'],build=dict(allocation)))
        level=s['end']+1
        label=str(s['start']) if s['start']==s['end'] else f"{s['start']}–{s['end']}"
        rows.append('<tr><td>'+label+'</td><td>'+html.escape(NODES[k]['name'])+'</td><td>'+html.escape(s['why'])+'</td></tr>')
    assert len(points)==51 and level==61
    assert points[30]['level']==40 and points[30]['build']['icebarrier']==1
    script="const t=require('./current-talents.js');let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>{for(const p of JSON.parse(s)){if(t.errors(p.build,p.level,true).length)process.exit(1);const d=t.decode(t.encode(p.build));if(Object.keys(d).length!==Object.keys(p.build).length||Object.entries(p.build).some(([k,v])=>d[k]!==v))process.exit(1);}console.log('PASS: all 51 leveling allocations in JavaScript');});"
    subprocess.run(['node','-e',script],input=json.dumps(points),text=True,cwd=ROOT,check=True)
    text=(ROOT/'leveling-template.html').read_text().replace('__ROWS__','\n'.join(rows)).replace('__POINTS__',json.dumps(points)).replace('__SOURCES__',''.join('<li><a href="'+html.escape(u,quote=True)+'">'+html.escape(u.split('/')[-2] or u)+'</a></li>' for u in plan['sources']))
    return text

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();text=build();out=ROOT/'leveling.html'
    if a.check:assert out.read_text()==text,'stale leveling guide'
    else:out.write_text(text)
    print('PASS: 51 consecutive legal points; no respec; Barrier at 40; guide fresh')
