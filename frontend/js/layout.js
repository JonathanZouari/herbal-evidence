// Page shell: header + role-based nav, live region, error display, auth/role gate.

import { api, get } from "./api.js";
import { getSession, loginUrl, signOut } from "./auth.js";
import { $, clear, h } from "./dom.js";
import { BRAND, errorMessage } from "./i18n.js";

const NAV = {
  user: [["/requests.html", "הבקשות שלי"], ["/new.html", "בקשה חדשה"]],
  researcher: [["/staff.html", "תור בקשות"], ["/reviews.html", "מאגר סקירות"], ["/requests.html", "הבקשות שלי"]],
  admin: [["/staff.html", "כל הבקשות"], ["/reviews.html", "מאגר סקירות"], ["/admin.html", "ניהול משתמשים"]],
};

export function renderHeader(me) {
  const header = $("#site-header");
  const links = me ? NAV[me.role] || NAV.user : [["/auth.html", "התחברות"]];
  const current = location.pathname.endsWith(".html") ? location.pathname : `${location.pathname}.html`;
  const nav = h("nav", { class: "site-nav", "aria-label": "ניווט ראשי" },
    links.map(([href, label]) => h("a", { href, "aria-current": current === href ? "page" : null }, label)),
    me ? h("button", { type: "button", onclick: signOut }, "יציאה") : null);
  clear(header).append(h("div", { class: "inner" },
    h("a", { class: "brand", href: me ? (NAV[me.role] || NAV.user)[0][0] : "/" },
      h("span", { class: "brand-mark", "aria-hidden": "true" }), "🌿", BRAND),
    nav));
}

/** Screen-reader announcement (polite). */
export function announce(message) {
  const live = $("#live");
  if (!live) return;
  live.textContent = "";
  setTimeout(() => { live.textContent = message; }, 50);
}

let toastTimer;
export function toast(message) {
  let el = $("#toast");
  if (!el) {
    el = h("div", { id: "toast", class: "toast", role: "status" });
    document.body.append(el);
  }
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 5000);   // role=status announces it once
}

/** Error box that takes focus, so keyboard and screen-reader users land on it. */
export function showError(container, err, extra) {
  const box = h("div", { class: "error-summary", role: "alert", tabindex: "-1" },
    h("p", { text: errorMessage(err?.code || "internal_error") }), extra || null);
  clear(container).append(box);
  box.focus();
  return box;
}

export function main() {
  return $("#main");
}

/** After a re-render, put focus on the page heading so keyboard users aren't dropped on <body>. */
export function focusHeading() {
  const h1 = $("#main h1");
  if (!h1) return;
  h1.setAttribute("tabindex", "-1");
  h1.focus({ preventScroll: true });
}

export function loading(container, text = "טוען…") {
  clear(container).append(h("p", { class: "muted", role: "status" }, text));
}

/** Require a session (and optionally a role). Returns /me, or redirects. */
export async function requireAuth(roles) {
  const session = await getSession();
  if (!session) {
    location.assign(loginUrl());
    return new Promise(() => {});
  }
  let me;
  try {
    me = await get("/me");
  } catch (e) {
    renderHeader(null);
    showError(main(), e);
    return new Promise(() => {});
  }
  renderHeader(me);
  if (roles && !roles.includes(me.role)) {
    clear(main()).append(h("div", { class: "callout warning", role: "alert" },
      h("p", { text: errorMessage("forbidden") })));
    return new Promise(() => {});
  }
  return me;
}

/** Header for public pages: shows the signed-in nav when a session exists. */
export async function publicShell() {
  const session = await getSession();
  let me = null;
  if (session) {
    try { me = await api("GET", "/me", undefined, { redirectOn401: false }); } catch { me = null; }
  }
  renderHeader(me);
  return me;
}

export function confirmDialog({ title, body, confirmLabel, danger = false }) {
  return new Promise((resolve) => {
    const dialog = h("dialog", { "aria-labelledby": "dlg-title" },
      h("h2", { id: "dlg-title", text: title }),
      h("p", { text: body }),
      h("div", { class: "row" },
        h("button", { type: "button", class: danger ? "btn danger" : "btn", onclick: () => close(true) }, confirmLabel),
        h("button", { type: "button", class: "btn secondary", onclick: () => close(false) }, "ביטול")));
    function close(result) {
      dialog.close();
      dialog.remove();
      resolve(result);
    }
    dialog.addEventListener("cancel", () => close(false));
    document.body.append(dialog);
    dialog.showModal();
  });
}
