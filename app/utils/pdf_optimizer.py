import io
import logging
from typing import BinaryIO, Optional, Tuple
import PyPDF2
from PIL import Image
import fitz  # PyMuPDF
import tempfile
import os

logger = logging.getLogger(__name__)


class PDFOptimizer:
    """Service for optimizing PDF files to reduce size without losing quality"""
    
    # Target file size in MB - stop optimization when reaching this
    TARGET_FILE_SIZE_MB = 10
    
    # Target DPI for images in PDFs
    TARGET_DPI = 150
    
    @staticmethod
    def should_optimize(file_size_bytes: int) -> bool:
        """Check if a PDF should be optimized - we optimize all PDFs"""
        return True  # Always try to optimize PDFs
    
    @staticmethod
    async def optimize_pdf(
        pdf_file: BinaryIO,
        original_size: int,
        target_size_mb: Optional[int] = None
    ) -> Tuple[BinaryIO, int, bool]:
        """
        Optimize a PDF file to reduce size while maintaining quality
        
        Args:
            pdf_file: The PDF file to optimize
            original_size: Original file size in bytes
            target_size_mb: Target size in MB (optional, defaults to 10MB)
            
        Returns:
            Tuple of (optimized_file, new_size, was_optimized)
        """
        target_size_mb = target_size_mb or PDFOptimizer.TARGET_FILE_SIZE_MB
        target_size_bytes = target_size_mb * 1024 * 1024
        
        # If already under target size, still try basic optimization
        if original_size <= target_size_bytes:
            logger.info(f"PDF already under {target_size_mb}MB ({original_size/1024/1024:.2f}MB), applying basic optimization")
        
        try:
            # First, try PyMuPDF optimization (better compression)
            optimized_file, new_size = await PDFOptimizer._optimize_with_pymupdf(
                pdf_file, original_size
            )
            
            # If still too large, try additional compression
            if new_size > target_size_bytes:
                logger.info(f"PDF still large after optimization ({new_size/1024/1024:.2f}MB), trying aggressive compression")
                optimized_file, new_size = await PDFOptimizer._aggressive_optimize(
                    optimized_file, new_size
                )
            
            # Check if we achieved meaningful compression
            compression_ratio = (original_size - new_size) / original_size
            was_optimized = compression_ratio > 0.1  # At least 10% reduction
            
            if was_optimized:
                logger.info(f"PDF optimized: {original_size/1024/1024:.2f}MB -> {new_size/1024/1024:.2f}MB ({compression_ratio*100:.1f}% reduction)")
            else:
                logger.info(f"PDF optimization resulted in minimal size reduction, using original")
                pdf_file.seek(0)
                return pdf_file, original_size, False
                
            return optimized_file, new_size, True
            
        except Exception as e:
            logger.error(f"Failed to optimize PDF: {str(e)}")
            # Return original file on error
            pdf_file.seek(0)
            return pdf_file, original_size, False
    
    @staticmethod
    async def _optimize_with_pymupdf(
        pdf_file: BinaryIO, 
        original_size: int
    ) -> Tuple[BinaryIO, int]:
        """Optimize PDF using PyMuPDF (better compression algorithms)"""
        pdf_file.seek(0)
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_in:
            temp_in.write(pdf_file.read())
            temp_in_path = temp_in.name
        
        try:
            # Open with PyMuPDF
            doc = fitz.open(temp_in_path)
            
            # Optimize settings
            optimize_output = io.BytesIO()
            
            # Save with optimization flags
            doc.save(
                optimize_output,
                garbage=4,  # Maximum garbage collection
                deflate=True,  # Compress streams
                deflate_images=True,  # Compress images
                deflate_fonts=True,  # Compress fonts
                clean=True,  # Clean up PDF
            )
            
            doc.close()
            
            # Get optimized size
            optimize_output.seek(0, 2)  # Seek to end
            new_size = optimize_output.tell()
            optimize_output.seek(0)  # Reset to beginning
            
            return optimize_output, new_size
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_in_path):
                os.unlink(temp_in_path)
    
    @staticmethod
    async def _aggressive_optimize(
        pdf_file: BinaryIO,
        current_size: int
    ) -> Tuple[BinaryIO, int]:
        """More aggressive optimization - reduce image quality"""
        pdf_file.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_in:
            temp_in.write(pdf_file.read())
            temp_in_path = temp_in.name
        
        try:
            doc = fitz.open(temp_in_path)
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get all images on the page
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    # Extract image
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha > 3:  # CMYK: convert to RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    # Convert to PIL Image for processing
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Reduce quality if image is large
                    if image.width > 1920 or image.height > 1920:
                        # Resize image maintaining aspect ratio
                        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                    
                    # Save with JPEG compression
                    img_buffer = io.BytesIO()
                    if image.mode == 'RGBA':
                        # Convert RGBA to RGB
                        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                        rgb_image.paste(image, mask=image.split()[3])
                        image = rgb_image
                    
                    image.save(img_buffer, format='JPEG', quality=85, optimize=True)
                    img_buffer.seek(0)
                    
                    # Replace image in PDF
                    page.clean_contents()
            
            # Save optimized PDF
            optimized_output = io.BytesIO()
            doc.save(
                optimized_output,
                garbage=4,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                clean=True,
            )
            doc.close()
            
            # Get new size
            optimized_output.seek(0, 2)
            new_size = optimized_output.tell()
            optimized_output.seek(0)
            
            return optimized_output, new_size
            
        finally:
            if os.path.exists(temp_in_path):
                os.unlink(temp_in_path)
    
    @staticmethod
    def get_pdf_info(pdf_file: BinaryIO) -> dict:
        """Get information about a PDF file"""
        pdf_file.seek(0)
        
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            
            info = {
                "pages": len(reader.pages),
                "encrypted": reader.is_encrypted,
                "title": reader.metadata.title if reader.metadata and reader.metadata.title else None,
                "author": reader.metadata.author if reader.metadata and reader.metadata.author else None,
                "subject": reader.metadata.subject if reader.metadata and reader.metadata.subject else None,
            }
            
            pdf_file.seek(0)
            return info
            
        except Exception as e:
            logger.error(f"Failed to get PDF info: {str(e)}")
            pdf_file.seek(0)
            return {"pages": 0, "encrypted": False}