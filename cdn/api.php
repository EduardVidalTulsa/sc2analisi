<?php
// SPDX-License-Identifier: GPL-3.0-or-later
// API privada de l'allotjament PHP per al servidor de la web: guarda els replays i fa de pont amb MySQL,
// perquè el servidor pot tenir IP dinàmica i no connectar-se directament a la base de dades.
//
// Tot passa per ?op=<operació> amb la capçalera X-Clau (secret compartit, a ~/.sc2/clau).
// Els replays es desen fora de la carpeta web, a ~/sc2-replays/<id>.SC2Replay.
declare(strict_types=1);

$BASE = dirname(__DIR__);
$CONF = "$BASE/.sc2";
$REPLAYS = "$BASE/sc2-replays";

function surt(int $codi, $dades): void {
    http_response_code($codi);
    header('Content-Type: application/json');
    header('Cache-Control: no-store');
    echo json_encode($dades, JSON_UNESCAPED_UNICODE);
    exit;
}

$clau = trim((string)@file_get_contents("$CONF/clau"));
if ($clau === '' || !hash_equals($clau, (string)($_SERVER['HTTP_X_CLAU'] ?? ''))) {
    surt(403, ['error' => 'clau']);
}

function db(): PDO {
    global $CONF;
    static $pdo = null;
    if ($pdo) return $pdo;
    $c = parse_ini_file("$CONF/my.cnf", true, INI_SCANNER_RAW)['client'];
    $pdo = new PDO("mysql:host={$c['host']};dbname={$c['database']};charset=utf8mb4", $c['user'], $c['password'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
    return $pdo;
}

function cos_json(): array {
    $d = json_decode((string)file_get_contents('php://input'), true);
    return is_array($d) ? $d : [];
}

function id_valid(string $id): bool { return (bool)preg_match('/^[0-9a-f]{12}$/', $id); }
function toon_valid(string $t): bool { return (bool)preg_match('/^[1-9]-S2-[1-9]-[0-9]{1,12}$/', $t); }

$op = $_GET['op'] ?? '';
try {
    switch ($op) {
    case 'installa':
        db()->exec("CREATE TABLE IF NOT EXISTS usuaris (id BIGINT PRIMARY KEY, battletag VARCHAR(64), toons JSON, vist INT)");
        db()->exec("CREATE TABLE IF NOT EXISTS sessions (clau CHAR(64) PRIMARY KEY, usuari BIGINT NOT NULL, caduca INT NOT NULL, INDEX (caduca))");
        db()->exec("CREATE TABLE IF NOT EXISTS perfils (toon VARCHAR(24) NOT NULL, partida CHAR(12) NOT NULL, afegit INT, PRIMARY KEY (toon, partida))");
        db()->exec("CREATE TABLE IF NOT EXISTS replays (id CHAR(12) PRIMARY KEY, origen VARCHAR(8) NOT NULL, nom VARCHAR(255), mida INT, rebut INT)");
        // compartir: l'usuari deixa que altres baixin els replays que ha pujat (per defecte, no)
        $c = db()->query("SHOW COLUMNS FROM usuaris LIKE 'compartir'")->fetch();
        if (!$c) db()->exec("ALTER TABLE usuaris ADD compartir TINYINT NOT NULL DEFAULT 0");
        // claus de Gemini dels usuaris, xifrades al servidor (aquí no hi ha la clau per desxifrar-les)
        db()->exec("CREATE TABLE IF NOT EXISTS claus_gemini (usuari BIGINT PRIMARY KEY, xifrada TEXT NOT NULL, final VARCHAR(8),
                    lang VARCHAR(4), afegida INT, estat VARCHAR(12) NOT NULL DEFAULT 'ok', error VARCHAR(255),
                    mes CHAR(7), fets INT NOT NULL DEFAULT 0, ultim INT)");
        surt(200, ['ok' => true]);

    // ---- replays
    case 'replay_puja':
        // arriba com a fitxer (multipart): el ModSecurity d'alguns allotjaments bloqueja un cos binari "cru"
        $id = $_GET['id'] ?? '';
        $tmp = $_FILES['replay']['tmp_name'] ?? '';
        $dades = ($tmp !== '' && is_uploaded_file($tmp)) ? (string)file_get_contents($tmp) : '';
        if (!id_valid($id) || strlen($dades) === 0 || strlen($dades) > 8 << 20) surt(400, ['error' => 'id']);
        // l'id és el principi del sha1 del fitxer: així no se'n pot desar un amb un id que no li toca
        if (substr(sha1($dades), 0, 12) !== $id) surt(400, ['error' => 'sha1']);
        if (!is_dir($REPLAYS)) mkdir($REPLAYS, 0700, true);
        $f = "$REPLAYS/$id.SC2Replay";
        if (!file_exists($f)) {
            file_put_contents("$f.tmp", $dades);
            rename("$f.tmp", $f);
        }
        // 'ma': partides de Marine Arena (ma.lestudi.com), que l'anàlisi de sc2 no fa servir
        $origen = in_array($_GET['origen'] ?? '', ['meu', 'enviat', 'ma'], true) ? $_GET['origen'] : 'enviat';
        db()->prepare("INSERT INTO replays (id, origen, nom, mida, rebut) VALUES (?,?,?,?,?)
                       ON DUPLICATE KEY UPDATE origen = IF(origen = 'meu', 'meu', VALUES(origen)), nom = COALESCE(VALUES(nom), nom)")
            ->execute([$id, $origen, mb_substr((string)($_GET['nom'] ?? ''), 0, 255) ?: null, strlen($dades), time()]);
        surt(200, ['ok' => true]);

    case 'replay_baixa':
        $id = $_GET['id'] ?? '';
        $f = "$REPLAYS/$id.SC2Replay";
        if (!id_valid($id) || !file_exists($f)) surt(404, ['error' => 'no-trobat']);
        header('Content-Type: application/octet-stream');
        header('Content-Length: ' . filesize($f));
        readfile($f);
        exit;

    case 'replay_permis':
        // es pot baixar si algú que l'ha pujada ho permet: els toons del seu perfil (taula perfils) i, si
        // és de les "meves", el toon que passa el servidor com a ?jo=
        $id = $_GET['id'] ?? '';
        if (!id_valid($id) || !file_exists("$REPLAYS/$id.SC2Replay")) surt(200, ['baixable' => false]);
        $s = db()->prepare("SELECT toon FROM perfils WHERE partida = ?");
        $s->execute([$id]);
        $toons = array_column($s->fetchAll(), 'toon');
        $s = db()->prepare("SELECT origen FROM replays WHERE id = ?");
        $s->execute([$id]);
        if (($s->fetch()['origen'] ?? '') === 'meu' && toon_valid((string)($_GET['jo'] ?? ''))) $toons[] = $_GET['jo'];
        $ok = false;
        $q = db()->prepare("SELECT 1 FROM usuaris WHERE compartir = 1 AND JSON_CONTAINS(toons, JSON_OBJECT('toon', ?)) LIMIT 1");
        foreach (array_unique($toons) as $t) {
            $q->execute([$t]);
            if ($q->fetch()) { $ok = true; break; }
        }
        surt(200, ['baixable' => $ok]);

    case 'replays':
        $s = db()->query("SELECT id, origen, nom, mida, rebut FROM replays ORDER BY rebut");
        surt(200, $s->fetchAll());

    // ---- usuaris i sessions (a la base de dades només hi ha el sha256 de la galeta de sessió)
    case 'usuari_desa':
        $d = cos_json();
        db()->prepare("INSERT INTO usuaris (id, battletag, toons, vist) VALUES (?,?,?,?)
                       ON DUPLICATE KEY UPDATE battletag = VALUES(battletag), toons = VALUES(toons), vist = VALUES(vist)")
            ->execute([(int)$d['id'], (string)$d['battletag'], json_encode($d['toons'] ?? []), time()]);
        surt(200, ['ok' => true]);

    case 'sessio_nova':
        $d = cos_json();
        if (!preg_match('/^[0-9a-f]{64}$/', (string)($d['clau'] ?? ''))) surt(400, ['error' => 'clau']);
        db()->prepare("DELETE FROM sessions WHERE caduca < ?")->execute([time()]);
        db()->prepare("INSERT INTO sessions (clau, usuari, caduca) VALUES (?,?,?)")->execute([$d['clau'], (int)$d['usuari'], (int)$d['caduca']]);
        surt(200, ['ok' => true]);

    case 'sessio_usuari':
        $d = cos_json();
        $s = db()->prepare("SELECT u.id, u.battletag, u.toons, u.compartir FROM sessions s JOIN usuaris u ON u.id = s.usuari
                            WHERE s.clau = ? AND s.caduca > ?");
        $s->execute([(string)($d['clau'] ?? ''), time()]);
        $u = $s->fetch();
        if ($u) { $u['toons'] = json_decode($u['toons'], true) ?: []; $u['compartir'] = (bool)$u['compartir']; }
        surt(200, ['usuari' => $u ?: null]);

    case 'usuari_compartir':
        $d = cos_json();
        db()->prepare("UPDATE usuaris SET compartir = ? WHERE id = ?")->execute([empty($d['compartir']) ? 0 : 1, (int)$d['id']]);
        surt(200, ['ok' => true]);

    // ---- claus de Gemini dels usuaris: fan els resums de les seves partides amb la seva quota
    case 'clau_desa':
        $d = cos_json();
        db()->prepare("REPLACE INTO claus_gemini (usuari, xifrada, final, lang, afegida, estat, error, mes, fets, ultim)
                       VALUES (?,?,?,?,?,'ok',NULL,NULL,0,NULL)")
            ->execute([(int)$d['usuari'], (string)$d['xifrada'], mb_substr((string)$d['final'], 0, 8), mb_substr((string)($d['lang'] ?? 'en'), 0, 4), time()]);
        surt(200, ['ok' => true]);

    case 'clau_esborra':
        db()->prepare("DELETE FROM claus_gemini WHERE usuari = ?")->execute([(int)(cos_json()['usuari'] ?? 0)]);
        surt(200, ['ok' => true]);

    case 'clau_info':
        $s = db()->prepare("SELECT final, lang, afegida, estat, error, mes, fets, ultim FROM claus_gemini WHERE usuari = ?");
        $s->execute([(int)(cos_json()['usuari'] ?? 0)]);
        surt(200, ['clau' => $s->fetch() ?: null]);

    case 'claus_actives':
        $s = db()->query("SELECT c.usuari, c.xifrada, c.lang, u.toons FROM claus_gemini c JOIN usuaris u ON u.id = c.usuari WHERE c.estat = 'ok'");
        $out = [];
        foreach ($s as $r) { $r['toons'] = array_column(json_decode($r['toons'], true) ?: [], 'toon'); $out[] = $r; }
        surt(200, $out);

    case 'clau_estat':
        $d = cos_json();
        db()->prepare("UPDATE claus_gemini SET estat = ?, error = ? WHERE usuari = ?")
            ->execute([in_array($d['estat'] ?? '', ['ok', 'error'], true) ? $d['estat'] : 'error', mb_substr((string)($d['error'] ?? ''), 0, 255) ?: null, (int)$d['usuari']]);
        surt(200, ['ok' => true]);

    case 'clau_us':
        // una crida feta amb la clau: compta les d'aquest mes
        $d = cos_json();
        $mes = (string)($d['mes'] ?? '');
        db()->prepare("UPDATE claus_gemini SET fets = IF(mes = ?, fets + 1, 1), mes = ?, ultim = ? WHERE usuari = ?")
            ->execute([$mes, $mes, time(), (int)$d['usuari']]);
        surt(200, ['ok' => true]);

    case 'sessio_tanca':
        db()->prepare("DELETE FROM sessions WHERE clau = ?")->execute([(string)(cos_json()['clau'] ?? '')]);
        surt(200, ['ok' => true]);

    // ---- quines partides ha pujat cada jugador (el que abans era enviats/perfils.json)
    case 'perfil_afegeix':
        $d = cos_json();
        if (!toon_valid((string)($d['toon'] ?? '')) || !id_valid((string)($d['partida'] ?? ''))) surt(400, ['error' => 'dades']);
        db()->prepare("INSERT IGNORE INTO perfils (toon, partida, afegit) VALUES (?,?,?)")->execute([$d['toon'], $d['partida'], time()]);
        surt(200, ['ok' => true]);

    case 'perfils':
        $out = [];
        foreach (db()->query("SELECT toon, partida FROM perfils ORDER BY afegit") as $r) $out[$r['toon']][] = $r['partida'];
        surt(200, (object)$out);

    default:
        surt(404, ['error' => 'op']);
    }
} catch (Throwable $e) {
    error_log('sc2 api: ' . $e->getMessage());
    surt(500, ['error' => 'intern']);
}
