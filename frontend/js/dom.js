// DOM helpers. Everything is built with createElement/textContent: untrusted text never becomes HTML.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "text") el.textContent = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key === "value") el.value = value;   // property: textarea/select ignore the attribute
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (key in el && typeof value !== "string") el[key] = value;
    else el.setAttribute(key, value === true ? "" : String(value));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/** Bidi-isolated text: user input, Latin names, PMIDs, DOIs inside RTL text. */
export function bdi(text) {
  return h("bdi", { text: text ?? "" });
}

export function clear(el) {
  el.replaceChildren();
  return el;
}

export function $(selector, root = document) {
  return root.querySelector(selector);
}

/** Only http(s) links may be rendered; anything else (javascript:, data:) becomes plain text. */
export function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.href : null;
  } catch {
    return null;
  }
}

export function extLink(url, label) {
  const href = safeUrl(url);
  if (!href) return bdi(label);
  return h("a", { href, target: "_blank", rel: "noopener noreferrer" }, bdi(label), h("span", { class: "sr-only", text: " (נפתח בחלון חדש)" }));
}

export function formatDate(iso) {
  if (!iso) return "";
  return new Intl.DateTimeFormat("he-IL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}

export function formatDay(iso) {
  if (!iso) return "";
  return new Intl.DateTimeFormat("he-IL", { dateStyle: "medium" }).format(new Date(iso));
}

export function param(name) {
  return new URLSearchParams(location.search).get(name);
}
