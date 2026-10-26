<?php
// SPDX-License-Identifier: GPL-3.0-or-later
// Baixada pública d'un replay amb un enllaç signat que fa el servidor (/api/download) quan la partida es pot baixar:
// r.php?id=<id>&e=<caduca>&n=<nom del fitxer>&s=<hmac>, amb s = HMAC-SHA256(clau, "id|e|n").
// Així el fitxer surt directament d'aquí, sense passar pel servidor, i no es poden endevinar enllaços.
declare(strict_types=1);

$BASE = dirname(__DIR__);
$id = (string)($_GET['id'] ?? '');
$e = (string)($_GET['e'] ?? '');
$n = (string)($_GET['n'] ?? '');
$clau = trim((string)@file_get_contents("$BASE/.sc2/clau"));
$f = "$BASE/sc2-replays/$id.SC2Replay";

$ok = $clau !== '' && preg_match('/^[0-9a-f]{12}$/', $id) && ctype_digit($e) && (int)$e >= time()
    && hash_equals(hash_hmac('sha256', "$id|$e|$n", $clau), (string)($_GET['s'] ?? '')) && file_exists($f);
if (!$ok) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Aquest enllaç no és vàlid o ha caducat.\n";
    exit;
}
// el nom ve signat, però per si de cas: res que pugui trencar la capçalera
$nom = preg_replace('/[^\p{L}\p{N} ._()\'-]+/u', '_', $n) ?: $id;
header('Content-Type: application/octet-stream');
header('Content-Length: ' . filesize($f));
header("Content-Disposition: attachment; filename=\"$id.SC2Replay\"; filename*=UTF-8''" . rawurlencode($nom . '.SC2Replay'));
header('Cache-Control: private, max-age=300');
header('X-Robots-Tag: noindex');
readfile($f);
