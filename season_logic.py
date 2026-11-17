"""Pure BMK season logic. No external connections, safe to unit-test."""


def rollover_candidates(memberships, from_year, to_year):
    """Carry forward only ACTIVE members, always as PENDING.

    An existing target-year entry is left untouched (including `left`/`inactive`).
    """
    target_ids = {str(m['athlete_id']) for m in memberships
                  if int(m['season_year']) == int(to_year)}
    out = []
    for m in memberships:
        if (int(m['season_year']) != int(from_year)
                or m.get('membership_status') != 'active'
                or str(m['athlete_id']) in target_ids):
            continue
        out.append({
            'season_year': int(to_year),
            'athlete_id': m['athlete_id'],
            'member_group': m.get('member_group') or 'ANDER',
            'member_number': m.get('member_number'),
            'membership_status': 'pending',
        })
    return out


def summarize_history(records, year):
    records = [r for r in records if int(r.get('season_year') or 0) == int(year)]
    return {
        'entries': len(records),
        'imported': sum(r.get('status') == 'Imported' for r in records),
        'approved': sum(r.get('status') == 'Approved' for r in records),
        'missing_dates': sum(not r.get('race_date') for r in records),
        'missing_distances': sum(r.get('distance_km') is None for r in records),
        'missing_times': sum(r.get('finish_seconds') is None for r in records),
    }


def can_approve_history(result, athlete):
    """Human review required; missing times/dates are not invented."""
    return bool(athlete and athlete.get('identity_status') == 'verified'
                and (result.get('race_name') or '').strip()
                and result.get('distance_km') is not None
                and float(result['distance_km']) > 0)
