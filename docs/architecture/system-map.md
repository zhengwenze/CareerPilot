# System Map

## Runtime Surfaces

- `apps/frontend`: Next.js 工作台界面，负责登录、Dashboard、简历与面试交互
- `apps/backend`: FastAPI API、业务服务、数据库模型、AI 集成和对象存储访问
- `apps/miniprogram`: 小程序端入口，当前不作为主要结构优化目标

## Shared Layers

- `packages/contracts`: 前后端共享的工作流契约、实体边界和 payload 示例
- `packages/api-client`: 从前端 API 层抽出的可复用 HTTP 客户端基础层
- `packages/configs`: 共享 TypeScript / ESLint 配置

## Main Data Flow

1. 前端上传主简历到后端
2. 后端完成抽取、Markdown 化和结构化沉淀
3. 前端维护目标岗位，后端解析 JD 并生成后续上下文
4. 前端发起专属简历生成或优化会话
5. 后端复用 resume + job + report 上下文生成结果
6. 前端从专属简历结果直接进入 mock interview
7. 后端在会话中复用岗位、简历和优化结果上下文

## Persistence And Infrastructure

- PostgreSQL: 业务主数据
- Redis: 缓存和异步状态辅助
- MinIO: 文件与对象存储
- AI providers: 简历处理、定制生成、模拟面试

## Structure Rule

系统图里的每一层都应该在仓库中有稳定归属：

- 运行单元在 `apps/`
- 共享边界在 `packages/`
- 知识说明在 `docs/`
- agent 工作流在 `.agents/skills/`
- 参考资产在 `references/`
