"""MCP server for PaddleOCR - accepts image path and outputs image path + .md or .yaml (snapshot format)"""

import asyncio
import os
import random
import string
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

try:
    import yaml
except ImportError:
    print("Error: pyyaml is not installed. Please install it with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Initialize MCP server
server = Server("fast-paddleocr-mcp")

# Cache PaddleOCR instance (lazy initialization with automatic fallback)
ocr_cache: dict[str, PaddleOCR] = {}

# Image preprocessing parameters
MAX_IMAGE_SIZE = 1920  # Maximum dimension (width or height) for automatic downsampling
SHARPEN_FACTOR = 1.2  # Sharpening factor (1.0 = no sharpening, higher = more sharpening)


def generate_ref() -> str:
    """Generate a unique reference ID in snapshot format (ref-xxxxx)"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))
    return f"ref-{random_str}"


def extract_ocr_data(ocr_result: Any) -> Tuple[list[str], Optional[Any], Optional[Any]]:
    """Extract text, bbox, and other data from OCR result
    
    Args:
        ocr_result: OCRResult object from PaddleOCR
        
    Returns:
        Tuple of (rec_texts, dt_polys, rec_boxes)
    """
    rec_texts = None
    dt_polys = None
    rec_boxes = None
    
    # Try multiple ways to access OCR result data
    if hasattr(ocr_result, 'get'):
        rec_texts = ocr_result.get('rec_texts', [])
        dt_polys = ocr_result.get('dt_polys', None)
        rec_boxes = ocr_result.get('rec_boxes', None)
    elif isinstance(ocr_result, dict):
        rec_texts = ocr_result.get('rec_texts', [])
        dt_polys = ocr_result.get('dt_polys', None)
        rec_boxes = ocr_result.get('rec_boxes', None)
    elif hasattr(ocr_result, 'rec_texts'):
        rec_texts = ocr_result.rec_texts
        dt_polys = getattr(ocr_result, 'dt_polys', None)
        rec_boxes = getattr(ocr_result, 'rec_boxes', None)
    
    # Normalize rec_texts to list
    if rec_texts is None:
        rec_texts = []
    elif isinstance(rec_texts, str):
        rec_texts = [rec_texts] if rec_texts.strip() else []
    elif not isinstance(rec_texts, list):
        rec_texts = []
    
    return rec_texts, dt_polys, rec_boxes


def convert_bbox_to_original(
    bbox: list[float],
    original_size: Tuple[int, int],
    preprocessed_size: Tuple[int, int]
) -> dict[str, int]:
    """Convert bbox coordinates from preprocessed image to original image
    
    Args:
        bbox: Bounding box [x_min, y_min, x_max, y_max] in preprocessed image coordinates
        original_size: (width, height) of original image
        preprocessed_size: (width, height) of preprocessed image
        
    Returns:
        Dictionary with converted coordinates
    """
    if original_size == preprocessed_size:
        # No resize, return as is
        return {
            'x_min': int(bbox[0]),
            'y_min': int(bbox[1]),
            'x_max': int(bbox[2]),
            'y_max': int(bbox[3])
        }
    
    # Calculate scale factors
    scale_x = original_size[0] / preprocessed_size[0]
    scale_y = original_size[1] / preprocessed_size[1]
    
    # Convert coordinates
    return {
        'x_min': int(bbox[0] * scale_x),
        'y_min': int(bbox[1] * scale_y),
        'x_max': int(bbox[2] * scale_x),
        'y_max': int(bbox[3] * scale_y)
    }


def convert_polygon_to_original(
    polygon: list[list[float]],
    original_size: Tuple[int, int],
    preprocessed_size: Tuple[int, int]
) -> list[list[int]]:
    """Convert polygon coordinates from preprocessed image to original image
    
    Args:
        polygon: Polygon coordinates [[x1, y1], [x2, y2], ...] in preprocessed image
        original_size: (width, height) of original image
        preprocessed_size: (width, height) of preprocessed image
        
    Returns:
        List of converted coordinates
    """
    if original_size == preprocessed_size:
        # No resize, return as is
        return [[int(p[0]), int(p[1])] for p in polygon]
    
    # Calculate scale factors
    scale_x = original_size[0] / preprocessed_size[0]
    scale_y = original_size[1] / preprocessed_size[1]
    
    # Convert coordinates
    return [[int(p[0] * scale_x), int(p[1] * scale_y)] for p in polygon]


def generate_snapshot_format(
    ocr_results: list[Any],
    image_path: str,
    language: str,
    original_size: Optional[Tuple[int, int]] = None,
    preprocessed_size: Optional[Tuple[int, int]] = None
) -> str:
    """Generate snapshot format (YAML) from OCR results with bbox information
    
    Args:
        ocr_results: List of OCRResult objects from PaddleOCR
        image_path: Path to the source image
        language: Language code used for OCR
        
    Returns:
        YAML string in snapshot format
    """
    # Root container
    root = {
        'role': 'generic',
        'ref': generate_ref(),
        'name': f'OCR Result: {Path(image_path).name}',
        'children': []
    }
    
    # Add metadata as first child
    metadata = {
        'role': 'generic',
        'ref': generate_ref(),
        'children': [
            {
                'role': 'text',
                'name': f'Source Image: {image_path}',
                'ref': generate_ref()
            },
            {
                'role': 'text',
                'name': f'Language: {language}',
                'ref': generate_ref()
            }
        ]
    }
    root['children'].append(metadata)
    
    # Process each OCR result
    if ocr_results:
        for ocr_result in ocr_results:
            rec_texts, dt_polys, rec_boxes = extract_ocr_data(ocr_result)
            
            if rec_texts:
                # Create a container for this OCR result
                result_container = {
                    'role': 'generic',
                    'ref': generate_ref(),
                    'children': []
                }
                
                # Add each detected text as a text element with bbox info
                for idx, text in enumerate(rec_texts):
                    if not text or not text.strip():
                        continue
                    
                    text_element = {
                        'role': 'text',
                        'name': text.strip(),
                        'ref': generate_ref()
                    }
                    
                    # Add bbox information if available
                    # Try to get bbox from rec_boxes first (rectangular format)
                    if rec_boxes is not None:
                        try:
                            # Handle numpy array or list
                            if hasattr(rec_boxes, '__len__'):
                                if idx < len(rec_boxes):
                                    bbox = rec_boxes[idx]
                                    # Convert numpy array to list if needed
                                    if hasattr(bbox, 'tolist'):
                                        bbox = bbox.tolist()
                                    elif hasattr(bbox, '__iter__') and not isinstance(bbox, str):
                                        bbox = list(bbox)
                                    
                                    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                                        # Convert coordinates to original image if needed
                                        if original_size and preprocessed_size:
                                            text_element['bbox'] = convert_bbox_to_original(
                                                bbox, original_size, preprocessed_size
                                            )
                                        else:
                                            text_element['bbox'] = {
                                                'x_min': int(bbox[0]),
                                                'y_min': int(bbox[1]),
                                                'x_max': int(bbox[2]),
                                                'y_max': int(bbox[3])
                                            }
                        except (IndexError, TypeError, AttributeError, ValueError):
                            pass
                    
                    # If no bbox from rec_boxes, try dt_polys (polygon format)
                    if 'bbox' not in text_element and dt_polys is not None:
                        try:
                            # Handle numpy array or list
                            if hasattr(dt_polys, '__len__'):
                                if idx < len(dt_polys):
                                    poly = dt_polys[idx]
                                    # Convert numpy array to list if needed
                                    if hasattr(poly, 'tolist'):
                                        poly = poly.tolist()
                                    elif hasattr(poly, '__iter__') and not isinstance(poly, str):
                                        poly = list(poly)
                                    
                                    if isinstance(poly, (list, tuple)) and len(poly) >= 4:
                                        # Extract coordinates from polygon
                                        polygon_coords = []
                                        for p in poly[:4]:
                                            if hasattr(p, 'tolist'):
                                                p = p.tolist()
                                            elif hasattr(p, '__iter__') and not isinstance(p, str):
                                                p = list(p)
                                            if isinstance(p, (list, tuple)) and len(p) >= 2:
                                                polygon_coords.append([int(p[0]), int(p[1])])
                                        
                                        if len(polygon_coords) == 4:
                                            # Convert coordinates to original image if needed
                                            if original_size and preprocessed_size:
                                                converted_polygon = convert_polygon_to_original(
                                                    polygon_coords, original_size, preprocessed_size
                                                )
                                                text_element['bbox'] = {
                                                    'polygon': converted_polygon
                                                }
                                            else:
                                                text_element['bbox'] = {
                                                    'polygon': polygon_coords
                                                }
                        except (IndexError, TypeError, AttributeError, ValueError):
                            pass
                    
                    result_container['children'].append(text_element)
                
                if result_container['children']:
                    root['children'].append(result_container)
    
    # Convert to YAML format (list format like example-snapshot.log)
    snapshot_list = [root]
    
    # Generate YAML string
    yaml_str = yaml.dump(
        snapshot_list,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
        indent=2
    )
    
    return yaml_str


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
            description="Extract text from an image using PaddleOCR with automatic optimizations. Returns paths to both markdown file (image_path + .md) and snapshot file (image_path + .snapshot.log) with bbox information. All optimizations are applied automatically.",
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
        
        # Get original image size before preprocessing
        from PIL import Image
        original_img = Image.open(str(image_path_obj))
        original_size = original_img.size  # (width, height)
        original_img.close()
        
        # Preprocess image: automatic downsampling and sharpening
        # This improves OCR performance and accuracy
        preprocessed_path = preprocess_image(str(image_path_obj))
        
        # Get preprocessed image size
        # Try to open preprocessed image, fallback to original size if it fails
        try:
            if os.path.exists(preprocessed_path):
                preprocessed_img = Image.open(preprocessed_path)
                preprocessed_size = preprocessed_img.size  # (width, height)
                preprocessed_img.close()
            else:
                # If preprocessed file doesn't exist, use original size
                preprocessed_size = original_size
        except Exception:
            # If opening preprocessed image fails (e.g., in tests with mocked paths), use original size
            preprocessed_size = original_size
        
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
        
        # Generate output file paths (both markdown and snapshot)
        markdown_path = Path(str(image_path_obj) + '.md')
        snapshot_path = Path(str(image_path_obj) + '.snapshot.log')
        
        # Extract text from OCR result for markdown
        # PaddleOCR 2.7+ returns OCRResult objects (dictionary-like) with rec_texts field
        detected_texts = []
        if result and len(result) > 0:
            for ocr_result in result:
                rec_texts, _, _ = extract_ocr_data(ocr_result)
                
                if rec_texts:
                    if isinstance(rec_texts, list):
                        # rec_texts is a list of detected text strings, filter out empty strings
                        detected_texts.extend([text for text in rec_texts if text and text.strip()])
                    elif isinstance(rec_texts, str):
                        # If it's a single string, add it
                        if rec_texts.strip():
                            detected_texts.append(rec_texts)
        
        # Write markdown file
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write("# OCR Result\n\n")
            f.write(f"**Source Image:** `{image_path}`\n\n")
            f.write(f"**Language:** `{language}`\n\n")
            f.write("---\n\n")
            
            if detected_texts:
                for text in detected_texts:
                    f.write(f"- {text}\n")
            else:
                f.write("- No text detected\n")
        
        # Generate and write snapshot format (YAML) with bbox information
        # Convert coordinates to original image coordinates
        snapshot_yaml = generate_snapshot_format(
            result, 
            str(image_path_obj), 
            language,
            original_size=original_size,
            preprocessed_size=preprocessed_size
        )
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            f.write(snapshot_yaml)
        
        # Return both output file paths
        return [
            types.TextContent(type="text", text=str(markdown_path)),
            types.TextContent(type="text", text=str(snapshot_path))
        ]
    
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
                server_version="0.5.0",
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
