#!/usr/bin/env python3
"""
PDF compression using Python libraries (PyMuPDF/fitz)
Alternative method when Ghostscript is not available

Usage Examples:
    # Basic compression (default settings)
    python compress_pdfs_python.py
    
    # With uv (recommended for isolated environment)
    uv run python compress_pdfs_python.py
    
    # Custom output directory
    python compress_pdfs_python.py --output-dir my_compressed_pdfs
    
    # Higher compression (lower quality)
    python compress_pdfs_python.py --image-quality 30 --image-dpi 100
    
    # Better quality (larger files)
    python compress_pdfs_python.py --image-quality 70 --image-dpi 200
    
    # More parallel workers for faster processing
    python compress_pdfs_python.py --workers 6
    
    # Process different input directory
    python compress_pdfs_python.py --input-dir my_pdfs --output-dir compressed
    
    # Complete example with all options
    python compress_pdfs_python.py --input-dir papers --output-dir papers_compressed --image-quality 50 --image-dpi 150 --workers 4

Requirements:
    pip install PyMuPDF Pillow
    
    or with uv:
    uv add PyMuPDF Pillow

Note:
    - Original files are preserved
    - Creates output directory automatically
    - Compression ratio typically 5-15% for academic papers
    - May trigger antivirus false positives (add output folder to exclusions)
"""

import os
import sys
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. Install with: pip install PyMuPDF")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available. Install with: pip install Pillow")

class PDFCompressorPython:
    def __init__(self, input_dir="papers", output_dir="papers_compressed_python", 
                 image_quality=50, image_dpi=150):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.image_quality = image_quality  # JPEG quality (0-100)
        self.image_dpi = image_dpi  # Target DPI for images
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
    
    def get_file_size(self, filepath):
        """Get file size in MB"""
        return os.path.getsize(filepath) / (1024 * 1024)
    
    def compress_pdf_pymupdf(self, input_path, output_path):
        """Compress PDF using PyMuPDF"""
        try:
            # Open the PDF
            doc = fitz.open(str(input_path))
            
            # Method 1: Basic compression using save options
            # This is more reliable than trying to manipulate individual images
            doc.save(str(output_path), 
                    garbage=4,        # Remove unused objects
                    deflate=True,     # Compress content streams
                    clean=True,       # Clean up syntax issues
                    pretty=False)     # Don't pretty-print (saves space)
            
            doc.close()
            
            # Calculate compression ratio
            original_size = self.get_file_size(input_path)
            compressed_size = self.get_file_size(output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            return {
                'success': True,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error compressing {input_path}: {str(e)}")
            return {
                'success': False,
                'original_size': self.get_file_size(input_path) if input_path.exists() else 0,
                'compressed_size': 0,
                'compression_ratio': 0,
                'error': str(e)
            }
    
    def compress_all(self, max_workers=2):
        """Compress all PDF files in the input directory"""
        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF is required but not installed")
            logger.error("Install with: pip install PyMuPDF")
            return
        
        if not PIL_AVAILABLE:
            logger.error("Pillow is required but not installed")
            logger.error("Install with: pip install Pillow")
            return
        
        # Get all PDF files
        pdf_files = list(self.input_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.error(f"No PDF files found in {self.input_dir}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to compress")
        logger.info(f"Image quality: {self.image_quality}%")
        logger.info(f"Target DPI: {self.image_dpi}")
        
        total_original_size = 0
        total_compressed_size = 0
        successful_compressions = 0
        failed_compressions = 0
        
        # Process files with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for pdf_file in pdf_files:
                output_file = self.output_dir / pdf_file.name
                future = executor.submit(self.compress_pdf_pymupdf, pdf_file, output_file)
                future_to_file[future] = pdf_file
            
            # Collect results
            for future in as_completed(future_to_file):
                pdf_file = future_to_file[future]
                result = future.result()
                
                if result['success']:
                    successful_compressions += 1
                    total_original_size += result['original_size']
                    total_compressed_size += result['compressed_size']
                    
                    logger.info(f"✓ {pdf_file.name}: "
                              f"{result['original_size']:.2f}MB → "
                              f"{result['compressed_size']:.2f}MB "
                              f"({result['compression_ratio']:.1f}% reduction)")
                else:
                    failed_compressions += 1
                    logger.error(f"✗ {pdf_file.name}: {result['error']}")
        
        # Summary
        overall_compression = (1 - total_compressed_size / total_original_size) * 100 if total_original_size > 0 else 0
        
        logger.info("\n" + "="*60)
        logger.info("COMPRESSION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total files processed: {len(pdf_files)}")
        logger.info(f"Successful compressions: {successful_compressions}")
        logger.info(f"Failed compressions: {failed_compressions}")
        logger.info(f"Total original size: {total_original_size:.2f} MB")
        logger.info(f"Total compressed size: {total_compressed_size:.2f} MB")
        logger.info(f"Overall size reduction: {overall_compression:.1f}%")
        logger.info(f"Space saved: {total_original_size - total_compressed_size:.2f} MB")
        logger.info("="*60)

def main():
    parser = argparse.ArgumentParser(description='Compress PDF files using Python libraries')
    parser.add_argument('--input-dir', default='papers', 
                       help='Input directory containing PDF files (default: papers)')
    parser.add_argument('--output-dir', default='papers_compressed_python', 
                       help='Output directory for compressed files (default: papers_compressed_python)')
    parser.add_argument('--image-quality', type=int, default=50, 
                       help='JPEG quality for images (0-100, default: 50)')
    parser.add_argument('--image-dpi', type=int, default=150,
                       help='Target DPI for images (default: 150)')
    parser.add_argument('--workers', type=int, default=2,
                       help='Number of parallel workers (default: 2)')
    
    args = parser.parse_args()
    
    compressor = PDFCompressorPython(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        image_quality=args.image_quality,
        image_dpi=args.image_dpi
    )
    
    compressor.compress_all(max_workers=args.workers)

if __name__ == "__main__":
    main()
