// Browser checks on the built site. Serves dist/ itself.
//   node tools/test-site.mjs            checks only
//   node tools/test-site.mjs --shots    also writes screenshots and a print PDF to test-output/
import { chromium, devices } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const dist = path.join(root, "dist");
const shots = process.argv.includes("--shots");
const outDir = path.join(root, "test-output");
if (shots) fs.mkdirSync(outDir, { recursive: true });
const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
  ".png": "image/png", ".webp": "image/webp", ".avif": "image/avif", ".woff2": "font/woff2", ".pdf": "application/pdf", ".xml": "application/xml", ".txt": "text/plain" };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  const f = path.join(dist, p);
  if (!f.startsWith(dist) || !fs.existsSync(f)) {
    res.writeHead(404, { "content-type": "text/html; charset=utf-8" });
    return res.end(fs.readFileSync(path.join(dist, p.startsWith("/en/") ? "en/404.html" : "404.html")));
  }
  res.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}`;

const pages = ["/", "/projekte/passkey.html", "/projekte/netzwaechter.html", "/projekte/homelab.html", "/projekte/messenger.html", "/datenschutz.html", "/404.html"];
const all = [...pages, ...pages.map(p => "/en" + p)];
const problems = [];
const fail = msg => { problems.push(msg); console.log("FAIL", msg); };
const browser = await chromium.launch();

async function open(ctxOpts, url, fn) {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error" && !/status\.json|404/.test(m.text())) fail(`${url}: console ${m.text()}`); });
  page.on("pageerror", e => fail(`${url}: ${e.message}`));
  page.on("requestfailed", r => fail(`${url}: request failed ${r.url()}`));
  await page.goto(base + url, { waitUntil: "networkidle" });
  await fn(page);
  await ctx.close();
}

// 1. Every page at phone, landscape, desktop and 400 % zoom (320 px): no sideways scrolling
const views = { android: devices["Pixel 5"], iphone: devices["iPhone 13"], landscape: devices["iPhone 13 landscape"],
  desktop: { viewport: { width: 1280, height: 900 } }, zoom400: { viewport: { width: 320, height: 640 } } };
for (const [name, opts] of Object.entries(views)) {
  for (const url of all) {
    await open(opts, url, async page => {
      const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (over > 0) fail(`${name} ${url}: page is ${over}px wider than the screen`);
    });
  }
}
console.log("layout: checked", all.length, "pages at", Object.keys(views).join(", "));

// 2. Touch targets on a phone: links and buttons outside running text at least 44 x 44 px
await open(views.android, "/", async page => {
  const small = await page.evaluate(() => [...document.querySelectorAll("a, button, summary")]
    .filter(el => el.offsetParent && !el.matches(".card h3 a") && !el.closest("p:not(.links):not(.more):not(.card-links), dd, li.log, .vh, .skip"))
    .map(el => [el, el.getBoundingClientRect()])
    .filter(([el, r]) => r.height < 44 || r.width < 24)
    .map(([el, r]) => `${el.textContent.trim().slice(0, 30)} (${Math.round(r.width)}x${Math.round(r.height)})`));
  small.forEach(s => fail(`touch target too small: ${s}`));
});

// 3. JavaScript off: all homelab panels readable, e-mail shown as text, nothing hidden
await open({ ...views.desktop, javaScriptEnabled: false }, "/projekte/homelab.html", async page => {
  const visible = await page.$$eval('[role="tabpanel"]', ps => ps.filter(p => p.offsetHeight > 0).length);
  if (visible !== 4) fail(`no JS: ${visible} of 4 homelab panels visible`);
});
await open({ ...views.desktop, javaScriptEnabled: false }, "/en/", async page => {
  const mail = await page.textContent(".contact .big");
  if (!/lukas\.dalloz \[at\] proton\.me/.test(mail)) fail(`no JS: e-mail fallback is "${mail}"`);
  if (!(await page.textContent("h1")).includes("Networks")) fail("no JS: English page not in English");
});
console.log("no-JS: checked");

// 4. Keyboard: skip link first, tabs and diagram with arrow keys, English text in the diagram
await open(views.desktop, "/en/projekte/homelab.html", async page => {
  await page.keyboard.press("Tab");
  if (!(await page.evaluate(() => document.activeElement.classList.contains("skip")))) fail("keyboard: skip link is not first");
  await page.focus('[role="tab"][aria-selected="true"]');
  await page.keyboard.press("End");
  if ((await page.getAttribute("#t-ops", "aria-selected")) !== "true") fail("keyboard: End does not select the last tab");
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowRight");
  if ((await page.getAttribute("#t-svc", "aria-selected")) !== "true") fail("keyboard: ArrowRight does not move to the next tab");
  if (!(await page.isHidden("#p-net"))) fail("tabs: first panel still visible after switching");
  await page.keyboard.press("Home");
  await page.focus('.net [aria-checked="true"]');
  await page.keyboard.press("ArrowDown");
  const info = await page.textContent("#net-info h4");
  if (info !== "Isolated") fail(`diagram: ArrowDown from DMZ shows "${info}"`);
  await page.keyboard.press("Home");
  if ((await page.textContent("#net-info p")).indexOf("Visitors") !== 0) fail("diagram: English text missing for Internet");
});
console.log("keyboard: checked");

// 5. Theme switch: follows the system, then sticks after a reload
await open({ ...views.desktop, colorScheme: "light" }, "/", async page => {
  const bg = () => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  if (await bg() !== "rgb(244, 244, 241)") fail(`theme: light system gives ${await bg()}`);
  await page.click("#theme");
  if (await bg() !== "rgb(20, 20, 19)") fail("theme: button does not switch to dark");
  await page.reload();
  if (await bg() !== "rgb(20, 20, 19)") fail("theme: choice not kept after reload");
});
console.log("theme: checked");

// 6. Slow 4G: time to load the start page
{
  const ctx = await browser.newContext(views.android);
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 750e3 / 8 });
  const t0 = Date.now();
  await page.goto(base + "/", { waitUntil: "load" });
  const bytes = await page.evaluate(() => performance.getEntriesByType("resource").reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0)
    + performance.getEntriesByType("navigation")[0].encodedBodySize);
  const lcp = await page.evaluate(() => new Promise(r => new PerformanceObserver(l => r(l.getEntries().at(-1).startTime)).observe({ type: "largest-contentful-paint", buffered: true })));
  console.log(`slow 4G: start page loaded in ${Date.now() - t0} ms, ${Math.round(bytes / 1024)} KB, largest paint at ${Math.round(lcp)} ms`);
  await ctx.close();
}

// 7. Screenshots and a print PDF for a person to look at
if (shots) {
  const shot = async (name, opts, url, extra) => open({ ...opts, deviceScaleFactor: opts.deviceScaleFactor || 1 }, url, async page => {
    if (extra) await extra(page);
    await page.screenshot({ path: path.join(outDir, name + ".png"), fullPage: true });
  });
  await shot("home-dark", { ...views.desktop, colorScheme: "dark" }, "/");
  await shot("home-light", { ...views.desktop, colorScheme: "light" }, "/en/");
  await shot("home-phone", { ...views.android, colorScheme: "light" }, "/");
  await shot("homelab-light", { ...views.desktop, colorScheme: "light" }, "/projekte/homelab.html");
  await shot("passkey-dark", { ...views.desktop, colorScheme: "dark" }, "/en/projekte/passkey.html");
  await open(views.desktop, "/projekte/homelab.html", async page => {
    await page.pdf({ path: path.join(outDir, "homelab-print.pdf"), format: "A4", printBackground: true });
  });
  console.log("screenshots in test-output/");
}

await browser.close();
server.close();
console.log(problems.length ? `${problems.length} problems` : "all browser checks passed");
process.exit(problems.length ? 1 : 0);
