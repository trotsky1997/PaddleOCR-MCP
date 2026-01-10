# PaddleOCR-MCP API 执行流程追踪

本文档详细追踪了 PaddleOCR-MCP 服务器处理 OCR 请求的完整执行流程。

## 流程图概览

```
Client Request
    │
    ▼
[main() - Entry Point]
    │
    ▼
[main_async() - Async Setup]
    │
    ▼
[stdio_server - Communication]
    │
    ▼
[server.run() - Event Loop]
    │
    ├─► tools/list ──────────► [handle_list_tools()] ──► Response
    │
    └─► tools/call ──────────► [handle_call_tool()] ──► Response
                                    │
                                    ├─► Validate Parameters
                                    ├─► Validate File
                                    ├─► [preprocess_image()] ──► Temp File
                                    ├─► [get_ocr()] ──► OCR Instance
                                    ├─► [ocr.predict()] ──► OCR Result
                                    ├─► Extract Text
                                    ├─► Generate Markdown
                                    ├─► Cleanup Temp File
                                    └─► Return Path
```

## 详细执行流程

### 阶段 1: 服务器启动

**代码位置**: `mcp_server.py:299-305`

```python
def main():
    """Main entry point for the MCP server (synchronous wrapper)"""
    asyncio.run(main_async())
```

**执行步骤**:
1. `main()` 被调用（通过 `python -m paddleocr_cli.mcp_server` 或 `fast-paddleocr-mcp` 命令）
2. 调用 `asyncio.run(main_async())` 启动异步事件循环

**代码位置**: `mcp_server.py:282-296`

```python
async def main_async():
    """Async main entry point for the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fast-paddleocr-mcp",
                server_version="0.4.2",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
```

**执行步骤**:
1. 创建 stdio 服务器（stdin/stdout）
2. 初始化 MCP 服务器，注册工具处理器
3. 进入事件循环，等待 JSON-RPC 请求

### 阶段 2: 工具列表请求 (tools/list)

**触发**: MCP 客户端发送 `tools/list` 请求

**代码位置**: `mcp_server.py:157-180`

```157:180:paddleocr_cli/mcp_server.py
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="ocr_image",
            description="Extract text from an image using PaddleOCR with automatic optimizations. Returns the path to the generated markdown file (image_path + .md). All optimizations are applied automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the input image file"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code for OCR (e.g., 'ch' for Chinese+English, 'en' for English, 'japan' for Japanese, 'korean' for Korean). Recommended: 'ch'",
                        "default": "ch"
                    }
                },
                "required": ["image_path", "language"]
            }
        )
    ]
```

**执行步骤**:
1. MCP 框架调用 `handle_list_tools()`（通过 `@server.list_tools()` 装饰器）
2. 返回工具定义，包含 `ocr_image` 工具
3. 工具定义包括输入参数 schema（`image_path` 和 `language`）

**响应示例**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [{
      "name": "ocr_image",
      "description": "Extract text from an image...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "image_path": {"type": "string", ...},
          "language": {"type": "string", "default": "ch", ...}
        },
        "required": ["image_path", "language"]
      }
    }]
  }
}
```

### 阶段 3: 工具调用请求 (tools/call) - 参数验证

**触发**: MCP 客户端发送 `tools/call` 请求

**代码位置**: `mcp_server.py:184-204`

```184:204:paddleocr_cli/mcp_server.py
@server.call_tool()
async def handle_call_tool(name: str, arguments: Optional[dict[str, Any]]) -> list[types.TextContent]:
    """Handle tool calls"""
    if name != "ocr_image":
        raise ValueError(f"Unknown tool: {name}")
    
    if not arguments or "image_path" not in arguments:
        raise ValueError("Missing required argument: image_path")
    
    image_path = arguments["image_path"]
    if not isinstance(image_path, str):
        raise ValueError("image_path must be a string")
    
    # Get language parameter (required, default to 'ch' if not provided)
    language = arguments.get("language", "ch")
    if not isinstance(language, str):
        raise ValueError("language must be a string")
    # Normalize to lowercase and use 'ch' as default if empty
    language = language.lower().strip() if language else 'ch'
    if not language:
        language = 'ch'  # Default to 'ch' if empty string
```

**执行步骤**:
1. 验证工具名称: `name == "ocr_image"`
2. 验证参数存在: `arguments` 不为空，包含 `image_path`
3. 验证参数类型: `image_path` 和 `language` 必须是字符串
4. 规范化语言代码: 转换为小写，默认 'ch'

**错误处理**:
- 工具名不匹配 → `ValueError("Unknown tool: {name}")`
- 缺少 `image_path` → `ValueError("Missing required argument: image_path")`
- 类型错误 → `ValueError("image_path must be a string")`

### 阶段 4: 文件验证

**代码位置**: `mcp_server.py:205-212`

```205:212:paddleocr_cli/mcp_server.py
    try:
        # Validate input file exists
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if not image_path_obj.is_file():
            raise ValueError(f"Path is not a file: {image_path}")
```

**执行步骤**:
1. 转换为 `Path` 对象
2. 检查文件是否存在: `Path.exists()`
3. 检查是否为文件（而非目录）: `Path.is_file()`

**错误处理**:
- 文件不存在 → `FileNotFoundError`
- 路径是目录 → `ValueError("Path is not a file")`

### 阶段 5: 图像预处理

**代码位置**: `mcp_server.py:214-216`

```214:216:paddleocr_cli/mcp_server.py
        # Preprocess image: automatic downsampling and sharpening
        # This improves OCR performance and accuracy
        preprocessed_path = preprocess_image(str(image_path_obj))
```

**详细处理**: `preprocess_image()` 函数 (42-124行)

```42:124:paddleocr_cli/mcp_server.py
def preprocess_image(image_path: str) -> str:
    """Preprocess image with automatic downsampling and sharpening for better OCR performance
    
    Args:
        image_path: Path to the input image file
        
    Returns:
        Path to the preprocessed image (temporary file)
    """
    from PIL import Image, ImageEnhance, ImageFilter
    
    # Open the original image
    img = Image.open(image_path)
    
    # Convert to RGB if necessary (handle RGBA, L, P, etc.)
    if img.mode != 'RGB':
        if img.mode == 'RGBA':
            # Create a white background for transparent images
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode == 'LA':
            # Convert LA (grayscale with alpha) to RGB
            background = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img = img.convert('RGB')
            # Use alpha channel from original image
            alpha = img.split()[1] if len(img.split()) > 1 else None
            if alpha:
                background.paste(rgb_img, mask=alpha)
            else:
                background.paste(rgb_img)
            img = background
        elif img.mode == 'P':
            # Convert palette mode to RGB (handle transparency)
            # First check if the palette image has transparency
            if 'transparency' in img.info:
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = background
            # else: already RGB, no conversion needed
        else:
            # Convert other modes (L, etc.) to RGB
            img = img.convert('RGB')
    
    # Automatic downsampling: resize if image is too large
    # Large images slow down OCR significantly, so we resize while maintaining aspect ratio
    width, height = img.size
    if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = MAX_IMAGE_SIZE
            new_height = int(height * (MAX_IMAGE_SIZE / width))
        else:
            new_height = MAX_IMAGE_SIZE
            new_width = int(width * (MAX_IMAGE_SIZE / height))
        
        # Resize using high-quality resampling (LANCZOS) to preserve text quality
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Apply sharpening filter to enhance text edges and improve OCR accuracy
    # Unsharp mask filter enhances edges without oversharpening
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    
    # Additional sharpening with ImageEnhance for fine control
    # This helps make text characters more distinct and easier to recognize
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(SHARPEN_FACTOR)
    
    # Save preprocessed image to temporary file
    # Use JPEG format with high quality to preserve text clarity
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', prefix='preprocessed_')
    temp_path = temp_file.name
    temp_file.close()
    
    # Save as JPEG with high quality to preserve text clarity
    img.save(temp_path, 'JPEG', quality=95, optimize=True)
    
    return temp_path
```

**执行步骤**:
1. **打开图像**: `PIL.Image.open(image_path)`
2. **格式转换**: 
   - RGBA → RGB（白色背景）
   - LA → RGB（白色背景）
   - P → RGB（处理透明度）
   - L → RGB（灰度转RGB）
3. **降采样**: 如果宽度或高度 > 1920px，按比例缩小
4. **锐化处理**: 
   - UnsharpMask 滤镜
   - Sharpness 增强（factor=1.2）
5. **保存临时文件**: JPEG格式，quality=95

**输出**: 临时文件路径 `preprocessed_path`

### 阶段 6: OCR实例获取

**代码位置**: `mcp_server.py:218-220`

```218:220:paddleocr_cli/mcp_server.py
        try:
            # Initialize OCR with specified language
            ocr_instance = get_ocr(language=language)
```

**详细处理**: `get_ocr()` 函数 (127-154行)

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

**执行步骤**:
1. 规范化语言代码: `lang_key = language.lower()`
2. 检查缓存: `if lang_key not in ocr_cache:`
3. 如果未缓存，初始化PaddleOCR:
   - 参数: `lang`, `use_textline_orientation=False`, `text_recognition_batch_size=1`
   - 创建实例: `PaddleOCR(**ocr_params)`
   - 缓存实例: `ocr_cache[lang_key] = instance`
4. 返回OCR实例（缓存或新建）

**缓存策略**: 每个语言一个实例，全局共享

### 阶段 7: OCR识别

**代码位置**: `mcp_server.py:222-224`

```222:224:paddleocr_cli/mcp_server.py
            # Perform OCR on preprocessed image
            # PaddleOCR 2.7+ uses predict() method (ocr() is deprecated)
            result = ocr_instance.predict(preprocessed_path)
```

**执行步骤**:
1. 调用 PaddleOCR `predict()` 方法（PaddleOCR 2.7+ API）
2. 传入预处理后的图像路径
3. 返回 OCR 结果: `list[OCRResult]`

**OCR结果格式** (PaddleOCR 2.7+):
```python
[
    OCRResult {
        "rec_texts": ["Hello", "World", ...]  # 识别的文本列表
    },
    ...
]
```

### 阶段 8: 结果提取

**代码位置**: `mcp_server.py:236-259`

```236:259:paddleocr_cli/mcp_server.py
        # Extract text from OCR result
        # PaddleOCR 2.7+ returns OCRResult objects (dictionary-like) with rec_texts field
        detected_texts = []
        if result and len(result) > 0:
            for ocr_result in result:
                # OCRResult is dictionary-like (has get method), extract rec_texts
                # Try multiple ways to access rec_texts to handle different object types
                rec_texts = None
                if hasattr(ocr_result, 'get'):
                    rec_texts = ocr_result.get('rec_texts', [])
                elif isinstance(ocr_result, dict):
                    rec_texts = ocr_result.get('rec_texts', [])
                elif hasattr(ocr_result, 'rec_texts'):
                    rec_texts = ocr_result.rec_texts
                
                if rec_texts:
                    if isinstance(rec_texts, list):
                        # rec_texts is a list of detected text strings, filter out empty strings
                        detected_texts.extend([text for text in rec_texts if text and text.strip()])
                    elif isinstance(rec_texts, str):
                        # If it's a single string, add it
                        if rec_texts.strip():
                            detected_texts.append(rec_texts)
```

**执行步骤**:
1. 初始化 `detected_texts = []`
2. 遍历 OCR 结果列表
3. 从每个 `OCRResult` 中提取 `rec_texts`:
   - 尝试 `get()` 方法（字典式）
   - 尝试直接访问 `rec_texts` 属性
   - 尝试字典访问 `['rec_texts']`
4. 处理 `rec_texts`:
   - 如果是列表，过滤空字符串后扩展
   - 如果是字符串，直接添加（如果非空）
5. 最终得到: `detected_texts = ["Hello", "World", ...]`

**兼容性处理**: 支持多种 OCR 结果格式，确保兼容性

### 阶段 9: Markdown文件生成

**代码位置**: `mcp_server.py:233-234, 260-271`

```233:234:paddleocr_cli/mcp_server.py
        # Generate output markdown file path (image.png -> image.png.md)
        output_path = Path(str(image_path_obj) + '.md')
```

```260:271:paddleocr_cli/mcp_server.py
        # Write markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# OCR Result\n\n")
            f.write(f"**Source Image:** `{image_path}`\n\n")
            f.write(f"**Language:** `{language}`\n\n")
            f.write("---\n\n")
            
            if detected_texts:
                for text in detected_texts:
                    f.write(f"- {text}\n")
            else:
                f.write("- No text detected\n")
```

**执行步骤**:
1. 生成输出路径: `image.png` → `image.png.md`
2. 打开文件（写入模式，UTF-8编码）
3. 写入Markdown格式:
   - 标题: `# OCR Result`
   - 源图像路径: `**Source Image:** `image_path``
   - 语言: `**Language:** `language``
   - 分隔线: `---`
   - 文本列表: 每个识别的文本一行 `- {text}`
   - 如果无文本: `- No text detected`

**Markdown输出示例**:
```markdown
# OCR Result

**Source Image:** `test.png`
**Language:** `ch`

---

- Hello
- World
```

### 阶段 10: 临时文件清理

**代码位置**: `mcp_server.py:225-231`

```225:231:paddleocr_cli/mcp_server.py
        finally:
            # Clean up temporary preprocessed image file
            try:
                if os.path.exists(preprocessed_path):
                    os.unlink(preprocessed_path)
            except Exception:
                pass  # Ignore cleanup errors
```

**执行步骤**:
1. `finally` 块确保清理执行（即使发生异常）
2. 检查临时文件是否存在: `os.path.exists(preprocessed_path)`
3. 删除临时文件: `os.unlink(preprocessed_path)`
4. 忽略清理异常（避免掩盖主要错误）

**设计考虑**: 即使清理失败，也不影响主要功能（文件系统会自动清理临时文件）

### 阶段 11: 返回结果

**代码位置**: `mcp_server.py:273-274`

```273:274:paddleocr_cli/mcp_server.py
        # Return the output file path
        return [types.TextContent(type="text", text=str(output_path))]
```

**执行步骤**:
1. 创建 `TextContent` 对象
2. 设置类型: `type="text"`
3. 设置内容: `text=str(output_path)`（输出文件路径）
4. 返回列表: `[TextContent]`

**响应格式**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "test.png.md"
    }]
  }
}
```

### 阶段 12: 错误处理

**代码位置**: `mcp_server.py:276-279`

```276:279:paddleocr_cli/mcp_server.py
    except Exception as e:
        error_msg = f"Error processing image {image_path}: {str(e)}"
        print(error_msg, file=sys.stderr)
        raise RuntimeError(error_msg) from e
```

**错误处理策略**:
1. 捕获所有异常
2. 构建描述性错误消息
3. 输出到 stderr（用于调试）
4. 包装为 `RuntimeError`（符合 MCP 协议）

**错误响应格式**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Error processing image test.png: ..."
  }
}
```

## 完整数据流总结

```
输入图像文件 (test.png)
    │
    ▼
[preprocess_image] → 临时JPEG文件 (preprocessed_xxx.jpg)
    │
    ▼
[get_ocr] → PaddleOCR实例 (缓存)
    │
    ▼
[ocr.predict] → [OCRResult(rec_texts=["Hello", "World"]), ...]
    │
    ▼
[Extract texts] → ["Hello", "World"]
    │
    ▼
[Generate markdown] → test.png.md
    │
    ▼
[Cleanup temp file] → (删除 preprocessed_xxx.jpg)
    │
    ▼
返回文件路径 ("test.png.md")
```

## 性能关键点

1. **OCR实例缓存**: 避免重复初始化（节省数秒）
2. **图像降采样**: 大图缩小到1920px（显著提升速度）
3. **格式统一**: RGB格式（PaddleOCR优化）
4. **锐化处理**: 提高OCR准确率（减少误识别）

---

**文档版本**: 1.0  
**最后更新**: 2024-XX-XX
