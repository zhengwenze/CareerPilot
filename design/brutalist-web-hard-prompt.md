STYLEKIT_STYLE_REFERENCE
style_name: 网页粗野主义
style_slug: brutalist-web
style_source: /styles/brutalist-web

# Hard Prompt

请严格遵守以下风格规则并保持一致性，禁止风格漂移。

## 执行要求
- 优先保证风格一致性，其次再做创意延展。
- 遇到冲突时以禁止项为最高优先级。
- 输出前自检：颜色、排版、间距、交互是否仍属于该风格。

## Style Rules
# Brutalist Web (网页粗野主义) Design System

> 回归90年代早期互联网的原始HTML美学，系统字体、蓝色下划线链接、纯白背景、无装饰，内容优先于形式。

## 核心理念

Brutalist Web embraces the raw aesthetics of the early 1990s internet. Content is king; decoration is irrelevant.

Core principles:
- Content over decoration - every element serves an informational purpose
- System fonts and monospace stacks - no custom web fonts needed
- Unstyled HTML feel - as if CSS barely exists
- Intentional lo-fi appearance - the roughness is the design
- Blue underlined links, purple visited links - classic browser defaults
- Times New Roman or Georgia for headings, system sans-serif or monospace for body
- Pure white backgrounds with black text - maximum readability
- Thin 1px borders only - no thick borders, no decorative frames
- Minimal or zero padding - content touches edges
- No visual hierarchy tricks - the document structure IS the hierarchy

---

## Token 字典（精确 Class 映射）

### 边框
```
宽度: border
颜色: border-black
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
悬停位移: 
过渡动画: 

```

### 字体
```
标题: font-serif font-bold
正文: font-mono text-sm
```

### 字号
```
Hero:  text-3xl md:text-5xl
H1:    text-2xl md:text-4xl
H2:    text-xl md:text-2xl
H3:    text-lg md:text-xl
正文:  text-sm md:text-base
小字:  text-xs md:text-sm
```

### 间距
```
Section: py-6 md:py-8
容器:    px-4
卡片:    p-4
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
- `backdrop-blur`
- `backdrop-blur-sm`
- `backdrop-blur-md`
- `backdrop-blur-lg`
- `transition`
- `transition-all`

### 禁止的模式
- 匹配 `^rounded-(?!none)`
- 匹配 `^shadow-(?!none)`
- 匹配 `^bg-gradient-`
- 匹配 `^backdrop-blur`
- 匹配 `^animate-`
- 匹配 `^transition-`
- 匹配 `^duration-`

### 禁止原因
- `rounded-lg`: Brutalist Web uses zero border-radius. Everything is sharp and unstyled.
- `shadow-lg`: Brutalist Web uses no shadows at all. Raw HTML has no shadows.
- `bg-gradient-to-r`: Brutalist Web uses flat white backgrounds only. No gradients.
- `backdrop-blur`: Brutalist Web rejects all modern visual effects. Plain and raw.
- `transition-all`: Brutalist Web uses no CSS transitions or animations. Static pages only.
- `animate-pulse`: Brutalist Web forbids all animations. The page is static like 90s HTML.

> WARNING: 如果你的代码中包含以上任何 class，必须立即替换。

---

## [REQUIRED] 必须包含

### 按钮必须包含
```
rounded-none
border
border-black
font-mono
bg-white
```

### 卡片必须包含
```
rounded-none
border
border-black
bg-white
```

### 输入框必须包含
```
rounded-none
border
border-black
font-mono
bg-white
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
<button class="rounded-none border border-black font-mono bg-white bg-[#ff006e] text-white px-4 py-2 md:px-6 md:py-3">
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
<div class="rounded-none border border-black bg-white p-4">
  <h3 class="font-serif font-bold text-lg md:text-xl">标题</h3>
</div>
```

### 输入框

[WRONG] **错误示例**（灰色边框、圆角）：
```html
<input class="rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-blue-500" />
```

[CORRECT] **正确示例**（黑色粗边框、聚焦阴影）：
```html
<input class="rounded-none border border-black font-mono bg-white px-3 py-2 md:px-4 md:py-3" placeholder="请输入..." />
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

### 1. 90年代个人主页

纯白背景、蓝色下划线链接的朴素个人主页

```
Use Brutalist Web style to create a personal homepage:
1. White background, no decoration
2. Large serif heading with the person's name
3. Horizontal rule separator
4. Monospace body text with a brief bio
5. Blue underlined links section: "My Projects", "My Blog", "Contact"
6. Simple 1px border table listing recent updates with dates
7. Footer with "Last updated" date and webmaster email link
8. No shadows, no rounded corners, no gradients, no animations
9. Buttons: Windows 95 bevel border style, transition-none
10. Inputs: inset bevel border, focus:bg-[#ffffcc] yellow highlight
```

### 2. 学术论文索引

类似早期学术网站的纯文本论文列表页

```
Use Brutalist Web style to create an academic paper index:
1. Serif heading: "Publications"
2. Numbered list of papers with titles as blue underlined links
3. Author names in monospace, dates in plain text
4. Thin 1px horizontal rules between sections
5. Navigation at top: simple blue links separated by " | "
6. No cards, no shadows, no visual decoration
7. Dense text layout with minimal spacing
```

### 3. 极简博客

回归互联网本质的纯内容博客

```
Use Brutalist Web style to create a minimalist blog:
1. Site title in large serif font at the top
2. Navigation as plain blue underlined links below title
3. Blog posts listed with serif titles, monospace dates, plain text excerpts
4. "Read more" as a simple blue underlined link
5. 1px black border separating posts
6. Sidebar (if any) is just a list of links
7. Footer: plain text copyright and a link to RSS feed
8. Maximum readability, zero decoration
```