-- Bootstrap admin/guest account tiers for known operator accounts.
-- Idempotent: safe to re-run. Matches docs/adversarial-review.md's
-- suggested bootstrap SQL. Uses email lookups (not hardcoded UUIDs) so
-- this is portable across environments where the same emails sign up.
--
-- sharath.sathish@outlook.com -> admin (app owner)
-- ashu20jan@gmail.com         -> guest (trusted tester, admin-level access
--                                without admin-panel/user-management rights)

insert into public.user_tiers (user_id, tier)
select u.id, 'admin'::public.account_tier
from auth.users u
where u.email = 'sharath.sathish@outlook.com'
on conflict (user_id) do update
  set tier = excluded.tier, updated_at = now();

insert into public.user_tiers (user_id, tier)
select u.id, 'guest'::public.account_tier
from auth.users u
where u.email = 'ashu20jan@gmail.com'
on conflict (user_id) do update
  set tier = excluded.tier, updated_at = now();

-- Verification query (run manually after applying):
-- select u.email, t.tier
-- from public.user_tiers t
-- join auth.users u on u.id = t.user_id
-- where u.email in ('sharath.sathish@outlook.com', 'ashu20jan@gmail.com');
