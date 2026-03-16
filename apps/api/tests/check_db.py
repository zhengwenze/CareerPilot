#!/usr/bin/env python3
"""
检查数据库中的解析任务
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db_session
from app.models import Resume, ResumeParseJob

async def check_db():
    async for session in get_db_session():
        # 检查所有简历
        result = await session.execute(select(Resume))
        resumes = result.scalars().all()
        
        print(f"📊 数据库中有 {len(resumes)} 份简历:")
        for resume in resumes:
            print(f"\n简历 ID: {resume.id}")
            print(f"  文件名: {resume.file_name}")
            print(f"  解析状态: {resume.parse_status}")
            print(f"  原始文本长度: {len(resume.raw_text) if resume.raw_text else 0}")
            print(f"  有结构化数据: {resume.structured_json is not None}")
            print(f"  版本号: {resume.latest_version}")
        
        # 检查所有解析任务
        result = await session.execute(select(ResumeParseJob))
        jobs = result.scalars().all()
        
        print(f"\n📝 数据库中有 {len(jobs)} 个解析任务:")
        for job in jobs:
            print(f"\n任务 ID: {job.id}")
            print(f"  简历 ID: {job.resume_id}")
            print(f"  状态: {job.status}")
            print(f"  尝试次数: {job.attempt_count}")
            print(f"  错误信息: {job.error_message}")
            print(f"  创建时间: {job.created_at}")
            print(f"  开始时间: {job.started_at}")
            print(f"  结束时间: {job.finished_at}")
        
        break

if __name__ == "__main__":
    asyncio.run(check_db())
