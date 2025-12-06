"""PDF parsing module for extracting text and images from PDF textbooks."""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


@dataclass
class PDFPage:
    """Represents a single page from a PDF document."""
    
    page_number: int
    text: str
    images: list[Image.Image]
    is_image_based: bool


@dataclass
class PDFDocument:
    """Represents a parsed PDF document."""
    
    path: Path
    pages: list[PDFPage]
    total_pages: int
    
    def get_all_text(self) -> str:
        """Get all text from the document."""
        return "\n\n".join(page.text for page in self.pages)


class PDFParser:
    """Parser for extracting content from PDF files."""
    
    def __init__(self, use_ocr: bool = True):
        """
        Initialize the PDF parser.
        
        Args:
            use_ocr: Whether to use OCR for image-based pages.
        """
        self.use_ocr = use_ocr and HAS_TESSERACT
    
    def parse(self, pdf_path: str | Path) -> PDFDocument:
        """
        Parse a PDF file and extract its content.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            PDFDocument containing all extracted content.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        pages = []
        
        # First, try to extract text using pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                is_image_based = len(text.strip()) < 50  # Likely image-based if little text
                
                pages.append(PDFPage(
                    page_number=i + 1,
                    text=text,
                    images=[],
                    is_image_based=is_image_based
                ))
        
        # For image-based pages, use PyMuPDF + OCR
        if self.use_ocr:
            doc = fitz.open(pdf_path)
            for i, page_data in enumerate(pages):
                if page_data.is_image_based:
                    fitz_page = doc[i]
                    # Render page to image
                    pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    page_data.images.append(img)
                    
                    # Perform OCR
                    ocr_text = self._perform_ocr(img)
                    if ocr_text:
                        page_data.text = ocr_text
            doc.close()
        
        # Also extract embedded images using PyMuPDF
        doc = fitz.open(pdf_path)
        for i, page_data in enumerate(pages):
            fitz_page = doc[i]
            images = self._extract_images(fitz_page)
            page_data.images.extend(images)
        doc.close()
        
        return PDFDocument(
            path=pdf_path,
            pages=pages,
            total_pages=total_pages
        )
    
    def _perform_ocr(self, image: Image.Image) -> Optional[str]:
        """Perform OCR on an image."""
        if not HAS_TESSERACT:
            return None
        
        try:
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception:
            return None
    
    def _extract_images(self, page: fitz.Page) -> list[Image.Image]:
        """Extract embedded images from a PDF page."""
        images = []
        image_list = page.get_images(full=True)
        
        doc = page.parent
        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                img = Image.open(io.BytesIO(image_bytes))
                images.append(img)
            except Exception:
                continue
        
        return images
