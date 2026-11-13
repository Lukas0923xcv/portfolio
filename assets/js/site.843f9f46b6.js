(() => {
const html = document.documentElement;
const de = html.lang === "de";
const btn = document.getElementById("theme");
const current = () => html.getAttribute("data-theme") ||
(matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
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
matchMedia("(prefers-color-scheme: light)").addEventListener("change", label);
label();
}
const bar = document.getElementById("bar");
const navLinks = document.body.classList.contains("home")
? [...document.querySelectorAll(".mainnav a")].filter(a => a.getAttribute("href").startsWith("#")) : [];
const targets = navLinks.map(a => document.querySelector(a.getAttribute("href")));
function onScroll() {
if (bar) bar.classList.toggle("scrolled", window.scrollY > 4);
if (!navLinks.length) return;
let current = -1;
targets.forEach((t, i) => { if (t && t.getBoundingClientRect().top < 160) current = i; });
if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) current = targets.length - 1;
navLinks.forEach((a, i) => i === current ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current"));
}
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();
document.querySelectorAll("a.mail[data-u]").forEach(a => {
const addr = a.dataset.u + "@" + a.dataset.d;
a.href = "mailto:" + addr;
if (!a.hasAttribute("data-label")) a.textContent = addr;
});
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