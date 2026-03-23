# HTTPS 问题报告

## 问题描述

开启 HTTPS 后，前端页面可以正常访问，但前后端无法通信，导致登录注册功能失败。

## 根本原因

### 1. 混合内容问题（Mixed Content）

**现象：**
- 前端通过 HTTPS 访问：`https://codeclaw.top`
- 后端 API 通过 HTTP 访问：`http://codeclaw.top`
- 浏览器阻止了 HTTPS 页面中的 HTTP 请求

**浏览器错误：**
```
Mixed Content: The page at 'https://codeclaw.top' was loaded over HTTPS, 
but requested an insecure resource 'http://codeclaw.top/auth/register'. 
This request has been blocked; the content must be served over HTTPS.
```

**原因：**
- 前端环境变量 `NEXT_PUBLIC_API_BASE_URL` 配置为 `http://codeclaw.top`
- HTTPS 页面中的 HTTP 请求会被浏览器安全策略阻止

### 2. CORS 配置问题

**现象：**
- 前端域名：`https://codeclaw.top`
- 后端 CORS 配置：未包含 `https://codeclaw.top`

**原因：**
- 后端 `CORS_ORIGINS` 环境变量只包含 `http://localhost:3000`
- 服务器部署时未更新为包含 `https://codeclaw.top`

### 3. Nginx 配置问题

**现象：**
- Nginx 只配置了 HTTP 重定向到 HTTPS
- 没有正确配置 HTTPS 的反向代理

**原因：**
- Nginx 配置中缺少 HTTPS 的 `ssl_certificate` 和 `ssl_certificate_key`
- 或者 HTTPS 配置不完整

## 解决方案

### 1. 前端配置

**修改 `docker-compose.yml`：**

```yaml
frontend:
  environment:
    - NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL:-https://codeclaw.top}
```

**修改 `.env.example`：**

```env
NEXT_PUBLIC_API_BASE_URL=https://codeclaw.top
```

### 2. 后端 CORS 配置

**修改 `docker-compose.yml`：**

```yaml
backend:
  environment:
    - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000,https://codeclaw.top}
```

### 3. Nginx 配置

**确保 Nginx 配置包含 HTTPS：**

```nginx
server {
    listen 443 ssl http2;
    server_name codeclaw.top;

    ssl_certificate /etc/nginx/ssl/codeclaw.top.pem;
    ssl_certificate_key /etc/nginx/ssl/codeclaw.top.key;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name codeclaw.top;
    return 301 https://$server_name$request_uri;
}
```

### 4. 环境变量文件

**创建 `.env` 文件（服务器）：**

```env
NEXT_PUBLIC_API_BASE_URL=https://codeclaw.top
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://codeclaw.top
```

## 验证步骤

### 1. 检查前端环境变量

```bash
docker compose -f docker-compose.yml exec frontend printenv | grep NEXT_PUBLIC_API_BASE_URL
```

**预期输出：**
```
NEXT_PUBLIC_API_BASE_URL=https://codeclaw.top
```

### 2. 检查后端 CORS 配置

```bash
docker compose -f docker-compose.yml exec backend printenv | grep CORS_ORIGINS
```

**预期输出：**
```
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://codeclaw.top
```

### 3. 测试 API 接口

```bash
curl -s https://codeclaw.top/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -w "\nHTTP Status: %{http_code}\n"
```

**预期输出：**
```
{"success":true,"data":{...}}
HTTP Status: 200
```

### 4. 浏览器测试

1. 打开 `https://codeclaw.top`
2. 按 F12 打开开发者工具
3. 切换到 Network 标签页
4. 尝试注册或登录
5. 检查请求 URL、状态码、响应内容

**预期结果：**
- 所有请求使用 HTTPS
- 状态码为 200
- 响应内容正确

## 预防措施

### 1. 环境变量管理

- 创建 `.env.example` 作为模板
- 创建 `.env.local` 用于本地开发
- 创建 `.env.production` 用于服务器部署
- 将 `.env*` 文件加入 `.gitignore`

### 2. 配置检查清单

部署前检查：

- [ ] 前端 `NEXT_PUBLIC_API_BASE_URL` 使用 HTTPS
- [ ] 后端 `CORS_ORIGINS` 包含所有域名
- [ ] Nginx 配置包含 HTTPS 和 SSL 证书
- [ ] SSL 证书文件存在且权限正确
- [ ] 所有服务已重启

### 3. 日志检查

```bash
# 查看前端日志
docker compose -f docker-compose.yml logs -f frontend

# 查看后端日志
docker compose -f docker-compose.yml logs -f backend

# 查看 Nginx 日志
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

## 总结

**问题根源：**
1. 混合内容问题：HTTPS 页面中的 HTTP 请求被阻止
2. CORS 配置缺失：后端未允许 HTTPS 域名
3. Nginx 配置不完整：缺少 HTTPS 配置

**解决方案：**
1. 前端环境变量使用 HTTPS
2. 后端 CORS 配置包含 HTTPS 域名
3. Nginx 配置 HTTPS 和 SSL 证书
4. 统一环境变量管理

**关键配置：**
- 前端：`NEXT_PUBLIC_API_BASE_URL=https://codeclaw.top`
- 后端：`CORS_ORIGINS=...,https://codeclaw.top`
- Nginx：配置 SSL 证书和 HTTPS 反向代理
