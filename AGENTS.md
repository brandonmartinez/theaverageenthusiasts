# AGENTS.md — theaverageenthusiasts.com

An **archive site**. The Average Enthusiasts was a video game podcast hosted by
Brandon Martinez and Kenny Graham, 38 episodes from 2017-09-17 to 2021-10-20.
The show is over. This repo republishes the whole run as one static page, and —
just as importantly — keeps the podcast feed alive for anyone still subscribed.

## The rule that matters most

**Do not invent content.** Every episode number, title, description, publish
date, duration, file size and audio URL on this page came out of the show's own
RSS feed. The "links mentioned" lists came from the show-note files written at
the time. The title cards are the ones that shipped with the episodes. Editorial
voice is confined to the hero, the season intros, and the colophon.

The one quoted human being is Brandon quoting his own **public** 2017 blog post.
Private material (iMessage, DMs) was used only as background for dates and
framing and must never be quoted on this public page.

## Provenance

| Thing                                                                                    | Source                                                      |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Episode numbers, titles, descriptions, dates, durations, GUIDs, byte lengths, audio URLs | `feed.xml` from the show's own published RSS feed           |
| "Links mentioned"                                                                        | `Episodes/tae-episode-NNN/*.txt` show-note files            |
| Episode title cards (eps 015–037)                                                        | artwork shipped in each `Episodes/tae-episode-NNN/` folder  |
| Album cover                                                                              | `Media/Podcast/`                                            |
| Wordmark, "TAE" mark, brand colors, typefaces                                            | `Media/Logo Pack/` — the brand sheet is `1x/Artboard 1.png` |
| Host photos                                                                              | `Media/Bios/`                                               |
| Framing of when and why the show started/stopped                                         | the owner's own public blog post, 2017-09-20                |

Source material lives outside this repo at
`~/Documents/Clients/The Average Enthusiasts`. It is **not** vendored here.

`data/episodes.json` is the parsed dataset and is the single source of truth for
everything generated.

## Brand

From the brand sheet, not guessed:

- Red `#E74C3C`, blue `#2980B9`
- Display sans: **Bebas Neue** Regular
- Serif: **Bodoni 72 Oldstyle** Book → **Bodoni Moda** on the web

`"Bodoni 72 Oldstyle"` leads the serif stack so Apple machines render the exact
brand face with no download at all.

## Generation

`src/index.html`, all three feeds and `src/sitemap.xml` are **generated**:

```sh
python3 scripts/generate.py
```

Editorial prose lives in the `TEMPLATE` string and the `SEASONS` list inside
`scripts/generate.py`. Edit it there, not in `src/index.html`, or the next run
will overwrite you.

**`src/feed/index.html` is hand-written** and is never touched by the generator.

## The feeds — read this before changing anything

There are three feed files, all emitted by the same `channel_xml()`:

| File                     | URL                                                   | Role                                   |
| ------------------------ | ----------------------------------------------------- | -------------------------------------- |
| `src/feed/feed.xml`      | `https://www.theaverageenthusiasts.com/feed/feed.xml` | **canonical** — the feed going forward |
| `src/podcast/feed.xml`   | `…/podcast/feed.xml`                                  | alias at the historic path shape       |
| `legacy/assets-feed.xml` | uploaded over the Azure blob's `podcast/feed.xml`     | migrates existing subscribers          |

Two contracts hold this together:

1. **`<guid>` values are byte-identical to the original feed** and
   `isPermaLink="false"`. They are old `http://assets…/audio/…` URLs and they
   look wrong. Leave them alone. Changing a GUID makes every podcast app treat
   the episode as brand new and re-download the entire back catalogue.
2. **`<itunes:new-feed-url>` appears only in `legacy/assets-feed.xml`.** That is
   Apple's permanent-move marker: apps that read the old blob feed follow it to
   the canonical URL and update themselves. Putting it in the canonical feed
   would create a redirect loop.

All three carry `<itunes:complete>yes</itunes:complete>` — the show has ended.

The old feed URL must keep answering. Do not delete the blob.

## Audio hosting

The MP3s are **not in this repo**. 958 MB of audio against GitHub Pages' 1 GB
published-site limit is not a fight worth having, so the audio stays exactly
where it has always been: the `taestorage` Azure Storage account.

`assets.theaverageenthusiasts.com` is a CNAME onto that account, and **Azure Blob
custom domains get no TLS certificate**. So:

- `https://assets.theaverageenthusiasts.com/…` → certificate name mismatch
- `http://assets.theaverageenthusiasts.com/…` on an HTTPS page → blocked as
  mixed content

Both fail. The site therefore points at the storage account's own HTTPS endpoint,
`https://taestorage.blob.core.windows.net/podcast/…`, which has a valid cert.

This is one constant in `scripts/generate.py`:

```python
CANONICAL_MEDIA_BASE = "https://assets.theaverageenthusiasts.com/podcast"
MEDIA_BASE = "https://taestorage.blob.core.windows.net/podcast"
```

Once `assets.` sits behind something that terminates TLS for it (the Cloudflare
migration), set `MEDIA_BASE = CANONICAL_MEDIA_BASE`, re-run the generator, and
re-upload `legacy/assets-feed.xml`. Nothing else changes.

**If the storage account is ever retired, this site loses all its audio.** That
dependency is the single biggest risk to the archive.

## Build

Static HTML + Tailwind v4, compiled by a local CLI build, published to GitHub
Pages by `.github/workflows/deploy.yml`.

```sh
npm install
npm run dev     # vite with Tailwind watching
npm run build   # emits _site/
```

- **No framework.** No React, no bundler, no CMS. Vite is a dev server only; the
  build is `cp -R src/. _site/`.
- The dependency budget is three dev dependencies: `@tailwindcss/cli`,
  `concurrently`, `vite`. `npm audit` must report zero.
- **Everything under `src/` ships; nothing outside it does.** `data/`,
  `scripts/`, `styles/` and `legacy/` are inputs, not output.
- Tailwind output lands at `src/styles.css` (gitignored) so
  `<link href="/styles.css">` resolves identically in dev and in production.
- **Tailwind is v4** — the entry point is `@import "tailwindcss";` and there is
  no `tailwind.config.js`. Customization goes in `@theme`. Don't reintroduce v3's
  `@tailwind base/components/utilities` + `content` glob.
- **Google Fonts is a deliberate exception** to the lean-dependency rule: one
  `<link>` for Bebas Neue + Bodoni Moda, justified by brand fidelity. Don't add
  a second third-party origin.
- `CNAME` is load-bearing and is copied into `_site/` by the build.
- **`src/player.js` is the only JavaScript**, and it is progressive
  enhancement — see below.

## The player

`src/player.js` is the **shared archive player**, byte-identical (below the
header comment) to the one on `lostinsanity.net`, `blythe-band.com` and
`reachableheights.com`. Keep it that way: fix a bug here, port it there.

It expects these DOM hooks, so don't rename them:

```html
<div class="ep-list" data-playlist data-record="Season 1">
  <article
    class="ep track"
    data-src="<absolute blob URL>"
    data-title="Introduction"
    data-seconds="498"
  >
    <button class="track-btn">
      <svg class="i-play">…</svg><svg class="i-pause hidden">…</svg>
    </button>
    <span class="track-elapsed"></span>
    <div class="track-seek hidden"><div class="track-fill"></div></div>
  </article>
</div>
```

plus the sticky bar `#player` with `#pl-{title,record,play,prev,next,seek,cur,dur,close}`.

Rules:

- **`data-seconds` must match the printed duration.** It is what the bar shows
  before metadata loads. Both come from `dur_seconds()`, so they can't drift.
- Episodes are grouped into playlists by the nearest `[data-playlist]` ancestor;
  `data-record` on it is the label in the bar. **Auto-advance and prev/next stay
  inside one season** — finishing the last Season 1 episode does not roll into
  Season 2.
- Player styles live in `@layer components`. **Tailwind utilities always beat
  that layer regardless of specificity**, so a state rule like
  `.ep.is-active .ep-title` only works while the `<h3>` carries no competing
  utility class. Don't add `text-white` to it in the markup.
- `preload="none"` is intentional — nothing is fetched until a play button is
  pressed. On a 958 MB archive that matters.
- **The page degrades honestly without JavaScript.** Every episode keeps its
  `Download MP3` link, and a `<noscript>` block above the seasons says so. The
  page must never depend on JS to _reach_ content.

Before publishing, confirm every `data-src` resolves:

```sh
grep -o 'data-src="[^"]*"' _site/index.html | sed 's/data-src="//;s/"//' \
  | while read u; do echo "$(curl -sS -o /dev/null -w '%{http_code}' -I "$u") $u"; done
```

## Deploying

The Pages source must be set to Actions, not a branch:

```sh
gh api -X PUT /repos/brandonmartinez/theaverageenthusiasts/pages -f build_type=workflow
```

Push over the SSH remote (`git@github.com:...`); the HTTPS remote resolves to the
wrong GitHub account on the owner's machine.

## Known follow-ups

- The apex `theaverageenthusiasts.com` is still a NameCheap http-only URL
  redirect pointing at a Facebook page. It should become GitHub's four A records
  so apex → `www` works over HTTPS.
- `legacy/assets-feed.xml` has to be uploaded by hand — see `README.md`.
