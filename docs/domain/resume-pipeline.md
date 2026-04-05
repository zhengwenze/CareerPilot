# Resume Pipeline

## Workflow Chain

主简历工作流不是孤立页面，而是一条连续链路：

1. 用户上传主简历
2. 系统抽取原始内容
3. 系统整理成可编辑 Markdown
4. 用户修改并保存 Markdown 简历
5. 后端把 Markdown 继续沉淀为结构化数据
6. 结构化结果被后续 JD 匹配、定制简历、模拟面试复用

## Required Invariants

- 主简历必须保持可编辑，而不是只存原始 PDF
- Markdown 保存后要能被后续流程复用
- 结构化结果不能只服务单一页面
- 定制简历和模拟面试不能要求用户重新输入已有上下文

## Related Contracts

- resume record
- resume parse job
- job record
- match report
- resume optimization session
- mock interview session

这些契约的汇总边界放在 `packages/contracts/`。

## Failure States That Matter

- 解析失败但原始文件仍保留
- Markdown 可见但结构化结果过期
- JD 已更新但旧的优化结果已 stale
- mock interview 会话引用的 resume / job 版本与当前版本不一致

这些状态必须在实现和文档里显式表达，而不是靠隐式假设。
