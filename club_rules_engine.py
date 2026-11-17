"""Bethlehem Marathon Klub awards as supplied in SKILLIE APP.pdf (17 Nov 2026).

This module intentionally DOES NOT combine Comrades points into Sportsman/
Sportswoman totals. The supplied club sheet defines those awards by total km,
without stating how Comrades points interact with them.

Only APPROVED races are considered. Imported/unverified staging data is excluded.
Official Gold and historical 10th/20th Comrades milestones require separate
committee verification. Club Champs are restricted to committee-designated races.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Iterable


def _num(v):
    try:
        if v is None or v == '':
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _seconds(v):
    try:
        s = int(v)
        return s if s > 0 else None
    except (TypeError, ValueError):
        return None


def _year(row):
    y = row.get('season_year')
    if y is not None:
        try:
            return int(y)
        except (TypeError, ValueError):
            pass
    d = row.get('race_date')
    if isinstance(d, (date, datetime)):
        return d.year
    if d and str(d)[:4].isdigit():
        return int(str(d)[:4])
    return None


def _category(row):
    cat = row.get('race_category')
    if cat:
        return str(cat)
    name = str(row.get('race_name') or '').casefold()
    if 'comrades' in name:
        return 'Comrades'
    km = _num(row.get('distance_km'))
    if km is not None:
        for distance, label in [(10, '10 km'), (21.1, '21.1 km'), (42.2, '42.2 km')]:
            if abs(km-distance) <= .05:
                return label
        if km > 42.2:
            return 'Ultra'
    return 'Other'


def is_approved(row, season_year):
    return str(row.get('status')) == 'Approved' and _year(row) == int(season_year)


def qualifying_rows(records: Iterable[dict], season_year):
    return [dict(r) for r in records if is_approved(r, season_year)]


def _identity(row):
    return str(row.get('member_id') or row.get('athlete') or '')


def _label(row):
    return str(row.get('athlete') or row.get('display_name') or _identity(row))


def _group(row):
    return str(row.get('group') or row.get('member_group') or 'ANDER').upper()


def km_rankings(records, season_year, group):
    """Source-defined Sportsman/Sportswoman: sum actual known kilometres.

    Missing distance is not treated as a zero-distance completed race;
    partial tallies are flagged for review.
    """
    acc = defaultdict(lambda: {'races': 0, 'known_distance_races': 0, 'km': 0.0,
                               'athlete': '', 'group': '', 'member_id': ''})
    for r in qualifying_rows(records, season_year):
        if _group(r) != group:
            continue
        who = _identity(r)
        rec = acc[who]
        rec['athlete'], rec['group'], rec['member_id'] = _label(r), _group(r), who
        rec['races'] += 1
        km = _num(r.get('distance_km'))
        if km is not None and km > 0:
            rec['known_distance_races'] += 1
            rec['km'] += km
    ranked = sorted(acc.values(), key=lambda v: (-v['km'], v['athlete'].casefold()))
    return [dict(rank=i, athlete=r['athlete'], member_id=r['member_id'],
                 group=r['group'], kilometres=round(r['km'], 2),
                 eligible_races=r['races'],
                 missing_distances=r['races']-r['known_distance_races'])
            for i, r in enumerate(ranked, 1)]


def known_half_marathon_rankings(records, season_year):
    acc = defaultdict(lambda: {'member_id': '', 'athlete': '', 'group': '', 'count': 0})
    for r in qualifying_rows(records, season_year):
        km = _num(r.get('distance_km'))
        if _category(r) != '21.1 km' and not (km is not None and abs(km-21.1) <= .05):
            continue
        who = _identity(r)
        item=acc[who]
        item.update(member_id=who,athlete=_label(r),group=_group(r))
        item['count'] += 1
    ranked=sorted(acc.values(),key=lambda v:(-v['count'],v['athlete'].casefold()))
    return [dict(rank=i, **v) for i,v in enumerate(ranked,1)]


def comrades_medal_points(finish_seconds, gold_verified=False):
    """Return (PDF medal label, points), with strict 'sub' cutoffs.

    Official Gold status MUST be independently verified; it is not synonymous
    with being one of the two fastest members of this club.
    """
    if gold_verified:
        return ('GOLD - officially verified', 100)
    sec = _seconds(finish_seconds)
    if sec is None:
        return ('Time not recorded', None)
    if sec < 7*3600 + 30*60:
        return ('SILVER', 80)
    if sec < 9*3600:
        return ('BILL ROWAN', 50)
    if sec < 10*3600:
        return ('ROBERT MTSHALI', 30)
    if sec < 11*3600:
        return ('BRONZE', 20)
    if sec < 12*3600:
        return ('VIC CLAPMAN', 10)
    return ('Outside club-provided scoring bands', None)


def comrades_results(records, season_year, gold_result_ids=()):
    gold={str(v) for v in gold_result_ids}
    results=[]
    for r in qualifying_rows(records, season_year):
        if _category(r)!='Comrades' and 'comrades' not in str(r.get('race_name','')).casefold():
            continue
        medal,points=comrades_medal_points(r.get('finish_seconds'),str(r.get('id')) in gold)
        results.append(dict(result_id=str(r.get('id') or ''),
                            member_id=_identity(r), athlete=_label(r),group=_group(r),
                            race_name=r.get('race_name'), race_date=r.get('race_date'),
                            distance_km=_num(r.get('distance_km')),
                            finish_seconds=_seconds(r.get('finish_seconds')),
                            medal=medal, points=points,
                            official_gold=str(r.get('id')) in gold))
    return sorted(results,key=lambda r:(r['finish_seconds'] is None,r['finish_seconds'] or 0,r['athlete'].casefold()))


def comrades_first_by_group(comrades, group):
    times=[r for r in comrades if r['group']==group and r['finish_seconds'] is not None]
    if not times:
        return None
    winner=min(times,key=lambda r:r['finish_seconds'])
    return winner  # preliminary unless all race distances/course editions comparable


def event_results(records, season_year, event, group='All'):
    """Ranking for one CHOSEN club championship event, not unrelated races."""
    name=str(event.get('race_name') or '').strip().casefold()
    if not name:
        return []
    event_date=event.get('race_date')
    cat=event.get('race_category')
    matched=[]
    for r in qualifying_rows(records, season_year):
        if str(r.get('race_name') or '').strip().casefold()!=name:
            continue
        if cat and _category(r)!=cat:
            continue
        if group!='All' and _group(r)!=group:
            continue
        if event_date and str(r.get('race_date') or '')[:10]!=str(event_date)[:10]:
            continue
        secs=_seconds(r.get('finish_seconds'))
        if secs is None:
            continue
        matched.append({'athlete':_label(r),'member_id':_identity(r),'group':_group(r),
                        'race':r.get('race_name'),'seconds':secs,'date':r.get('race_date'),
                        'distance_km':_num(r.get('distance_km'))})
    matched.sort(key=lambda r:(r['seconds'],r['athlete'].casefold()))
    rank=0
    previous=None
    for idx,r in enumerate(matched,1):
        if r['seconds']!=previous:
            rank=idx
        r['rank']=rank
        previous=r['seconds']
    return matched


def fmt_time(seconds):
    sec=_seconds(seconds)
    if sec is None:
        return 'Not recorded'
    h,rest=divmod(sec,3600)
    m,s=divmod(rest,60)
    return f'{h:02d}:{m:02d}:{s:02d}'
