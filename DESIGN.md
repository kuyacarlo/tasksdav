# TasksDAV Design System

Brand kit for product UI, docs, containers, and social. Keep this file authoritative; code tokens should match.

## Positioning

**One line:** Google Tasks, speaking CalDAV.

**Voice:** calm infra, not productivity-guru. Short sentences. No hype, no emoji spam.

**Feel:** dark forest console — a pipe you trust, not a pastel todo app.

---

## Logo

Files live in [`brand/`](./brand/):

| Asset | Use |
|-------|-----|
| `logo.svg` | Primary lockup (mark + wordmark) |
| `logo-mark.svg` | App icon / favicon / avatar |
| `logo-wordmark.svg` | Wordmark only (nav, docs headers) |
| `logo.png` | Raster export for README / social when SVG isn’t ideal |

### Mark

A rounded square “tray” with a checklist tick that resolves into a sync arc — task list meeting CalDAV sync. No Google colors; no purple glow.

### Wordmark

- **Tasks** in ink (`#E8F0EA`)
- **DAV** in accent (`#3DBA7A`)
- Type: **DM Sans** Bold, tracking `-0.04em`
- Never set the whole word in accent; never invert the split

### Clear space

Keep empty margin ≥ **¼ of mark height** on all sides. Don’t put the mark inside another colored circle unless using the provided mark (already has a tray).

### Minimum size

| Form | Min |
|------|-----|
| Mark only | 24×24 px |
| Full lockup | 120 px wide |
| Favicon | 32×32 (mark only) |

### Don’t

- Stretch or rotate the mark
- Recolor accent to Google blue / Material purple
- Add drop shadows, neon outlines, or glassmorphism
- Place on busy photography without a solid scrim

---

## Color

### Core tokens

| Token | Hex | Role |
|-------|-----|------|
| `--bg0` | `#0F1412` | Page / deepest surface |
| `--bg1` | `#1A2420` | Cards, panels |
| `--ink` | `#E8F0EA` | Primary text |
| `--muted` | `#8FA396` | Secondary text, labels |
| `--accent` | `#3DBA7A` | Brand action, DAV, focus |
| `--accent-dim` | `#2A7A52` | Pressed / darker accent |
| `--line` | `#2C3A33` | Borders, hairlines |
| `--warn` | `#E6B35A` | One-time secrets, caution |
| `--on-accent` | `#04140C` | Text on accent buttons |

### Atmosphere (background only)

```css
background:
  radial-gradient(1200px 600px at 10% -10%, #1E3D2F 0%, transparent 55%),
  radial-gradient(900px 500px at 100% 0%, #243028 0%, transparent 50%),
  var(--bg0);
```

### Light surface (docs / README only)

Rare. Prefer dark. If needed:

| Token | Hex |
|-------|-----|
| `--paper` | `#F3F6F4` |
| `--ink-on-paper` | `#14201A` |
| `--accent` | `#2A7A52` (use dim as primary on light) |

### Contrast rules

- Body text (`ink` on `bg0`) — default
- Labels use `muted`, never pure gray `#888`
- Buttons: `accent` fill + `on-accent` text
- Destructive isn’t in MVP; don’t invent red until needed

---

## Typography

| Role | Family | Weight | Notes |
|------|--------|--------|-------|
| UI / display | **DM Sans** | 400 / 600 / 700 | Optical size on; tracking tight on brand |
| Mono / credentials | **IBM Plex Mono** | 400 / 500 | CalDAV URLs, tokens, code |
| Fallback UI | `system-ui, sans-serif` | — | After DM Sans |
| Fallback mono | `ui-monospace, monospace` | — | After Plex |

### Scale (connect UI)

| Style | Size | Weight | Tracking |
|-------|------|--------|----------|
| Brand | `clamp(2.4rem, 6vw, 3.4rem)` | 700 | `-0.04em` |
| Lede | `1.05rem` | 400 | normal, line-height 1.5 |
| Body / status | `0.95–1rem` | 400 | — |
| Label | `0.75rem` | 400 | `0.06em`, uppercase |
| Mono field | `0.85rem` | 400–500 | — |
| Note | `0.9rem` | 400 | muted |

### Google Fonts import

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

---

## Shape & space

| Token | Value |
|-------|-------|
| Page max width | `40rem` |
| Card radius | `12px` |
| Control radius | `8px` |
| Card padding | `1.25rem 1.35rem` |
| Field padding | `0.7rem 0.8rem` |
| Stack gap | `0.6–1rem` |

Borders: `1px solid var(--line)`. Prefer border over shadow. No multi-layer shadows.

---

## Motion

Keep quiet.

| Moment | Motion |
|--------|--------|
| Button hover | `filter: brightness(1.05)` (~120ms) |
| Copy feedback | label text → “Copied” → revert (~1.2s) |
| Connect reveal | optional fade-in of card, ≤200ms opacity |

No ambient particle loops, no gradient animation on the hero.

---

## UI patterns (connect page)

1. **Brand first** — `Tasks` + accent `DAV` as the hero signal
2. One lede sentence
3. One card: Connect **or** credentials
4. Credentials: label → mono field → Copy
5. Warn styling only for one-time app password

Avoid: pill clusters, stat strips, badge stickers on the hero, nested cards.

---

## CSS variables snippet

```css
:root {
  --bg0: #0f1412;
  --bg1: #1a2420;
  --ink: #e8f0ea;
  --muted: #8fa396;
  --accent: #3dba7a;
  --accent-dim: #2a7a52;
  --line: #2c3a33;
  --warn: #e6b35a;
  --on-accent: #04140c;
  --radius-card: 12px;
  --radius-control: 8px;
  --font-sans: "DM Sans", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
}
```

---

## Social / OG

- Background: `--bg0` with soft green radials
- Center: `logo.svg` lockup
- Optional one line under: “Google Tasks → CalDAV”
- Size: 1200×630

---

## Related

- Product contract: [`SPEC.md`](./SPEC.md)
- Security / tenancy: [`docs/security.md`](./docs/security.md)
- Live UI tokens: [`frontend/index.html`](./frontend/index.html)
