Able Player Usage (Audio)

Overview
- This repo is wired to load Able Player assets only on pages that set `ableplayer: true` in front matter.
- Use a standard HTML5 `<audio>` element with the `data-able-player` attribute; Able Player upgrades it with accessible controls.

1) Enable Able Player on a page
- In the page’s front matter:

  ---
  layout: default
  title: My Audio Page
  ableplayer: true
  ---

2) Add an audio player
- Minimal example:

  <figure class="audio-player">
    <figcaption>Episode title or stream name</figcaption>
    <audio data-able-player preload="none">
      <source src="https://example.com/path/audio.mp3" type="audio/mpeg">
    </audio>
  </figure>

3) Provide multiple sources (optional)
- Add additional `<source>` elements so browsers can pick a supported format:

  <audio data-able-player preload="none">
    <source src=".../audio.mp3" type="audio/mpeg">
    <source src=".../audio.ogg" type="audio/ogg">
  </audio>

4) Add captions/transcript (recommended)
- Include a WebVTT track; Able Player will expose a transcript UI when captions are present:

  <audio data-able-player preload="none">
    <source src=".../audio.mp3" type="audio/mpeg">
    <track kind="captions" src="/assets/captions/ep1.vtt" srclang="en" label="English">
  </audio>

5) Fallback link (good practice)
- Provide a direct link if playback is blocked (e.g., HTTP audio on an HTTPS page):

  <p class="audio-fallback">
    Can’t play? Open the stream:
    <a href="http://stream.example.com/live">http://stream.example.com/live</a>
  </p>

Notes & gotchas
- Mixed content: Browsers may block HTTP audio when your site is served over HTTPS. Prefer HTTPS audio URLs if available; otherwise include a fallback link.
- jQuery: The page loader pulls jQuery and Able Player automatically when `ableplayer: true` is set.
- Multiple players: You can place multiple `<audio data-able-player>` elements on the same page; each will be upgraded.
- Styling: Use `<figure>` + `<figcaption>` to provide context. Able Player comes with default CSS; light tweaks can go in `assets/css/extra.css`.

Quick copy/paste block

<figure class="audio-player">
  <figcaption>Live Blind Hams Network audio stream</figcaption>
  <audio data-able-player preload="none">
    <source src="http://stream.borris.me:8888/blind-hams" type="audio/mpeg">
  </audio>
  <p class="audio-fallback" style="font-size:.9em;margin-top:.4rem">
    If playback fails, open the stream directly:
    <a href="http://stream.borris.me:8888/blind-hams">http://stream.borris.me:8888/blind-hams</a>.
  </p>
</figure>

