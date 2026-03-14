-- 创建数据库
CREATE DATABASE "career-pilot";

-- 连接到数据库
\c "career-pilot"

-- 启用 vector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 用户表
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  nickname VARCHAR(80),
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);

-- 简历表
CREATE TABLE resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  file_name VARCHAR(255) NOT NULL,
  file_url TEXT NOT NULL,
  parse_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  raw_text TEXT,
  structured_json JSONB,
  latest_version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_parse_status ON resumes(parse_status);

-- JD 表
CREATE TABLE job_descriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255),
  jd_text TEXT NOT NULL,
  structured_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jds_user_id ON job_descriptions(user_id);

-- 知识分片表
CREATE TABLE knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type VARCHAR(30) NOT NULL,
  source_id UUID NOT NULL,
  chunk_text TEXT NOT NULL,
  chunk_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding VECTOR(1536),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunks_source ON knowledge_chunks(source_type, source_id);

-- Prompt 版本表
CREATE TABLE prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_name VARCHAR(50) NOT NULL,
  version_name VARCHAR(50) NOT NULL,
  template_text TEXT NOT NULL,
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- JD 匹配报告表
CREATE TABLE match_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  resume_id UUID NOT NULL REFERENCES resumes(id),
  jd_id UUID NOT NULL REFERENCES job_descriptions(id),
  overall_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  rule_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  model_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  gap_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_match_reports_user_id ON match_reports(user_id);
CREATE INDEX idx_match_reports_resume_jd ON match_reports(resume_id, jd_id);

-- 简历优化建议表
CREATE TABLE optimization_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_report_id UUID NOT NULL REFERENCES match_reports(id),
  advice_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  priority_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 项目话术表
CREATE TABLE project_scripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  resume_id UUID NOT NULL REFERENCES resumes(id),
  script_type VARCHAR(30) NOT NULL,
  content TEXT NOT NULL,
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 面试会话表
CREATE TABLE interview_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  resume_id UUID NOT NULL REFERENCES resumes(id),
  jd_id UUID NOT NULL REFERENCES job_descriptions(id),
  thread_id VARCHAR(100) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  interview_mode VARCHAR(30) NOT NULL DEFAULT 'mixed',
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON interview_sessions(user_id);
CREATE INDEX idx_sessions_status ON interview_sessions(status);

-- 面试轮次表
CREATE TABLE interview_turns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  turn_index INTEGER NOT NULL,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  score_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_turns_session_id ON interview_turns(session_id, turn_index);

-- 检索日志表
CREATE TABLE retrieval_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  turn_id UUID NOT NULL REFERENCES interview_turns(id),
  query_text TEXT NOT NULL,
  hit_chunks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  recall_label_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 面试总评表
CREATE TABLE interview_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL UNIQUE REFERENCES interview_sessions(id),
  total_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  dimension_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
  weaknesses_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  improvement_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 评测运行表
CREATE TABLE evaluation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_name VARCHAR(50) NOT NULL,
  dataset_name VARCHAR(100) NOT NULL,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
