# Project Instructions

> **⚠️ Important:** You must read `cursor-agents-md` skills every time before write or update this `AGENTS.md`.

## Project Overview

This is a Fast PaddleOCR MCP (Model Context Protocol) server that extracts text from images using PaddleOCR and outputs results in markdown format. The server provides an `ocr_image` tool that accepts an image path and returns the path to the generated markdown file (image_path + .md).

## Code Style

- Use **Python 3.8+** (supports up to 3.12)
- Follow **PEP 8** style guidelines
- Use **type hints** with `typing` module (e.g., `Optional[dict[str, Any]]`)
- Maximum line length: **100 characters** (preferred) or **120 characters** (if needed)
- Use **async/await** for MCP server handlers
- Use **f-strings** for string formatting
- Use **Path** from `pathlib` for file operations, not `os.path`
- Import order: standard library → third-party → local imports
- Use **snake_case** for function and variable names
- Use **UPPER_CASE** for constants

### Example Code Style

```python
from pathlib import Path
from typing import Any, Optional

async def handle_call_tool(name: str, arguments: Optional[dict[str, Any]]) -> list[types.TextContent]:
    """Handle tool calls with proper type hints"""
    if not arguments or "image_path" not in arguments:
        raise ValueError("Missing required argument: image_path")
    
    image_path = arguments["image_path"]
    image_path_obj = Path(image_path)
    
    if not image_path_obj.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
```

## Architecture

### MCP Server Structure

- **Single tool**: `ocr_image` - Main functionality
- **Lazy initialization**: OCR instances are cached by language
- **Error handling**: Wrap exceptions in RuntimeError with descriptive messages
- **Async handlers**: All MCP handlers must be async functions
- **Stdio transport**: Server communicates via standard input/output

### Key Components

1. **OCR Instance Management**: 
   - Cache PaddleOCR instances by language in global `ocr_cache` dict
   - Use lowercase language keys for consistency
   - Lazy initialization on first use

2. **Tool Handlers**:
   - `handle_list_tools()`: Returns tool definitions with input schema
   - `handle_call_tool()`: Processes OCR requests and generates markdown output

3. **Main Entry Point**:
   - `main()`: Synchronous wrapper for `main_async()`
   - `main_async()`: Async server initialization and stdio loop

### Design Patterns

- **Singleton pattern**: Cached OCR instances per language
- **Decorator pattern**: Use `@server.list_tools()` and `@server.call_tool()` decorators
- **Dependency injection**: Pass language parameter to `get_ocr()` function

## Testing

- **Framework**: pytest with pytest-asyncio
- **Coverage target**: 85%+ (current: 85%)
- **Test location**: `tests/test_mcp_server.py`
- **Test organization**: Group tests by class (TestGetOCR, TestCallTool, etc.)
- **Mocking**: Use `unittest.mock` to mock PaddleOCR and file operations
- **Fixtures**: Use pytest fixtures for common test objects (mock_paddleocr, test_image, cleanup_cache)

### Test Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=paddleocr_cli --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=paddleocr_cli --cov-report=html

# Run specific test class
pytest tests/test_mcp_server.py::TestGetOCR

# Run specific test
pytest tests/test_mcp_server.py::TestGetOCR::test_get_ocr_default_language
```

### Test Requirements

- All async test functions must use `@pytest.mark.asyncio`
- Mock PaddleOCR to avoid downloading models in tests
- Use `tmp_path` fixture for temporary files
- Clean up OCR cache before and after tests
- Test both success and error scenarios
- Verify markdown output format and content

### Example Test

```python
@pytest.mark.asyncio
async def test_call_tool_success(test_image, mock_paddleocr, cleanup_cache):
    """Test successful OCR tool call"""
    with patch("paddleocr_cli.mcp_server.get_ocr", return_value=mock_paddleocr):
        arguments = {"image_path": test_image}
        result = await mcp_server.handle_call_tool("ocr_image", arguments)
        
        assert len(result) == 1
        assert result[0].type == "text"
        output_path = Path(result[0].text)
        assert output_path.exists()
        assert output_path.suffix == ".md"
```

## File Structure

```
PaddleOCR-MCP/
├── paddleocr_cli/          # Main package
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # Module entry point (python -m paddleocr_cli.mcp_server)
│   └── mcp_server.py       # MCP server implementation
├── tests/                  # Test suite
│   ├── __init__.py         # Test package initialization
│   └── test_mcp_server.py  # Unit tests for MCP server
├── pyproject.toml          # Project configuration and dependencies
├── README.md               # Project documentation
├── MCP_README.md           # MCP server specific documentation
└── AGENTS.md              # This file - agent instructions
```

### File Naming Conventions

- Python files: `snake_case.py`
- Test files: `test_*.py`
- Markdown files: `PascalCase.md` or `UPPER_CASE.md`
- Config files: `pyproject.toml`, `.gitignore`

## Dependencies

### Required Dependencies

- `mcp>=1.0.0` - Model Context Protocol Python SDK
- `paddleocr>=2.7.0` - PaddleOCR library
- `paddlepaddle>=2.5.0` - PaddlePaddle deep learning framework
- `pillow>=10.0.0` - Image processing library

### Development Dependencies

- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage reporting

### Installation

```bash
# Install package in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Commands

### Development

```bash
# Install package
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=paddleocr_cli --cov-report=html

# Run server as module
python -m paddleocr_cli.mcp_server

# Run server via entry point (after installation)
fast-paddleocr-mcp
```

### Running via uvx

```bash
# Run via uvx (no installation needed)
uvx fast-paddleocr-mcp
```

### MCP Client Configuration

For MCP clients (like Cursor, Claude Desktop), configure in MCP settings:

```json
{
  "mcpServers": {
    "fast-paddleocr-mcp": {
      "command": "uvx",
      "args": ["fast-paddleocr-mcp"]
    }
  }
}
```

## Key Functionality

### OCR Tool: `ocr_image`

**Parameters:**
- `image_path` (string, required): Path to input image file
- `language` (string, optional): Language code for OCR (default: 'ch')
  - Common values: 'ch', 'en', 'japan', 'korean', 'chinese_cht'
  - See PaddleOCR documentation for full list

**Returns:**
- Path to generated markdown file (image_path + .md)

**Behavior:**
- Validates image file exists and is a file (not directory)
- Initializes PaddleOCR with specified language (cached per language)
- Performs OCR on image
- Generates markdown file with OCR results
- Returns path to markdown file

**Markdown Output Format:**
```markdown
# OCR Result

**Source Image:** `image.png`
**Language:** `ch`

---

- Detected text line 1
- Detected text line 2
```

### OCR Configuration

**Default settings** (optimized for speed):
- `use_angle_cls=False` - Fast mode (no textline orientation classification)
- `lang='ch'` - Chinese and English support (default)
- `show_log=False` - Disable logging
- `use_gpu=True` - Auto-detect GPU, fallback to CPU
- `det_model_dir=None` - Use default mobile models (PP-OCRv4)
- `rec_model_dir=None` - Use default mobile models

## Error Handling

- **FileNotFoundError**: When image file doesn't exist
- **ValueError**: When path is not a file or invalid parameter type
- **RuntimeError**: Wraps all exceptions with descriptive error messages
- All errors are logged to stderr before raising
- Error messages include the problematic image_path for debugging

### Example Error Handling

```python
try:
    # Process image
    result = ocr_instance.ocr(str(image_path_obj), cls=False)
except Exception as e:
    error_msg = f"Error processing image {image_path}: {str(e)}"
    print(error_msg, file=sys.stderr)
    raise RuntimeError(error_msg) from e
```

## Boundaries

### What NOT to Do

- ❌ **Never modify OCR cache directly** - Always use `get_ocr()` function
- ❌ **Don't remove error handling** - All exceptions must be caught and wrapped
- ❌ **Don't hardcode language** - Always use parameter, default to 'ch'
- ❌ **Don't modify test files** unless fixing bugs - Tests are comprehensive
- ❌ **Don't change output format** without updating tests
- ❌ **Don't remove type hints** - All functions must have type annotations
- ❌ **Don't commit secrets** - Check for API keys, tokens, credentials
- ❌ **Don't modify pyproject.toml** without updating this document

### What Requires Approval

- ✅ **Changing default language** - Currently 'ch', requires discussion
- ✅ **Adding new dependencies** - Must update pyproject.toml and this document
- ✅ **Changing output format** - Must update tests and documentation
- ✅ **Adding new tools** - Requires updating MCP server structure
- ✅ **Performance optimizations** - May affect default settings

## Best Practices

### Code Quality

- Write descriptive docstrings for all functions
- Include type hints for all function parameters and return values
- Use meaningful variable names (e.g., `image_path_obj` not `path`)
- Add comments for non-obvious logic
- Keep functions focused on single responsibility

### Performance

- Cache OCR instances by language (already implemented)
- Lazy initialization (only create OCR instance when needed)
- Use Path operations instead of string concatenation
- Minimize file I/O operations

### Maintainability

- Update tests when changing functionality
- Update this AGENTS.md when adding features
- Keep error messages descriptive and actionable
- Document any special behavior in code comments

## Common Patterns

### Adding a New Language Support

Languages are automatically supported if PaddleOCR supports them. Just pass the language code:

```python
# User passes language parameter
arguments = {"image_path": "image.png", "language": "en"}

# Server uses it to get/create OCR instance
ocr_instance = get_ocr(language)  # Returns cached or new instance
```

### Processing OCR Results

```python
# OCR returns: [[[box_coords], (text, confidence)], ...]
result = ocr_instance.ocr(str(image_path_obj), cls=False)

# Extract text from result
detected_texts = []
if result and result[0]:
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]  # Extract text from (text, confidence) tuple
            if text:
                detected_texts.append(text)
```

### Generating Output Path

```python
# Input: "image.png"
# Output: "image.png.md"
output_path = Path(str(image_path_obj) + '.md')
```

## Update Log

### 2024-01-XX (Initial)
- ✅ Created AGENTS.md with project guidelines
- ✅ Documented code style, architecture, and testing requirements
- ✅ Added file structure and commands documentation
- ✅ Defined boundaries and best practices
