# 发布到 PyPI 指南

## 准备工作

1. **创建 PyPI 账户**（如果还没有）
   - 访问 https://pypi.org/account/register/
   - 注册账户并验证邮箱

2. **安装构建工具**
   ```bash
   uv pip install build twine
   ```

## 发布步骤

### 1. 更新版本号

在 `pyproject.toml` 中更新版本号：
```toml
version = "0.1.0"  # 修改为新版本，如 "0.1.1"
```

同时更新 `paddleocr_cli/__init__.py` 中的版本号：
```python
__version__ = "0.1.0"  # 保持一致
```

### 2. 清理构建文件

```bash
# 删除旧的构建文件
rm -rf dist/ build/ *.egg-info
```

Windows PowerShell:
```powershell
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
```

### 3. 构建分发包

使用 `uv` 构建：
```bash
uv build
```

或者使用传统的 `build` 工具：
```bash
python -m build
```

这将创建：
- `dist/paddleocr-mcp-0.1.0.tar.gz` (源码包)
- `dist/paddleocr_mcp-0.1.0-py3-none-any.whl` (wheel 包)

### 4. 检查分发包

使用 `twine` 检查分发包：
```bash
uv pip install twine
twine check dist/*
```

### 5. 测试发布（可选，推荐）

先发布到 Test PyPI 进行测试：
```bash
# 上传到 Test PyPI
twine upload --repository testpypi dist/*

# 测试安装
pip install -i https://test.pypi.org/simple/ paddleocr-mcp
```

### 6. 发布到 PyPI

**方法 1: 使用 twine（推荐，最常用）**
```bash
twine upload dist/*
```

**方法 2: 使用 uv publish**
```bash
uv publish
```

**方法 3: 使用 uvx + twine**
```bash
uvx twine upload dist/*
```

系统会提示输入 PyPI 用户名和密码（或使用 API token）。

### 7. 使用 API Token（推荐）

更安全的方式是使用 API Token：

1. 在 https://pypi.org/manage/account/token/ 创建 API Token
2. 设置环境变量或使用配置文件：
   ```bash
   # Windows PowerShell
   $env:TWINE_USERNAME = "__token__"
   $env:TWINE_PASSWORD = "your-api-token-here"
   
   # Linux/Mac
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=your-api-token-here
   ```
3. 然后运行：
   ```bash
   twine upload dist/*
   ```

或者创建 `~/.pypirc` 文件：
```ini
[pypi]
username = __token__
password = your-api-token-here
```

## 验证发布

发布后，可以通过以下方式安装：
```bash
pip install paddleocr-mcp
```

或使用 `uvx`：
```bash
uvx paddleocr-mcp <image_path>
```

## 版本更新流程

每次发布新版本时：

1. 更新版本号（在 `pyproject.toml` 和 `__init__.py` 中）
2. 更新 `CHANGELOG.md`（如果有）
3. 提交更改
4. 构建分发包
5. 测试
6. 发布到 PyPI

## 注意事项

- ⚠️ PyPI 不允许删除或覆盖已发布的版本
- ✅ 如果发现错误，只能发布新的版本号
- ✅ 确保在发布前充分测试
- ✅ 考虑先在 Test PyPI 上测试
