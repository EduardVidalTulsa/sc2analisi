// SPDX-License-Identifier: GPL-3.0-or-later
"use strict";

// ---- enviar un replay
(() => {
  const zona = $("#zona"), estat = $("#estat"), fitxer = $("#fitxer");
  async function envia(f) {
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) { estat.textContent = t("err_mida"); return; }
    zona.classList.add("ocupat");
    estat.textContent = t("envia_puja");
    // passat un moment la pujada ja ha acabat i el que queda és l'anàlisi
    const rellotge = setTimeout(() => { estat.textContent = t("envia_analitza"); }, 1200);
    try {
      const r = await fetch(ARREL + "api/upload", { method: "POST", body: f, headers: { "Content-Type": "application/octet-stream" } });
      const d = await r.json().catch(() => ({}));
      // una partida de Marine Arena: la seva fitxa és a ma.lestudi.com
      if (r.ok && d.id && d.web === "ma") { location.href = `https://ma.lestudi.com/game.html?id=${d.id}&lang=${LANG}`; return; }
      if (r.ok && d.id) { location.href = "game.html?id=" + d.id; return; }
      estat.textContent = t(r.status === 429 ? "err_429" : r.status === 413 ? "err_mida" : "err_" + (d.error || "analisi"));
    } catch {
      estat.textContent = t("err_xarxa");
    } finally {
      clearTimeout(rellotge);
      zona.classList.remove("ocupat");
    }
  }
  fitxer.addEventListener("change", () => envia(fitxer.files[0]));
  for (const ev of ["dragenter", "dragover"]) zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add("sobre"); });
  for (const ev of ["dragleave", "drop"]) zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.remove("sobre"); });
  zona.addEventListener("drop", e => envia(e.dataTransfer.files[0]));
})();

// ---- instal·lar a Linux: copia l'ordre
$("#copia-linux").addEventListener("click", async ev => {
  try { await navigator.clipboard.writeText($("#cmd-linux").textContent); ev.target.textContent = t("copiat"); }
  catch { getSelection().selectAllChildren($("#cmd-linux")); }  // sense permís de porta-retalls: almenys queda seleccionada
});

// una partida de la llista de ma.lestudi.com, com les d'aquí; la fitxa i els perfils són allà
const MA = "https://ma.lestudi.com/";
function deMa(g) {
  const eqs = Object.values(g.equips).map(e => e.jugadors.map(j => ({
    nom: j.nom, toon: j.toon, resultat: e.posicio === 1 ? "V" : null,
    perfil: `${MA}player.html?player=${encodeURIComponent(j.toon)}&lang=${LANG}`,
  })));
  return { id: g.id, data: Date.parse(g.data + "Z") / 1000, mapa: g.mapa, durada: g.durada, mmr: null, mu: "Marine Arena",
           jugadors: eqs.flat(), equips: eqs, href: `${MA}game.html?id=${g.id}&lang=${LANG}` };
}

// ---- al perfil: les partides de Marine Arena del jugador (data/ma-players/ és data/players/ de ma.lestudi.com)
async function marineArena(toon, propi) {
  const P = await json(`data/ma-players/${toon}.json`).catch(() => null);
  if (!P || !P.length) return;
  const dataMa = d => data(Date.parse(d + "Z") / 1000);
  $("#ma-cap").innerHTML = `<tr><th>${t("data")}</th><th>${t("ma_posicio")}</th><th>${t("ma_company")}</th><th class="num">${t("durada")}</th></tr>`;
  $("#ma-llista").innerHTML = P.slice(0, 20).map(p => `<tr class="clic" data-href="${MA}game.html?id=${p.id}&lang=${LANG}">
    <td>${dataMa(p.data)}</td><td>${p.posicio ? `${p.posicio === 1 ? "<b>1</b>" : p.posicio} <span class="apagat">/ ${p.n_equips}</span>` : `<span class="apagat">–</span>`}</td>
    <td>${esc(p.company.join(", "))}</td><td class="num">${mmss(p.durada)}</td></tr>`).join("");
  $("#ma-llista").addEventListener("click", ev => { const tr = ev.target.closest("tr[data-href]"); if (tr) location.href = tr.dataset.href; });
  $("#ma-perfil").href = `${MA}player.html?player=${encodeURIComponent(toon)}&lang=${LANG}`;
  $("#ma-perfil").textContent = propi ? t("ma_perfil") : t("ma_perfil_de", { nom: P[0].nom });
  $("#ma").classList.remove("amagat");
}

// ---- llista del servidor: totes les partides registrades, de qualsevol jugador, amb ordre i filtres
async function recents() {
  $("#tauler").classList.add("amagat");
  $("#recents").classList.remove("amagat");
  $("#cap-titol").textContent = t("h1_convidat");
  const [sc2, ma] = await Promise.all([json("data/games.json").catch(() => []), json("data/ma-games.json").catch(() => [])]);
  const gs = sc2.map(g => {
    const ms = g.jugadors.map(j => j.mmr).filter(Boolean);
    const rs = g.jugadors.map(j => RACA[j.raça] || "?").sort();
    return { ...g, mmr: ms.length ? ms.reduce((a, b) => a + b, 0) / ms.length : null, mu: rs.join("v") };
  }).concat(ma.map(deMa)).sort((a, b) => b.data - a.data);
  // columnes ordenables: [clau, text, numèrica]
  const COLS = [["data", t("data"), true], ["mapa", t("mapa"), false], [null, t("jugadors")],
                ["mmr", t("mmr_mitja"), true], ["durada", t("durada"), true]];
  let ordre = "data", desc = true, mostra = 50;
  try { const o = JSON.parse(localStorage.getItem("sc2-ordre-servidor")); if (o && COLS.some(c => c[0] === o[0])) [ordre, desc] = o; } catch {}

  const opcions = (sel, vals, tots) => { $(sel).innerHTML = `<option value="">${tots}</option>` + vals.map(v => `<option>${esc(v)}</option>`).join(""); };
  const compte = clau => { const m = new Map(); for (const g of gs) m.set(g[clau], (m.get(g[clau]) || 0) + 1); return [...m.entries()].sort((a, b) => b[1] - a[1]).map(x => x[0]); };
  opcions("#r-mapa", compte("mapa"), t("tots_mapes"));
  opcions("#r-mu", compte("mu"), t("tots_mu"));
  $("#r-nom").placeholder = t("cerca_jugador");

  const jugador = j => {
    const nom = /^[1-9]-S2-[1-9]-[0-9]+$/.test(j.toon || "") ? `<a class="nom-jugador" href="${j.perfil || "./?player=" + encodeURIComponent(j.toon)}">${esc(j.nom)}</a>` : esc(j.nom);
    return `${j.raça ? raca(j.raça) + " " : ""}${j.resultat === "V" ? `<b>${nom}</b>` : nom}`;
  };
  // Marine Arena: quatre equips de dos, cadascun en una línia (en una sola, la taula no hi cap)
  const jugadors = g => g.equips ? g.equips.map(e => `<div class="equip-ma">${e.map(jugador).join(" + ")}</div>`).join("")
    : g.jugadors.map(jugador).join(` <span class="apagat">${t("vs")}</span> `);
  function pinta() {
    $("#recents-cap").innerHTML = "<tr>" + COLS.map(([c, txt, n]) => !c ? `<th>${txt}</th>`
      : `<th class="${n && c !== "data" ? "num" : ""}" data-ord="${c}" aria-sort="${c === ordre ? (desc ? "descending" : "ascending") : "none"}" tabindex="0">${txt}<span class="fletxa">${c === ordre ? (desc ? "▼" : "▲") : ""}</span></th>`).join("") + "</tr>";
    const fm = $("#r-mapa").value, fu = $("#r-mu").value, fn = $("#r-nom").value.trim().toLowerCase();
    const P = gs.filter(g => (!fm || g.mapa === fm) && (!fu || g.mu === fu) && (!fn || g.jugadors.some(j => j.nom.toLowerCase().includes(fn))));
    // les que no tenen el valor (partides sense MMR) sempre al final
    P.sort((a, b) => {
      const x = a[ordre], y = b[ordre];
      if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
      const r = typeof x === "string" ? x.localeCompare(y, LOC) : x - y;
      return desc ? -r : r;
    });
    $("#r-compte").textContent = t("n_partides", { n: P.length });
    $("#recents-llista").innerHTML = P.slice(0, mostra).map(g => `<tr class="clic" data-href="${g.href || "game.html?id=" + g.id}">
      <td>${data(g.data)}</td><td>${esc(g.mapa)}</td>
      <td>${jugadors(g)}</td>
      <td class="num">${g.mmr ? num(g.mmr) : "–"}</td>
      <td class="num">${mmss(g.durada)}</td></tr>`).join("")
      || `<tr><td colspan="5" class="apagat">${t(gs.length ? "cap_filtre" : "cap_recent")}</td></tr>`;
    $("#r-mes").classList.toggle("amagat", P.length <= mostra);
    $("#r-mes").textContent = t("mes", { n: P.length - mostra });
  }
  const ordena = th => {
    const c = th.dataset.ord, num_ = COLS.find(x => x[0] === c)[2];
    desc = c === ordre ? !desc : num_;  // en canviar de columna: números de més a menys, text de la A a la Z
    ordre = c; mostra = 50;
    try { localStorage.setItem("sc2-ordre-servidor", JSON.stringify([ordre, desc])); } catch {}
    pinta();
  };
  $("#recents-cap").addEventListener("click", ev => { const th = ev.target.closest("th[data-ord]"); if (th) ordena(th); });
  $("#recents-cap").addEventListener("keydown", ev => { const th = ev.target.closest("th[data-ord]"); if (th && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); ordena(th); } });
  for (const id of ["#r-mapa", "#r-mu", "#r-nom"]) $(id).addEventListener("input", () => { mostra = 50; pinta(); });
  $("#r-mes").addEventListener("click", () => { mostra += 100; pinta(); });
  $("#recents-llista").addEventListener("click", ev => { if (ev.target.closest("a")) return; const tr = ev.target.closest("tr[data-href]"); if (tr) location.href = tr.dataset.href; });
  pinta();
}

(async () => {
  // perfil: ?player=<codi de jugador> (abans ?j=); si no, el de qui ha entrat; si no, portada de convidat (recents)
  const usuari = await SESSIO;
  const elsMeus = (usuari && usuari.toons || []).map(x => x.toon);
  const demanat = (new URLSearchParams(location.search).get("player") || new URLSearchParams(location.search).get("j") || "");
  const valid = /^[1-9]-S2-[1-9]-[0-9]{1,12}$/.test(demanat);
  // ?all (abans ?totes), o convidat sense perfil demanat: la pujada i les partides de tothom, no el tauler de ningú
  if (["all", "totes"].some(k => new URLSearchParams(location.search).has(k)) || (!valid && !elsMeus.length)) return recents();
  let perfil = valid ? demanat : elsMeus[0];
  const propi = elsMeus.includes(perfil);
  // al meu perfil: la meva clau de Gemini per als resums de les meves partides
  if (propi) {
    const estat = $("#clau-estat"), entrada = $("#clau-in");
    $("#clau-desa").textContent = t("clau_desa");
    $("#clau-esborra").textContent = t("clau_esborra");
    entrada.placeholder = t("clau_placeholder");
    const mostra = c => {
      $("#clau-esborra").classList.toggle("amagat", !c);
      estat.className = "clau-estat " + (!c ? "" : c.estat === "ok" ? "bona" : "dolenta");
      const mes = new Date().toISOString().slice(0, 7);
      estat.textContent = !c ? t("clau_cap") : c.estat === "ok" ? t("clau_activa", { f: c.final, n: c.mes === mes ? c.fets : 0 })
        : t("clau_error", { f: c.final, e: c.error || "?" });
    };
    const envia = async cos => {
      const r = await fetch(ARREL + "api/key", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(cos) }).catch(() => null);
      const d = r ? await r.json().catch(() => ({})) : {};
      return { ok: r && r.ok, d };
    };
    $("#clau-ia").classList.remove("amagat");
    fetch(ARREL + "api/key", { credentials: "same-origin" }).then(r => r.json()).then(d => mostra(d.clau)).catch(() => {});
    $("#clau-form").addEventListener("submit", async ev => {
      ev.preventDefault();
      const clau = entrada.value.trim();
      if (!clau) return;
      $("#clau-desa").disabled = true; estat.className = "clau-estat"; estat.textContent = t("clau_provant");
      const { ok, d } = await envia({ clau, lang: LANG });
      $("#clau-desa").disabled = false;
      if (ok) { entrada.value = ""; mostra(d.clau); return; }
      estat.className = "clau-estat dolenta";
      estat.textContent = d.error === "format" ? t("clau_format") : d.error === "clau" ? t("clau_dolenta", { e: d.detall || "?" }) : t("clau_errgen");
    });
    $("#clau-esborra").addEventListener("click", async () => {
      const { ok, d } = await envia({ esborra: true });
      if (ok) mostra(d.clau);
    });
  }
  // al meu perfil: si deixo que altres baixin els replays que he pujat
  if (propi) {
    const casella = $("#compartir input");
    casella.checked = !!usuari.compartir;
    $("#compartir").classList.remove("amagat");
    casella.addEventListener("change", async () => {
      casella.disabled = true;
      const r = await fetch(ARREL + "api/share", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ compartir: casella.checked }) }).catch(() => null);
      if (!r || !r.ok) casella.checked = !casella.checked;
      casella.disabled = false;
    });
  }
  marineArena(perfil, propi);
  let totes = await json(`data/players/${perfil}.json`).catch(() => null);
  if (!totes) {
    if (propi) $("#tiles").innerHTML = `<p class="apagat">${t("sense_partides")}</p>`;
    totes = [];
  }
  const enllac = g => `game.html?id=${g.id}&pov=${g.jo.pid}`;
  // només les partides on jugo jo; "jo" i "rival" per a cada una
  const TOTES = totes.map(g => {
    const jo = g.jugadors.find(j => j.jo);
    if (!jo) return null;
    const rival = g.jugadors.find(j => j !== jo);
    const c8 = g.control && g.control["8"];
    return {
      ...g, jo, rival,
      mu: RACA[jo.raça] + "v" + RACA[rival.raça],
      guanya: jo.resultat === "V",
      ctrl8: c8 ? [c8[jo.pid], c8[rival.pid]] : null,
    };
  }).filter(Boolean);

  // capçaleres fixes de la llista i dels filtres
  $("#llista-cap").innerHTML = `<tr><th>${t("data")}</th><th>${t("resultat")}</th><th>${t("mapa")}</th><th>${t("rival")}</th><th class="num">${terme("mmr")}</th><th class="num">${t("durada")}</th><th class="num">${t("combats")}</th><th>${t("ctrl8_curt")}</th></tr>`;
  $("#f-res").innerHTML = `<option value="">${t("tots_res")}</option><option value="V">${t("victories")}</option><option value="D">${t("derrotes")}</option>`;
  $("#f-rival").placeholder = t("rival_cerca");

  // ---- pestanyes per raça: filtren les meves partides i canvien el tema
  const compte = r => TOTES.filter(g => g.jo.raça === r).length;
  const races = ["Terran", "Zerg", "Protoss"].filter(compte).sort((a, b) => compte(b) - compte(a));
  let triada = null;
  try { triada = localStorage.getItem("sc2-raca"); } catch {}
  if (triada !== "" && !races.includes(triada)) triada = races[0] || "";
  $("#races").setAttribute("aria-label", t("races"));
  $("#races").innerHTML = races.map(r => `<button data-r="${r}"><i class="ico ico-${TEMES[r]}"></i>${r} <small>${compte(r)}</small></button>`).join("")
    + `<button data-r=""><i class="ico ico-space"></i>${t("totes")} <small>${TOTES.length}</small></button>`;
  $("#races").addEventListener("click", ev => {
    const b = ev.target.closest("button[data-r]"); if (!b) return;
    triada = b.dataset.r;
    try { localStorage.setItem("sc2-raca", triada); } catch {}
    render();
  });

  const pct = (a, b) => b ? Math.round(100 * a / b) + "%" : "–";
  // mitjana mòbil de les últimes n partides: una partida sola diu poc, la tendència sí
  const mobil = (punts, n = 15) => punts.map((p, k) => {
    const fin = punts.slice(Math.max(0, k - n + 1), k + 1);
    return [p[0], fin.reduce((a, q) => a + q[1], 0) / fin.length];
  });
  const mitjana = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
  let mostra = 40, pinta = () => {};

  function render() {
    for (const b of document.querySelectorAll("#races button")) b.setAttribute("aria-pressed", b.dataset.r === triada);
    document.documentElement.dataset.raca = TEMES[triada] || "space";
    const P = TOTES.filter(g => !triada || g.jo.raça === triada);
    const V = P.filter(g => g.guanya).length;
    const ambMmr = P.filter(g => g.jo.mmr && g.competitiu).sort((a, b) => a.data - b.data);
    const darrer = ambMmr[ambMmr.length - 1];
    const amb8 = P.filter(g => g.ctrl8);

    const nomPerfil = TOTES.length ? TOTES[0].jo.nom : "";
    $("#cap-titol").textContent = propi ? (triada ? t("h1_raca", { r: triada }) : t("h1_index"))
      : (triada ? t("perfil_raca", { nom: nomPerfil, r: triada }) : t("perfil_de", { nom: nomPerfil }));
    $("#resum-cap").textContent = P.length ? t("resum", { n: P.length, a: data(P[P.length - 1].data), b: data(P[0].data) }) : "";

    // ---- tiles
    const durM = mitjana(P.map(g => g.durada));
    const ctrlV = mitjana(amb8.filter(g => g.guanya).map(g => g.ctrl8[0]));
    const ctrlD = mitjana(amb8.filter(g => !g.guanya).map(g => g.ctrl8[0]));
    $("#tiles").innerHTML = `
      <div class="targeta tile"><div class="etiq">${t("partides")}</div><div class="valor">${P.length}</div><div class="det">${t("vd", { v: V, d: P.length - V })}</div></div>
      <div class="targeta tile"><div class="etiq">${t("pct_v")}</div><div class="valor">${pct(V, P.length)}</div><div class="det">${t("durada_mitjana", { t: mmss(durM) })}</div></div>
      <div class="targeta tile"><div class="etiq">${terme("mmr", t("mmr_actual"))}</div><div class="valor">${darrer ? num(darrer.jo.mmr) : "–"}</div><div class="det">${darrer ? esc(t("despres_de", { m: darrer.mapa })) : ""}</div></div>
      <div class="targeta tile"><div class="etiq">${terme("control", t("ctrl8"))}</div>
        <div class="valor vs">${ctrlV != null ? Math.round(ctrlV) + "%" : "–"}<span class="sep">${t("vs")}</span>${ctrlD != null ? Math.round(ctrlD) + "%" : "–"}</div>
        <div class="det">${t("ctrl8_det")}</div></div>`;

    // ---- MMR: una línia per raça, perquè cada raça té el seu MMR
    if (ambMmr.length) {
      const colors = [color("jo"), color("serie3"), color("serie4")];
      const rs = [...new Set(ambMmr.map(g => g.jo.raça))]
        .sort((a, b) => ambMmr.filter(g => g.jo.raça === b).length - ambMmr.filter(g => g.jo.raça === a).length);
      const ys = ambMmr.map(g => g.jo.mmr);
      const lo = Math.floor((Math.min(...ys) - 50) / 100) * 100, hi = Math.ceil((Math.max(...ys) + 50) / 100) * 100;
      const t0 = ambMmr[0].data, t1 = ambMmr[ambMmr.length - 1].data;
      // eix Y desplaçat: restem el mínim i el tornem a sumar en format
      const s = rs.slice(0, 3).map((r, i) => ({ nom: r, color: colors[i],
        punts: ambMmr.filter(g => g.jo.raça === r).map(g => [g.data, g.jo.mmr - lo, g.guanya]) }));
      const propera = x => ambMmr.reduce((m, g) => Math.abs(g.data - x) < Math.abs(m.data - x) ? g : m);
      $("#llegenda-mmr").innerHTML = s.length > 1 ? llegenda(s) : "";
      grafic($("#g-mmr"), {
        series: s, xmin: t0, xmax: Math.max(t0 + 1, t1), ymax: hi - lo, alt: 220, punts: ambMmr.length < 150,
        yfmt: y => String(Math.round(y + lo)),
        xfmt: x => new Date(x * 1000).toLocaleDateString(LOC, { month: "short", year: "2-digit" }),
        xpas: 30 * 86400,
        xtitol: x => { const g = propera(x); return `${data(g.data)} · ${esc(g.mapa)} · ${g.guanya ? t("victoria") : t("derrota")} ${t("vs")} ${esc(g.rival.nom)}`; },
        onClic: x => { location.href = enllac(propera(x)); },
      });
    } else { $("#llegenda-mmr").innerHTML = ""; $("#g-mmr").innerHTML = `<p class="apagat">${t("cap_mmr")}</p>`; }

    // ---- control als 8 min vs resultat
    const trams = [[t("tram_darrere"), d => d < -10], [t("tram_igual"), d => d >= -10 && d <= 10], [t("tram_davant"), d => d > 10]];
    $("#t-control").innerHTML = `<table><thead><tr><th>${t("als8")}</th><th class="num">${t("partides")}</th><th class="num">${t("guanyes")}</th></tr></thead><tbody>${
      trams.map(([nom, f]) => {
        const gs = amb8.filter(g => f(g.ctrl8[0] - g.ctrl8[1]));
        const v = gs.filter(g => g.guanya).length;
        return `<tr><td>${nom}</td><td class="num">${gs.length}</td><td class="num"><b>${pct(v, gs.length)}</b></td></tr>`;
      }).join("")}</tbody></table>`;

    // ---- ritme d'expansió
    const tb = (gs, n) => mitjana(gs.map(g => g.jo.t_bases[n]).filter(x => x != null));
    const PV = P.filter(g => g.guanya), PD = P.filter(g => !g.guanya);
    $("#t-bases").innerHTML = `<table><thead><tr><th>${t("base")}</th><th class="num">${t("victories")}</th><th class="num">${t("derrotes")}</th><th class="num">${t("rival_mitjana")}</th></tr></thead><tbody>${
      [1, 2, 3].map(n => `<tr><td>${t("base" + (n + 1))}</td><td class="num">${mmss(tb(PV, n))}</td><td class="num">${mmss(tb(PD, n))}</td><td class="num apagat">${mmss(mitjana(P.map(g => g.rival.t_bases[n]).filter(x => x != null)))}</td></tr>`).join("")
    }</tbody></table>`;

    // ---- APM i victòries
    const ambApm = P.filter(g => g.jo.apm && g.rival.apm);
    const apmV = mitjana(ambApm.filter(g => g.guanya).map(g => g.jo.apm)), apmD = mitjana(ambApm.filter(g => !g.guanya).map(g => g.jo.apm));
    const tramsA = [[t("apm_menys"), r => r < .85], [t("apm_igual"), r => r >= .85 && r <= 1.15], [t("apm_mes"), r => r > 1.15]];
    $("#t-apm").innerHTML = ambApm.length ? `<div class="tile" style="margin-bottom:10px"><div class="etiq">${terme("apm", t("apm_mitja"))}</div>
        <div class="valor vs">${apmV != null ? Math.round(apmV) : "–"}<span class="sep">${t("vs")}</span>${apmD != null ? Math.round(apmD) : "–"}</div>
        <div class="det">${t("apm_det", { v: apmV != null ? Math.round(apmV) : "–", d: apmD != null ? Math.round(apmD) : "–" })}</div>
        ${(() => { const e = P.filter(g => g.jo.epm != null); if (!e.length) return ""; const ev = mitjana(e.filter(g => g.guanya).map(g => g.jo.epm)), ed = mitjana(e.filter(g => !g.guanya).map(g => g.jo.epm));
          return `<div class="det">${terme("epm", "EPM")}: ${t("apm_det", { v: ev != null ? Math.round(ev) : "–", d: ed != null ? Math.round(ed) : "–" })}</div>`; })()}</div>
      <table><thead><tr><th>${t("apm_vs")}</th><th class="num">${t("partides")}</th><th class="num">${t("guanyes")}</th></tr></thead><tbody>${
        tramsA.map(([nom, f]) => { const gs = ambApm.filter(g => f(g.jo.apm / g.rival.apm)); const v = gs.filter(g => g.guanya).length;
          return `<tr><td>${nom}</td><td class="num">${gs.length}</td><td class="num"><b>${pct(v, gs.length)}</b></td></tr>`; }).join("")
      }</tbody></table>` : `<p class="apagat">–</p>`;
    $("#h-apm-temps").textContent = t("mitjana_15", { x: "APM" });
    const perData = ambApm.slice().sort((a, b) => a.data - b.data);
    if (perData.length > 1) {
      const propera = x => perData.reduce((m, g) => Math.abs(g.data - x) < Math.abs(m.data - x) ? g : m);
      grafic($("#g-apm"), {
        series: [{ nom: "APM", color: color("jo"), punts: mobil(perData.map(g => [g.data, g.jo.apm])) },
                 { nom: t("rival"), color: color("rival"), puntejat: true, gruix: 1.5, punts: mobil(perData.map(g => [g.data, g.rival.apm])) }],
        xmin: perData[0].data, xmax: perData[perData.length - 1].data, alt: 200,
        yfmt: y => String(Math.round(y)),
        xfmt: x => new Date(x * 1000).toLocaleDateString(LOC, { month: "short", year: "2-digit" }), xpas: 30 * 86400,
        xtitol: x => { const g = propera(x); return `${data(g.data)} · ${esc(g.mapa)} · ${g.guanya ? t("victoria") : t("derrota")}`; },
        onClic: x => { location.href = enllac(propera(x)); },
      });
    } else $("#g-apm").innerHTML = "";

    // ---- eficiència de despesa (SQ)
    $("#h-sq").textContent = t("sq_titol");
    $("#sub-sq").textContent = t("sq_explica");
    const ambSq = P.filter(g => g.jo.sq != null && g.rival.sq != null);
    const sqV = mitjana(ambSq.filter(g => g.guanya).map(g => g.jo.sq)), sqD = mitjana(ambSq.filter(g => !g.guanya).map(g => g.jo.sq));
    const tramsS = [[t("sq_pitjor"), d => d <= -5], [t("sq_igual"), d => d > -5 && d < 5], [t("sq_millor"), d => d >= 5]];
    $("#t-sq").innerHTML = ambSq.length ? `<div class="tile" style="margin-bottom:10px"><div class="etiq">${terme("sq")}</div>
        <div class="valor vs">${sqV != null ? Math.round(sqV) : "–"}<span class="sep">${t("vs")}</span>${sqD != null ? Math.round(sqD) : "–"}</div>
        <div class="det">${t("apm_det", { v: sqV != null ? Math.round(sqV) : "–", d: sqD != null ? Math.round(sqD) : "–" })}</div></div>
      <table><thead><tr><th>${t("sq_vs")}</th><th class="num">${t("partides")}</th><th class="num">${t("guanyes")}</th></tr></thead><tbody>${
        tramsS.map(([nom, f]) => { const gs = ambSq.filter(g => f(g.jo.sq - g.rival.sq)); const v = gs.filter(g => g.guanya).length;
          return `<tr><td>${nom}</td><td class="num">${gs.length}</td><td class="num"><b>${pct(v, gs.length)}</b></td></tr>`; }).join("")
      }</tbody></table>` : `<p class="apagat">–</p>`;
    $("#h-sq-temps").textContent = t("mitjana_15", { x: "SQ" });
    const sqData = ambSq.slice().sort((a, b) => a.data - b.data);
    if (sqData.length > 1) {
      const propera = x => sqData.reduce((m, g) => Math.abs(g.data - x) < Math.abs(m.data - x) ? g : m);
      grafic($("#g-sq"), {
        series: [{ nom: "SQ", color: color("jo"), punts: mobil(sqData.map(g => [g.data, g.jo.sq])) },
                 { nom: t("rival"), color: color("rival"), puntejat: true, gruix: 1.5, punts: mobil(sqData.map(g => [g.data, g.rival.sq])) }],
        xmin: sqData[0].data, xmax: sqData[sqData.length - 1].data, alt: 200,
        yfmt: y => String(Math.round(y)),
        xfmt: x => new Date(x * 1000).toLocaleDateString(LOC, { month: "short", year: "2-digit" }), xpas: 30 * 86400,
        xtitol: x => { const g = propera(x); return `${data(g.data)} · ${esc(g.mapa)} · ${g.guanya ? t("victoria") : t("derrota")}`; },
        onClic: x => { location.href = enllac(propera(x)); },
      });
    } else $("#g-sq").innerHTML = "";

    // ---- per enfrontament i per mapa
    const agrupa = (clau) => {
      const m = new Map();
      for (const g of P) { const k_ = clau(g); if (!m.has(k_)) m.set(k_, []); m.get(k_).push(g); }
      return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
    };
    const barraPct = (v, n) => `<span class="barra-mini" title="${pct(v, n)}"><i class="jo" style="width:${n ? 100 * v / n : 0}%;border-radius:4px"></i></span>`;
    $("#t-matchup").innerHTML = `<table><thead><tr><th>${t("enfrontament")}</th><th class="num">${t("partides")}</th><th class="num">${t("victories")}</th><th></th></tr></thead><tbody>${
      agrupa(g => g.mu).map(([mu, gs]) => { const v = gs.filter(g => g.guanya).length;
        return `<tr><td>${mu}</td><td class="num">${gs.length}</td><td class="num"><b>${pct(v, gs.length)}</b></td><td>${barraPct(v, gs.length)}</td></tr>`; }).join("")
    }</tbody></table>`;
    $("#t-mapes").innerHTML = `<div class="taula-cont"><table><thead><tr><th>${t("mapa")}</th><th class="num">${t("partides")}</th><th class="num">${t("victories")}</th><th class="num">${t("ctrl8_curt")}</th></tr></thead><tbody>${
      agrupa(g => g.mapa).map(([m, gs]) => { const v = gs.filter(g => g.guanya).length;
        const c = mitjana(gs.filter(g => g.ctrl8).map(g => g.ctrl8[0]));
        return `<tr><td>${esc(m)}</td><td class="num">${gs.length}</td><td class="num"><b>${pct(v, gs.length)}</b></td><td class="num">${c != null ? Math.round(c) + "%" : "–"}</td></tr>`; }).join("")
    }</tbody></table></div>`;

    // ---- llista amb filtres
    const opcions = (sel, vals, tots) => {
      const v = $(sel).value;
      $(sel).innerHTML = `<option value="">${tots}</option>` + vals.map(m => `<option>${esc(m)}</option>`).join("");
      if (vals.includes(v)) $(sel).value = v;
    };
    opcions("#f-mapa", agrupa(g => g.mapa).map(x => x[0]), t("tots_mapes"));
    opcions("#f-mu", agrupa(g => g.mu).map(x => x[0]), t("tots_mu"));
    pinta = () => {
      const fm = $("#f-mapa").value, fu = $("#f-mu").value, fr = $("#f-res").value, fn = $("#f-rival").value.trim().toLowerCase();
      const gs = P.filter(g => (!fm || g.mapa === fm) && (!fu || g.mu === fu) && (!fr || g.jo.resultat === fr) && (!fn || g.rival.nom.toLowerCase().includes(fn)));
      $("#mes").classList.toggle("amagat", gs.length <= mostra);
      $("#mes").textContent = t("mes", { n: gs.length - mostra });
      $("#llista").innerHTML = gs.slice(0, mostra).map(g => `<tr class="clic" data-href="${enllac(g)}">
        <td>${data(g.data)}</td><td>${res(g.jo.resultat)}</td><td>${esc(g.mapa)}</td>
        <td>${raca(g.jo.raça)} <span class="apagat">${t("vs")}</span> ${raca(g.rival.raça)} ${/^[1-9]-S2-[1-9]-[0-9]+$/.test(g.rival.toon || "") ? `<a class="nom-jugador" href="./?player=${encodeURIComponent(g.rival.toon)}">${esc(g.rival.nom)}</a>` : esc(g.rival.nom)}</td>
        <td class="num">${g.jo.mmr ? num(g.jo.mmr) : "–"} <span class="apagat">/ ${g.rival.mmr ? num(g.rival.mmr) : "–"}</span></td>
        <td class="num">${mmss(g.durada)}</td><td class="num">${g.batalles}</td>
        <td>${g.ctrl8 ? `<span class="barra-mini" title="${esc(t("barra_ctrl", { a: g.ctrl8[0], b: g.ctrl8[1] }))}"><i class="jo" style="width:${g.ctrl8[0]}%"></i><i class="rival" style="width:${g.ctrl8[1]}%"></i></span>` : `<span class="apagat">–</span>`}</td>
      </tr>`).join("") || `<tr><td colspan="8" class="apagat">${t("cap_filtre")}</td></tr>`;
    };
    mostra = 40;
    pinta();
  }

  for (const id of ["#f-mapa", "#f-mu", "#f-res", "#f-rival"]) $(id).addEventListener("input", () => { mostra = 40; pinta(); });
  $("#mes").addEventListener("click", () => { mostra += 60; pinta(); });
  $("#llista").addEventListener("click", ev => { if (ev.target.closest("a")) return; const tr = ev.target.closest("tr[data-href]"); if (tr) location.href = tr.dataset.href; });
  render();
})().catch(e => { document.querySelector(".pagina").insertAdjacentHTML("beforeend", `<p class="carregant">${esc(e.message)}</p>`); });
