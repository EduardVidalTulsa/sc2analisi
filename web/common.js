// SPDX-License-Identifier: GPL-3.0-or-later
// Utilitats compartides: format, colors i un gràfic de línies SVG amb tooltip.
"use strict";

const $ = (s, el = document) => el.querySelector(s);
// textos: window.T i window.LANG els posa genera.py a cada pàgina
const LANG = window.LANG || "ca", LOC = (window.LOCALE || "ca-ES") + "-u-nu-latn", ARREL = window.ARREL || "";
function t(k, v = {}) {
  let s = (window.T && window.T[k]) || k;
  for (const [a, b] of Object.entries(v)) s = s.split("{" + a + "}").join(b);
  return s;
}
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mmss = s => s == null ? "–" : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
const RACA = { Terran: "T", Protoss: "P", Zerg: "Z" };
const raca = r => `<span class="raca" title="${esc(r)}">${RACA[r] || "?"}</span>`;
const res = r => `<span class="res ${r}">${r === "V" ? t("victoria") : r === "D" ? t("derrota") : "?"}</span>`;
const data = ts => new Date(ts * 1000).toLocaleDateString(LOC, { day: "numeric", month: "short", year: "numeric" });
const dataHora = ts => new Date(ts * 1000).toLocaleString(LOC, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const num = n => n == null ? "–" : Math.round(n).toLocaleString(LOC);
const k = n => n >= 1000 ? (n / 1000).toLocaleString(LOC, { maximumFractionDigits: 1 }) + "k" : String(Math.round(n));
const TEMES = { Terran: "terran", Zerg: "zerg", Protoss: "protoss" };

function color(nom) { return getComputedStyle(document.documentElement).getPropertyValue("--" + nom).trim(); }

async function json(url) {
  const r = await fetch(ARREL + url);
  if (!r.ok) throw new Error(url + ": " + r.status);
  return r.json();
}

// Gràfic de línies.
//  opts: { series: [{nom, color, punts: [[x, y], ...], gruix}], xmax, ymax?, yfmt, xfmt, alt,
//          bandes?: [[x0, x1]], cursor?: x, onClic?: x => {}, punts?: bool }
// Retorna { posaCursor(x) } per sincronitzar-lo amb el mapa.
function grafic(el, opts) {
  el.classList.add("grafic");
  el.innerHTML = "";
  const tip = document.createElement("div"); tip.className = "tooltip"; el.appendChild(tip);
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg"); el.appendChild(svg);
  const alt = opts.alt || 160, mE = 40, mD = 8, mS = 8, mI = 22;
  const xfmt = opts.xfmt || mmss, yfmt = opts.yfmt || k;
  let W = 0, cursorX = opts.cursor ?? null, linCursor = null;

  const totsY = opts.series.flatMap(s => s.punts.map(p => p[1]));
  let ymax = opts.ymax ?? Math.max(1, ...totsY);
  // pas "rodó" per a l'eix Y
  const passos = [1, 2, 2.5, 5, 10];
  const brut = ymax / 4, mag = Math.pow(10, Math.floor(Math.log10(brut)));
  const pas = passos.find(p => p * mag >= brut) * mag;
  if (opts.ymax == null) ymax = Math.ceil(ymax / pas) * pas;
  const xmin = opts.xmin || 0, xmax = opts.xmax;

  function dibuixa() {
    W = el.clientWidth || 600;
    svg.setAttribute("viewBox", `0 0 ${W} ${alt}`);
    svg.setAttribute("height", alt);
    const sx = x => mE + (x - xmin) / (xmax - xmin) * (W - mE - mD);
    const sy = y => mS + (1 - y / ymax) * (alt - mS - mI);
    let h = "";
    for (const [a, b] of opts.bandes || [])
      h += `<rect x="${sx(a)}" y="${mS}" width="${Math.max(2, sx(b) - sx(a))}" height="${alt - mS - mI}" fill="var(--text3)" opacity=".13"/>`;
    h += `<g class="reixa">`;
    for (let y = 0; y <= ymax + 1e-9; y += pas) h += `<line x1="${mE}" x2="${W - mD}" y1="${sy(y)}" y2="${sy(y)}" ${y ? 'stroke-dasharray="2 4"' : ""}/>`;
    h += `</g><g class="eix">`;
    for (let y = 0; y <= ymax + 1e-9; y += pas) h += `<text x="${mE - 6}" y="${sy(y) + 4}" text-anchor="end">${yfmt(y)}</text>`;
    const xpas = opts.xpas || ((xmax - xmin) > 1800 ? 300 : (xmax - xmin) > 600 ? 120 : 60);
    for (let x = Math.ceil(xmin / xpas) * xpas; x <= xmax; x += xpas) h += `<text x="${sx(x)}" y="${alt - 5}" text-anchor="middle">${xfmt(x)}</text>`;
    h += `</g>`;
    for (const s of opts.series) {
      if (!s.punts.length) continue;
      const d = s.punts.map((p, i) => `${i ? "L" : "M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
      h += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.gruix || 2}" stroke-linejoin="round" stroke-linecap="round" ${s.puntejat ? 'stroke-dasharray="4 4"' : ""}/>`;
      if (opts.punts) for (const p of s.punts)
        h += `<circle cx="${sx(p[0])}" cy="${sy(p[1])}" r="4" fill="${p[2] === false ? "var(--sup)" : s.color}" stroke="${s.color}" stroke-width="2"/>`;
    }
    h += `<line class="cursor" y1="${mS}" y2="${alt - mI}" visibility="hidden"/>`;
    h += `<rect x="${mE}" y="0" width="${W - mE - mD}" height="${alt}" fill="transparent" class="hit"/>`;
    svg.innerHTML = h;
    linCursor = svg.querySelector(".cursor");
    posaCursor(cursorX);
    const hit = svg.querySelector(".hit");
    const xDe = ev => {
      const r = svg.getBoundingClientRect();
      const px = (ev.clientX - r.left) * W / r.width;
      return Math.max(xmin, Math.min(xmax, xmin + (px - mE) / (W - mE - mD) * (xmax - xmin)));
    };
    hit.addEventListener("pointermove", ev => {
      const x = xDe(ev);
      let html = `<b>${opts.xtitol ? opts.xtitol(x) : xfmt(x)}</b>`;
      for (const s of opts.series) {
        if (!s.punts.length) continue;
        let m = s.punts[0];
        for (const p of s.punts) if (Math.abs(p[0] - x) < Math.abs(m[0] - x)) m = p;
        html += `<br><span class="punt" style="background:${s.color}"></span>${esc(s.nom)}: <b>${yfmt(m[1])}</b>`;
      }
      tip.innerHTML = html; tip.style.display = "block";
      const r = el.getBoundingClientRect();
      let lx = ev.clientX - r.left + 14;
      if (lx + tip.offsetWidth > r.width) lx = ev.clientX - r.left - tip.offsetWidth - 14;
      tip.style.left = lx + "px"; tip.style.top = Math.max(0, ev.clientY - r.top - 20) + "px";
      if (!opts.onClic) return;
      linCursor.setAttribute("x1", sx(x)); linCursor.setAttribute("x2", sx(x)); linCursor.setAttribute("visibility", "visible");
    });
    hit.addEventListener("pointerleave", () => { tip.style.display = "none"; posaCursor(cursorX); });
    if (opts.onClic) { hit.style.cursor = "pointer"; hit.addEventListener("click", ev => opts.onClic(xDe(ev))); }
  }
  function posaCursor(x) {
    cursorX = x;
    if (!linCursor) return;
    if (x == null) { linCursor.setAttribute("visibility", "hidden"); return; }
    const px = mE + (x - xmin) / (xmax - xmin) * (W - mE - mD);
    linCursor.setAttribute("x1", px); linCursor.setAttribute("x2", px); linCursor.setAttribute("visibility", "visible");
  }
  dibuixa();
  let amplada = el.clientWidth;
  new ResizeObserver(() => { if (el.clientWidth !== amplada) { amplada = el.clientWidth; dibuixa(); } }).observe(el);
  return { posaCursor };
}

function llegenda(series) {
  return `<div class="llegenda">${series.map(s => `<span><i style="background:${s.color}"></i>${esc(s.nom)}</span>`).join("")}</div>`;
}

// ---- sessió (Battle.net): barra de dalt. Torna l'usuari o null.
const SESSIO = (async () => {
  let u = null;
  try {
    const r = await fetch(ARREL + "api/me", { credentials: "same-origin" });
    if (r.ok) { const d = await r.json(); if (d.battletag) u = d; }
  } catch {}
  const el = document.getElementById("sessio");
  if (el) {
    if (u) {
      const meu = u.toons && u.toons[0];
      el.innerHTML = `<span class="apagat">${esc(t("has_entrat", { nom: u.battletag }))}</span>`
        + (meu ? ` · <a href="./?player=${encodeURIComponent(meu.toon)}">${t("meves")}</a>` : "")
        + ` · <a href="./?all">${t("totes_servidor")}</a>`
        + ` · <button class="enllac" type="button" id="surt">${t("surt")}</button>`;
      document.getElementById("surt").onclick = async () => {
        await fetch(ARREL + "api/logout", { method: "POST", credentials: "same-origin" });
        location.reload();
      };
    } else {
      const torna = encodeURIComponent(location.pathname + location.search);
      el.innerHTML = `<a class="boto boto-bnet" href="${ARREL}api/login?return=${torna}">${t("entra")}</a>`;
    }
    if (new URLSearchParams(location.search).get("login") === "error")
      el.insertAdjacentHTML("beforeend", ` <span class="envia-estat">${t("login_error")}</span>`);
  }
  return u;
})();

// ---- termes amb explicació: en passar el ratolí, enfocar-los o tocar-los amb el dit surt una bombolla
function terme(clau, text) {
  return `<button type="button" class="terme" data-terme="${clau}" aria-describedby="bombolla">${esc(text ?? clau.toUpperCase())}</button>`;
}
(() => {
  const b = document.createElement("div");
  b.id = "bombolla"; b.className = "bombolla"; b.setAttribute("role", "tooltip"); b.hidden = true;
  document.body.appendChild(b);
  let actual = null, fixat = false;
  const mostra = el => {
    actual = el;
    b.textContent = t("def_" + el.dataset.terme);
    b.hidden = false;
    const r = el.getBoundingClientRect(), amp = Math.min(320, innerWidth - 24);
    b.style.maxWidth = amp + "px";
    let x = r.left + r.width / 2 - b.offsetWidth / 2;
    x = Math.max(12, Math.min(x, innerWidth - b.offsetWidth - 12));
    let y = r.bottom + 8;
    if (y + b.offsetHeight > innerHeight - 8) y = r.top - b.offsetHeight - 8;
    b.style.left = x + scrollX + "px"; b.style.top = y + scrollY + "px";
  };
  const amaga = () => { b.hidden = true; actual = null; fixat = false; };
  document.addEventListener("mouseover", ev => { const el = ev.target.closest(".terme"); if (el && !fixat) mostra(el); });
  document.addEventListener("mouseout", ev => { if (!fixat && ev.target.closest(".terme")) amaga(); });
  document.addEventListener("focusin", ev => { const el = ev.target.closest(".terme"); if (el) mostra(el); });
  document.addEventListener("focusout", ev => { if (!fixat && ev.target.closest(".terme")) amaga(); });
  // tocar (mòbil) o clicar: fixa la bombolla fins que es toqui fora
  document.addEventListener("click", ev => {
    const el = ev.target.closest(".terme");
    if (el) { ev.preventDefault(); ev.stopPropagation(); if (fixat && actual === el) amaga(); else { mostra(el); fixat = true; } return; }
    if (fixat) amaga();
  }, true);
  document.addEventListener("keydown", ev => { if (ev.key === "Escape") amaga(); });
  addEventListener("scroll", () => { if (!b.hidden && actual) mostra(actual); }, { passive: true });
})();

// ---- avís de galetes (només n'hi ha de tècniques: s'informa, no cal consentiment)
(() => {
  let vist = false;
  try { vist = localStorage.getItem("sc2-galetes") === "1"; } catch {}
  if (vist) return;
  const d = document.createElement("div");
  d.className = "avis-galetes"; d.setAttribute("role", "region"); d.setAttribute("aria-label", "Cookies");
  d.innerHTML = `<p>🍪 ${esc(t("galetes"))}</p><button class="boto" type="button">${esc(t("entesos"))}</button>`;
  d.querySelector("button").onclick = () => { try { localStorage.setItem("sc2-galetes", "1"); } catch {} d.remove(); };
  document.body.appendChild(d);
})();

// ---- detector de bloquejador d'anuncis: un element esquer amb classes d'anunci i el fitxer ads.js
addEventListener("load", () => {
  const esquer = document.createElement("div");
  esquer.className = "adsbox ad-banner ad-placeholder pub_300x250 textads banner-ads";
  esquer.style.cssText = "position:absolute;left:-9999px;top:-9999px;width:300px;height:250px;";
  esquer.innerHTML = "&nbsp;";
  document.body.appendChild(esquer);
  setTimeout(() => {
    const amagat = !esquer.offsetParent || esquer.offsetHeight === 0 || getComputedStyle(esquer).display === "none" || getComputedStyle(esquer).visibility === "hidden";
    const bloquejat = amagat || !window.sc2SenseBloquejador;
    esquer.remove();
    const el = document.getElementById("adblock");
    if (el) el.textContent = t(bloquejat ? "adblock_si" : "adblock_no");
  }, 300);
});
