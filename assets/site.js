(() => {
  const html = document.documentElement;

  // ---------- Language: German by default, English on request ----------
  const titleDe = document.title;
  const descTag = document.querySelector('meta[name="description"]');
  const descDe = descTag ? descTag.content : "";
  const translated = [...document.querySelectorAll("[data-en]")];
  const german = new Map(translated.map(el => [el, el.innerHTML]));
  const altDe = new Map();
  const altEl = [...document.querySelectorAll("[data-alt-en]")];
  altEl.forEach(el => altDe.set(el, el.getAttribute("alt")));
  const langButtons = [...document.querySelectorAll(".lang button")];
  let lang = "de";
  const listeners = [];

  function setLang(l) {
    lang = l;
    html.lang = l;
    document.title = l === "en" && html.dataset.titleEn ? html.dataset.titleEn : titleDe;
    if (descTag) descTag.content = l === "en" && html.dataset.descEn ? html.dataset.descEn : descDe;
    translated.forEach(el => el.innerHTML = l === "en" ? el.dataset.en : german.get(el));
    altEl.forEach(el => el.setAttribute("alt", l === "en" ? el.dataset.altEn : altDe.get(el)));
    langButtons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === l)));
    listeners.forEach(fn => fn(l));
    try { localStorage.setItem("lang", l); } catch (e) {}
  }
  langButtons.forEach(b => b.addEventListener("click", () => setLang(b.dataset.lang)));

  // ---------- Sticky header: border once scrolled, mark the current section ----------
  const bar = document.getElementById("bar");
  const navLinks = [...document.querySelectorAll(".top nav a")].filter(a => a.getAttribute("href").startsWith("#"));
  const targets = navLinks.map(a => document.querySelector(a.getAttribute("href")));
  function onScroll() {
    if (bar) bar.classList.toggle("scrolled", window.scrollY > 4);
    if (!navLinks.length) return;
    let current = -1;
    targets.forEach((t, i) => { if (t && t.getBoundingClientRect().top < 140) current = i; });
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) current = targets.length - 1;
    navLinks.forEach((a, i) => a.setAttribute("aria-current", String(i === current)));
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ---------- Tabs (homelab page) ----------
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  function select(tab) {
    tabs.forEach(t => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
  }
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => select(t));
    t.addEventListener("keydown", e => {
      const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!d) return;
      const next = tabs[(i + d + tabs.length) % tabs.length];
      select(next); next.focus();
    });
  });

  // ---------- Network diagram (homelab page) ----------
  const panel = document.getElementById("net-info");
  if (panel) {
    const info = {
      de: {
        internet: ["Internet", "Besucher erreichen nur den Reverse Proxy und den Game-Server. Alles andere bleibt von aussen zu."],
        router:   ["Router des Providers", "Der Router gibt eingehenden Verkehr direkt an die Firewall weiter, so wird alles an einem Ort gefiltert."],
        fw:       ["pfSense-Firewall", "Routet und filtert zwischen allen Zonen. Blocklisten und Länderfilter greifen zuerst, und der Login auf die Firewall braucht zusätzlich zum Passwort einen Passkey."],
        lab:      ["Lab", "Interne Dienste wie Inventar, Monitoring und Automatisierung. Nichts davon ist aus dem Internet erreichbar. Admin-Zugriff läuft über Cloudflare Tunnels mit Mehrfaktor-Login."],
        dmz:      ["DMZ", "Hier laufen die öffentlichen Dienste: der Reverse Proxy mit Single Sign-on, die Web-Apps dahinter und der Minecraft-Server. Die DMZ ist von den anderen Netzen abgeschnitten."],
        iso:      ["Isoliert", "Eine Sandbox für Testmaschinen. Sie hat Internetzugang, kann aber mit nichts anderem im Lab sprechen."]
      },
      en: {
        internet: ["Internet", "Visitors only ever reach the reverse proxy and the game server. Everything else stays closed from the outside."],
        router:   ["ISP router", "The router hands incoming traffic straight to the firewall, so all filtering happens in one place."],
        fw:       ["pfSense firewall", "Routes and filters between all zones. Blocklists and country filters run first, and logging in to the firewall needs a passkey on top of the password."],
        lab:      ["Lab", "Internal services like the inventory, monitoring and automation. Nothing here is reachable from the internet. Admin access goes through Cloudflare Tunnels with multi-factor login."],
        dmz:      ["DMZ", "Where public services live: the reverse proxy with single sign-on, the web apps behind it and the Minecraft server. The DMZ is cut off from the other networks."],
        iso:      ["Isolated", "A sandbox for test machines. It has internet access but can't talk to anything else in the lab."]
      }
    };
    const boxes = [...document.querySelectorAll(".net .box")];
    let node = "dmz";
    const show = n => {
      node = n;
      boxes.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.node === n)));
      panel.querySelector("h4").textContent = info[lang][n][0];
      panel.querySelector("p").textContent = info[lang][n][1];
    };
    boxes.forEach(b => b.addEventListener("click", () => show(b.dataset.node)));
    listeners.push(() => show(node));
  }

  // ---------- Start in the saved language ----------
  let saved = null;
  try { saved = localStorage.getItem("lang"); } catch (e) {}
  setLang(saved === "en" ? "en" : "de");
})();
