"""Committee-only BMK Athlete Directory, annual membership and historic data review.

Access rules enforced in Supabase RLS. No service-role key. The UI does not
silently promote historical entries to official awards.
"""
from datetime import datetime, timezone
from html import escape

import pandas as pd
import streamlit as st

from season_logic import rollover_candidates, summarize_history, can_approve_history


def _fetch(sb, table, cols='*'):
    records = []
    for offset in range(0, 20000, 1000):
        page = sb.table(table).select(cols).range(offset, offset+999).execute().data or []
        records.extend(page)
        if len(page) < 1000:
            return records
    raise RuntimeError(f'{table}: too many records for this dashboard')


def _label(label):
    st.markdown(
        '<div style="background:#fff;color:#24201B!important;'
        'border-left:4px solid #B74715;border-radius:6px;'
        'padding:8px 10px;font-weight:750;margin:12px 0 6px">'
        + escape(label) + '</div>', unsafe_allow_html=True)


def _table(rows, empty):
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info(empty)


def render_season_manager(sb, lang, role, current_user_id):
    t = lambda en,af: af if lang=='AFR' else en
    can_edit = role in ('committee', 'super_admin')
    st.markdown('### ' + t('Athlete Directory & Season Manager', 'Atleetregister en Seisoenbestuur'))
    st.caption(t('A permanent athlete record survives new seasons, leaving and rejoining. Imported 2026 results remain provisional until verified.',
                 'Atleetrekords bly oor seisoene behoue. Ingevoerde 2026-uitslae bly voorlopig totdat dit geverifieer is.'))
    try:
        seasons = _fetch(sb,'bmk_seasons')
        athletes = _fetch(sb,'bmk_athletes')
        memberships = _fetch(sb,'bmk_season_memberships')
        history = _fetch(sb,'bmk_historical_results')
        profiles = _fetch(sb,'profiles','id,display_name,member_group,active')
    except Exception:
        st.error(t('Season tables unavailable. Run the two Season Manager SQL scripts in Supabase before updating GitHub.',
                   'Seisoentabelle nie beskikbaar nie. Voer eers die twee SQL-skripte in Supabase uit.'))
        return

    name_by_id = {str(a['id']): a.get('display_name') or 'Unknown' for a in athletes}
    athlete_by_id = {str(a['id']): a for a in athletes}
    years = sorted({int(s['season_year']) for s in seasons},reverse=True)
    if not years:
        st.warning(t('No seasons are configured.','Geen seisoene is opgestel nie.'))
        return
    _label(t('Season','Seisoen'))
    open_year = next((int(s['season_year']) for s in seasons if s['state']=='open'), years[0])
    selected_year = st.selectbox(t('Season','Seisoen'), years, index=years.index(open_year) if open_year in years else 0,
                                  label_visibility='collapsed',key='bmk_manager_year')
    season_info = next((s for s in seasons if int(s['season_year'])==selected_year),{})
    roster = [m for m in memberships if int(m['season_year'])==selected_year]
    yr_history = [r for r in history if int(r['season_year'])==selected_year]
    counts = summarize_history(history, selected_year)
    a,b,c,d=st.columns(4)
    a.metric(t('Roster entries','Ledelys-inskrywings'),len(roster))
    b.metric(t('Active','Aktief'),sum(m['membership_status']=='active' for m in roster))
    c.metric(t('Historical races','Historiese wedlope'),counts['entries'])
    d.metric(t('Awaiting review','Wag op hersiening'),counts['imported'])
    st.caption(t(f"Season status: {season_info.get('state','unknown')}. A provisional identity is not an approved award entry.",
                 f"Seisoenstatus: {season_info.get('state','unknown')}. Voorlopige identiteit beteken nie 'n goedgekeurde prysinskrywing nie."))

    tab_directory,tab_members,tab_history,tab_rollover = st.tabs([
        t('Athlete directory','Atleetregister'),t('Season membership','Seisoenlidmaatskap'),
        t('Historical races','Historiese wedlope'),t('New season','Nuwe seisoen')])

    with tab_directory:
        st.caption(t('The first 2026 import created one provisional record per Excel athlete reference. Potential duplicate people must be reconciled manually.',
                     'Die eerste invoer het een voorlopige rekord per Excel-atleetverwysing geskep. Moontlike duplikate moet handmatig nagegaan word.'))
        athlete_rows = [{
            'Athlete / Atleet':a['display_name'],
            'Identity / Identiteit':a['identity_status'],
            'Login linked / Aanmelding': 'Yes' if a.get('auth_user_id') else 'No',
            'Source / Bron': a.get('initial_source_member_ref') or 'Manual',
        } for a in sorted(athletes,key=lambda x:x['display_name'].casefold())]
        _table(athlete_rows,t('No athlete records yet.','Nog geen atleetrekords nie.'))
        if can_edit and athletes:
            st.markdown('#### '+t('Verify identity or link existing login', 'Bevestig identiteit of koppel bestaande aanmelding'))
            _label(t('Choose athlete','Kies atleet'))
            athlete_id=st.selectbox(t('Choose athlete','Kies atleet'),list(name_by_id),
                format_func=lambda i: f"{name_by_id[i]} · {athlete_by_id[i].get('initial_source_member_ref') or 'manual'}",
                label_visibility='collapsed',key='bmk_identity_athlete')
            selected = athlete_by_id[str(athlete_id)]
            st.info(t('Check the original spreadsheet and club membership list before confirming that this is one person.',
                      'Vergelyk eers die oorspronklike Excel en klubledelys voordat die identiteit bevestig word.'))
            if selected['identity_status']!='verified':
                confirmed=st.checkbox(t('I checked this athlete identity against the club records.',
                                       'Ek het die atleet se identiteit teen die klubrekords nagegaan.'),
                                      key=f'bmk_identity_confirm_{athlete_id}')
                if st.button(t('Mark identity verified','Merk identiteit as bevestig'),
                             disabled=not confirmed,key='bmk_mark_verified'):
                    try:
                        sb.table('bmk_athletes').update({'identity_status':'verified'}).eq('id',athlete_id).execute()
                        st.success(t('Athlete identity verified.','Atleetidentiteit bevestig.'));st.rerun()
                    except Exception:
                        st.error(t('Could not verify this identity.','Kon nie die identiteit bevestig nie.'))
            else:
                st.success(t('Identity verified. An app login can be linked, but is not required for historical results.',
                             'Identiteit bevestig. ’n App-aanmelding kan gekoppel word, maar is nie nodig vir historiese uitslae nie.'))
                unlinked_profiles={str(p['id']):p['display_name'] for p in profiles
                   if str(p['id']) not in {str(a['auth_user_id']) for a in athletes if a.get('auth_user_id')}}
                if not selected.get('auth_user_id') and unlinked_profiles:
                    _label(t('Match an existing login (optional)','Koppel ’n bestaande aanmelding (opsioneel)'))
                    user_id=st.selectbox(t('Existing profile','Bestaande profiel'),list(unlinked_profiles),
                        format_func=lambda i: unlinked_profiles[i],label_visibility='collapsed',key='bmk_match_login')
                    confirm_link=st.checkbox(t('I verified this login belongs to the selected athlete.',
                        'Ek het bevestig dat hierdie aanmelding aan die gekose atleet behoort.'),key=f'bmk_link_confirm_{athlete_id}')
                    if st.button(t('Link login to athlete','Koppel aanmelding aan atleet'),
                                 disabled=not confirm_link,key='bmk_link_login'):
                        try:
                            sb.table('bmk_athletes').update({'auth_user_id':user_id}).eq('id',athlete_id).execute()
                            st.success(t('Login linked. Historical results are now accessible only to this verified athlete and authorised committee members.',
                                         'Aanmelding gekoppel. Historiese uitslae is slegs vir hierdie atleet en bevoegde komiteelede beskikbaar.'))
                            st.rerun()
                        except Exception:
                            st.error(t('Could not link login. Check that it is not linked elsewhere.',
                                       'Kon nie aanmelding koppel nie. Kontroleer of dit elders gekoppel is.'))
                elif selected.get('auth_user_id'):
                    st.caption(t('This athlete already has a linked login.','Hierdie atleet het reeds ’n gekoppelde aanmelding.'))
        if can_edit:
            with st.expander(t('Add a new athlete','Voeg ’n nuwe atleet by')):
                with st.form('bmk_new_athlete'):
                    _label(t('Athlete name','Atleetnaam'))
                    full_name=st.text_input(t('Athlete name','Atleetnaam'),label_visibility='collapsed')
                    _label(t('Member group for this season','Ledegroep vir hierdie seisoen'))
                    grp=st.selectbox(t('Member group','Ledegroep'),['MANS','VROUE','ANDER'],label_visibility='collapsed')
                    create=st.form_submit_button(t('Create provisional athlete','Skep voorlopige atleet'),type='primary')
                if create:
                    if not full_name.strip():st.error(t('Enter a name.','Voer ’n naam in.'))
                    else:
                        try:
                            r=sb.table('bmk_athletes').insert({'display_name':full_name.strip(),'identity_status':'provisional'}).execute().data
                            sb.table('bmk_season_memberships').insert({'season_year':selected_year,
                                'athlete_id':r[0]['id'],'member_group':grp,'membership_status':'pending'}).execute()
                            st.success(t('Athlete created for review.','Atleet geskep vir hersiening.')); st.rerun()
                        except Exception:
                            st.error(t('Could not finish creating athlete. Review the directory before retrying to prevent duplicates.',
                                       'Kon nie atleet skep nie. Gaan eers die register na om duplikate te voorkom.'))

    with tab_members:
        display=[]
        for m in sorted(roster,key=lambda m:name_by_id.get(str(m['athlete_id']),'').casefold()):
            display.append({'Athlete / Atleet':name_by_id.get(str(m['athlete_id']),'Unknown'),
                'Group / Groep':m['member_group'],'Status':m['membership_status'],
                'Member no / Ledenommer':m.get('member_number') or '—',
                'Verified / Bevestig':athlete_by_id.get(str(m['athlete_id']),{}).get('identity_status')})
        _table(display,t('No members for this season.','Geen lede vir hierdie seisoen nie.'))
        if can_edit and athletes:
            st.markdown('#### '+t('Edit annual membership','Wysig jaarlikse lidmaatskap'))
            _label(t('Athlete','Atleet'))
            a_id=st.selectbox(t('Athlete','Atleet'),list(name_by_id),format_func=lambda i:name_by_id[i],
                              label_visibility='collapsed',key='bmk_member_edit_id')
            existing=next((m for m in roster if str(m['athlete_id'])==str(a_id)),None)
            status_options=['pending','active','inactive','left']
            group_options=['MANS','VROUE','ANDER']
            with st.form('bmk_member_edit'):
                _label(t('Membership status','Lidmaatskapstatus'))
                ms=st.selectbox(t('Membership status','Lidmaatskapstatus'),status_options,
                    index=status_options.index(existing['membership_status']) if existing else 0,
                    label_visibility='collapsed')
                _label(t('Member group','Ledegroep'))
                gp=st.selectbox(t('Member group','Ledegroep'),group_options,
                    index=group_options.index(existing['member_group']) if existing else 2,
                    label_visibility='collapsed')
                _label(t('Membership number (optional)','Ledenommer (opsioneel)'))
                mn=st.text_input(t('Membership number (optional)','Ledenommer (opsioneel)'),
                                 value=existing.get('member_number') or '' if existing else '',label_visibility='collapsed')
                save=st.form_submit_button(t('Save annual membership','Stoor jaarlidmaatskap'),type='primary')
            if save:
                payload={'member_group':gp,'membership_status':ms,'member_number':mn.strip() or None,
                         'updated_at':datetime.now(timezone.utc).isoformat()}
                try:
                    if existing:
                        sb.table('bmk_season_memberships').update(payload).eq('season_year',selected_year).eq('athlete_id',a_id).execute()
                    else:
                        payload.update({'season_year':selected_year,'athlete_id':a_id})
                        sb.table('bmk_season_memberships').insert(payload).execute()
                    st.success(t('Membership saved.','Lidmaatskap gestoor.'));st.rerun()
                except Exception:
                    st.error(t('Could not save membership.','Kon nie lidmaatskap stoor nie.'))

    with tab_history:
        st.caption(t('Historical entries are private. No entry contributes to awards until a committee member verifies the athlete and approves the result.',
                     'Historiese inskrywings is privaat. Geen inskrywing tel vir pryse voordat die identiteit en uitslag bevestig is nie.'))
        _label(t('Show results','Wys uitslae'))
        status_filter=st.selectbox(t('Show results','Wys uitslae'),['Imported','Approved','Rejected','All'],
                                   label_visibility='collapsed',key='bmk_hist_status')
        shown=[r for r in yr_history if status_filter=='All' or r['status']==status_filter]
        hist_rows=[{'Athlete / Atleet':name_by_id.get(str(r['athlete_id']),'Unknown'),
                    'Race / Wedloop':r.get('race_name') or 'Not recorded',
                    'Category / Kategorie':r['race_category'],
                    'Date / Datum':r.get('race_date') or 'Not recorded',
                    'Km':r.get('distance_km'),
                    'Time / Tyd':_time(r.get('finish_seconds')),
                    'Status':r['status'],
                    'Issues / Probleme':r.get('review_flags') or ''}
                   for r in shown]
        _table(hist_rows,t('No matching historical results.','Geen ooreenstemmende historiese uitslae nie.'))
        st.caption(t(f"Missing dates: {counts['missing_dates']} · missing times: {counts['missing_times']} · missing distances: {counts['missing_distances']}",
                     f"Ontbrekende datums: {counts['missing_dates']} · tye: {counts['missing_times']} · afstande: {counts['missing_distances']}"))
        if can_edit:
            reviewable=[r for r in yr_history if r['status']=='Imported']
            if reviewable:
                st.markdown('#### '+t('Review one historical race','Hersien een historiese wedloop'))
                _label(t('Choose race','Kies wedloop'))
                selected=st.selectbox(t('Choose race','Kies wedloop'),reviewable,
                    format_func=lambda r:f"{name_by_id.get(str(r['athlete_id']),'Unknown')} · {r.get('race_name') or 'Unknown race'} · {r['source_ref']}",
                    label_visibility='collapsed', key='bmk_hist_choose')
                athlete=athlete_by_id.get(str(selected['athlete_id']))
                valid=can_approve_history(selected,athlete)
                if not valid:
                    st.warning(t('Cannot approve yet: verify athlete identity and ensure race name and distance are recorded.',
                                 'Kan nog nie goedkeur nie: bevestig identiteit, wedloopnaam en afstand.'))
                if not selected.get('race_date'):
                    st.caption(t('Date missing: this entry can contribute to season kilometre totals after approval, but not chronology-dependent improvement.',
                                 'Datum ontbreek: ná goedkeuring kan kilometers tel, maar nie verbetering volgens tydsverloop nie.'))
                with st.form('bmk_hist_review'):
                    _label(t('Decision','Besluit'))
                    decision=st.radio(t('Decision','Besluit'),['Approved','Rejected'],horizontal=True,
                                      label_visibility='collapsed')
                    confirm=st.checkbox(t('I checked the evidence and athlete identity.',
                                         'Ek het die bewyse en atleetidentiteit nagegaan.'), key=f'bmk_hist_confirm_{selected["id"]}')
                    save=st.form_submit_button(t('Save reviewed result','Stoor hersiene uitslag'),type='primary')
                if save:
                    if not confirm:
                        st.error(t('Confirm the review before saving.','Bevestig eers die hersiening.'))
                    elif decision=='Approved' and not valid:
                        st.error(t('Missing information prevents approval.','Ontbrekende inligting verhoed goedkeuring.'))
                    else:
                        try:
                            sb.table('bmk_historical_results').update({'status':decision,
                                'reviewed_by':current_user_id,
                                'reviewed_at':datetime.now(timezone.utc).isoformat()}).eq('id',selected['id']).eq('status','Imported').execute()
                            st.success(t('Historical result reviewed.','Historiese uitslag hersien.'));st.rerun()
                        except Exception:
                            st.error(t('Could not save review.','Kon nie hersiening stoor nie.'))

    with tab_rollover:
        st.markdown('#### '+t('Prepare next season','Berei volgende seisoen voor'))
        _label(t('Next season year','Volgende seisoenjaar'))
        next_year=st.number_input(t('Next season year','Volgende seisoenjaar'),min_value=selected_year+1,
                                  max_value=2100,value=min(selected_year+1,2100),step=1,label_visibility='collapsed')
        dest=next((s for s in seasons if int(s['season_year'])==next_year),None)
        to_copy=rollover_candidates(memberships, selected_year, next_year)
        st.info(t(f'{len(to_copy)} active {selected_year} members can be carried into {next_year} as PENDING, awaiting committee renewal confirmation.',
                  f'{len(to_copy)} aktiewe {selected_year}-lede kan na {next_year} as HANGEND oorgedra word, onderhewig aan bevestiging.'))
        if can_edit:
            if dest is None:
                if st.button(t('Create draft season','Skep konsepseisoen'),type='primary',key='bmk_create_season'):
                    try:
                        sb.table('bmk_seasons').insert({'season_year':int(next_year),'title':f'{next_year} Season','state':'draft'}).execute()
                        st.success(t('Draft season created.','Konsepseisoen geskep.'));st.rerun()
                    except Exception:
                        st.error(t('Could not create season.','Kon nie seisoen skep nie.'))
            elif dest['state']!='draft':
                st.warning(t('Target season is not a draft. Review its status before copying memberships.',
                             'Teikenseisoen is nie ’n konsep nie. Gaan die status na.'))
            elif to_copy:
                confirmed=st.checkbox(t('Copy only active members, as pending. Do not automatically renew anyone.',
                                        'Dra slegs aktiewe lede oor, as hangend. Hernu niemand outomaties nie.'),key=f'bmk_rollover_confirm_{next_year}')
                if st.button(t('Copy members into draft','Kopieer lede na konsep'),
                             disabled=not confirmed,key='bmk_do_rollover'):
                    try:
                        sb.table('bmk_season_memberships').insert(to_copy).execute()
                        st.success(t('Members copied as pending. Historical results are unchanged.',
                                     'Lede oorgedra as hangend. Historiese uitslae is onveranderd.'));st.rerun()
                    except Exception:
                        st.error(t('Could not copy all memberships. Refresh and check for duplicates before trying again.',
                                   'Kon nie alle lidmaatskappe oordra nie. Verfris en kontroleer eers duplikate.'))
            else:
                st.success(t('No additional eligible members to copy.','Geen verdere geskikte lede om oor te dra nie.'))
            if role=='super_admin' and dest is not None and dest['state']=='draft':
                st.warning(t('Only activate the new season when the committee is ready. The current open season will be closed.',
                             'Aktiveer slegs wanneer die komitee gereed is. Die huidige oop seisoen sal sluit.'))
                confirm_open=st.checkbox(t('I approve activating this season and closing the previous one.',
                                           'Ek keur die nuwe seisoen en sluiting van die vorige een goed.'),key=f'bmk_activate_confirm_{next_year}')
                if st.button(t('Activate new season','Aktiveer nuwe seisoen'),disabled=not confirm_open,key='bmk_activate'):
                    try:
                        sb.rpc('bmk_activate_season',{'target_year':int(next_year)}).execute()
                        st.success(t('New season is now active.','Nuwe seisoen is nou aktief.'));st.rerun()
                    except Exception:
                        st.error(t('Could not activate season.','Kon nie seisoen aktiveer nie.'))


def _time(seconds):
    if seconds is None: return 'Not recorded'
    try:
        val=int(seconds)
        if val <= 0: return 'Not recorded'
        h,rem=divmod(val,3600)
        m,s=divmod(rem,60)
        return f'{h:02d}:{m:02d}:{s:02d}'
    except (ValueError,TypeError):
        return 'Not recorded'
