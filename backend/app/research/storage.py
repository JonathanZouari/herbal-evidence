"""Supabase Storage upload for the herb-images bucket (public reads; the service role is the only writer).
A non-2xx response raises FetchError already, same as any other SafeClient call - no separate error type."""

from app.research.http import SafeClient

BUCKET = "herb-images"


def upload_herb_image(client: SafeClient, supabase_url: str, service_key: str, herb_id: int,
                      content: bytes, content_type: str) -> str:
    """Uploads (upsert) to `<herb_id>.jpg` in the bucket and returns the stored object path."""
    path = f"{herb_id}.jpg"
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{BUCKET}/{path}"
    headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key,
              "Content-Type": content_type, "x-upsert": "true"}
    client.post_bytes(url, content, headers=headers)
    return path
