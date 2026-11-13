# Portfolio Lukas Dalloz

Statische Website auf Deutsch und Englisch, ohne Framework. Ein kleines Python-Skript
baut aus `src/` die fertige Website in `dist/`. Sie läuft auf einem nginx-LXC in der DMZ
meines Homelabs, hinter Nginx Proxy Manager.

## Aufbau

- `src/pages/` – eine Datei pro Seite. Deutsch steht im Element, Englisch im Attribut
  `data-en="…"` desselben Elements. Oben in jeder Datei stehen Titel und Beschreibung.
- `src/site.json` – Adresse, E-Mail, Änderungsprotokoll des Labs und optionale Angaben
  (was ich suche, ein GeoGuessr-Detail, Search-Console-Codes). Leere Felder erscheinen nicht.
- `src/assets/` – CSS, JavaScript, Bilder, die Schrift Archivo (SIL Open Font License,
  siehe `src/assets/fonts/OFL-Archivo.txt`) und die Lebenslauf-PDFs.
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

- **Farben:** Graphit `#141413` oder helles Grau `#F4F4F1` als Grund, Schrift `#F1EFE8` bzw.
  `#141413`, und genau eine Signalfarbe: Gelb `#F5C518` wie Beschriftungsband aus dem
  Etikettendrucker. Gelb ist immer Hintergrund mit schwarzer Schrift darauf (Status „live“,
  gewählter Teil im Netzwerkdiagramm, Kontaktband), nie Textfarbe auf hellem Grund. Für
  Unterstreichungen und den Fokusrahmen im hellen Modus gibt es ein dunkles Ocker (`--mark`).
- **Hell und dunkel:** folgt dem System, bis jemand umschaltet. Die Wahl liegt nur im Browser.
- **Schrift:** Archivo, Überschriften fett und breit (`font-stretch: 112%`), Text normal.
  Monospace nur für Status-Etiketten, Daten und Befehle.
- **Formen:** eckig, keine Schatten, kein Leuchten, keine Kästen um Text. Abstände trennen
  Abschnitte, Linien nur dort, wo Zeilen einer Liste getrennt werden.
- **Links:** im Fliesstext und im Fuss unterstrichen, in Navigation und Projekttiteln nicht.
  Links auf andere Websites tragen einen kleinen Pfeil.
- **Nicht hinzufügen:** Verläufe, Glas-Effekte, Emoji, Einblend-Animationen beim Scrollen,
  Karten mit Rahmen und Schatten, eine zweite Akzentfarbe.
