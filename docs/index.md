# Docs Index

从这里开始阅读仓库知识，而不是只靠 README 或源码反推。

## First Read

- [product/overview.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/product/overview.md): 产品目标、主流程、已交付与未交付边界
- [architecture/system-map.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/architecture/system-map.md): 前后端、存储、AI、异步流程总览
- [domain/resume-pipeline.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/domain/resume-pipeline.md): 简历到面试的连续工作流
- [domain/entities.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/domain/entities.md): 核心实体与关系

## Repository Guides

- [codex-workspace.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/codex-workspace.md): 仓库结构地图
- [git-sync-workflow.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/git-sync-workflow.md): 双仓库同步发布约定
- [mcp-setup.md](/Users/zhengwenze/Desktop/codex/career-pilot/docs/mcp-setup.md): 外部工具与 MCP 说明

## Shared Layers

- `packages/contracts/`: 共享契约与领域边界
- `packages/api-client/`: 可复用 API 客户端基础层
- `packages/configs/`: 共享 TypeScript / ESLint 配置

## Agent Routing

优先按业务语义选择 skill：

- `resume-pipeline`
- `tailored-resume-contract`
- `mock-interview-session`

如果任务主要是技术实现，再落到 frontend/backend 等技术型 skill。
