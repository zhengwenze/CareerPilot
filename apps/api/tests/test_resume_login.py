#!/usr/bin/env python3
"""
测试简历解析接口（使用已存在的用户）
"""

import asyncio
import sys
from pathlib import Path
import httpx
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8000"

async def test_resume_parsing():
    """测试简历上传和解析流程"""
    
    async with httpx.AsyncClient() as client:
        # 1. 登录用户
        print("=" * 60)
        print("步骤 1: 登录用户")
        print("=" * 60)
        
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "testuser1@example.com",
                "password": "test123456",
            },
        )
        
        print(f"状态码: {login_response.status_code}")
        if login_response.status_code == 200:
            print("✅ 用户登录成功")
            access_token = login_response.json()["data"]["access_token"]
        else:
            print("❌ 用户登录失败")
            print(login_response.json())
            return
        
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        # 2. 上传简历
        print("\n" + "=" * 60)
        print("步骤 2: 上传简历 PDF")
        print("=" * 60)
        
        resume_path = Path("/Users/zhengwenze/Desktop/resume.pdf")
        
        if not resume_path.exists():
            print(f"❌ 简历文件不存在: {resume_path}")
            return
        
        print(f"📄 简历文件: {resume_path}")
        print(f"📏 文件大小: {resume_path.stat().st_size / 1024:.2f} KB")
        
        with open(resume_path, "rb") as f:
            files = {"file": ("resume.pdf", f, "application/pdf")}
            
            upload_response = await client.post(
                f"{BASE_URL}/resumes/upload",
                headers=auth_headers,
                files=files,
            )
        
        print(f"状态码: {upload_response.status_code}")
        
        if upload_response.status_code == 201:
            print("✅ 简历上传成功")
            resume_data = upload_response.json()["data"]
            resume_id = resume_data["id"]
            print(f"简历 ID: {resume_id}")
            print(f"文件名: {resume_data['file_name']}")
            print(f"解析状态: {resume_data['parse_status']}")
        else:
            print("❌ 简历上传失败")
            print(upload_response.json())
            return
        
        # 3. 等待解析完成
        print("\n" + "=" * 60)
        print("步骤 3: 等待解析完成")
        print("=" * 60)
        
        max_wait = 60
        wait_interval = 2
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            detail_response = await client.get(
                f"{BASE_URL}/resumes/{resume_id}",
                headers=auth_headers,
            )
            
            if detail_response.status_code == 200:
                resume_detail = detail_response.json()["data"]
                status = resume_detail["parse_status"]
                print(f"[{elapsed}s] 解析状态: {status}")
                
                if status == "success":
                    print("✅ 解析成功!")
                    break
                elif status == "failed":
                    print("❌ 解析失败")
                    print(f"错误信息: {resume_detail.get('parse_error')}")
                    return
            else:
                print(f"❌ 获取详情失败: {detail_response.status_code}")
                return
        else:
            print(f"⏳ 超时（{max_wait}秒），解析仍在进行中")
        
        # 4. 查看解析结果
        print("\n" + "=" * 60)
        print("步骤 4: 查看解析结果")
        print("=" * 60)
        
        detail_response = await client.get(
            f"{BASE_URL}/resumes/{resume_id}",
            headers=auth_headers,
        )
        
        if detail_response.status_code == 200:
            resume_detail = detail_response.json()["data"]
            
            print(f"\n📄 原始文本预览（前 500 字符）:")
            print("-" * 60)
            raw_text = resume_detail.get("raw_text", "")[:500]
            print(raw_text)
            if len(resume_detail.get("raw_text", "")) > 500:
                print("...")
            
            print(f"\n📊 结构化数据:")
            print("-" * 60)
            structured = resume_detail.get("structured_json", {})
            
            if structured:
                basic_info = structured.get("basic_info", {})
                print(f"姓名: {basic_info.get('name', 'N/A')}")
                print(f"邮箱: {basic_info.get('email', 'N/A')}")
                print(f"手机: {basic_info.get('phone', 'N/A')}")
                print(f"地点: {basic_info.get('location', 'N/A')}")
                print(f"摘要: {basic_info.get('summary', 'N/A')[:100]}...")
                
                print(f"\n教育经历 ({len(structured.get('education', []))} 条):")
                for edu in structured.get("education", [])[:3]:
                    print(f"  - {edu[:80]}...")
                
                print(f"\n工作经历 ({len(structured.get('work_experience', []))} 条):")
                for exp in structured.get("work_experience", [])[:3]:
                    print(f"  - {exp[:80]}...")
                
                print(f"\n项目经历 ({len(structured.get('projects', []))} 条):")
                for proj in structured.get("projects", [])[:3]:
                    print(f"  - {proj[:80]}...")
                
                skills = structured.get("skills", {})
                print(f"\n技术技能: {', '.join(skills.get('technical', []))}")
                print(f"工具技能: {', '.join(skills.get('tools', []))}")
                print(f"语言能力: {', '.join(skills.get('languages', []))}")
                
                print(f"\n证书与奖项 ({len(structured.get('certifications', []))} 条):")
                for cert in structured.get("certifications", [])[:3]:
                    print(f"  - {cert[:80]}...")
            else:
                print("❌ 未找到结构化数据")
            
            print(f"\n🔢 版本号: v{resume_detail.get('latest_version', 1)}")
            print(f"📅 创建时间: {resume_detail.get('created_at', 'N/A')}")
            print(f"📅 更新时间: {resume_detail.get('updated_at', 'N/A')}")
        
        # 5. 查看解析任务记录
        print("\n" + "=" * 60)
        print("步骤 5: 查看解析任务记录")
        print("=" * 60)
        
        jobs_response = await client.get(
            f"{BASE_URL}/resumes/{resume_id}/parse-jobs",
            headers=auth_headers,
        )
        
        if jobs_response.status_code == 200:
            jobs = jobs_response.json()["data"]
            print(f"共 {len(jobs)} 条解析任务记录:")
            
            for job in jobs:
                print(f"\n  任务 ID: {job['id']}")
                print(f"  状态: {job['status']}")
                print(f"  尝试次数: {job['attempt_count']}")
                print(f"  创建时间: {job['created_at']}")
                if job.get('started_at'):
                    print(f"  开始时间: {job['started_at']}")
                if job.get('finished_at'):
                    print(f"  结束时间: {job['finished_at']}")
                if job.get('error_message'):
                    print(f"  错误信息: {job['error_message']}")
        
        # 6. 测试获取简历列表
        print("\n" + "=" * 60)
        print("步骤 6: 测试获取简历列表")
        print("=" * 60)
        
        list_response = await client.get(
            f"{BASE_URL}/resumes",
            headers=auth_headers,
        )
        
        if list_response.status_code == 200:
            resumes = list_response.json()["data"]
            print(f"✅ 共 {len(resumes)} 份简历")
            for resume in resumes:
                print(f"  - {resume['file_name']} (状态: {resume['parse_status']}, 版本: v{resume['latest_version']})")
        else:
            print("❌ 获取简历列表失败")
            print(list_response.json())
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_resume_parsing())
