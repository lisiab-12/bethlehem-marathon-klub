"""BMK pilot: password login and RLS-enforced Supabase race results.

No service-role key is used. All reads and writes run with the signed-in
member's short-lived access token and are subject to PostgreSQL RLS.
"""
from datetime import date
from html import escape
import pandas as pd
import streamlit as st
from supabase import create_client
from awards_engine import default_awards, compute_award

ORANGE = '#D95116'


def _fmt_time(value):
    if isinstance(value, int) and value > 0:
        hours, remainder = divmod(value, 3600)
        mins, secs = divmod(remainder, 60)
        return f'{hours:02}:{mins:02}:{secs:02}'
    return '—'


def _parse_time(v):
    try:
        h, m, s = [int(x) for x in v.strip().split(':')]
        if h < 0 or m not in range(60) or s not in range(60) or h * 3600 + m * 60 + s <= 0:
            return None
        return h * 3600 + m * 60 + s
    except (ValueError, AttributeError):
        return None


def _client():
    if 'bmk_db_client' not in st.session_state:
        st.session_state.bmk_db_client = create_client(st.secrets['BMK_SUPABASE_URL'], st.secrets['BMK_SUPABASE_KEY'])
    return st.session_state.bmk_db_client


def _auth():
    sb = _client()
    try:
        session = sb.auth.get_session()
        if session is None or not session.access_token:
            return None
        user_resp = sb.auth.get_user(session.access_token)
        return user_resp.user
    except Exception:
        return None


def _render(df):
    if df.empty:
        st.info('No results to display / Geen uitslae om te wys nie')
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def _fetch_all(query_builder, chunk=1000):
    """Fetch all authorized rows, not just the Supabase default first page."""
    out = []
    for start in range(0, 50000, chunk):
        page = query_builder().range(start, start + chunk - 1).execute().data or []
        out.extend(page)
        if len(page) < chunk:
            return out
    raise RuntimeError('Too many rows for pilot: contact administrator')



def _field_heading(label, container=st):
    """Always-visible high-contrast labels independent of Streamlit widget theme.

    Native widget labels remain available to assistive tech but are visually
    collapsed, avoiding the unreadable dark-theme-on-light-background mismatch.
    """
    clean = escape(str(label))
    container.markdown(
        '<div class="bmk-visible-label" '
        'style="background:#FFFFFF!important;color:#24201B!important;'
        'font-size:16px!important;line-height:1.4!important;'
        'font-weight:750!important;opacity:1!important;'
        'padding:7px 12px!important;margin:10px 0 6px!important;'
        'border:1px solid #DACBBA!important;border-left:4px solid #B74715!important;'
        'border-radius:8px!important">'
        '<span style="color:#24201B!important;opacity:1!important">'
        + clean + '</span></div>',
        unsafe_allow_html=True
    )

def run():
    st.markdown('''<style>
    /* Bethlehem Marathon Klub: high-contrast light theme for ALL live pages.
       Keeps login, results, submissions, committee and awards UI legible. */
    :root {color-scheme:light!important;}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background:#F6F0E7!important; color:#24201B!important;
    }
    [data-testid="stHeader"] {background:#F6F0E7!important;}
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background:#FFFCF7!important; color:#24201B!important;
    }
    [data-testid="stSidebar"] {border-right:1px solid #E1D4C5!important;}

    /* Titles, instructions, captions, and text: never inherit pale dark-mode colours. */
    .stApp :is(h1,h2,h3,h4,h5,h6),
    .stApp [data-testid="stMarkdownContainer"] :is(p,li,strong,em,small),
    .stApp [data-testid="stCaptionContainer"] :is(p,span),
    .stApp [data-testid="stText"] {
        color:#29231F!important;
        opacity:1!important;
    }
    .stApp [data-testid="stCaptionContainer"] :is(p,span) {
        color:#5A4D42!important;
    }
    .stApp [data-testid="stSidebar"] :is(p,span,label,strong,small),
    .stApp [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
    .stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
        color:#332B25!important;
        opacity:1!important;
    }

    /* Every form label: this was the source of the barely visible field headings. */
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-testid="stWidgetLabel"] *,
    .stApp [data-testid="stForm"] label,
    .stApp [data-testid="stForm"] label *,
    .stApp [data-testid="stForm"] [data-testid="stMarkdownContainer"] :is(p,span),
    .stApp [data-testid="stTextInput"] label *,
    .stApp [data-testid="stNumberInput"] label *,
    .stApp [data-testid="stDateInput"] label *,
    .stApp [data-testid="stSelectbox"] label *,
    .stApp [data-testid="stRadio"] label *,
    .stApp [data-testid="stTextArea"] label * {
        color:#302720!important;
        opacity:1!important;
        -webkit-text-fill-color:#302720!important;
    }
    .stApp [data-testid="stForm"] {
        background:#FFFCF7!important;
        border:1px solid #D7C7B5!important;
        border-radius:16px!important;
        padding:18px!important;
    }

    /* All native fields, dates, selects and numeric steppers share the same light theme. */
    .stApp [data-baseweb="input"],
    .stApp [data-baseweb="base-input"],
    .stApp [data-baseweb="select"] > div,
    .stApp [data-testid="stTextInput"] input,
    .stApp [data-testid="stNumberInput"] input,
    .stApp [data-testid="stDateInput"] input,
    .stApp [data-testid="stTextArea"] textarea {
        background:#FFFFFF!important;
        color:#29231F!important;
        -webkit-text-fill-color:#29231F!important;
        border-color:#B8A797!important;
        opacity:1!important;
    }
    .stApp [data-testid="stSelectbox"] [data-baseweb="select"] *,
    .stApp [data-testid="stSelectbox"] [data-baseweb="select"] span,
    .stApp [data-baseweb="select"] input,
    .stApp [data-baseweb="select"] svg,
    .stApp [data-testid="stNumberInput"] button,
    .stApp [data-testid="stDateInput"] svg {
        color:#29231F!important;
        fill:currentColor;
        opacity:1!important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder {
        color:#6A5B50!important;
        -webkit-text-fill-color:#6A5B50!important;
        opacity:1!important;
    }
    .stApp input:focus-visible, .stApp textarea:focus-visible {
        outline:2px solid #BD4A19!important;
        outline-offset:1px;
    }
    [role="listbox"], [role="listbox"] [role="option"] {
        background:#FFFFFF!important;
        color:#29231F!important;
    }
    [role="listbox"] [role="option"] * {color:#29231F!important;}

    /* Sidebar and action selector radios: both selected and unselected are readable. */
    .stApp [data-testid="stRadio"] [role="radiogroup"] {gap:10px!important;}
    .stApp [data-testid="stRadio"] [role="radiogroup"] label {
        background:#FFFFFF!important;
        border:1px solid #C9B8A6!important;
        border-radius:12px!important;
        padding:8px 12px!important;
        color:#29231F!important;
        opacity:1!important;
    }
    .stApp [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
        background:#FFF0E2!important;
        border:2px solid #B74715!important;
    }
    .stApp [data-testid="stRadio"] [role="radiogroup"] label *,
    .stApp [data-testid="stRadio"] [role="radiogroup"] label p {
        color:#29231F!important;
        -webkit-text-fill-color:#29231F!important;
        opacity:1!important;
    }

    /* Metrics and headings. */
    .stApp [data-testid="stMetric"] {
        background:#FFFFFF!important;
        border:1px solid #DED0C0!important;
        border-radius:18px!important;
        padding:18px!important;
    }
    .stApp [data-testid="stMetricLabel"],
    .stApp [data-testid="stMetricLabel"] *,
    .stApp [data-testid="stMetricValue"],
    .stApp [data-testid="stMetricValue"] * {
        color:#29231F!important;
        opacity:1!important;
    }

    /* Tabs and navigation including inactive controls. */
    .stApp [data-testid="stTabs"] [role="tab"] {
        color:#40352D!important;
        background:#FFFFFF!important;
        border:1px solid #D5C6B7!important;
        border-radius:10px!important;
        padding:10px 14px!important;
        opacity:1!important;
    }
    .stApp [data-testid="stTabs"] [role="tab"] *,
    .stApp [data-testid="stTabs"] [role="tab"] p {
        color:#40352D!important;
        opacity:1!important;
    }
    .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background:#B74715!important;
        color:#FFFFFF!important;
        border-color:#B74715!important;
    }
    .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] * {
        color:#FFFFFF!important;
        -webkit-text-fill-color:#FFFFFF!important;
    }
    .stApp [data-testid="stTabs"] [role="tab"]:focus-visible,
    .stApp button:focus-visible {
        outline:3px solid #E98C43!important;
        outline-offset:2px;
    }

    /* Buttons: high contrast for both primary and secondary states. */
    .stApp [data-testid="stFormSubmitButton"] button,
    .stApp .stButton button[kind="primary"],
    .stApp [data-testid="stDownloadButton"] button[kind="primary"] {
        background:#B74715!important;
        border:1px solid #9F3B10!important;
        color:#FFFFFF!important;
        font-weight:700!important;
        border-radius:12px!important;
    }
    .stApp [data-testid="stFormSubmitButton"] button *,
    .stApp .stButton button[kind="primary"] *,
    .stApp [data-testid="stDownloadButton"] button[kind="primary"] * {
        color:#FFFFFF!important;
        -webkit-text-fill-color:#FFFFFF!important;
        opacity:1!important;
    }
    .stApp .stButton button:not([kind="primary"]),
    .stApp [data-testid="stDownloadButton"] button:not([kind="primary"]) {
        background:#FFFFFF!important;
        color:#29231F!important;
        border:1px solid #9E8977!important;
    }
    .stApp .stButton button:not([kind="primary"]) * {
        color:#29231F!important;
    }

    /* Tables and editable values, where Streamlit exposes HTML wrappers. */
    .stApp [data-testid="stTable"] {background:#FFFFFF!important;color:#29231F!important;}
    .stApp [data-testid="stTable"] th {
        background:#F0E6D9!important;
        color:#29231F!important;
        font-weight:700!important;
    }
    .stApp [data-testid="stTable"] td {
        background:#FFFFFF!important;
        color:#29231F!important;
    }
    .stApp [data-testid="stDataFrame"] {
        background:#FFFFFF!important;
        border:1px solid #D7C7B5!important;
        border-radius:12px!important;
        overflow:hidden;
    }

    /* Readable notices. Never rely on low-opacity labels. */
    .stApp [data-testid="stAlert"] {opacity:1!important;}
    .stApp [data-testid="stAlert"] :is(p,span,strong) {opacity:1!important;}

    /* Only the orange hero has white text, deliberately. */
    .stApp .pilot-hero {
        background:linear-gradient(110deg,#A83B18,#D95116,#E88620)!important;
        border-radius:22px!important;
        color:#FFFFFF!important;
        padding:30px!important;
        margin-bottom:20px!important;
    }
    .stApp .pilot-hero, .stApp .pilot-hero :is(h1,h2,h3,h4,p,span,strong,small) {
        color:#FFFFFF!important;
        -webkit-text-fill-color:#FFFFFF!important;
        opacity:1!important;
    }
    .stApp .pilot-hero h2 {margin:0!important;}
    </style>''', unsafe_allow_html=True)
    st.sidebar.image('logo.png', width=180)
    _field_heading('Language / Taal', st.sidebar)
    lang = st.sidebar.radio('Language / Taal', ['EN', 'AFR'], horizontal=True, label_visibility='collapsed')
    def t(en, af): return af if lang == 'AFR' else en

    sb = _client()
    user = _auth()
    if user is None:
        st.markdown('<div class="pilot-hero"><h2>Bethlehem Marathon Klub</h2><p>Member login · Ledetoegang</p></div>', unsafe_allow_html=True)
        st.info(t('Pilot access is invitation-only. Ask the club administrator for your account.',
                  'Toetsweergawe is slegs op uitnodiging. Vra die klubadministrateur vir jou rekening.'))
        with st.form('login_form'):
            _field_heading(t('Email address', 'E-posadres'))
            email = st.text_input(t('Email address', 'E-posadres'), label_visibility='collapsed')
            _field_heading(t('Password', 'Wagwoord'))
            password = st.text_input(t('Password', 'Wagwoord'), type='password', label_visibility='collapsed')
            submit = st.form_submit_button(t('Sign in', 'Meld aan'), type='primary')
        if submit:
            try:
                sb.auth.sign_in_with_password({'email':email.strip(), 'password': password})
                st.rerun()
            except Exception:
                st.error(t('Sign in failed. Check your details or contact your club administrator.',
                           'Aanmelding het misluk. Gaan jou besonderhede na of kontak die klubadministrateur.'))
        return

    try:
        profiles = sb.table('profiles').select('id,display_name,member_number,member_group,age_category,role,active').eq('id', str(user.id)).limit(1).execute().data or []
        profile = profiles[0] if profiles else None
    except Exception:
        st.error(t('Cannot access member profile. Ask the administrator to check database setup.',
                   'Kan nie ledeprofiel laai nie. Vra die administrateur om die databasis na te gaan.'))
        return
    if not profile or not profile['active']:
        st.warning(t('Your account has not yet been activated by the committee.',
                     'Jou rekening is nog nie deur die komitee geaktiveer nie.'))
        if st.button(t('Sign out', 'Meld af')):
            sb.auth.sign_out(); st.rerun()
        return

    can_manage = profile['role'] in ('committee','awards_admin','super_admin')
    st.sidebar.markdown('**'+escape(profile['display_name'])+'**')
    st.sidebar.caption(t('Secure pilot • connected database', 'Veilige proefweergawe • gekoppelde databasis'))
    _field_heading(t('View', 'Aansig'), st.sidebar)
    view = st.sidebar.radio(t('View', 'Aansig'),
                            ['Member', 'Committee'] if can_manage else ['Member'],
                            format_func=lambda v: t('My dashboard','My oorsig') if v == 'Member' else t('Committee','Komitee'),
                            label_visibility='collapsed')
    if st.sidebar.button(t('Sign out', 'Meld af')):
        sb.auth.sign_out(); st.rerun()
    st.markdown(f'<div class="pilot-hero"><h2>{t("Your running year" if view == "Member" else "Committee command centre", "Jou hardloopjaar" if view == "Member" else "Komitee-beheersentrum")}</h2><p>{escape(profile["display_name"])} · Bethlehem Marathon Klub</p></div>', unsafe_allow_html=True)

    if view == 'Member':
        try:
            rows = _fetch_all(lambda: sb.table('race_results').select('id,race_name,race_date,discipline,distance_km,finish_seconds,status,created_at').eq('member_id',str(user.id)).order('race_date',desc=True))
        except Exception:
            st.error(t('Unable to retrieve your race results.','Kan nie jou wedloopuitslae laai nie.'))
            return
        d = pd.DataFrame(rows)
        _field_heading(t('Season','Seisoen'))
        year = st.selectbox(t('Season','Seisoen'), sorted(set([date.today().year] + ([int(str(x)[:4]) for x in d.race_date if x] if not d.empty else [])), reverse=True), label_visibility='collapsed')
        active = d[d.race_date.astype(str).str.startswith(str(year))] if not d.empty else d
        approved = active[active.status == 'Approved'] if not active.empty else active
        a,b,c=st.columns(3)
        a.metric(t('Approved kilometres','Goedgekeurde kilometers'), f'{approved.distance_km.sum():,.1f} km' if not approved.empty else '0 km')
        b.metric(t('Approved races','Goedgekeurde wedlope'),len(approved))
        c.metric(t('Awaiting review','Wag op hersiening'),int((active.status=='Pending').sum()) if not active.empty else 0)
        st.markdown(f"<div style='background:#FFF8EF;border:1px solid #E5D6C5;border-radius:16px;padding:14px 16px;margin:12px 0 18px 0;color:#4A4038'><strong>{t('Choose what you want to do','Kies wat jy wil doen')}</strong><br>{t('Use the buttons below to view your saved results or add a new race.','Gebruik die knoppies hieronder om jou uitslae te sien of ’n nuwe wedloop by te voeg.')}</div>", unsafe_allow_html=True)
        member_view = st.radio(
            t('Member action','Lede-aksie'),
            [t('My results','My uitslae'), t('Add a race','Voeg wedloop by')],
            horizontal=True,
            label_visibility='collapsed'
        )
        if member_view == t('My results','My uitslae'):
            if not active.empty:
                display = active[['race_name','race_date','discipline','distance_km','finish_seconds','status']].copy()
                display['finish_seconds']=display.finish_seconds.map(_fmt_time)
                display.columns=['Race','Date','Type','Distance (km)','Finish time','Status']
                _render(display)
            else:
                st.info(t('No races for this year yet. Use “Add a race” below to submit your first result.','Nog geen wedlope vir hierdie jaar nie. Gebruik “Voeg wedloop by” hieronder om jou eerste uitslag in te dien.'))
        else:
            st.markdown(f"<div style='background:#FFFFFF;border:1px solid #E5D6C5;border-radius:16px;padding:14px 16px;margin:8px 0 16px 0;color:#4A4038'><strong>{t('Add a new race result','Voeg ’n nuwe wedloopuitslag by')}</strong><br>{t('Fill in the form below. Your submission will be saved and sent to the committee for approval.','Vul die vorm hieronder in. Jou inskrywing sal gestoor word en na die komitee vir goedkeuring gestuur word.')}</div>", unsafe_allow_html=True)
            with st.form('new_race'):
                _field_heading(t('Race name','Wedloopnaam'))
                race=st.text_input(t('Race name','Wedloopnaam'), label_visibility='collapsed')
                c1,c2=st.columns(2)
                _field_heading(t('Race date','Wedloopdatum'), c1)
                when=c1.date_input(t('Race date','Wedloopdatum'), value=date.today(),max_value=date.today(), label_visibility='collapsed')
                _field_heading(t('Discipline','Dissipline'), c2)
                discipline=c2.selectbox(t('Discipline','Dissipline'), ['Road','Trail','Cross-country','Track','Other'], label_visibility='collapsed')
                c1,c2=st.columns(2)
                _field_heading(t('Actual distance (km)','Werklike afstand (km)'), c1)
                km=c1.number_input(t('Actual distance (km)','Werklike afstand (km)'), min_value=0.1, max_value=1000., value=10., step=0.1, label_visibility='collapsed')
                _field_heading(t('Finish time HH:MM:SS','Eindtyd UU:MM:SS'), c2)
                clock=c2.text_input(t('Finish time HH:MM:SS','Eindtyd UU:MM:SS'),placeholder='01:52:30', label_visibility='collapsed')
                submitted=st.form_submit_button(t('Submit for approval','Dien in vir goedkeuring'),type='primary')
            if submitted:
                secs=_parse_time(clock)
                if not race.strip() or secs is None:
                    st.error(t('Please enter a race name and valid positive finish time.','Vul asseblief ’n wedloopnaam en geldige eindtyd in.'))
                elif len(race.strip())>200:
                    st.error(t('Race name is too long.','Wedloopnaam is te lank.'))
                else:
                    try:
                        sb.table('race_results').insert({'member_id':str(user.id),'race_name':race.strip(),
                            'race_date':when.isoformat(),'discipline':discipline,'distance_km':km,
                            'finish_seconds':secs}).execute()
                        st.success(t('Saved! Awaiting committee review.','Gestoor! Wag op komiteegoedkeuring.'))
                        st.rerun()
                    except Exception:
                        st.error(t('Could not save the submission. Please contact the administrator.',
                                   'Kon nie die inskrywing stoor nie. Kontak die administrateur.'))
        return

    # All queries below are also protected by RLS; no trust in sidebar role alone.
    try:
        all_rows = _fetch_all(lambda: sb.table('race_results').select('id,member_id,race_name,race_date,discipline,distance_km,finish_seconds,status,created_at').order('race_date',desc=True))
        all_profiles = _fetch_all(lambda: sb.table('profiles').select('id,display_name,member_group,age_category,active'))
    except Exception:
        st.error(t('Unable to load the committee data.','Kan nie komiteedata laai nie.'))
        return
    df=pd.DataFrame(all_rows)
    profiles_by_id={str(p['id']):p for p in all_profiles}
    if not df.empty:
        df['athlete']=df.member_id.map(lambda v:profiles_by_id.get(str(v),{}).get('display_name','Unknown'))
        df['group']=df.member_id.map(lambda v:profiles_by_id.get(str(v),{}).get('member_group','Unknown'))
    overview,review,analysis,awards=st.tabs([t('Overview','Oorsig'),t('Review results','Hersien uitslae'),t('Analysis','Ontleding'),t('Awards preview','Prysvoorskou')])
    with overview:
        x,y,z=st.columns(3)
        x.metric(t('Active athletes','Aktiewe atlete'), sum(bool(p['active']) for p in all_profiles))
        y.metric(t('Race entries','Wedloopinskrywings'),len(df))
        z.metric(t('Awaiting review','Wag op hersiening'),int(df.status.eq('Pending').sum()) if not df.empty else 0)
        st.caption(t('Totals are from the permanent database. Only approved results count towards official metrics.',
                     'Totale kom uit die permanente databasis. Slegs goedgekeurde uitslae tel vir amptelike maatstawwe.'))
    with review:
        if df.empty: st.info(t('No submissions yet.','Nog geen inskrywings nie.'))
        else:
            pending=df[df.status=='Pending'].copy()
            if pending.empty: st.success(t('No pending submissions.','Geen hangende inskrywings nie.'))
            else:
                pending['finish_time']=pending.finish_seconds.map(_fmt_time)
                _render(pending[['athlete','race_name','race_date','distance_km','finish_time']])
                options = pending.id.tolist()
                _field_heading(t('Choose pending result','Kies hangende uitslag'))
                selected=st.selectbox(t('Choose pending result','Kies hangende uitslag'),options,
                    format_func=lambda rid: f"{pending.loc[pending.id==rid,'athlete'].iloc[0]} · {pending.loc[pending.id==rid,'race_name'].iloc[0]}", label_visibility='collapsed')
                with st.form('review_result'):
                    _field_heading(t('Decision','Besluit'))
                    decision=st.radio(t('Decision','Besluit'),['Approved','Rejected'],horizontal=True,label_visibility='collapsed')
                    save=st.form_submit_button(t('Record decision','Stoor besluit'),type='primary')
                if save:
                    try:
                        sb.table('race_results').update({'status':decision,'reviewed_by':str(user.id),'reviewed_at':date.today().isoformat()}).eq('id',selected).eq('status','Pending').execute()
                        st.success(t('Decision saved.','Besluit gestoor.'));st.rerun()
                    except Exception:
                        st.error(t('Could not save decision.','Kon nie besluit stoor nie.'))
    with analysis:
        if df.empty: st.info(t('No results yet.','Nog geen uitslae nie.'))
        else:
            a,b,c=st.columns(3)
            _field_heading(t('Season','Seisoen'),a)
            yr=a.selectbox(t('Season','Seisoen'), sorted({int(str(x)[:4]) for x in df.race_date if x}, reverse=True), label_visibility='collapsed')
            groups=sorted(df.group.dropna().unique().tolist())
            _field_heading(t('Member category','Ledekategorie'),b)
            group=b.selectbox(t('Member category','Ledekategorie'), ['All']+groups, label_visibility='collapsed')
            _field_heading(t('Discipline','Dissipline'),c)
            types=c.selectbox(t('Discipline','Dissipline'), ['All']+sorted(df.discipline.dropna().unique().tolist()), label_visibility='collapsed')
            q=df[df.race_date.astype(str).str.startswith(str(yr))].copy()
            if group!='All':q=q[q.group==group]
            if types!='All':q=q[q.discipline==types]
            _field_heading(t('Specific race','Spesifieke wedloop'))
            race=st.selectbox(t('Specific race','Spesifieke wedloop'), ['All']+sorted(q.race_name.dropna().unique().tolist()), label_visibility='collapsed')
            if race!='All':q=q[q.race_name==race]
            _field_heading(t('Review status','Hersieningstatus'))
            status=st.selectbox(t('Review status','Hersieningstatus'),['Approved','All','Pending','Rejected'], label_visibility='collapsed')
            if status!='All':q=q[q.status==status]
            if q.empty: st.info(t('No matching results.','Geen ooreenstemmende uitslae nie.'))
            else:
                q['Finish time']=q.finish_seconds.map(_fmt_time)
                _render(q[['athlete','group','race_name','race_date','discipline','distance_km','Finish time','status']])
                st.download_button(t('Download filtered CSV','Laai gefiltreerde CSV af'),q.to_csv(index=False).encode('utf-8-sig'),'bmk_secure_results.csv','text/csv')
    with awards:
        if profile['role'] not in ('awards_admin','super_admin'):
            st.info(t('Awards calculations are restricted to awards administrators.','Prysberekeninge is slegs vir prysadministrateurs.'))
        elif df.empty or not (df.status=='Approved').any():
            st.info(t('No approved results yet. Add test accounts and approve a few races to preview awards.',
                      'Nog geen goedgekeurde uitslae nie. Voeg toetsrekeninge en uitslae by om pryse te voorskou.'))
        else:
            st.warning(t('Provisional preview only. Official club award rules and historical imports are not yet finalised.',
                         'Slegs voorlopige voorskou. Amptelike klubprysreëls en historiese invoere is nog nie afgehandel nie.'))
            members={str(p['id']):p for p in all_profiles}
            calc=df.copy()
            calc['member']=calc.member_id
            calc['race']=calc.race_name
            calc['date']=calc.race_date
            calc['year']=calc.race_date.astype(str).str.slice(0,4).astype(int)
            calc['category']=calc.discipline.map(lambda v:'trail' if v=='Trail' else 'Road')
            calc['distance']=calc.distance_km
            calc['time']=calc.finish_seconds.map(_fmt_time)
            calc['seconds']=calc.finish_seconds
            calc['age_category']=calc.member_id.map(lambda v:members.get(str(v),{}).get('age_category') or 'Not recorded')
            calc=calc[calc.status=='Approved']
            calc['group']=calc.member_id.map(lambda v:members.get(str(v),{}).get('member_group','ANDER'))
            calc['athlete']=calc.member_id.map(lambda v:members.get(str(v),{}).get('display_name','Unknown'))
            awards_list=default_awards(int(calc.year.max()))
            _field_heading(t('Award','Prys'))
            award=st.selectbox(t('Award','Prys'),awards_list, format_func=lambda v:v['name_en'] if lang=='EN' else v['name_af'], label_visibility='collapsed')
            # Explicit preview only; finalized awards and editable definitions require further DB tables/policies.
            try:
                result=compute_award(calc,award,False,{})
                # compute_award returns a dict. Show key output without modifying it.
                if isinstance(result,dict):
                    rankings=result.get('rankings')
                    if isinstance(rankings,pd.DataFrame): _render(rankings)
                    elif rankings is not None: _render(pd.DataFrame(rankings))
                    else: st.info(t('Not enough qualifying results.','Nie genoeg kwalifiserende uitslae nie.'))
                else:
                    st.info(t('Award calculation is not available yet.','Prysberekening is nog nie beskikbaar nie.'))
            except Exception:
                st.info(t('This award is not yet calculable from current verified results.','Hierdie prys kan nog nie met huidige geverifieerde uitslae bereken word nie.'))
