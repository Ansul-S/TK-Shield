---
version: alpha
name: Duna Light
description: A calm, airy editorial system with a dark core accent and generous whitespace.
colors:
  primary: "#222221"
  secondary: "#6C6A66"
  tertiary: "#8F8A83"
  neutral: "#F4F1EC"
  surface: "#FFFFFF"
  on-surface: "#222221"
  background: "#FFFFFF"
  text: "#222221"
  border: "#E5E7EB"
  muted: "#9A948B"
  accent-warm: "#F6C98D"
  accent-pink: "#EFC0CF"
  accent-sky: "#C8D8E8"
  error: "#D64545"
typography:
  headline-display:
    fontFamily: "GT America Regular"
    fontSize: "64px"
    fontWeight: 400
    lineHeight: 64px
    letterSpacing: "-3.84px"
  headline-lg:
    fontFamily: "GT America Regular"
    fontSize: "40px"
    fontWeight: 400
    lineHeight: 44px
    letterSpacing: "-2px"
  headline-md:
    fontFamily: "GT America Regular"
    fontSize: "36px"
    fontWeight: 400
    lineHeight: 43.2px
    letterSpacing: "-1.08px"
  headline-sm:
    fontFamily: "GT America Regular"
    fontSize: "28px"
    fontWeight: 400
    lineHeight: 33.6px
    letterSpacing: "-0.84px"
  body-lg:
    fontFamily: "GT America Regular"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: "0px"
  body-md:
    fontFamily: "GT America Regular"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 21px
    letterSpacing: "0px"
  body-sm:
    fontFamily: "GT America Regular"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 18px
    letterSpacing: "0px"
  label-lg:
    fontFamily: "GT America Regular"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: "0px"
  label-md:
    fontFamily: "GT America Regular"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 21px
    letterSpacing: "0px"
  label-sm:
    fontFamily: "GT America Regular"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 18px
    letterSpacing: "0px"
  nav-md:
    fontFamily: "GT America Regular"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: "0px"
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
  full: 9999px
spacing:
  xs: 6px
  sm: 16px
  md: 24px
  lg: 64px
  xl: 140px
  gutter: 24px
  section: 140px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
    height: "40px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    height: "40px"
  button-tertiary:
    backgroundColor: "transparent"
    textColor: "{colors.surface}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.none}"
    padding: "0px"
    height: "24px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: "12px 14px"
  chip:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.full}"
    padding: "6px 12px"
---
# Duna Light

## Overview
Duna feels serene, optimistic, and premium, with a soft editorial tone supported by a dramatic hero image and a restrained interface. The audience appears to be business buyers evaluating an AI-native onboarding platform, so the system balances trustworthiness with a slightly whimsical, aspirational visual mood. Spacious composition, simple navigation, and a single dominant dark accent keep the experience calm and focused.

## Colors
- **Primary (#222221):** A near-black ink used for core text, primary calls to action, and the strongest contrast moments. It anchors the otherwise airy page and keeps the brand feeling mature.
- **Surface (#FFFFFF):** The main canvas color for the page and cards. It allows the pastel imagery and dark typography to breathe.
- **Background (#FFFFFF):** Matching the surface tone, this reinforces the light, open layout and keeps large sections visually quiet.
- **Text (#222221):** The main reading color for headlines and body copy. It should remain highly legible against white and warm imagery.
- **Secondary (#6C6A66):** A softened neutral for supporting navigation or meta text when less emphasis is needed.
- **Tertiary (#8F8A83):** A warmer muted neutral that can be used for secondary hierarchy, subtle labels, or quiet UI states.
- **Border (#E5E7EB):** A very light divider color for cards, utility panels, and low-emphasis containers.
- **Muted (#9A948B):** Best for placeholder text, helper text, and subdued UI details.
- **Accent-warm (#F6C98D):** A warm sunset tint drawn from the hero art; useful as a contextual decorative accent rather than a core UI color.
- **Accent-pink (#EFC0CF):** A soft floral highlight that supports the dreamy illustration palette.
- **Accent-sky (#C8D8E8):** A cool atmospheric blue for balancing the warmer tones in background imagery and illustrations.
- **Error (#D64545):** Reserved for validation and destructive states; keep it visually isolated from the brand palette.

## Typography
Duna uses a single clean grotesk voice: GT America Regular. The overall system is light in weight and highly editorial, relying on scale and negative tracking rather than boldness for hierarchy. Headings use tight, deliberate letter spacing in large sizes, while body text stays relaxed and readable.

- **Headlines:** `headline-display`, `headline-lg`, `headline-md`, and `headline-sm` are all regular weight, with progressively smaller sizes and increasingly subtle negative letter spacing. They are intended for hero statements, section titles, and product messaging.
- **Body:** `body-lg`, `body-md`, and `body-sm` provide readable copy tiers. The default reading voice is calm and unobtrusive, with modest line heights and no special casing.
- **Labels and navigation:** `label-lg`, `label-md`, `label-sm`, and `nav-md` support buttons, nav links, chips, and utility text. Uppercase styling is not a dominant pattern in the screenshot; labels should remain sentence case unless a specific product context requires otherwise.
- **Tone:** Keep typographic contrast mostly in size and spacing, not in weight. Avoid heavy bold styles unless used for emphasis in content-rich areas.

## Layout
The layout is expansive and centered, with a strong hero-first composition that gives the artwork room to establish mood before the conversion content appears. Content blocks are spaced widely, using large vertical rhythm tokens (`lg` and `xl`) to preserve the premium, tranquil feel. Containers should generally sit on a broad, fluid grid with comfortable side padding rather than a dense fixed-max-width approach.

Section spacing is generous: use `section` or `xl` for major page transitions, `lg` for large gaps between hero elements and body content, and `md`/`sm` for tighter relationships like nav items or card internals. Cards and small utility surfaces should use `16px` padding to stay compact and restrained.

## Elevation & Depth
The system is intentionally flat. There are no visible shadows in the source; hierarchy comes from color contrast, whitespace, and the layering between imagery and white page content. Cards use a thin border and light surface separation instead of shadow-based depth, which keeps the interface crisp and editorial.

Because the page already contains a richly layered illustration, the UI chrome should remain subdued. Avoid heavy blur, drop shadows, and stacked elevation unless required for temporary overlays or menus.

## Shapes
The corner language is soft but disciplined. Primary buttons use a full pill shape, which gives the interface a friendly, approachable feel, while cards and inputs use small radii for structure. Overall, shapes should feel rounded enough to be welcoming but not so soft that they compete with the organic hero artwork.

Use `rounded.full` for major CTAs and chips, `rounded.sm` for inputs and secondary buttons, and `rounded.md` for cards and panels. Keep geometry simple and mostly rectangular elsewhere.

## Components
- **Primary button (`button-primary`):** Dark fill, white text, pill radius, and compact horizontal padding. This is the highest-emphasis action and should be used for conversion moments like “Get started” and “Schedule a demo.” Keep the height around `40px` and avoid oversized padding that would break the sleek feel.
- **Secondary button (`button-secondary`):** Transparent fill with dark text and a subtle outline or quiet contrast treatment. Use it for lower-emphasis actions when the layout needs an alternative to the primary CTA.
- **Tertiary button (`button-tertiary`):** Minimal text-only treatment for inline actions, navigation-like actions, or lightweight utility links.
- **Cards (`card`):** White background, thin border, and `16px` padding. Cards should feel like clean containers, not floating objects.
- **Inputs (`input`):** White fill, soft radius, comfortable internal padding, and dark text. Validation states should be clear but not loud; prefer border color changes over filled error backgrounds.
- **Chips (`chip`):** Pill-shaped status or announcement labels with dark fill and white text, matching the small hero announcement badge.
- **Navigation:** Use understated text links in the top bar with minimal visual chrome. The active or primary nav item should be indicated by placement or subtle contrast rather than decoration.
- **Cookie prompts and utility panels:** Keep them lightweight, white, and bordered, with rounded corners and compact internal spacing.

## Do's and Don'ts
- Do keep the interface spacious and let the hero imagery do much of the emotional work.
- Do use the dark primary color for the strongest actionable elements and headlines.
- Do preserve the light editorial tone by relying on whitespace and typography instead of shadow-heavy depth.
- Do keep corner radii modest on containers and fully rounded on pills and chips.
- Don't introduce loud saturated UI colors that compete with the illustration palette.
- Don't use bold weights or condensed styles for the main hierarchy; the system is intentionally regular-weight.
- Don't stack multiple elevated cards or heavy shadows to create hierarchy; use contrast and spacing instead.
- Don't crowd the layout with dense UI chrome or overly tight spacing around large headings.