import json
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Bethlehem Marathon Klub | BMK', page_icon='🏃', layout='wide', initial_sidebar_state='expanded')
ROOT = Path(__file__).parent
seed = json.loads((ROOT / 'demo.json').read_text(encoding='utf-8'))
if 'results' not in st.session_state:
    st.session_state.results = [dict(r, year=2026, date=None) for r in seed['results']]

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif!important;}
.stApp {background:#F6F0E7;color:#26231F;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {background:#FFFCF7;border-right:1px solid #E9DFD2;}
[data-testid="stSidebar"] > div:first-child {padding-top:1.5rem;}
.block-container {padding-top:2.3rem;padding-bottom:3rem;max-width:1500px;}
h1,h2,h3 {letter-spacing:-.045em;color:#26231F!important;}
h1 {font-size:2.45rem!important;font-weight:800!important;}
h2 {font-size:1.5rem!important;font-weight:800!important;}
h3 {font-size:1.15rem!important;font-weight:700!important;}
p, label, [data-testid="stCaptionContainer"] {color:#554E45;}
[data-testid="stMetric"] {background:#FFFFFF;border:1px solid #EDE4D9;border-radius:18px;padding:19px 22px;box-shadow:0 5px 24px #7c4a1a08;min-height:120px;}
[data-testid="stMetricLabel"] {font-weight:600;color:#72685E;}
[data-testid="stMetricValue"] {font-size:2rem;font-weight:800;letter-spacing:-.04em;color:#2A2723;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px;border:0;flex-wrap:wrap;}
[data-testid="stTabs"] button[role="tab"] {border:1px solid #E7DCCE;border-radius:11px;background:#FFFCF8;padding:10px 17px;color:#5A5148;font-weight:700;}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {background:#D95116;color:white;border-color:#D95116;}
[data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] {display:none;}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {border-color:#EAE0D4;}
[data-testid="stDataFrame"] {border-radius:15px;overflow:hidden;border:1px solid #E9DFD4;}
[data-testid="stSelectbox"]>div, [data-testid="stTextInput"]>div, [data-testid="stNumberInput"]>div {border-radius:11px;}
.stButton>button[kind="primary"], [data-testid="stFormSubmitButton"] button {background:#D95116!important;color:#fff!important;border:0!important;border-radius:11px!important;font-weight:700!important;}
.stButton>button {border-radius:11px;font-weight:700;}
[data-testid="stAlert"] {border-radius:13px;}
[data-testid="stRadio"] label {font-weight:600;}
.hero {background:linear-gradient(112deg,#A73B18 0%,#E55C12 64%,#FF9E25 100%);border-radius:23px;padding:27px 30px;color:#fff;box-shadow:0 12px 32px #c7642130;margin-bottom:22px;}
.hero .eyebrow {font-size:12px;font-weight:800;letter-spacing:.16em;color:#FFE2C9;margin-bottom:8px;}
.hero h2 {font-size:2.05rem!important;color:white!important;margin:0 0 8px;}
.hero p {color:#FFF1E7;margin:0;}
.section-note {font-size:13px;color:#7E7061;margin-bottom:16px;}
.panel-title {font-size:19px;font-weight:800;letter-spacing:-.03em;margin:8px 0 10px;color:#2B2622;}
.pill {display:inline-block;border-radius:20px;background:#FCE8D8;color:#A74716;padding:6px 11px;font-weight:700;font-size:12px;}
.small-label {font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:#958578;font-weight:800;}
.st-key-info_box {background:white;border:1px solid #EDE4D9;border-radius:18px;padding:15px 20px;}
</style>''', unsafe_allow_html=True)

members = pd.DataFrame(seed['members'])
names = dict(zip(members.id, members.name))
groups = dict(zip(members.id, members.group))

lang = st.sidebar.radio('Language / Taal', ['EN', 'AFR'], horizontal=True)
def t(en, af): return af if lang == 'AFR' else en
st.sidebar.image(str(ROOT/'logo.png'), width=190)
st.sidebar.markdown('**BMK · 2026**')
st.sidebar.caption(t('Internal running club platform', 'Interne hardloopklubplatform'))
role = st.sidebar.radio(t('View as', 'Bekyk as'), ['Member','Committee'], format_func=lambda x: t(x, {'Member':'Lid','Committee':'Komitee'}[x]))
st.sidebar.divider()
st.sidebar.caption(t('DEMONSTRATION ONLY · No real login or persistent storage', 'SLEGS DEMO · Geen werklike aanmelding of permanente berging'))

def seconds(v):
    try:
        p=[int(x) for x in str(v).split(':')]
        return p[0]*3600+p[1]*60+p[2] if len(p)==3 and p[0]>=0 and 0<=p[1]<60 and 0<=p[2]<60 and sum(p)>0 else None
    except (ValueError,TypeError): return None

def frame():
    d=pd.DataFrame(st.session_state.results)
    d['athlete']=d.member.map(names)
    d['group']=d.member.map(groups)
    d['seconds']=d.time.map(seconds)
    d['distance']=pd.to_numeric(d.distance, errors='coerce')
    d['date']=d['date'].fillna('')
    d['year']=pd.to_numeric(d.year, errors='coerce').fillna(2026).astype(int)
    return d

def eligible(d): return d[d.status.isin(['Imported','Approved'])]
def shown(d):
    cols=['athlete','race','category','distance','time','date','status']
    q=d[cols].copy()
    q['date']=q['date'].replace('', t('Not recorded','Nie aangeteken nie'))
    q['distance']=q['distance'].map(lambda x:f'{x:,.1f} km' if pd.notna(x) else '—')
    q.columns=[t('Athlete','Atleet'),t('Race','Wedloop'),t('Category','Kategorie'),t('Distance','Afstand'),t('Time','Tyd'),t('Date','Datum'),t('Status','Status')]
    st.dataframe(q,hide_index=True,use_container_width=True)

def card_heading(text, subtitle=''):
    st.markdown(f'<div class="panel-title">{text}</div>',unsafe_allow_html=True)
    if subtitle: st.caption(subtitle)

def hero(title,subtitle,eyebrow='BETHLEHEM MARATHON KLUB'):
    st.markdown(f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{subtitle}</p></div>',unsafe_allow_html=True)

def improvement(d):
    out=[]
    for (m,c),g in d.groupby(['member','category']):
        g=g[(g.date!='') & g.seconds.notna()].sort_values('date')
        if len(g)>=3 and c in ['5','10','15','21.1','42.2'] and g.date.nunique()>=2:
            a,b=g.iloc[0],g.iloc[-1]
            out.append({'athlete':names[m], 'distance':f'{c} km','improvement %':round(100*(a.seconds-b.seconds)/a.seconds,1),'first':a.time,'latest':b.time})
    return pd.DataFrame(out,columns=['athlete','distance','improvement %','first','latest'])

d=frame()
if role=='Member':
    m=st.sidebar.selectbox(t('Demo athlete','Demo-atleet'),members.id,format_func=lambda x:names[x])
    yr=st.sidebar.selectbox(t('Season','Seisoen'),sorted(d.year.unique(),reverse=True))
    own=d[(d.member==m)&(d.year==yr)]
    hero(t('Your running year','Jou hardloopjaar'),f'{names[m]}  ·  {yr}  ·  '+t('Your personal race overview','Jou persoonlike wedloopoorsig'))
    tabs=st.tabs([t('Overview','Oorsig'),t('My results','My uitslae'),t('Add a race','Voeg wedloop by')])
    with tabs[0]:
        q=eligible(own)
        a,b,c=st.columns(3)
        a.metric(t('Recorded kilometres','Aangetekende kilometers'),f'{q.distance.sum():,.1f} km')
        b.metric(t('Race entries','Wedloopinskrywings'),len(q))
        c.metric(t('Awaiting review','Wag vir hersiening'),int((own.status=='Pending').sum()))
        st.caption(t('Imported results are not yet verified. Totals exclude unknown distances.','Ingevoerde uitslae is nog nie geverifieer nie. Onbekende afstande word uitgesluit.'))
        left,right=st.columns([1,1],gap='large')
        with left:
            card_heading(t('Best recorded times','Beste aangetekende tye'))
            best=q[q.seconds.notna()].sort_values('seconds').drop_duplicates('category')
            if len(best): shown(best)
            else: st.info(t('No timed finishes recorded.','Geen tye aangeteken nie.'))
        with right:
            card_heading(t('Race distance mix','Wedloopafstande'))
            mix=q.groupby('category').size().sort_values(ascending=False)
            if len(mix): st.bar_chart(mix,color='#DF641D',horizontal=True)
            else: st.info(t('No race records yet.','Nog geen wedlope nie.'))
        card_heading(t('Recent results','Onlangse uitslae'))
        shown(own.tail(8).iloc[::-1])
    with tabs[1]:
        card_heading(t('My race history','My wedloopgeskiedenis'))
        shown(own)
    with tabs[2]:
        card_heading(t('Submit a race result','Dien wedloopuitslag in'))
        st.caption(t('New submissions are pending until reviewed by the committee.','Nuwe inskrywings wag totdat die komitee dit hersien.'))
        with st.form('submit'):
            race=st.text_input(t('Race name','Wedloopnaam'))
            a,b=st.columns(2)
            dt=a.date_input(t('Race date','Wedloopdatum'),value=date.today())
            cat=b.selectbox(t('Distance category','Afstandskategorie'),['5','10','15','21.1','42.2','Ultra','Comrades','trail','Other'])
            a,b=st.columns(2)
            dist=a.number_input(t('Actual distance (km)','Werklike afstand (km)'),min_value=0.1,value=10.0)
            tm=b.text_input(t('Finish time HH:MM:SS','Eindtyd UU:MM:SS'),placeholder='01:52:30')
            if st.form_submit_button(t('Submit for review','Dien in vir hersiening'),type='primary'):
                if not race.strip() or seconds(tm) is None: st.error(t('Enter a race and valid finish time.','Voer wedloop en geldige eindtyd in.'))
                else:
                    st.session_state.results.append(dict(member=m,race=race.strip(),distance=dist,time=tm,category=cat,status='Pending',year=dt.year,date=dt.isoformat()))
                    st.success(t('Result submitted for review.','Uitslag ingedien vir hersiening.'))
                    st.rerun()
else:
    hero(t('Committee command centre','Komitee-beheersentrum'),t('Club performance, race results and confidential awards · 2026','Klubprestasie, wedloopuitslae en vertroulike pryse · 2026'))
    tabs=st.tabs([t('Overview','Oorsig'),t('Review results','Hersien uitslae'),t('Performance analysis','Prestasie-ontleding'),t('Awards builder','Prysbouer')])
    with tabs[0]:
        a,b,c,dcol=st.columns(4)
        a.metric(t('Athlete profiles','Atleetprofiele'),len(members))
        b.metric(t('Race entries','Wedloopinskrywings'),len(d))
        c.metric(t('Recorded kilometres','Aangetekende kilometers'),f'{eligible(d).distance.sum():,.1f}')
        dcol.metric(t('Pending review','Wag vir hersiening'),int((d.status=='Pending').sum()))
        st.caption(t('Demo totals include imported, unverified records.','Demo-totale sluit ongeverifieerde ingevoerde uitslae in.'))
        left,right=st.columns([1.4,1],gap='large')
        with left:
            card_heading(t('Race entries by distance','Wedloopinskrywings per afstand'))
            st.bar_chart(d.groupby('category').size().sort_values(ascending=False),color='#DD5D1B',horizontal=True)
        with right:
            card_heading(t('Member category breakdown','Ledekategorie-verdeling'))
            st.bar_chart(members.groupby('group').size(),color='#EEA15B')
        card_heading(t('Latest recorded results','Jongste aangetekende uitslae'))
        shown(d.tail(10).iloc[::-1])
    with tabs[1]:
        card_heading(t('Review submissions','Hersien inskrywings'))
        pending=d[d.status.isin(['Pending','Review','Imported'])]
        st.caption(t('Imported records are unverified; approving them in this demo is temporary.','Ingevoerde uitslae is ongeverifieer; goedkeuring in hierdie demo is tydelik.'))
        if len(pending):
            shown(pending)
            ix=st.selectbox(t('Choose result','Kies uitslag'),pending.index,format_func=lambda i:f'{d.loc[i,"athlete"]} · {d.loc[i,"race"]} · {d.loc[i,"time"]}')
            a,b,_=st.columns([1,1,3])
            if a.button(t('Approve','Keur goed'),type='primary'):
                st.session_state.results[int(ix)]['status']='Approved';st.rerun()
            if b.button(t('Reject','Verwerp')):
                st.session_state.results[int(ix)]['status']='Rejected';st.rerun()
        else: st.success(t('No records awaiting review.','Geen uitslae wag vir hersiening nie.'))
    with tabs[2]:
        card_heading(t('Performance explorer','Prestasie-ontleder'),t('Combine filters to find qualifying athletes and compare race results.','Kombineer filters om kwalifiserende atlete en uitslae te vergelyk.'))
        a,b,c=st.columns(3)
        yr=a.selectbox(t('Season','Seisoen'),sorted(d.year.unique(),reverse=True),key='analysis_year')
        group=b.selectbox(t('Member category','Ledekategorie'),['All']+sorted(d.group.dropna().unique()),key='analysis_group')
        cat=c.selectbox(t('Distance category','Afstandskategorie'),['All']+sorted(d.category.dropna().unique()),key='analysis_cat')
        a,b,c=st.columns(3)
        q=d[d.year==yr]
        if group!='All':q=q[q.group==group]
        if cat!='All':q=q[q.category==cat]
        race=a.selectbox(t('Specific race','Spesifieke wedloop'),['All']+sorted(q.race.dropna().unique()),key='analysis_race')
        status=b.selectbox(t('Record status','Rekordstatus'),['All','Approved','Imported','Pending','Review','Rejected'],key='analysis_status')
        athlete=c.selectbox(t('Athlete','Atleet'),['All']+sorted(q.athlete.dropna().unique()),key='analysis_athlete')
        for col,val in [('race',race),('status',status),('athlete',athlete)]:
            if val!='All':q=q[q[col]==val]
        a,b,c=st.columns(3)
        a.metric(t('Matching entries','Passende inskrywings'),len(q))
        b.metric(t('Athletes','Atlete'),q.member.nunique())
        c.metric(t('Matching kilometres','Passende kilometers'),f'{eligible(q).distance.sum():,.1f}')
        metric=st.radio(t('Compare by','Vergelyk volgens'),['Results','Fastest time','Most km','Most races','Improvement'],horizontal=True)
        if metric=='Fastest time':
            if cat=='All':st.info(t('Choose a distance category to compare finishing times fairly.','Kies ’n afstandskategorie om eindtye billik te vergelyk.'))
            else:
                timed=eligible(q).dropna(subset=['seconds']).sort_values('seconds')
                shown(timed)
        elif metric in ('Most km','Most races'):
            ag=eligible(q).groupby('athlete').agg(races=('race','size'),kilometres=('distance','sum')).reset_index()
            key='kilometres' if metric=='Most km' else 'races'
            ag=ag.sort_values(key,ascending=False).reset_index(drop=True)
            ag.insert(0,t('Rank','Plek'),range(1,len(ag)+1))
            ag['kilometres']=ag.kilometres.round(1)
            st.dataframe(ag,hide_index=True,use_container_width=True)
            if len(ag):st.bar_chart(ag.set_index('athlete')[key].head(10),color='#DE601C',horizontal=True)
        elif metric=='Improvement':
            imp=improvement(eligible(q))
            if imp.empty:st.info(t('No eligible improvements yet. This metric requires three dated finishes of the same distance; imported dates are missing.','Nog geen kwalifiserende verbeterings nie. Drie gedateerde uitslae oor dieselfde afstand is nodig; ingevoerde datums ontbreek.'))
            else:st.dataframe(imp.sort_values('improvement %',ascending=False),hide_index=True,use_container_width=True)
        else:shown(q)
        st.download_button(t('Export filtered CSV','Laai gefiltreerde CSV af'),q.to_csv(index=False).encode('utf-8-sig'),'bmk_filtered_results.csv',mime='text/csv')
    with tabs[3]:
        card_heading(t('Annual awards studio','Jaarlikse prysateljee'),t('Private, provisional rankings — not official award decisions.','Privaat, voorlopige ranglyste — nie amptelike prysbesluite nie.'))
        a,b=st.columns(2)
        g=a.selectbox(t('Eligible category','Kwalifiserende kategorie'),['MANS','VROUE','ANDER'])
        yr=b.selectbox(t('Award season','Prysseisoen'),sorted(d.year.unique(),reverse=True),key='award_year')
        q=eligible(d[(d.group==g)&(d.year==yr)])
        s=q.groupby('member').agg(races=('race','size'),km=('distance','sum'))
        s['athlete']=s.index.map(names)
        st.markdown('<div class="small-label">'+t('Adjust award weightings','Verstel prysgewigte')+'</div>',unsafe_allow_html=True)
        a,b=st.columns(2)
        w1=a.slider(t('Participation (%)','Deelname (%)'),0,100,50,5)
        w2=b.slider(t('Distance (%)','Afstand (%)'),0,100,50,5)
        st.caption(t('These two criteria are illustrative. Performance, age grading and sportsmanship require agreed rules and more data.','Hierdie twee kriteria is illustratief. Prestasie, ouderdomsgradering en sportmangees vereis reëls en meer data.'))
        if w1+w2!=100:st.error(t('Weights must total 100%.','Gewigte moet altesaam 100% wees.'))
        elif s.empty:st.info(t('No qualifying records.','Geen kwalifiserende uitslae nie.'))
        else:
            s['participation_score']=100*s.races/max(1,s.races.max())
            s['distance_score']=100*s.km/max(1,s.km.max())
            s['score']=(w1*s.participation_score+w2*s.distance_score)/100
            s=s.sort_values('score',ascending=False).reset_index(drop=True)
            s.insert(0,t('Rank','Plek'),range(1,len(s)+1))
            leader=s.iloc[0]
            st.markdown(f'<div class="hero"><div class="eyebrow">{t("CURRENT LEADING CANDIDATE · DEMO ONLY","HUIDIGE VOORLOPER · SLEGS DEMO")}</div><h2>{leader.athlete}</h2><p>{leader.score:.1f} / 100 {t("points","punte")} · {int(leader.races)} {t("races","wedlope")} · {leader.km:,.1f} km</p></div>',unsafe_allow_html=True)
            display=s[[t('Rank','Plek'),'athlete','races','km','participation_score','distance_score','score']].copy()
            display.columns=[t('Rank','Plek'),t('Athlete','Atleet'),t('Races','Wedlope'),'km',t('Participation score','Deelnamepunte'),t('Distance score','Afstandpunte'),t('Total score','Totale punte')]
            for col in [t('Participation score','Deelnamepunte'),t('Distance score','Afstandpunte'),t('Total score','Totale punte')]:display[col]=display[col].round(1)
            st.dataframe(display,hide_index=True,use_container_width=True)
            st.bar_chart(s.set_index('athlete')['score'].head(10),color='#D95116',horizontal=True)
            st.caption(t('Scores are relative to the maximum in this category. Imported results are unverified. No winner has been selected.','Punte is relatief tot die maksimum in hierdie kategorie. Ingevoerde uitslae is ongeverifieer. Geen wenner is gekies nie.'))
            st.download_button(t('Export provisional rankings','Laai voorlopige ranglys af'),display.to_csv(index=False).encode('utf-8-sig'),f'bmk_awards_{yr}_{g}.csv',mime='text/csv')
