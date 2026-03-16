# Scripts 目录

本目录用于存放具有独立功能的 Python 脚本，这些脚本在测试验证通过后，才会被集成到后端 API 中。

## 目录结构

```
scripts/
├── README.md                    # 本说明文档
├── requirements.txt             # 脚本依赖（可选）
├── utils/                       # 工具函数
│   └── __init__.py
├── test_*.py                    # 测试脚本
└── *.py                         # 独立功能脚本
```

## 使用规范

1. **独立性**：每个脚本应该是自包含的，可以独立运行
2. **测试优先**：在脚本中添加 `if __name__ == "__main__":` 用于测试
3. **清晰命名**：使用 `test_` 前缀表示测试脚本
4. **版本控制**：测试通过后删除测试脚本，将功能集成到 `apps/api/`

## 示例

```python
#!/usr/bin/env python
"""独立功能脚本示例"""

def main():
    """主函数"""
    print("功能测试中...")
    # 实现功能逻辑
    result = some_function()
    print(f"结果: {result}")

def some_function():
    """功能实现"""
    return "测试通过"

if __name__ == "__main__":
    main()
```

## 运行方式

```bash
# 运行脚本
uv run python scripts/test_example.py

# 运行独立功能脚本
uv run python scripts/example.py
```


可以。这个问题其实很适合拿来学“怎么排查一条跨前后端链路的故障”。

**核心方法**

我不是先猜“前端坏了”或“PDF 解析器坏了”，而是把整条链路拆开，一段一段排除：

1. 上传有没有成功
2. 后端有没有创建 parse job
3. parse job 有没有从 `pending` 进入 `processing`
4. PDF 文本有没有被提取出来
5. 结构化结果有没有写回数据库
6. 前端是不是只是没展示出来

只要每一步都拿证据，不靠感觉，最后根因会自己浮出来。

**这次我是怎么查的**

第一步，我先验证“真实 PDF 能不能被读出文字”。  
我直接用你桌面的 `/Users/zhengwenze/Desktop/resume.pdf` 调用后端解析函数，结果发现 `pypdf` 是能抽出原始文本的。  
这一步很关键，因为它直接排除了“PDF 本身完全不可解析”这个大方向。

第二步，我验证“后端主链路逻辑本身能不能跑通”。  
我没有立刻去点前端页面，而是用测试客户端直接走上传接口，结果发现：
- 上传成功
- job 能创建
- 在测试环境里能进入 `success`

这说明代码框架不是完全坏的，问题更像是“真实运行环境”或“真实数据状态”。

第三步，我盯状态流转。  
你前端日志里最关键的信息不是报错文本，而是这个事实：

- 每次 `retry` 后，`latestParseJobStatus` 还是 `pending`
- parse job 数量一直增加
- 但没有一个进入 `processing`

这说明不是前端轮询坏了，而是后端任务根本没真正执行起来，或者一启动就崩了。

第四步，我看后端真实日志，而不是只看前端日志。  
一看就发现两个根因：

1. 认证接口 500 的根因  
   后端连接数据库时 `localhost` 解析异常，所以注册登录失败。
2. 简历解析卡 `pending` 的根因  
   parse job 在更新 `started_at` 时崩了，异常是：
   `can't subtract offset-naive and offset-aware datetimes`

这句异常一出来，问题就从“系统层面模糊故障”变成了“一个具体字段写入类型不匹配”。

**为什么能这么快定位**

因为我一直在找“系统里第一个不符合预期的点”。

比如这次预期状态应该是：

- `pending -> processing -> success`

而实际是：

- 一直 `pending`

那就不要去想一百种可能，只问一句：

“是谁阻止了它从 `pending` 变成 `processing`？”

然后顺着这一步去查日志，最后就看到是 `started_at` 写库崩了。

**这次具体修了什么**

1. 修复本地依赖服务连接  
在 [config.py](/Users/zhengwenze/Desktop/codex/career-pilot/apps/api/app/core/config.py) 里，把 `localhost` 自动规范成 `127.0.0.1`，解决数据库/Redis/MinIO 连接异常。

2. 修复 parse job 时间写库  
在 [resume.py](/Users/zhengwenze/Desktop/codex/career-pilot/apps/api/app/services/resume.py) 里，把带时区的 UTC 时间改成无时区时间去写 `TIMESTAMP WITHOUT TIME ZONE` 字段。

3. 增加任务自愈  
在 [resumes.py](/Users/zhengwenze/Desktop/codex/career-pilot/apps/api/app/api/routes/resumes.py) 里加了补调度逻辑，避免任务丢了以后永远卡住。

4. 补测试  
我不是修完就算了，而是补了回归测试，确保以后不会再被同类问题打回来。

**你可以直接学的排查套路**

以后遇到类似问题，按这个顺序来：

1. 先定义“预期状态流转”  
比如上传解析就是 `pending -> processing -> success/failed`

2. 找“第一个偏离预期的节点”  
不要一上来就通篇乱看代码

3. 用真实数据复现  
能用真实文件就别只靠 mock

4. 区分“代码逻辑问题”和“运行环境问题”  
这次注册登录失败就是环境配置问题，解析卡住是代码+数据库字段问题

5. 优先看后端日志里的第一条真实异常  
不是看最后的 500，而是看第一条 stack trace

6. 修完必须补测试  
否则只是这次运气好，不算真正解决

**这次最值得你记住的一点**

前端看到的“不可用”，往往不是前端问题。  
真正高水平的排查，不是盯着报错页面猜，而是把链路拆开，找到“第一个失真的状态”。
