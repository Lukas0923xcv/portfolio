(() => {
  const html = document.documentElement;
  const de = html.lang === "de";

  // ---------- Light and dark: light unless the visitor switched to dark ----------
  const btn = document.getElementById("theme");
  const current = () => html.getAttribute("data-theme") === "dark" ? "dark" : "light";
  const label = () => {
    if (!btn) return;
    const next = current() === "dark" ? (de ? "Helles Design" : "Light design") : (de ? "Dunkles Design" : "Dark design");
    btn.setAttribute("aria-label", next);
    btn.title = next;
  };
  if (btn) {
    btn.addEventListener("click", () => {
      const next = current() === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      label();
    });
    label();
  }

  // ---------- Sticky header: border once scrolled, mark the current section on the start page ----------
  const bar = document.getElementById("bar");
  const navLinks = document.body.classList.contains("home")
    ? [...document.querySelectorAll(".mainnav a")].filter(a => a.getAttribute("href").startsWith("#")) : [];
  const targets = navLinks.map(a => document.querySelector(a.getAttribute("href")));
  const totop = document.querySelector(".totop");
  function onScroll() {
    if (bar) bar.classList.toggle("scrolled", window.scrollY > 4);
    if (totop) totop.classList.toggle("on", window.scrollY > window.innerHeight * .8);
    if (!navLinks.length) return;
    let current = -1;
    targets.forEach((t, i) => { if (t && t.getBoundingClientRect().top < 160) current = i; });
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) current = targets.length - 1;
    navLinks.forEach((a, i) => i === current ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current"));
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ---------- E-mail address: assembled here, so it isn't in the HTML for scrapers ----------
  document.querySelectorAll("a.mail[data-u]").forEach(a => {
    const addr = a.dataset.u + "@" + a.dataset.d;
    a.href = "mailto:" + addr;
    if (!a.hasAttribute("data-label")) a.textContent = addr;
  });

  // ---------- Copy the address (start page) ----------
  const copy = document.querySelector("button.copy");
  const mailA = document.querySelector("a.mail[data-u]");
  if (copy && mailA && navigator.clipboard) {
    const text = copy.querySelector("span");
    const idle = text.textContent;
    let timer;
    copy.hidden = false;
    copy.addEventListener("click", () => {
      const done = ok => {
        text.textContent = ok ? (de ? "Kopiert ✓" : "Copied ✓") : (de ? "Bitte manuell kopieren" : "Please copy by hand");
        clearTimeout(timer);
        timer = setTimeout(() => { text.textContent = idle; }, 2000);
      };
      navigator.clipboard.writeText(mailA.dataset.u + "@" + mailA.dataset.d).then(() => done(true), () => done(false));
    });
  }

  // ---------- Project filter (start page). Without JavaScript every project is listed. ----------
  const chips = [...document.querySelectorAll(".chip[data-filter]")];
  const rows = [...document.querySelectorAll(".prow[data-cat]")];
  const count = document.querySelector("[data-count]");
  if (chips.length && rows.length) {
    chips[0].parentElement.hidden = false;
    const pad = n => String(n).padStart(2, "0");
    chips.forEach(c => c.addEventListener("click", () => {
      const f = c.dataset.filter;
      chips.forEach(o => o.setAttribute("aria-pressed", String(o === c)));
      let shown = 0;
      rows.forEach(r => { const on = f === "all" || r.dataset.cat === f; r.hidden = !on; if (on) shown++; });
      if (count) count.textContent = `${pad(shown)} / ${pad(rows.length)} ${de ? "routen" : "routes"}`;
    }));
  }

  // ---------- Live lab status, written every few minutes by deploy/status/write_status.py ----------
  const fmt = iso => new Date(iso).toLocaleDateString(de ? "de-CH" : "en-GB", { day: "numeric", month: "short" });
  fetch("/status.json", { cache: "no-store" })
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(s => {
      if (!s || !s.updated || Date.now() - new Date(s.updated) > 36 * 3600 * 1000) return;  // stale: keep the static text
      const set = (key, text) => document.querySelectorAll(`[data-status="${key}"]`).forEach(el => { el.textContent = text; el.hidden = false; });
      const parts = [];
      if (s.services) parts.push(de ? `${s.services.up} von ${s.services.total} Diensten erreichbar` : `${s.services.up} of ${s.services.total} services up`);
      if (s.backup_offsite) parts.push(de ? `letztes Backup ausser Haus am ${fmt(s.backup_offsite)}` : `last off-site backup on ${fmt(s.backup_offsite)}`);
      if (parts.length) set("summary", parts.join(", "));
      if (s.backup_offsite) set("backup", (de ? "Letztes Backup ausser Haus: " : "Last off-site backup: ") + fmt(s.backup_offsite));
      if (s.updates_last_run) set("updates", (de ? "Letzter Update-Lauf: " : "Last update run: ") + fmt(s.updates_last_run));
      if (s.minecraft) set("minecraft", s.minecraft.online
        ? (de ? `Minecraft-Server online, ${s.minecraft.players} von ${s.minecraft.max} Plätzen belegt` : `Minecraft server online, ${s.minecraft.players} of ${s.minecraft.max} players`)
        : (de ? "Minecraft-Server gerade offline" : "Minecraft server offline right now"));
      document.querySelectorAll(".tag[data-status-live]").forEach(t => t.classList.toggle("live", !s.services || s.services.up === s.services.total));
    })
    .catch(() => {});
})();
