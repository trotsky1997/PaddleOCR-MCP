# PaddleOCR-MCP 架构文档 (C4模型)

本文档使用 C4 模型描述 PaddleOCR-MCP 的架构，从系统上下文到组件级别。

## Level 1: 系统上下文 (System Context)

### 系统概览

PaddleOCR-MCP 是一个 MCP (Model Context Protocol) 服务器，为 AI 助手提供图像 OCR 文字识别能力。

```
┌─────────────────────────────────────────────────────────────┐
│                      System Context                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐                    ┌──────────────┐     │
│   │  MCP Client  │                    │   File System│     │
│   │  (Cursor,    │                    │              │     │
│   │   Claude     │                    │  - Input     │     │
│   │   Desktop,   │                    │    images    │     │
│   │   etc.)      │                    │  - Output    │     │
│   └──────┬───────┘                    │    .md files │     │
│          │                            └──────┬───────┘     │
│          │ JSON-RPC 2.0                      │              │
│          │ (stdio)                           │              │
│          ▼                                   │              │
│   ┌──────────────────────────────────────┐  │              │
│   │    PaddleOCR-MCP Server              │  │              │
│   │                                      │◄─┘              │
│   │  - MCP Protocol Handler              │                 │
│   │  - OCR Manager                       │                 │
│   │  - Image Preprocessor                │                 │
│   └──────────────┬───────────────────────┘                 │
│                  │                                          │
│                  │ Python API                               │
│                  ▼                                          │
│   ┌──────────────────────────────────────┐                 │
│   │      PaddleOCR Library               │                 │
│   │                                      │                 │
│   │  - Detection Model (PP-OCRv4)        │                 │
│   │  - Recognition Model (PP-OCRv4)      │                 │
│   │  - Deep Learning Framework           │                 │
│   └──────────────────────────────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 用户和外部系统

**MCP客户端** (如 Cursor, Claude Desktop)
- **角色**: 调用OCR服务的客户端
- **通信方式**: JSON-RPC 2.0 over stdio
- **交互**: 发送工具调用请求，接收结果文件路径

**文件系统**
- **角色**: 存储输入图像和输出Markdown文件
- **交互**: 
  - 读取输入图像文件
  - 写入输出Markdown文件（`image_path + .md`）
  - 创建临时预处理图像文件

**PaddleOCR库**
- **角色**: 提供OCR核心功能
- **接口**: Python API (`PaddleOCR` 类)
- **功能**: 图像文字检测和识别

### 系统边界

- **内部**: MCP协议处理、OCR实例管理、图像预处理、结果格式化
- **外部**: PaddleOCR库（深度学习模型）、文件系统（持久化）

## Level 2: 容器 (Containers)

### 部署单元

单一可执行进程，无其他容器：

```
┌────────────────────────────────────────────────────┐
│            PaddleOCR-MCP Process                    │
├────────────────────────────────────────────────────┤
│                                                     │
│  Transport: stdio (stdin/stdout)                   │
│  Protocol: JSON-RPC 2.0                            │
│  Language: Python 3.8+                             │
│  Runtime: Single process, synchronous processing   │
│                                                     │
│  Entry Point:                                      │
│    - main() → main_async()                         │
│    - python -m paddleocr_cli.mcp_server            │
│                                                     │
│  State:                                            │
│    - Stateless (per request)                       │
│    - In-memory OCR cache (ocache)                  │
│                                                     │
└────────────────────────────────────────────────────┘
```

### 容器特征

- **通信**: 通过标准输入输出（stdio）进行JSON-RPC通信
- **状态管理**: 基本无状态，但维护OCR实例缓存（内存中）
- **并发**: 同步处理请求，每个请求完整处理后返回
- **扩展性**: 水平扩展（启动多个进程），但无法共享OCR缓存

## Level 3: 组件 (Components)

### 组件架构图

```
┌─────────────────────────────────────────────────────────────┐
│                  MCP Server Component                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │      MCP Protocol Handler                          │    │
│  │                                                     │    │
│  │  Responsibilities:                                  │    │
│  │  - Handle JSON-RPC messages                        │    │
│  │  - Route requests to handlers                      │    │
│  │  - Format responses                                │    │
│  │  - Error handling                                  │    │
│  │                                                     │    │
│  │  Functions:                                        │    │
│  │  - handle_list_tools() → list[types.Tool]         │    │
│  │  - handle_call_tool(name, args) → list[TextContent]│   │
│  │  - main_async() → setup stdio server              │    │
│  │  - main() → entry point                           │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   │ Uses                                    │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │          OCR Manager (Singleton Cache)              │    │
│  │                                                     │    │
│  │  Responsibilities:                                  │    │
│  │  - Initialize PaddleOCR instances                  │    │
│  │  - Cache instances by language                     │    │
│  │  - Provide optimized OCR configuration             │    │
│  │                                                     │    │
│  │  State:                                            │    │
│  │  - ocr_cache: dict[str, PaddleOCR]                │    │
│  │                                                     │    │
│  │  Functions:                                        │    │
│  │  - get_ocr(language='ch') → PaddleOCR             │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   │ Uses                                    │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Image Preprocessor                          │    │
│  │                                                     │    │
│  │  Responsibilities:                                  │    │
│  │  - Convert image formats (RGBA/LA/P → RGB)        │    │
│  │  - Downsample large images (max 1920px)           │    │
│  │  - Apply sharpening filters                        │    │
│  │  - Manage temporary files                          │    │
│  │                                                     │    │
│  │  Functions:                                        │    │
│  │  - preprocess_image(path) → temp_path             │    │
│  │                                                     │    │
│  │  Constants:                                        │    │
│  │  - MAX_IMAGE_SIZE = 1920                           │    │
│  │  - SHARPEN_FACTOR = 1.2                            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 组件详细说明

#### 1. MCP Protocol Handler

**职责**: 处理MCP协议相关操作

**关键函数**:

```127:154:paddleocr_cli/mcp_server.py
def get_ocr(language: str = 'ch') -> PaddleOCR:
    """Initialize PaddleOCR with optimized settings for speed and low latency
    
    Args:
        language: Language code for OCR (default: 'ch' for Chinese and English)
    
    Returns:
        PaddleOCR instance with optimal configuration
    """
    global ocr_cache
    
    # Normalize language code to lowercase
    lang_key = language.lower() if language else 'ch'
    
    if lang_key not in ocr_cache:
        # Build optimization parameters compatible with PaddleOCR 2.7+
        # Note: PaddleOCR 2.7+ uses different parameter names
        ocr_params = {
            'lang': lang_key,
            'use_textline_orientation': False,  # Fast mode: disable textline orientation classification
            'text_recognition_batch_size': 1,  # Process one image at a time for lowest latency
        }
        
        # Initialize PaddleOCR with compatible parameters
        # PaddleOCR 2.7+ automatically detects GPU/CPU and uses optimal settings
        ocr_cache[lang_key] = PaddleOCR(**ocr_params)
    
    return ocr_cache[lang_key]
```

**数据流**:
- 输入: JSON-RPC 请求
- 输出: JSON-RPC 响应
- 内部调用: `get_ocr()`, `preprocess_image()`

#### 2. OCR Manager

**职责**: 管理OCR实例生命周期和缓存

**关键数据结构**:
- `ocr_cache: dict[str, PaddleOCR]` - 全局缓存字典，key为语言代码

**关键函数**: `get_ocr(language)`

**设计模式**: 单例模式（每个语言一个实例）

**优化策略**:
- 懒加载：首次使用时初始化
- 按语言缓存：不同语言使用不同实例
- 优化参数：fast mode, batch size=1

#### 3. Image Preprocessor

**职责**: 图像预处理以提高OCR性能和准确率

**处理步骤**:
1. 格式转换 (RGBA/LA/P → RGB)
2. 降采样 (大图→1920px)
3. 锐化处理 (UnsharpMask + Enhance)

**关键函数**: `preprocess_image(image_path)`

**临时文件管理**:
- 创建: `tempfile.NamedTemporaryFile`
- 清理: `finally` 块中 `os.unlink`

## Level 4: 类/函数级别 (Code Level)

### 核心类/函数结构

```
mcp_server.py (306 lines)
│
├── Global State
│   ├── server: Server("fast-paddleocr-mcp")
│   ├── ocr_cache: dict[str, PaddleOCR] = {}
│   ├── MAX_IMAGE_SIZE = 1920
│   └── SHARPEN_FACTOR = 1.2
│
├── preprocess_image(image_path: str) -> str
│   ├── Image.open()
│   ├── Format conversion (RGBA/LA/P → RGB)
│   ├── Downsampling (if > MAX_IMAGE_SIZE)
│   ├── Sharpening (UnsharpMask + Enhance)
│   └── Save temporary file
│
├── get_ocr(language: str = 'ch') -> PaddleOCR
│   ├── Check ocr_cache[lang_key]
│   ├── Initialize PaddleOCR(**ocr_params) if not cached
│   └── Return cached/new instance
│
├── @server.list_tools()
│   └── handle_list_tools() -> list[types.Tool]
│       └── Return tool definition (ocr_image)
│
├── @server.call_tool()
│   └── handle_call_tool(name, arguments) -> list[types.TextContent]
│       ├── Validate parameters
│       ├── Validate file exists
│       ├── preprocess_image()
│       ├── get_ocr(language)
│       ├── ocr_instance.predict(preprocessed_path)
│       ├── Extract rec_texts
│       ├── Generate markdown file
│       ├── Cleanup temporary file (finally)
│       └── Return output path
│
├── async main_async()
│   ├── stdio_server() context manager
│   └── server.run(read_stream, write_stream, ...)
│
└── main()
    └── asyncio.run(main_async())
```

### 数据流详解

#### OCR工具调用数据流

```
Input: JSON-RPC Request
    │
    ├─► name: "ocr_image"
    ├─► arguments: {
    │     "image_path": "test.png",
    │     "language": "ch"
    │   }
    │
    ▼
handle_call_tool(name, arguments)
    │
    ├─► Validate: name == "ocr_image"
    ├─► Validate: image_path exists and is file
    ├─► Validate: language is string
    │
    ▼
preprocess_image(image_path)
    │
    ├─► Load: PIL.Image.open(image_path)
    ├─► Convert: RGBA/LA/P → RGB
    ├─► Downsample: resize if > 1920px
    ├─► Sharpen: UnsharpMask + Enhance
    └─► Save: temp_file (JPEG, quality=95)
    │
    ▼ (preprocessed_path)
get_ocr(language="ch")
    │
    ├─► Check: ocr_cache["ch"]
    ├─► If not exists:
    │     Initialize: PaddleOCR(lang="ch", ...)
    │     Cache: ocr_cache["ch"] = instance
    └─► Return: PaddleOCR instance
    │
    ▼
ocr_instance.predict(preprocessed_path)
    │
    ├─► PaddleOCR processes image
    └─► Returns: [OCRResult, ...]
    │     OCRResult = {
    │       "rec_texts": ["Hello", "World", ...]
    │     }
    │
    ▼
Extract and filter texts
    │
    ├─► Iterate OCRResult objects
    ├─► Extract rec_texts field
    ├─► Filter empty strings
    └─► Build: detected_texts = ["Hello", "World"]
    │
    ▼
Generate markdown file
    │
    ├─► output_path = Path(image_path + ".md")
    ├─► Write markdown format:
    │     # OCR Result
    │     **Source Image:** `image_path`
    │     **Language:** `language`
    │     ---
    │     - Hello
    │     - World
    └─► Save file
    │
    ▼
Cleanup (finally block)
    │
    └─► os.unlink(preprocessed_path)
    │
    ▼
Output: JSON-RPC Response
    │
    └─► {
          "result": {
            "content": [{
              "type": "text",
              "text": "test.png.md"
            }]
          }
        }
```

## 架构决策记录 (ADR)

### ADR-1: 使用全局OCR缓存

**上下文**: PaddleOCR初始化需要加载深度学习模型，耗时数秒

**决策**: 使用全局字典 `ocr_cache` 缓存OCR实例，按语言key存储

**后果**:
- ✅ 显著提升性能（避免重复初始化）
- ⚠️ 内存占用增加（每个语言一个模型实例）
- ✅ 懒加载策略（首次使用才创建）

### ADR-2: 图像预处理作为独立组件

**上下文**: 大图和某些格式会降低OCR性能和准确率

**决策**: 独立的 `preprocess_image()` 函数，统一处理格式转换、降采样、锐化

**后果**:
- ✅ 提高OCR准确率和速度
- ✅ 代码清晰，职责分离
- ⚠️ 增加处理时间（但总体更快）

### ADR-3: 临时文件在finally中清理

**上下文**: 预处理图像需要保存为临时文件，可能因异常导致泄漏

**决策**: 使用 `try-finally` 块，在 `finally` 中清理临时文件，忽略清理异常

**后果**:
- ✅ 确保清理执行
- ⚠️ 可能掩盖清理错误（但这是可接受的权衡）

### ADR-4: 使用PaddleOCR 2.7+ API

**上下文**: PaddleOCR 2.7 改变了API（`ocr()` → `predict()`）

**决策**: 使用新API，不维护向后兼容

**后果**:
- ✅ 获得最新功能和性能优化
- ❌ 不支持旧版本PaddleOCR（但这是合理的）

## 扩展点

### 添加新工具

1. 在 `handle_list_tools()` 中添加工具定义
2. 在 `handle_call_tool()` 中添加处理逻辑
3. 添加对应的测试

### 优化性能

1. **异步预处理**: 将 `preprocess_image()` 改为异步
2. **批量处理**: 支持多图像批量OCR
3. **结果缓存**: 缓存相同图像路径的结果

### 增强功能

1. **更多OCR参数**: 在 `get_ocr()` 中添加可配置参数
2. **更多输出格式**: 支持JSON、TXT等格式
3. **OCR结果详细信息**: 包含坐标、置信度等

---

**文档版本**: 1.0  
**最后更新**: 2024-XX-XX
