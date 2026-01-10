# PaddleOCR-MCP

PaddleOCR MCP (Model Context Protocol) server and CLI tool that extracts text from images and outputs results in markdown format. Optimized for fast inference with GPU auto-detection.

## MCP Server Configuration

The MCP (Model Context Protocol) server allows integration with MCP clients like Cursor, Claude Desktop, etc.

**Use `uvx` directly (no installation required, automatically downloads from PyPI):**

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

#### MCP Tool: `ocr_image`

The server provides a single tool called `ocr_image` that:
- **Input**: `image_path` (string) - Path to the input image file
- **Output**: Returns the path to the generated markdown file containing OCR results
- **Automatic optimizations**: All performance optimizations are applied automatically with intelligent fallback
- **Default language**: Uses 'ch' (Chinese and English) by default for maximum compatibility

Example: When called with `image_path: "photo.png"`, it returns `"photo.png.md"` containing the recognized text.

**Note**: The server automatically applies all optimizations (HPI, GPU acceleration, image preprocessing, etc.) and falls back to simpler configurations if needed. No configuration required from the caller.

See [MCP_README.md](MCP_README.md) for detailed MCP server documentation.

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

The MCP server is optimized for **low latency** by default with these settings:

- ✅ **Fast mode enabled**: Disables textline orientation classification (skips one model)
- ✅ **PP-OCRv4**: Uses faster mobile models (PP-OCRv4_mobile_det, PP-OCRv4_mobile_rec)
- ✅ **High-Performance Inference (HPI)**: Automatically selects optimal inference backend
  - Can reduce latency by **40-73%** (e.g., 73.1% reduction on PP-OCRv5_mobile_rec)
  - Supports Paddle Inference, OpenVINO, ONNX Runtime, TensorRT
- ✅ **Multi-threaded CPU**: Uses all available CPU cores for parallel processing
- ✅ **MKL-DNN enabled**: Intel CPU optimization for faster inference
- ✅ **Single image batch**: `rec_batch_num=1` for lowest latency per image
- ✅ **Auto GPU detection**: Automatically uses GPU if available, falls back to CPU
  - **GPU device selection**: Uses first available GPU (gpu_id=0)
  - **TensorRT support**: Automatically enabled via HPI if TensorRT is installed
  - **GPU memory**: Uses default allocation (can be customized if needed)
- ✅ **Automatic image preprocessing**: Optimizes images before OCR for better performance
  - **Automatic downsampling**: Resizes large images to maximum 1920px (maintains aspect ratio)
    - Reduces processing time for large images significantly
    - Uses high-quality LANCZOS resampling to preserve text quality
  - **Image sharpening**: Enhances text edges for improved OCR accuracy
    - Uses unsharp mask filter (radius=1, percent=150, threshold=3)
    - Additional sharpening enhancement (factor=1.2)
    - Makes text characters more distinct and easier to recognize
  - **Format conversion**: Automatically converts RGBA, LA, P modes to RGB with white background
  - **Temporary file management**: Automatically cleans up preprocessed images after OCR
- ✅ **Logging disabled**: Reduces overhead by disabling verbose logging

**GPU Performance:**
- When GPU is available, HPI automatically selects TensorRT backend for maximum performance
- TensorRT can provide 2-3x speedup compared to standard GPU inference
- First run with HPI may take longer to build the inference engine, but subsequent runs will be much faster

**Requirements**: 
- PaddleOCR >= 2.7.0 with all latest features supported (HPI, MKL-DNN, etc.)
- No backward compatibility - requires latest PaddleOCR version
- For maximum GPU performance: NVIDIA GPU with CUDA support and TensorRT (optional)
- Sufficient GPU memory (typically 1-2GB for mobile models)

#### Customization Options

1. **`--no-fast`**: Disable fast mode for better accuracy
   - Enables textline orientation classification
   - Better accuracy on rotated text, but slower

2. **`--cpu`**: Force CPU mode
   - Overrides auto GPU detection
   - Explicitly use CPU

3. **`--gpu`**: Force GPU mode
   - Will fail if GPU not available
   - Use when you want to ensure GPU usage

4. **`--ocr-version PP-OCRv5`**: Use better accuracy version
   - PP-OCRv5 has better accuracy but slower than PP-OCRv4 (default)
   - Uses server models

5. **`--max-size <pixels>`**: Adjust image processing size
   - Default: 640px
   - Larger values (e.g., 960, 1280) = better accuracy, slower
   - Smaller values (e.g., 480) = faster, may reduce accuracy

6. **`--hpi`**: High-Performance Inference
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

## Testing

Run tests using pytest:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=paddleocr_cli --cov-report=html

# Run specific test file
pytest tests/test_mcp_server.py

# Run specific test class or function
pytest tests/test_mcp_server.py::TestGetOCR
pytest tests/test_mcp_server.py::TestGetOCR::test_get_ocr_default_language
```

The test suite includes:
- OCR instance initialization and caching
- Tool listing and definition
- OCR tool calls with various parameters
- Language parameter handling
- File validation and error handling
- Markdown output generation
- Edge cases and error scenarios

## License

MIT
