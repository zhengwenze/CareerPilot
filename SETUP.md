# Career Pilot 安装与配置指南

欢迎！本指南将带你在本地完成 Career Pilot 的安装与配置。

---

## 目录

- [本地开发](#本地开发)
- [服务器部署](#服务器部署)
- [配置 AI 提供商](#配置-ai-提供商)

---

## 本地开发

### 1. 克隆仓库

```bash
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot
```

### 2. 启动依赖服务

```bash
docker compose -f docker-compose.yml up -d postgres redis minio
```

### 3. 后端配置

```bash
cd apps/backend

# 创建环境变量文件
cp .env.example .env

# 编辑 .env 文件，配置 AI 提供商（见下方）
code .env

# 安装依赖
uv sync

# 执行数据库迁移
uv run alembic upgrade head

# 启动后端
uv run uvicorn app.main:app --reload --port 8000
```

### 4. 前端配置

```bash
cd apps/frontend

# 安装依赖
npm install

# 启动前端
npm run dev
```

浏览器打开 **http://localhost:3000** 即可。

---

## 服务器部署

### 方案 A：一键部署（推荐）

```bash
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot
chmod +x docker/deploy.sh
./docker/deploy.sh
```

### 方案 B：手动部署

```bash
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot

# 创建环境变量文件
cd apps/backend
cp .env.example .env

# 编辑 .env 文件（见下方配置说明）
code .env

# 启动所有服务
cd ../..
docker compose -f docker-compose.yml up -d
```

### 常用命令

```bash
# 查看服务状态
docker compose -f docker-compose.yml ps

# 查看日志
docker compose -f docker-compose.yml logs -f

# 停止服务
docker compose -f docker-compose.yml down

# 重启服务
docker compose -f docker-compose.yml restart
```

---

## 配置 AI 提供商

在 `apps/backend/.env` 文件中配置 AI 提供商。

### 选项 A：MiniMax（推荐）

```env
RESUME_AI_PROVIDER=minimax
RESUME_AI_BASE_URL=https://api.minimaxi.com/anthropic
RESUME_AI_API_KEY=your_api_key_here
RESUME_AI_MODEL=MiniMax-M2.5
RESUME_AI_TIMEOUT_SECONDS=30

MATCH_AI_PROVIDER=minimax
MATCH_AI_BASE_URL=https://api.minimaxi.com/anthropic
MATCH_AI_API_KEY=your_api_key_here
MATCH_AI_MODEL=MiniMax-M2.5
MATCH_AI_TIMEOUT_SECONDS=90
```

### 选项 B：Anthropic

```env
RESUME_AI_PROVIDER=anthropic
RESUME_AI_BASE_URL=https://api.anthropic.com/v1
RESUME_AI_API_KEY=sk-ant-your-key-here
RESUME_AI_MODEL=claude-3-5-sonnet-20241022
RESUME_AI_TIMEOUT_SECONDS=30

MATCH_AI_PROVIDER=anthropic
MATCH_AI_BASE_URL=https://api.anthropic.com/v1
MATCH_AI_API_KEY=sk-ant-your-key-here
MATCH_AI_MODEL=claude-3-5-sonnet-20241022
MATCH_AI_TIMEOUT_SECONDS=90
```

### 选项 C：本地大模型代理（免费）

```env
RESUME_AI_PROVIDER=openai-compatible
RESUME_AI_BASE_URL=http://localhost:8001/v1
RESUME_AI_API_KEY=dummy-key
RESUME_AI_MODEL=local-model-name
RESUME_AI_TIMEOUT_SECONDS=30

MATCH_AI_PROVIDER=openai-compatible
MATCH_AI_BASE_URL=http://localhost:8001/v1
MATCH_AI_API_KEY=dummy-key
MATCH_AI_MODEL=local-model-name
MATCH_AI_TIMEOUT_SECONDS=90
```

启动代理：

```bash
python scripts/codex2gpt/server.py
```

---

## 访问地址

| URL                                | 说明                |
| ---------------------------------- | ------------------- |
| **http://localhost:3000**          | 主应用（本地）      |
| **https://codeclaw.top**           | 主应用（服务器）    |
| **http://localhost:8000**          | 后端 API（本地）    |
| **http://localhost:9001**          | MinIO 控制台        |
