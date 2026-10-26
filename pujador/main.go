// SPDX-License-Identifier: GPL-3.0-or-later
// sc2-pujador: vigila les carpetes de replays de StarCraft II i puja les partides noves a
// sc2.lestudi.com, perquè apareguin al perfil del jugador.
//
// Obert sense arguments, s'instal·la (es copia, s'afegeix a l'inici de sessió i s'engega en
// segon pla). Amb --fons fa la feina: cada 30 s mira si hi ha replays nous i els puja.
// Amb --desinstalla ho treu tot.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

// El servidor on es pugen les partides. Es fixa en compilar (puja.sh, PKGBUILD):
//
//	go build -ldflags "-X main.servidor=https://el-meu-servidor/"
//
// i, si cal, es pot canviar sense recompilar amb la variable d'entorn SC2_WEB.
var servidor = "https://sc2.lestudi.com/"

// "si" quan l'ha instal·lat un gestor de paquets (PKGBUILD): llavors no es copia a ~/.local/bin ni s'activa sol.
var empaquetat = ""

const (
	versio  = "1.1"
	pausa   = 30 * time.Second
	maxMida = 8 << 20
)

var reToon = regexp.MustCompile(`^[1-9]-S2-[1-9]-[0-9]{1,12}$`)

// Estat d'un replay ja tractat. Es reenvia si canvia la mida o la data.
type fet struct {
	Mida  int64  `json:"mida"`
	Data  int64  `json:"data"`
	Estat string `json:"estat"` // ok, no-1v1, rebutjat
}

type estat struct {
	Fets map[string]fet `json:"fets"`
}

func main() {
	if w := strings.TrimSpace(os.Getenv("SC2_WEB")); w != "" {
		servidor = strings.TrimRight(w, "/") + "/"
	}
	arg := ""
	if len(os.Args) > 1 {
		arg = os.Args[1]
	}
	switch arg {
	case "--fons":
		fons()
	case "--desinstalla", "--uninstall":
		desinstalla()
		avisa("SC2 · anàlisi", "Desinstal·lat. / Uninstalled.")
	case "--una-volta":
		// per provar: una passada i prou
		configuraLog(true)
		passada(carregaEstat())
	case "":
		if empaquetat != "" {
			instruccionsPaquet()
		} else {
			installa()
		}
	default:
		fmt.Println("sc2-pujador " + versio + " · " + nomServidor())
		fmt.Println("  (sense arguments)  s'instal·la i s'activa / installs and starts itself")
		fmt.Println("  --fons             puja les partides noves (el fa servir el servei) / uploads new games")
		fmt.Println("  --una-volta        una passada i prou / one pass and exit")
		fmt.Println("  --uninstall        el treu / removes it")
	}
}

// nomServidor: sc2.lestudi.com, per als missatges
func nomServidor() string {
	return strings.TrimSuffix(strings.TrimPrefix(strings.TrimPrefix(servidor, "https://"), "http://"), "/")
}

// Instal·lat amb el gestor de paquets: el binari ja és a /usr/bin i el servei d'usuari també hi és; només cal activar-lo.
func instruccionsPaquet() {
	fmt.Println("sc2-pujador " + versio + " · " + nomServidor())
	fmt.Println("Activa'l per al teu usuari / Enable it for your user:")
	fmt.Println("  systemctl --user enable --now sc2-pujador")
	for _, d := range carpetesReplays() {
		if t := toonDe(d); t != "" {
			obreNavegador(servidor + "?player=" + t)
		}
	}
}

// ---------------------------------------------------------------- feina en segon pla

func fons() {
	configuraLog(false)
	log.Printf("sc2-pujador %s engegat", versio)
	e := carregaEstat()
	for {
		passada(e)
		time.Sleep(pausa)
	}
}

func passada(e *estat) {
	for _, dir := range carpetesReplays() {
		toon := toonDe(dir)
		fitxers, _ := filepath.Glob(filepath.Join(dir, "*.SC2Replay"))
		// primer els més antics, perquè el perfil s'ompli en ordre
		sort.Slice(fitxers, func(i, j int) bool { return mtime(fitxers[i]) < mtime(fitxers[j]) })
		for _, f := range fitxers {
			info, err := os.Stat(f)
			if err != nil || info.Size() > maxMida {
				continue
			}
			// un replay acabat d'escriure: esperem que el joc el tanqui
			if time.Since(info.ModTime()) < 10*time.Second {
				continue
			}
			ant, ja := e.Fets[f]
			if ja && ant.Mida == info.Size() && ant.Data == info.ModTime().Unix() {
				continue
			}
			res, espera := puja(f, toon)
			if espera > 0 {
				// el servidor demana calma (429) o no hi ha xarxa: ja ho tornarem a provar
				time.Sleep(espera)
				return
			}
			e.Fets[f] = fet{Mida: info.Size(), Data: info.ModTime().Unix(), Estat: res}
			desaEstat(e)
			log.Printf("%s: %s", filepath.Base(f), res)
		}
	}
}

// puja un replay. Torna l'estat i, si cal esperar i reintentar, quant.
func puja(f, toon string) (string, time.Duration) {
	dades, err := os.ReadFile(f)
	if err != nil {
		return "rebutjat", 0
	}
	url := servidor + "api/upload"
	if toon != "" {
		url += "?player=" + toon
	}
	req, _ := http.NewRequest("POST", url, bytes.NewReader(dades))
	req.Header.Set("Content-Type", "application/octet-stream")
	req.Header.Set("User-Agent", "sc2-pujador/"+versio)
	cli := &http.Client{Timeout: 3 * time.Minute}
	resp, err := cli.Do(req)
	if err != nil {
		log.Printf("xarxa: %v", err)
		return "", 2 * time.Minute
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
	switch {
	case resp.StatusCode == 200:
		return "ok", 0
	case resp.StatusCode == 422:
		return "no-1v1", 0
	case resp.StatusCode == 429:
		return "", time.Minute
	case resp.StatusCode >= 500:
		log.Printf("servidor: %d", resp.StatusCode)
		return "", 5 * time.Minute
	default:
		return "rebutjat", 0
	}
}

// ---------------------------------------------------------------- on són els replays

// carpetesReplays torna totes les carpetes .../Accounts/<compte>/<toon>/Replays/Multiplayer.
func carpetesReplays() []string {
	var arrels []string
	if c := llegeixConfig(); c != "" {
		arrels = append(arrels, c)
	}
	arrels = append(arrels, arrelsSistema()...)
	vist := map[string]bool{}
	var out []string
	for _, a := range arrels {
		m, _ := filepath.Glob(filepath.Join(a, "Accounts", "*", "*", "Replays", "Multiplayer"))
		for _, d := range m {
			r, err := filepath.EvalSymlinks(d)
			if err != nil {
				r = d
			}
			if !vist[r] {
				vist[r] = true
				out = append(out, d)
			}
		}
	}
	return out
}

// arrelsLinux: carpetes "StarCraft II" dins de Wine, Bottles, Lutris i Proton.
func arrelsLinux(home string) []string {
	pats := []string{
		".wine*/drive_c/users/*/Documents/StarCraft II",
		".wine*/drive_c/users/*/My Documents/StarCraft II",
		".local/share/bottles/bottles/*/drive_c/users/*/Documents/StarCraft II",
		".var/app/com.usebottles.bottles/data/bottles/bottles/*/drive_c/users/*/Documents/StarCraft II",
		"Games/*/drive_c/users/*/Documents/StarCraft II",
		".local/share/lutris/prefixes/*/drive_c/users/*/Documents/StarCraft II",
		".steam/steam/steamapps/compatdata/*/pfx/drive_c/users/steamuser/Documents/StarCraft II",
		".local/share/Steam/steamapps/compatdata/*/pfx/drive_c/users/steamuser/Documents/StarCraft II",
	}
	var out []string
	for _, p := range pats {
		m, _ := filepath.Glob(filepath.Join(home, p))
		out = append(out, m...)
	}
	return out
}

func toonDe(dir string) string {
	t := filepath.Base(filepath.Dir(filepath.Dir(dir)))
	if reToon.MatchString(t) {
		return t
	}
	return ""
}

func llegeixConfig() string {
	b, err := os.ReadFile(filepath.Join(dirDades(), "carpeta.txt"))
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(b))
}

// ---------------------------------------------------------------- estat i registre

func fitxerEstat() string { return filepath.Join(dirDades(), "estat.json") }

func carregaEstat() *estat {
	e := &estat{Fets: map[string]fet{}}
	if b, err := os.ReadFile(fitxerEstat()); err == nil {
		json.Unmarshal(b, e)
		if e.Fets == nil {
			e.Fets = map[string]fet{}
		}
	}
	return e
}

func desaEstat(e *estat) {
	b, _ := json.Marshal(e)
	tmp := fitxerEstat() + ".tmp"
	if os.WriteFile(tmp, b, 0o644) == nil {
		os.Rename(tmp, fitxerEstat())
	}
}

func configuraLog(pantalla bool) {
	os.MkdirAll(dirDades(), 0o755)
	f, err := os.OpenFile(filepath.Join(dirDades(), "registre.txt"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	// el registre no creix sense límit
	if info, _ := f.Stat(); info != nil && info.Size() > 1<<20 {
		f.Truncate(0)
	}
	if pantalla {
		log.SetOutput(io.MultiWriter(f, os.Stdout))
	} else {
		log.SetOutput(f)
	}
}

func mtime(f string) int64 {
	if i, err := os.Stat(f); err == nil {
		return i.ModTime().UnixNano()
	}
	return 0
}

// ---------------------------------------------------------------- instal·lació

func installa() {
	os.MkdirAll(dirDades(), 0o755)
	desti := rutaInstallada()
	jo, _ := os.Executable()
	if r, err := filepath.EvalSymlinks(jo); err == nil {
		jo = r
	}
	if !mateixFitxer(jo, desti) {
		aturaAnterior()
		if err := copia(jo, desti); err != nil {
			avisa("SC2 · anàlisi", "No s'ha pogut instal·lar / Could not install:\n"+err.Error())
			os.Exit(1)
		}
	}
	if err := activaInici(desti); err != nil {
		avisa("SC2 · anàlisi", "No s'ha pogut afegir a l'inici / Could not add to startup:\n"+err.Error())
	}
	dirs := carpetesReplays()
	toons := map[string]bool{}
	for _, d := range dirs {
		if t := toonDe(d); t != "" {
			toons[t] = true
		}
	}
	msg := "Instal·lat! Les teves partides 1v1 es pujaran soles a " + nomServidor() + ".\n" +
		"Installed! Your 1v1 games will be uploaded to " + nomServidor() + " automatically.\n\n"
	if len(dirs) == 0 {
		msg += "No he trobat cap carpeta de replays. Escriu-ne la ruta (la carpeta \"StarCraft II\") a:\n" +
			"No replay folder found. Write its path (the \"StarCraft II\" folder) in:\n" +
			filepath.Join(dirDades(), "carpeta.txt")
	} else {
		msg += fmt.Sprintf("Carpetes trobades / Folders found: %d", len(dirs))
	}
	avisa("SC2 · anàlisi", msg)
	for t := range toons {
		obreNavegador(servidor + "?player=" + t)
	}
}

func copia(de, a string) error {
	os.MkdirAll(filepath.Dir(a), 0o755)
	in, err := os.Open(de)
	if err != nil {
		return err
	}
	defer in.Close()
	tmp := a + ".nou"
	out, err := os.OpenFile(tmp, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o755)
	if err != nil {
		return err
	}
	if _, err = io.Copy(out, in); err != nil {
		out.Close()
		return err
	}
	out.Close()
	os.Remove(a)
	return os.Rename(tmp, a)
}

func mateixFitxer(a, b string) bool {
	ia, e1 := os.Stat(a)
	ib, e2 := os.Stat(b)
	return e1 == nil && e2 == nil && os.SameFile(ia, ib)
}

func desinstalla() {
	aturaAnterior()
	treuInici()
	os.Remove(rutaInstallada())
}
