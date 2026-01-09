# PaddleOCR-MCP

PaddleOCR MCP (Model Context Protocol) server that extracts text from images and outputs results in markdown format. Optimized for fast inference with GPU auto-detection.

## Installation

### Using uvx (Recommended - No Installation Needed)

```bash
# Run MCP server directly
uvx fast-paddleocr-mcp
```

### Or Install from PyPI

```bash
pip install fast-paddleocr-mcp
fast-paddleocr-mcp
```

## MCP Server Configuration

### MCP Tool: `ocr_image`

The server provides a single tool called `ocr_image` that:

- **Input**: `image_path` (string) - Path to the input image file
- **Output**: Returns the path to the generated markdown file containing OCR results

### Integration with MCP Clients

To use this server with an MCP client (like Cursor, Claude Desktop, etc.), configure it in your MCP settings:

```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "uvx",
      "args": ["fast-paddleocr-mcp"]
    }
  }
}
```

### MCP Request/Response Example

**Request:**

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

**Response:**

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

## Default Optimization Settings

The MCP server uses optimized default settings for fast inference:

- ✅ **Fast mode enabled**: Disables textline orientation classification (skips one model)
- ✅ **PP-OCRv4**: Uses faster mobile models (PP-OCRv4_mobile_det, PP-OCRv4_mobile_rec)
- ✅ **640px image size limit**: Faster processing (vs default 960px)
- ✅ **Auto GPU detection**: Automatically uses GPU if available, falls back to CPU
- ✅ **Document preprocessing disabled**: Skips unnecessary preprocessing steps

## Output Format

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

## Requirements

- Python >= 3.8
- PaddleOCR
- PaddlePaddle
- Pillow

## License

MIT