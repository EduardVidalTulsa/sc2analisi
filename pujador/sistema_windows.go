// SPDX-License-Identifier: GPL-3.0-or-later
//go:build windows

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"
)

const clauInici = `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`

func dirDades() string {
	d := os.Getenv("LOCALAPPDATA")
	if d == "" {
		d = filepath.Join(os.Getenv("USERPROFILE"), "AppData", "Local")
	}
	return filepath.Join(d, "SC2Analisi")
}

func rutaInstallada() string { return filepath.Join(dirDades(), "sc2-pujador.exe") }

// Documents pot dir-se diferent segons l'idioma i pot estar a OneDrive: provem amb comodins.
func arrelsSistema() []string {
	home := os.Getenv("USERPROFILE")
	var out []string
	for _, p := range []string{"*/StarCraft II", "OneDrive*/*/StarCraft II"} {
		m, _ := filepath.Glob(filepath.Join(home, p))
		out = append(out, m...)
	}
	return out
}

func amagat(c *exec.Cmd) *exec.Cmd {
	c.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000} // CREATE_NO_WINDOW
	return c
}

func activaInici(exe string) error {
	if err := amagat(exec.Command("reg", "add", clauInici, "/v", "SC2Analisi", "/t", "REG_SZ",
		"/d", `"`+exe+`" --fons`, "/f")).Run(); err != nil {
		return err
	}
	// i l'engeguem ja, sense esperar al proper inici de sessió
	c := exec.Command(exe, "--fons")
	c.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x00000008 | 0x08000000} // DETACHED_PROCESS | CREATE_NO_WINDOW
	return c.Start()
}

func treuInici() {
	amagat(exec.Command("reg", "delete", clauInici, "/v", "SC2Analisi", "/f")).Run()
}

func aturaAnterior() {
	amagat(exec.Command("taskkill", "/F", "/IM", "sc2-pujador.exe", "/FI", "PID ne "+itoa(os.Getpid()))).Run()
}

func obreNavegador(url string) {
	amagat(exec.Command("rundll32", "url.dll,FileProtocolHandler", url)).Start()
}

// avisa amb una finestra de missatge (l'exe no té consola)
func avisa(titol, text string) {
	u := syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW")
	t, _ := syscall.UTF16PtrFromString(titol)
	m, _ := syscall.UTF16PtrFromString(text)
	u.Call(0, uintptr(unsafe.Pointer(m)), uintptr(unsafe.Pointer(t)), 0x40) // MB_ICONINFORMATION
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	s := ""
	for n > 0 {
		s = string(rune('0'+n%10)) + s
		n /= 10
	}
	return s
}
