# context_limit_probe

这个版本的探针只做一件事：

**在 `stream=true` 前提下，对比 simple / B1 / B2 / B3 四组 prompt 的真实流式可用性。**

当前阶段不是测最终稳定上限，也不做二分逼近。
当前阶段的目标是先明确：

- 哪些组能跑起来
- 每组的 `first_success_point`
- 每组的 `first_failure_point`
- 每组的 `main_error_type`
- 哪一组值得继续做稳定上限测试

## 固定测试条件

- 接口：`POST /v1/chat/completions`
- 模型：当前 backend `.env` 默认 `gpt-5.4`
- 模式：`stream=true`
- 不测试 `stream=false`
- 不测试 `gpt-5.4-1m`

## 四组 prompt

- `simple_prompt`
  - 简单自然语言任务
  - 低结构约束
  - 用中性 filler 扩容

- `complex_prompt_b1`
  - 复杂 instruction
  - Markdown 分段输出
  - 不带重结构输入

- `complex_prompt_b2`
  - 复杂 instruction
  - 中等结构化输入
  - 需要短 JSON 输出

- `complex_prompt_b3`
  - 真实业务重载链路
  - 使用 `tailored_resume/full_document.txt`
  - 带 `job_description / job_keywords / original_resume_json / original_resume_markdown / optimization_level`

## 默认夹具

- `fixtures/resume_realistic.md`
- `fixtures/jd_realistic.txt`
- `fixtures/filler_neutral.txt`

## 扩容方式

按固定 token 档位摸底：

- `2000`
- `4000`
- `8000`
- `12000`
- `16000`
- `24000`
- `32000`
- `48000`
- `64000`

脚本会对每组从低档位开始跑，遇到首个失败后停止该组后续档位。

## 记录指标

每条 run 都会记录：

- `time_to_first_token_ms`
- `time_to_last_token_ms`
- `received_done`
- `chunk_count`
- `output_chars`
- `finish_reason`
- `error_type`
- `error_message`
- `usable`

结果分类至少区分：

- `success_usable`
- `success_but_weak`
- `stream_broken`
- `empty_output`
- `http_error`
- `timeout`
- `parse_error`
- `invalid_business_output`

## 运行

小规模 smoke run：

```bash
python3 references/codex2gpt-demo/context_limit_probe.py \
  --smoke-only \
  --json-out references/codex2gpt-demo/context_limit_probe_result.sample.json
```

正式 real run：

```bash
python3 references/codex2gpt-demo/context_limit_probe.py \
  --json-out references/codex2gpt-demo/context_limit_probe_result.real.json \
  --csv-out references/codex2gpt-demo/context_limit_probe_result.real.csv \
  --report-out references/codex2gpt-demo/context_limit_probe_report.md
```

## 结果文件结构

真实结果 JSON 顶层包含：

- `metadata`
- `probe_settings`
- `prompt_groups`
- `runs`
- `group_summaries`
- `summary`

`group_summaries` 每组至少给出：

- `first_success_point`
- `first_failure_point`
- `max_usable_success`
- `main_error_type`
- `success_rate`
- `avg_seconds`
- `p50_seconds`
- `max_seconds`

`summary` 直接给出：

- 简单提示词整体结论
- 复杂提示词整体结论
- 简单 vs 复杂差异
- 当前 `stream=true` 工程建议
- 值得继续做稳定上限测试的组

## 先看哪里

先看：

- `context_limit_probe_report.md`

再看原始明细：

- `context_limit_probe_result.real.json`
- `context_limit_probe_result.real.csv`
