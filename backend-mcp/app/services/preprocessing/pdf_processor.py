"""PDF processing utilities for multi-page extraction"""
import base64
import io
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)

# Import memory manager if available (for backend-langgraph)
try:
    from app.utils.memory_manager import MemoryManager
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False
    MemoryManager = None


class PDFProcessor:
    """Processor for extracting pages from PDF documents"""
    
    def __init__(self):
        """Initialize PDF processor"""
        self.use_pymupdf = PYMUPDF_AVAILABLE
        self.use_pdf2image = PDF2IMAGE_AVAILABLE
        
        # Initialize memory manager if available
        self.memory_manager = None
        if MEMORY_MANAGER_AVAILABLE and MemoryManager:
            try:
                self.memory_manager = MemoryManager()
            except:
                pass
        
        if not self.use_pymupdf and not self.use_pdf2image:
            safe_log(
                logger,
                logging.WARNING,
                "No PDF processing library available. Install PyMuPDF or pdf2image."
            )
        else:
            preferred = "PyMuPDF" if self.use_pymupdf else "pdf2image"
            safe_log(
                logger,
                logging.INFO,
                f"PDFProcessor initialized using {preferred}"
            )
    
    def get_page_count(self, pdf_content: bytes) -> int:
        """
        Get the number of pages in a PDF.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Number of pages
        """
        if self.use_pymupdf:
            try:
                doc = fitz.open(stream=pdf_content, filetype="pdf")
                page_count = len(doc)
                doc.close()
                return page_count
            except Exception as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Error getting page count with PyMuPDF",
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return 0
        
        # Fallback: try to count pages using pdf2image (slower)
        if self.use_pdf2image:
            try:
                images = convert_from_bytes(pdf_content, first_page=1, last_page=1)
                # This is a workaround - we'll need to process all pages to count
                # For now, return 1 if we can at least open the PDF
                return 1  # Will be updated when processing pages
            except Exception as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Error getting page count with pdf2image",
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return 0
        
        return 0
    
    def extract_pdf_pages(
        self,
        pdf_content: bytes,
        batch_size: int = 5,
        dpi: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Extract all pages from PDF and convert to base64 images.
        
        Args:
            pdf_content: PDF file content as bytes
            batch_size: Number of pages to process at once (for memory management)
            dpi: DPI for image conversion (higher = better quality, larger size)
            
        Returns:
            List of page dictionaries with page_number, image_b64, and image_mime
        """
        pages = []
        
        if self.use_pymupdf:
            try:
                doc = fitz.open(stream=pdf_content, filetype="pdf")
                total_pages = len(doc)
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Extracting PDF pages with PyMuPDF",
                    total_pages=total_pages,
                    batch_size=batch_size
                )
                
                # Process pages in batches to manage memory
                for page_num in range(total_pages):
                    try:
                        page = doc[page_num]
                        
                        # Convert page to image (pixmap)
                        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                        
                        # Convert to PIL Image
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        # Convert to base64
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG", optimize=True)
                        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        
                        pages.append({
                            "page_number": page_num + 1,
                            "image_b64": img_b64,
                            "image_mime": "image/png"
                        })
                        
                        # Clean up
                        pix = None
                        img = None
                        
                        # Memory cleanup after each page
                        if self.memory_manager:
                            self.memory_manager.cleanup_memory()
                        
                        # Log progress for large PDFs
                        if (page_num + 1) % batch_size == 0:
                            safe_log(
                                logger,
                                logging.INFO,
                                "PDF page extraction progress",
                                processed_pages=page_num + 1,
                                total_pages=total_pages
                            )
                            if self.memory_manager:
                                self.memory_manager.log_memory_usage(f"after {page_num + 1} pages")
                    
                    except Exception as e:
                        safe_log(
                            logger,
                            logging.ERROR,
                            f"Error processing PDF page {page_num + 1}",
                            error_type=type(e).__name__,
                            error_message=str(e) if e else "Unknown"
                        )
                        continue
                
                doc.close()
                
                safe_log(
                    logger,
                    logging.INFO,
                    "PDF pages extracted successfully",
                    total_pages=len(pages)
                )
                
                return pages
                
            except Exception as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Error extracting PDF pages with PyMuPDF",
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
        
        # Fallback to pdf2image
        if self.use_pdf2image:
            try:
                safe_log(
                    logger,
                    logging.INFO,
                    "Extracting PDF pages with pdf2image",
                    batch_size=batch_size
                )
                
                # Convert PDF to images (processes all pages)
                images = convert_from_bytes(pdf_content, dpi=dpi)
                
                for page_num, img in enumerate(images):
                    try:
                        # Convert to base64
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG", optimize=True)
                        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        
                        pages.append({
                            "page_number": page_num + 1,
                            "image_b64": img_b64,
                            "image_mime": "image/png"
                        })
                        
                        # Clean up
                        img = None
                        
                        # Log progress
                        if (page_num + 1) % batch_size == 0:
                            safe_log(
                                logger,
                                logging.INFO,
                                "PDF page extraction progress",
                                processed_pages=page_num + 1,
                                total_pages=len(images)
                            )
                    
                    except Exception as e:
                        safe_log(
                            logger,
                            logging.ERROR,
                            f"Error processing PDF page {page_num + 1} with pdf2image",
                            error_type=type(e).__name__,
                            error_message=str(e) if e else "Unknown"
                        )
                        continue
                
                safe_log(
                    logger,
                    logging.INFO,
                    "PDF pages extracted successfully with pdf2image",
                    total_pages=len(pages)
                )
                
                return pages
                
            except Exception as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Error extracting PDF pages with pdf2image",
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
        
        # If no library available, return empty list
        safe_log(
            logger,
            logging.WARNING,
            "No PDF processing library available, cannot extract pages"
        )
        return []

