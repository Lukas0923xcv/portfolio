# Portfolio Lukas Dalloz

Statische Website (HTML, CSS, etwas JavaScript), Deutsch und Englisch.
Läuft auf einem nginx-LXC in der DMZ meines Homelabs, hinter Nginx Proxy Manager.

## Aufbau

- `index.html` – Startseite
- `projekte/` – eine Seite pro Projekt
- `assets/` – CSS, JavaScript, Bilder und die Schrift Archivo (SIL Open Font License, siehe `assets/fonts/OFL-Archivo.txt`)

## Auf dem Server aktualisieren

```bash
cd /var/www/portfolio-src && sudo git pull
sudo rsync -a --delete --exclude .git --exclude README.md /var/www/portfolio-src/ /var/www/portfolio/
```
