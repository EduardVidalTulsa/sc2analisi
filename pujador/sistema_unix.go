// SPDX-License-Identifier: GPL-3.0-or-later
//go:build !windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

func home() string { h, _ := os.UserHomeDir(); return h }

func dirDades() string {
	if d := os.Getenv("XDG_DATA_HOME"); d != "" {
		return filepath.Join(d, "sc2-analisi")
	}
	return filepath.Join(home(), ".local", "share", "sc2-analisi")
}

func rutaInstallada() string { return filepath.Join(home(), ".local", "bin", "sc2-pujador") }

func arrelsSistema() []string { return arrelsLinux(home()) }

func dirUnitats() string {
	if d := os.Getenv("XDG_CONFIG_HOME"); d != "" {
		return filepath.Join(d, "systemd", "user")
	}
	return filepath.Join(home(), ".config", "systemd", "user")
}

const unitat = `[Unit]
Description=SC2 anàlisi: puja les partides noves al servidor

[Service]
ExecStart=%s --fons
Restart=on-failure
RestartSec=60

[Install]
WantedBy=default.target
`

// Amb systemd d'usuari si n'hi ha; si no, una entrada d'inici automàtic de l'escriptori.
func activaInici(exe string) error {
	if _, err := exec.LookPath("systemctl"); err == nil {
		os.MkdirAll(dirUnitats(), 0o755)
		f := filepath.Join(dirUnitats(), "sc2-pujador.service")
		if err := os.WriteFile(f, []byte(fmt.Sprintf(unitat, exe)), 0o644); err != nil {
			return err
		}
		exec.Command("systemctl", "--user", "daemon-reload").Run()
		if exec.Command("systemctl", "--user", "enable", "--now", "sc2-pujador.service").Run() == nil {
			exec.Command("systemctl", "--user", "restart", "sc2-pujador.service").Run()
			return nil
		}
	}
	d := filepath.Join(home(), ".config", "autostart")
	os.MkdirAll(d, 0o755)
	desk := "[Desktop Entry]\nType=Application\nName=SC2 anàlisi\nExec=" + exe + " --fons\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\n"
	if err := os.WriteFile(filepath.Join(d, "sc2-pujador.desktop"), []byte(desk), 0o644); err != nil {
		return err
	}
	return exec.Command(exe, "--fons").Start()
}

func treuInici() {
	exec.Command("systemctl", "--user", "disable", "--now", "sc2-pujador.service").Run()
	os.Remove(filepath.Join(dirUnitats(), "sc2-pujador.service"))
	os.Remove(filepath.Join(home(), ".config", "autostart", "sc2-pujador.desktop"))
}

// atura una còpia anterior en marxa (però no aquest mateix procés, que pot dir-se igual)
func aturaAnterior() {
	exec.Command("systemctl", "--user", "stop", "sc2-pujador.service").Run()
	procs, _ := filepath.Glob("/proc/[0-9]*/exe")
	for _, p := range procs {
		if dest, err := os.Readlink(p); err == nil && filepath.Base(dest) == "sc2-pujador" {
			var pid int
			fmt.Sscanf(filepath.Base(filepath.Dir(p)), "%d", &pid)
			if pid != os.Getpid() {
				if pr, err := os.FindProcess(pid); err == nil {
					pr.Kill()
				}
			}
		}
	}
}

func obreNavegador(url string) { exec.Command("xdg-open", url).Start() }

// avisa per la terminal i, si hi ha escriptori, amb una notificació
func avisa(titol, text string) {
	fmt.Println(titol)
	fmt.Println(text)
	if _, err := exec.LookPath("notify-send"); err == nil {
		exec.Command("notify-send", titol, text).Run()
	}
}
