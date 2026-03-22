#!/bin/bash
set -euo pipefail

# CareerPilot Linux 服务器一键部署脚本
# 用途：在 Linux 服务器上快速部署完整应用（Docker Compose）
# 用法：./docker/deploy.sh

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

# 启动所有服务
start_services() {
    log_step "启动所有服务..."

    cd "$(dirname "$0")/.."

    log_info "正在启动 PostgreSQL, Redis, MinIO, Backend, Frontend..."
    docker compose -f docker-compose.yml up -d

    log_info "服务启动命令已执行，等待服务就绪..."
    sleep 5

    log_info "服务状态："
    docker compose -f docker-compose.yml ps

    cd - > /dev/null
}

# 查看服务日志
show_logs() {
    log_step "查看服务日志..."

    cd "$(dirname "$0")/.."

    echo "按 Ctrl+C 停止查看"
    docker compose -f docker-compose.yml logs -f

    cd - > /dev/null
}

# 显示部署完成信息
show_completion_info() {
    cd "$(dirname "$0")/.."

    echo ""
    echo "=============================================="
    echo -e "${GREEN}部署完成！${NC}"
    echo "=============================================="
    echo ""
    echo "访问地址："
    echo "  - 应用前端：  http://<服务器IP>:3000"
    echo "  - 后端 API：  http://<服务器IP>:8000"
    echo "  - API 文档：  http://<服务器IP>:8000/docs"
    echo "  - MinIO 控制台：http://<服务器IP>:9001"
    echo ""
    echo "常用命令："
    echo "  - 查看服务状态：  docker compose -f docker-compose.yml ps"
    echo "  - 查看服务日志：  docker compose -f docker-compose.yml logs -f"
    echo "  - 停止所有服务：  docker compose -f docker-compose.yml down"
    echo "  - 重启服务：      docker compose -f docker-compose.yml restart"
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
    log_step "=== CareerPilot Linux 服务器部署脚本 ==="
    echo ""

    check_dependencies
    check_env_files
    start_services
    show_completion_info
}

# 命令行参数处理
case "${1:-deploy}" in
    deploy)
        main
        ;;
    logs)
        cd "$(dirname "$0")/.."
        log_step "查看服务日志（按 Ctrl+C 停止）..."
        docker compose -f docker-compose.yml logs -f
        cd - > /dev/null
        ;;
    stop)
        cd "$(dirname "$0")/.."
        log_step "停止所有服务..."
        docker compose -f docker-compose.yml down
        cd - > /dev/null
        ;;
    restart)
        cd "$(dirname "$0")/.."
        log_step "重启所有服务..."
        docker compose -f docker-compose.yml restart
        cd - > /dev/null
        ;;
    status)
        cd "$(dirname "$0")/.."
        log_step "服务状态："
        docker compose -f docker-compose.yml ps
        cd - > /dev/null
        ;;
    *)
        echo "用法：$0 {deploy|logs|stop|restart|status}"
        echo ""
        echo "命令说明："
        echo "  deploy  - 部署并启动所有服务（默认）"
        echo "  logs    - 查看服务日志"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        exit 1
        ;;
esac
