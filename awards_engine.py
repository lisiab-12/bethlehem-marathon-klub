"""BMK demo award calculation engine.

No user authentication, persistence, official competition rules, or age-grading.
This module is pure Python/pandas so its calculations can be tested separately.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import math
import pandas as pd

METRICS = ("performance", "participation", "distance", "improvement", "consistency", "contribution")
SCORE_LABELS = {
    "performance": "Comparable race performance",
    "participation": "Race participation",
    "distance": "Race kilometres",
    "improvement": "Measured improvement",
    "consistency": "Months with races",
    "contribution": "Committee sportsmanship score",
}
METRIC_HELP = {
    "performance": "For each standard road distance (10, 21.1, 42.2 km), each athlete's fastest time is compared with the fastest time among eligible club athletes at that distance. At least two athletes are needed. The best three comparable distance scores are averaged; this is NOT an official age grade.",
    "participation": "Completed race finishes divided by the highest eligible athlete's race count, multiplied by 100.",
    "distance": "Completed race kilometres divided by the highest eligible athlete's kilometres, multiplied by 100. Unknown distances do not contribute.",
    "improvement": "First-to-last percentage improvement in one comparable standard distance with at least three dated finishes. The best positive improvement is scaled against the highest observed improvement; undated imports cannot qualify.",
    "consistency": "Number of different calendar months containing dated completed races, relative to the highest eligible athlete's number of active months.",
    "contribution": "A manually entered committee score from 0 to 100. No score is inferred for missing entries.",
}


def default_awards(season: int = 2026) -> list[dict]:
    items = [
        ("Sportsman of the Year", "Sportman van die Jaar", "MANS", "weighted", None),
        ("Sportswoman of the Year", "Sportvrou van die Jaar", "VROUE", "weighted", None),
        ("Most Race Kilometres", "Meeste Wedloopkilometers", "All", "most_km", None),
        ("Most Completed Races", "Meeste Voltooide Wedlope", "All", "most_races", None),
        ("Fastest 10 km", "Vinnigste 10 km", "All", "fastest", 10.0),
        ("Fastest Half Marathon", "Vinnigste Halfmarathon", "All", "fastest", 21.1),
        ("Fastest Marathon", "Vinnigste Marathon", "All", "fastest", 42.2),
        ("Biggest Improver", "Grootste Vordering", "All", "improvement", None),
        ("Most Consistent Runner", "Mees Konsekwente Atleet", "All", "consistency", None),
    ]
    out = []
    for i, (en, af, group, mode, target) in enumerate(items, 1):
        out.append({
            "id": f"preset-{i}", "name_en": en, "name_af": af,
            "season": season, "group": group, "age_category": "All",
            "discipline": "All", "race_filter": "All", "mode": mode,
            "target_distance": target, "min_races": 1, "archived": False,
            # Improvement and sportsmanship start at zero because the imported
            # records have no dates and no committee scores.
            "weights": {"performance": 60, "participation": 25, "distance": 15,
                        "improvement": 0, "consistency": 0, "contribution": 0},
        })
    return out


def new_award(source: dict | None = None) -> dict:
    d = deepcopy(source or default_awards()[0])
    d["id"] = str(uuid4())
    d["name_en"] = "Custom award" if not source else f"{d['name_en']} (copy)"
    d["name_af"] = "Pasgemaakte prys" if not source else f"{d['name_af']} (kopie)"
    d["archived"] = False
    return d


def _completed(df: pd.DataFrame) -> pd.DataFrame:
    """Only rows with valid finishing times are counted as completed races."""
    if df.empty:
        return df.copy()
    sec = pd.to_numeric(df["seconds"], errors="coerce")
    return df[sec.notna() & (sec > 0)].copy()


def _discipline(df: pd.DataFrame) -> pd.Series:
    # The historical spreadsheet does not have a reliable discipline column.
    # 'Trail' is known; other results are left as *unclassified*, not assumed road.
    return pd.Series(
        ["Trail" if str(c).strip().lower() == "trail" else "Not tagged trail"
         for c in df["category"]], index=df.index,
    )


def select_records(df: pd.DataFrame, rule: dict, include_imported: bool) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    approved = ["Approved"] + (["Imported"] if include_imported else [])
    q = df[df["status"].isin(approved) & (df["year"] == int(rule["season"]))].copy()
    if rule.get("group", "All") != "All":
        q = q[q["group"] == rule["group"]]
    if rule.get("age_category", "All") != "All":
        q = q[q["age_category"] == rule["age_category"]]
    disc = rule.get("discipline", "All")
    if disc != "All" and not q.empty:
        q = q[_discipline(q) == disc]
    race = rule.get("race_filter", "All")
    if race != "All":
        q = q[q["race"] == race]
    if include_imported and (q["status"] == "Imported").any():
        warnings.append("Imported results are unverified and included for preview only.")
    if not q.empty:
        dupe = q.duplicated(subset=["member", "race", "distance", "time", "year"], keep=False)
        if dupe.any():
            warnings.append(f"{int(dupe.sum())} matching records may be duplicates; review before using official rankings.")
    q = _completed(q)
    return q, warnings


def _proportional(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0).clip(lower=0)
    top = numeric.max() if len(numeric) else 0
    return numeric / top * 100 if pd.notna(top) and top > 0 else pd.Series(0., index=values.index)


def _performance_by_member(q: pd.DataFrame) -> dict:
    # Include only standard road distance categories, and compare runners at
    # the *same actual distance*. Unknown trail classification is excluded by
    # the explicit 'trail' tag. This is a provisional club-relative metric.
    comp = q[(q["distance"].notna()) & (q["seconds"].notna()) &
             (q["category"].astype(str).str.lower() != "trail") &
             q["distance"].round(1).isin([10.0, 21.1, 42.2])].copy()
    if comp.empty:
        return {}
    comp["dist_key"] = comp["distance"].round(1)
    best = comp.groupby(["dist_key", "member"], as_index=False)["seconds"].min()
    out: dict[str, list[tuple[float, float]]] = {}
    for distance, field in best.groupby("dist_key"):
        if field["member"].nunique() < 2:
            continue
        leader = float(field["seconds"].min())
        for _, r in field.iterrows():
            out.setdefault(r["member"], []).append((float(100 * leader / r["seconds"]), float(distance)))
    return {m: (round(sum(x[0] for x in sorted(items, reverse=True)[:3]) / min(3, len(items)), 5),
                ", ".join(f"{dist:g} km" for _, dist in sorted(items, reverse=True)[:3]))
            for m, items in out.items()}


def _improvement_by_member(q: pd.DataFrame) -> dict:
    valid = q[(q["seconds"].notna()) & q["distance"].round(1).isin([10.0, 21.1, 42.2]) &
              (q["category"].astype(str).str.lower() != "trail")].copy()
    if valid.empty:
        return {}
    valid["race_date"] = pd.to_datetime(valid["date"], errors="coerce")
    valid = valid.dropna(subset=["race_date"])
    if valid.empty:
        return {}
    valid["dist_key"] = valid["distance"].round(1)
    out: dict[str, tuple[float, str]] = {}
    for (m, distance), records in valid.groupby(["member", "dist_key"]):
        records = records.sort_values("race_date")
        if len(records) < 3 or records["race_date"].nunique() < 2:
            continue
        start, finish = records.iloc[0], records.iloc[-1]
        pct = 100 * (start["seconds"] - finish["seconds"]) / start["seconds"]
        if m not in out or pct > out[m][0]:
            out[m] = (round(float(pct), 4), f"{distance:g} km, {len(records)} dated finishes")
    return out


def compute_award(df: pd.DataFrame, rule: dict, include_imported: bool,
                  manual_scores: dict | None = None) -> dict:
    """Return deterministic, explainable provisional award rankings.

    If a weighted criterion has no supporting data in the filtered population,
    rankings are intentionally blocked rather than silently redistributing weights.
    """
    q, warnings = select_records(df, rule, include_imported)
    if q.empty:
        return {"rankings": pd.DataFrame(), "warnings": warnings + ["No completed, eligible results found."],
                "blocked": True, "reason": "No completed, eligible results found.", "source_count": 0}

    stats = q.groupby("member").agg(
        races=("race", "size"),
        km=("distance", "sum"),
        athlete=("athlete", "first"),
        group=("group", "first"),
    ).reset_index()
    stats = stats[stats["races"] >= max(1, int(rule.get("min_races", 1)))].copy()
    if stats.empty:
        return {"rankings": pd.DataFrame(), "warnings": warnings,
                "blocked": True, "reason": "No athlete meets the minimum number of completed races.",
                "source_count": len(q)}

    mode = rule.get("mode", "weighted")
    manual_scores = manual_scores or {}
    # Metric raw values and evidence only for qualifying athletes
    perf = _performance_by_member(q)
    improve = _improvement_by_member(q)
    months = q.assign(date_parsed=pd.to_datetime(q["date"], errors="coerce"))
    months = months.dropna(subset=["date_parsed"]).assign(month=lambda x: x["date_parsed"].dt.month)
    month_count = months.groupby("member")["month"].nunique().to_dict() if len(months) else {}
    stats["performance_raw"] = stats["member"].map({m: s for m, (s, _) in perf.items()})
    stats["performance_evidence"] = stats["member"].map({m: e for m, (_, e) in perf.items()})
    stats["improvement_pct"] = stats["member"].map({m: pct for m, (pct, _) in improve.items()})
    stats["improvement_evidence"] = stats["member"].map({m: e for m, (_, e) in improve.items()})
    stats["active_months"] = stats["member"].map(month_count)
    stats["manual_score"] = stats["member"].map(manual_scores)
    stats["km"] = stats["km"].round(1)

    if mode == "fastest":
        dist = rule.get("target_distance")
        if dist is None or not math.isfinite(float(dist)) or float(dist) <= 0:
            return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                    "reason": "Choose a valid exact distance for the fastest-time award.", "source_count": len(q)}
        dist_q = q[q["distance"].notna() & (q["distance"].sub(float(dist)).abs() <= 0.051)]
        if rule.get("discipline", "All") == "All":
            # No road vs trail comparison in a fastest-time award by default.
            dist_q = dist_q[dist_q["category"].astype(str).str.lower() != "trail"]
        if dist_q.empty:
            return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                    "reason": "No comparable timed finishes at this exact distance.", "source_count": len(q)}
        best = dist_q.sort_values(["seconds", "member"]).drop_duplicates("member")
        stats = stats.merge(best[["member", "seconds", "time", "race"]], how="inner", on="member")
        stats = stats.sort_values(["seconds", "athlete"]).reset_index(drop=True)
        if stats.empty:
            return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                    "reason": "No eligible athlete has a valid time at that distance.", "source_count": len(q)}
        stats["score"] = (100 * stats["seconds"].min() / stats["seconds"]).round(2)
    elif mode in ("most_km", "most_races", "consistency", "improvement", "manual"):
        val = {"most_km": "km", "most_races": "races", "consistency": "active_months",
               "improvement": "improvement_pct", "manual": "manual_score"}[mode]
        if not stats[val].notna().any():
            return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                    "reason": f"No supporting data for {val.replace('_',' ')}. Add valid dated results or committee scores first.",
                    "source_count": len(q)}
        if mode == "improvement":
            stats = stats[stats[val] > 0].copy()
            if stats.empty:
                return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                        "reason": "No positive improvement supported by three comparable dated finishes.", "source_count": len(q)}
        else:
            stats = stats[stats[val].notna()].copy()
        stats["score"] = _proportional(stats[val]).round(2)
        stats = stats.sort_values([val, "athlete"], ascending=[False, True]).reset_index(drop=True)
    elif mode == "weighted":
        weights = rule.get("weights", {})
        if any(not isinstance(weights.get(k, 0), (int, float)) or weights.get(k, 0) < 0 for k in METRICS):
            return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                    "reason": "Weights must be non-negative numbers.", "source_count": len(q)}
        if abs(sum(weights.get(k, 0) for k in METRICS) - 100) > 0.001:
            return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                    "reason": "All award weights must total 100%.", "source_count": len(q)}
        metric_raw = {
            "performance": "performance_raw", "participation": "races", "distance": "km",
            "improvement": "improvement_pct", "consistency": "active_months",
            "contribution": "manual_score",
        }
        for key in METRICS:
            raw = metric_raw[key]
            w = weights.get(key, 0)
            if w and not stats[raw].notna().any():
                return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                        "reason": f"Cannot calculate: '{SCORE_LABELS[key]}' has no qualifying data. Set its weight to 0 or supply supporting results.",
                        "source_count": len(q)}
            if key == "performance":
                scores = stats[raw].fillna(0).clip(0, 100)
            elif key == "contribution":
                scores = stats[raw].fillna(0).clip(0, 100)
            else:
                scores = _proportional(stats[raw])
            stats[f"{key}_score"] = scores.round(2)
        stats["score"] = sum(weights.get(k, 0) * stats[f"{k}_score"] for k in METRICS) / 100
        stats["score"] = stats["score"].round(2)
        stats = stats.sort_values(["score", "athlete"], ascending=[False, True]).reset_index(drop=True)
        active = [k for k in METRICS if weights.get(k, 0) > 0]
        stats["missing_metric_evidence"] = stats.apply(
            lambda r: ", ".join(SCORE_LABELS[k] for k in active if pd.isna(r[metric_raw[k]])) or "—", axis=1)
        missing = int(stats["missing_metric_evidence"].ne("—").sum())
        if missing:
            warnings.append(f"{missing} candidate(s) lack evidence for at least one weighted criterion; those missing scores are 0, not fabricated.")
    else:
        return {"rankings": pd.DataFrame(), "warnings": warnings, "blocked": True,
                "reason": f"Unsupported award mode: {mode}", "source_count": len(q)}

    # Award ties share a rank. Fastest times are ranked ascending; every other
    # award is ranked on its descending calculated/underlying score.
    order_values = stats["seconds"] if mode == "fastest" else stats["score"]
    stats.insert(0, "rank", order_values.rank(method="min", ascending=(mode == "fastest")).astype(int))
    return {"rankings": stats, "warnings": warnings,
            "blocked": False, "reason": "", "source_count": len(q)}


def freeze_snapshot(rule: dict, rankings: pd.DataFrame, source_count: int, include_imported: bool) -> dict:
    """Demo-only in-session frozen preview, *not* an official/secure award record."""
    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule": deepcopy(rule), "preview_imported": include_imported,
        "source_count": source_count,
        "rankings": rankings.where(pd.notna(rankings), None).to_dict(orient="records"),
        "demo_only": True,
    }
