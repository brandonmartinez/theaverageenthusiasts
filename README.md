# theaverageenthusiasts.com

The archive of **The Average Enthusiasts** — a video game podcast by Brandon
Martinez and Kenny Graham, 38 episodes between September 2017 and October 2021.

One static page with the whole run on it, plus a living podcast feed so the show
stays subscribable.

- Site: <https://www.theaverageenthusiasts.com>
- Feed: <https://www.theaverageenthusiasts.com/feed/feed.xml>

## Working on it

```sh
npm install
npm run dev                  # local preview
python3 scripts/generate.py  # regenerate index + feeds from data/episodes.json
npm run build                # emits _site/
```

`src/index.html`, `src/feed/feed.xml`, `src/podcast/feed.xml`,
`legacy/assets-feed.xml` and `src/sitemap.xml` are all generated. Edit prose in
`scripts/generate.py`, episode data in `data/episodes.json`.

`src/feed/index.html` is hand-written and safe to edit directly.

Read [`AGENTS.md`](AGENTS.md) before changing the feeds. There are two contracts
in there (GUID stability and `<itunes:new-feed-url>` placement) that will break
every existing subscriber if you get them wrong.

## The one manual step: migrating the old feed

Existing subscribers point at the old Azure Blob feed:

```
http://assets.theaverageenthusiasts.com/podcast/feed.xml
```

`legacy/assets-feed.xml` is a drop-in replacement for that file. It carries the
same 38 episodes and the same GUIDs, plus `<itunes:new-feed-url>` pointing at the
new canonical feed — which is how Apple Podcasts, Overcast, Pocket Casts and the
rest permanently move a subscriber without them doing anything.

Upload it over the existing blob:

```sh
az storage blob upload \
  --account-name taestorage \
  --container-name podcast \
  --name feed.xml \
  --file legacy/assets-feed.xml \
  --content-type "text/xml" \
  --overwrite
```

Then confirm the move marker is live:

```sh
curl -s http://assets.theaverageenthusiasts.com/podcast/feed.xml | grep new-feed-url
```

**Do not delete the blob afterwards.** Apps only migrate when they next poll, and
the audio files in that same storage account are what every episode on the site
plays from.

## Audio

The MP3s are not in this repo — 958 MB would blow past GitHub Pages' 1 GB limit.
They stay in the `taestorage` Azure Storage account and are referenced over its
HTTPS endpoint. See the "Audio hosting" section of [`AGENTS.md`](AGENTS.md) for
why the pretty `assets.` hostname can't be used yet, and the one-line change to
switch back once it can.
