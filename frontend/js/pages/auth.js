// Login / signup / reset / set-new-password. Messages never reveal whether an email is registered.

import { arrivedWithAuthCode, safeNext, sb } from "../auth.js";
import { clear, h, param } from "../dom.js";
import { announce, main, renderHeader } from "../layout.js";

renderHeader(null);
const root = main();
const origin = location.origin;
const next = safeNext(param("next"));

function passwordField(id, label, autocomplete) {
  const isNew = autocomplete === "new-password";   // existing passwords are checked by the server only
  return h("div", { class: "field" },
    h("label", { for: id }, label),
    isNew ? h("span", { class: "hint", id: `${id}-hint` }, "לפחות 8 תווים") : null,
    h("input", { id, name: id, type: "password", required: true, minlength: isNew ? 8 : null, autocomplete,
      "aria-describedby": isNew ? `${id}-hint` : null }));
}

// Supabase reports a bad/expired email link in the query or the hash
const hashParams = new URLSearchParams(location.hash.slice(1));
const linkError = param("error_code") || hashParams.get("error_code") || param("error") || hashParams.get("error");
const LINK_HELP = "הקישור אינו תקף או שפג תוקפו. יש לפתוח את הקישור באותו דפדפן שבו נשלחה הבקשה, או לבקש קישור חדש.";

function emailField() {
  return h("div", { class: "field" },
    h("label", { for: "email" }, "דוא״ל"),
    h("input", { id: "email", name: "email", type: "email", required: true, autocomplete: "email", dir: "ltr" }));
}

function page(title, form, links = []) {
  const msg = h("div", { id: "form-msg", tabindex: "-1" });
  clear(root).append(h("div", { class: "card narrow" },
    h("h1", {}, title), msg, form,
    links.length ? h("p", { class: "row small" }, links) : null));
  return msg;
}

function say(msg, text, kind = "info") {
  clear(msg).append(h("div", { class: `callout ${kind}`, role: kind === "danger" ? "alert" : "status" }, h("p", {}, text)));
  msg.focus();
  announce(text);
}

function busy(form, on) {
  for (const el of form.querySelectorAll("button, input")) el.disabled = on;
}

const link = (mode, text) => h("a", { href: `/auth.html?mode=${mode}${param("next") ? `&next=${encodeURIComponent(next)}` : ""}` }, text);

function login() {
  const form = h("form", { novalidate: false }, emailField(), passwordField("password", "סיסמה", "current-password"),
    h("button", { class: "btn", type: "submit" }, "התחברות"));
  const msg = page("התחברות", form, [link("signup", "אין לך חשבון? הרשמה"), link("reset", "שכחת סיסמה?")]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    busy(form, true);
    const { error } = await sb.auth.signInWithPassword({ email: form.email.value.trim(), password: form.password.value });
    busy(form, false);
    if (error) {
      const unconfirmed = /confirm/i.test(error.message);
      say(msg, unconfirmed ? "יש לאשר את כתובת הדוא״ל דרך הקישור שנשלח אליך." : "הדוא״ל או הסיסמה אינם נכונים.", "danger");
      return;
    }
    location.assign(next);
  });
}

function signup() {
  const consent = h("input", { id: "consent", type: "checkbox", required: true });
  const form = h("form", {}, emailField(), passwordField("password", "סיסמה", "new-password"),
    h("div", { class: "field" }, h("label", { class: "check", for: "consent" }, consent,
      "הבנתי שהשירות מסכם מחקרים ואינו נותן המלצות טיפוליות.")),
    h("button", { class: "btn", type: "submit" }, "הרשמה"));
  const msg = page("הרשמה", form, [link("login", "כבר יש לך חשבון? התחברות")]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    busy(form, true);
    const { error } = await sb.auth.signUp({
      email: form.email.value.trim(), password: form.password.value,
      options: { emailRedirectTo: `${origin}/auth.html?mode=verified` },
    });
    busy(form, false);
    if (error && /password/i.test(error.message)) return say(msg, "הסיסמה חלשה מדי. יש לבחור סיסמה ארוכה יותר.", "danger");
    if (error && /rate|limit/i.test(error.message)) return say(msg, "נשלחו יותר מדי בקשות. יש לנסות שוב מאוחר יותר.", "danger");
    say(msg, "אם הכתובת תקינה, נשלח אליה קישור לאישור. יש לפתוח אותו כדי להשלים את ההרשמה.");
    form.reset();
  });
}

function reset() {
  const form = h("form", {}, emailField(), h("button", { class: "btn", type: "submit" }, "שליחת קישור לאיפוס"));
  const msg = page("איפוס סיסמה", form, [link("login", "חזרה להתחברות")]);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    busy(form, true);
    await sb.auth.resetPasswordForEmail(form.email.value.trim(), { redirectTo: `${origin}/auth.html?mode=update` });
    busy(form, false);
    say(msg, "אם קיים חשבון עם הכתובת הזו, נשלח אליו קישור לאיפוס הסיסמה.");
  });
}

async function update() {
  const { data } = await sb.auth.getSession();
  // only right after following a recovery link, never as a way to change a signed-in password silently
  if (linkError || !data.session || !arrivedWithAuthCode) {
    page("איפוס סיסמה", h("p", {}, LINK_HELP), [link("reset", "שליחת קישור חדש")]);
    return;
  }
  const form = h("form", {}, passwordField("password", "סיסמה חדשה", "new-password"),
    h("button", { class: "btn", type: "submit" }, "שמירת סיסמה"));
  const msg = page("בחירת סיסמה חדשה", form);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    busy(form, true);
    const { error } = await sb.auth.updateUser({ password: form.password.value });
    busy(form, false);
    if (error) return say(msg, "לא ניתן היה לשמור את הסיסמה. יש לנסות סיסמה אחרת.", "danger");
    say(msg, "הסיסמה עודכנה.");
    setTimeout(() => location.assign("/requests.html"), 1200);
  });
}

async function verified() {
  if (linkError) {
    page("אישור הדוא״ל", h("p", {}, LINK_HELP), [link("login", "התחברות"), link("signup", "הרשמה מחדש")]);
    return;
  }
  const { data } = await sb.auth.getSession();
  page("הדוא״ל אושר", h("p", {}, data.session ? "החשבון פעיל. אפשר להתחיל." : "החשבון אושר. אפשר להתחבר."),
    [data.session ? h("a", { class: "btn", href: "/new.html" }, "שליחת בקשה") : link("login", "התחברות")]);
}

const modes = { login, signup, reset, update, verified };
await (modes[param("mode")] || login)();
