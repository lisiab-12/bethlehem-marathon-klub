# Bethlehem Marathon Klub — Version 2.2 (demo)

This is a **demonstration**, not a secure member-management system. Do not upload real member personal information or award decisions. Public GitHub repositories expose committed files.

## Updating the existing Streamlit Community Cloud app

On the `main` branch of your existing GitHub repository, upload/replace the following **at the top (root) level**:

1. `app.py` (replace Version 2.1)
2. `awards_engine.py` (**new file**, essential for V2.2)
3. `requirements.txt` (replace)

Keep your existing `demo.json`, `logo.png` and `.streamlit/config.toml` unchanged. You do not need to make another app or redeploy it manually; Streamlit Community Cloud normally deploys a new commit automatically. If the app fails to start, verify `awards_engine.py` is beside `app.py`.

## Testing V2.2

In the app sidebar switch to **Committee**, then select **Awards builder**. You can:

- Choose a preset award (Sportsman/Sportswoman of the Year, most kilometres, most races, fastest 10 km/half/marathon, biggest improver, consistency).
- Create or duplicate a rule, choose eligible categories, distances and race filters, and set minimum race counts.
- Change weighted criteria; weights must total 100%.
- View provisional athlete rankings and their scoring evidence.
- Export rankings or scoring rules; freeze a read-only **demo** snapshot of the provisional results.

The original imported 2026 records are unverified and mostly undated. Therefore, preview rankings must never be treated as official and the improvement and consistency awards will generally be unavailable until valid dated results are recorded. A preview toggle controls whether imported records are included at all.

**All changes are temporary session data**, including rules, committee scores, approvals and snapshots. Real secure logins, server-side authorisation, POPIA review, permanent database, audit trails and official award scoring rules are future work.

## Tests

`python -m pytest -q tests/test_awards_engine.py`

The calculation engine has isolated tests for weighted rankings, required data, comparable distances, tie ranks, imported-result restrictions and frozen preview snapshots.
