// SPDX-License-Identifier: GPL-3.0-or-later
"use strict";

// Model d'influència: el mateix que control_mapa() a analitza.py. Si en canvies res, canvia-ho allà.
const FONTS = { th: [4.0, 12], def: [2.0, 9], s: [1.5, 8], tumor: [1.0, 7] };
const SIGMA_EXER = 8, CADUCA_EXER = 30, LLINDAR = 0.15, DOMINI = 1.5, RES = 2;
const pesExercit = (valor, antig) => antig <= 60 ? Math.min(valor / 150, 3) * Math.exp(-antig / CADUCA_EXER) : 0;

// el mapa sempre és fosc, així que hi fem servir els colors del mode fosc
const MC = { jo: [57, 135, 229], rival: [217, 89, 38] };
const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

(async () => {
  const params = new URLSearchParams(location.search);
  const id = params.get("id");
  if (!id || !/^[0-9a-f]{12}$/.test(id)) throw new Error("id");
  const g = await json(`data/games/${id}.json`);

  // punt de vista: ?pov=<pid> (abans ?jo=), si no el jugador marcat com a "jo", si no el primer
  const triat = g.jugadors.find(j => String(j.pid) === (params.get("pov") || params.get("jo")));
  const jo = triat || g.jugadors.find(j => j.jo) || g.jugadors[0];
  const rival = g.jugadors.find(j => j !== jo);
  const qui = p => p == jo.pid ? "jo" : "rival";
  const nomDe = p => p == jo.pid ? jo.nom : rival.nom;
  const MU = RACA[jo.raça] + "v" + RACA[rival.raça];
  // Spending Quotient: el mateix càlcul que spending_quotient() a analitza.py
  const sq = st => {
    if (!st || st.length < 6) return null;
    const ing = st.reduce((a, s) => a + s.min + s.gas, 0) / st.length;
    const banc = Math.max(1, st.reduce((a, s) => a + s.banc, 0) / st.length);
    return Math.round(35 * (0.00137 * ing - Math.log(banc)) + 240);
  };
  jo.sq = sq(g.stats[jo.pid]); rival.sq = sq(g.stats[rival.pid]);
  if (TEMES[jo.raça]) document.documentElement.dataset.raca = TEMES[jo.raça];

  const nomBase = b => !b ? t("camp_obert") : b.nom === "main" ? t("base_main", { nom: nomDe(b.de) })
    : b.nom === "nat" ? t("base_nat", { nom: nomDe(b.de) }) : t("base_n", { n: b.nom });
  const llocDe = bt => bt.lloc == null ? null : g.bases[bt.lloc];
  const tipusB = bt => t("tb_" + bt.tipus);

  document.title = `${jo.nom} ${t("vs")} ${rival.nom} · ${g.mapa_nom}`;
  $("#cap-mapa").textContent = `${g.mapa_nom} · ${MU}`;
  // cada nom porta a les partides que tenim d'aquell jugador
  const aJugador = j => /^[1-9]-S2-[1-9]-[0-9]+$/.test(j.toon || "") ? `<a class="nom-jugador" href="./?player=${encodeURIComponent(j.toon)}" title="${esc(t("veure_partides", { nom: j.nom }))}">${esc(j.nom)}</a>` : esc(j.nom);
  $("#cap-titol").innerHTML = `<span class="punt jo"></span>${aJugador(jo)} ${raca(jo.raça)} <span class="apagat" style="font-weight:400">${t("vs")}</span> <span class="punt rival"></span>${aJugador(rival)} ${raca(rival.raça)}`;
  $("#cap-det").innerHTML = `${res(jo.resultat)} · ${dataHora(g.data)} · ${mmss(g.durada)}${jo.mmr ? ` · ${terme("mmr")} ${num(jo.mmr)} ${t("vs")} ${num(rival.mmr)}` : ""}${jo.apm ? ` · ${terme("apm")} ${jo.apm} ${t("vs")} ${rival.apm}` : ""}${jo.epm != null ? ` · ${terme("epm")} ${jo.epm} ${t("vs")} ${rival.epm}` : ""}${jo.sq != null ? ` · ${terme("sq")} ${jo.sq} ${t("vs")} ${rival.sq}` : ""}`
    + ` · <a href="?id=${id}&pov=${rival.pid}">${esc(t("vista", { nom: rival.nom }))}</a>`;

  // ---- baixada del replay, si qui l'ha pujat ho permet
  fetch(ARREL + `api/download?id=${id}&check=1`).then(r => r.json()).then(d => {
    if (d.baixable) { $("#baixa").href = ARREL + `api/download?id=${id}`; $("#baixa").classList.remove("amagat"); }
  }).catch(() => {});

  // ---- resum automàtic: {A} i {B} són jugadors[0] i jugadors[1]; si encara no hi és en aquest idioma, es fa ara
  (async () => {
    const posa = d => {
      const noms = { A: aJugador(g.jugadors[0]), B: aJugador(g.jugadors[1]) };
      $("#resum-text").classList.remove("apagat");
      $("#resum-text").innerHTML = esc(d.text).replace(/\{([AB])\}/g, (_, x) => noms[x])
        + `<span class="nota">${esc(t("resum_nota"))}</span>`;
    };
    const desat = await json(`data/summaries/${id}.${LANG}.json`).catch(() => null);
    if (desat) { $("#resum").classList.remove("amagat"); return posa(desat); }
    $("#resum-text").textContent = t("resum_fent");
    $("#resum-text").classList.add("apagat");
    $("#resum").classList.remove("amagat");
    const r = await fetch(ARREL + `api/summary?id=${id}&lang=${LANG}`).catch(() => null);
    if (r && r.ok) posa(await r.json()); else $("#resum").classList.add("amagat");
  })();

  // ---- tiles
  const B = g.batalles;
  const sumP = p => B.reduce((a, b) => a + b.perdues[p].valor, 0);
  const guanyades = B.filter(b => b.guanya == jo.pid).length;
  const pctC = g.control ? g.control.pct : null;
  const mitj = xs => xs.reduce((a, b) => a + b, 0) / xs.length;
  const clau = B.find(b => b.clau);
  const llocTxt = b => b.lloc != null ? t("lloc_a", { l: nomBase(llocDe(b)) }) : "";
  $("#tiles").innerHTML = `
    <div class="targeta tile"><div class="etiq">${t("resultat")}</div><div class="valor">${jo.resultat === "V" ? t("victoria") : t("derrota")}</div><div class="det">${t("resultat_en", { t: mmss(g.durada) })}</div></div>
    <div class="targeta tile"><div class="etiq">${terme("control", t("ctrl_mitja"))}</div>
      ${pctC ? `<div class="valor vs"><span><span class="punt jo"></span>${Math.round(mitj(pctC[jo.pid]))}%</span><span class="sep">${t("vs")}</span><span><span class="punt rival"></span>${Math.round(mitj(pctC[rival.pid]))}%</span></div>` : `<div class="valor">–</div>`}
      <div class="det">${t("ningu")}</div></div>
    <div class="targeta tile"><div class="etiq">${esc(t("balanc_titol", { nom: jo.nom }))}</div>
      <div class="valor">${(() => { const d = sumP(rival.pid) - sumP(jo.pid); return (d > 0 ? "+" : d < 0 ? "−" : "") + k(Math.abs(d)); })()}</div>
      <div class="det">${t("balanc_det", { g: guanyades, n: B.length, a: k(sumP(rival.pid)), b: k(sumP(jo.pid)) })}</div></div>
    <div class="targeta tile"><div class="etiq">${t("moment_clau")}</div>
      ${clau ? `<div class="valor"><a href="#" id="anar-clau">${mmss(clau.t0)}</a></div><div class="det">${esc(t("clau_det", { tipus: tipusB(clau), lloc: llocTxt(clau), nom: nomDe(clau.guanya), d: k(clau.diferencia) }))}</div>` : `<div class="valor">–</div>`}</div>`;

  // ---- mapa
  const M = g.mapa ? await json(`data/maps/${g.mapa}.json`).catch(() => null) : null;
  const img = new Image();
  if (M) { img.src = ARREL + `data/maps/${g.mapa}.png`; await img.decode().catch(() => {}); }
  const W = M ? M.w : 200, H = M ? M.h : 200;
  const [cl, cb, cr, ct] = M ? M.camera : [0, 0, W, H];
  const MARGE = 6;
  const x0 = Math.max(0, cl - MARGE), x1 = Math.min(W, cr + MARGE), y0 = Math.max(0, cb - MARGE), y1 = Math.min(H, ct + MARGE);

  // graella de cel·les jugables a resolució RES
  const gw = Math.ceil(W / RES), gh = Math.ceil(H / RES);
  const jugable = new Uint8Array(gw * gh);
  if (M) {
    let pos = 0, val = 0;
    for (const n of M.jugable) {
      if (val) for (let i = pos; i < pos + n; i++) { const x = i % W, y = (i / W) | 0; jugable[((y / RES) | 0) * gw + ((x / RES) | 0)] = 1; }
      pos += n; val ^= 1;
    }
  }

  function darreraPos(pos, tt) {
    let d = null;
    for (const m of pos) { if (m[0] <= tt) d = m; else break; }
    return d;
  }
  function viusExercit(tt) {
    const out = [];
    for (const [p, valor, t1, pos] of g.exercit) {
      if (pos[0][0] > tt || (t1 != null && t1 <= tt)) continue;
      const d = darreraPos(pos, tt);
      out.push({ p, valor, x: d[1], y: d[2], antig: tt - d[0] });
    }
    return out;
  }
  function influencia(tt) {
    const inf = { [jo.pid]: new Float32Array(gw * gh), [rival.pid]: new Float32Array(gw * gh) };
    const afegeix = (p, x, y, w, sigma) => {
      const a = inf[p]; if (!a || w <= 0) return;
      const sg = sigma / RES, rad = Math.ceil(3 * sg), d2 = 2 * sg * sg;
      const cx = Math.floor(x / RES), cy = Math.floor(y / RES);
      for (let j = Math.max(0, cy - rad); j <= Math.min(gh - 1, cy + rad); j++)
        for (let i = Math.max(0, cx - rad); i <= Math.min(gw - 1, cx + rad); i++) {
          const dx = i - cx, dy = j - cy;
          a[j * gw + i] += w * Math.exp(-(dx * dx + dy * dy) / d2);
        }
    };
    for (const [p, kind, t0, t1, x, y] of g.estructures)
      if (t0 <= tt && (t1 == null || t1 > tt)) afegeix(p, x, y, FONTS[kind][0], FONTS[kind][1]);
    for (const u of viusExercit(tt)) afegeix(u.p, u.x, u.y, pesExercit(u.valor, u.antig), SIGMA_EXER);
    return inf;
  }

  const cv = $("#mapa"), ctx = cv.getContext("2d");
  const off = document.createElement("canvas"); off.width = gw; off.height = gh;
  const offCtx = off.getContext("2d");
  let escala = 1, t_ = 0, seleccionat = null;
  const capa = s => $(s).checked;
  const aPx = (x, y) => [(x - x0) * escala, (y1 - y) * escala];

  function mida() {
    const dpr = window.devicePixelRatio || 1;
    // que hi càpiga d'ample i que no passi del 78% de l'alçada de la finestra
    const amp = Math.min(cv.parentElement.clientWidth, innerHeight * .78 * (x1 - x0) / (y1 - y0));
    escala = amp / (x1 - x0) * dpr;
    cv.width = Math.round(amp * dpr); cv.height = Math.round((y1 - y0) * escala);
    cv.style.width = amp + "px";
    pinta();
  }

  function pinta() {
    const dpr = window.devicePixelRatio || 1, tt = t_;
    ctx.fillStyle = "#0e1116"; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.imageSmoothingEnabled = false;
    if (M && img.complete) ctx.drawImage(img, x0, H - y1, x1 - x0, y1 - y0, 0, 0, cv.width, cv.height);

    if (capa("#c-control") && M) {
      // es pinta a resolució de graella en un canvas a part i s'escala suavitzat
      const inf = influencia(tt), A = inf[jo.pid], Bp = inf[rival.pid];
      const id_ = offCtx.createImageData(gw, gh), d = id_.data;
      for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) {
        const n = j * gw + i;
        if (!jugable[n]) continue;
        const a = A[n], b = Bp[n], o = ((gh - 1 - j) * gw + i) * 4;
        let c = null, al = 0;
        if (a > LLINDAR && a > DOMINI * b) { c = MC.jo; al = Math.min(.5, .2 + a * .08); }
        else if (b > LLINDAR && b > DOMINI * a) { c = MC.rival; al = Math.min(.5, .2 + b * .08); }
        else if (a > LLINDAR && b > LLINDAR) { c = [255, 255, 255]; al = .12; }
        if (!c) continue;
        d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2]; d[o + 3] = al * 255;
      }
      offCtx.putImageData(id_, 0, 0);
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(off, x0 / RES, (gh * RES - y1) / RES, (x1 - x0) / RES, (y1 - y0) / RES, 0, 0, cv.width, cv.height);
    }
    if (M) for (const [x, y, k_] of M.recursos) {
      const [px, py] = aPx(x, y);
      ctx.fillStyle = k_ === "g" ? "rgba(90,220,140,.8)" : "rgba(120,200,255,.75)";
      ctx.fillRect(px - escala * .5, py - escala * .5, escala, escala);
    }
    // bases: anell del propietari actual
    for (const b of g.bases) {
      const occ = b.ocupacio.find(o => o.t0 <= tt && (o.t1 == null || o.t1 > tt));
      const [px, py] = aPx(b.x, b.y);
      if (occ) {
        ctx.strokeStyle = rgba(MC[qui(occ.p)], occ.fet != null && occ.fet <= tt ? .95 : .5);
        ctx.lineWidth = 2 * dpr;
        ctx.beginPath(); ctx.arc(px, py, 6 * escala, 0, Math.PI * 2); ctx.stroke();
      }
      if (capa("#c-bases")) {
        const nom = nomBase(b);
        ctx.font = `${11 * dpr}px system-ui, sans-serif`; ctx.textAlign = "center";
        ctx.fillStyle = "rgba(0,0,0,.6)"; ctx.fillText(nom, px + dpr, py + 9 * escala + dpr);
        ctx.fillStyle = "rgba(230,232,236,.85)"; ctx.fillText(nom, px, py + 9 * escala);
      }
    }
    if (capa("#c-estr")) for (const [p, kind, t0, t1, x, y, fet, prod] of g.estructures) {
      if (t0 > tt || (t1 != null && t1 <= tt)) continue;
      const [px, py] = aPx(x, y);
      const c = MC[qui(p)];
      if (kind === "tumor") { ctx.fillStyle = rgba(c, .5); ctx.beginPath(); ctx.arc(px, py, .7 * escala, 0, 7); ctx.fill(); continue; }
      const m = (kind === "th" ? 5 : 2) * escala, construint = fet != null && tt < fet;
      ctx.fillStyle = rgba(c, construint ? .4 : .95); ctx.fillRect(px - m / 2, py - m / 2, m, m);
      ctx.strokeStyle = kind === "def" ? "#fff" : "rgba(0,0,0,.7)"; ctx.lineWidth = dpr;
      ctx.strokeRect(px - m / 2, py - m / 2, m, m);
      // rellotge: com va la construcció de l'edifici o, si ja està fet, la unitat que està fent
      if (construint) rellotge(px, py, (tt - t0) / Math.max(1, fet - t0), c, 0);
      else if (prod && prod.length) {
        const fent = prod.filter(([a, b]) => a <= tt && tt < b);
        if (fent.length) {
          const [a, b] = fent.reduce((x, y) => (tt - y[0]) / (y[1] - y[0]) > (tt - x[0]) / (x[1] - x[0]) ? y : x);
          rellotge(px, py, (tt - a) / (b - a), c, fent.length);
        }
      }
    }
    if (capa("#c-exer")) for (const u of viusExercit(tt)) {
      if (u.antig > 45) continue;
      const [px, py] = aPx(u.x, u.y);
      ctx.fillStyle = rgba(MC[qui(u.p)], Math.max(.25, 1 - u.antig / 45));
      ctx.beginPath(); ctx.arc(px, py, Math.max(2 * dpr, Math.sqrt(u.valor) / 12 * escala), 0, 7); ctx.fill();
      ctx.strokeStyle = "rgba(0,0,0,.6)"; ctx.lineWidth = dpr; ctx.stroke();
    }
    if (capa("#c-comb")) for (const b of g.batalles) {
      const actiu = tt >= b.t0 - 3 && tt <= b.t1 + 8, passat = tt > b.t1 + 8;
      if (!actiu && !passat && b !== seleccionat) continue;
      const [px, py] = aPx(b.x, b.y);
      const c = b.guanya ? MC[qui(b.guanya)] : [200, 200, 200];
      const r = Math.max(5, b.r) * escala;
      ctx.lineWidth = (b === seleccionat ? 3 : actiu ? 2.5 : 1) * dpr;
      ctx.strokeStyle = b === seleccionat ? "#fff" : actiu ? rgba(c, 1) : rgba(c, .35);
      ctx.setLineDash(actiu || b === seleccionat ? [] : [3 * dpr, 3 * dpr]);
      ctx.beginPath(); ctx.arc(px, py, r, 0, 7); ctx.stroke(); ctx.setLineDash([]);
      if (actiu || b === seleccionat) {
        for (const [mt, mx, my, mp] of b.morts) {
          if (mt > tt && b !== seleccionat) continue;
          const [qx, qy] = aPx(mx, my), s = 1.6 * escala;
          ctx.strokeStyle = rgba(MC[qui(mp)], .95); ctx.lineWidth = 1.5 * dpr;
          ctx.beginPath(); ctx.moveTo(qx - s, qy - s); ctx.lineTo(qx + s, qy + s); ctx.moveTo(qx + s, qy - s); ctx.lineTo(qx - s, qy + s); ctx.stroke();
        }
      }
    }
    // càmera de cada jugador: un trapezi aproximat de la pantalla (més ample per dalt, per la perspectiva)
    if (g.camera && capa("#c-camera")) for (const p of [jo.pid, rival.pid]) {
      const c = camA(p, tt);
      if (!c) continue;
      const vores = [[-CAM_DALT, CAM_ALT], [CAM_DALT, CAM_ALT], [CAM_BAIX, -CAM_ALT], [-CAM_BAIX, -CAM_ALT]];
      ctx.beginPath();
      vores.forEach(([dx, dy], i) => { const [px, py] = aPx(c[1] + dx, c[2] + dy); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
      ctx.closePath();
      ctx.fillStyle = rgba(MC[qui(p)], .08); ctx.fill();
      ctx.strokeStyle = rgba(MC[qui(p)], .95); ctx.lineWidth = 1.5 * dpr; ctx.stroke();
    }
    panell();
    for (const gr of grafics) gr.posaCursor(tt);
  }
  // un rellotge petit sobre un edifici: el sector blanc és la part feta; n > 1, quantes unitats fa alhora (reactor)
  function rellotge(px, py, frac, c, n) {
    const dpr = window.devicePixelRatio || 1, r = Math.max(5 * dpr, 1.3 * escala), cy = py - r * 1.4;
    ctx.fillStyle = "rgba(10,12,16,.8)"; ctx.beginPath(); ctx.arc(px, cy, r, 0, 7); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,.92)"; ctx.beginPath(); ctx.moveTo(px, cy);
    ctx.arc(px, cy, r * .78, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * Math.min(1, Math.max(0, frac))); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = rgba(c, 1); ctx.lineWidth = 1.5 * dpr; ctx.beginPath(); ctx.arc(px, cy, r, 0, 7); ctx.stroke();
    if (n > 1) {
      ctx.font = `bold ${9 * dpr}px system-ui, sans-serif`; ctx.textAlign = "left";
      ctx.fillStyle = "rgba(0,0,0,.7)"; ctx.fillText("×" + n, px + r + 2 * dpr, cy + 4 * dpr);
      ctx.fillStyle = "#fff"; ctx.fillText("×" + n, px + r + 1 * dpr, cy + 3 * dpr);
    }
  }
  // on mirava cada jugador al segon tt: el darrer moviment de càmera abans (cerca binària)
  const CAM_DALT = 17, CAM_BAIX = 12, CAM_ALT = 9;  // mitges amplades i mitja alçada, en cel·les
  function camA(p, tt) {
    const c = g.camera && g.camera[p];
    if (!c || !c.length || c[0][0] > tt) return null;
    let lo = 0, hi = c.length - 1;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (c[m][0] <= tt) lo = m; else hi = m - 1; }
    return c[lo];
  }

  // ---- panell lateral
  // Només es reescriu quan el contingut canvia: si es reescrivís a cada fotograma, durant la
  // reproducció els botons es destruirien entre el clic i el deixar anar, i el clic es perdria.
  const statA = (p, tt) => { let s = null; for (const x of g.stats[p]) { if (x.t <= tt) s = x; else break; } return s || g.stats[p][0]; };
  let panellHtml = "";
  function panell() {
    const el = $("#panell");
    let html;
    if (seleccionat) {
      const b = seleccionat, pj = b.perdues[jo.pid], pr = b.perdues[rival.pid];
      const llista = u => Object.entries(u).map(([n, c]) => `${c}× ${esc(n)}`).join(", ") || t("res");
      const tit = tipusB(b);
      html = `<h3>${esc(tit[0].toUpperCase() + tit.slice(1))} · ${mmss(b.t0)}–${mmss(b.t1)}</h3>
        <div class="apagat" style="font-size:13px;margin-bottom:8px">${esc(nomBase(llocDe(b)))} · ${b.guanya ? `<b style="color:var(--text)">${esc(t("guanya", { nom: nomDe(b.guanya) }))}</b>` : t("empat")}${b.clau ? ` · <span class="etiqueta clau">${t("moment_clau")}</span>` : ""}</div>
        <div class="fila"><span>${t("exer_abans")}</span><span><span class="punt jo"></span><b>${k(b.exercit_abans[jo.pid])}</b> · <span class="punt rival"></span><b>${k(b.exercit_abans[rival.pid])}</b></span></div>
        <div class="fila"><span><span class="punt jo"></span>${esc(t("perd", { nom: jo.nom }))}</span><b>${k(pj.valor)}${pj.treb ? ` · ${t("treb_n", { n: pj.treb })}` : ""}</b></div>
        <div class="llista-u">${llista(pj.unitats)}</div>
        <div class="fila" style="margin-top:6px"><span><span class="punt rival"></span>${esc(t("perd", { nom: rival.nom }))}</span><b>${k(pr.valor)}${pr.treb ? ` · ${t("treb_n", { n: pr.treb })}` : ""}</b></div>
        <div class="llista-u">${llista(pr.unitats)}</div>
        <p style="margin:12px 0 0"><button class="boto" type="button" data-accio="tanca">${t("tanca")}</button></p>`;
    } else {
      const tt = Math.round(t_);
      const sj = statA(jo.pid, tt), sr = statA(rival.pid, tt);
      const i = g.control ? Math.min(Math.round(tt / g.control.pas), pctC[jo.pid].length - 1) : null;
      const cj = i != null ? pctC[jo.pid][i] : null, crv = i != null ? pctC[rival.pid][i] : null;
      const basesDe = p => g.bases.filter(b => b.ocupacio.some(o => o.p == p && o.fet != null && o.fet <= tt && (o.t1 == null || o.t1 > tt))).length;
      const fila = (nom, a, b_) => `<div class="fila"><span>${nom}</span><span><b>${a}</b> <span class="apagat">·</span> <b>${b_}</b></span></div>`;
      const actius = g.batalles.filter(b => tt >= b.t0 - 3 && tt <= b.t1 + 8);
      html = `<h3>${t("al_minut", { t: mmss(tt) })}</h3>
        <div class="apagat" style="font-size:12.5px"><span class="punt jo"></span>${esc(jo.nom)} &nbsp; <span class="punt rival"></span>${esc(rival.nom)}</div>
        ${cj != null ? `<div class="control-barra"><i style="width:${cj}%;background:var(--jo)"></i><i style="flex:1"></i><i style="width:${crv}%;background:var(--rival)"></i></div>
        <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:8px"><span>${t("del_mapa", { p: cj })}</span><span>${crv}%</span></div>` : ""}
        ${fila(t("bases"), basesDe(jo.pid), basesDe(rival.pid))}
        ${fila(t("treballadors"), sj.treb, sr.treb)}
        ${fila(t("exercit"), k(sj.exer), k(sr.exer))}
        ${fila(t("subministrament"), sj.sup + "/" + sj.supmax, sr.sup + "/" + sr.supmax)}
        ${fila(t("ingressos_min"), k(sj.min + sj.gas), k(sr.min + sr.gas))}
        ${fila(t("banc"), k(sj.banc), k(sr.banc))}
        ${actius.length ? `<p style="margin:10px 0 0;font-size:13px">${t("combat_curs")} ${actius.map(b => `<a href="#" data-b="${g.batalles.indexOf(b)}">${esc(tipusB(b))}${esc(llocTxt(b))}</a>`).join(", ")}</p>` : ""}`;
    }
    if (html !== panellHtml) { el.innerHTML = html; panellHtml = html; }
  }
  $("#panell").addEventListener("click", ev => {
    if (ev.target.closest("[data-accio=tanca]")) { seleccionat = null; marcaFila(); pinta(); return; }
    const a = ev.target.closest("a[data-b]");
    if (a) { ev.preventDefault(); selecciona(g.batalles[+a.dataset.b], false); }
  });

  // ---- temps i reproducció
  const rang = $("#temps");
  rang.max = g.durada;
  let jugant = false, darrerT = 0;
  function posaT(nt) {
    t_ = Math.max(0, Math.min(g.durada, nt));
    rang.value = Math.round(t_); $("#temps-txt").textContent = mmss(t_);
    pinta();
  }
  rang.addEventListener("input", () => { musica.buida(); posaT(+rang.value); });

  // ---- música (musica.js): sona amb el reproductor; el MIDI és la partida sencera a ×16
  const musica = Musica(g, jo, rival, tt => ({
    treb: [statA(jo.pid, tt).treb, statA(rival.pid, tt).treb],
    exer: [statA(jo.pid, tt).exer, statA(rival.pid, tt).exer],
  }));
  // encesa per defecte (si no s'ha apagat mai); el navegador només deixa sonar després d'un clic: s'engega amb ▶
  try { if (localStorage.getItem("sc2-so") === "0") $("#c-so").checked = false; } catch {}
  $("#c-so").addEventListener("change", ev => {
    musica.activa(ev.target.checked && jugant);
    try { localStorage.setItem("sc2-so", ev.target.checked ? "1" : "0"); } catch {}
  });
  $("#midi").addEventListener("click", ev => {
    ev.preventDefault();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(musica.midi());
    a.download = `${g.mapa_nom} - ${g.jugadors.map(j => j.nom).join(" vs ")}.mid`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  });
  $("#play").onclick = () => {
    jugant = !jugant; $("#play").textContent = jugant ? "❚❚" : "▶";
    if (!jugant) musica.buida();
    musica.activa(jugant && $("#c-so").checked);
    if (jugant) { if (t_ >= g.durada) t_ = 0; darrerT = performance.now(); requestAnimationFrame(pas); }
  };
  function pas(ara) {
    if (!jugant) return;
    const dt = (ara - darrerT) / 1000; darrerT = ara;
    const abans = t_;
    posaT(t_ + dt * +$("#velocitat").value);
    musica.avanca(abans, t_);
    if (t_ >= g.durada) { jugant = false; $("#play").textContent = "▶"; return; }
    requestAnimationFrame(pas);
  }
  // espai: reprodueix o fa pausa, com a qualsevol reproductor (excepte si s'escriu en un camp o es tria en un desplegable)
  document.addEventListener("keydown", ev => {
    if (ev.code !== "Space" || ev.repeat || ev.ctrlKey || ev.altKey || ev.metaKey) return;
    const el = ev.target;
    if (el.isContentEditable || el.tagName === "TEXTAREA" || el.tagName === "SELECT"
        || (el.tagName === "INPUT" && !["range", "checkbox"].includes(el.type))) return;
    ev.preventDefault();  // que no faci baixar la pàgina ni "clicar" el botó o la casella que tingui el focus
    $("#play").click();
  });
  for (const c of ["#c-control", "#c-estr", "#c-exer", "#c-comb", "#c-bases", "#c-camera"]) $(c).addEventListener("change", pinta);
  // les partides analitzades abans que guardéssim la càmera no en tenen
  if (!g.camera) $("#c-camera").parentElement.classList.add("amagat");

  cv.addEventListener("click", ev => {
    const r = cv.getBoundingClientRect();
    const px = (ev.clientX - r.left) * cv.width / r.width, py = (ev.clientY - r.top) * cv.height / r.height;
    const wx = x0 + px / escala, wy = y1 - py / escala;
    let millor = null, dm = 1e9;
    for (const b of g.batalles) {
      if (b.t0 > t_ + 8 && b !== seleccionat) continue;
      const d = Math.hypot(b.x - wx, b.y - wy);
      if (d < Math.max(6, b.r) && d < dm) { millor = b; dm = d; }
    }
    if (millor) selecciona(millor, false);
  });

  function selecciona(b, saltar = true) {
    seleccionat = b; marcaFila();
    if (saltar) posaT(b.t0); else pinta();
  }

  // ---- gràfics
  const colJo = color("jo"), colRival = color("rival");
  const bandes = g.batalles.filter(b => b.total >= 1500).map(b => [b.t0, Math.max(b.t1, b.t0 + 4)]);
  const sers = (f) => [
    { nom: jo.nom, color: colJo, punts: g.stats[jo.pid].map(s => [s.t, f(s)]) },
    { nom: rival.nom, color: colRival, punts: g.stats[rival.pid].map(s => [s.t, f(s)]) },
  ];
  $("#llegenda-g").innerHTML = llegenda([{ nom: jo.nom, color: colJo }, { nom: rival.nom, color: colRival }]);
  const comuns = { xmax: g.durada, bandes, onClic: x => posaT(x), alt: 170 };
  const grafics = [];
  if (pctC) grafics.push(grafic($("#g-control"), { ...comuns, ymax: 100, yfmt: y => Math.round(y) + "%",
    series: [{ nom: jo.nom, color: colJo, punts: pctC[jo.pid].map((v, i) => [i * g.control.pas, v]) },
             { nom: rival.nom, color: colRival, punts: pctC[rival.pid].map((v, i) => [i * g.control.pas, v]) }] }));
  grafics.push(grafic($("#g-exer"), { ...comuns, series: sers(s => s.exer) }));
  grafics.push(grafic($("#g-treb"), { ...comuns, yfmt: y => String(Math.round(y)), series: sers(s => s.treb) }));
  grafics.push(grafic($("#g-ing"), { ...comuns, series: sers(s => s.min + s.gas) }));
  if (g.apm) grafics.push(grafic($("#g-apm"), { ...comuns, yfmt: y => String(Math.round(y)),
    series: [jo, rival].map((j, n) => ({ nom: `${j.nom} (${j.apm})`, color: n ? colRival : colJo,
      punts: g.apm[j.pid].map((v, i) => [Math.min(g.durada, i * 60 + 30), i === g.apm[j.pid].length - 1 ? v * 60 / Math.max(1, g.durada - i * 60) : v]) })) }));
  else $("#g-apm").closest(".targeta").remove();

  // ---- taula de combats
  $("#combats-cap").innerHTML = `<tr><th>${t("moment")}</th><th>${t("lloc")}</th><th>${t("tipus")}</th>
    <th class="num"><span class="punt jo"></span>${esc(t("perd", { nom: jo.nom }))}</th><th class="num"><span class="punt rival"></span>${esc(t("perd", { nom: rival.nom }))}</th><th>${t("resultat")}</th></tr>`;
  $("#combats").innerHTML = g.batalles.map((b, i) => {
    const pj = b.perdues[jo.pid], pr = b.perdues[rival.pid];
    const r = b.guanya == null ? `<span class="apagat">${t("empat")}</span>` : b.guanya == jo.pid ? `<b>${esc(t("guanya", { nom: jo.nom }))}</b>` : `<span class="apagat">${esc(t("guanya", { nom: rival.nom }))}</span>`;
    return `<tr class="clic" data-i="${i}"><td>${mmss(b.t0)}</td><td>${b.lloc != null ? esc(nomBase(llocDe(b))) : `<span class="apagat">${t("camp_obert")}</span>`}</td>
      <td>${esc(tipusB(b))} ${b.clau ? `<span class="etiqueta clau">${t("clau")}</span>` : ""}</td>
      <td class="num">${k(pj.valor)}${pj.treb ? ` <span class="apagat">(${t("treb_n", { n: pj.treb })})</span>` : ""}</td>
      <td class="num">${k(pr.valor)}${pr.treb ? ` <span class="apagat">(${t("treb_n", { n: pr.treb })})</span>` : ""}</td><td>${r}</td></tr>`;
  }).join("") || `<tr><td colspan="6" class="apagat">${t("cap_combat")}</td></tr>`;
  function marcaFila() {
    for (const tr of document.querySelectorAll("#combats tr")) tr.classList.toggle("sel", !!seleccionat && +tr.dataset.i === g.batalles.indexOf(seleccionat));
  }
  $("#combats").addEventListener("click", ev => {
    const tr = ev.target.closest("tr[data-i]"); if (!tr) return;
    selecciona(g.batalles[+tr.dataset.i]);
    $(".mapa-zona").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  const ac = $("#anar-clau");
  if (ac) ac.onclick = ev => { ev.preventDefault(); selecciona(clau); $(".mapa-zona").scrollIntoView({ behavior: "smooth" }); };

  // ---- gantt de bases
  const ordreB = g.bases.map((b, i) => ({ b, i, primer: Math.min(...b.ocupacio.map(o => o.t0), Infinity) }))
    .filter(x => x.b.ocupacio.length).sort((a, b) => a.primer - b.primer);
  const lliures = g.bases.length - ordreB.length;
  const pc = x => (100 * x / g.durada).toFixed(2) + "%";
  $("#gantt").innerHTML = ordreB.map(({ b }) => `<div class="filera"><div class="nom" title="${esc(nomBase(b))}">${esc(nomBase(b))}</div><div class="pista">${
    b.ocupacio.map(o => {
      const fi = o.t1 ?? g.durada, fet = o.fet ?? fi, c = qui(o.p);
      const tit = esc(`${nomDe(o.p)}: ${o.tipus} · ${t("comenca", { t: mmss(o.t0) })}${o.fet != null ? ", " + t("acabada", { t: mmss(o.fet) }) : ""}${o.t1 != null ? ", " + t("destruida", { t: mmss(o.t1) }) : ""}`);
      return (fet > o.t0 ? `<div class="tram obra ${c}" style="left:${pc(o.t0)};width:${pc(fet - o.t0)}" title="${tit}"></div>` : "")
        + (fi > fet ? `<div class="tram ${c}" style="left:${pc(fet)};width:${pc(fi - fet)}" title="${tit}"></div>` : "");
    }).join("")}</div></div>`).join("")
    + `<div class="filera"><div></div><div class="apagat" style="font-size:12px;display:flex;justify-content:space-between"><span>0:00</span><span>${lliures ? t("sense_ocupar", { n: lliures }) : ""}</span><span>${mmss(g.durada)}</span></div></div>`;

  // ---- ordre de construcció
  const ordre = (p, el) => {
    $(el).innerHTML = (g.ordre[p] || []).map(([tt, n, c]) =>
      `<div><span class="t">${mmss(tt)}</span><span class="${n.startsWith("⬆") ? "mill" : ""}">${esc(n)}${c > 1 ? ` ×${c}` : ""}</span></div>`).join("");
  };
  $("#ordre-jo-t").innerHTML = `<span class="punt jo"></span>${esc(jo.nom)}`;
  $("#ordre-rival-t").innerHTML = `<span class="punt rival"></span>${esc(rival.nom)}`;
  ordre(jo.pid, "#ordre-jo"); ordre(rival.pid, "#ordre-rival");

  // comencem a 6 minuts, que a l'inici no hi ha res a veure
  t_ = Math.min(360, g.durada);
  rang.value = t_; $("#temps-txt").textContent = mmss(t_);
  new ResizeObserver(mida).observe(cv.parentElement);
  mida();
})().catch(e => {
  $("#cap-titol").textContent = t("err_partida");
  $("#cap-det").textContent = e.message === "id" ? "" : e.message;
});
