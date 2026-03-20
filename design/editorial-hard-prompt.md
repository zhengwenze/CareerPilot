STYLEKIT_STYLE_REFERENCE
style_name: 编辑杂志风
style_slug: editorial
style_source: /styles/editorial

# Hard Prompt

请严格遵守以下风格规则并保持一致性，禁止风格漂移。

## 执行要求
- 优先保证风格一致性，其次再做创意延展。
- 遇到冲突时以禁止项为最高优先级。
- 输出前自检：颜色、排版、间距、交互是否仍属于该风格。

## Style Rules
# Editorial (编辑杂志风) Design System

> 优雅的杂志排版风格，衬线标题、无衬线正文、精致的留白和网格系统。灵感来自高端时尚杂志和报纸排版。暖米色背景、柔和黑文字、精细的透明度层次和动画下划线交互。

## 核心理念

Editorial（编辑杂志风）设计风格源于传统印刷媒体的排版美学，特别是高端时尚杂志和报纸的设计语言。这种风格强调内容的层次结构、精致的字体搭配和大量留白。

核心理念：
- 内容为王：设计服务于内容，不喧宾夺主。UI 是低声细语，不是大声喊叫
- 字体层次：衬线标题与无衬线正文形成对比，标签使用 uppercase tracking 增加呼吸感
- 留白即美：适当的负空间让内容呼吸，section 间距 py-24 md:py-40 起步
- 单色克制：仅使用 #1C1C1C 配合不同透明度（/60 /40 /10）构建视觉层次，拒绝彩色装饰
- 微妙动效：hover-underline 动画、clip-path reveal、group-hover:italic 等克制而精致的交互

---

## Token 字典（精确 Class 映射）

### 边框
```
宽度: border
颜色: border-border
圆角: rounded-none
```

### 阴影
```
小:   shadow-none
中:   shadow-none
大:   shadow-none
悬停: shadow-none
聚焦: shadow-none
```

### 交互效果
```
悬停位移: undefined
过渡动画: transition-colors duration-200
按下状态: active:scale-95
```

### 字体
```
标题: font-serif tracking-tight
正文: font-sans
```

### 字号
```
Hero:  text-4xl md:text-6xl lg:text-7xl
H1:    text-3xl md:text-5xl
H2:    text-2xl md:text-3xl
H3:    text-xl md:text-2xl
正文:  text-sm md:text-base
小字:  text-xs
```

### 间距
```
Section: py-16 md:py-24 lg:py-32
容器:    px-6 md:px-12
卡片:    p-6
```

---

## [FORBIDDEN] 绝对禁止

以下 class 在本风格中**绝对禁止使用**，生成时必须检查并避免：

### 禁止的 Class
- `rounded-sm`
- `rounded`
- `rounded-md`
- `rounded-lg`
- `rounded-xl`
- `rounded-2xl`
- `rounded-3xl`
- `rounded-full`
- `shadow-sm`
- `shadow`
- `shadow-md`
- `shadow-lg`
- `shadow-xl`
- `shadow-2xl`
- `border-2`
- `border-4`
- `border-8`
- `bg-blue-500`
- `bg-green-500`
- `bg-yellow-500`

### 禁止的模式
- 匹配 `^rounded-(?!none)`
- 匹配 `^shadow-(?!none)`
- 匹配 `^border-[248]`
- 匹配 `^bg-gradient-`

### 禁止原因
- `rounded-lg`: Editorial uses sharp corners only (rounded-none)
- `shadow-lg`: Editorial avoids shadows completely
- `border-4`: Editorial uses thin borders only (border)
- `bg-gradient-to-r`: Editorial uses solid colors, no gradients
- `font-black`: Editorial headings use font-serif with normal weight, not bold

> WARNING: 如果你的代码中包含以上任何 class，必须立即替换。

---

## [REQUIRED] 必须包含

### 按钮必须包含
```
px-6 py-3
text-sm tracking-wide
transition-colors
```

### 卡片必须包含
```
border border-border
hover:border-foreground
transition-colors
```

### 输入框必须包含
```
border border-border
text-sm
focus:outline-none
focus:border-foreground
transition-colors
placeholder:text-muted
```

---

## [COMPARE] 错误 vs 正确对比

### 按钮

[WRONG] **错误示例**（使用了圆角和模糊阴影）：
```html
<button class="rounded-lg shadow-lg bg-blue-500 text-white px-4 py-2 hover:bg-blue-600">
  点击我
</button>
```

[CORRECT] **正确示例**（使用硬边缘、无圆角、位移效果）：
```html
<button class="px-6 py-3 text-sm tracking-wide transition-colors bg-[#ff006e] text-white px-4 py-2 md:px-6 md:py-3">
  点击我
</button>
```

### 卡片

[WRONG] **错误示例**（使用了渐变和圆角）：
```html
<div class="rounded-xl shadow-2xl bg-gradient-to-r from-purple-500 to-pink-500 p-6">
  <h3 class="text-xl font-semibold">标题</h3>
</div>
```

[CORRECT] **正确示例**（纯色背景、硬边缘阴影）：
```html
<div class="border border-border hover:border-foreground transition-colors p-6">
  <h3 class="font-serif tracking-tight text-xl md:text-2xl">标题</h3>
</div>
```

### 输入框

[WRONG] **错误示例**（灰色边框、圆角）：
```html
<input class="rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-blue-500" />
```

[CORRECT] **正确示例**（黑色粗边框、聚焦阴影）：
```html
<input class="border border-border text-sm focus:outline-none focus:border-foreground transition-colors placeholder:text-muted px-3 py-2 md:px-4 md:py-3" placeholder="请输入..." />
```

---

## [TEMPLATES] 页面骨架模板

使用以下模板生成页面，只需替换 `{PLACEHOLDER}` 部分：

### 导航栏骨架
```html
<nav class="bg-white border-b-2 md:border-b-4 border-black px-4 md:px-8 py-3 md:py-4">
  <div class="flex items-center justify-between max-w-6xl mx-auto">
    <a href="/" class="font-black text-xl md:text-2xl tracking-wider">
      {LOGO_TEXT}
    </a>
    <div class="flex gap-4 md:gap-8 font-mono text-sm md:text-base">
      {NAV_LINKS}
    </div>
  </div>
</nav>
```

### Hero 区块骨架
```html
<section class="min-h-[60vh] md:min-h-[80vh] flex items-center px-4 md:px-8 py-12 md:py-0 bg-{ACCENT_COLOR} border-b-2 md:border-b-4 border-black">
  <div class="max-w-4xl mx-auto">
    <h1 class="font-black text-4xl md:text-6xl lg:text-8xl leading-tight tracking-tight mb-4 md:mb-6">
      {HEADLINE}
    </h1>
    <p class="font-mono text-base md:text-xl max-w-xl mb-6 md:mb-8">
      {SUBHEADLINE}
    </p>
    <button class="bg-black text-white font-black px-6 py-3 md:px-8 md:py-4 border-2 md:border-4 border-black shadow-[4px_4px_0px_0px_rgba(255,0,110,1)] md:shadow-[8px_8px_0px_0px_rgba(255,0,110,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all text-sm md:text-base">
      {CTA_TEXT}
    </button>
  </div>
</section>
```

### 卡片网格骨架
```html
<section class="py-12 md:py-24 px-4 md:px-8">
  <div class="max-w-6xl mx-auto">
    <h2 class="font-black text-2xl md:text-4xl mb-8 md:mb-12">{SECTION_TITLE}</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
      <!-- Card template - repeat for each card -->
      <div class="bg-white border-2 md:border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] md:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-4 md:p-6 hover:shadow-[4px_4px_0px_0px_rgba(255,0,110,1)] md:hover:shadow-[8px_8px_0px_0px_rgba(255,0,110,1)] hover:-translate-y-1 transition-all">
        <h3 class="font-black text-lg md:text-xl mb-2">{CARD_TITLE}</h3>
        <p class="font-mono text-sm md:text-base text-gray-700">{CARD_DESCRIPTION}</p>
      </div>
    </div>
  </div>
</section>
```

### 页脚骨架
```html
<footer class="bg-black text-white py-12 md:py-16 px-4 md:px-8 border-t-2 md:border-t-4 border-black">
  <div class="max-w-6xl mx-auto">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <div>
        <span class="font-black text-xl md:text-2xl">{LOGO_TEXT}</span>
        <p class="font-mono text-sm mt-4 text-gray-400">{TAGLINE}</p>
      </div>
      <div>
        <h4 class="font-black text-lg mb-4">{COLUMN_TITLE}</h4>
        <ul class="space-y-2 font-mono text-sm text-gray-400">
          {FOOTER_LINKS}
        </ul>
      </div>
    </div>
  </div>
</footer>
```

---

## [CHECKLIST] 生成后自检清单

**在输出代码前，必须逐项验证以下每一条。如有违反，立即修正后再输出：**

### 1. 圆角检查
- [ ] 搜索代码中的 `rounded-`
- [ ] 确认只有 `rounded-none` 或无圆角
- [ ] 如果发现 `rounded-lg`、`rounded-md` 等，替换为 `rounded-none`

### 2. 阴影检查
- [ ] 搜索代码中的 `shadow-`
- [ ] 确认只使用 `shadow-[Xpx_Xpx_0px_0px_rgba(...)]` 格式
- [ ] 如果发现 `shadow-lg`、`shadow-xl` 等，替换为正确格式

### 3. 边框检查
- [ ] 搜索代码中的 `border-`
- [ ] 确认边框颜色是 `border-black`
- [ ] 如果发现 `border-gray-*`、`border-slate-*`，替换为 `border-black`

### 4. 交互检查
- [ ] 所有按钮都有 `hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]`
- [ ] 所有卡片都有 hover 效果（阴影变色或位移）
- [ ] 都包含 `transition-all`

### 5. 响应式检查
- [ ] 边框有 `border-2 md:border-4`
- [ ] 阴影有 `shadow-[4px...] md:shadow-[8px...]`
- [ ] 间距有 `p-4 md:p-6` 或类似的响应式值
- [ ] 字号有 `text-sm md:text-base` 或类似的响应式值

### 6. 字体检查
- [ ] 标题使用 `font-black`
- [ ] 正文使用 `font-mono`

> CRITICAL: **如果任何一项检查不通过，必须修正后重新生成代码。**

---

## [EXAMPLES] 示例 Prompt

### 1. 创意作品集

编辑杂志风格的创意设计师作品集

```
Use Editorial style to create a creative portfolio page:
1. Fixed nav: font-serif logo with tracking-[0.3em], hover-underline links
2. Hero: massive serif title (9rem+) with italic subtitle in #1C1C1C/60, clip-path image reveal
3. Featured works: numbered list (01, 02, 03) with hover image float and group-hover:italic
4. Infinite marquee ticker: services list with dot separators
5. Archive grid: masonry 2-col layout with staggered scroll reveals
6. About section: sticky portrait left, serif quote right, services/clients lists
7. Contact: floating-label inputs with bottom borders, hover-underline submit button
8. Palette: bg-[#F9F8F6], text-[#1C1C1C] with /60 /40 /10 opacity hierarchy only
```

### 2. 杂志风格博客

经典杂志排版的博客首页

```
Use Editorial style to create a magazine blog homepage:
1. Navigation: fixed top, bg-[#F9F8F6]/90 backdrop-blur, hover-underline links
2. Featured article: full-width grayscale image with clip-path reveal, serif title text-7xl
3. Article list: numbered editorial list with border-b border-[#1C1C1C]/10 dividers
4. Typography: font-serif headings tracking-tighter, font-sans text-xs labels with tracking-[0.2em] uppercase
5. Footer: minimal, text-xs uppercase with dot separators
6. Colors: monochrome only, #F9F8F6 background, #1C1C1C text with opacity variants
```

### 3. 工作室介绍

设计工作室的介绍页面

```
Use Editorial style to design a studio about page:
1. Layout: 12-col grid, col-span-5 sticky portrait + col-span-7 content
2. Hero quote: font-serif text-6xl with line breaks and italic decorative words
3. Body text: font-sans text-sm leading-relaxed text-[#1C1C1C]/80, max-w-xl
4. Services & clients: two-column grid with uppercase tracking labels, serif list items
5. Contact section: Say Hello heading text-8xl, floating-label form inputs
6. Interactions: IntersectionObserver scroll reveals, group-hover:italic on links
7. Palette: bg-[#F9F8F6], pure monochrome, NO accent colors
```