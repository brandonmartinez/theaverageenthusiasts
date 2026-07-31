#!/usr/bin/env python3
"""Generate src/index.html, src/feed/feed.xml and the alias/legacy feeds.

Run from the repo root:  python3 scripts/generate.py

Everything factual comes from data/episodes.json, which was parsed once from the
show's own RSS feed (the original `feed.xml` off the Azure blob) plus the
per-episode `.txt` show-note files in the production archive. The editorial prose
lives in this file so the page can be regenerated without losing it.
"""

import html
import json
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.theaverageenthusiasts.com"
FEED_URL = f"{SITE}/feed/feed.xml"
OLD_FEED_URL = "http://assets.theaverageenthusiasts.com/podcast/feed.xml"
ALBUM_ART = f"{SITE}/images/albumcover.jpg"

# Where the MP3s are served from. `assets.theaverageenthusiasts.com` is an Azure
# Blob custom domain, and Blob custom domains get NO TLS certificate -- so an
# HTTPS page cannot load audio from that hostname (cert name mismatch) and a
# plain-http URL would be blocked as mixed content. Until `assets.` sits behind
# something that terminates TLS for it (Cloudflare proxy), point at the storage
# account's own HTTPS endpoint, which has a valid `*.blob.core.windows.net`
# cert. To switch back: set MEDIA_BASE to CANONICAL_MEDIA_BASE and re-run this
# script. Nothing else needs to change.
CANONICAL_MEDIA_BASE = "https://assets.theaverageenthusiasts.com/podcast"
MEDIA_BASE = "https://taestorage.blob.core.windows.net/podcast"

E = lambda s: html.escape(s or "", quote=True)


def load():
    with open(os.path.join(ROOT, "data", "episodes.json"), encoding="utf-8") as f:
        eps = json.load(f)
    for e in eps:
        e["audio"] = f"{MEDIA_BASE}/{e['audio'].rsplit('/', 1)[-1]}"
    return eps


# ── seasons ──────────────────────────────────────────────────────────────────
# Episode 027 is literally titled "Season 2!"; 036 and 037 arrive after the show
# had already stopped, so they get their own group rather than pretending the
# run was continuous.
SEASONS = [
    {
        "id": "season-1",
        "label": "Season 1",
        "range": (0, 26),
        "dates": "September 2017 – September 2018",
        "blurb": (
            "Twenty-seven episodes in twelve months, starting weekly and drifting "
            "monthly. Consumer tech and Nintendo at first, then whatever the two "
            "of them were actually arguing about that week."
        ),
    },
    {
        "id": "season-2",
        "label": "Season 2",
        "range": (27, 35),
        "dates": "January 2019 – March 2020",
        "blurb": (
            "A restart after a four-month gap, with new cover art for every "
            "episode and longer, looser conversations. It ends on "
            "<em>Wash Your Hands!</em>, recorded the week the world shut down."
        ),
    },
    {
        "id": "after",
        "label": "After",
        "range": (36, 99),
        "dates": "April 2021 – October 2021",
        "blurb": (
            "Two episodes, eighteen months apart, from a show that had already "
            "stopped. The second one is the last one."
        ),
    },
]

PRETTY_DATE = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%B %-d, %Y")


def dur_seconds(dur):
    """Durations in the original feed are MM:SS (and occasionally HH:MM:SS)."""
    parts = [int(p) for p in dur.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def mmss(dur):
    total = dur_seconds(dur)
    h, rem = divmod(total, 3600)
    m = rem // 60
    return f"{h}h {m}m" if h else f"{m} min"


def episode_html(e):
    if e["art"]:
        art = f"""
          <img
            src="{e['art']}"
            alt="Title card for {E(e['title'])}"
            width="1000"
            height="563"
            loading="lazy"
            decoding="async"
            class="w-full rounded-sm border border-white/10 bg-black/20"
          />"""
    else:
        art = f"""
          <div class="ep-noart" aria-hidden="true">
            <span>{e['num']:03d}</span>
            <p>no title card</p>
          </div>"""
    links = ""
    if e["links"]:
        items = "\n".join(
            f'              <li><a href="{E(l["url"])}" rel="noopener nofollow">{E(l["label"])}</a></li>'
            for l in e["links"]
        )
        links = f"""
          <details class="notes">
            <summary>Links mentioned ({len(e['links'])})</summary>
            <ul>
{items}
            </ul>
            <p class="note-caveat">
              Short links from the original show notes. They still redirect; what
              they redirect <em>to</em> is another matter.
            </p>
          </details>"""
    mb = f"{e['bytes'] / 1_048_576:.0f}&nbsp;MB"
    return f"""
      <article id="{e['slug']}" class="ep">
        <div class="ep-art">{art}
        </div>
        <div class="ep-body">
          <p class="ep-meta">
            <span class="ep-num">{e['num']:03d}</span>
            <time datetime="{e['date']}">{PRETTY_DATE(e['date'])}</time>
            <span aria-hidden="true">&middot;</span>
            <span>{mmss(e['duration'])}</span>
          </p>
          <h3 class="ep-title">{E(e['short'])}</h3>
          <p class="ep-desc">{E(e['desc'])}</p>
          <audio controls preload="none" src="{E(e['audio'])}"></audio>
          <p class="ep-dl">
            <a href="{E(e['audio'])}" download>Download MP3</a>
            <span aria-hidden="true">&middot;</span>
            <span>{mb}</span>
          </p>{links}
        </div>
      </article>"""


def build_index(eps):
    sections = []
    nav = []
    for s in SEASONS:
        lo, hi = s["range"]
        group = [e for e in eps if lo <= e["num"] <= hi]
        if not group:
            continue
        nav.append(
            f'<a href="#{s["id"]}">{s["label"]} <span class="nav-sub">{len(group)} episodes</span></a>'
        )
        body = "\n".join(episode_html(e) for e in group)
        sections.append(
            f"""
    <section id="{s['id']}" class="season">
      <div class="wrap">
        <div class="season-head">
          <h2 class="section-h">{s['label']}</h2>
          <p class="season-dates">{s['dates']}</p>
          <p class="season-blurb">{s['blurb']}</p>
        </div>
        <div class="ep-list">
{body}
        </div>
      </div>
    </section>"""
        )

    total_min = sum(dur_seconds(e["duration"]) for e in eps) // 60
    hours, mins = divmod(total_min, 60)

    return TEMPLATE.format(
        nav="\n          ".join(nav),
        sections="\n".join(sections),
        count=len(eps),
        hours=hours,
        mins=mins,
        first=PRETTY_DATE(eps[0]["date"]),
        last=PRETTY_DATE(eps[-1]["date"]),
        feed=FEED_URL,
        year=datetime.now().year,
    )


TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>
      The Average Enthusiasts &mdash; an archive &middot; a podcast, 2017&ndash;2021
    </title>
    <meta
      name="description"
      content="The complete archive of The Average Enthusiasts, a podcast by Brandon Martinez and Kenny Graham. {count} episodes, September 2017 to October 2021. Every episode still plays."
    />
    <link rel="canonical" href="https://www.theaverageenthusiasts.com/" />
    <link rel="icon" href="/images/mark.svg" />
    <link rel="apple-touch-icon" href="/images/albumcover.jpg" />
    <link
      rel="alternate"
      type="application/rss+xml"
      title="The Average Enthusiasts"
      href="{feed}"
    />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Bodoni+Moda:opsz,wght@6..96,400;6..96,500&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="/styles.css" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="The Average Enthusiasts" />
    <meta property="og:title" content="The Average Enthusiasts &mdash; an archive" />
    <meta
      property="og:description"
      content="We're not great at anything, but we're enthusiastic about a lot. {count} episodes, 2017&ndash;2021, complete and still playable."
    />
    <meta
      property="og:image"
      content="https://www.theaverageenthusiasts.com/images/albumcover.jpg"
    />
    <meta property="og:url" content="https://www.theaverageenthusiasts.com/" />
    <meta name="twitter:card" content="summary_large_image" />
  </head>

  <body class="antialiased">
    <!-- ── archive banner ──────────────────────────────────────────────── -->
    <div class="banner">
      <div class="wrap flex flex-col gap-1 py-3 sm:flex-row sm:items-baseline sm:gap-4">
        <p class="banner-tag">Archive</p>
        <p class="banner-text">
          The Average Enthusiasts ended in October 2021. No new episodes are
          coming, no email is monitored, and the social accounts are dormant. All
          {count} episodes are below and every one of them still plays.
        </p>
      </div>
    </div>

    <!-- ── hero ───────────────────────────────────────────────────────── -->
    <header class="hero">
      <div class="wrap py-12 sm:py-16">
          <img
            src="/images/wordmark.svg"
            alt="The Average Enthusiasts"
            width="500"
            height="326"
            class="w-full max-w-md"
          />
          <p class="tagline">
            We&rsquo;re not great at anything, but we&rsquo;re enthusiastic about
            a lot!
          </p>
          <dl class="stats">
            <div><dt>Episodes</dt><dd>{count}</dd></div>
            <div><dt>Run</dt><dd>2017&ndash;2021</dd></div>
            <div><dt>Runtime</dt><dd>{hours}h {mins}m</dd></div>
            <div><dt>Hosts</dt><dd>2</dd></div>
          </dl>
      </div>
    </header>

    <!-- ── feed strip ─────────────────────────────────────────────────── -->
    <div class="feedstrip">
      <div class="wrap py-5">
        <p class="feedstrip-lede">
          <strong>The feed still works.</strong> If it&rsquo;s in your podcast app
          from years ago, leave it &mdash; nothing needs to change. If you want to
          add it now, point your app at:
        </p>
        <p class="feedurl"><code>{feed}</code></p>
        <p class="feedstrip-note">
          <a href="/feed/">What happened to the old feed URL?</a>
        </p>
      </div>
    </div>

    <!-- ── story ──────────────────────────────────────────────────────── -->
    <section id="story" class="story">
      <div class="wrap">
        <h2 class="section-h">What this was</h2>
        <div class="prose-archive">
          <p>
            Two friends with microphones and no particular qualifications. That
            was the whole premise, and the name said it out loud before the first
            episode did.
          </p>
          <p>
            Brandon Martinez and Kenny Graham recorded the introduction on a
            Sunday in September 2017 and had it approved and live in the podcast
            directories two days later. Brandon announced it on his blog that
            week:
          </p>
          <blockquote>
            <p>
              &ldquo;The Average Enthusiasts are Kenny Graham and myself. The
              general topics of the podcast are anything from consumer tech to
              gaming, with potential of things like cooking, photography, family,
              and more.&rdquo;
            </p>
            <footer>
              &mdash; brandonmartinez.com, September&nbsp;20,&nbsp;2017
            </footer>
          </blockquote>
          <p>
            What actually happened was broader than that list and better for it.
            The iPhone X and the Nintendo Switch got their due, but so did
            nostalgia for the 90s, weird food, MoviePass (twice &mdash; the second
            time angrily), camping, wedding planning, getting a dog, and a running
            argument about whether anybody should be allowed to talk during a
            movie.
          </p>
          <p>
            Season&nbsp;1 ran from September&nbsp;2017 to September&nbsp;2018 and
            stopped on an anniversary episode. Season&nbsp;2 restarted in
            January&nbsp;2019 with proper cover art for every episode and longer,
            looser conversations. It made it to March&nbsp;2020 and
            <em>Wash Your Hands!</em>, which was recorded as a joke about a
            precaution and aged into a period piece within a fortnight.
          </p>
          <p>
            Two more episodes followed &mdash; a pandemic catch-up in
            April&nbsp;2021 and one about money in October&nbsp;2021. Nobody
            announced an ending. Shows like this rarely get one; they just stop
            being the next thing on the list. The last episode went up on
            {last}.
          </p>
          <p>
            It ran {hours} hours and {mins} minutes in total, which is a long time
            to be enthusiastic about nothing in particular.
          </p>
        </div>
      </div>
    </section>

    <!-- ── hosts ──────────────────────────────────────────────────────── -->
    <section id="hosts" class="hosts">
      <div class="wrap">
        <h2 class="section-h">The enthusiasts</h2>
        <div class="host-grid">
          <div class="host">
            <img
              src="/images/bios/brandon.jpg"
              alt="Brandon Martinez"
              width="480"
              height="480"
              loading="lazy"
            />
            <div>
              <h3>Brandon Martinez</h3>
              <p>
                Co-host, and the one who did the editing &mdash; the cuts, the
                artwork, the feed, and the complaining about breathing noises.
              </p>
            </div>
          </div>
          <div class="host">
            <img
              src="/images/bios/kenny.jpg"
              alt="Kenny Graham"
              width="480"
              height="480"
              loading="lazy"
            />
            <div>
              <h3>Kenny Graham</h3>
              <p>
                Co-host, and the one who kept pushing for structure: weekly
                installments, segments, topics, a plan. Roughly half of it stuck.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── episode nav ────────────────────────────────────────────────── -->
    <nav class="epnav" aria-label="Episodes">
      <div class="wrap">
        <p class="epnav-label">All {count} episodes</p>
        <div class="epnav-links">
          {nav}
        </div>
      </div>
    </nav>
{sections}

    <!-- ── colophon ───────────────────────────────────────────────────── -->
    <section id="colophon" class="colophon">
      <div class="wrap">
        <h2 class="section-h">About this page</h2>
        <div class="prose-archive">
          <p>
            This is an archive, built from the show&rsquo;s own material. Every
            episode title, description, date, duration and audio file here came
            out of the podcast&rsquo;s original RSS feed; the &ldquo;links
            mentioned&rdquo; lists came from the show-note files written at the
            time. The title cards are the ones that shipped with the episodes.
            Nothing has been rewritten, and nothing has been added to make the run
            look tidier than it was.
          </p>
          <p>
            The audio is served from where it has always been served from, so old
            links and old feeds keep resolving. The feed itself now lives
            <a href="{feed}">at <code>/feed/feed.xml</code> on this domain</a>;
            the original feed URL still answers and still points subscribers
            here.
          </p>
          <p>
            Fifteen of the earliest episodes have no title card, because there
            weren&rsquo;t any until episode&nbsp;015. That gap is left as it is.
          </p>
        </div>
      </div>
    </section>

    <footer class="foot">
      <div class="wrap">
        <img src="/images/mark.svg" alt="" width="44" height="44" aria-hidden="true" />
        <p>
          The Average Enthusiasts &middot; {first} &ndash; {last}<br />
          Brandon Martinez &amp; Kenny Graham
        </p>
        <p class="foot-links">
          <a href="{feed}">RSS feed</a>
          <span aria-hidden="true">&middot;</span>
          <a href="/feed/">Subscribe</a>
          <span aria-hidden="true">&middot;</span>
          <a href="#story">The story</a>
        </p>
        <p class="foot-fine">
          &copy; 2021 The Average Enthusiasts. Archived {year}.
        </p>
      </div>
    </footer>
  </body>
</html>
"""


# ── feeds ────────────────────────────────────────────────────────────────────

CDATA = lambda s: "<![CDATA[" + (s or "").replace("]]>", "]]&gt;") + "]]>"


def items_xml(eps):
    out = []
    for e in sorted(eps, key=lambda x: -x["num"]):
        art = f'\n      <itunes:image href="{SITE}{e["art"]}"/>' if e["art"] else ""
        out.append(
            f"""    <item>
      <title>{CDATA(e['title'])}</title>
      <description>{CDATA(e['desc'])}</description>
      <link>{SITE}/#{e['slug']}</link>
      <guid isPermaLink="false">{e['guid']}</guid>
      <dc:creator>{CDATA('The Average Enthusiasts')}</dc:creator>
      <pubDate>{e['pubDate']}</pubDate>
      <enclosure url="{e['audio']}" length="{e['bytes']}" type="audio/mpeg"/>
      <itunes:author>The Average Enthusiasts</itunes:author>
      <itunes:summary>{E(e['desc'])}</itunes:summary>
      <itunes:explicit>false</itunes:explicit>
      <itunes:duration>{e['duration']}</itunes:duration>
      <itunes:episode>{e['num']}</itunes:episode>{art}
    </item>"""
        )
    return "\n".join(out)


def channel_xml(eps, self_url, new_feed_url=None, extra_link=None):
    """A complete channel. `new_feed_url` emits <itunes:new-feed-url>, which is
    how Apple Podcasts is told a feed has permanently moved."""
    moved = (
        f"\n    <itunes:new-feed-url>{new_feed_url}</itunes:new-feed-url>"
        if new_feed_url
        else ""
    )
    built = format_datetime(datetime.now(timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{CDATA('The Average Enthusiasts')}</title>
    <description>{CDATA("We're not great at anything, but we're enthusiastic about a lot! A podcast by Brandon Martinez and Kenny Graham, 2017-2021. The show has ended; the complete archive of all 38 episodes lives at " + SITE + " .")}</description>
    <link>{SITE}/</link>
    <image>
      <url>{ALBUM_ART}</url>
      <title>The Average Enthusiasts</title>
      <link>{SITE}/</link>
    </image>
    <atom:link href="{self_url}" rel="self" type="application/rss+xml"/>{extra_link or ''}{moved}
    <lastBuildDate>{built}</lastBuildDate>
    <pubDate>{eps[-1]['pubDate']}</pubDate>
    <author>{CDATA('The Average Enthusiasts')}</author>
    <copyright>{CDATA('2021 The Average Enthusiasts')}</copyright>
    <language>en</language>
    <generator>hand-rolled, from the archive</generator>
    <itunes:author>The Average Enthusiasts</itunes:author>
    <itunes:summary>We're not great at anything, but we're enthusiastic about a lot! A podcast by Brandon Martinez and Kenny Graham, 2017-2021. The show has ended.</itunes:summary>
    <itunes:type>episodic</itunes:type>
    <itunes:complete>yes</itunes:complete>
    <itunes:owner>
      <itunes:name>The Average Enthusiasts</itunes:name>
      <itunes:email>contact@theaverageenthusiasts.com</itunes:email>
    </itunes:owner>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="Leisure">
      <itunes:category text="Games"/>
      <itunes:category text="Hobbies"/>
      <itunes:category text="Video Games"/>
    </itunes:category>
    <itunes:image href="{ALBUM_ART}"/>
{items_xml(eps)}
  </channel>
</rss>
"""


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  wrote {path}  ({len(text):,} bytes)")


def main():
    eps = load()
    print(f"generating from {len(eps)} episodes")

    write("src/index.html", build_index(eps))

    # Canonical feed.
    write("src/feed/feed.xml", channel_xml(eps, FEED_URL))
    # Alias at the historic path shape, so /podcast/feed.xml resolves here too.
    write("src/podcast/feed.xml", channel_xml(eps, f"{SITE}/podcast/feed.xml"))
    # The replacement for the file sitting on the Azure blob: same episodes, but
    # it tells podcast clients the feed has permanently moved.
    write(
        "legacy/assets-feed.xml",
        channel_xml(eps, OLD_FEED_URL, new_feed_url=FEED_URL),
    )

    # Sitemap.
    urls = "\n".join(
        f"  <url><loc>{SITE}/{p}</loc></url>" for p in ("", "feed/")
    )
    write(
        "src/sitemap.xml",
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
    )


if __name__ == "__main__":
    main()
