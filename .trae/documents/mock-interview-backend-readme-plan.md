# 计划：创建模拟面试模块后端详细设计文档

## 目标
在 `/Users/zhengwenze/Desktop/codex/career-pilot/references/` 文件夹内创建一份全面的 README 文档，详细介绍模拟面试模块的后端设计流程、功能点和接口信息。

## 文档结构规划

### 1. 概述部分
- 模块定位和职责
- 与整体工作流的关系
- 核心特性概览

### 2. 架构设计
- 数据模型（ER 图描述）
  - MockInterviewSession
  - MockInterviewTurn
- 服务层架构
  - mock_interview.py（核心服务）
  - mock_interview_runtime.py（异步任务调度）
  - interview_review.py（深度点评服务）
- AI Prompt 体系

### 3. 核心流程详解
- 会话创建流程
- 问题准备流程（异步）
- 答题处理流程
- 深度点评生成流程
- 追问/切题决策流程
- 会话结束流程

### 4. 功能点清单
- 会话管理功能
- 问题生成功能
- 回答提交与处理
- 深度点评系统
- 追问逻辑
- 复盘总结

### 5. API 接口文档
- 端点列表
- 请求/响应格式
- 状态码说明
- 错误处理

### 6. 数据模型详解
- 字段说明
- 关系说明
- 约束条件

### 7. AI Prompt 设计
- Prompt 分类
- 输入输出格式
- 评分标准

### 8. 配置说明
- AI 提供商配置
- 模型选择
- 超时设置

## 实施步骤

1. 创建文档文件：`/Users/zhengwenze/Desktop/codex/career-pilot/references/mock-interview-backend-readme.md`
2. 按照上述结构编写完整文档
3. 确保包含代码示例和流程图（使用 Mermaid 语法）
4. 验证文档完整性和准确性

## 输出文件
- `/Users/zhengwenze/Desktop/codex/career-pilot/references/mock-interview-backend-readme.md`
