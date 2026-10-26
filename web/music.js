// SPDX-License-Identifier: GPL-3.0-or-later
// Música de la partida, sincronitzada amb el reproductor del mapa (prototip).
//  - cada jugador és un instrument segons la raça, un a cada costat (estèreo)
//  - cada unitat que neix és una nota: les barates agudes i curtes, les cares greus i llargues
//  - els edificis: les bases són notes greus llargues, la resta campanetes
//  - els combats són percussió, tan forta com els recursos que s'hi perden; el moment clau, un plat
//  - un baix a cada compàs, que puja amb els treballadors, en major si "jo" té més exèrcit i en menor si no
// Les notes no sonen a l'instant: es quantitzen a corxeres a BPM, que és el que fa que soni a música.
// Inspirat en sc2midi (github.com/obohrer/sc2midi), que convertia replays en MIDI.
"use strict";

function Musica(g, jo, rival, estat) {
  const BPM = 112, CORXERA = 60 / BPM / 2;
  const MAJOR = [0, 2, 4, 7, 9], MENOR = [0, 3, 5, 7, 10];  // pentatòniques: sempre sonen bé
  const LA = 57;  // La3 en MIDI
  const PAN = { [jo.pid]: -0.6, [rival.pid]: 0.6 };
  const RACA_DE = { [jo.pid]: jo.raça, [rival.pid]: rival.raça };
  const freq = m => 440 * Math.pow(2, (m - 69) / 12);

  // ---- esdeveniments de la partida, en temps de joc
  const ev = [];
  for (const [p, valor, , pos] of g.exercit) if (pos && pos.length) ev.push({ t: pos[0][0], p, tipus: "unitat", valor });
  for (const [p, kind, t0] of g.estructures) if (t0 > 0) ev.push({ t: t0, p, tipus: kind });
  for (const b of g.batalles) ev.push({ t: b.t0, tipus: "combat", forca: Math.min(1, Math.log10(1 + b.total) / 4), clau: !!b.clau, t1: b.t1 });
  ev.sort((a, b) => a.t - b.t);

  // de valor (minerals+gas) a grau de l'escala: un Zergling (25) ben amunt, un Ultralisk (550) avall
  const grau = valor => Math.max(0, Math.min(9, Math.round(9 - Math.log2(Math.max(25, valor) / 25) * 2)));
  const nota = (escala, g_, oct = 0) => LA + 12 * (oct + Math.floor(g_ / 5)) + escala[g_ % 5];
  const escalaA = tt => { const e = estat(tt); return e.exer[0] >= e.exer[1] ? MAJOR : MENOR; };

  // ---- àudio
  let ctx = null, mestre = null, actiu = false, proper = 0, pas = 0, tJoc = 0;
  const cua = { [jo.pid]: [], [rival.pid]: [] }, cops = [];
  let combatFins = -1;

  function engega() {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    const comp = ctx.createDynamicsCompressor();
    mestre = ctx.createGain(); mestre.gain.value = 0.5;
    // un eco suau dona espai sense haver de fer reverberació
    const eco = ctx.createDelay(); eco.delayTime.value = CORXERA * 3;
    const ret = ctx.createGain(); ret.gain.value = 0.28;
    const humit = ctx.createGain(); humit.gain.value = 0.22;
    mestre.connect(comp); mestre.connect(eco); eco.connect(ret); ret.connect(eco); eco.connect(humit); humit.connect(comp);
    comp.connect(ctx.destination);
  }

  function to(m, quan, dur, vol, raca, pan) {
    const env = ctx.createGain(), panner = ctx.createStereoPanner();
    panner.pan.value = pan; env.connect(panner); panner.connect(mestre);
    const f = freq(m), oscs = [];
    if (raca === "Protoss") {  // dos sinus una mica desafinats: un pad lluminós
      for (const d of [-4, 4]) {
        const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = f; o.detune.value = d;
        o.connect(env); oscs.push(o);
      }
      dur *= 1.8;
    } else {  // Terran quadrada, Zerg dent de serra que "llisca", la resta (campanetes, baix) triangular
      const o = ctx.createOscillator(), filtre = ctx.createBiquadFilter();
      o.type = raca === "Zerg" ? "sawtooth" : raca === "Terran" ? "square" : "triangle";
      o.frequency.value = f;
      if (raca === "Zerg") { o.frequency.setValueAtTime(f * 1.03, quan); o.frequency.exponentialRampToValueAtTime(f, quan + 0.08); }
      filtre.type = "lowpass"; filtre.frequency.value = raca === "Zerg" ? 1100 : 2000;
      o.connect(filtre); filtre.connect(env); oscs.push(o);
    }
    for (const o of oscs) { o.start(quan); o.stop(quan + dur + 0.05); }
    env.gain.setValueAtTime(0.0001, quan);
    env.gain.exponentialRampToValueAtTime(vol, quan + 0.015);
    env.gain.exponentialRampToValueAtTime(0.0001, quan + dur);
  }

  function soroll(quan, dur, vol, fq) {
    const n = ctx.createBufferSource(), mostres = Math.ceil(ctx.sampleRate * dur);
    const buf = ctx.createBuffer(1, mostres, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < mostres; i++) d[i] = Math.random() * 2 - 1;
    n.buffer = buf;
    const f = ctx.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = fq; f.Q.value = 0.8;
    const env = ctx.createGain();
    env.gain.setValueAtTime(vol, quan); env.gain.exponentialRampToValueAtTime(0.0001, quan + dur);
    n.connect(f); f.connect(env); env.connect(mestre); n.start(quan);
  }

  function bombo(quan, vol) {
    const o = ctx.createOscillator(), env = ctx.createGain();
    o.frequency.setValueAtTime(130, quan); o.frequency.exponentialRampToValueAtTime(42, quan + 0.18);
    env.gain.setValueAtTime(vol, quan); env.gain.exponentialRampToValueAtTime(0.0001, quan + 0.35);
    o.connect(env); env.connect(mestre); o.start(quan); o.stop(quan + 0.4);
  }

  // una corxera: com a molt una nota per jugador (la més important de les que esperen), percussió i baix
  function toca(quan) {
    const escala = escalaA(tJoc);
    for (const p of [jo.pid, rival.pid]) {
      const q = cua[p];
      if (!q.length) continue;
      q.sort((a, b) => b.pes - a.pes);
      const e = q.shift();
      if (q.length > 12) q.length = 12;  // a ×64 n'hi ha massa: les petites es perden
      const r = RACA_DE[p];
      if (e.tipus === "unitat") to(nota(escala, grau(e.valor)), quan, 0.12 + (9 - grau(e.valor)) * 0.05, 0.16, r, PAN[p]);
      else if (e.tipus === "th") { to(nota(escala, 0, -1), quan, 1.6, 0.22, r, PAN[p]); to(nota(escala, 3, -1), quan, 1.6, 0.14, r, PAN[p]); }
      else to(nota(escala, 7 + (pas % 3), 1), quan, 0.25, 0.07, "bell", PAN[p]);
    }
    while (cops.length) {
      const c = cops.shift();
      bombo(quan, 0.5 + 0.5 * c.forca);
      soroll(quan, 0.12, 0.25 * c.forca, 1800);
      if (c.clau) soroll(quan, 1.4, 0.35, 6000);
    }
    // mentre dura un combat, caixa a contratemps i charleston
    if (tJoc <= combatFins) { if (pas % 4 === 2) soroll(quan, 0.15, 0.22, 1500); soroll(quan, 0.03, 0.05, 8000); }
    if (pas % 8 === 0) {
      const e = estat(tJoc), treb = e.treb[0] + e.treb[1];
      to(LA - 24 + escala[Math.min(4, Math.floor(treb / 30))], quan, CORXERA * 7, 0.18, "Baix", 0);
    }
    pas++;
  }

  return {
    // engegar o parar el so (l'AudioContext s'ha de crear després d'un clic de l'usuari)
    activa(si) {
      actiu = si;
      if (si && !ctx) engega();
      if (ctx) si ? ctx.resume() : ctx.suspend();
      if (si) proper = ctx.currentTime + 0.05;
    },
    // el reproductor ha avançat de tA a tB (segons de joc): encua el que ha passat i toca les corxeres que toquen
    avanca(tA, tB) {
      if (!actiu || tB <= tA) return;
      tJoc = tB;
      for (const e of ev) {
        if (e.t <= tA) continue;
        if (e.t > tB) break;
        if (e.tipus === "combat") { cops.push(e); combatFins = Math.max(combatFins, e.t1); }
        else if (cua[e.p]) cua[e.p].push({ ...e, pes: e.tipus === "th" ? 1e4 : e.tipus === "unitat" ? e.valor : 30 });
      }
      if (proper < ctx.currentTime) proper = ctx.currentTime + 0.02;
      while (proper < ctx.currentTime + 0.12) { toca(proper); proper += CORXERA; }
    },
    // en saltar o aturar: res pendent
    buida() { cua[jo.pid].length = 0; cua[rival.pid].length = 0; cops.length = 0; combatFins = -1; },

    // la partida sencera com a fitxer MIDI (a ×16, com el reproductor): jo canal 1, rival canal 2, percussió canal 10
    midi() {
      const PPQ = 480, VEL = 16, tic = t => Math.round(t / VEL * (BPM / 60) * PPQ);
      const prog = { Terran: 80, Zerg: 38, Protoss: 89 };  // General MIDI: lead square, synth bass, pad
      const msgs = [];
      const posa = (t, dades) => msgs.push([t, dades]);
      [jo, rival].forEach((j, c) => posa(0, [0xC0 | c, prog[j.raça] ?? 0]));
      for (const e of ev) {
        const t = tic(e.t);
        if (e.tipus === "combat") {
          posa(t, [0x99, 36, Math.round(70 + 57 * e.forca)]); posa(t + PPQ / 4, [0x89, 36, 0]);
          if (e.clau) { posa(t, [0x99, 49, 110]); posa(t + PPQ, [0x89, 49, 0]); }
          continue;
        }
        const c = e.p === jo.pid ? 0 : 1, esc = escalaA(e.t);
        const n = e.tipus === "unitat" ? nota(esc, grau(e.valor)) : e.tipus === "th" ? nota(esc, 0, -1) : nota(esc, 7, 1);
        const dur = e.tipus === "th" ? PPQ * 4 : e.tipus === "unitat" ? PPQ / 4 + (9 - grau(e.valor)) * PPQ / 12 : PPQ / 4;
        posa(t, [0x90 | c, n, e.tipus === "unitat" ? 80 : 60]); posa(t + dur, [0x80 | c, n, 0]);
      }
      msgs.sort((a, b) => a[0] - b[0] || (a[1][0] & 0xF0) - (b[1][0] & 0xF0));  // a igual temps, primer els "note off"
      const vlq = n => { const b = [n & 0x7F]; while ((n >>= 7)) b.unshift((n & 0x7F) | 0x80); return b; };
      const pista = [0, 0xFF, 0x51, 3, ...[16, 8, 0].map(s => (Math.round(60e6 / BPM) >> s) & 0xFF)];
      let ant = 0;
      for (const [t, d] of msgs) { pista.push(...vlq(t - ant), ...d); ant = t; }
      pista.push(0, 0xFF, 0x2F, 0);
      const n32 = n => [24, 16, 8, 0].map(s => (n >> s) & 0xFF);
      const bytes = [0x4D, 0x54, 0x68, 0x64, ...n32(6), 0, 0, 0, 1, PPQ >> 8, PPQ & 0xFF,
                     0x4D, 0x54, 0x72, 0x6B, ...n32(pista.length), ...pista];
      return new Blob([new Uint8Array(bytes)], { type: "audio/midi" });
    },
  };
}
