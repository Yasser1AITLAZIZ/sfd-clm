"""Memory management utilities for large document processing"""
import gc
import io
import logging
from typing import Optional, Tuple
from PIL import Image

try:
    import psutil
    import os
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)


class MemoryManager:
    """Memory management for document processing"""
    
    # Maximum document size in bytes (50MB)
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024
    
    # Maximum image dimensions (to prevent excessive memory usage)
    MAX_IMAGE_WIDTH = 4000
    MAX_IMAGE_HEIGHT = 4000
    
    def __init__(self):
        """Initialize memory manager"""
        self.process = None
        if PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process(os.getpid())
            except Exception as e:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Could not initialize process monitor",
                    error_message=str(e) if e else "Unknown"
                )
    
    def get_memory_usage(self) -> Optional[dict]:
        """
        Get current memory usage.
        
        Returns:
            Dictionary with memory usage info or None if psutil unavailable
        """
        if not self.process:
            return None
        
        try:
            memory_info = self.process.memory_info()
            return {
                "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size in MB
                "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
                "percent": self.process.memory_percent()
            }
        except Exception as e:
            safe_log(
                logger,
                logging.WARNING,
                "Error getting memory usage",
                error_message=str(e) if e else "Unknown"
            )
            return None
    
    def log_memory_usage(self, context: str = ""):
        """
        Log current memory usage.
        
        Args:
            context: Context description for logging
        """
        memory = self.get_memory_usage()
        if memory:
            safe_log(
                logger,
                logging.INFO,
                f"Memory usage {context}",
                rss_mb=round(memory["rss_mb"], 2),
                vms_mb=round(memory["vms_mb"], 2),
                percent=round(memory["percent"], 2)
            )
    
    def validate_document_size(self, document_content: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate document size.
        
        Args:
            document_content: Document content as bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        size = len(document_content)
        
        if size > self.MAX_DOCUMENT_SIZE:
            error_msg = f"Document size {size / (1024 * 1024):.2f}MB exceeds maximum {self.MAX_DOCUMENT_SIZE / (1024 * 1024)}MB"
            safe_log(
                logger,
                logging.WARNING,
                "Document size validation failed",
                document_size_mb=round(size / (1024 * 1024), 2),
                max_size_mb=self.MAX_DOCUMENT_SIZE / (1024 * 1024)
            )
            return False, error_msg
        
        return True, None
    
    def compress_image(
        self,
        image_b64: str,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        quality: int = 85
    ) -> str:
        """
        Compress image by reducing size/quality.
        
        Args:
            image_b64: Base64 encoded image
            max_width: Maximum width (default: MAX_IMAGE_WIDTH)
            max_height: Maximum height (default: MAX_IMAGE_HEIGHT)
            quality: JPEG quality (1-100, default: 85)
            
        Returns:
            Compressed base64 encoded image
        """
        try:
            import base64
            
            if max_width is None:
                max_width = self.MAX_IMAGE_WIDTH
            if max_height is None:
                max_height = self.MAX_IMAGE_HEIGHT
            
            # Decode base64
            image_data = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_data))
            
            original_size = len(image_data)
            original_width, original_height = image.size
            
            # Resize if too large
            if original_width > max_width or original_height > max_height:
                # Calculate new dimensions maintaining aspect ratio
                ratio = min(max_width / original_width, max_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Image resized for memory optimization",
                    original_size=f"{original_width}x{original_height}",
                    new_size=f"{new_width}x{new_height}"
                )
            
            # Convert to RGB if necessary (for JPEG)
            if image.mode in ("RGBA", "P"):
                # Create white background
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                image = rgb_image
            
            # Save with compression
            buffer = io.BytesIO()
            
            # Use JPEG for better compression
            if image.format != "JPEG":
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
            else:
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
            
            compressed_data = buffer.getvalue()
            compressed_size = len(compressed_data)
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            safe_log(
                logger,
                logging.INFO,
                "Image compressed",
                original_size_kb=round(original_size / 1024, 2),
                compressed_size_kb=round(compressed_size / 1024, 2),
                compression_ratio=round(compression_ratio, 2)
            )
            
            # Encode back to base64
            compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
            
            return compressed_b64
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error compressing image",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return original if compression fails
            return image_b64
    
    def cleanup_memory(self):
        """
        Force garbage collection to free memory.
        """
        collected = gc.collect()
        safe_log(
            logger,
            logging.INFO,
            "Memory cleanup performed",
            objects_collected=collected
        )
    
    def should_compress_image(self, image_b64: str, threshold_mb: float = 5.0) -> bool:
        """
        Check if image should be compressed based on size.
        
        Args:
            image_b64: Base64 encoded image
            threshold_mb: Size threshold in MB
            
        Returns:
            True if image should be compressed
        """
        import base64
        try:
            # Estimate size from base64 (base64 is ~33% larger than binary)
            size_bytes = len(image_b64) * 3 / 4
            size_mb = size_bytes / (1024 * 1024)
            return size_mb > threshold_mb
        except:
            return False


