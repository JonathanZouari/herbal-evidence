// Supabase Auth (email/password, verification, reset). The session is the only client-side secret; the
// strict CSP (no inline script, self-only sources) and textContent-only rendering protect it.

const cfg = window.APP_CONFIG || {};

if (!window.supabase || !cfg.SUPABASE_URL || !cfg.SUPABASE_PUBLISHABLE_KEY) {
  throw new Error("runtime config missing: js/config.js must define APP_CONFIG");
}

// Captured synchronously, before supabase-js exchanges and strips the PKCE ?code= from the URL.
export const arrivedWithAuthCode = new URLSearchParams(location.search).has("code");

export const sb = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_PUBLISHABLE_KEY, {
  auth: { flowType: "pkce", persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
});

export async function getSession() {
  const { data } = await sb.auth.getSession();
  return data.session;
}

export async function getToken() {
  return (await getSession())?.access_token || null;
}

export function loginUrl() {
  const next = location.pathname + location.search;
  return `/auth.html?next=${encodeURIComponent(next)}`;
}

/** Only same-site relative paths are accepted as a post-login target (no open redirect). */
export function safeNext(value) {
  const fallback = "/requests.html";
  if (!value || !value.startsWith("/")) return fallback;
  try {
    // resolve like the browser will (tabs/newlines stripped, backslashes as slashes) and require our origin
    const u = new URL(value, location.origin);
    return u.origin === location.origin ? u.pathname + u.search + u.hash : fallback;
  } catch {
    return fallback;
  }
}

export async function signOut() {
  await sb.auth.signOut();
  location.assign("/");
}
