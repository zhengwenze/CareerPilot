#!/bin/bash
set -euo pipefail

# CareerPilot Linux 服务器部署脚本
# 用途：在 Linux 服务器上快速部署完整应用（Docker Compose）
# 用法：./docker/deploy.sh [dev|prod]
#
#   dev   - 开发/测试环境（默认），热更新、调试模式
#   prod  - 生产环境，优化构建、无卷挂载

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_step "检查依赖环境..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        echo "请先安装 Docker：https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        echo "请先安装 Docker Compose：https://docs.docker.com/compose/install/"
        exit 1
    fi

    log_info "依赖检查完成"
}

# 检查并创建 .env 文件
check_env_files() {
    log_step "检查环境变量文件..."

    cd "$(dirname "$0")/.."

    if [[ ! -f "apps/backend/.env" ]]; then
        log_warn "apps/backend/.env 不存在，正在创建..."
        cp apps/backend/.env.example apps/backend/.env
        log_info "已创建 apps/backend/.env"
        echo ""
        echo "请编辑 apps/backend/.env 文件，配置以下关键项："
        echo "  - JWT_SECRET_KEY（建议使用：openssl rand -hex 32）"
        echo "  - RESUME_AI_API_KEY（AI 提供商 API Key）"
        echo "  - MATCH_AI_API_KEY（AI 提供商 API Key）"
        echo ""
        read -p "是否现在编辑？(y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} apps/backend/.env
        fi
    else
        log_info "apps/backend/.env 已存在"
    fi

    cd - > /dev/null
}

# 启动开发环境
start_dev() {
    log_step "启动开发环境..."

    cd "$(dirname "$0")/.."

    log_info "正在启动 PostgreSQL, Redis, MinIO, Backend, Frontend (开发模式)..."
    docker compose -f docker-compose.yml up -d

    log_info "服务启动命令已执行，等待服务就绪..."
    sleep 5

    log_info "服务状态："
    docker compose -f docker-compose.yml ps

    cd - > /dev/null
}

# 启动生产环境
start_prod() {
    log_step "启动生产环境..."

    cd "$(dirname "$0")/.."

    log_info "正在构建并启动所有服务 (生产模式)..."
    log_info "这可能需要几分钟进行 Docker 镜像构建..."

    docker compose -f docker-compose.prod.yml up -d --build

    log_info "服务启动命令已执行，等待服务就绪..."
    sleep 10

    log_info "服务状态："
    docker compose -f docker-compose.prod.yml ps

    cd - > /dev/null
}

# 查看服务日志
show_logs() {
    local compose_file="${1:-docker-compose.yml}"
    log_step "查看服务日志..."

    cd "$(dirname "$0")/.."

    echo "按 Ctrl+C 停止查看"
    docker compose -f "$compose_file" logs -f

    cd - > /dev/null
}

# 显示部署完成信息
show_completion_info() {
    local mode="${1:-dev}"
    cd "$(dirname "$0")/.."

    echo ""
    echo "=============================================="
    echo -e "${GREEN}部署完成！${NC}"
    echo "=============================================="
    echo ""
    echo "部署模式: $mode"
    echo ""
    echo "访问地址："

    if [[ "$mode" == "prod" ]]; then
        echo "  - 应用前端：  http://<服务器IP>"
        echo "  - 后端 API：  http://<服务器IP>:8000"
        echo "  - API 文档：  http://<服务器IP>:8000/docs"
        echo "  - MinIO 控制台：http://<服务器IP>:9001"
    else
        echo "  - 应用前端：  http://localhost:3000"
        echo "  - 后端 API：  http://localhost:8000"
        echo "  - API 文档：  http://localhost:8000/docs"
        echo "  - MinIO 控制台：http://localhost:9001"
    fi

    echo ""
    echo "常用命令："

    if [[ "$mode" == "prod" ]]; then
        echo "  - 查看服务状态：  docker compose -f docker-compose.prod.yml ps"
        echo "  - 查看服务日志：  docker compose -f docker-compose.prod.yml logs -f"
        echo "  - 停止所有服务：  docker compose -f docker-compose.prod.yml down"
        echo "  - 重启服务：      docker compose -f docker-compose.prod.yml restart"
        echo "  - 重新构建并启动：docker compose -f docker-compose.prod.yml up -d --build"
    else
        echo "  - 查看服务状态：  docker compose -f docker-compose.yml ps"
        echo "  - 查看服务日志：  docker compose -f docker-compose.yml logs -f"
        echo "  - 停止所有服务：  docker compose -f docker-compose.yml down"
        echo "  - 重启服务：      docker compose -f docker-compose.yml restart"
    fi

    echo ""
    echo "如需查看实时日志，请运行："
    echo "  ./docker/deploy.sh logs"
    echo ""
    echo "首次使用前，请确保已配置 AI 提供商 API Key"
    echo "=============================================="

    cd - > /dev/null
}

# 主流程
main() {
    local mode="${1:-dev}"

    if [[ "$mode" != "dev" && "$mode" != "prod" ]]; then
        echo "用法：$0 {dev|prod|logs|stop|restart|status}"
        echo ""
        echo "模式说明："
        echo "  dev   - 开发/测试环境（默认），热更新、调试模式"
        echo "  prod  - 生产环境，优化构建、无卷挂载"
        echo ""
        echo "命令说明："
        echo "  deploy dev  - 部署并启动所有服务（开发模式，默认）"
        echo "  deploy prod - 部署并启动所有服务（生产模式）"
        echo "  logs        - 查看服务日志"
        echo "  stop        - 停止所有服务"
        echo "  restart     - 重启所有服务"
        echo "  status      - 查看服务状态"
        exit 1
    fi

    log_step "=== CareerPilot Linux 服务器部署脚本 ==="
    echo ""

    check_dependencies
    check_env_files

    if [[ "$mode" == "prod" ]]; then
        start_prod
    else
        start_dev
    fi

    show_completion_info "$mode"
}

# 命令行参数处理
case "${1:-deploy}" in
    deploy)
        main "${2:-dev}"
        ;;
    dev)
        main "dev"
        ;;
    prod)
        main "prod"
        ;;
    logs)
        cd "$(dirname "$0")/.."
        if [[ -f "docker-compose.prod.yml" ]] && docker compose -f docker-compose.prod.yml ps &> /dev/null; then
            log_step "查看生产环境服务日志（按 Ctrl+C 停止）..."
            docker compose -f docker-compose.prod.yml logs -f
        else
            log_step "查看开发环境服务日志（按 Ctrl+C 停止）..."
            docker compose -f docker-compose.yml logs -f
        fi
        cd - > /dev/null
        ;;
    stop)
        cd "$(dirname "$0")/.."
        log_step "停止所有服务..."
        docker compose -f docker-compose.yml down 2>/dev/null || true
        docker compose -f docker-compose.prod.yml down 2>/dev/null || true
        cd - > /dev/null
        ;;
    restart)
        cd "$(dirname "$0")/.."
        log_step "重启所有服务..."
        docker compose -f docker-compose.yml restart 2>/dev/null || true
        docker compose -f docker-compose.prod.yml restart 2>/dev/null || true
        cd - > /dev/null
        ;;
    status)
        cd "$(dirname "$0")/.."
        log_step "服务状态："
        echo "--- 开发环境 ---"
        docker compose -f docker-compose.yml ps 2>/dev/null || echo "未运行"
        echo ""
        echo "--- 生产环境 ---"
        docker compose -f docker-compose.prod.yml ps 2>/dev/null || echo "未运行"
        cd - > /dev/null
        ;;
    *)
        main "dev"
        ;;
esac
