# Design tokens

Direction: mission control meets scientific journal. Calm, dense but legible, precise.
Tokens live in `web/app/globals.css`; dark is the default, light follows the OS or `data-theme`.

## Surfaces
| Token | Dark | Light |
|---|---|---|
| `--bg` | `#0b0f14` | `#f6f7f9` |
| `--panel` | `#11171e` | `#ffffff` |
| `--raised` | `#1a222c` | `#eef1f5` |
| `--border` | `rgba(255,255,255,.08)` | `rgba(11,15,20,.10)` |

Radius 10-12 px, 8 pt spacing grid, hairline borders.

## Colour roles (Okabe-Ito based)
- MODIS: amber `--modis`
- VIIRS: sky blue `--viirs`
- Harmonized: violet `--harmonized`
- Anomaly high: red `--anomaly-high`; anomaly low: steel blue `--anomaly-low`
- Heat ramps: perceptual inferno/magma only, never rainbow.

## Type
Inter for UI, JetBrains Mono for numbers and coordinates. Numerals are tabular (`.num`).
Two weights per view at most.

## Accessibility
- Minimum 44 px touch targets (`min-h-11`, `size-11`).
- Visible focus ring on every interactive element (`--focus`).
- `prefers-reduced-motion` collapses animation; motion is 150-250 ms ease-out.
- Text colours target WCAG AA on their surface.

## Components (`web/components/ui`)
Panel, Stat, SensorBadge, ChartFrame (loading / empty / error states), MetricPill, Tooltip, Drawer.

## Relation to Apple HIG
HIG principles (clarity, deference, semantic colour, light/dark, 44 px targets, reduced motion) are
applied. Where this file differs from HIG defaults (Inter instead of SF, fixed dark-first palette),
this design system wins because the product brief asks for it.
