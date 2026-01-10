# PaddleOCR-MCP

MCP (Model Context Protocol) server for PaddleOCR that accepts image input and returns the path to the generated markdown file. Part of the PaddleOCR-MCP project.

## Installation

```bash
uv pip install -e .
```

## Usage

### Running the MCP Server

The MCP server communicates via stdio (standard input/output) using JSON-RPC 2.0 protocol.

**Using uvx (recommended - from local directory):**
```bash
uvx --from . python -m paddleocr_cli.mcp_server
```

**Or using Python module directly:**
```bash
python -m paddleocr_cli.mcp_server
```

**After installation:**
```bash
uv pip install -e .
paddleocr-mcp
```

### MCP Tool: `ocr_image`

The server provides a single tool called `ocr_image` that:

- **Input**: `image_path` (string) - Path to the input image file
- **Output**: Returns the path to the generated markdown file containing OCR results
- **Automatic optimizations**: All performance optimizations are applied automatically
  - High-Performance Inference (HPI) with automatic backend selection
  - GPU acceleration with automatic fallback to CPU
  - Image preprocessing (downsampling and sharpening)
  - Multi-threaded CPU processing
  - Intelligent fallback to simpler configurations if needed
- **Default language**: Uses 'ch' (Chinese and English) for maximum compatibility

### Example MCP Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ocr_image",
    "arguments": {
      "image_path": "test_image.png"
    }
  }
}
```

**Note**: Only `image_path` is required. All optimizations are applied automatically.

### Example MCP Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "test_image.png.md"
      }
    ]
  }
}
```

### List Available Tools

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

### Default Settings

The MCP server uses optimized default settings with all performance enhancements:
- **Fast mode enabled**: Disables textline orientation classification
- **PP-OCRv4**: Uses faster mobile models (PP-OCRv4_mobile_det, PP-OCRv4_mobile_rec)
- **High-Performance Inference (HPI)**: Automatically enabled (requires PaddleOCR >= 2.7.0)
- **GPU acceleration**: Auto-detects GPU, falls back to CPU if not available
- **Image preprocessing**: Automatic downsampling (max 1920px) and sharpening
- **Multi-threaded CPU**: Uses all available CPU cores
- **MKL-DNN optimization**: Enabled for Intel CPUs
- **Default language**: 'ch' (Chinese and English) for maximum compatibility
- **No backward compatibility**: Requires latest PaddleOCR version with all features supported

### Output Format

The generated markdown file contains:
- Source image path
- List of detected text (one per line)

Example output (`test_image.png.md`):
```markdown
# OCR Result

**Source Image:** `test_image.png`

---

- HelloPaddleOcR
- 10000C
```

## Integration with MCP Clients

To use this server with an MCP client (like Cursor, Claude Desktop, etc.), configure it in your MCP settings:

**Using uvx (recommended - from local directory):**
```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "uvx",
      "args": ["--from", ".", "python", "-m", "paddleocr_cli.mcp_server"]
    }
  }
}
```

Or using absolute path:
```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "uvx",
      "args": ["--from", "/absolute/path/to/PaddleOCR-MCP", "python", "-m", "paddleocr_cli.mcp_server"]
    }
  }
}
```

**Using Python module:**
```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "python",
      "args": ["-m", "paddleocr_cli.mcp_server"]
    }
  }
}
```

**Or if installed locally:**
```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "paddleocr-mcp"
    }
  }
}
```
