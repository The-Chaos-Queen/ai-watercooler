```markdown
# Design System Specification

## 1. Overview & Creative North Star: "The Digital Cuneiform"
This design system is built on the tension between the enduring weight of antiquity and the frictionless speed of modern AI. We reject the "disposable" aesthetic of modern SaaS. Instead, we treat the desktop interface as a digital artifact—an intentional, grounded workspace where high-velocity technology meets the tactile soul of the earth.

**Creative North Star: The Digital Curator**
The UI should not feel like a "website"; it should feel like a curated editorial experience. We achieve this through:
*   **Intentional Asymmetry:** Breaking the 12-column grid with staggered content blocks to mimic the organic feel of a manuscript.
*   **Tonal Depth:** Replacing harsh lines with shifts in clay-inspired surfaces.
*   **The Power of Whitespace:** Using large, breathing gaps (16–24 spacing units) to signify premium authority and technical clarity.

---

## 2. Colors: The Earth & The Kiln
The palette is rooted in natural pigments—Terracotta, Sage, and Sand. We avoid "pure" blacks or grays, opting instead for "On-Surface" tones that feel like charcoal or deep soil.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or containment. 
*   **Separation via Surface:** Boundaries must be defined solely through background color shifts. For example, a `surface-container-low` (#faf3e6) section sitting on a `surface` (#fff8ef) background.
*   **Glassmorphism:** For floating menus or overlays, use `surface` at 80% opacity with a `24px` backdrop-blur. This allows the earthy tones of the background to "bleed" through, creating a frosted, organic glass effect.

### Surface Hierarchy
Treat the UI as a series of physical layers:
*   **Base:** `surface` (#fff8ef) - The canvas.
*   **Nesting:** Use `surface-container-low` for secondary content and `surface-container-highest` (#e9e2d6) for the most interactive, elevated elements. 

### Signature Textures
Main CTAs should not be flat. Use a subtle linear gradient (45-degree) from `primary` (#a03f28) to `primary-container` (#c0573e). This "Kiln-Fired" effect adds a sense of light and dimension that feels bespoke.

---

## 3. Typography: The Scholar & The Engineer
We utilize a high-contrast typographic pairing to bridge five millennia of communication.

*   **The Scholar (Newsreader Serif):** Used for `display` and `headline` roles. This evokes historical depth and narrative authority. It should be typeset with slightly tighter letter-spacing (-1% to -2%) for a premium, editorial feel.
*   **The Engineer (Manrope Sans-Serif):** Used for `title`, `body`, and `label` roles. This provides the technical clarity required for AI interactions.

**Hierarchy Guidelines:**
*   **Display-LG (3.5rem):** Reserved for Hero moments. Use `on-surface` color.
*   **Headline-MD (1.75rem):** For major section starts.
*   **Body-MD (0.875rem):** The workhorse. Maintain a line height of 1.6 to ensure readability against the creamy `surface` background.

---

## 4. Elevation & Depth: Tonal Layering
Traditional box-shadows are often too "digital." We achieve lift through "Tonal Layering."

*   **The Layering Principle:** To "lift" a card, do not add a shadow. Instead, place a `surface-container-lowest` (#ffffff) card on a `surface-container-low` (#faf3e6) background. The subtle shift in hex value creates a soft, natural lift.
*   **Ambient Shadows:** If an element must float (e.g., a dropdown), use a shadow with a 48px blur, 0% spread, and 6% opacity. The shadow color must be derived from `on-surface` (#1e1b14) to mimic natural light hitting clay.
*   **The "Ghost Border" Fallback:** If accessibility requires a border, use `outline-variant` (#ddc0ba) at **15% opacity**. A 100% opaque border is a failure of the system.

---

## 5. Components: Tactile Primitives

### Buttons
*   **Primary:** Kiln-gradient (`primary` to `primary-container`). White text. `0.375rem` (md) roundedness. No border.
*   **Secondary:** `secondary-container` (#d0e5d2) background with `on-secondary-container` (#546758) text.
*   **Tertiary:** Text-only in `primary` (#a03f28). On hover, add a `2px` underline with `0.5rem` offset.

### Cards & Lists
*   **Constraint:** Zero dividers. 
*   **Separation:** Use `spacing-6` (2rem) of vertical whitespace or a transition to `surface-container` to separate list items. 
*   **The Cuneiform Mark:** Use the 𒄉 symbol as a sophisticated bullet point or a watermark in the bottom-right of high-level cards.

### Input Fields
*   **Style:** Underline-only or subtle tonal shifts. Avoid the "box" look.
*   **State:** The active state should transition the underline to `primary` (#a03f28) with a thickness of `2px`.

### Contextual Tooltips
*   **Style:** `surface-container-highest` background with `on-surface` text. Use `backdrop-blur` to prevent the UI from feeling "blocked."

---

## 6. Do’s and Don'ts

### Do:
*   **Embrace Asymmetry:** Align text to the left but allow imagery or data visualizations to sit "off-center" to the right.
*   **Use the Spacing Scale religiously:** Use `16` (5.5rem) for section padding to convey a sense of luxury.
*   **Check Contrast:** Ensure the `on-primary` and `on-secondary` tokens are always used against their respective containers for AA accessibility.

### Don’t:
*   **No "Tech Blue":** Avoid any blue-spectrum colors. If a "success" state is needed, use `secondary` (Green).
*   **No Hard Edges:** Avoid `roundedness-none`. Everything in nature has a slight radius; use `0.25rem` (DEFAULT) as your baseline.
*   **No Grid-Lock:** Do not feel the need to fill every corner of the desktop screen. A centered, narrow-column layout (max-width: 1024px) often feels more premium than a full-width dashboard.

---

## 7. The Cuneiform Logo Usage
The 𒄉 (ul) character is our seal of speed. 
*   **Scale:** In the header, it should be no larger than `2rem`.
*   **Color:** Always in `primary` (#a03f28) or `on-surface` (#1e1b14).
*   **Treatment:** When used as a background element, reduce opacity to 3% to 5% and scale it up to `20rem`. It should feel like an embossed texture on the page.