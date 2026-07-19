---
name: Cyber Atelier
colors:
  surface: '#131314'
  surface-dim: '#131314'
  surface-bright: '#3a393a'
  surface-container-lowest: '#0e0e0f'
  surface-container-low: '#1c1b1c'
  surface-container: '#201f20'
  surface-container-high: '#2a2a2b'
  surface-container-highest: '#353436'
  on-surface: '#e5e2e3'
  on-surface-variant: '#cbc3d7'
  inverse-surface: '#e5e2e3'
  inverse-on-surface: '#313031'
  outline: '#958ea0'
  outline-variant: '#494454'
  surface-tint: '#d0bcff'
  primary: '#d0bcff'
  on-primary: '#3c0091'
  primary-container: '#a078ff'
  on-primary-container: '#340080'
  inverse-primary: '#6d3bd7'
  secondary: '#c8c5ca'
  on-secondary: '#303033'
  secondary-container: '#47464a'
  on-secondary-container: '#b6b4b8'
  tertiary: '#ffb869'
  on-tertiary: '#482900'
  tertiary-container: '#ca801e'
  on-tertiary-container: '#3f2300'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e9ddff'
  primary-fixed-dim: '#d0bcff'
  on-primary-fixed: '#23005c'
  on-primary-fixed-variant: '#5516be'
  secondary-fixed: '#e4e1e6'
  secondary-fixed-dim: '#c8c5ca'
  on-secondary-fixed: '#1b1b1e'
  on-secondary-fixed-variant: '#47464a'
  tertiary-fixed: '#ffdcbb'
  tertiary-fixed-dim: '#ffb869'
  on-tertiary-fixed: '#2c1700'
  on-tertiary-fixed-variant: '#673d00'
  background: '#131314'
  on-background: '#e5e2e3'
  surface-variant: '#353436'
typography:
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '450'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
  container-max: 1440px
---

## Brand & Style
The design system embodies a "Cyber Atelier" aesthetic—a digital workshop where narrative intelligence is forged with surgical precision. It is a high-end developer environment that balances the raw, technical nature of AI engineering with the refined elegance of a luxury toolset.

The visual direction is **Minimalist-Technic**. It utilizes a dark-mode-first architecture to reduce eye strain during long orchestration sessions, employing deep slate surfaces and high-contrast typography. The emotional response is one of calm authority, professional focus, and cutting-edge innovation. Design elements lean into geometric purity, thin lines, and purposeful "Electric Violet" accents that simulate a subtle energetic glow within a structured, dark void.

## Colors
The palette is rooted in deep blacks and slates to create an expansive sense of depth.

- **Primary (Electric Violet):** Used exclusively for primary actions, active states, and critical paths. It represents the "spark" of AI life.
- **Surface & Container:** The foundation is a near-black `#0A0A0B`. Elevated interface areas use `#121214` to provide subtle structural separation without breaking the dark immersion.
- **Typography:** Text levels are strictly tiered. Use White/Zinc-100 for core content and Zinc-400 for metadata and labels to maintain a clear visual hierarchy.
- **Borders:** Thin, low-contrast borders (`#27272A`) are the primary method of containment, replacing heavy shadows.

## Typography
This design system employs a dual-font strategy to distinguish between UI orchestration and technical data.

- **UI & Narrative (Geist/Inter):** Geist is used for headings to provide a sharp, modern geometric feel. Inter handles body copy for maximum legibility in documentation and settings.
- **Technical Data (JetBrains Mono):** All system IDs, API endpoints, JSON payloads, and variables must be rendered in JetBrains Mono. This provides a clear visual "mode switch" for the developer, signaling that the content is code-centric.
- **Labels:** Use uppercase monospaced labels for small section headers or status indicators to reinforce the "instrument cluster" feel of the console.

## Layout & Spacing
The layout follows a **Rigid Grid** philosophy. Content is organized into modular panels that snap to a 4px base unit.

- **Grid:** A 12-column grid is used for the main dashboard. Sidebars are fixed-width (240px or 280px) to ensure code editors and logs have consistent horizontal space.
- **Padding:** Generous internal padding within panels (24px) prevents the dark UI from feeling cramped.
- **Responsive Behavior:** On mobile, the multi-panel layout collapses into a single-column vertical stack. Complex data tables and code editors should enable horizontal scrolling rather than wrapping, preserving code structure.

## Elevation & Depth
Depth is communicated through **Tonal Layering** and **Subtle Outlines** rather than traditional shadows.

1.  **Level 0 (Base):** `#0A0A0B` - The canvas.
2.  **Level 1 (Panels):** `#121214` - For cards, sidebars, and header bars. These must have a 1px border of `#27272A`.
3.  **Level 2 (Popovers/Modals):** `#18181B` - To stand out against Level 1, these use a slightly lighter background and a subtle 10% opacity Violet glow (40px blur) to simulate "backlit" floating elements.

Interactive elements (buttons/inputs) do not use elevation; they use state-based color shifts (e.g., border color changing to Electric Violet on focus).

## Shapes
The shape language is **Precision-Sharp**. 

- **Radius:** A consistent 4px (Soft) radius is applied to all buttons, inputs, and panel corners. This is just enough to remove the "hostility" of 0px corners while maintaining a professional, engineered look.
- **Iconography:** Use 1.5pt stroke-based icons with geometric terminals. Icons should be encased in square bounding boxes to maintain the grid's visual alignment.

## Components
- **Buttons:** 
  - **Primary:** Solid Electric Violet with white text. No gradient. 
  - **Secondary:** Transparent background with a `#27272A` border. 
  - **Ghost:** Minimalist, text-only until hover, where a subtle slate background appears.
- **Code Blocks:** Rendered on `#18181B` with a 1px border. Use syntax highlighting that favors the Violet accent for keywords.
- **Inputs:** Dark backgrounds (`#0A0A0B`), subtle borders, and a 2px Electric Violet left-border indicator on focus.
- **Chips/Badges:** Use Monospace font. Status indicators (Online/Offline) use small 6px circles next to the text rather than large pill backgrounds.
- **Navigation:** Vertical sidebar navigation using high-contrast active states. Active links should have a vertical Electric Violet line on the far left.
- **Cards:** No shadows. Defined entirely by their `#27272A` border and a slightly lighter background than the base canvas.