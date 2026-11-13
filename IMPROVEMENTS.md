# Ways to improve the portfolio

A working list for server-lukas.com, written against the `redesign-dark` branch.
Nothing here is implemented yet. Items are grouped by area and roughly ordered by
how much they help within each group. Tick them off as you go.

Items marked **(checked)** are things I verified in the repo. The rest are
recommendations to judge yourself.

## Do these first

- [ ] Use the updated rsync command from the README on the server. It now has `--exclude IMPROVEMENTS.md`; with the old command this file would be published.
- [ ] Add `width` and `height` to the three images on the home page **(checked: none of them have it, the project pages do)**. Without them the page jumps while images load.
- [ ] Add a social preview image (`og:image`, 1200 × 630) **(checked: missing)**. Right now a link shared in WhatsApp, Signal or Discord shows no picture.
- [ ] Add `<link rel="canonical">` and `og:url` to every page **(checked: missing)**.
- [ ] Make the English version reachable without JavaScript. The EN text only exists in `data-en` attributes, so search engines and people with scripts off only ever see German.
- [ ] Add a real 404 page in the site's design and point nginx at it.

## Content and copy

- [ ] Put one concrete number in the hero or the first screen: machines, containers, services, uptime, or how many people use the photo library.
- [ ] Give each project card one outcome instead of only a description. Example: "in use on my firewall since October 2026".
- [ ] Add a short "what I'm working on now" line and date it, so the site shows it is alive.
- [ ] Add a photo of the actual hardware: the server, the Netzwächter board, the wiring. Real photos are the strongest proof the work is yours.
- [ ] Add a photo or short clip of the Netzwächter sending its SMS.
- [ ] Show a real SMS screenshot next to the drawn SMS bubbles.
- [ ] Give the messenger project a real screenshot. It is the only project with a drawn placeholder.
- [ ] Write one "what I would do differently" paragraph per project. It reads as experience, not marketing.
- [ ] State on each AI-assisted project which parts you decided, tested and fixed yourself, with one specific example.
- [ ] Link the GitHub repository directly from the passkey and Netzwächter cards, not only from the project page.
- [ ] Add a downloadable CV as PDF, in German and English.
- [ ] Say what you are looking for and from when: an internship, a job after the apprenticeship in a given year, or nothing right now.
- [ ] Add the expected end date of the apprenticeship to the facts list.
- [ ] Cut the three "about me" paragraphs by a third. The middle one repeats the homelab card.
- [ ] Replace "Womit ich arbeite" lists with a line per tool on what you used it for. A bare list of names proves little.
- [ ] Mark which skills come from the apprenticeship and which from the homelab.
- [ ] Add the pfSense HA cluster from the apprenticeship as its own short project, as far as your school allows you to describe it.
- [ ] Write the GeoGuessr paragraph with one specific detail: best rank, favourite country to guess, or a region you always get wrong.
- [ ] Decide on "Sie" or "Du" in the contact text and use it everywhere. The contact text says "Sie", the network diagram hint says "Wähle".
- [ ] Have someone else proofread the English version.
- [ ] Add a changelog or "last updated" date on the home page, like the one on the homelab page.

## Structure and navigation

- [ ] Add "Werdegang" or the CV to the top navigation, or drop sections from the page that the nav does not reach.
- [ ] Add previous and next links at the top of project pages as well as the bottom.
- [ ] Show the current project in the nav or crumb so visitors know where they are.
- [ ] Add a table of contents with anchor links on the long homelab page.
- [ ] Make section headings linkable (an anchor icon on hover) so you can send someone a direct link.
- [ ] Open GitHub links in the same tab, or mark external links clearly. Be consistent either way.
- [ ] Keep the language choice when moving between pages via a URL (`/en/…`) rather than only `localStorage`.
- [ ] Add a `sitemap.xml` and a `robots.txt`.

## Design

- [ ] Re-crop the passkey thumbnail. The current crop shows mostly a blue area with the dialog cut off at the top.
- [ ] Pick one screenshot style: all with a browser frame or none, all at the same zoom level.
- [ ] Take screenshots at 2× so they are sharp on phones and high-density laptops.
- [ ] Decide whether a light theme is worth having. The original site had one and many people read in daylight.
- [ ] Check the yellow contact band on a phone in bright light and in a dim room. If it is too loud, shrink its height before changing its colour.
- [ ] Give the hero something only your site has, such as a small live line from the lab (see "Live data" below).
- [ ] Test the big headline with the longest English and German words at 320 px width.
- [ ] Set `hyphens: auto` with the right `lang` on long German compound words in narrow columns.
- [ ] Check every text colour against its background with a contrast checker, including the grey on the panel colour and the small tags.
- [ ] Make link styling consistent: decide which links are underlined and keep to it in running text, cards and footer.
- [ ] Add a visible pressed state to buttons and tabs, not only hover and focus.
- [ ] Draw a proper favicon as SVG and add a 180 px `apple-touch-icon`. The current one is letters in Arial.
- [ ] Add a print style check: print one project page to PDF and fix what looks wrong.

## Accessibility

- [ ] Go through every page with the keyboard only: Tab, Shift+Tab, Enter, arrow keys on the tabs.
- [ ] Add `aria-current="page"` to the active nav item on project pages.
- [ ] The tabs on the homelab page: add Home and End keys, and make sure the hidden panels are reachable when printing or with scripts off.
- [ ] The network diagram buttons use `aria-pressed`. A radio group or tab pattern fits better, because exactly one is always selected.
- [ ] Check the page with a screen reader once (NVDA on Windows or TalkBack on Android), in both languages.
- [ ] When the language switches, text inside elements changes but nothing is announced. Move focus or add a polite live region.
- [ ] Set `lang="en"` on English terms inside German text where pronunciation matters, and the reverse.
- [ ] Make sure every touch target is at least 44 × 44 px. The DE/EN buttons and footer link are smaller.
- [ ] Zoom the browser to 200 % and 400 % and check nothing overlaps or is cut off.
- [ ] Check the site with `prefers-contrast: more` and with forced colours (Windows high contrast).
- [ ] Describe the diagrams in text for people who cannot see them. The Netzwächter diagram is `aria-hidden` with only a caption.

## Performance

- [ ] Serve images in two or three sizes with `srcset` and `sizes`, so phones do not load desktop images.
- [ ] Add AVIF versions next to WebP via `<picture>`.
- [ ] Mark the first visible image with `fetchpriority="high"` and keep `loading="lazy"` only for images below the fold.
- [ ] Subset the Archivo font to Latin characters you use. The file is 48 KB **(checked)** and can likely be halved.
- [ ] Add a fallback font with matching metrics (`size-adjust`, `ascent-override`) so text does not shift when Archivo loads.
- [ ] Set long cache lifetimes for `assets/` in nginx and add a version to file names (`style.3f2a.css`), so updates still arrive at once.
- [ ] Turn on Brotli or at least gzip for HTML, CSS, JS and SVG in nginx.
- [ ] Turn on HTTP/2 or HTTP/3 in Nginx Proxy Manager if it is not already on.
- [ ] Minify CSS and JS during deploy. A small step in the deploy script is enough; no build tool needed.
- [ ] Split `site.js`: the tab and diagram code is only needed on the homelab page.
- [ ] Run Lighthouse and WebPageTest on the live site from a phone profile and write down the numbers before changing anything.

## SEO and sharing

- [ ] Give each project page its own `og:image` with the project name on it.
- [ ] Add `twitter:card` meta tags so previews work in more apps.
- [ ] Add structured data: `Person` on the home page, `CreativeWork` or `SoftwareSourceCode` on project pages.
- [ ] Add `hreflang` links once the English version has its own URLs.
- [ ] Write a distinct `<title>` and description per page and keep titles under about 60 characters.
- [ ] Register the site in Google Search Console and Bing Webmaster Tools and submit the sitemap.
- [ ] Link the site from your GitHub profile and from each repository's README.

## Security and privacy

- [ ] Add security headers in Nginx Proxy Manager: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`.
- [ ] The site loads nothing from third parties any more, so a strict policy works: `default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'`.
- [ ] Turn on HSTS once you are sure every subdomain serves HTTPS.
- [ ] Test the result on securityheaders.com and with the Mozilla Observatory.
- [ ] Add a `security.txt` under `/.well-known/` with a contact address. It fits a site about running infrastructure.
- [ ] Protect the e-mail address from scrapers a little, or accept the spam. A plain `mailto:` gets harvested.
- [ ] Add a short imprint and privacy note. State plainly that the site sets no cookies and loads nothing from third parties.
- [ ] Check the screenshots once more for anything that should not be public: internal hostnames, IP addresses, usernames.
- [ ] Hide the nginx version (`server_tokens off`).

## Reliability and operations

- [ ] Replace the two manual commands with one deploy script on the server, and add `--dry-run` as a first step so you see what will change.
- [ ] Or deploy automatically: a webhook or a small timer on the server that pulls `main` and runs the rsync.
- [ ] Add a check in CI (GitHub Actions) that validates the HTML, checks links and fails on broken ones.
- [ ] Add an external uptime check, so you hear about an outage from outside your own network.
- [ ] Decide what visitors see when the homelab is down: a static fallback page at Cloudflare or a second host.
- [ ] Keep a tagged release per deploy so you can roll back with one command.
- [ ] Look at the nginx access log once a month for 404s and fix or redirect them.
- [ ] If you want visitor numbers, run a self-hosted, cookie-free tool such as GoAccess on the logs, Plausible or Umami.

## Live data from the lab (what would make this site unlike any other)

- [ ] Show a real status line on the home page: "all services up", fed by a small JSON file your monitoring writes every few minutes.
- [ ] Show the date of the last successful off-site backup on the homelab page.
- [ ] Show the date of the last Ansible update run.
- [ ] Show the Minecraft server's online state and player count.
- [ ] Generate the "Zuletzt geändert" list from a file you already keep, not by hand.
- [ ] Keep all of this static: a cron job writes one JSON file into the web root, the page reads it and falls back to plain text if it is missing.

## Code quality

- [ ] The header, navigation and footer are copied into five files. Generate the pages from one template with a small script, or use server-side includes in nginx.
- [ ] Move the German and English texts into one place per page, so a change does not have to be made twice inside an attribute.
- [ ] Run the HTML through the W3C validator and the CSS through a linter once.
- [ ] Remove CSS rules that no page uses any more after the redesign.
- [ ] Add an `.editorconfig` and format all files the same way.
- [ ] Write a short section in the README on how the design works: colours, the font, what the yellow is for, and what not to add.

## Test before calling it done

- [ ] A small Android phone and an iPhone, in portrait and landscape.
- [ ] Firefox, Chrome and Safari on desktop.
- [ ] A slow connection (throttle to "Slow 4G" in the browser tools).
- [ ] JavaScript switched off.
- [ ] The English version on every page, every tab and every diagram state.
- [ ] Ask two people who do not know the site to find your e-mail address and one project, and watch where they hesitate.
