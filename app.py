import json
from copy import deepcopy
from datetime import date
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from html import escape
import streamlit as st
from awards_engine import (METRICS, SCORE_LABELS, METRIC_HELP, default_awards,
                           new_award, compute_award, freeze_snapshot)

st.set_page_config(page_title='Bethlehem Marathon Klub | BMK', page_icon='🏃', layout='wide', initial_sidebar_state='expanded')
# Activate the separate RLS-backed pilot only when its two project secrets exist.
try:
    LIVE = bool(st.secrets.get('BMK_SUPABASE_URL') and st.secrets.get('BMK_SUPABASE_KEY'))
except (FileNotFoundError, KeyError):
    LIVE = False
if LIVE:
    from secure_app import run
    run()
    st.stop()

ROOT = Path(__file__).parent
seed = json.loads((ROOT / 'demo.json').read_text(encoding='utf-8'))
if 'member_ages' not in st.session_state:
    st.session_state.member_ages = {}  # Optional demo-only age on 31 December of season
if 'age_bands' not in st.session_state:
    st.session_state.age_bands = [(0, 39, 'Under 40'), (40, 49, '40–49'), (50, 59, '50–59'), (60, 69, '60–69'), (70, 120, '70+') ]
if 'award_definitions' not in st.session_state:
    st.session_state.award_definitions = default_awards(2026)
if 'manual_award_scores' not in st.session_state:
    st.session_state.manual_award_scores = {}
if 'award_snapshots' not in st.session_state:
    st.session_state.award_snapshots = {}
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
[data-testid="stDataFrame"] {border-radius:15px;overflow:hidden;border:1px solid #E9DFD4;background:white!important;}
[data-testid="stDataFrame"] iframe {color-scheme:light!important;}
[data-testid="stSelectbox"] [data-baseweb="select"]>div, [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {background:#fff!important;color:#302820!important;border:1px solid #E7DCCE!important;}
[data-testid="stRadio"] [role="radiogroup"] {gap:14px;}
[data-testid="stSidebar"] [data-baseweb="select"]>div {background:#fff!important;}
[data-testid="stPlotlyChart"] {background:#fff;border:1px solid #EDE4D9;border-radius:18px;padding:10px;}

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

:root {color-scheme:light;}
[data-baseweb="select"] > div {background:#FFF!important;color:#26231F!important;border-color:#E7DCCE!important;}
[data-baseweb="select"] span, [data-baseweb="select"] input {color:#26231F!important;}
[data-testid="stDataFrame"] {background:#FFF!important;}
.bmk-scroll {background:#fff;border:1px solid #EADFD3;border-radius:16px;overflow:auto;max-height:445px;box-shadow:0 5px 20px #683d1d09;margin:10px 0 14px;}
.bmk-table {border-collapse:collapse;min-width:650px;width:100%;background:#fff;color:#292520;font-size:13px;}
.bmk-table th {position:sticky;top:0;background:#F7EFE5;color:#746358;text-transform:none;font-size:12px;font-weight:800;letter-spacing:.01em;text-align:left;border-bottom:1px solid #E8DCCE;padding:12px 14px;white-space:nowrap;}
.bmk-table td {padding:11px 14px;border-bottom:1px solid #F0E7DC;white-space:nowrap;}
.bmk-table tr:nth-child(even) {background:#FFFCF8;}
.bmk-table tr:hover {background:#FFF1E7;}
.bmk-table .bmk-number {font-variant-numeric:tabular-nums;font-weight:700;}
.bmk-callout {border:1px solid #EACDB7;background:#FFF7EE;border-radius:16px;padding:13px 17px;color:#8F481B;margin:12px 0;}
.bmk-tiny {font-size:12px;color:#74685F;}
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

def age_category(age):
    if age is None or pd.isna(age): return 'Not recorded'
    for lo,hi,label in st.session_state.age_bands:
        if lo <= int(age) <= hi: return label
    return 'Not recorded'

def chart(data, x, y, horizontal=False, title=None):
    if data.empty: return
    fig=px.bar(data, x=y if horizontal else x, y=x if horizontal else y,
               orientation='h' if horizontal else 'v', color_discrete_sequence=['#DE5B16'])
    fig.update_layout(template='plotly_white', paper_bgcolor='white',plot_bgcolor='white',
        font=dict(color='#534B42',family='Arial'),margin=dict(l=12,r=14,t=15,b=20),
        height=290,showlegend=False,xaxis_title=None,yaxis_title=None)
    fig.update_xaxes(showgrid=not horizontal,gridcolor='#F1E9E0',zeroline=False)
    fig.update_yaxes(showgrid=horizontal,gridcolor='#F1E9E0',zeroline=False)
    st.plotly_chart(fig,use_container_width=True,theme=None)

def export_csv(df,filename,label):
    st.download_button(label,df.to_csv(index=False).encode('utf-8-sig'),filename,mime='text/csv')

def html_table(df, max_rows=150, numeric_cols=None):
    """Light, responsive and safely escaped read-only table."""
    if df is None or df.empty:
        st.info(t('No results to display.', 'Geen uitslae om te wys nie.'))
        return
    numeric_cols = set(numeric_cols or [])
    tbl = df.head(max_rows).copy()
    header = ''.join('<th>' + escape(str(c)) + '</th>' for c in tbl.columns)
    body = []
    for row in tbl.itertuples(index=False, name=None):
        cells=[]
        for col, val in zip(tbl.columns, row):
            if pd.isna(val): val = '—'
            if isinstance(val, float): val = f'{val:,.1f}'
            css = ' class="bmk-number"' if col in numeric_cols else ''
            cells.append(f'<td{css}>' + escape(str(val)) + '</td>')
        body.append('<tr>' + ''.join(cells) + '</tr>')
    markup = '<div class="bmk-scroll"><table class="bmk-table"><thead><tr>' + header + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'
    st.markdown(markup, unsafe_allow_html=True)
    if len(df) > max_rows:
        st.caption(t(f'Displaying first {max_rows} of {len(df)} rows. Download the full CSV for all results.',
                     f'Wys eerste {max_rows} van {len(df)} rye. Laai die volledige CSV af vir alle resultate.'))


def quality_flags(q):
    if q.empty: return pd.DataFrame(columns=['Issue','Count'])
    issues={
      'Missing race date':int(q.date.eq('').sum()),
      'Missing or invalid finish time':int(q.seconds.isna().sum()),
      'Missing or invalid distance':int((q.distance.isna() | (q.distance<=0)).sum()),
      'Imported, not approved':int(q.status.eq('Imported').sum()),
      'Possible duplicates':int(q.duplicated(subset=['member','race','distance','time','year'],keep=False).sum())}
    return pd.DataFrame({'Issue':list(issues),'Count':list(issues.values())})

def frame():
    d=pd.DataFrame(st.session_state.results)
    d['athlete']=d.member.map(names)
    d['group']=d.member.map(groups)
    d['age']=d.member.map(st.session_state.member_ages)
    d['age_category']=d['age'].map(age_category)
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
    html_table(q)

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
            if len(mix): chart(mix.rename_axis('Distance').reset_index(name='Races'), 'Distance','Races',horizontal=True)
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
            chart(d.groupby('category').size().sort_values(ascending=False).rename_axis('Distance').reset_index(name='Races'),'Distance','Races',horizontal=True)
        with right:
            card_heading(t('Member category breakdown','Ledekategorie-verdeling'))
            chart(members.groupby('group').size().rename_axis('Group').reset_index(name='Athletes'),'Group','Athletes')
        with st.expander(t('Optional age-category setup (demo)','Opsionele ouderdomskategorieë (demo)')):
            st.caption(t('No age categories are assumed to be official. Ages entered here are temporary and are not saved.',
                         'Geen ouderdomskategorieë word as amptelik aanvaar nie. Ingevoerde ouderdomme is tydelik.'))
            chosen=st.selectbox(t('Athlete','Atleet'),members.id,format_func=lambda x:names[x],key='age_member')
            value=st.number_input(t('Age at season end (optional)','Ouderdom teen seisoeneinde (opsioneel)'),min_value=0,max_value=120,value=int(st.session_state.member_ages.get(chosen,35)),key='age_value')
            if st.button(t('Save demo age','Stoor demo-ouderdom')):
                st.session_state.member_ages[chosen]=value
                st.rerun()
            st.caption(t('Provisional bands: Under 40, 40–49, 50–59, 60–69, 70+. They can be changed when the committee confirms its rules.',
                         'Voorlopige groepe: Onder 40, 40–49, 50–59, 60–69, 70+.'))
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
        cat=c.selectbox(t('Race distance','Wedloopafstand'),['All']+sorted(d.category.dropna().astype(str).unique()),key='analysis_cat')
        a,b,c=st.columns(3)
        q=d[d.year==yr]
        if group!='All':q=q[q.group==group]
        if cat!='All':q=q[q.category.astype(str)==cat]
        race=a.selectbox(t('Specific race','Spesifieke wedloop'),['All']+sorted(q.race.dropna().unique()),key='analysis_race')
        status=b.selectbox(t('Record status','Rekordstatus'),['All','Approved','Imported','Pending','Review','Rejected'],key='analysis_status')
        athlete=c.selectbox(t('Athlete','Atleet'),['All']+sorted(q.athlete.dropna().unique()),key='analysis_athlete')
        age_choice=st.selectbox(t('Optional age category','Opsionele ouderdomskategorie'),['All']+sorted(d.age_category.unique()),key='analysis_age')
        if age_choice!='All':q=q[q.age_category==age_choice]
        st.caption(t('Age groups are optional. No age is assumed for imported athletes; enter demo ages in Committee Overview.',
                     'Ouderdomsgroepe is opsioneel. Geen ouderdom word geraai nie; voeg demo-ouderdomme by onder Komitee-oorsig.'))
        for col,val in [('race',race),('status',status),('athlete',athlete)]:
            if val!='All':q=q[q[col]==val]
        a,b,c=st.columns(3)
        a.metric(t('Matching entries','Passende inskrywings'),len(q))
        b.metric(t('Athletes','Atlete'),q.member.nunique())
        c.metric(t('Matching kilometres','Passende kilometers'),f'{eligible(q).distance.sum():,.1f}')
        metric=st.radio(t('Compare by','Vergelyk volgens'),['Results','Fastest time','Most km','Most races','Improvement'],horizontal=True)
        if metric=='Fastest time':
            if cat=='All':st.info(t('Choose a race distance to compare equivalent distances.', 'Kies ’n wedloopafstand om gelyke afstande te vergelyk.'))
            else:
                timed=eligible(q).dropna(subset=['seconds','distance']).copy()
                # Category labels may be coarse (e.g. Ultra); require the same actual distance.
                distinct=sorted(timed.distance.unique())
                if len(distinct)>1:
                    actual=st.selectbox(t('Exact distance (km)','Presiese afstand (km)'),distinct)
                    timed=timed[timed.distance==actual]
                timed=timed.sort_values('seconds').drop_duplicates('member').reset_index(drop=True)
                timed.insert(0,'Rank',range(1,len(timed)+1))
                if len(timed):
                    html_table(timed[['Rank','athlete','race','distance','time','status']].rename(columns={'athlete':'Athlete','race':'Race','distance':'Distance (km)','time':'Finish time','status':'Status'}))
                    export_csv(timed[['Rank','athlete','race','distance','time','status']],'bmk_fastest_rankings.csv',t('Export rankings','Laai ranglys af'))
                else:st.info(t('No timed finishes for this distance.','Geen eindtye vir hierdie afstand nie.'))
        elif metric in ('Most km','Most races'):
            ag=eligible(q).groupby('athlete').agg(races=('race','size'),kilometres=('distance','sum')).reset_index()
            key='kilometres' if metric=='Most km' else 'races'
            ag=ag.sort_values(key,ascending=False).reset_index(drop=True)
            ag.insert(0,t('Rank','Plek'),range(1,len(ag)+1))
            ag['kilometres']=ag.kilometres.round(1)
            html_table(ag, numeric_cols=["races","kilometres"])
            if len(ag):chart(ag.head(10),'athlete',key,horizontal=True)
        elif metric=='Improvement':
            imp=improvement(eligible(q))
            if imp.empty:st.info(t('No eligible improvements yet. This metric requires three dated finishes of the same distance; imported dates are missing.','Nog geen kwalifiserende verbeterings nie. Drie gedateerde uitslae oor dieselfde afstand is nodig; ingevoerde datums ontbreek.'))
            else:html_table(imp.sort_values('improvement %',ascending=False))
        else:shown(q)
        export_csv(q[['athlete','group','age_category','race','category','distance','time','date','status']], 'bmk_filtered_results.csv',t('Export filtered CSV','Laai gefiltreerde CSV af'))
        with st.expander(t('Data quality checks','Datagehaltekontroles')):
            html_table(quality_flags(q))
            st.caption(t('Possible duplicates use athlete, race, distance, time and season; review manually before deleting.',
                         'Moontlike duplikate gebruik atleet, wedloop, afstand, tyd en seisoen; kontroleer voor verwydering.'))
    with tabs[3]:
        card_heading(t('Annual Awards Studio · Version 2.2', 'Jaarlikse Prysateljee · Weergawe 2.2'),
                     t('Editable award rules, auditable scores and provisional candidate rankings.',
                       'Wysigbare prysreëls, naspeurbare puntetellings en voorlopige kandidaatranglyste.'))
        st.markdown('<div class="bmk-callout">' + escape(t(
            'DEMO ONLY — Committee access is a preview switch, not a secure login. Award rules, committee scores and frozen previews exist only in this browser session. No winners are announced.',
            'SLEGS DEMO — Komiteetoegang is ’n voorskou-skakelaar, nie ’n veilige aanmelding nie. Prysreëls, komiteepunte en gevriesde voorskoue bestaan net vir hierdie blaaiersessie. Geen wenners word aangekondig nie.')) + '</div>', unsafe_allow_html=True)

        available = [x for x in st.session_state.award_definitions if not x.get('archived')]
        if not available:
            if st.button(t('Create first award', 'Skep eerste prys'), type='primary'):
                st.session_state.award_definitions.append(new_award())
                st.rerun()
        else:
            options = [x['id'] for x in available]
            labels = {x['id']: (x['name_af'] if lang == 'AFR' else x['name_en']) for x in available}
            # Switch awards BEFORE constructing the keyed widget. Streamlit forbids
            # writing to a widget key after that widget has been instantiated.
            go_to = st.session_state.pop('award_go_to', None)
            if go_to in options:
                st.session_state.selected_award = go_to
            elif st.session_state.get('selected_award') not in options:
                st.session_state.selected_award = options[0]
            chosen_id = st.selectbox(t('Choose award', 'Kies prys'), options,
                                     format_func=lambda x: labels.get(x, x), key='selected_award')
            award = next(x for x in available if x['id'] == chosen_id)
            is_frozen = chosen_id in st.session_state.award_snapshots
            btn1, btn2, btn3 = st.columns([1, 1, 1])
            if btn1.button(t('Create new award', 'Skep nuwe prys'), key='new_award_btn'):
                new = new_award()
                st.session_state.award_definitions.append(new)
                st.session_state.award_go_to = new['id']
                st.rerun()
            if btn2.button(t('Duplicate this award', 'Dupliseer hierdie prys'), key='duplicate_award'):
                new = new_award(award)
                st.session_state.award_definitions.append(new)
                st.session_state.award_go_to = new['id']
                st.rerun()
            if btn3.button(t('Archive award', 'Argiveer prys'), key='archive_award', disabled=is_frozen):
                award['archived'] = True
                st.session_state.award_go_to = next((x['id'] for x in available if x['id'] != chosen_id), None)
                st.rerun()

            if is_frozen:
                snap = st.session_state.award_snapshots[chosen_id]
                st.success(t('Frozen demonstration snapshot — edit a duplicate instead.',
                             'Gevriesde demo-voorskou — wysig eerder ’n duplikaat.'))
                st.caption(t('Captured (UTC): ', 'Vasgelê (UTC): ') + snap['captured_at_utc'])
                frozen_df = pd.DataFrame(snap['rankings'])
                cols = [c for c in ['rank','athlete','races','km','score','time','race','improvement_pct'] if c in frozen_df]
                if cols: html_table(frozen_df[cols],numeric_cols=['rank','races','km','score'])
                with st.expander(t('Frozen rules and evidence', 'Gevriesde reëls en bewyse')):
                    st.json({k: v for k,v in snap.items() if k != 'rankings'})
                st.download_button(t('Download frozen snapshot JSON', 'Laai gevriesde JSON af'),
                                   json.dumps(snap, indent=2, ensure_ascii=False, default=str),
                                   file_name='bmk_award_snapshot_demo.json', mime='application/json')
            else:
                st.markdown('### ' + t('1. Award definition', '1. Prysdefinisie'))
                ed1, ed2 = st.columns(2)
                award_en = ed1.text_input(t('Award name (English)', 'Prysnaam (Engels)'),
                                          value=award['name_en'], key=f'nameen_{chosen_id}')
                award_af = ed2.text_input(t('Award name (Afrikaans)', 'Prysnaam (Afrikaans)'),
                                          value=award['name_af'], key=f'nameaf_{chosen_id}')
                type_options = {
                    'weighted': t('Weighted Sportsman/Sportswoman score', 'Geweegde Sportman-/Sportvroupunt'),
                    'most_km': t('Most kilometres', 'Meeste kilometers'),
                    'most_races': t('Most completed races', 'Meeste voltooide wedlope'),
                    'fastest': t('Fastest finish at one distance', 'Vinnigste tyd oor een afstand'),
                    'improvement': t('Biggest improvement', 'Grootste vordering'),
                    'consistency': t('Most active months', 'Meeste aktiewe maande'),
                    'manual': t('Committee manual score', 'Komitee se handmatige telling'),
                }
                a, b, c = st.columns(3)
                mode = a.selectbox(t('Award calculation', 'Prysberekening'), list(type_options),
                                   index=list(type_options).index(award.get('mode','weighted')),
                                   format_func=lambda x: type_options[x], key=f'mode_{chosen_id}')
                season_opts = sorted(set(d.year.unique().tolist() + [int(award['season'])]), reverse=True)
                season = b.selectbox(t('Season', 'Seisoen'), season_opts,
                                     index=season_opts.index(int(award['season'])), key=f'yr_{chosen_id}')
                groups_available = ['All'] + sorted(members.group.dropna().unique().tolist())
                group = c.selectbox(t('Member grouping', 'Ledegroep'), groups_available,
                                    index=groups_available.index(award.get('group','All')) if award.get('group','All') in groups_available else 0,
                                    key=f'group_{chosen_id}')
                a, b, c = st.columns(3)
                age_opts = ['All'] + [label for _,_,label in st.session_state.age_bands]
                age_choice = a.selectbox(t('Optional age group', 'Opsionele ouderdomsgroep'), age_opts,
                                         index=age_opts.index(award.get('age_category','All')) if award.get('age_category','All') in age_opts else 0,
                                         key=f'age_{chosen_id}')
                discipline_opts = ['All', 'Trail', 'Not tagged trail']
                disc = b.selectbox(t('Discipline label', 'Dissipline-etiket'), discipline_opts,
                                   index=discipline_opts.index(award.get('discipline','All')) if award.get('discipline','All') in discipline_opts else 0,
                                   key=f'disc_{chosen_id}')
                min_races = c.number_input(t('Minimum completed races', 'Minimum voltooide wedlope'),
                                           min_value=1, max_value=100, value=int(award.get('min_races',1)), key=f'min_{chosen_id}')
                a, b = st.columns(2)
                race_opts = ['All'] + sorted(d.race.dropna().unique().tolist())
                race_default = award.get('race_filter','All')
                race_choice = a.selectbox(t('Specific race (optional)', 'Spesifieke wedloop (opsioneel)'),race_opts,
                                          index=race_opts.index(race_default) if race_default in race_opts else 0,
                                          key=f'race_{chosen_id}')
                target = b.number_input(t('Exact distance (km), for fastest-time awards', 'Presiese afstand (km), vir vinnigste tyd'),
                                        min_value=0.1, max_value=1000., value=float(award.get('target_distance') or 42.2),
                                        step=0.1, key=f'distance_{chosen_id}', disabled=mode!='fastest')
                st.caption(t('The source Excel file does not contain athlete ages or reliable discipline tags. Age filters only work after an age is entered for a demo athlete. Trail records are tagged; all other disciplines are unverified.',
                             'Die oorspronklike Excel het nie atleetouderdomme of betroubare dissipline-etikette nie. Ouderdomsfilters werk eers ná ’n demo-ouderdom ingevoer is. Roetetikette vir veldwedlope is beskikbaar; ander dissiplines is ongeverifieer.'))

                weights = deepcopy(award.get('weights', {}))
                if mode == 'weighted':
                    st.markdown('### ' + t('2. Set scoring weightings', '2. Stel puntgewigte in'))
                    st.caption(t('All weights must add up to 100%. Criteria with no data block the ranking rather than creating imaginary scores.',
                                 'Alle gewigte moet altesaam 100% wees. Kriteria sonder data blokkeer die ranglys eerder as om denkbeeldige punte te skep.'))
                    for i, metric in enumerate(METRICS):
                        col_label, col_slider = st.columns([1.2, 2.4])
                        with col_label: st.markdown('**' + SCORE_LABELS[metric] + '**')
                        with col_slider:
                            weights[metric] = st.slider(SCORE_LABELS[metric] + ' (%)', 0, 100,
                                                         int(weights.get(metric,0)), 5, key=f'weight_{chosen_id}_{metric}',
                                                         label_visibility='collapsed')
                    total_weight = sum(weights.values())
                    if total_weight == 100:
                        st.success(t('Weights total 100%.', 'Gewigte tel op tot 100%.'))
                    else:
                        st.warning(t(f'Weights total {total_weight}% — adjust to 100% for a ranking.',
                                     f'Gewigte tel op tot {total_weight}% — verstel na 100% vir ’n ranglys.'))
                    with st.expander(t('How each scoring metric works', 'Hoe elke puntmaatstaf werk')):
                        for metric in METRICS:
                            st.markdown(f'**{SCORE_LABELS[metric]}:** {METRIC_HELP[metric]}')
                else:
                    st.markdown('### ' + t('2. Scoring method', '2. Puntmetode'))
                    st.info(type_options[mode] + ' · ' + t('Uses one metric; weighted percentages are not applied.',
                                                           'Gebruik een maatstaf; geweegde persentasies is nie van toepassing nie.'))

                edited = deepcopy(award)
                edited.update(name_en=award_en.strip() or 'Untitled award',
                              name_af=award_af.strip() or 'Naamlose prys', mode=mode,
                              season=int(season), group=group, age_category=age_choice,
                              discipline=disc, min_races=int(min_races), race_filter=race_choice,
                              target_distance=float(target) if mode=='fastest' else None,
                              weights=weights)
                if st.button(t('Save award definition (this session)', 'Stoor prysdefinisie (hierdie sessie)'),
                             type='primary', key=f'save_{chosen_id}'):
                    award.update(edited)
                    st.success(t('Award settings saved for this session.', 'Prysinstellings vir hierdie sessie gestoor.'))

                st.markdown('### ' + t('3. Candidate scoring', '3. Kandidaatpuntetelling'))
                preview = st.checkbox(t('Include unverified imported records for demonstration',
                                         'Sluit ongeverifieerde ingevoerde rekords in vir demonstrasie'),
                                      value=True,key=f'include_{chosen_id}')
                if mode in ('weighted','manual') and (mode=='manual' or weights.get('contribution',0)>0):
                    with st.expander(t('Enter committee scores (demo only)', 'Voer komiteepunte in (slegs demo)'), expanded=True):
                        group_members = members if group=='All' else members[members.group==group]
                        mscore = st.selectbox(t('Athlete to score', 'Atleet om punte te gee'), group_members.id,
                                              format_func=lambda m: names[m],key=f'score_member_{chosen_id}')
                        existing_scores = st.session_state.manual_award_scores.get(chosen_id,{})
                        score_value = st.number_input(t('Committee score (0–100)', 'Komiteepunte (0–100)'),
                                                      min_value=0., max_value=100., value=float(existing_scores.get(mscore, 50.)),
                                                      step=5.,key=f'manual_value_{chosen_id}_{mscore}')
                        if st.button(t('Record score', 'Stoor telling'),key=f'record_score_{chosen_id}'):
                            st.session_state.manual_award_scores.setdefault(chosen_id,{})[mscore] = float(score_value)
                            st.rerun()
                        st.caption(t(f'{len(existing_scores)} athlete(s) currently have manual scores. Missing scores count as zero in a weighted preview.',
                                     f'{len(existing_scores)} atleet(e) het tans handmatige punte. Ontbrekende punte tel as nul in ’n geweegde voorskou.'))

                outcome = compute_award(d, edited, preview,
                                        st.session_state.manual_award_scores.get(chosen_id, {}))
                for msg in outcome['warnings']:
                    st.warning(msg)
                if outcome['blocked']:
                    st.info(outcome['reason'])
                else:
                    ranks = outcome['rankings']
                    winner = ranks.iloc[0]
                    hero(t('Leading candidate · provisional', 'Voorloper · voorlopig'),
                         escape(f"{winner['athlete']} · {winner['score']:,.1f} / 100 points · {int(winner['races'])} races · {winner['km']:,.1f} km"),
                         eyebrow=t('DEMONSTRATION, NOT AN OFFICIAL AWARD', 'DEMONSTRASIE, NIE ’N AMPTELIKE PRYS NIE'))
                    view_cols = ['rank','athlete','races','km']
                    if mode=='fastest': view_cols += ['race','time']
                    if mode=='improvement': view_cols += ['improvement_pct','improvement_evidence']
                    if mode=='consistency': view_cols += ['active_months']
                    if mode=='weighted':
                        view_cols += [f'{x}_score' for x in METRICS if weights.get(x,0)>0]
                        view_cols += ['missing_metric_evidence']
                    if mode=='manual': view_cols += ['manual_score']
                    view_cols += ['score']
                    headers = {'rank':t('Rank','Plek'), 'athlete':t('Athlete','Atleet'),
                               'races':t('Races','Wedlope'), 'km':'km', 'race':t('Race','Wedloop'),
                               'time':t('Finish time','Eindtyd'), 'score':t('Total / 100','Totaal / 100'),
                               'active_months':t('Active months','Aktiewe maande'),
                               'improvement_pct':t('Improvement (%)','Vordering (%)'),
                               'improvement_evidence':t('Evidence','Bewyse'),
                               'manual_score':t('Committee score','Komiteepunte'),
                               'missing_metric_evidence':t('Missing evidence','Ontbrekende bewyse')}
                    for metric in METRICS: headers[f'{metric}_score'] = SCORE_LABELS[metric] + ' / 100'
                    display = ranks[view_cols].rename(columns=headers).copy()
                    html_table(display, numeric_cols=[headers[k] for k in ['rank','races','km','score']])
                    st.caption(t('Score = sum of normalised metric scores multiplied by their saved weights. The fastest-time ranking sorts actual times; its points are only for display. Every source record can be reviewed in Performance Analysis.',
                                 'Telling = som van genormaliseerde maatstawwe vermenigvuldig met gewigte. Vinnigste tye word volgens werklike tyd gerangskik. Elke bronrekord kan in Prestasie-ontleding nagegaan word.'))
                    left,right = st.columns([1.3,1], gap='large')
                    with left:
                        card_heading(t('Leading candidates', 'Voorste kandidate'))
                        chart(ranks.head(10), 'athlete','score', horizontal=True)
                    with right:
                        card_heading(t('Scoring evidence', 'Puntebewyse'))
                        st.metric(t('Eligible athlete candidates', 'Kwalifiserende kandidate'), len(ranks))
                        st.metric(t('Completed source results', 'Voltooide bronuitslae'), outcome['source_count'])
                    st.download_button(t('Download provisional ranking CSV', 'Laai voorlopige ranglys CSV af'),
                                       display.to_csv(index=False).encode('utf-8-sig'),
                                       file_name=f'bmk_awards_{season}_{chosen_id}.csv', mime='text/csv')
                    st.download_button(t('Download calculation rules JSON', 'Laai berekeningsreëls JSON af'),
                                       json.dumps(edited, ensure_ascii=False, indent=2),
                                       file_name=f'bmk_award_rules_{chosen_id}.json', mime='application/json')
                    st.divider()
                    st.caption(t('Freezing saves a read-only *demo snapshot* in this session. It is NOT secure approval or long-term storage.',
                                 'Vries stoor ’n leesalleen *demo-voorskou* vir hierdie sessie. Dit is NIE veilige goedkeuring of permanente berging nie.'))
                    if st.button(t('Freeze demo preview (not official)', 'Vries demo-voorskou (nie amptelik nie)'),
                                 key=f'freeze_{chosen_id}'):
                        st.session_state.award_snapshots[chosen_id] = freeze_snapshot(edited, ranks,
                                                                                outcome['source_count'], preview)
                        award.update(edited)
                        st.rerun()
