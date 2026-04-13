# codex2gpt stream=true prompt complexity probe

## 一眼结论

### simple_prompt

- first_success_point: None
- first_failure_point: 2882
- max_usable_success: None
- main_error_type: stream_broken
- success_rate: 0.0

### complex_prompt_b1

- first_success_point: 2917
- first_failure_point: 5669
- max_usable_success: 2917
- main_error_type: stream_broken
- success_rate: 0.5

### complex_prompt_b2

- first_success_point: None
- first_failure_point: 3701
- max_usable_success: None
- main_error_type: stream_broken
- success_rate: 0.0

### complex_prompt_b3

- first_success_point: 8430
- first_failure_point: 8430
- max_usable_success: 8430
- main_error_type: stream_broken
- success_rate: 0.5

## 差异判断

- 简单 prompt 并没有天然更稳。当前样本里，simple_prompt 在约 2882 tokens 就断流，而 complex_prompt_b1、complex_prompt_b3 至少各出现过一次完整 success_usable。
- 值得继续做稳定上限测试的组：complex_prompt_b1

## 工程建议

- 当前 stream=true 还不适合直接把真实长 JSON 链路当作稳定方案。B1 有清晰成功区间，适合下一轮做临界点复测与稳定上限测量；B3 更像排障对象，因为它要么首档即断流，要么单次成功但 TTFT/总耗时极高。
