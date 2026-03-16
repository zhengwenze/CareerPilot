#!/usr/bin/env python3
"""
检查简历状态
"""

import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def check_resume_status():
    async with httpx.AsyncClient() as client:
        # 1. 注册用户
        register_response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "checktest@example.com",
                "password": "test123456",
                "nickname": "检查测试用户",
            },
        )
        
        if register_response.status_code == 201:
            access_token = register_response.json()["data"]["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            # 2. 上传简历
            resume_path = "/Users/zhengwenze/Desktop/resume.pdf"
            
            with open(resume_path, "rb") as f:
                files = {"file": ("resume.pdf", f, "application/pdf")}
                
                upload_response = await client.post(
                    f"{BASE_URL}/resumes/upload",
                    headers=auth_headers,
                    files=files,
                )
            
            if upload_response.status_code == 201:
                resume_id = upload_response.json()["data"]["id"]
                print(f"✅ 简历上传成功: {resume_id}")
                
                # 3. 等待解析
                import time
                for i in range(15):
                    time.sleep(2)
                    
                    detail_response = await client.get(
                        f"{BASE_URL}/resumes/{resume_id}",
                        headers=auth_headers,
                    )
                    
                    if detail_response.status_code == 200:
                        data = detail_response.json()["data"]
                        status = data["parse_status"]
                        print(f"[{i*2}s] 状态: {status}")
                        
                        if status == "success":
                            print("\n✅ 解析成功!")
                            print(f"原始文本长度: {len(data.get('raw_text', ''))}")
                            print(f"结构化数据: {data.get('structured_json') is not None}")
                            break
                        elif status == "failed":
                            print(f"\n❌ 解析失败: {data.get('parse_error')}")
                            break
            
            # 4. 检查解析任务
            jobs_response = await client.get(
                f"{BASE_URL}/resumes/{resume_id}/parse-jobs",
                headers=auth_headers,
            )
            
            if jobs_response.status_code == 200:
                jobs = jobs_response.json()["data"]
                print(f"\n解析任务记录: {len(jobs)} 条")
                for job in jobs:
                    print(f"  状态: {job['status']}, 尝试: {job['attempt_count']}")
                    if job.get('error_message'):
                        print(f"  错误: {job['error_message']}")

if __name__ == "__main__":
    asyncio.run(check_resume_status())
