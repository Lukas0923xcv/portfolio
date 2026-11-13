# Portfolio Lukas Dalloz

Statische Website (HTML, CSS, etwas JavaScript), Deutsch und Englisch.
Läuft auf einem nginx-LXC in der DMZ meines Homelabs, hinter Nginx Proxy Manager.

## Aufbau

- `index.html` – Startseite
- `projekte/` – eine Seite pro Projekt
- `assets/` – CSS, JavaScript und Bilder. Die Schriften Geist und Geist Mono kommen von Google Fonts.

## Auf dem Server aktualisieren

```bash
cd /var/www/portfolio-src && sudo git pull
sudo rsync -a --delete --exclude .git --exclude README.md /var/www/portfolio-src/ /var/www/portfolio/
```
