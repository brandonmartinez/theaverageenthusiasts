/* Archive audio player: one <audio>, per-season playlists, sticky now-playing bar.
   Shared with lostinsanity.net, blythe-band.com and reachableheights.com --
   keep the DOM hooks (article.track, .track-btn, .track-seek, .track-fill,
   .track-elapsed, [data-playlist]/data-record) identical across all four. */
(function () {
  const bar = document.getElementById('player');
  if (!bar) return;

  const audio = new Audio();
  audio.preload = 'none';

  const el = (id) => document.getElementById(id);
  const ui = {
    title: el('pl-title'),
    record: el('pl-record'),
    play: el('pl-play'),
    prev: el('pl-prev'),
    next: el('pl-next'),
    seek: el('pl-seek'),
    cur: el('pl-cur'),
    dur: el('pl-dur'),
    close: el('pl-close'),
  };

  const tracks = Array.from(document.querySelectorAll('article.track')).map((node, i) => ({
    i,
    node,
    src: node.dataset.src,
    title: node.dataset.title,
    seconds: Number(node.dataset.seconds) || 0,
    record: node.closest('[data-playlist]')?.dataset.record || '',
  }));
  if (!tracks.length) return;

  let current = null;

  const fmt = (s) => {
    if (!isFinite(s) || s < 0) s = 0;
    const m = Math.floor(s / 60);
    return m + ':' + String(Math.floor(s % 60)).padStart(2, '0');
  };

  const siblings = (t) => tracks.filter((x) => x.record === t.record);

  function paint() {
    tracks.forEach((t) => {
      const on = current && t.i === current.i;
      t.node.classList.toggle('is-active', !!on);
      t.node.querySelector('.track-seek').classList.toggle('hidden', !on);
      const playing = on && !audio.paused;
      t.node.querySelector('.i-play').classList.toggle('hidden', playing);
      t.node.querySelector('.i-pause').classList.toggle('hidden', !playing);
      t.node.querySelector('.track-btn').setAttribute(
        'aria-label',
        (playing ? 'Pause ' : 'Play ') + t.title
      );
    });
    ui.play.querySelector('.i-play').classList.toggle('hidden', !audio.paused);
    ui.play.querySelector('.i-pause').classList.toggle('hidden', audio.paused);
    ui.play.setAttribute('aria-label', audio.paused ? 'Play' : 'Pause');
  }

  function show() {
    bar.classList.remove('translate-y-full');
    bar.removeAttribute('aria-hidden');
    document.body.classList.add('has-player');
  }

  function load(t, autoplay) {
    current = t;
    audio.src = t.src;
    ui.title.textContent = t.title;
    ui.record.textContent = t.record;
    ui.dur.textContent = fmt(t.seconds);
    ui.cur.textContent = '0:00';
    ui.seek.value = 0;
    ui.seek.style.setProperty('--pct', '0%');
    show();
    if (autoplay) audio.play().catch(() => {});
    paint();
  }

  function toggle(t) {
    if (current && current.i === t.i) {
      audio.paused ? audio.play().catch(() => {}) : audio.pause();
    } else {
      load(t, true);
    }
  }

  function step(delta) {
    if (!current) return;
    const list = siblings(current);
    const at = list.findIndex((x) => x.i === current.i);
    const nxt = list[at + delta];
    if (nxt) load(nxt, true);
  }

  tracks.forEach((t) => {
    t.node.querySelector('.track-btn').addEventListener('click', () => toggle(t));
  });

  audio.addEventListener('timeupdate', () => {
    const total = audio.duration || (current && current.seconds) || 0;
    const pct = total ? (audio.currentTime / total) * 100 : 0;
    ui.cur.textContent = fmt(audio.currentTime);
    if (!ui.seek.matches(':active')) ui.seek.value = String(pct);
    ui.seek.style.setProperty('--pct', pct + '%');
    if (current) {
      const fill = current.node.querySelector('.track-fill');
      if (fill) fill.style.width = pct + '%';
      const e = current.node.querySelector('.track-elapsed');
      if (e) e.textContent = fmt(audio.currentTime) + ' / ';
    }
  });

  audio.addEventListener('loadedmetadata', () => {
    if (isFinite(audio.duration)) ui.dur.textContent = fmt(audio.duration);
  });
  audio.addEventListener('play', paint);
  audio.addEventListener('pause', paint);
  audio.addEventListener('ended', () => {
    const list = siblings(current);
    const at = list.findIndex((x) => x.i === current.i);
    if (list[at + 1]) load(list[at + 1], true);
    else paint();
  });
  audio.addEventListener('error', () => {
    ui.title.textContent = 'Could not load ' + (current ? current.title : 'track');
  });

  ui.play.addEventListener('click', () => {
    if (!current) return load(tracks[0], true);
    audio.paused ? audio.play().catch(() => {}) : audio.pause();
  });
  ui.prev.addEventListener('click', () => {
    if (audio.currentTime > 3) audio.currentTime = 0;
    else step(-1);
  });
  ui.next.addEventListener('click', () => step(1));
  ui.seek.addEventListener('input', () => {
    const total = audio.duration || (current && current.seconds) || 0;
    if (total) audio.currentTime = (Number(ui.seek.value) / 100) * total;
    ui.seek.style.setProperty('--pct', ui.seek.value + '%');
  });
  ui.close.addEventListener('click', () => {
    audio.pause();
    bar.classList.add('translate-y-full');
    bar.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('has-player');
    current = null;
    paint();
  });

  document.addEventListener('keydown', (e) => {
    if (!current) return;
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
    if (e.code === 'Space') {
      e.preventDefault();
      audio.paused ? audio.play().catch(() => {}) : audio.pause();
    } else if (e.code === 'ArrowRight') {
      audio.currentTime = Math.min(audio.currentTime + 5, audio.duration || 1e9);
    } else if (e.code === 'ArrowLeft') {
      audio.currentTime = Math.max(audio.currentTime - 5, 0);
    }
  });
})();
