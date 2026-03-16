#!/usr/bin/env python3
"""
检查最新简历的解析任务
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db_session
from app.models import Resume, ResumeParseJob

async def check_latest():
    async for session in get_db_session():
        # 获取最新的简历
        result = await session.execute(
            select(Resume)
            .order_by(desc(Resume.created_at))
            .limit(1)
        )
        resume = result.scalar_one_or_none()
        
        if resume:
            print(f"最新简历 ID: {resume.id}")
            print(f"文件名: {resume.file_name}")
            print(f"解析状态: {resume.parse_status}")
            
            # 获取解析任务
            result = await session.execute(
                select(ResumeParseJob)
                .where(ResumeParseJob.resume_id == resume.id)
                .order_by(desc(ResumeParseJob.created_at))
                .limit(1)
            )
            job = result.scalar_one_or_none()
            
            if job:
                print(f"\n最新解析任务 ID: {job.id}")
                print(f"状态: {job.status}")
                print(f"尝试次数: {job.attempt_count}")
                print(f"创建时间: {job.created_at}")
                print(f"开始时间: {job.started_at}")
                print(f"结束时间: {job.finished_at}")
        
        break

if __name__ == "__main__":
    asyncio.run(check_latest())
