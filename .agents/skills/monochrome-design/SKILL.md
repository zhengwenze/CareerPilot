---
name: monochrome
description: Monochrome web interface design system for black, white, and grayscale layouts. Use for minimal, editorial, architectural, premium brand, portfolio, and photography interfaces that avoid hue-based color entirely.
version: 2.0.0
author: StyleKit
keywords:
  - monochrome
  - black and white
  - grayscale
  - minimal
  - editorial
  - architecture
  - premium
  - 单色
  - 黑白灰
  - 极简
style_type: visual
---

# Monochrome

A strict monochrome design system for web interfaces built entirely with black, white, and grayscale values.

This style should be used when the product needs to feel refined, minimal, editorial, architectural, premium, calm, or highly art-directed without relying on hue. Visual hierarchy must come from **contrast, spacing, typography, scale, alignment, and grayscale layering**, not color.

---

## When to Use This Style

Use `monochrome` when the user asks for or clearly implies:

- 黑白灰设计
- 单色、无彩色、去色相界面
- 极简、高级、克制、冷静、理性风格
- 摄影、建筑、艺术展览、作品集、高端品牌官网
- editorial / minimal / premium / gallery-like visual direction

This style is especially effective for:

- portfolio websites
- architecture studios
- photography landing pages
- luxury or premium brand pages
- editorial product sites
- minimalist SaaS marketing pages

Avoid using this style when the user explicitly wants:

- playful or colorful UI
- strong gradient branding
- neon / cyberpunk / glassmorphism color effects
- illustration-heavy cheerful products
- children's products or festival-like marketing pages

---

## Core Design Philosophy

Monochrome is not merely “removing color.” It is a disciplined visual system where hierarchy is created through:

1. **Grayscale contrast**
2. **Typography weight and scale**
3. **Generous whitespace**
4. **Sharp composition**
5. **Restraint in decoration**
6. **Precise borders instead of loud fills**
7. **Subtle shadow only when necessary**

The result should feel:

- calm
- premium
- intentional
- spacious
- sharp
- timeless

It must never feel:

- flat because of weak contrast
- boring because of weak hierarchy
- generic because of missing typography structure
- soft or playful because of excessive roundness
- “accidentally monochrome” due to lack of art direction

---

## Non-Negotiable Style Rules

These rules always apply:

- Use **only black, white, and neutral grayscale**
- Do **not** use any hue-based color
- Prefer **sharp corners**: `rounded-none` or `rounded-sm`
- Prefer **thin borders** over heavy fills
- Use **large whitespace** to create rhythm
- Use **font weight contrast** to create hierarchy
- Keep shadows subtle and rare
- Avoid decorative visual noise
- Avoid bright accents, gradients, glows, and colorful status treatments unless the user explicitly overrides the monochrome constraint

---

## Visual Character

### Tone

- restrained
- elegant
- editorial
- premium
- minimal
- architectural

### Shape Language

- rectilinear
- sharp-edged
- grid-aligned
- clean framing
- low ornamentation

### Hierarchy Strategy

Establish hierarchy using:

- black vs white contrast
- strong display type
- thin divider lines
- scale jumps between headline and body
- dense-to-light rhythm across sections
- whitespace blocks between content groups

Do **not** rely on colored badges, gradients, or loud button accents.

---

## Design Tokens

### Colors

Use grayscale only.

- Page background: `bg-[#fafafa]`
- Secondary background: `bg-[#f5f5f5]`
- Elevated neutral surface: `bg-white`
- Primary text: `text-[#111111]`
- Secondary text: `text-[#666666]`
- Muted text: `text-[#888888]`
- Border: `border-[#e5e5e5]`
- Strong divider: `border-[#d4d4d4]`
- Primary action background: `bg-[#111111]`
- Primary action text: `text-[#fafafa]`
- Hover dark: `hover:bg-[#333333]`

### Border

- Width: `border`
- Default color: `border-[#e5e5e5]`
- Emphasis border: `border-[#d4d4d4]`
- Radius: `rounded-none` or `rounded-sm`

### Shadow

Use shadow only to separate layers gently.

- Small: `shadow-sm`
- Medium: `shadow-sm`
- Large: `shadow-md`
- Hover: `hover:shadow-sm`

Never use dramatic floating shadows.

### Typography

Typography is one of the primary hierarchy tools in monochrome layouts.

- Display / Hero: `text-4xl md:text-6xl lg:text-8xl font-bold tracking-tight`
- H1: `text-3xl md:text-5xl font-bold tracking-tight`
- H2: `text-2xl md:text-4xl font-semibold tracking-tight`
- H3: `text-xl md:text-2xl font-semibold`
- Body large: `text-base md:text-lg font-light leading-7`
- Body default: `text-sm md:text-base font-light leading-6`
- Caption / meta: `text-xs md:text-sm text-[#666666] tracking-wide`
- Strong emphasis: `font-bold`
- Soft body copy: `font-light`

### Spacing

Spacing must feel deliberate and generous.

- Section spacing: `py-16 md:py-24`
- Hero spacing: `py-24 md:py-32`
- Container padding: `px-6 md:px-8`
- Card padding: `p-6`
- Dense block gap: `gap-4`
- Standard block gap: `gap-6`
- Spacious layout gap: `gap-8 md:gap-12`

---

## Layout Guidance

Monochrome layouts should feel structured, editorial, and balanced.

### Preferred Layout Traits

- strong grid alignment
- generous margins
- asymmetry used carefully
- consistent section rhythm
- visual breathing room
- image blocks framed cleanly
- restrained CTA placement

### Recommended Layout Archetypes

- `landing-hero-centered`  
  Centered headline, supporting copy, and CTA. Best for minimal premium statements.

- `landing-hero-split`  
  Text on one side, visual or product image on the other. Useful for brand storytelling.

- `landing-hero-fullscreen`  
  Large immersive opening section with strong typography and minimal chrome.

- `landing-video-hero`  
  Full-screen video with strong black/white treatment and sparse overlay content.

- `landing-saas-pricing`  
  Structured pricing page using borders, contrast, and spacing instead of colorful tiers.

- `landing-waitlist`  
  Minimal waitlist page with restrained email capture and sharp hierarchy.

### Section Composition Advice

For most pages:

- start with a bold hero
- follow with a restrained feature grid
- use line dividers or spacing to separate sections
- keep CTA blocks focused and minimal
- end with a clean footer with muted meta text

---

## Component Recipes

### Button

#### Base

`font-sans font-medium tracking-wide rounded-none transition-all duration-200`

#### Primary

`bg-[#111111] text-[#fafafa] border border-[#111111]`

Use for the main CTA only.

#### Outline

`bg-transparent text-[#111111] border border-[#111111]`

Use for secondary actions.

#### Hover

`hover:bg-[#333333]`

#### Button Guidance

- keep buttons rectangular
- avoid pill buttons
- avoid colorful fills
- avoid oversized playful motion
- use one dominant primary CTA per section

---

### Card

#### Base

`bg-[#fafafa] border border-[#e5e5e5] rounded-none overflow-hidden`

#### Hover

`hover:shadow-sm`

#### Card Guidance

- use cards only when grouping is necessary
- prefer border separation over strong elevation
- keep inner spacing clean and even
- avoid decorative gradients or tinted backgrounds

---

### Input

#### Base

`w-full bg-[#fafafa] border border-[#e5e5e5] text-[#111111] placeholder:text-[#666666]/50 focus:outline-none rounded-none transition-all duration-200`

#### Focus Recommendation

Prefer subtle focus treatment such as:

- darker border
- slightly stronger contrast
- minimal ring if necessary, but keep it neutral

Example neutral focus direction:

`focus:border-[#111111]`

#### Input Guidance

- keep fields simple and rectangular
- avoid heavy glow focus
- avoid colorful validation states unless product requirements force them

---

### Divider

Recommended for separating content cleanly.

- Base: `border-t border-[#e5e5e5]`
- Strong: `border-t border-[#d4d4d4]`

Use dividers to replace unnecessary visual decoration.

---

### Navigation

Recommended character:

- minimal
- text-first
- generous spacing
- subtle hover contrast
- no colorful active underline

Suggested treatment:

- transparent or white background
- slim bottom border when needed
- uppercase or tracking-wide labels for editorial feel

---

## Content Styling Guidance

Monochrome works best when copy is disciplined.

### Headlines

- short
- high-contrast
- declarative
- visually dominant

### Body Copy

- concise
- calm
- spacious
- avoid marketing clutter

### CTA Copy

Prefer clear, restrained verbs:

- Explore
- View Work
- See Collection
- Start Now
- Learn More
- Join Waitlist

Avoid overly loud CTA language unless required by the brand.

---

## Accessibility and Contrast

Because this style relies heavily on grayscale, contrast discipline is critical.

Always ensure:

- primary text has strong contrast against background
- muted text remains readable
- buttons remain distinguishable without hue
- section boundaries are visible through spacing or border
- disabled states do not become illegible

Do not confuse “minimal” with “low contrast.”

---

## Forbidden Patterns

The following must **never** be used unless the user explicitly overrides monochrome constraints.

### Forbidden Utility Patterns

- `bg-blue-500`
- `bg-red-500`
- `bg-green-500`
- `bg-pink-500`
- `bg-purple-500`
- `bg-yellow-500`
- `bg-orange-500`
- `bg-cyan-500`
- `bg-indigo-500`
- `bg-teal-500`
- `rounded-full`
- `shadow-lg`
- `shadow-xl`
- `shadow-2xl`
- `bg-gradient-to-*`

### Forbidden Regex Patterns

- `^bg-(?:blue|red|green|pink|purple|yellow|orange|cyan|indigo|teal|emerald|rose|violet|amber|lime|sky|fuchsia)-`
- `^text-(?:blue|red|green|pink|purple|yellow|orange|cyan|indigo|teal|emerald|rose|violet|amber|lime|sky|fuchsia)-`
- `^border-(?:blue|red|green|pink|purple|yellow|orange|cyan|indigo|teal|emerald|rose|violet|amber|lime|sky|fuchsia)-`
- `^from-`
- `^via-`
- `^to-`
- `^rounded-full$`
- `^shadow-(?:lg|xl|2xl)$`

### Why These Are Forbidden

- Hue-based colors break the monochrome constraint
- Gradients introduce visual color energy and decorative noise
- `rounded-full` makes the UI feel soft or playful rather than sharp and editorial
- heavy shadows create unnecessary depth and reduce the restrained premium quality

---

## Do

- 使用纯灰阶背景，如 `bg-[#fafafa]`、`bg-[#f5f5f5]`、`bg-white`
- 使用深灰主文字与中灰辅助文字建立层次
- 用 `font-light` 与 `font-bold` 建立强字重对比
- 使用大留白创造高级感与节奏
- 用细边框而不是彩色块面进行分隔
- 保持布局严格对齐，优先 grid-based layout
- 通过标题尺度、留白、边框和密度变化建立视觉节奏
- 优先做“少而准”的组件表达，而不是堆砌模块

## Don’t

- 禁止任何带色相的颜色
- 禁止彩色按钮、彩色标签、彩色图标高亮
- 禁止渐变、霓虹、发光、毛玻璃彩色叠层
- 禁止 `rounded-full` 式柔软圆角
- 禁止重阴影和漂浮感过强的卡片
- 禁止用过多装饰元素弥补信息层次不足
- 禁止低对比度到影响可读性

---

## Implementation Workflow

When applying this style to a page or component, follow this sequence:

### Step 1: Classify the Interface

Identify:

- product type
- audience
- page goal
- content density
- required sections
- whether the page should feel more editorial, architectural, portfolio-like, or premium commercial

### Step 2: Establish the Contrast Model

Decide:

- page background
- surface background
- text hierarchy
- border intensity
- CTA contrast level

### Step 3: Build Hierarchy Through Type and Space

Choose:

- hero scale
- heading rhythm
- body density
- section spacing
- whitespace emphasis zones

### Step 4: Apply Components Conservatively

Add:

- buttons
- cards
- inputs
- dividers
- navigation

Only when structurally necessary.

### Step 5: Remove Visual Noise

Check and remove:

- colorful classes
- unnecessary gradients
- excessive rounded corners
- decorative shadows
- redundant icon accents
- overdesigned badges and chips

### Step 6: Final Monochrome Audit

Before finalizing, verify:

- no hue-based color exists
- contrast is sufficient
- hierarchy is strong without color
- layout feels premium rather than empty
- buttons and inputs still feel interactive
- the page is minimal but not lifeless

---

## Output Expectations

When generating UI in this style, the result should:

- look premium without color
- feel minimal but intentional
- use typography and whitespace as primary design tools
- maintain strong readability
- avoid playful or overly friendly styling
- feel suitable for serious, aesthetic, or high-end digital products

---

## Example Prompt

```text
Generate a landing page with:
- Style: monochrome
- Archetype: landing-hero-centered
- Tone: premium, minimal, editorial
- Sections: hero, features, cta, footer
- Components: heading (hero variant), button (primary, lg), card (default)
- Constraint: grayscale only, no hue-based colors, no rounded-full, no heavy shadows
```
