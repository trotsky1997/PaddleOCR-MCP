# PaddleOCR-MCP

MCP (Model Context Protocol) server for PaddleOCR that accepts image input and returns the path to the generated markdown file. Part of the PaddleOCR-MCP project.

## Installation

**From PyPI (recommended):**
```bash
pip install fast-paddleocr-mcp
```

**From local directory:**
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

The MCP server uses optimized default settings:
- Fast mode enabled
- PP-OCRv4 (faster mobile models)
- 640px image size limit
- Auto GPU detection (falls back to CPU if GPU not available)

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

**Or if installed from PyPI:**
```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "paddleocr-mcp"
    }
  }
}
```

**Using uvx from PyPI:**
```json
{
  "mcpServers": {
    "paddleocr": {
      "command": "uvx",
      "args": ["fast-paddleocr-mcp", "paddleocr-mcp"]
    }
  }
}
```
