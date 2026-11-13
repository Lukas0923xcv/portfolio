// Turns build-cv/cv-de.html and cv-en.html into PDFs in src/assets/cv/.
// Run after `python3 build.py --cv`:   node tools/make-cv.mjs
// Needs Playwright with Chromium (npx playwright install chromium).
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const out = path.join(root, "src/assets/cv");
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage();
for (const [lang, name] of [["de", "lebenslauf-lukas-dalloz.pdf"], ["en", "cv-lukas-dalloz-en.pdf"]]) {
  await page.goto("file://" + path.join(root, "build-cv", `cv-${lang}.html`));
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: path.join(out, name), format: "A4", printBackground: true, preferCSSPageSize: true });
  console.log("wrote", name);
}
await browser.close();
