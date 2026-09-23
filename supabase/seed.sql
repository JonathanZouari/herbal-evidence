-- Seed for the dev project. Apply: supabase db query --linked -f supabase/seed.sql
-- Herbs = real reference data. Everything else is MOCK (emails @example.invalid, content {"mock": true}).
-- Mock users have NO password: they cannot log in (repo is public). Create real test logins via the Auth admin API.
-- Idempotent: skipped when the mock users already exist.

insert into public.herbs (name_he, name_en, latin_name, aliases, origin_regions, traditions, history_he) values
  ('ג׳ינג׳ר',   'Ginger',    'Zingiber officinale',         '{ginger,ג''ינג''ר,גינגר,זנגביל}',
   '{southeast_asia}', '{tcm,ayurveda}',
   'מקורו בדרום-מזרח אסיה, שם הוא מגודל אלפי שנים. הגיע לאגן הים התיכון דרך סחר התבלינים בעת העתיקה, ומשמש ברפואה הסינית ובאיורוודה.'),
  ('ג׳ינסנג',   'Ginseng',   'Panax ginseng',               '{ginseng,ג''ינסנג,גינסנג}',
   '{east_asia}', '{tcm,korean}',
   'גדל בר ביערות קוריאה, צפון-מזרח סין והמזרח הרחוק הרוסי. תופס מקום מרכזי ברפואה הסינית והקוריאנית המסורתית, וכיום מגודל בעיקר בחוות בקוריאה ובסין.'),
  ('כורכום',    'Turmeric',  'Curcuma longa',               '{turmeric,curcumin,כורכום,כורכומין}',
   '{south_asia,southeast_asia}', '{ayurveda,tcm}',
   'מקורו בתת-היבשת ההודית ובדרום-מזרח אסיה. משמש אלפי שנים במטבח ההודי, באיורוודה וברפואה הסינית, וגם כצבע טבעי.'),
  ('חילבה',     'Fenugreek', 'Trigonella foenum-graecum',   '{fenugreek,חילבה,תלתן}',
   '{middle_east,mediterranean}', '{middle_eastern_folk,unani,ayurveda}',
   'מקורה במזרח התיכון ובאגן הים התיכון, וזרעיה נמצאו באתרים ארכאולוגיים עתיקים באזור. משמשת ברפואה העממית של המזרח התיכון, ברפואת היונאני ובאיורוודה, וגם במטבח התימני.'),
  ('אסטרגלוס',  'Astragalus','Astragalus membranaceus',     '{astragalus,אסטרגלוס,קדד}',
   '{east_asia}', '{tcm}',
   'גדל בצפון סין, במונגוליה ובקוריאה. שורשו (הואנג צ׳י) הוא מהצמחים הנפוצים ביותר ברפואה הסינית המסורתית.'),
  ('קנאביס',    'Cannabis',  'Cannabis sativa',             '{cannabis,marijuana,קנאביס,קנביס}',
   '{central_asia,east_asia}', '{tcm,ayurveda}',
   'מקורו במרכז או במזרח אסיה (הדעות חלוקות). משמש אלפי שנים לסיבים, למזון ולמטרות רפואיות, ומוזכר בטקסטים של הרפואה הסינית והאיורוודה.')
-- origins are reference data too: re-running the seed refreshes them on existing herbs
on conflict (name_en) do update
  set origin_regions = excluded.origin_regions, traditions = excluded.traditions, history_he = excluded.history_he;

do $$
declare
  u_patient    uuid := '5eed0000-0000-4000-a000-000000000001';
  u_caregiver  uuid := '5eed0000-0000-4000-a000-000000000002';
  u_researcher uuid := '5eed0000-0000-4000-a000-000000000003';
  u_admin      uuid := '5eed0000-0000-4000-a000-000000000004';
  r uuid;
begin
  if exists (select 1 from auth.users where id = u_patient) then return; end if;

  insert into auth.users (id, email, aud, role) values
    (u_patient,    'mock-patient@example.invalid',    'authenticated', 'authenticated'),
    (u_caregiver,  'mock-caregiver@example.invalid',  'authenticated', 'authenticated'),
    (u_researcher, 'mock-researcher@example.invalid', 'authenticated', 'authenticated'),
    (u_admin,      'mock-admin@example.invalid',      'authenticated', 'authenticated');
  update public.profiles set display_name = 'MOCK מטופלת' where id = u_patient;
  update public.profiles set display_name = 'MOCK מטפל' where id = u_caregiver;
  update public.profiles set display_name = 'MOCK חוקרת', role = 'researcher' where id = u_researcher;
  update public.profiles set display_name = 'MOCK מנהל', role = 'admin' where id = u_admin;

  perform set_config('app.actor_id', u_admin::text, true);

  -- submitted
  insert into public.requests (user_id, herb_name_input, herb_id, preparation)
  values (u_patient, 'ג''ינג''ר', (select id from public.herbs where name_en = 'Ginger'), 'MOCK תה');

  -- researching, with a queued job
  insert into public.requests (user_id, herb_name_input, herb_id, cancer_type)
  values (u_patient, 'כורכום', (select id from public.herbs where name_en = 'Turmeric'), 'MOCK') returning id into r;
  update public.requests set status = 'researching', assigned_researcher_id = u_researcher where id = r;
  insert into public.research_jobs (kind, request_id, idempotency_key, payload)
  values ('research', r, 'mock:' || r || ':research:1', '{"mock": true}');

  -- awaiting clarification
  insert into public.requests (user_id, herb_name_input, herb_id)
  values (u_caregiver, 'גינסנג', (select id from public.herbs where name_en = 'Ginseng')) returning id into r;
  update public.requests set status = 'researching', assigned_researcher_id = u_researcher where id = r;
  update public.requests set status = 'draft_ready' where id = r;
  update public.requests set status = 'in_review' where id = r;
  update public.requests set status = 'awaiting_clarification' where id = r;
  insert into public.response_drafts (request_id, content, ai_provider) values (r, '{"mock": true}', 'MOCK');
  insert into public.clarifications (request_id, question, asked_by)
  values (r, 'MOCK: באיזו צורה נלקח הצמח (תה, כמוסה, אבקה)?', u_researcher);

  -- published, backed by an approved reusable review
  insert into public.evidence_reviews (herb_id, content, approved_by, approved_at)
  values ((select id from public.herbs where name_en = 'Fenugreek'), '{"mock": true}', u_researcher, now());
  insert into public.requests (user_id, herb_name_input, herb_id, treatment)
  values (u_caregiver, 'חילבה', (select id from public.herbs where name_en = 'Fenugreek'), 'MOCK כימותרפיה')
  returning id into r;
  update public.requests set status = 'researching', assigned_researcher_id = u_researcher where id = r;
  update public.requests set status = 'draft_ready' where id = r;
  update public.requests set status = 'in_review' where id = r;
  update public.requests set status = 'published' where id = r;
  insert into public.responses (request_id, evidence_review_id, body, approved_by)
  values (r, (select id from public.evidence_reviews limit 1), '{"mock": true}', u_researcher);

  -- unrecognised herb, withdrawn by the user
  insert into public.requests (user_id, herb_name_input) values (u_patient, 'MOCK צמח לא מזוהה') returning id into r;
  update public.requests set status = 'withdrawn' where id = r;
end $$;
