import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import date
st.set_page_config(page_title='Bethlehem Marathon Klub',page_icon='🏃',layout='wide')
ROOT=Path(__file__).parent
seed=json.loads((ROOT/'demo.json').read_text())
if 'results' not in st.session_state:
    st.session_state.results=[dict(r,year=2026,date=None) for r in seed['results']]
if 'decisions' not in st.session_state: st.session_state.decisions={}
lang=st.sidebar.radio('Language / Taal',['EN','AFR'],horizontal=True)
def t(en,af): return af if lang=='AFR' else en
st.sidebar.image(str(ROOT/'logo.png'),width=150)
st.sidebar.caption(t('Demo only • no secure login','Slegs demo • geen veilige aanmelding'))
role=st.sidebar.radio(t('Preview role','Voorskourol'),['Member','Committee'],format_func=lambda x:t(x,{'Member':'Lid','Committee':'Komitee'}[x]))
st.title('Bethlehem Marathon Klub')
st.caption(t('2026 running season • anonymised demonstration','2026 hardloopseisoen • geanonimiseerde demonstrasie'))
st.warning(t('Demo: role switching is not security. Changes last only for this browser session. Imported records are not verified.','Demo: rolwisseling is nie sekuriteit nie. Veranderinge geld net vir hierdie blaaiersessie. Ingevoerde uitslae is nie geverifieer nie.'))
members=pd.DataFrame(seed['members']); names=dict(zip(members.id,members.name)); groups=dict(zip(members.id,members.group))
def seconds(v):
    try:
        p=[int(x) for x in str(v).split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 and p[0]>=0 and 0<=p[1]<60 and 0<=p[2]<60 and sum(p)>0 else None
    except: return None
def frame():
    d=pd.DataFrame(st.session_state.results);d['athlete']=d.member.map(names);d['group']=d.member.map(groups);d['seconds']=d.time.map(seconds);d['distance']=pd.to_numeric(d.distance,errors='coerce');return d

def show(d):
    st.dataframe(d[['athlete','race','category','distance','time','date','status']],hide_index=True,use_container_width=True)
def eligible(d): return d[d.status.isin(['Imported','Approved'])]
def improvement(d):
    out=[]
    for (m,c),g in d.groupby(['member','category']):
        g=g[g.date.notna() & g.seconds.notna()].sort_values('date')
        if len(g)>=3 and c in ['10','21.1','42.2','5','15'] and g.date.nunique()>=2:
            a,b=g.iloc[0],g.iloc[-1];out.append({'member':m,'athlete':names[m],'category':c,'improvement':100*(a.seconds-b.seconds)/a.seconds,'baseline':a.time,'latest':b.time})
    return pd.DataFrame(out,columns=['member','athlete','category','improvement','baseline','latest'])
d=frame()
if role=='Member':
    m=st.sidebar.selectbox(t('Demo athlete','Demo-atleet'),members.id,format_func=lambda x:names[x]); own=d[d.member==m]; yr=st.sidebar.selectbox(t('Season','Seisoen'),sorted(d.year.unique(),reverse=True));own=own[own.year==yr]
    tab,history,add=st.tabs([t('My dashboard','My oorsig'),t('My results','My uitslae'),t('Add a race','Voeg wedloop by')])
    with tab:
        st.subheader(names[m]); q=eligible(own); a,b,c=st.columns(3);a.metric(t('Recorded km','Aangetekende km'),f'{q.distance.sum():.1f}');b.metric(t('Recorded races','Aangetekende wedlope'),len(q));c.metric(t('Pending','Hangende'),int((own.status=='Pending').sum()));st.caption(t('Includes imported, unverified records; unknown distances excluded.','Sluit ongeverifieerde invoere in; onbekende afstande uitgesluit.'))
        st.subheader(t('Best recorded times','Beste aangetekende tye'));show(q[q.seconds.notna()].sort_values('seconds').drop_duplicates('category'));st.subheader(t('Race history','Wedloopgeskiedenis'));show(own)
    with history: show(own)
    with add:
        with st.form('submit'):
            race=st.text_input(t('Race name','Wedloopnaam'));dt=st.date_input(t('Race date','Wedloopdatum'));cat=st.selectbox(t('Category','Kategorie'),['5','10','15','21.1','42.2','Ultra','Comrades','trail','Other']);dist=st.number_input(t('Actual km','Werklike km'),min_value=0.1,value=10.0);tm=st.text_input(t('Finish time HH:MM:SS','Eindtyd UU:MM:SS'));ok=st.form_submit_button(t('Submit','Dien in'))
            if ok:
                if not race.strip() or seconds(tm) is None: st.error(t('Enter a race and valid time.','Voer wedloop en geldige tyd in.'))
                else: st.session_state.results.append(dict(member=m,race=race.strip(),distance=dist,time=tm,category=cat,status='Pending',year=dt.year,date=dt.isoformat()));st.success(t('Submitted for review.','Ingedien vir hersiening.'));st.rerun()
else:
    overview,review,analysis,awards=st.tabs([t('Overview','Oorsig'),t('Review','Hersien'),t('Performance analysis','Prestasie-ontleding'),t('Awards builder','Prysbouer')])
    with overview:
        a,b,c=st.columns(3);a.metric(t('Athletes','Atlete'),len(members));b.metric(t('Race entries','Wedloopinskrywings'),len(d));c.metric(t('Pending','Hangende'),int((d.status=='Pending').sum()));st.bar_chart(d.groupby('category').size())
    with review:
        pending=d[d.status.isin(['Pending','Review','Imported'])];show(pending)
        if len(pending):
            ix=st.selectbox(t('Select record','Kies rekord'),pending.index,format_func=lambda i:f'{d.loc[i,"athlete"]} — {d.loc[i,"race"]}');a,b=st.columns(2)
            if a.button(t('Approve','Keur goed')): st.session_state.results[ix]['status']='Approved';st.rerun()
            if b.button(t('Reject','Verwerp')): st.session_state.results[ix]['status']='Rejected';st.rerun()
    with analysis:
        a,b,c=st.columns(3);yr=a.selectbox(t('Season','Seisoen'),sorted(d.year.unique(),reverse=True));group=b.selectbox(t('Member category','Ledekategorie'),['All']+sorted(d.group.unique()));cat=c.selectbox(t('Distance category','Afstandskategorie'),['All']+sorted(d.category.unique()));race=st.selectbox(t('Specific race','Spesifieke wedloop'),['All']+sorted(d.race.unique()));status=st.selectbox(t('Record status','Rekordstatus'),['All','Approved','Imported','Pending','Review','Rejected']);q=d[d.year==yr]
        for col,val in [('group',group),('category',cat),('race',race),('status',status)]:
            if val!='All': q=q[q[col]==val]
        metric=st.radio(t('Rank by','Rangskik volgens'),['Results','Fastest time','Most km','Most races','Improvement'],horizontal=True)
        if metric=='Fastest time':
            if cat=='All': st.info(t('Select a distance category for comparable times.','Kies n afstandskategorie vir vergelykbare tye.'))
            else: show(eligible(q).dropna(subset=['seconds']).sort_values('seconds'))
        elif metric=='Most km': st.dataframe(eligible(q).groupby('athlete').distance.sum().sort_values(ascending=False))
        elif metric=='Most races': st.dataframe(eligible(q).groupby('athlete').size().sort_values(ascending=False))
        elif metric=='Improvement': st.dataframe(improvement(eligible(q)));st.caption(t('Requires three dated comparable finishes; imported dates are unknown.','Vereis drie gedateerde vergelykbare uitslae; ingevoerde datums is onbekend.'))
        else: show(q)
        st.download_button(t('Export filtered results','Laai gefiltreerde uitslae af'),q.to_csv(index=False),'results.csv')
    with awards:
        st.subheader(t('Provisional weighted awards','Voorlopige geweegde pryse'));st.caption(t('Illustrative scoring, not official club rules. Imported data is unverified.','Illustratiewe puntetoekenning, nie amptelike klubreëls nie. Ingevoerde data is ongeverifieer.'))
        g=st.selectbox(t('Eligible category','Geskikte kategorie'),['MANS','VROUE','ANDER']);q=eligible(d[(d.group==g)&(d.year==2026)]);s=q.groupby('member').agg(races=('race','size'),km=('distance','sum'));s['athlete']=s.index.map(names)
        # Participation and distance are transparent relative-to-group maxima.
        w1=st.slider(t('Participation weight','Deelnamegewig'),0,100,50);w2=st.slider(t('Distance weight','Afstandgewig'),0,100,50);s['participation_score']=100*s.races/max(1,s.races.max()) if len(s) else 0;s['distance_score']=100*s.km/max(1,s.km.max()) if len(s) else 0
        if w1+w2==100:
            s['score']=(w1*s.participation_score+w2*s.distance_score)/100;st.dataframe(s.sort_values('score',ascending=False),hide_index=True);st.caption(t('Scores are relative to the highest value in the selected group. No official winner is selected.','Punte is relatief tot die hoogste waarde in die groep. Geen amptelike wenner word gekies nie.'))
        else: st.error(t('Weights must total 100%.','Gewigte moet 100% wees.'))
        st.info(t('Competitive performance, age grading and sportsmanship scoring require agreed rules and additional data.','Mededingende prestasie, ouderdomsgradering en sportmangees vereis ooreengekome reëls en bykomende data.'))
