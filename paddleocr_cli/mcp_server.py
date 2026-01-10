"""MCP server for PaddleOCR - accepts image path and outputs image path + .md"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple

try:
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types
except ImportError:
    print("Error: mcp package is not installed. Please install it with: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("Error: paddleocr is not installed. Please install it with: pip install paddleocr", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    print("Error: pillow is not installed. Please install it with: pip install pillow", file=sys.stderr)
    sys.exit(1)

# Initialize MCP server
server = Server("fast-paddleocr-mcp")

# Cache PaddleOCR instance (lazy initialization with automatic fallback)
ocr_cache: dict[str, PaddleOCR] = {}

# Image preprocessing parameters
MAX_IMAGE_SIZE = 1920  # Maximum dimension (width or height) for automatic downsampling
SHARPEN_FACTOR = 1.2  # Sharpening factor (1.0 = no sharpening, higher = more sharpening)


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
    
    try:
        # Validate input file exists
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if not image_path_obj.is_file():
            raise ValueError(f"Path is not a file: {image_path}")
        
        # Preprocess image: automatic downsampling and sharpening
        # This improves OCR performance and accuracy
        preprocessed_path = preprocess_image(str(image_path_obj))
        
        try:
            # Initialize OCR with specified language
            ocr_instance = get_ocr(language=language)
            
            # Perform OCR on preprocessed image
            # PaddleOCR 2.7+ uses predict() method (ocr() is deprecated)
            result = ocr_instance.predict(preprocessed_path)
        finally:
            # Clean up temporary preprocessed image file
            try:
                if os.path.exists(preprocessed_path):
                    os.unlink(preprocessed_path)
            except Exception:
                pass  # Ignore cleanup errors
        
        # Generate output markdown file path (image.png -> image.png.md)
        output_path = Path(str(image_path_obj) + '.md')
        
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
        
        # Return the output file path
        return [types.TextContent(type="text", text=str(output_path))]
    
    except Exception as e:
        error_msg = f"Error processing image {image_path}: {str(e)}"
        print(error_msg, file=sys.stderr)
        raise RuntimeError(error_msg) from e


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


def main():
    """Main entry point for the MCP server (synchronous wrapper)"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
