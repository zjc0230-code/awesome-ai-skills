#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart OCR - Intelligent Image Text Recognition
Supports multiple OCR engines with automatic fallback

Usage:
    python3 smart_ocr.py <image_path>
    python3 smart_ocr.py <image_url> --download
"""

import sys
import os
import json
from typing import Tuple, Optional

def get_image_info(image_path: str) -> dict:
    """Get basic image information"""
    try:
        from PIL import Image
        img = Image.open(image_path)
        size = os.path.getsize(image_path)
        
        return {
            'width': img.size[0],
            'height': img.size[1],
            'format': img.format,
            'mode': img.mode,
            'size_kb': round(size / 1024, 2)
        }
    except Exception as e:
        return {'error': str(e)}


def ocr_with_paddleocr(image_path: str) -> Tuple[Optional[str], str]:
    """OCR using PaddleOCR (best for Chinese)"""
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        result = ocr.ocr(image_path, cls=True)
        
        if not result or not result[0]:
            return None, "PaddleOCR: no text detected"
        
        lines = []
        for line in result[0]:
            lines.append(line[1][0])
        
        return '\n'.join(lines), 'PaddleOCR'
    except ImportError:
        return None, "PaddleOCR: not installed"
    except Exception as e:
        return None, f"PaddleOCR error: {e}"


def ocr_with_tesseract(image_path: str) -> Tuple[Optional[str], str]:
    """OCR using Tesseract"""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        
        if not text.strip():
            return None, "Tesseract: no text detected"
        
        return text.strip(), 'Tesseract'
    except ImportError:
        return None, "Tesseract: pytesseract not installed"
    except Exception as e:
        return None, f"Tesseract error: {e}"


def ocr_with_easyocr(image_path: str) -> Tuple[Optional[str], str]:
    """OCR using EasyOCR"""
    try:
        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
        result = reader.readtext(image_path)
        
        if not result:
            return None, "EasyOCR: no text detected"
        
        lines = [item[1] for item in result]
        return '\n'.join(lines), 'EasyOCR'
    except ImportError:
        return None, "EasyOCR: not installed"
    except Exception as e:
        return None, f"EasyOCR error: {e}"


def ocr_with_online_api(image_path: str) -> Tuple[Optional[str], str]:
    """OCR using OCR.space Free API"""
    try:
        import requests
        
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'file': f},
                data={'apikey': 'helloworld', 'language': 'chs'},
                timeout=60
            )
        
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            error_msg = result.get('ErrorMessage', ['Unknown error'])
            return None, f"OCR.space API error: {error_msg}"
        
        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return None, "OCR.space API: no results"
        
        text = parsed_results[0].get('ParsedText', '')
        if not text.strip():
            return None, "OCR.space API: no text detected"
        
        return text.strip(), 'OCR.space API'
    except ImportError:
        return None, "OCR.space API: requests not installed"
    except requests.exceptions.Timeout:
        return None, "OCR.space API: request timeout"
    except Exception as e:
        return None, f"OCR.space API error: {e}"


def download_image(url: str, output_path: str) -> bool:
    """Download image from URL"""
    try:
        import requests
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return False


def smart_ocr(image_path: str, output_format: str = 'text') -> dict:
    """
    Intelligent OCR with multiple engine fallback
    
    Args:
        image_path: Path to image file
        output_format: 'text', 'json', or 'markdown'
    
    Returns:
        dict with keys: success, text, engine, image_info, errors
    """
    result = {
        'success': False,
        'text': None,
        'engine': None,
        'image_info': None,
        'errors': []
    }
    
    if not os.path.exists(image_path):
        result['errors'].append(f"File not found: {image_path}")
        return result
    
    # Get image info
    result['image_info'] = get_image_info(image_path)
    
    # Try OCR engines in priority order
    engines = [
        ('PaddleOCR', ocr_with_paddleocr),
        ('Tesseract', ocr_with_tesseract),
        ('EasyOCR', ocr_with_easyocr),
        ('OCR.space API', ocr_with_online_api),
    ]
    
    for engine_name, engine_func in engines:
        text, message = engine_func(image_path)
        
        if text:
            result['success'] = True
            result['text'] = text
            result['engine'] = engine_name
            break
        else:
            result['errors'].append(message)
    
    return result


def format_output(result: dict, output_format: str = 'text') -> str:
    """Format OCR result for output"""
    if output_format == 'json':
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    elif output_format == 'markdown':
        lines = []
        lines.append("## 🖼️ OCR Recognition Result\n")
        
        if result['image_info'] and 'error' not in result['image_info']:
            info = result['image_info']
            lines.append(f"**Image Info**: {info['width']}x{info['height']} | {info['format']} | {info['size_kb']} KB\n")
        
        if result['success']:
            lines.append(f"**Engine**: {result['engine']}\n")
            lines.append("### Recognized Text\n")
            lines.append("```")
            lines.append(result['text'])
            lines.append("```")
        else:
            lines.append("### ❌ Recognition Failed\n")
            lines.append("**Attempted engines**:")
            for error in result['errors']:
                lines.append(f"- ⚠️ {error}")
        
        return '\n'.join(lines)
    
    else:  # text format
        if result['success']:
            return result['text']
        else:
            return "OCR failed: " + "; ".join(result['errors'])


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart OCR - Image Text Recognition')
    parser.add_argument('image', help='Image file path or URL')
    parser.add_argument('--download', '-d', action='store_true', help='Download from URL first')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'markdown'], default='text', help='Output format')
    parser.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    image_path = args.image
    
    # Handle URL download
    if args.download or image_path.startswith(('http://', 'https://')):
        import tempfile
        import hashlib
        
        url_hash = hashlib.md5(image_path.encode()).hexdigest()[:8]
        temp_path = os.path.join(tempfile.gettempdir(), f'ocr_image_{url_hash}.png')
        
        print(f"Downloading image to {temp_path}...", file=sys.stderr)
        if not download_image(image_path, temp_path):
            print("Failed to download image", file=sys.stderr)
            sys.exit(1)
        
        image_path = temp_path
    
    # Run OCR
    result = smart_ocr(image_path)
    
    # Format output
    output = format_output(result, args.format)
    
    # Write or print
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Result written to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    # Exit code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
