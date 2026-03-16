import asyncio
import httpx

async def test_profile():
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient() as client:
        # 1. 注册用户
        print("=== 1. 注册用户 ===")
        register_response = await client.post(
            f"{base_url}/auth/register",
            json={
                "email": "testcurl@example.com",
                "password": "test123456",
                "nickname": "测试用户",
            },
        )
        print(f"状态码: {register_response.status_code}")
        print(f"响应: {register_response.json()}")
        
        if register_response.status_code == 201:
            access_token = register_response.json()["data"]["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            # 2. 获取用户资料（初始状态）
            print("\n=== 2. 获取用户资料（初始状态） ===")
            profile_response = await client.get(
                f"{base_url}/profile/me",
                headers=auth_headers
            )
            print(f"状态码: {profile_response.status_code}")
            print(f"响应: {profile_response.json()}")
            
            # 3. 更新用户资料
            print("\n=== 3. 更新用户资料 ===")
            update_response = await client.put(
                f"{base_url}/profile/me",
                headers=auth_headers,
                json={
                    "nickname": "阿泽",
                    "job_direction": "后端开发工程师",
                    "target_city": "北京",
                    "target_role": "Python后端开发",
                },
            )
            print(f"状态码: {update_response.status_code}")
            print(f"响应: {update_response.json()}")
            
            # 4. 再次获取用户资料（验证更新）
            print("\n=== 4. 验证更新后资料 ===")
            me_response = await client.get(
                f"{base_url}/profile/me",
                headers=auth_headers
            )
            print(f"状态码: {me_response.status_code}")
            print(f"响应: {me_response.json()}")
        else:
            print("注册失败，无法继续测试")

if __name__ == "__main__":
    asyncio.run(test_profile())
