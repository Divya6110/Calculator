---
name: tezzart-cinematic
description: TEZZART's cinematic short-video style for art reels (murals, sketches, paintings). Turns photos/clips of an artwork into a 9:16 storytelling film on a music track - eased camera moves, film grade, trailer titles that slam in on the beat, letterbox title cards, a big reveal on the drop, and the TEZZART logo end card with "PRESENTED BY". Use whenever TEZZART asks to edit, make, or redo a video, reel, short or story in "my style", "cinematic", "like the Luffy video", or for any art progress / time-lapse / reveal video.
---

# TEZZART cinematic edit

The approved reference is the Luffy wall-mural film (`examples/luffy_mural.json`). Match its feel unless the user asks otherwise.

## Brand rules (always)
- The name is **TEZZART**. Double Z, never "Teezart" or "Tezart".
- End card: `assets/tezzart_logo.png`, full frame, ungraded so the brand colours stay true, with **"PRESENTED BY"** rising in above it (or "ART BY" if the user asks).
- Only use **the user's own artwork and footage**. Never put the TEZZART credit on someone else's art. If a source video or drawing is from another creator, say so and leave it out.
- Don't download copyrighted anime or film footage, characters or scenery from the web. For an atmospheric opening, use the procedural `village` scene (`scripts/village.py`) or build a new original one in the same way.
- Music: reusing a trending track is the user's call. Mention that adding it in-app (Reels/TikTok sound library) is the safer route.

## The look (what the user approved)
- **Story arc:** atmospheric opening → blank wall/paper → sketch details → first paint → stage dissolves → **complete artwork revealed on the drop** → quick beat cuts across the stages → pull back to the full artwork → logo end card.
- **Titles: trailer style, Bebas Neue, brushed-silver fill.** Big words **slam** on audible hits: they scale down from 1.45x with motion blur, then a red/cyan split settles, a small camera shake and white flash hit, and a shine sweeps across the letters. Small words **rise** out of a blur. Text sits centred, with letterbox bars and a soft darkening during title cards.
  - The user rejected thin elegant serif titles ("not cinematic").
  - The user also rejected the heavier variant with light-ray bursts, shockwave rings, sparks, glitch slices and decode text ("before video text only good"). Keep titles at the level in `cinematic_render.py`.
- **Grade:** gentle S-curve, lifted film blacks, cool shadows and warm highlights, vignette, fine grain. Mild flashes on cuts and hits, and a warm light leak drifting across the reveal.
- **No people in frame** when the user asks for it. Build the film from photos of the artwork with camera moves (Ken Burns) instead of clips of the artist.
- **Clean the photos.** Remove stickers, captions, date text and app overlays (see "Cleaning photos" below).

## Workflow
1. **Inventory:** `ffprobe` the clips and check each photo's upright size (`ImageOps.exif_transpose`; phone photos are often stored sideways). Make contact sheets and look at them. Note any stickers or text to remove, and any people.
2. **Audio map:** `python3 -I scripts/beats.py <track>`. Put title **slams on `onsets`** (audible hits), cuts on beats, and the **reveal on the drop** (where loudness jumps and onsets get dense).
3. **Propose the plan** (a shot table and the title wording) and wait for the user to confirm.
4. **Write `project.json`** in the user's video folder (copy `examples/luffy_mural.json`), with `shots`, `titles`, `cards`, `flashes`, `light_leak` and `end_card`.
   - Camera moves are `[centre_x, centre_y, width]` in source pixels. The 9:16 window is clamped inside the image automatically.
   - Overlapping shots cross-dissolve.
5. **Preview the key moments** before the full render:
   `python3 -I scripts/cinematic_render.py project.json preview_dir --preview 0.5,2.6,9.95,13.4,19.5`
   Look at every frame: words not cut off, text readable, nothing unwanted left in frame.
6. **Render:** `python3 -I scripts/cinematic_render.py project.json out.mp4` (about 3–4 min for 20s at 1080×1920).
7. **Verify, then deliver:** check the frame count and duration with `ffprobe`, and loudness with `ffmpeg -i out.mp4 -af ebur128=peak=true -f null -` (audio is stream-copied, so it should match the source). Sample frames at every cut. Then send the file and remind the user the session folder is temporary.

## project.json reference
| key | meaning |
|---|---|
| `size`, `fps`, `duration` | output; duration usually = audio length |
| `audio` | file whose audio track is copied unchanged |
| `sources.<name>` | `{"type":"photo","path":…}`, `{"type":"video","path":…}` (shot gets `"in"` seconds), `{"type":"scene","module":"village"}`; add `"grade": false` to keep original colours |
| `shots[]` | `src`, `start`, `end`, `from`/`to` camera `[cx, cy, w]` (eased) |
| `titles[]` | `style` `slam`/`rise`, `text`, `size`, `in`, `out`, `y`, optional `track`, `strength` (shake 0–1.3); `parts:[{text,in},…]` puts words of one line on separate hits |
| `cards` | `[start,end]` windows for letterbox bars + darkening |
| `flashes` | `[time, amount, decay_s]` white flashes (hits, cuts, reveal) |
| `light_leak` | `[start,end]` warm leak drifting across (use on the reveal) |
| `end_card` | `text`, `text_in`, `text_y`, `text_size` (logo shot itself goes in `shots`) |
| `font`, `title_max_width`, `letterbox`, `fade_in`, `fade_out` | optional overrides |

Paths are relative to the JSON. `@skill/…` points inside this skill.

## Cleaning photos
- **Captions or stickers on a plain wall:** `python3 -I scripts/remove_regions.py in.jpg out.jpg x0,y0,x1,y1 [--text]`. Use `--text` for thin caption lettering.
- **Big stickers over structured areas** (door frames, outlines, skin): inpainting smears. Clone texture from right next to the area instead, align any straight outlines by measuring their slope, and redraw thin lines. `examples/clean_sticker_example.py` is the worked version that removed a cartoon sticker from the Luffy mural photo. Always check a zoomed crop of the seam.
- Or simply frame the camera window to avoid the sticker.

## Setup
`ffmpeg`/`ffprobe` on PATH; `pip install numpy pillow` (renderer), `librosa` (beats), `opencv-python-headless` (cleanup).

Fonts: Bebas Neue is bundled (OFL). Other Google fonts can be fetched with `npm pack @fontsource/<name>`, then converting the `.woff` to `.ttf` with fontTools.

The general-purpose `video-use` skill (transcripts, talking-head cuts, subtitles) lives next to this one. Use it for speech-driven edits, and this skill for art reels.
