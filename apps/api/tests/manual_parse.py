#!/usr/bin/env python3
"""
手动触发简历解析
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.models import Resume, ResumeParseJob
from app.services.resume_parser import build_structured_resume, extract_text_from_pdf_bytes
from app.services.storage import MinioObjectStorage
from app.core.config import get_settings

async def manual_parse_resume(resume_id: UUID):
    """手动触发简历解析"""
    
    # 获取数据库会话
    async for session in get_db_session():
        # 获取简历和解析任务
        resume = await session.get(Resume, resume_id)
        if resume is None:
            print(f"❌ 简历 {resume_id} 不存在")
            return
        
        # 获取最新的解析任务
        from sqlalchemy import select, desc
        result = await session.execute(
            select(ResumeParseJob)
            .where(ResumeParseJob.resume_id == resume_id)
            .order_by(desc(ResumeParseJob.created_at))
            .limit(1)
        )
        parse_job = result.scalar_one_or_none()
        
        if parse_job is None:
            print(f"❌ 简历 {resume_id} 没有解析任务")
            return
        
        print(f"📄 开始解析简历: {resume.file_name}")
        print(f"📊 任务 ID: {parse_job.id}")
        
        # 更新任务状态
        parse_job.status = "processing"
        parse_job.attempt_count += 1
        parse_job.error_message = None
        from datetime import datetime
        parse_job.started_at = datetime.now()
        parse_job.updated_by = resume.user_id
        resume.parse_status = "processing"
        resume.parse_error = None
        resume.updated_by = resume.user_id
        session.add(resume)
        session.add(parse_job)
        await session.commit()
        
        try:
            # 获取存储配置
            settings = get_settings()
            
            # 创建存储客户端
            storage = MinioObjectStorage(
                endpoint=settings.storage_endpoint,
                access_key=settings.storage_access_key,
                secret_key=settings.storage_secret_key,
                secure=settings.storage_use_ssl,
            )
            
            # 从 MinIO 获取 PDF 文件
            print("📥 从 MinIO 获取 PDF 文件...")
            file_bytes = await storage.get_object_bytes(
                bucket_name=resume.storage_bucket,
                object_key=resume.storage_object_key,
            )
            print(f"✅ 获取成功，文件大小: {len(file_bytes)} 字节")
            
            # 提取原始文本
            print("📝 提取原始文本...")
            raw_text = extract_text_from_pdf_bytes(file_bytes)
            print(f"✅ 提取成功，文本长度: {len(raw_text)} 字符")
            
            # 结构化解析
            print("📊 结构化解析...")
            structured = build_structured_resume(raw_text)
            print("✅ 结构化解析成功")
            
            # 更新简历和任务
            resume.raw_text = raw_text
            resume.structured_json = structured.model_dump()
            resume.parse_status = "success"
            resume.parse_error = None
            resume.latest_version = max(resume.latest_version, 1)
            parse_job.status = "success"
            parse_job.error_message = None
            
            # 更新时间
            from datetime import datetime
            finished_at = datetime.now()
            resume.updated_by = resume.user_id
            parse_job.updated_by = resume.user_id
            parse_job.finished_at = finished_at
            
            session.add(resume)
            session.add(parse_job)
            await session.commit()
            
            print("✅ 解析完成!")
            print(f"   原始文本长度: {len(raw_text)}")
            print(f"   有结构化数据: {resume.structured_json is not None}")
            print(f"   版本号: {resume.latest_version}")
            
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            resume.parse_status = "failed"
            resume.parse_error = str(e)
            parse_job.status = "failed"
            parse_job.error_message = str(e)
            
            finished_at = datetime.now(UTC)
            resume.updated_by = resume.user_id
            parse_job.updated_by = resume.user_id
            parse_job.finished_at = finished_at
            
            session.add(resume)
            session.add(parse_job)
            await session.commit()
        
        break

if __name__ == "__main__":
    # 使用数据库中的第一个简历 ID
    import sys
    if len(sys.argv) > 1:
        resume_id = UUID(sys.argv[1])
    else:
        # 使用数据库中的第一个简历
        resume_id = UUID("afe1c9d5-561c-448b-a18d-a83fe7577b04")
    
    print(f"🔧 手动触发简历解析: {resume_id}")
    asyncio.run(manual_parse_resume(resume_id))
