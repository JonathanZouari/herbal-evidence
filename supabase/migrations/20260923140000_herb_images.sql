-- Herb reference photo, fetched lazily (once per herb) by the research worker from Wikimedia and cached
-- in our own storage. `herbs` is already fully public-read, so no RLS change is needed for the new columns.

alter table public.herbs
  add column image_path        text,             -- object path in the herb-images bucket; null until fetched
  add column image_attribution text,             -- credit line (artist / license) for display next to the photo
  add column image_source_url  text,             -- the Wikipedia page the image came from
  add column image_status      text not null default 'pending'
                                check (image_status in ('pending', 'found', 'not_found')),
  add column image_fetched_at  timestamptz;

-- Public bucket: images are non-sensitive, and serving them via the public object URL avoids a backend
-- proxy route. No storage.objects policy needed for reads; writes go through the service role only.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('herb-images', 'herb-images', true, 5242880, array['image/jpeg', 'image/png', 'image/webp']);
