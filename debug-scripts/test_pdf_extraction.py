"""
Test script to diagnose PDF extraction issues
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend-mcp"))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_pdf_extraction():
    """Test PDF extraction with different libraries"""
    logger.info("=" * 80)
    logger.info("PDF EXTRACTION DIAGNOSTIC TEST")
    logger.info("=" * 80)
    
    # Test 1: Check available libraries
    logger.info("\n1. Checking available PDF libraries...")
    try:
        import fitz  # PyMuPDF
        logger.info("✅ PyMuPDF (fitz) is available")
        pymupdf_available = True
    except ImportError as e:
        logger.warning(f"❌ PyMuPDF not available: {e}")
        pymupdf_available = False
    
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image
        logger.info("✅ pdf2image is available")
        pdf2image_available = True
    except ImportError as e:
        logger.warning(f"❌ pdf2image not available: {e}")
        pdf2image_available = False
    
    # Test 2: Try to download a test PDF
    logger.info("\n2. Downloading test PDF...")
    import httpx
    
    pdf_url = "http://localhost:8001/documents/001XX000001_Claim_Declaration_GlassBreak_EN.pdf"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(pdf_url, timeout=10.0)
            if response.status_code == 200:
                pdf_content = response.content
                logger.info(f"✅ PDF downloaded successfully ({len(pdf_content)} bytes)")
            else:
                logger.error(f"❌ Failed to download PDF: HTTP {response.status_code}")
                return
    except Exception as e:
        logger.error(f"❌ Error downloading PDF: {type(e).__name__}: {e}")
        return
    
    # Test 3: Try PyMuPDF extraction
    if pymupdf_available:
        logger.info("\n3. Testing PyMuPDF extraction...")
        try:
            import fitz
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(doc)
            logger.info(f"✅ PyMuPDF: PDF has {page_count} pages")
            
            # Extract first page
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            logger.info(f"✅ PyMuPDF: First page extracted ({pix.width}x{pix.height})")
            doc.close()
        except Exception as e:
            logger.error(f"❌ PyMuPDF extraction failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Test 4: Try pdf2image extraction
    if pdf2image_available:
        logger.info("\n4. Testing pdf2image extraction...")
        try:
            from pdf2image import convert_from_bytes
            logger.info("Attempting to convert PDF to images...")
            images = convert_from_bytes(pdf_content, dpi=200)
            logger.info(f"✅ pdf2image: Successfully converted to {len(images)} images")
            if images:
                logger.info(f"✅ First image size: {images[0].size}")
        except Exception as e:
            logger.error(f"❌ pdf2image extraction failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Check for poppler error
            error_msg = str(e).lower()
            if "poppler" in error_msg or "pdftoppm" in error_msg:
                logger.error("\n" + "=" * 80)
                logger.error("POppler ERROR DETECTED")
                logger.error("=" * 80)
                logger.error("pdf2image requires poppler-utils to be installed.")
                logger.error("\nInstallation instructions:")
                logger.error("  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
                logger.error("           Extract and add to PATH, or set POPPLER_PATH environment variable")
                logger.error("  Linux:   sudo apt-get install poppler-utils")
                logger.error("  Mac:     brew install poppler")
                logger.error("\nAlternatively, install PyMuPDF which doesn't require system dependencies:")
                logger.error("  pip install PyMuPDF")
    
    # Test 5: Test PDFProcessor
    logger.info("\n5. Testing PDFProcessor class...")
    try:
        from app.services.preprocessing.pdf_processor import PDFProcessor
        processor = PDFProcessor()
        logger.info(f"✅ PDFProcessor initialized")
        logger.info(f"   - PyMuPDF available: {processor.use_pymupdf}")
        logger.info(f"   - pdf2image available: {processor.use_pdf2image}")
        
        if processor.use_pymupdf or processor.use_pdf2image:
            logger.info("Attempting to extract pages...")
            pages = processor.extract_pdf_pages(pdf_content, dpi=200)
            logger.info(f"✅ PDFProcessor extracted {len(pages)} pages")
            if pages:
                logger.info(f"   - First page keys: {list(pages[0].keys())}")
        else:
            logger.error("❌ No PDF processing library available in PDFProcessor")
    except Exception as e:
        logger.error(f"❌ PDFProcessor test failed: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_pdf_extraction())

