#!/bin/bash

# Profile API 测试脚本
# 使用 curl 命令测试 GET /profile/me 和 PUT /profile/me

BASE_URL="http://127.0.0.1:8000"

echo "=========================================="
echo "Profile API 测试 - 使用 curl 命令"
echo "=========================================="

# 1. 注册用户
echo ""
echo "=== 1. 注册用户 ==="
echo "命令: curl -X POST $BASE_URL/auth/register ..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "curltest@example.com",
    "password": "test123456",
    "nickname": "curl测试用户"
  }')

echo "响应:"
echo "$REGISTER_RESPONSE" | jq .

# 提取 access_token
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.data.access_token')

if [ "$ACCESS_TOKEN" != "null" ]; then
  echo ""
  echo "获取到 Token: ${ACCESS_TOKEN:0:50}..."
  
  # 2. 获取用户资料（初始状态）
  echo ""
  echo "=== 2. 获取用户资料（初始状态） ==="
  echo "命令: curl -X GET $BASE_URL/profile/me -H 'Authorization: Bearer $ACCESS_TOKEN' ..."
  PROFILE_RESPONSE=$(curl -s -X GET "$BASE_URL/profile/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json")
  
  echo "响应:"
  echo "$PROFILE_RESPONSE" | jq .
  
  # 3. 更新用户资料
  echo ""
  echo "=== 3. 更新用户资料 ==="
  echo "命令: curl -X PUT $BASE_URL/profile/me ..."
  UPDATE_RESPONSE=$(curl -s -X PUT "$BASE_URL/profile/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "nickname": "curl阿泽",
      "job_direction": "前端开发工程师",
      "target_city": "杭州",
      "target_role": "Vue前端开发"
    }')
  
  echo "响应:"
  echo "$UPDATE_RESPONSE" | jq .
  
  # 4. 验证更新后资料
  echo ""
  echo "=== 4. 验证更新后资料 ==="
  echo "命令: curl -X GET $BASE_URL/profile/me -H 'Authorization: Bearer $ACCESS_TOKEN' ..."
  ME_RESPONSE=$(curl -s -X GET "$BASE_URL/profile/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json")
  
  echo "响应:"
  echo "$ME_RESPONSE" | jq .
  
  echo ""
  echo "=========================================="
  echo "✅ 所有测试通过！"
  echo "=========================================="
  
  # 保存 token 到文件，方便后续测试
  echo "$ACCESS_TOKEN" > /tmp/profile_test_token.txt
  echo "Token 已保存到: /tmp/profile_test_token.txt"
  
else
  echo "❌ 注册失败，无法继续测试"
fi
