# Portfolio Lukas Dalloz

Statische Website auf Deutsch und Englisch, ohne Framework. Ein kleines Python-Skript
baut aus `src/` die fertige Website in `dist/`. Sie läuft auf einem nginx-LXC in der DMZ
meines Homelabs, hinter Nginx Proxy Manager.

## Aufbau

- `src/pages/` – eine Datei pro Seite. Deutsch steht im Element, Englisch im Attribut
  `data-en="…"` desselben Elements. Oben in jeder Datei stehen Titel und Beschreibung.
- `src/site.json` – Adresse, E-Mail, Änderungsprotokoll des Labs und optionale Angaben
  (was ich suche, ein GeoGuessr-Detail, Search-Console-Codes). Leere Felder erscheinen nicht.
- `src/assets/` – CSS, JavaScript, Bilder, die Schriften Bricolage Grotesque und JetBrains Mono
  (SIL Open Font License, siehe `src/assets/fonts/OFL-*.txt`; Archivo nur noch für den Lebenslauf)
  und die Lebenslauf-PDFs.
- `build.py` – baut `dist/`: Seiten in beiden Sprachen (`/` und `/en/`), gemeinsamer Kopf und
  Fuss, Bilder in mehreren Grössen als AVIF und WebP, Schrift auf die verwendeten Zeichen
  gekürzt, Dateinamen mit Hash, Vorschaubilder für geteilte Links, Sitemap, `robots.txt`,
  `security.txt`, gzip- und Brotli-Dateien.
- `tools/` – Prüfungen (`check.py`, `test-site.mjs`) und der Lebenslauf (`cv.html`, `make-cv.mjs`).
- `deploy/` – Deploy-Skript, nginx-Konfiguration, systemd-Timer und das Skript für `status.json`.
- `IMPROVEMENTS.md` – Liste mit Verbesserungen und ihrem Stand.

## Lokal bauen und prüfen

```bash
pip install -r requirements.txt
```

```bash
python3 build.py && python3 tools/check.py
```

```bash
npm install --no-save playwright && npx playwright install chromium && node tools/test-site.mjs --shots
```

Ansehen: `python3 -m http.server -d dist 8000` und dann http://localhost:8000 öffnen.

Lebenslauf neu erzeugen, nachdem `tools/cv.html` geändert wurde:

```bash
python3 build.py --cv && node tools/make-cv.mjs
```

## Wie eine Änderung live geht

1. Änderung auf `main` pushen.
2. GitHub Actions baut die Website, prüft Links, HTML, Kontrast und das Verhalten im Browser
   und legt das Ergebnis in den Branch `site`, mit einem Tag pro Build (`site-…`).
3. Auf dem Server holt ein Timer alle 10 Minuten den neusten Build und kopiert ihn in den
   Web-Root. Von Hand geht es mit `sudo portfolio-deploy`, das zuerst zeigt, was sich ändert.

Zurück auf einen älteren Stand: `sudo portfolio-deploy --list`, dann
`sudo portfolio-deploy site-20261113-1500-abc1234`.

## Server einmalig umstellen

Bisher zeigte `/var/www/portfolio-src` auf `main`. Neu zeigt es auf den gebauten Branch `site`:

```bash
cd /var/www/portfolio-src && sudo git fetch origin site && sudo git checkout -B site origin/site
```

```bash
sudo install -m 755 /var/www/portfolio-src/_deploy/deploy.sh /usr/local/sbin/portfolio-deploy
```

```bash
sudo portfolio-deploy
```

Automatisch deployen und den Lab-Status schreiben:

```bash
sudo cp /var/www/portfolio-src/_deploy/systemd/* /etc/systemd/system/ && sudo systemctl daemon-reload
```

```bash
sudo systemctl enable --now portfolio-deploy.timer
```

```bash
sudo install -D -m 644 /var/www/portfolio-src/_deploy/status/write_status.py /usr/local/lib/portfolio/write_status.py
```

```bash
sudo cp /var/www/portfolio-src/_deploy/status/example-config.json /etc/portfolio-status.json
```

Dann `/etc/portfolio-status.json` anpassen (welche Adressen geprüft werden, welche Dateien
das letzte Backup und den letzten Update-Lauf markieren) und starten:

```bash
sudo systemctl enable --now portfolio-status.timer
```

Damit das Backup- und Update-Datum stimmt, am Ende des Backup-Jobs bzw. des Ansible-Laufs
die Marker-Datei berühren, zum Beispiel `touch /var/lib/portfolio-status/offsite-backup.done`.

nginx: `deploy/nginx/portfolio.conf` und `portfolio-headers.conf` nach den Anleitungen in den
Dateien installieren. Nginx Proxy Manager: siehe `deploy/nginx/npm-advanced.conf`
(HTTP/2, HSTS und zwei Zusatzzeilen).

404-Fehler aus dem Log der letzten Wochen: `deploy/check-404.sh`.
Besucherzahlen ohne Cookies, direkt aus dem Log: `sudo goaccess /var/log/nginx/access.log --log-format=COMBINED -o /var/www/stats.html`
(nicht in den Web-Root der Website legen).

## Wie das Design funktioniert

- **Farben:** warmes Off-White `#F4F2EC` (dunkel: `#0E0F0C`) mit feinem 48-px-Raster wie
  Millimeterpapier, Schrift `#121410` bzw. `#ECEAE3`, und genau eine Signalfarbe: Blau
  `#3B30FF` (dunkel: `#A29DFF`). Blau ist Fläche mit heller Schrift (Knöpfe, gewählter Filter,
  Automation-Kachel) oder Text, Unterstreichung und Fokusrahmen (`--mark`).
- **Hell und dunkel:** hell ist Standard, der Knopf oben rechts schaltet auf dunkel. Die Wahl
  liegt nur im Browser.
- **Schrift:** Bricolage Grotesque für Text und grosse, enge Überschriften; JetBrains Mono für
  Etiketten, Daten, Navigation und Knöpfe.
- **Sprache der Oberfläche:** Netzwerk-Jargon als roter Faden: Abschnitte heissen
  `§01 — routing-tabelle`, der Lebenslauf ist ein `traceroute`, der Kontakt ein `SYN → / ← ACK`,
  die 404 ein `ICMP type 3`.
- **Formen:** eckig, dünne Linien, Kacheln mit 1-px-Rahmen, keine Verläufe, kein Leuchten.
  Einzige Bewegung: das Laufband mit den Werkzeugen (aus bei «Bewegung reduzieren»).
- **Links:** im Fliesstext unterstrichen, in Navigation, Projektzeilen und Fuss nicht.
  Links auf andere Websites tragen einen kleinen Pfeil.
- **Nicht hinzufügen:** eine zweite Akzentfarbe, Schatten, Glas-Effekte, Emoji,
  Einblend-Animationen beim Scrollen.
