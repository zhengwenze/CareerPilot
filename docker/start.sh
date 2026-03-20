#!/bin/bash
set -euo pipefail

# CareerPilot 启动脚本
# 用途：一键启动所有中间件服务和后端服务
# 用法：./docker/start.sh

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖环境..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker Desktop"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Desktop"
        exit 1
    fi

    if ! command -v uv &> /dev/null; then
        log_error "uv 未安装，请先安装 uv"
        exit 1
    fi

    log_info "依赖检查完成"
}

# 检查 .env 文件
check_env_files() {
    log_info "检查环境变量文件..."

    if [[ ! -f "apps/backend/.env" ]]; then
        log_warn "apps/backend/.env 不存在，正在创建..."
        cp apps/backend/.env.example apps/backend/.env
        log_info "已创建 apps/backend/.env，请检查并配置必要的环境变量（特别是 AI API Key）"
    fi

    if [[ ! -f "apps/frontend/.env.local" ]]; then
        log_warn "apps/frontend/.env.local 不存在，正在创建..."
        cp apps/frontend/.env.example apps/frontend/.env.local
        log_info "已创建 apps/frontend/.env.local"
    fi

    log_info "环境变量文件检查完成"
}

# 启动中间件服务
start_middleware() {
    log_info "启动中间件服务 (PostgreSQL, Redis, MinIO)..."

    cd "$(dirname "$0")/.."

    if ! docker compose -f docker-compose.yml ps &> /dev/null; then
        log_info "正在启动中间件服务..."
        docker compose -f docker-compose.yml up -d
        log_info "中间件服务启动命令已执行""等待中间件服务就绪..."
        sleep 5

        # 检查服务状态
        for service in postgres redis minio; do
            for i in {1..10}; do
                if docker compose -f docker-compose.yml ps "$service" | grep -q "healthy"; then
                    log_info "服务 $service 已就绪"
                    break
                fi
                if [[ $i -eq 10 ]]; then
                    log_warn "服务 $service 可能未完全就绪，请手动检查"
                fi
                sleep 2
            done
        done
    else
        log_info "中间件服务已在运行"
    fi

    cd - > /dev/null
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    cd apps/backend

    if [[ ! -f ".env" ]]; then
        log_error "apps/backend/.env 不存在，请先运行脚本或手动创建"
        exit 1
    fi

    log_info "执行数据库迁移..."
    uv run alembic upgrade head

    log_info "数据库初始化完成"
    cd - > /dev/null
}

# 启动后端 API 服务
start_backend() {
    log_info "启动后端 API 服务..."

    cd apps/backend

    if [[ ! -f ".env" ]]; then
        log_error "apps/backend/.env 不存在，请先运行脚本或手动创建"
        exit 1
    fi

    log_info "启动 uvicorn 服务器..."
    log_info "后端 API 将运行在 http://127.0.0.1:8000"
    log_info "API 文档将运行在 http://127.0.0.1:8000/docs"

    uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
}

# 主流程
main() {
    log_info "=== CareerPilot 启动脚本 ==="
    log_info "开始启动服务..."

    check_dependencies
    check_env_files
    start_middleware
    init_database
    start_backend
}

# 执行主流程
main "$@"
