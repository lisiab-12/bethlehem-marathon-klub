# Bethlehem Marathon Klub — V2.3 secure pilot

Version 2.3 preserves the working V2.2 anonymised demonstration. It adds an **opt-in Supabase-backed mode** for testing secure logins, member-owned results, persistent submissions, committee review, filtering and a limited, private awards preview. The secure pilot is **not yet a completed production release**.

## 1. Upload to the existing GitHub repository

Upload these **four files** to the repository root, replacing `app.py` and `requirements.txt`, and adding `secure_app.py` and `supabase_setup.sql`:
- `app.py`
- `secure_app.py`
- `requirements.txt`
- `supabase_setup.sql`

Keep your existing `demo.json`, `awards_engine.py`, `logo.png` and `.streamlit/config.toml`. No new deployment is needed. **With no Streamlit secrets configured, the old V2.2 demo stays active.**

## 2. Prepare Supabase (before entering credentials)

1. Create a new Supabase project owned by the club, in a region approved by its committee. Check data hosting and POPIA obligations first.
2. Under **SQL Editor**, paste and run `supabase_setup.sql` once. Do not paste personal member data into GitHub.
3. Under **Authentication → Providers**, confirm email/password login is enabled. Disable public sign-ups for the pilot, if the project supports this setting; do not allow anonymous access to member data.
4. Under **Authentication → Users**, invite **two fictional/test users** (one member, one committee administrator). You need access to the invitation emails for password setup. Do not use real members yet.
5. Copy each test user's UUID from the Auth Users screen, then in **SQL Editor** insert profiles:

```sql
insert into public.profiles(id,display_name,member_group,role)
values
('REPLACE_WITH_MEMBER_UUID','Test Runner','MANS','member'),
('REPLACE_WITH_COMMITTEE_UUID','Test Administrator','ANDER','super_admin');
```

The first test runner can only see their own results; the second test committee account can review all results and preview awards. The app cannot grant itself committee privileges; role changes require an administrator working in the Supabase dashboard.

## 3. Add Streamlit secrets — never to GitHub

In **Streamlit Community Cloud → My apps → Bethlehem Marathon Klub → Settings → Secrets**, add:

```toml
BMK_SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
BMK_SUPABASE_KEY = "YOUR_SUPABASE_PUBLISHABLE_KEY"
```

Find the project URL and **publishable key** in Supabase Project Settings → API Keys / Connect. If your project has a legacy public `anon` key, it can also be used, with correct RLS. **NEVER use a service_role key or `sb_secret_...` key in this app.**

Saving the two secrets enables the live pilot, replacing the demo UI. Remove these two Streamlit secrets to return to the anonymised demo. Your deployed Streamlit URL does not change.

## 4. Pilot checks (must pass before entering real data)

- Log in as Member A, submit a race and confirm status is Pending after signing out and in again.
- Log in as Committee Admin, approve it, and verify it shows as Approved for Member A.
- Create Member B, and verify Member B does not see Member A's results.
- Using an authenticated direct Supabase REST request with Member B's access token, verify RLS denies access to Member A's records (not only a hidden sidebar).
- Confirm Members cannot update a status or change their roles; ordinary committee users must not see awards preview unless assigned awards_admin/super_admin.
- Confirm non-members, disabled profiles, and unsigned users cannot read results.
- Confirm no real member names, email addresses, keys or files appear anywhere in public GitHub history.

## What's still intentionally excluded

- Bulk import of the historical Excel data (needs matching of real names to Auth UUIDs and explicit permission)
- Supporting document upload and private storage bucket
- Permanent award-rule editing and versioned annual award decisions (the old demo Awards Studio still demonstrates these; secure pilot has read-only preview templates)
- Password reset within the Streamlit app, email invitations in the app, member profile editing, correction requests
- Formal security audit, POPIA process, privacy notices, backup and retention policies, penetration/security testing

## Notes

Do not put passwords or Supabase keys into the public GitHub repository or `demo.json`. The public repository can remain public *only if all contents and commit history are safe to publish*. Public Streamlit URL is fine for a login-gated pilot **provided RLS is verified first**. Do not assume the UI role selector of the V2.2 demo is an authentication system.
