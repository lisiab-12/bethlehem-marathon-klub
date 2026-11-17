"""Administrator-only pages for BMK source-defined club awards.

IMPORTANT: Caller checks profile.role; database RLS independently blocks
non-admin read/write of Gold, championship, and milestone records.
"""
from datetime import date
from html import escape
import pandas as pd
import streamlit as st
from club_rules_engine import (
    km_rankings, known_half_marathon_rankings, comrades_results,
    comrades_first_by_group, event_results, fmt_time,
)


def _get(sb,table):
    result=[]
    for offset in range(0, 10000, 1000):
        records=sb.table(table).select('*').range(offset,offset+999).execute().data or []
        result.extend(records)
        if len(records)<1000:
            return result
    raise RuntimeError('Too many club-award records')


def _results_table(items, t):
    if not items:
        st.info(t('No verified qualifying records yet.',
                  'Nog geen geverifieerde kwalifiserende uitslae nie.'))
        return
    st.dataframe(pd.DataFrame(items), hide_index=True, use_container_width=True)


def render_club_awards(sb, df, profiles, user_id, lang, season_default):
    t = lambda en,af: af if lang=='AFR' else en
    def visible_label(text):
        st.markdown('<div style="background:#FFFFFF!important;color:#24201B!important;'
                    'border-left:4px solid #B74715;padding:6px 10px;margin:10px 0 6px;'
                    'border-radius:6px;font-size:16px;font-weight:700">'
                    + escape(str(text)) + '</div>', unsafe_allow_html=True)
    st.markdown(f'### {t("Official club awards — working preview", "Klubpryse — werkende voorskou")}')
    st.info(t('The rules below follow the new club document. Only approved races count. Rankings are preliminary until the committee checks and finalises winners.',
              'Die reëls volg die nuwe klubdokument. Slegs goedgekeurde wedlope tel. Ranglyste is voorlopig totdat die komitee wenners bevestig.'))
    try:
        champs=_get(sb,'bmk_club_champ_events')
        gold_rows=_get(sb,'bmk_comrades_gold_verifications')
        milestones=_get(sb,'bmk_comrades_milestones')
    except Exception:
        st.error(t('Award tables are not available. Run 01_supabase_awards_and_history.sql in Supabase SQL Editor first.',
                   'Prysstelseltabelle is nie beskikbaar nie. Voer eers 01_supabase_awards_and_history.sql in Supabase SQL Editor uit.'))
        return
    year_choices = sorted(set([int(season_default)] + [int(v) for v in df.get('season_year',pd.Series(dtype=int)).dropna().tolist()]), reverse=True)
    visible_label(t('Award season','Prysjaar'))
    year=st.selectbox(t('Award season','Prysjaar'), year_choices, key='bmk_awards_season', label_visibility='collapsed')
    records=df.to_dict('records')
    gold_ids={str(g['result_id']) for g in gold_rows}
    tab_summary,tab_comrades,tab_champs,tab_milestones=st.tabs([
        t('Year-end rankings','Jaareindranglyste'),
        'Comrades',
        t('Club Champs','Klubkampioenskappe'),
        t('Green Numbers','Groennommers'),
    ])
    with tab_summary:
        st.markdown(f'#### {t("Sportsman & Sportswoman of the Year", "Sportman en Sportvrou van die Jaar")}')
        st.caption(t('As stated in the club document: total qualifying race kilometres. Comrades medal points are displayed separately, not added to these totals.',
                     'Volgens die klubdokument: totale kwalifiserende wedloopkilometers. Comrades-medaljepunte word apart gewys en nie by die totale getel nie.'))
        a,b=st.columns(2)
        with a:
            st.markdown('**SPORTSMAN / SPORTMAN**')
            men=km_rankings(records,year,'MANS')
            if any(r['missing_distances'] for r in men):
                st.warning(t('Some athletes have approved races without a recorded distance. Totals may be incomplete.',
                             'Sommige atlete se goedgekeurde wedlope het geen afstand nie. Totale kan onvolledig wees.'))
            _results_table(men,t)
        with b:
            st.markdown('**SPORTSWOMAN / SPORTVROU**')
            women=km_rankings(records,year,'VROUE')
            if any(r['missing_distances'] for r in women):
                st.warning(t('Some athletes have approved races without a recorded distance. Totals may be incomplete.',
                             'Sommige atlete se goedgekeurde wedlope het geen afstand nie. Totale kan onvolledig wees.'))
            _results_table(women,t)
        st.markdown(f'#### {t("Runner with most known 21s", "Atleet met meeste bekende 21s")}')
        st.caption(t('Counts approved 21.1 km completions in the selected season. The club should confirm whether the prize is season-only or lifetime.',
                     'Tel goedgekeurde 21,1 km-voltooiings in die gekose jaar. Die klub moet bevestig of die prys jaarliks of lewenslank is.'))
        _results_table(known_half_marathon_rankings(records,year),t)
        st.caption(t('No official winners are announced by this screen.',
                     'Geen amptelike wenners word deur hierdie skerm aangekondig nie.'))

    with tab_comrades:
        st.markdown('#### Comrades')
        st.caption(t('Time-based points come from the supplied club table. At exactly a cutoff, the slower band applies unless the committee decides otherwise. Gold (100 points) must be independently verified.',
                     'Tydspunte volg die klub se tabel. Op die presiese afsnypunt geld voorlopig die stadiger band. Goud (100 punte) moet onafhanklik bevestig word.'))
        comrades=comrades_results(records,year,gold_ids)
        best_man=comrades_first_by_group(comrades,'MANS')
        best_woman=comrades_first_by_group(comrades,'VROUE')
        k1,k2=st.columns(2)
        k1.metric(t('Comrades — First Man','Comrades — Eerste Man'),
                  f"{best_man['athlete']} ({fmt_time(best_man['finish_seconds'])})" if best_man else '—')
        k2.metric(t('Comrades — First Woman','Comrades — Eerste Vrou'),
                  f"{best_woman['athlete']} ({fmt_time(best_woman['finish_seconds'])})" if best_woman else '—')
        st.caption(t('If Comrades course lengths differ across editions, the committee should verify comparability before naming a winner.',
                     'As Comrades-afstande tussen jare verskil, moet die komitee eers vergelykbaarheid bevestig.'))
        visible=[]
        for row in comrades:
            visible.append({'Athlete / Atleet':row['athlete'],'Group':row['group'],
                  'Race':row['race_name'],'Km':row['distance_km'],
                  'Time / Tyd':fmt_time(row['finish_seconds']),
                  'Medal band / Medaljeband':row['medal'],
                  'Points / Punte':row['points'],'Gold verified / Goud bevestig':row['official_gold']})
        _results_table(visible,t)
        st.markdown(f'##### {t("Verify official Gold", "Bevestig amptelike Goud")}')
        st.caption(t('Never use the first two club finishers as a substitute for the official Gold designation.',
                     'Moenie die eerste twee klublede verwar met amptelike Goud-toekenning nie.'))
        if comrades:
            options=[r for r in comrades if r['result_id']]
            if options:
                with st.form('bmk_gold_form'):
                    visible_label(t('Comrades finish','Comrades-voltooiing'))
                    chosen=st.selectbox(t('Comrades finish','Comrades-voltooiing'),options,
                        format_func=lambda r:f"{r['athlete']} · {fmt_time(r['finish_seconds'])}",label_visibility='collapsed')
                    visible_label(t('Official evidence / committee note','Amptelike bewys / komiteenota'))
                    note=st.text_input(t('Official evidence / committee note','Amptelike bewys / komiteenota'),label_visibility='collapsed')
                    save=st.form_submit_button(t('Confirm official Gold','Bevestig amptelike Goud'),type='primary')
                if save:
                    if len(note.strip())<4:
                        st.error(t('Enter a short verification note first.','Voeg eers ’n kort bevestigingsnota by.'))
                    elif chosen['result_id'] in gold_ids:
                        st.warning(t('Already verified.','Reeds bevestig.'))
                    else:
                        try:
                            sb.table('bmk_comrades_gold_verifications').insert({
                                'result_id':chosen['result_id'], 'verified_by':user_id,
                                'evidence_note':note.strip()}).execute()
                            st.success(t('Gold verified and saved.','Goud bevestig en gestoor.'))
                            st.rerun()
                        except Exception:
                            st.error(t('Could not save Gold verification.','Kon nie Goud-bevestiging stoor nie.'))

    with tab_champs:
        st.markdown(f'#### {t("Designated Club Champs races", "Aangewese klubkampioenskapwedlope")}')
        st.caption(t('Only committee-designated events count. This is not a ranking of the fastest club runner over each distance at any race.',
                     'Slegs deur die komitee aangewese wedlope tel. Dit is nie die vinnigste klubatleet se tyd oor alle wedlope nie.'))
        sel=[e for e in champs if int(e['season_year'])==year]
        if sel:
            st.dataframe(pd.DataFrame([{'Race':e['race_name'],'Category':e['race_category'],
                    'Date':e['race_date'] or 'Not recorded'} for e in sel]),hide_index=True,use_container_width=True)
            visible_label(t('Compare selected event','Vergelyk aangewese wedloop'))
            chosen=st.selectbox(t('Compare selected event','Vergelyk aangewese wedloop'),sel,
                                format_func=lambda e:f"{e['race_name']} · {e['race_category']} · {e['race_date'] or year}",label_visibility='collapsed')
            visible_label(t('Member group','Ledegroep'))
            grouped=st.selectbox(t('Member group','Ledegroep'),['All','MANS','VROUE','ANDER'],key='bmk_champ_group',label_visibility='collapsed')
            results=event_results(records,year,chosen,grouped)
            _results_table([{'Rank':r['rank'],'Athlete':r['athlete'],'Group':r['group'],
                             'Time':fmt_time(r['seconds']),'Distance':r['distance_km']} for r in results],t)
            st.caption(t('This is a race-specific finishing-time comparison. Official club-champ scoring and eligibility must be confirmed by the committee.',
                         'Hierdie is ’n tydvergelyking vir die spesifieke wedloop. Die komitee moet amptelike kampioenskapspunte en kwalifikasie bevestig.'))
        else:
            st.info(t('No championship events designated for this season. Surrender Hill is an example in the rules, not automatically confirmed for 2026.',
                      'Geen kampioenskapwedlope is vir die jaar aangewys nie. Surrender Hill is ’n voorbeeld en nie outomaties vir 2026 bevestig nie.'))
        with st.expander(t('Designate a championship race','Wys ’n kampioenskapwedloop aan')):
            with st.form('bmk_champ_event'):
                visible_label(t('Official race name','Amptelike wedloopnaam'))
                race_name=st.text_input(t('Official race name','Amptelike wedloopnaam'),label_visibility='collapsed')
                visible_label(t('Championship distance','Kampioenskapafstand'))
                distance=st.selectbox(t('Championship distance','Kampioenskapafstand'),['10 km','21.1 km','42.2 km'],label_visibility='collapsed')
                visible_label(t('Race date (optional)','Wedloopdatum (opsioneel)'))
                race_date=st.date_input(t('Race date (optional)','Wedloopdatum (opsioneel)'),value=None,label_visibility='collapsed')
                visible_label(t('Committee note (optional)','Komiteenota (opsioneel)'))
                note=st.text_input(t('Committee note (optional)','Komiteenota (opsioneel)'),label_visibility='collapsed')
                submit=st.form_submit_button(t('Save selected race','Stoor aangewese wedloop'),type='primary')
            if submit:
                if not race_name.strip():
                    st.error(t('Enter the official race name.','Voer die amptelike wedloopnaam in.'))
                else:
                    try:
                        sb.table('bmk_club_champ_events').insert({'season_year':year,
                            'race_name':race_name.strip(),'race_category':distance,
                            'race_date':race_date.isoformat() if race_date else None,
                            'committee_notes':note.strip(),'created_by':user_id}).execute()
                        st.success(t('Saved to committee event list.','Op komiteelys gestoor.'))
                        st.rerun()
                    except Exception:
                        st.error(t('Could not save the event.','Kon nie die wedloop stoor nie.'))

    with tab_milestones:
        st.markdown(f'#### {t("10th / 20th Comrades completion", "10de / 20ste Comrades-voltooiing")}')
        st.caption(t('A single-year spreadsheet does not establish an athlete’s lifetime Comrades count. Record milestones only after official verification.',
                     'Een jaar se resultate bewys nie ’n atleet se lewenslange Comrades-telling nie. Merk mylpale slegs na amptelike bevestiging.'))
        pbyid={str(p['id']):p.get('display_name') or str(p['id']) for p in profiles}
        shown=[{'Athlete':pbyid.get(str(m['member_id']),'Unknown'),
                'Milestone':m['milestone_number'],'Year':m['milestone_year'],
                'Evidence':m['evidence_note']} for m in milestones if int(m['milestone_year'])==year]
        _results_table(shown,t)
        if pbyid:
            with st.form('bmk_green_number'):
                visible_label(t('Athlete','Atleet'))
                member_id=st.selectbox(t('Athlete','Atleet'),list(pbyid),format_func=lambda x:pbyid[x],label_visibility='collapsed')
                visible_label(t('Comrades milestone','Comrades-mylpaal'))
                milestone=st.selectbox(t('Comrades milestone','Comrades-mylpaal'),[10,20],label_visibility='collapsed')
                visible_label(t('Year achieved','Jaar behaal'))
                milestone_year=st.number_input(t('Year achieved','Jaar behaal'),min_value=1900,max_value=2100,value=year,label_visibility='collapsed')
                visible_label(t('Verification note / evidence','Bevestigingsnota / bewys'))
                evidence=st.text_input(t('Verification note / evidence','Bevestigingsnota / bewys'),label_visibility='collapsed')
                submit=st.form_submit_button(t('Save verified milestone','Stoor bevestigde mylpaal'),type='primary')
            if submit:
                if len(evidence.strip())<4:
                    st.error(t('Add a verification note before saving.','Voeg eers ’n bevestigingsnota by.'))
                elif any(str(m['member_id'])==str(member_id) and int(m['milestone_number'])==int(milestone) for m in milestones):
                    st.warning(t('This milestone is already recorded; contact an administrator to correct it.',
                                 'Hierdie mylpaal is reeds aangeteken; kontak ’n administrateur vir wysiging.'))
                else:
                    try:
                        sb.table('bmk_comrades_milestones').insert({
                            'member_id':member_id,'milestone_number':milestone,
                            'milestone_year':int(milestone_year),
                            'evidence_note':evidence.strip(),'verified_by':user_id}).execute()
                        st.success(t('Milestone saved.','Mylpaal gestoor.'))
                        st.rerun()
                    except Exception:
                        st.error(t('Could not save milestone.','Kon nie mylpaal stoor nie.'))
