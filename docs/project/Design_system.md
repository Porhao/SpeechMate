# Design System

SpeechMate follows the **Clay** design language. The full source spec, with SpeechMate's adaptations at the top, is [`frontend/DESIGN.md`](../../frontend/DESIGN.md). This page is the quick reference for building UI.

## Principles

1. **Warm and playful, never noisy.** Cream canvas, near-black ink, one saturated colour per card.
2. **Depth from clay, not chrome.** `.clay` shading, pointer tilt and three.js clay objects; no glassmorphism, no glow.
3. **Plain words first, detail on demand.** Every number has a one-line meaning; the method sits behind "Show how".
4. **Accessible by default.** AA contrast in both themes, keyboard paths, reduced motion respected.

## Tokens (`frontend/app/globals.css`)

| Group | Tokens | Notes |
|---|---|---|
| Surfaces | `--bg` `--surface` `--surface-2` `--surface-3` | Cream in light; teal-night in dark |
| Lines | `--line` `--line-2` `--line-strong` | Warm, never cool grey |
| Text | `--ink` `--ink-3` `--ink-2` `--muted` `--faint` | Contrast noted next to each |
| Action | `--accent` (fills, white text) · `--accent-ink` (links, accent text) | |
| Status | `--ok` `--warn` `--bad` | Always with an icon/label, never colour alone |
| Brand fills | `--pink` `--teal` `--lavender` `--peach` `--ochre` `--mint` | Same in both themes; text colour chosen per card |
| Text-safe brand | `--pink-ink` `--violet-ink` `--teal-ink` `--slate-ink` | Use `inkOf(color)` for text drawn in a brand colour |
| Radius | 12 px controls · 16 px cards · 24 px feature cards | `rounded-md` / `rounded-lg` / `rounded-xl` |
| Type | `.font-display` (Inter 600, −0.035em) for headlines; Inter for everything else | |

Never put a hex value in a component. If a colour is missing, add a token.

## Mode colours

| Function | Card fill | Session accent |
|---|---|---|
| Conversation | `--pink` | `#D6245F` |
| Interview | `--teal` | `#1A3A3A` |
| Presentation | `--lavender` | `#6B4FC4` |

## Components (`frontend/components/ui/kit.tsx`)

`PageHeader` (optional `art` slot) · `Card` · `Button` / `LinkButton` (primary, secondary, ghost) · `Field` + `inputClass`/`inputStyle` · `Notice` · `StatusBadge` · `ScoreBar` · `Dots` · `TiltCard`.

## 3D and motion

| Piece | Where | Rule |
|---|---|---|
| `.clay` | any saturated fill | inset light top, shade bottom, soft drop |
| `TiltCard` / `.tilt` | home feature cards | mouse/pen only |
| `ClayScene` (three.js) | page heroes via `ClayArt` (desktop only), nav logo (`variant="logo"`) | one WebGL context per use; disposed on unmount |
| `VoiceOrb` (three.js) | sign-in, session partner | reacts to voice |
| Page transition | `app/(app)/template.tsx` + "clay pop" CSS | View Transitions API; nav bar anchored |
| Nav | `.clay-nav`, `.nav-pill`, `.nav-pill-active` | lift on hover, press on click |
| Contact dock | `ContactDock` in the footer | keys magnify and flip to link icons |

Every animation stops under `prefers-reduced-motion`.

## Accessibility checklist

- [ ] Text uses text tokens; AA contrast in light **and** dark.
- [ ] Every control reachable by keyboard; visible focus (`--accent-ink` outline).
- [ ] Icons-only buttons have `aria-label`.
- [ ] Live changes (turn banner) use `role="status"` / `aria-live`.
- [ ] Charts: a table view and an `aria-label` summary.
- [ ] Works at 390 px wide with no horizontal scroll.
