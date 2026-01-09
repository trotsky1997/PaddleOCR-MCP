# PaddleOCR-MCP

PaddleOCR MCP (Model Context Protocol) server and CLI tool that extracts text from images and outputs results in markdown format. Optimized for fast inference with GPU auto-detection.

## Installation

### CLI Tool

This tool can be run using `uvx`:

```bash
# From local directory
uvx --from . paddleocr-md <image_path> [-o output.md]

# From PyPI (after publishing)
uvx fast-paddleocr-mcp paddleocr-md <image_path> [-o output.md]
```

Or install it locally:

```bash
uv pip install -e .
paddleocr-md <image_path> [-o output.md]
```

Or install from PyPI:

```bash
pip install fast-paddleocr-mcp
paddleocr-md <image_path> [-o output.md]
```

### MCP Server

The MCP (Model Context Protocol) server allows integration with MCP clients like Cursor, Claude Desktop, etc.

**Run MCP server with uvx:**

```bash
# From local directory
uvx --from . python -m paddleocr_cli.mcp_server

# From PyPI
uvx fast-paddleocr-mcp paddleocr-mcp
```

**Or after installation:**

```bash
pip install fast-paddleocr-mcp
paddleocr-mcp
```

## MCP Server Configuration

### MCP Tool: `ocr_image`

The server provides a single tool called `ocr_image` that:

- **Input**: `image_path` (string) - Path to the input image file
- **Output**: Returns the path to the generated markdown file containing OCR results

### Integration with MCP Clients

To use this server with an MCP client (like Cursor, Claude Desktop, etc.), configure it in your MCP settings:

**Using uvx from PyPI (recommended):**

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

**Using uvx from local directory:**

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

**Or using absolute path:**

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

**Using Python module (if installed locally):**

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

## Usage

### Basic Usage

The tool is optimized for speed by default with the following settings:

- **Fast mode enabled** (disables preprocessing for maximum speed)
- **PP-OCRv4** (faster mobile models)
- **640px image size limit** (faster processing)
- **Auto GPU detection** (uses GPU if available, falls back to CPU)

```bash
# Output will be saved as <image_name>.png.md
# Uses: fast mode + PP-OCRv4 + 640px + auto GPU detection
uvx --from . paddleocr-md image.png

# Specify custom output path
uvx --from . paddleocr-md image.png -o result.md

# Force CPU mode
uvx --from . paddleocr-md image.png --cpu

# Disable fast mode for better accuracy on rotated text
uvx --from . paddleocr-md image.png --no-fast

# Use PP-OCRv5 for better accuracy (slower)
uvx --from . paddleocr-md image.png --ocr-version PP-OCRv5
```

### Default Optimization Settings

The tool is optimized for speed by default with these settings:

- ✅ **Fast mode enabled**: Disables textline orientation classification (skips one model)
- ✅ **PP-OCRv4**: Uses faster mobile models (PP-OCRv4_mobile_det, PP-OCRv4_mobile_rec)
- ✅ **640px image size limit**: Faster processing (vs default 960px)
- ✅ **Auto GPU detection**: Automatically uses GPU if available, falls back to CPU
- ✅ **Document preprocessing disabled**: Skips unnecessary preprocessing steps

#### Customization Options

1. `**--no-fast**`: Disable fast mode for better accuracy
  - Enables textline orientation classification
  - Better accuracy on rotated text, but slower
2. `**--cpu**`: Force CPU mode
  - Overrides auto GPU detection
  - Explicitly use CPU
3. `**--gpu**`: Force GPU mode
  - Will fail if GPU not available
  - Use when you want to ensure GPU usage
4. `**--ocr-version PP-OCRv5**`: Use better accuracy version
  - PP-OCRv5 has better accuracy but slower than PP-OCRv4 (default)
  - Uses server models
5. `**--max-size <pixels>**`: Adjust image processing size
  - Default: 640px
  - Larger values (e.g., 960, 1280) = better accuracy, slower
  - Smaller values (e.g., 480) = faster, may reduce accuracy
6. `**--hpi**`: High-Performance Inference
  - Automatically selects best inference backend (Paddle Inference, OpenVINO, ONNX Runtime, TensorRT)
  - Requires HPI dependencies: `paddleocr install_hpi_deps cpu/gpu`
  - Best performance but requires additional setup

### Examples

```bash
# Basic usage (uses all optimizations by default: fast + PP-OCRv4 + 640px + auto GPU)
uvx --from . paddleocr-md photo.jpg

# Process with custom output
uvx --from . paddleocr-md document.png -o extracted_text.md

# Better accuracy (slower) - disable fast mode and use PP-OCRv5
uvx --from . paddleocr-md image.png --no-fast --ocr-version PP-OCRv5 --max-size 960

# Force CPU mode
uvx --from . paddleocr-md image.png --cpu

# Use High-Performance Inference (requires HPI dependencies)
uvx --from . paddleocr-md image.png --hpi
```

## Output Format

The tool generates a markdown file containing:

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
- Pillow

## License

MIT