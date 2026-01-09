"""Main entry point for PaddleOCR CLI tool."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Disable model source check and connectivity check for faster startup
os.environ.setdefault('DISABLE_MODEL_SOURCE_CHECK', 'True')

from paddleocr import PaddleOCR


def check_gpu_available() -> bool:
    """
    Check if GPU is available for PaddlePaddle.
    
    Returns:
        True if GPU is available, False otherwise
    """
    try:
        import paddle
        return paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
    except Exception:
        return False


def image_to_markdown(image_path: str, output_path: Optional[str] = None, fast_mode: bool = True, 
                     use_gpu: Optional[bool] = None, ocr_version: Optional[str] = None, 
                     max_image_size: Optional[int] = None, enable_hpi: bool = False) -> str:
    """
    Convert image to markdown using PaddleOCR.
    
    Args:
        image_path: Path to input image
        output_path: Optional output markdown file path
        fast_mode: If True, disable preprocessing for faster inference. Default: True
        use_gpu: If True, use GPU; if False, use CPU; if None, auto-detect GPU. Default: None (auto-detect)
        ocr_version: OCR version ('PP-OCRv4' for faster, 'PP-OCRv5' for better accuracy). Default: 'PP-OCRv4'
        max_image_size: Maximum side length for image processing (e.g., 960, 640). Default: 640
        enable_hpi: Enable high-performance inference (requires HPI dependencies installed)
        
    Returns:
        Path to output markdown file
    """
    # Initialize PaddleOCR with optimized settings
    # Disable document preprocessing by default for faster inference (usually unnecessary for most images)
    ocr_kwargs = {
        'lang': 'ch',
        'use_doc_orientation_classify': False,  # Disable document orientation classification for speed
        'use_doc_unwarping': False,  # Disable document unwarping for speed
    }
    
    # OCR version selection: default to PP-OCRv4 for faster inference
    if ocr_version is None:
        ocr_version = 'PP-OCRv4'
    ocr_kwargs['ocr_version'] = ocr_version
    
    # Fast mode: disable all preprocessing for maximum speed (default: True)
    if fast_mode:
        ocr_kwargs['use_textline_orientation'] = False
    else:
        ocr_kwargs['use_textline_orientation'] = True
    
    # Image size limit: default to 640 for faster processing
    if max_image_size is None:
        max_image_size = 640
    ocr_kwargs['text_det_limit_side_len'] = max_image_size
    
    # GPU detection and selection
    # Auto-detect GPU if use_gpu is None
    if use_gpu is None:
        use_gpu = check_gpu_available()
        if use_gpu:
            print("GPU detected. Using GPU for inference.")
        else:
            print("GPU not available. Falling back to CPU.")
    
    # GPU device selection (PaddleOCR auto-detects GPU, but we can try to set via environment)
    # Note: device parameter may not be directly supported in all versions
    if use_gpu:
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
        # Try to set device if supported (will be ignored if not supported)
        try:
            ocr_kwargs['device'] = 'gpu:0'
        except:
            pass
    else:
        # Explicitly use CPU
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
    
    # High-Performance Inference (HPI) - automatically selects best inference backend
    # Note: Requires HPI dependencies installed via: paddleocr install_hpi_deps cpu/gpu
    if enable_hpi:
        ocr_kwargs['enable_hpi'] = True
    
    # Try to initialize PaddleOCR with GPU, fallback to CPU if it fails
    ocr = None
    gpu_fallback = False
    
    if use_gpu:
        try:
            ocr = PaddleOCR(**ocr_kwargs)
        except Exception as e:
            # If GPU initialization fails, try CPU fallback
            if 'cuda' in str(e).lower() or 'gpu' in str(e).lower() or 'device' in str(e).lower():
                print(f"GPU initialization failed: {e}")
                print("Falling back to CPU...")
                gpu_fallback = True
                # Remove GPU-specific settings
                if 'device' in ocr_kwargs:
                    del ocr_kwargs['device']
                os.environ['CUDA_VISIBLE_DEVICES'] = ''
                ocr_kwargs['device'] = 'cpu'
                try:
                    ocr = PaddleOCR(**ocr_kwargs)
                except Exception as cpu_e:
                    # If HPI is enabled but not installed, provide helpful error message
                    if enable_hpi and 'hpi' in str(cpu_e).lower():
                        raise RuntimeError(
                            "High-Performance Inference (HPI) requested but dependencies not installed. "
                            "Please install HPI dependencies first:\n"
                            "  paddleocr install_hpi_deps cpu   # for CPU\n"
                            "  paddleocr install_hpi_deps gpu   # for GPU"
                        ) from cpu_e
                    raise
            else:
                # For other errors (like HPI), handle them
                if enable_hpi and 'hpi' in str(e).lower():
                    raise RuntimeError(
                        "High-Performance Inference (HPI) requested but dependencies not installed. "
                        "Please install HPI dependencies first:\n"
                        "  paddleocr install_hpi_deps cpu   # for CPU\n"
                        "  paddleocr install_hpi_deps gpu   # for GPU"
                    ) from e
                raise
    else:
        # CPU mode
        try:
            ocr = PaddleOCR(**ocr_kwargs)
        except Exception as e:
            # If HPI is enabled but not installed, provide helpful error message
            if enable_hpi and 'hpi' in str(e).lower():
                raise RuntimeError(
                    "High-Performance Inference (HPI) requested but dependencies not installed. "
                    "Please install HPI dependencies first:\n"
                    "  paddleocr install_hpi_deps cpu   # for CPU\n"
                    "  paddleocr install_hpi_deps gpu   # for GPU"
                ) from e
            raise
    
    # Perform OCR
    result = ocr.predict(image_path)
    
    # Generate markdown content (optimized: use list join instead of repeated appends)
    markdown_lines = [
        "# OCR Result\n\n",
        f"**Source Image:** `{image_path}`\n\n",
        "---\n\n"
    ]
    
    if result and len(result) > 0:
        page_result = result[0]  # Get first page result
        rec_texts = page_result.get('rec_texts', [])
        
        if rec_texts:
            for text in rec_texts:
                markdown_lines.append(f"- {text}\n")
        else:
            markdown_lines.append("*No text detected in image.*\n")
    else:
        markdown_lines.append("*No text detected in image.*\n")
    
    markdown_content = "".join(markdown_lines)
    
    # Determine output path
    if output_path is None:
        image_path_obj = Path(image_path)
        output_path = f"{image_path_obj}.md"
    
    # Write markdown file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return output_path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PaddleOCR command line tool - Convert images to markdown"
    )
    parser.add_argument(
        "image",
        type=str,
        help="Path to input image file"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output markdown file path (default: <image_name>.md appended to input filename)"
    )
    parser.add_argument(
        "--no-fast",
        dest="fast",
        action="store_false",
        help="Disable fast mode (enables preprocessing for better accuracy on rotated text). Default: fast mode enabled"
    )
    parser.add_argument(
        "--cpu",
        dest="use_gpu",
        action="store_const",
        const=False,
        default=None,
        help="Force CPU mode (default: auto-detect GPU, fallback to CPU if not available)"
    )
    parser.add_argument(
        "--gpu",
        dest="use_gpu",
        action="store_const",
        const=True,
        default=None,
        help="Force GPU mode (will fail if GPU not available). Default: auto-detect"
    )
    parser.add_argument(
        "--ocr-version",
        type=str,
        choices=['PP-OCRv4', 'PP-OCRv5'],
        default=None,
        help="OCR version: PP-OCRv4 (faster, default) or PP-OCRv5 (better accuracy)"
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=None,
        metavar="PIXELS",
        help="Maximum image side length for processing (e.g., 960, 640). Default: 640"
    )
    parser.add_argument(
        "--hpi",
        action="store_true",
        help="Enable High-Performance Inference (automatically selects best backend). Requires: paddleocr install_hpi_deps"
    )
    
    args = parser.parse_args()
    
    # Validate input image exists
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)
    
    if not image_path.is_file():
        print(f"Error: Path is not a file: {args.image}", file=sys.stderr)
        sys.exit(1)
    
    try:
        output_path = image_to_markdown(
            str(image_path), 
            args.output, 
            fast_mode=args.fast, 
            use_gpu=args.use_gpu,
            ocr_version=args.ocr_version,
            max_image_size=args.max_size,
            enable_hpi=args.hpi
        )
        if args.hpi:
            print("Note: High-Performance Inference (HPI) enabled.")
        print(f"OCR completed. Output saved to: {output_path}")
    except Exception as e:
        print(f"Error during OCR processing: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
