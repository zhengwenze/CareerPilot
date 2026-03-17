# Codex API 调用手册

> 适用范围：本文档面向通过 `codex2gpt` 本地代理调用 Codex 上游能力的开发者。  
> 说明：本文档**不包含登录与认证部分**，仅说明接口调用、参数行为与兼容边界。

## 1. 概述

`codex2gpt` 启动后会在本地暴露一组 OpenAI 风格接口，便于现有客户端直接接入。常用接口如下：

- `POST /v1/responses`
- `POST /v1/chat/completions`
- `GET /v1/models`
- `GET /health`

默认基础地址：

```text
http://127.0.0.1:18100/v1
```

默认模型通常为：

```text
gpt-5.4
```

需要特别说明的是：这套接口是**本地代理层**暴露出的兼容接口，不应等同理解为 OpenAI 官方直连接口的完整实现。`/v1/responses` 与 `/v1/chat/completions` 的整体风格参考 OpenAI API，但部分默认值、字段补齐、字段清洗与兼容行为属于该代理额外提供的能力。

## 2. 接口说明

### 2.1 `POST /v1/responses`

主调用入口，建议新项目优先使用。请求体通常包含：

- `model`
- `input`
- `stream`

最小可用示例：

```bash
curl http://127.0.0.1:18100/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "input": "用中文打个招呼。",
    "stream": false
  }'
```

### 2.2 `POST /v1/chat/completions`

兼容入口，适合已有 Chat Completions 风格客户端平滑接入。常见字段包括：

- `model`
- `messages`
- `tools`
- `tool_choice`
- `stream`
- `temperature`
- `reasoning`
- `text`
- `prompt_cache_key`

示例：

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      {"role": "system", "content": "你是一个助手"},
      {"role": "user", "content": "只回复 OK"}
    ],
    "stream": false
  }'
```

### 2.3 `GET /v1/models`

用于读取代理声明的模型列表：

```bash
curl http://127.0.0.1:18100/v1/models
```

### 2.4 `GET /health`

用于本地服务健康检查：

```bash
curl http://127.0.0.1:18100/health
```

## 3. `/v1/responses` 调用规范

### 3.1 推荐请求头

```http
Content-Type: application/json
```

### 3.2 非流式调用示例

```bash
curl http://127.0.0.1:18100/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "input": "请用中文解释这段代码。",
    "stream": false
  }'
```

### 3.3 带推理与输出详细度控制的调用示例

```bash
curl http://127.0.0.1:18100/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "input": "请用中文解释这段代码。",
    "stream": false,
    "reasoning": {"effort": "high"},
    "text": {"verbosity": "high"}
  }'
```

## 4. 默认参数与本地补齐行为

如果请求体未显式传入部分字段，代理通常会自动补齐默认配置，例如：

```json
{
  "model": "gpt-5.4",
  "reasoning": {"effort": "high"},
  "text": {"verbosity": "low"}
}
```

README 同时给出过一组典型本地配置：

```bash
LITE_MODEL=gpt-5.4
LITE_MODELS=gpt-5.4,gpt-5.3-codex
LITE_REASONING_EFFORT=high
LITE_TEXT_VERBOSITY=low
LITE_MODEL_CONTEXT_WINDOW=258400
LITE_MODEL_AUTO_COMPACT_TOKEN_LIMIT=232560
```

其中需要区分两类信息：

- `reasoning.effort` 与 `text.verbosity`：请求级默认参数
- `context window` 与自动压缩阈值：代理本地的预检查与运行配置，不属于标准通用 API 入参

## 5. 参数支持与经验性结论

根据 README 中的实测说明，可整理出以下经验结论：

- `gpt-5.4`：已验证可接受 `reasoning.effort=medium/high` 与 `text.verbosity=high`
- `gpt-5.3-codex`：默认可用；未显式指定时，上游会返回 `reasoning.effort=medium`、`text.verbosity=medium`
- `text.verbosity=xhigh`：会被上游拒绝
- 推荐枚举值：
  - `reasoning.effort`：`low` / `medium` / `high` / `xhigh`
  - `text.verbosity`：`low` / `medium` / `high`

这些内容应理解为 README 当前记录的**经验性结果**，不应视为所有模型、所有时间点都恒定不变的官方保证。

## 6. 高级字段与会话延续

如果上游支持，建议优先关注以下字段：

- `previous_response_id`
- `truncation`
- `prompt_cache_key`

适用场景如下：

- `previous_response_id`：基于前一次响应继续对话或延续上下文
- `truncation`：控制超长输入的截断策略
- `prompt_cache_key`：在重复或相似提示中复用缓存，提高性能并降低重复计算成本

其中 `prompt_cache_key` 已在 README 中被明确提及，并配有缓存命中 smoke test。

## 7. 自动清洗的不兼容字段

为兼容更多 OpenAI 风格客户端，代理会在转发前忽略一批 Codex 上游当前不接收或不保证支持的字段：

- `max_output_tokens`
- `max_tokens`
- `max_completion_tokens`
- `metadata`
- `service_tier`
- `response_format`
- `parallel_tool_calls`
- `stream_options`
- `user`
- `n`

这意味着：这些字段即使由客户端自动附带，也不应默认认为会在上游真正生效。  
实际接入时，建议在调用封装层主动移除这类字段，避免“表面上传了参数，实际上被代理吞掉”的误判。

## 8. Chat Completions 兼容边界

`/v1/chat/completions` 的主要价值是兼容已有客户端，而不是替代 `/v1/responses` 作为新的主语义层。

当 `stream=true` 时，README 说明该代理会返回 **SSE 风格的兼容 completion chunk**，并以 `[DONE]` 结束；但它不是严格意义上的逐 token 流式输出，而更接近一次性完成后的分块兼容返回。

因此：

- 已有旧客户端可较低成本复用
- 新项目仍建议优先面向 `/v1/responses`
- 若前端强依赖逐 token 打字机效果，需要单独验证兼容性

## 9. 模型列表与模型选择

代理通常会通过本地配置暴露一组模型名，例如：

```bash
LITE_MODEL=gpt-5.4
LITE_MODELS=gpt-5.4,gpt-5.3-codex
```

也可以按需扩展：

```bash
LITE_MODEL=gpt-5.3-codex
LITE_MODELS=gpt-5.4,gpt-5.3-codex,gpt-5.1-codex,gpt-5.1-codex-max,gpt-5.1-codex-mini
```

需要注意三点：

1. `/v1/models` 返回的是代理声明的模型列表  
2. 请求中的 `model` 字段通常会直接透传给上游  
3. 某个模型能否真正调用成功，最终仍取决于上游账号权限与模型开放状态

## 10. 可靠性与测试建议

### 10.1 多账号与故障切换

README 描述了多账号轮换与故障切换能力：当某个账号返回 `429`、`403`、`5xx` 或发生网络异常时，代理会切换到下一个账号，并对失败账号实施短暂冷却。

这意味着：

- 同一本地地址背后可能承载多个上游账号
- 某些瞬时失败可能被代理自动吸收
- 不同时间段的配额、可用模型与缓存表现可能并不完全一致

### 10.2 建议的测试方式

单元测试：

```bash
python3 -m unittest discover -s tests -v
```

缓存命中 smoke test：

```bash
python3 tests/cache_hit_smoke.py
```

README 说明：若第二次请求的返回结果中出现 `usage.input_tokens_details.cached_tokens > 0`，即可视为观察到缓存命中。

## 11. 速查示例

### Responses 最小调用

```bash
curl http://127.0.0.1:18100/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "input": "你好",
    "stream": false
  }'
```

### Responses 推荐调用

```bash
curl http://127.0.0.1:18100/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "input": "请总结下面这段代码的用途和风险。",
    "stream": false,
    "reasoning": {"effort": "high"},
    "text": {"verbosity": "high"},
    "prompt_cache_key": "repo-review-001"
  }'
```

### Chat Completions 兼容调用

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      {"role": "system", "content": "你是一个严谨的代码助手"},
      {"role": "user", "content": "解释这段 Python"}
    ],
    "stream": false
  }'
```

### 健康检查

```bash
curl http://127.0.0.1:18100/health
```

### 模型列表

```bash
curl http://127.0.0.1:18100/v1/models
```

---

## 结语

对开发者而言，最稳妥的接入方式是把 `codex2gpt` 视作一个**具备明确边界的本地代理层**：

- 主接口使用 `/v1/responses`
- 兼容接口使用 `/v1/chat/completions`
- 模型名透传，但可用性取决于上游
- 默认参数、字段清洗、故障切换与缓存支持都属于代理层增强能力

因此，在工程设计上，建议优先围绕 Responses API 构建调用封装，并对模型可用性、缓存命中与兼容字段做显式处理。
