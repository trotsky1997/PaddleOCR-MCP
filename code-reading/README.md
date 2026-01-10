# PaddleOCR-MCP 代码库阅读文档

本文档提供了对 PaddleOCR-MCP 代码库的系统性理解和分析。

## 文档导航

- **[code-reading.md](code-reading.md)** - 主要阅读文档（方法论、发现、术语表）
- **[architecture.md](architecture.md)** - 架构图（C4模型）
- **[api-flow.md](api-flow.md)** - API执行流程追踪
- **[key-modules.md](key-modules.md)** - 核心模块详细分析

## 阅读目标

本次代码库阅读的目标是：
**理解 PaddleOCR MCP 服务器的架构、执行流程和核心功能，能够安全地修改和扩展代码**

## 项目概览

PaddleOCR-MCP 是一个基于 Model Context Protocol (MCP) 的服务器，提供图像OCR文字识别功能。核心特点：

- **单一工具**: `ocr_image` - 接受图像路径，返回Markdown文件路径
- **自动优化**: 图像预处理、OCR实例缓存、性能优化
- **协议**: 使用 stdio 传输，JSON-RPC 2.0 协议
- **依赖**: PaddleOCR 2.7+, MCP SDK, PIL

## 快速开始

### 运行项目

```bash
# 通过模块运行
python -m paddleocr_cli.mcp_server

# 通过uvx运行（推荐）
uvx fast-paddleocr-mcp
```

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=paddleocr_cli --cov-report=html
```

## 核心执行流程

1. **MCP客户端请求** → `tools/call` 方法，工具名 `ocr_image`
2. **参数验证** → 检查 `image_path` 和 `language` 参数
3. **图像预处理** → 格式转换、降采样、锐化
4. **OCR识别** → 调用 PaddleOCR 进行文字识别
5. **结果处理** → 提取文本，生成Markdown文件
6. **返回路径** → 返回生成的文件路径（image_path + .md）

详细流程请参考 [api-flow.md](api-flow.md)

## 关键模块

- **`mcp_server.py`** - 主服务器实现
  - `handle_list_tools()` - 工具列表
  - `handle_call_tool()` - 工具调用处理
  - `get_ocr()` - OCR实例管理（缓存）
  - `preprocess_image()` - 图像预处理
  - `main_async()` / `main()` - 服务器入口

详细分析请参考 [key-modules.md](key-modules.md)

## 架构层次

- **系统上下文**: MCP客户端 ↔ PaddleOCR-MCP服务器 ↔ PaddleOCR库
- **容器**: 单一stdin/stdout进程
- **组件**: MCP服务器、OCR管理器、图像预处理器

详细架构请参考 [architecture.md](architecture.md)

## 更新日志

- **2024-XX-XX**: 初始代码库阅读文档创建
