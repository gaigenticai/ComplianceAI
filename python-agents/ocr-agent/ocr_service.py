"""
OCR Agent Service for KYC Automation Platform

This service handles Optical Character Recognition (OCR) processing for identity documents.
It extracts text from uploaded documents and identifies key information like names, 
dates of birth, and ID numbers.

Features:
- Document text extraction using Tesseract OCR
- Image preprocessing for better OCR accuracy
- Structured data extraction from common ID document formats
- Document quality assessment
- Support for multiple document types (passport, driver's license, national ID)
"""

import os
import re
import cv2
import numpy as np
import pytesseract
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from PIL import Image, ImageEnhance, ImageFilter
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OCR Agent Service",
    description="Document OCR processing for KYC verification",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DocumentInfo(BaseModel):
    """Document information structure"""
    document_type: str
    file_path: str
    filename: str
    file_size: int
    mime_type: str

class OCRRequest(BaseModel):
    """OCR processing request structure"""
    request_id: str
    documents: List[DocumentInfo]

class ExtractedData(BaseModel):
    """Extracted data from document"""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    document_number: Optional[str] = None
    nationality: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    issuing_authority: Optional[str] = None

class OCRResult(BaseModel):
    """OCR processing result"""
    document_type: str
    extracted_text: str
    extracted_data: ExtractedData
    confidence_score: float = Field(ge=0, le=100)
    document_quality: float = Field(ge=0, le=100)
    processing_time_ms: int
    errors: List[str] = []
    warnings: List[str] = []

class OCRResponse(BaseModel):
    """OCR service response"""
    agent_name: str = "ocr"
    status: str
    data: Dict[str, Any]
    processing_time: int
    error: Optional[str] = None
    version: str = "1.0.0"

class OCRProcessor:
    """Main OCR processing class"""
    
    def __init__(self):
        """Initialize OCR processor with configuration"""
        # Configure Tesseract path if needed
        # pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        
        # Document type patterns for data extraction
        self.document_patterns = {
            'passport': {
                'name_patterns': [
                    r'(?:Given Names?|First Name)\s*:?\s*([A-Z\s]+)',
                    r'(?:Surname|Last Name|Family Name)\s*:?\s*([A-Z\s]+)',
                    r'Name\s*:?\s*([A-Z\s,]+)',
                ],
                'dob_patterns': [
                    r'(?:Date of Birth|DOB|Born)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{2,4})',
                ],
                'id_patterns': [
                    r'(?:Passport No|Passport Number|Document No)\s*:?\s*([A-Z0-9]+)',
                    r'([A-Z]{1,2}\d{6,9})',
                ],
                'nationality_patterns': [
                    r'(?:Nationality|Country)\s*:?\s*([A-Z\s]+)',
                ],
            },
            'drivers_license': {
                'name_patterns': [
                    r'(?:Name|Full Name)\s*:?\s*([A-Z\s,]+)',
                    r'([A-Z]+,\s*[A-Z\s]+)',
                ],
                'dob_patterns': [
                    r'(?:DOB|Date of Birth|Born)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                ],
                'id_patterns': [
                    r'(?:License No|DL|Driver License)\s*:?\s*([A-Z0-9\-]+)',
                    r'([A-Z]{1,2}\d{6,12})',
                ],
                'address_patterns': [
                    r'(?:Address|Addr)\s*:?\s*([A-Z0-9\s,\.]+)',
                ],
            },
            'national_id': {
                'name_patterns': [
                    r'(?:Name|Full Name)\s*:?\s*([A-Z\s,]+)',
                ],
                'dob_patterns': [
                    r'(?:DOB|Date of Birth|Born)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                ],
                'id_patterns': [
                    r'(?:ID No|National ID|Identity)\s*:?\s*([A-Z0-9\-]+)',
                    r'(\d{9,15})',
                ],
            }
        }
        
        logger.info("OCR Processor initialized")

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image from {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up the image
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
            
            return processed
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            # Return original image if preprocessing fails
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    def assess_document_quality(self, image_path: str) -> float:
        """
        Assess the quality of the document image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Quality score from 0-100
        """
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return 0.0
            
            # Calculate sharpness using Laplacian variance
            laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
            
            # Calculate brightness
            brightness = np.mean(image)
            
            # Calculate contrast
            contrast = np.std(image)
            
            # Normalize scores
            sharpness_score = min(laplacian_var / 1000, 1.0) * 40  # Max 40 points
            brightness_score = (1.0 - abs(brightness - 127) / 127) * 30  # Max 30 points
            contrast_score = min(contrast / 50, 1.0) * 30  # Max 30 points
            
            total_score = sharpness_score + brightness_score + contrast_score
            
            logger.info(f"Document quality assessment: {total_score:.1f}/100")
            return min(total_score, 100.0)
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            return 50.0  # Default medium quality

    def extract_text_from_image(self, image_path: str) -> tuple[str, float]:
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Configure Tesseract
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:/- '
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(
                processed_image, 
                config=custom_config, 
                output_type=pytesseract.Output.DICT
            )
            
            # Filter out low-confidence text
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 30]
            texts = [data['text'][i] for i, conf in enumerate(data['conf']) if int(conf) > 30]
            
            # Calculate average confidence
            avg_confidence = np.mean(confidences) if confidences else 0
            
            # Combine text
            extracted_text = ' '.join(texts).strip()
            
            logger.info(f"OCR extracted {len(extracted_text)} characters with {avg_confidence:.1f}% confidence")
            
            return extracted_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return "", 0.0

    def extract_structured_data(self, text: str, document_type: str) -> ExtractedData:
        """
        Extract structured data from OCR text based on document type
        
        Args:
            text: Raw OCR text
            document_type: Type of document (passport, drivers_license, national_id)
            
        Returns:
            ExtractedData object with parsed information
        """
        extracted_data = ExtractedData()
        
        # Normalize document type
        doc_type = document_type.lower().replace(' ', '_').replace('-', '_')
        if 'passport' in doc_type:
            doc_type = 'passport'
        elif 'driver' in doc_type or 'license' in doc_type:
            doc_type = 'drivers_license'
        elif 'national' in doc_type or 'id' in doc_type:
            doc_type = 'national_id'
        
        patterns = self.document_patterns.get(doc_type, self.document_patterns['passport'])
        
        # Extract name
        for pattern in patterns.get('name_patterns', []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                extracted_data.name = name
                
                # Try to split into first and last name
                name_parts = name.replace(',', '').split()
                if len(name_parts) >= 2:
                    extracted_data.first_name = name_parts[0]
                    extracted_data.last_name = ' '.join(name_parts[1:])
                break
        
        # Extract date of birth
        for pattern in patterns.get('dob_patterns', []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dob = match.group(1).strip()
                # Normalize date format
                extracted_data.date_of_birth = self.normalize_date(dob)
                break
        
        # Extract ID number
        for pattern in patterns.get('id_patterns', []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted_data.id_number = match.group(1).strip()
                break
        
        # Extract nationality (for passports)
        if doc_type == 'passport':
            for pattern in patterns.get('nationality_patterns', []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data.nationality = match.group(1).strip()
                    break
        
        # Extract address (for driver's licenses)
        if doc_type == 'drivers_license':
            for pattern in patterns.get('address_patterns', []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data.address = match.group(1).strip()
                    break
        
        # Extract gender
        gender_match = re.search(r'(?:Sex|Gender|M/F)\s*:?\s*([MF])', text, re.IGNORECASE)
        if gender_match:
            gender = gender_match.group(1).upper()
            extracted_data.gender = 'Male' if gender == 'M' else 'Female'
        
        # Extract dates (issue/expiry)
        date_patterns = [
            r'(?:Issue Date|Issued)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(?:Expiry Date|Expires|Valid Until)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        ]
        
        for i, pattern in enumerate(date_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = self.normalize_date(match.group(1))
                if i == 0:
                    extracted_data.issue_date = date_str
                else:
                    extracted_data.expiry_date = date_str
        
        logger.info(f"Extracted structured data: {extracted_data.dict()}")
        return extracted_data

    def normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string
        """
        try:
            # Remove extra spaces and normalize separators
            date_str = re.sub(r'[\/\-\.]', '-', date_str.strip())
            
            # Try different date formats
            formats = [
                '%d-%m-%Y', '%m-%d-%Y', '%Y-%m-%d',
                '%d-%m-%y', '%m-%d-%y', '%y-%m-%d',
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    # Convert 2-digit years to 4-digit
                    if parsed_date.year < 100:
                        if parsed_date.year > 50:
                            parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                        else:
                            parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                    
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # If no format matches, return original
            return date_str
            
        except Exception as e:
            logger.warning(f"Date normalization failed for '{date_str}': {str(e)}")
            return date_str

    def process_document(self, document_info: DocumentInfo) -> OCRResult:
        """
        Process a single document for OCR
        
        Args:
            document_info: Document information
            
        Returns:
            OCR processing result
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        try:
            # Check if file exists
            if not os.path.exists(document_info.file_path):
                raise FileNotFoundError(f"Document file not found: {document_info.file_path}")
            
            # Assess document quality
            quality_score = self.assess_document_quality(document_info.file_path)
            if quality_score < 50:
                warnings.append(f"Low document quality detected: {quality_score:.1f}/100")
            
            # Extract text
            extracted_text, confidence = self.extract_text_from_image(document_info.file_path)
            
            if not extracted_text.strip():
                errors.append("No text could be extracted from the document")
                confidence = 0.0
            
            # Extract structured data
            extracted_data = self.extract_structured_data(extracted_text, document_info.document_type)
            
            # Validate extracted data
            if not extracted_data.name and not extracted_data.id_number:
                warnings.append("Could not extract key identifying information (name or ID number)")
            
            # Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return OCRResult(
                document_type=document_info.document_type,
                extracted_text=extracted_text,
                extracted_data=extracted_data,
                confidence_score=confidence,
                document_quality=quality_score,
                processing_time_ms=processing_time,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return OCRResult(
                document_type=document_info.document_type,
                extracted_text="",
                extracted_data=ExtractedData(),
                confidence_score=0.0,
                document_quality=0.0,
                processing_time_ms=processing_time,
                errors=[str(e)],
                warnings=warnings
            )

# Initialize OCR processor
ocr_processor = OCRProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ocr-agent",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process", response_model=OCRResponse)
async def process_ocr_request(request: OCRRequest):
    """
    Process OCR request for document text extraction
    
    Args:
        request: OCR processing request
        
    Returns:
        OCR processing response
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing OCR request: {request.request_id}")
        
        results = []
        total_confidence = 0.0
        total_quality = 0.0
        
        # Process each document
        for doc_info in request.documents:
            # Skip selfie documents for OCR
            if 'selfie' in doc_info.document_type.lower():
                continue
                
            result = ocr_processor.process_document(doc_info)
            results.append(result.dict())
            total_confidence += result.confidence_score
            total_quality += result.document_quality
        
        if not results:
            raise ValueError("No valid documents found for OCR processing")
        
        # Calculate averages
        avg_confidence = total_confidence / len(results)
        avg_quality = total_quality / len(results)
        
        # Calculate overall risk score based on quality and confidence
        risk_score = max(0, 100 - (avg_confidence * 0.6 + avg_quality * 0.4))
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        response_data = {
            "results": results,
            "summary": {
                "documents_processed": len(results),
                "average_confidence": avg_confidence,
                "average_quality": avg_quality,
                "risk_score": risk_score
            }
        }
        
        return OCRResponse(
            status="Success",
            data=response_data,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return OCRResponse(
            status="Error",
            data={"error": str(e)},
            processing_time=processing_time,
            error=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "OCR Agent",
        "description": "Document OCR processing for KYC verification",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process": "/process"
        }
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8001))
    
    # Run the service
    uvicorn.run(
        "ocr_service:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
