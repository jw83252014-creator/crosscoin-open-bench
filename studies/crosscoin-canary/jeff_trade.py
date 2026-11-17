"""Jeff's trade: Kalshi 15m round. When BTC's side FIRST hits 90c+ (bid>=.90 yes side, or 1-ask>=.90 no side) at minute m (1-13),
look at SOL's SAME side ask at that minute. If ask in band -> buy floor(20/ask) contracts at the ask, hold to settlement.
Fee: Kalshi taker 0.07*p*(1-p) per contract, rounded UP to the next cent per order (Kalshi's schedule).
Data: Fable's full_candles.jsonl (bid/ask at minute close), official results from rounds/*.jsonl. Same loading as Fable's redo.py."""
import json, math, os, itertools, pickle
from collections import defaultdict
from datetime import datetime, timezone
H=os.path.dirname(os.path.abspath(__file__))
ep=lambda s:int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())
C=('BTC','ETH','SOL'); info={}
for c in C:
    for l in open(f'{H}/KX{c}15M.jsonl'):
        r=json.loads(l)
        if r.get('result') in('yes','no'): info[r['ticker']]=(ep(r['open_time']),1 if r['result']=='yes' else 0)
cd={}
for l in open(os.path.join(H,'full_candles.jsonl')):
    d=json.loads(l); o=info.get(d['t'])
    if o: cd[d['t']]={int((row[0]-o[0])//60):(row[1],row[2]) for row in d['c'] if row[1] is not None and row[2] is not None and 0<row[1]<row[2]<1}
rounds=[]
for bt,(o,_) in sorted(info.items(),key=lambda kv:kv[1][0]):
    if not bt.startswith('KXBTC15M'): continue
    suf=bt[len('KXBTC15M'):]; tk={c:f'KX{c}15M{suf}' for c in C}
    if all(tk[c] in cd and tk[c] in info and len(cd[tk[c]])>=10 for c in C): rounds.append((o,{c:cd[tk[c]] for c in C},{c:info[tk[c]][1] for c in C}))
print("rounds",len(rounds), datetime.fromtimestamp(rounds[0][0],timezone.utc), datetime.fromtimestamp(rounds[-1][0],timezone.utc))
def side_of(q,thr):
    if q[0]>=thr: return 1
    if 1-q[1]>=thr: return 0
    return None
def sideask(q,s): return q[1] if s else 1-q[0]
def sidebid(q,s): return q[0] if s else 1-q[1]
mon=lambda o:datetime.fromtimestamp(o,timezone.utc).strftime('%b')
# events: one per round, at BTC's first 90c+ minute
ev=[]
for o,q,res in rounds:
    for m in range(1,14):
        x=q['BTC'].get(m)
        if x and side_of(x,0.90) is not None:
            s=side_of(x,0.90); g=q['SOL'].get(m); e=q['ETH'].get(m)
            if g:
                later=[sidebid(q['SOL'][k],s) for k in range(m+1,15) if k in q['SOL']]
                ev.append(dict(o=o,m=m,s=s,ask=sideask(g,s),spr=g[1]-g[0],win=int(res['SOL']==s),btcwin=int(res['BTC']==s),
                    eth=sideask(e,s) if e else None, ethbid=sidebid(e,s) if e else None,
                    runup=int(any(b>=0.90 for b in later)), mon=mon(o)))
            break
print("rounds where BTC side hit 90c+ in min 1-13 with SOL quote:",len(ev))
def trade(e):
    p=e['ask']; n=math.floor(20/p+1e-9); fee=math.ceil(100*0.07*n*p*(1-p)-1e-9)/100
    pnl=n*(e['win']-p)-fee; return n,pnl,(e['win']-p-0.07*p*(1-p))
def stats(T):
    if not T: return None
    T=sorted(T,key=lambda e:e['o']); res=[trade(e) for e in T]
    st=cur=0
    for e in T:
        cur=cur+1 if not e['win'] else 0; st=max(st,cur)
    tot=sum(r[1] for r in res)
    return dict(n=len(T),win=100*sum(e['win'] for e in T)/len(T),ask=100*sum(e['ask'] for e in T)/len(T),
        net=100*sum(r[2] for r in res)/len(T),tot=tot,per=tot/len(T),streak=st,
        runup=100*sum(e['runup'] for e in T)/len(T),stake=sum(r[0]*e['ask'] for r,e in zip(res,T)))
def fmt(name,s):
    if not s: return f"{name:28s} n=0"
    return f"{name:28s} n={s['n']:<4d} win {s['win']:5.1f}%  avg ask {s['ask']:4.1f}c  net {s['net']:+6.2f}c/ct  P&L ${s['tot']:+8.2f} (${s['per']:+5.2f}/trade)  maxLstreak {s['streak']:2d}  ran-up90 {s['runup']:5.1f}%"
B={'50-65':(0.50,0.65),'55-60':(0.55,0.60),'50-55':(0.50,0.55),'60-65':(0.60,0.65)}
inb=lambda e,b:B[b][0]<=e['ask']<B[b][1]
out={}
for b in B:
    T=[e for e in ev if inb(e,b)]; s=stats(T); out[b]=s
    print("\n=== band",b); print(fmt('ALL',s))
    for mo in ('Sep','Oct','Nov'): print(fmt('  '+mo,stats([e for e in T if e['mon']==mo])))
    for lo,hi in ((1,3),(4,6),(7,9),(10,13)): print(fmt(f'  BTC hit 90 at min {lo}-{hi}',stats([e for e in T if lo<=e['m']<=hi])))
    print(f"  BTC itself settled same side: {100*sum(e['btcwin'] for e in T)/len(T):.1f}%   SOL ran up to 90+ then settled $0: {100*sum(e['runup'] and not e['win'] for e in T)/len(T):.1f}%   settled $1 without hitting 90 later: {100*sum(e['win'] and not e['runup'] for e in T)/len(T):.1f}%")
# all SOL ask bands for context
print("\n=== all SOL ask bands at BTC first-90 (context)")
for lo in range(5,100,10):
    print(fmt(f'{lo}-{lo+10}c',stats([e for e in ev if lo/100<=e['ask']<(lo+10)/100])))
# Variant search
print("\n=== VARIANT SEARCH (band x minutes x ETH filter x spread filter)")
bands=[(0.50,0.65),(0.55,0.60),(0.50,0.55),(0.60,0.65),(0.50,0.60),(0.55,0.65),(0.45,0.65),(0.40,0.70)]
mins=[(1,13),(1,3),(1,4),(1,6),(4,9),(7,13),(10,13)]
ethf=[None,0.80,0.85,0.90,'eth<0.70','eth<0.85']
sprf=[None,0.02,0.04]
V=[]
for (blo,bhi),(mlo,mhi),ef,sf in itertools.product(bands,mins,ethf,sprf):
    T=[e for e in ev if blo<=e['ask']<bhi and mlo<=e['m']<=mhi and (sf is None or e['spr']<=sf+1e-9)]
    if ef is None: pass
    elif isinstance(ef,float): T=[e for e in T if e['ethbid'] is not None and e['ethbid']>=ef]
    elif ef=='eth<0.70': T=[e for e in T if e['ethbid'] is not None and e['ethbid']<0.70]
    else: T=[e for e in T if e['ethbid'] is not None and e['ethbid']<0.85]
    s=stats(T)
    if s and s['n']>=30: V.append(((blo,bhi),(mlo,mhi),ef,sf,s,T))
print("variants tested (n>=30):",len(V)," positive:",sum(1 for v in V if v[4]['tot']>0))
for v in sorted(V,key=lambda v:-v[4]['net'])[:12]:
    print(fmt(f"{int(v[0][0]*100)}-{int(v[0][1]*100)} m{v[1][0]}-{v[1][1]} eth{v[2]} spr{v[3]}",v[4]))
    T=v[5]; print("      by month:", {mo:(lambda s:(s['n'],round(s['net'],2)) if s else None)(stats([e for e in T if e['mon']==mo])) for mo in ('Sep','Oct','Nov')})
pickle.dump(dict(ev=ev,V=[(v[0],v[1],v[2],v[3],v[4]) for v in V]),open(f'{H}/jeff_ev.pkl','wb'))
