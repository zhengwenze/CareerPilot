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
