#!/usr/bin/env python3
"""
直接测试上传接口
"""

import asyncio
import sys
from pathlib import Path
import httpx

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8000"

async def test_upload():
    async with httpx.AsyncClient() as client:
        # 登录
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "testuser1@example.com",
                "password": "test123456",
            },
        )
        
        if login_response.status_code == 200:
            access_token = login_response.json()["data"]["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            # 上传简历
            resume_path = Path("/Users/zhengwenze/Desktop/resume.pdf")
            
            with open(resume_path, "rb") as f:
                files = {"file": ("resume.pdf", f, "application/pdf")}
                
                upload_response = await client.post(
                    f"{BASE_URL}/resumes/upload",
                    headers=auth_headers,
                    files=files,
                )
            
            print(f"上传状态码: {upload_response.status_code}")
            if upload_response.status_code == 201:
                resume_data = upload_response.json()["data"]
                resume_id = resume_data["id"]
                print(f"简历 ID: {resume_id}")
                print(f"latest_parse_job: {resume_data.get('latest_parse_job')}")
                
                # 等待几秒
                import time
                time.sleep(5)
                
                # 检查解析状态
                detail_response = await client.get(
                    f"{BASE_URL}/resumes/{resume_id}",
                    headers=auth_headers,
                )
                
                if detail_response.status_code == 200:
                    data = detail_response.json()["data"]
                    print(f"解析状态: {data['parse_status']}")
                    print(f"原始文本长度: {len(data.get('raw_text', ''))}")
                    print(f"有结构化数据: {data.get('structured_json') is not None}")
            else:
                print("上传失败")
                print(upload_response.json())

if __name__ == "__main__":
    asyncio.run(test_upload())
