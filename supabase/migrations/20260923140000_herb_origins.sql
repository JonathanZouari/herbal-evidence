-- Herb origins: where a herb comes from and which traditional systems use it.
-- Background information shown next to a herb the user already chose; never evidence, never a recommendation.
-- Fixed value sets (labels live in the frontend); adding a value = a new migration.
-- Data for the reference herbs lives in supabase/seed.sql.

alter table public.herbs
  add column origin_regions text[] not null default '{}'
    check (origin_regions <@ array['east_asia', 'southeast_asia', 'south_asia', 'central_asia', 'middle_east',
                                   'mediterranean', 'europe', 'africa', 'north_america', 'south_america',
                                   'oceania']::text[]),
  add column traditions text[] not null default '{}'
    check (traditions <@ array['tcm', 'korean', 'kampo', 'ayurveda', 'unani', 'middle_eastern_folk',
                               'european_herbalism', 'african_traditional', 'amazonian', 'andean',
                               'native_american']::text[]),
  add column history_he text check (char_length(history_he) <= 600);
