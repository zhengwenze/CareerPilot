# codex2gpt API 调用说明

这份文档面向“调用这个本地服务的人”。

目标很简单：把你本地登录好的 Codex，转换成一个可以按 OpenAI 风格直接调用的 HTTP API。

如果服务已经启动，默认地址就是：

```text
http://127.0.0.1:18100
```

默认推理入口：

```text
http://127.0.0.1:18100/v1
```

## 1. 这是什么

`codex2gpt` 是一个本地代理服务。

它会：

- 接收你发来的 OpenAI 风格请求
- 转换成 Codex 后端能理解的请求
- 用你本机已登录的 Codex 账号完成调用
- 再把结果包装成你熟悉的 API 响应格式返回

所以对于调用方来说，它看起来就像一个“本地 GPT API”。

## 2. 启动和检查

在项目根目录执行：

```bash
./run.sh start
```

查看状态：

```bash
./run.sh status
```

健康检查：

```bash
curl http://127.0.0.1:18100/health
```

查看模型列表：

```bash
curl http://127.0.0.1:18100/v1/models
```

## 3. 默认地址和鉴权

默认情况下：

- `Base URL`: `http://127.0.0.1:18100/v1`
- 如果没有配置 `LITE_API_KEY`，本地调用可以不带 Bearer Token
- 但很多 SDK 强制要求传一个 `api_key`，这时随便传一个非空字符串即可，比如 `dummy`

如果你在 `runtime/lite.env` 里配置了：

```text
LITE_API_KEY=your-local-key
```

那所有推理请求都应该带上：

```http
Authorization: Bearer your-local-key
```

## 4. 支持的接口

这个服务同时支持多种协议：

- OpenAI Chat Completions: `POST /v1/chat/completions`
- OpenAI Responses API: `POST /v1/responses`
- Anthropic Messages: `POST /v1/messages`
- Anthropic Count Tokens: `POST /v1/messages/count_tokens`
- Gemini Generate Content: `POST /v1beta/models/{model}:generateContent`
- Gemini Stream Generate Content: `POST /v1beta/models/{model}:streamGenerateContent`

如果你只是想“把 Codex 当成 GPT API 来用”，优先用：

- `POST /v1/chat/completions`

## 5. OpenAI 兼容调用

### 请求地址

```text
POST /v1/chat/completions
```

完整地址：

```text
http://127.0.0.1:18100/v1/chat/completions
```

### 请求头

最少需要：

```http
Content-Type: application/json
```

如果开启了本地 API Key，再额外带上：

```http
Authorization: Bearer your-local-key
```

### 常用请求参数

下面这些字段最常用，也最值得先掌握。

| 参数               | 类型          | 是否必填 | 说明                                       |
| ------------------ | ------------- | -------- | ------------------------------------------ |
| `model`            | string        | 是       | 模型名，比如 `gpt-5.4`                     |
| `messages`         | array         | 是       | 对话消息数组                               |
| `stream`           | boolean       | 否       | 是否流式返回，默认 `false`                 |
| `tools`            | array         | 否       | 函数工具定义，兼容 OpenAI function calling |
| `tool_choice`      | string/object | 否       | 控制模型是否调用工具                       |
| `response_format`  | object        | 否       | 控制结构化 JSON 输出                       |
| `client_id`        | string        | 否       | 调用方身份，建议稳定传递                   |
| `business_key`     | string        | 否       | 业务场景标识，建议稳定传递                 |
| `conversation_id`  | string        | 否       | 会话标识，可用于保持同一逻辑流程           |
| `session_id`       | string        | 否       | 会话标识，适合长链路调用                   |
| `prompt_cache_key` | string        | 否       | 显式指定缓存身份，一般不需要               |

### `messages` 格式

常见格式如下：

```json
[
  { "role": "system", "content": "你是一个简洁的助手。" },
  { "role": "user", "content": "请用一句话介绍杭州。" }
]
```

支持的常见角色：

- `system`
- `developer`
- `user`
- `assistant`
- `tool`

用户消息也支持多模态数组形式，例如文本加图片 URL：

```json
{
  "role": "user",
  "content": [
    { "type": "text", "text": "请描述这张图" },
    {
      "type": "image_url",
      "image_url": { "url": "https://example.com/demo.jpg" }
    }
  ]
}
```

### 推荐你额外传的两个字段

这两个字段不是必须，但非常建议传：

- `client_id`: 调用这个接口的客户端身份，比如 `my-app`
- `business_key`: 业务场景，比如 `chat`、`summary`、`translate`

示例：

```json
{
  "client_id": "my-app",
  "business_key": "chat"
}
```

这样做的好处是：

- 更稳定的请求路由
- 更好的缓存复用
- 同一工作流更容易串起来

不要每次都生成随机值，否则缓存和会话收益会很差。

## 6. 最小示例

### 最简单的 `curl`

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "user", "content": "你好，请介绍一下你自己。" }
    ],
    "stream": false
  }'
```

### 带上下文身份的推荐写法

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "client_id": "demo-client",
    "business_key": "quickstart",
    "messages": [
      { "role": "system", "content": "你是一个简洁的中文助手。" },
      { "role": "user", "content": "用三句话介绍西湖。" }
    ],
    "stream": false
  }'
```

## 7. 非流式响应长什么样

典型响应会是 OpenAI Chat Completions 风格：

```json
{
  "id": "chatcmpl_xxx",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "gpt-5.4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "西湖位于浙江杭州，是中国最有代表性的湖景之一。它以湖山相映、四季皆景闻名。白堤、苏堤和雷峰塔都是最常见的经典景点。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 56,
    "total_tokens": 179
  }
}
```

最常用的数据读取方式：

- 文本结果：`choices[0].message.content`
- 停止原因：`choices[0].finish_reason`
- token 用量：`usage`

## 8. 流式输出怎么调

把 `stream` 改成 `true` 即可：

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -N \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "user", "content": "请分三段介绍上海。" }
    ],
    "stream": true
  }'
```

返回会是标准 SSE 形式，大致像这样：

```text
data: {"id":"chatcmpl_xxx","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl_xxx","object":"chat.completion.chunk","choices":[{"delta":{"content":"上"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl_xxx","object":"chat.completion.chunk","choices":[{"delta":{"content":"海"},"index":0,"finish_reason":null}]}

data: [DONE]
```

如果你想在流式模式里额外返回 usage，可传：

```json
{
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}
```

## 9. Python 调用示例

### 方式一：直接用标准库 HTTP

```python
import json
import urllib.request

BASE_URL = "http://127.0.0.1:18100/v1"

payload = {
    "model": "gpt-5.4",
    "client_id": "python-demo",
    "business_key": "quickstart",
    "messages": [
        {"role": "user", "content": "请用一句话介绍深圳。"}
    ],
    "stream": False,
}

req = urllib.request.Request(
    f"{BASE_URL}/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer dummy",
    },
    method="POST",
)

with urllib.request.urlopen(req, timeout=180) as resp:
    body = json.loads(resp.read().decode("utf-8"))
    print(body["choices"][0]["message"]["content"])
```

### 方式二：用 OpenAI 官方 Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:18100/v1",
    api_key="dummy",
)

resp = client.chat.completions.create(
    model="gpt-5.4",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文助手。"},
        {"role": "user", "content": "请用一句话介绍成都。"},
    ],
)

print(resp.choices[0].message.content)
```

现成可运行示例：

- [openai_compatible_demo.py](./openai_compatible_demo.py)

执行方式：

```bash
python3 examples/openai_compatible_demo.py
python3 examples/openai_compatible_demo.py "请只回复：测试成功"
```

## 10. JavaScript 调用示例

```js
const resp = await fetch("http://127.0.0.1:18100/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: "Bearer dummy",
  },
  body: JSON.stringify({
    model: "gpt-5.4",
    client_id: "js-demo",
    business_key: "quickstart",
    messages: [{ role: "user", content: "请用一句话介绍苏州。" }],
    stream: false,
  }),
});

const data = await resp.json();
console.log(data.choices[0].message.content);
```

## 11. 结构化 JSON 输出

如果你希望模型直接返回 JSON，可使用 `response_format`。

### 方式一：简单 JSON 对象

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "user", "content": "返回一个 JSON，包含 city 和 country 两个字段，表示杭州所属国家。" }
    ],
    "response_format": {
      "type": "json_object"
    }
  }'
```

### 方式二：JSON Schema

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "user", "content": "返回杭州的结构化信息。" }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "city_info",
        "strict": true,
        "schema": {
          "type": "object",
          "properties": {
            "city": { "type": "string" },
            "province": { "type": "string" },
            "country": { "type": "string" }
          },
          "required": ["city", "province", "country"],
          "additionalProperties": false
        }
      }
    }
  }'
```

## 12. 工具调用 / Function Calling

OpenAI 风格的 `tools` 和 `tool_choice` 可以直接传。

示例：

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "user", "content": "帮我查一下杭州天气。" }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "获取某个城市的天气",
          "parameters": {
            "type": "object",
            "properties": {
              "city": { "type": "string" }
            },
            "required": ["city"]
          }
        }
      }
    ],
    "tool_choice": "auto"
  }'
```

如果模型决定调用工具，响应里会出现：

- `choices[0].message.tool_calls`

你需要：

1. 取出工具名和参数
2. 在你自己的业务代码里执行对应函数
3. 把工具结果作为 `role=tool` 的消息回传
4. 再次请求模型拿最终答案

## 13. Responses API

如果你不是为了兼容旧版 OpenAI Chat，而是自己开发新客户端，也可以直接用：

```text
POST /v1/responses
```

最小示例：

```bash
curl http://127.0.0.1:18100/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "input": "请用一句话介绍重庆。",
    "stream": false
  }'
```

这个接口更接近当前原生响应式模型接口，适合新系统集成。

## 14. 其他协议

### Anthropic 兼容

接口：

```text
POST /v1/messages
```

必须额外带请求头：

```http
anthropic-version: 2023-06-01
```

### Gemini 兼容

接口：

```text
POST /v1beta/models/{model}:generateContent
```

例如：

```bash
curl http://127.0.0.1:18100/v1beta/models/gpt-5.4:generateContent \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [
      {
        "role": "user",
        "parts": [{ "text": "请用一句话介绍武汉。" }]
      }
    ]
  }'
```

## 15. 可用模型

先用这个命令查看当前服务实际暴露的模型：

```bash
curl http://127.0.0.1:18100/v1/models
```

常见模型包括：

- `gpt-5.4`
- `gpt-5.3-codex`
- `gpt-5.4-1m`

其中：

- `gpt-5.4` 是常规默认模型
- `gpt-5.4-1m` 是这个代理额外暴露的长上下文模型名

## 16. 常见错误

### 1. `connection refused`

说明服务没启动。

处理方式：

```bash
./run.sh start
./run.sh status
```

### 2. `missing ~/.codex/auth.json`

说明本机还没有可用的 Codex 登录态。

处理方式：

1. 先在本机登录 Codex
2. 确认 `~/.codex/auth.json` 已生成
3. 执行 `./run.sh add-auth oauth-01`
4. 再执行 `./run.sh restart`

### 3. `401` 或 `403`

可能原因：

- 账号过期
- 本地 API Key 不对
- 上游账号状态失效

建议检查：

- `./run.sh status`
- Dashboard
- `runtime/server.log`

### 4. `413 context_limit_error`

说明输入上下文太长，超过模型窗口。

可选处理：

- 缩短输入
- 改用 `gpt-5.4-1m`
- 拆分任务

### 5. SDK 报必须传 `api_key`

即使你本地服务没启用鉴权，很多 SDK 也要求必须传一个值。

直接传：

```text
dummy
```

即可。

## 17. 建议的接入方式

如果你在接第三方客户端，通常只改这两项就够了：

- `Base URL` 改成 `http://127.0.0.1:18100/v1`
- `API Key` 填一个非空值，或者填你配置的本地 Key

如果你在自己写程序，推荐默认传：

```json
{
  "client_id": "your-app-name",
  "business_key": "your-scenario"
}
```

这样后续排障、缓存、路由都会更稳定。

## 18. 一分钟上手

如果你只想最快打通，直接跑这条：

```bash
curl http://127.0.0.1:18100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "user", "content": "请只回复：接口已打通" }
    ]
  }'
```

然后从响应里取：

```text
choices[0].message.content
```

这就是最终文本结果。
