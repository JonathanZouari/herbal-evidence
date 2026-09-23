// Backend client: Bearer token from the Supabase session; errors become ApiError with the stable backend code.

import { getToken, loginUrl, sb } from "./auth.js";

const BASE = `${(window.APP_CONFIG?.API_BASE_URL || "").replace(/\/$/, "")}/api/v1`;

export class ApiError extends Error {
  constructor(status, code, message, fields = []) {
    super(message || code);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

/** redirectOn401=false: public pages just treat the visitor as signed out. */
export async function api(method, path, body, { redirectOn401 = true } = {}) {
  const token = await getToken();
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(BASE + path, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit", cache: "no-store", redirect: "error",
    });
  } catch {
    throw new ApiError(0, "network");
  }
  if (res.status === 401) {
    const code = (await res.json().catch(() => null))?.error?.code || "invalid_token";
    // drop the local session first, otherwise a session the backend rejects loops login -> page -> login
    await sb.auth.signOut({ scope: "local" });
    if (redirectOn401 && code !== "unknown_user") location.assign(loginUrl());
    throw new ApiError(401, code);
  }
  if (res.status === 204 || res.status === 202) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const e = data?.error || {};
    throw new ApiError(res.status, e.code || "internal_error", e.message, e.fields || []);
  }
  return data;
}

export const get = (path) => api("GET", path);
export const post = (path, body) => api("POST", path, body);
export const put = (path, body) => api("PUT", path, body);
export const patch = (path, body) => api("PATCH", path, body);
