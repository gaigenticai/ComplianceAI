"""
Watchlist Screening Agent Service for KYC Automation Platform

This service handles watchlist screening for AML (Anti-Money Laundering) compliance.
It checks customer information against various watchlists including sanctions lists,
PEP (Politically Exposed Persons) databases, and other compliance databases.

Features:
- Multiple watchlist database support (OFAC, EU, UN, PEP, etc.)
- Fuzzy name matching with configurable thresholds
- Date of birth verification
- Nationality and address matching
- Risk scoring based on match quality and list type
- Detailed match reporting with confidence scores
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import logging
import re
from fuzzywuzzy import fuzz, process
import phonenumbers
import pycountry

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Watchlist Screening Agent Service",
    description="AML watchlist screening for KYC compliance",
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

class CustomerInfo(BaseModel):
    """Customer information structure"""
    customer_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    metadata: Dict[str, str] = {}

class IdentityData(BaseModel):
    """Identity data from OCR results"""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    address: Optional[str] = None

class WatchlistRequest(BaseModel):
    """Watchlist screening request structure"""
    request_id: str
    identity_data: Optional[Dict[str, Any]] = None
    customer_info: CustomerInfo

class WatchlistMatch(BaseModel):
    """Individual watchlist match result"""
    list_name: str
    match_type: str  # exact, fuzzy, partial
    matched_name: str
    original_name: str
    confidence_score: float = Field(ge=0, le=100)
    match_details: Dict[str, Any] = {}
    risk_level: str  # low, medium, high, critical
    additional_info: Dict[str, Any] = {}

class ScreeningResult(BaseModel):
    """Watchlist screening result"""
    flagged: bool
    total_matches: int
    matches: List[WatchlistMatch] = []
    highest_risk_level: str = "low"
    overall_confidence: float = Field(ge=0, le=100)
    lists_checked: List[str] = []
    processing_time_ms: int
    errors: List[str] = []
    warnings: List[str] = []

class WatchlistResponse(BaseModel):
    """Watchlist service response"""
    agent_name: str = "watchlist"
    status: str
    data: Dict[str, Any]
    processing_time: int
    error: Optional[str] = None
    version: str = "1.0.0"

class WatchlistProcessor:
    """Main watchlist screening processor"""
    
    def __init__(self):
        """Initialize watchlist processor with databases"""
        # Initialize watchlist databases
        self.watchlists = {}
        self.load_watchlist_databases()
        
        # Matching thresholds
        self.fuzzy_threshold = 85  # Minimum fuzzy match score
        self.partial_threshold = 70  # Minimum partial match score
        
        # Risk level mappings
        self.risk_levels = {
            'sanctions': 'critical',
            'pep': 'high',
            'adverse_media': 'medium',
            'internal_blacklist': 'high',
            'regulatory_enforcement': 'high'
        }
        
        logger.info("Watchlist Processor initialized")

    def load_watchlist_databases(self):
        """Load watchlist databases from various sources"""
        try:
            # In a production environment, these would be loaded from actual databases
            # For this implementation, we'll create sample data
            
            # OFAC Sanctions List (sample data)
            self.watchlists['ofac_sanctions'] = pd.DataFrame([
                {
                    'name': 'JOHN DOE SMITH',
                    'aliases': 'JOHN D SMITH;J D SMITH',
                    'date_of_birth': '1970-01-15',
                    'nationality': 'US',
                    'list_type': 'sanctions',
                    'program': 'OFAC SDN',
                    'added_date': '2020-01-01'
                },
                {
                    'name': 'MARIA GONZALEZ RODRIGUEZ',
                    'aliases': 'MARIA G RODRIGUEZ;M GONZALEZ',
                    'date_of_birth': '1965-03-22',
                    'nationality': 'MX',
                    'list_type': 'sanctions',
                    'program': 'OFAC SDN',
                    'added_date': '2019-05-15'
                }
            ])
            
            # EU Sanctions List (sample data)
            self.watchlists['eu_sanctions'] = pd.DataFrame([
                {
                    'name': 'VLADIMIR PETROV',
                    'aliases': 'V PETROV;VLADIMIR P',
                    'date_of_birth': '1960-12-05',
                    'nationality': 'RU',
                    'list_type': 'sanctions',
                    'program': 'EU Sanctions',
                    'added_date': '2021-02-01'
                }
            ])
            
            # PEP Database (sample data)
            self.watchlists['pep_database'] = pd.DataFrame([
                {
                    'name': 'ROBERT JOHNSON',
                    'aliases': 'BOB JOHNSON;R JOHNSON',
                    'date_of_birth': '1955-07-10',
                    'nationality': 'US',
                    'list_type': 'pep',
                    'position': 'Former Government Official',
                    'country': 'US',
                    'added_date': '2018-01-01'
                },
                {
                    'name': 'ANGELA MUELLER',
                    'aliases': 'A MUELLER;ANGELA M',
                    'date_of_birth': '1962-11-30',
                    'nationality': 'DE',
                    'list_type': 'pep',
                    'position': 'Corporate Executive',
                    'country': 'DE',
                    'added_date': '2019-06-01'
                }
            ])
            
            # Adverse Media Database (sample data)
            self.watchlists['adverse_media'] = pd.DataFrame([
                {
                    'name': 'MICHAEL BROWN',
                    'aliases': 'MIKE BROWN;M BROWN',
                    'date_of_birth': '1975-04-18',
                    'nationality': 'GB',
                    'list_type': 'adverse_media',
                    'category': 'Financial Crime',
                    'source': 'News Media',
                    'added_date': '2022-03-15'
                }
            ])
            
            logger.info(f"Loaded {len(self.watchlists)} watchlist databases")
            
        except Exception as e:
            logger.error(f"Failed to load watchlist databases: {str(e)}")
            self.watchlists = {}

    def normalize_name(self, name: str) -> str:
        """
        Normalize name for better matching
        
        Args:
            name: Input name string
            
        Returns:
            Normalized name string
        """
        if not name:
            return ""
        
        # Convert to uppercase
        normalized = name.upper()
        
        # Remove special characters and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common prefixes/suffixes
        prefixes = ['MR', 'MRS', 'MS', 'DR', 'PROF']
        suffixes = ['JR', 'SR', 'III', 'IV']
        
        words = normalized.split()
        words = [w for w in words if w not in prefixes and w not in suffixes]
        
        return ' '.join(words)

    def parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string to date object
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Parsed date object or None
        """
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y',
            '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None

    def calculate_name_similarity(self, name1: str, name2: str) -> Tuple[float, str]:
        """
        Calculate similarity between two names
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Tuple of (similarity_score, match_type)
        """
        if not name1 or not name2:
            return 0.0, "none"
        
        # Normalize names
        norm_name1 = self.normalize_name(name1)
        norm_name2 = self.normalize_name(name2)
        
        # Exact match
        if norm_name1 == norm_name2:
            return 100.0, "exact"
        
        # Fuzzy matching
        fuzzy_score = fuzz.ratio(norm_name1, norm_name2)
        
        if fuzzy_score >= self.fuzzy_threshold:
            return float(fuzzy_score), "fuzzy"
        elif fuzzy_score >= self.partial_threshold:
            return float(fuzzy_score), "partial"
        
        # Token-based matching for names with different word orders
        token_score = fuzz.token_sort_ratio(norm_name1, norm_name2)
        
        if token_score >= self.fuzzy_threshold:
            return float(token_score), "fuzzy"
        elif token_score >= self.partial_threshold:
            return float(token_score), "partial"
        
        return max(float(fuzzy_score), float(token_score)), "weak"

    def check_date_match(self, date1: str, date2: str) -> Tuple[bool, float]:
        """
        Check if two dates match
        
        Args:
            date1: First date string
            date2: Second date string
            
        Returns:
            Tuple of (is_match, confidence)
        """
        parsed_date1 = self.parse_date(date1)
        parsed_date2 = self.parse_date(date2)
        
        if not parsed_date1 or not parsed_date2:
            return False, 0.0
        
        if parsed_date1 == parsed_date2:
            return True, 100.0
        
        # Check if years match (common for approximate dates)
        if parsed_date1.year == parsed_date2.year:
            return True, 70.0
        
        return False, 0.0

    def screen_against_watchlist(
        self, 
        identity_data: IdentityData, 
        watchlist_name: str, 
        watchlist_df: pd.DataFrame
    ) -> List[WatchlistMatch]:
        """
        Screen identity against a specific watchlist
        
        Args:
            identity_data: Identity information to screen
            watchlist_name: Name of the watchlist
            watchlist_df: Watchlist dataframe
            
        Returns:
            List of matches found
        """
        matches = []
        
        try:
            # Get the name to search for
            search_name = identity_data.name or f"{identity_data.first_name or ''} {identity_data.last_name or ''}".strip()
            
            if not search_name:
                return matches
            
            # Search through watchlist entries
            for _, entry in watchlist_df.iterrows():
                entry_matches = []
                
                # Check primary name
                similarity, match_type = self.calculate_name_similarity(search_name, entry['name'])
                
                if similarity >= self.partial_threshold:
                    entry_matches.append({
                        'matched_field': 'primary_name',
                        'similarity': similarity,
                        'match_type': match_type,
                        'matched_value': entry['name']
                    })
                
                # Check aliases if available
                if 'aliases' in entry and pd.notna(entry['aliases']):
                    aliases = entry['aliases'].split(';')
                    for alias in aliases:
                        alias_similarity, alias_match_type = self.calculate_name_similarity(search_name, alias.strip())
                        
                        if alias_similarity >= self.partial_threshold:
                            entry_matches.append({
                                'matched_field': 'alias',
                                'similarity': alias_similarity,
                                'match_type': alias_match_type,
                                'matched_value': alias.strip()
                            })
                
                # If we have name matches, create a match record
                if entry_matches:
                    # Get the best match
                    best_match = max(entry_matches, key=lambda x: x['similarity'])
                    
                    # Additional verification checks
                    additional_info = {}
                    confidence_factors = [best_match['similarity']]
                    
                    # Date of birth verification
                    if identity_data.date_of_birth and 'date_of_birth' in entry and pd.notna(entry['date_of_birth']):
                        dob_match, dob_confidence = self.check_date_match(
                            identity_data.date_of_birth, 
                            str(entry['date_of_birth'])
                        )
                        additional_info['date_of_birth_match'] = dob_match
                        additional_info['date_of_birth_confidence'] = dob_confidence
                        
                        if dob_match:
                            confidence_factors.append(dob_confidence)
                    
                    # Nationality verification
                    if identity_data.nationality and 'nationality' in entry and pd.notna(entry['nationality']):
                        nationality_match = identity_data.nationality.upper() == str(entry['nationality']).upper()
                        additional_info['nationality_match'] = nationality_match
                        
                        if nationality_match:
                            confidence_factors.append(90.0)
                    
                    # Calculate overall confidence
                    overall_confidence = np.mean(confidence_factors)
                    
                    # Determine risk level
                    list_type = entry.get('list_type', 'unknown')
                    risk_level = self.risk_levels.get(list_type, 'medium')
                    
                    # Create match record
                    match = WatchlistMatch(
                        list_name=watchlist_name,
                        match_type=best_match['match_type'],
                        matched_name=best_match['matched_value'],
                        original_name=search_name,
                        confidence_score=overall_confidence,
                        match_details={
                            'all_matches': entry_matches,
                            'best_similarity': best_match['similarity'],
                            'entry_data': entry.to_dict()
                        },
                        risk_level=risk_level,
                        additional_info=additional_info
                    )
                    
                    matches.append(match)
            
            logger.info(f"Found {len(matches)} matches in {watchlist_name}")
            return matches
            
        except Exception as e:
            logger.error(f"Error screening against {watchlist_name}: {str(e)}")
            return matches

    def screen_identity(self, identity_data: IdentityData, customer_info: CustomerInfo) -> ScreeningResult:
        """
        Screen identity against all watchlists
        
        Args:
            identity_data: Identity information to screen
            customer_info: Customer information
            
        Returns:
            Complete screening result
        """
        start_time = datetime.now()
        all_matches = []
        lists_checked = []
        errors = []
        warnings = []
        
        try:
            # Screen against each watchlist
            for watchlist_name, watchlist_df in self.watchlists.items():
                try:
                    matches = self.screen_against_watchlist(identity_data, watchlist_name, watchlist_df)
                    all_matches.extend(matches)
                    lists_checked.append(watchlist_name)
                    
                except Exception as e:
                    error_msg = f"Error screening against {watchlist_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Determine if flagged
            flagged = len(all_matches) > 0
            
            # Calculate highest risk level
            risk_levels_order = ['low', 'medium', 'high', 'critical']
            highest_risk_level = 'low'
            
            if all_matches:
                risk_levels = [match.risk_level for match in all_matches]
                for level in reversed(risk_levels_order):
                    if level in risk_levels:
                        highest_risk_level = level
                        break
            
            # Calculate overall confidence
            if all_matches:
                overall_confidence = max(match.confidence_score for match in all_matches)
            else:
                overall_confidence = 0.0
            
            # Add warnings for high-risk matches
            critical_matches = [m for m in all_matches if m.risk_level == 'critical']
            if critical_matches:
                warnings.append(f"Found {len(critical_matches)} critical risk matches")
            
            high_risk_matches = [m for m in all_matches if m.risk_level == 'high']
            if high_risk_matches:
                warnings.append(f"Found {len(high_risk_matches)} high risk matches")
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ScreeningResult(
                flagged=flagged,
                total_matches=len(all_matches),
                matches=all_matches,
                highest_risk_level=highest_risk_level,
                overall_confidence=overall_confidence,
                lists_checked=lists_checked,
                processing_time_ms=processing_time,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Watchlist screening failed: {str(e)}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ScreeningResult(
                flagged=False,
                total_matches=0,
                matches=[],
                highest_risk_level='low',
                overall_confidence=0.0,
                lists_checked=lists_checked,
                processing_time_ms=processing_time,
                errors=[str(e)],
                warnings=warnings
            )

    def extract_identity_from_ocr(self, ocr_data: Dict[str, Any]) -> IdentityData:
        """
        Extract identity data from OCR results
        
        Args:
            ocr_data: OCR processing results
            
        Returns:
            Extracted identity data
        """
        identity_data = IdentityData()
        
        try:
            # Handle different OCR result structures
            if 'data' in ocr_data:
                ocr_results = ocr_data['data']
            else:
                ocr_results = ocr_data
            
            # Extract from results array
            if 'results' in ocr_results and isinstance(ocr_results['results'], list):
                for result in ocr_results['results']:
                    if 'extracted_data' in result:
                        extracted = result['extracted_data']
                        
                        identity_data.name = extracted.get('name')
                        identity_data.first_name = extracted.get('first_name')
                        identity_data.last_name = extracted.get('last_name')
                        identity_data.date_of_birth = extracted.get('date_of_birth')
                        identity_data.nationality = extracted.get('nationality')
                        identity_data.address = extracted.get('address')
                        
                        # Use first non-empty result
                        if identity_data.name or identity_data.first_name:
                            break
            
            # Direct extraction if structure is different
            elif 'extracted_data' in ocr_results:
                extracted = ocr_results['extracted_data']
                identity_data.name = extracted.get('name')
                identity_data.first_name = extracted.get('first_name')
                identity_data.last_name = extracted.get('last_name')
                identity_data.date_of_birth = extracted.get('date_of_birth')
                identity_data.nationality = extracted.get('nationality')
                identity_data.address = extracted.get('address')
            
            logger.info(f"Extracted identity data: {identity_data.dict()}")
            return identity_data
            
        except Exception as e:
            logger.error(f"Failed to extract identity from OCR data: {str(e)}")
            return identity_data

# Initialize watchlist processor
watchlist_processor = WatchlistProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "watchlist-agent",
        "version": "1.0.0",
        "watchlists_loaded": len(watchlist_processor.watchlists),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process", response_model=WatchlistResponse)
async def process_watchlist_request(request: WatchlistRequest):
    """
    Process watchlist screening request
    
    Args:
        request: Watchlist screening request
        
    Returns:
        Watchlist screening response
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing watchlist screening request: {request.request_id}")
        
        # Extract identity data from OCR results or use provided data
        if request.identity_data:
            identity_data = watchlist_processor.extract_identity_from_ocr(request.identity_data)
        else:
            # Create identity data from customer info if OCR data not available
            identity_data = IdentityData()
            
            # Try to extract name from email or other sources
            if request.customer_info.email:
                email_parts = request.customer_info.email.split('@')[0].split('.')
                if len(email_parts) >= 2:
                    identity_data.first_name = email_parts[0].title()
                    identity_data.last_name = email_parts[1].title()
                    identity_data.name = f"{identity_data.first_name} {identity_data.last_name}"
        
        # Perform watchlist screening
        screening_result = watchlist_processor.screen_identity(identity_data, request.customer_info)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Determine status
        status = "success"
        if screening_result.errors:
            status = "error"
        elif screening_result.warnings or screening_result.flagged:
            status = "warning"
        
        response_data = screening_result.dict()
        
        return WatchlistResponse(
            status=status,
            data=response_data,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Watchlist screening failed: {str(e)}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return WatchlistResponse(
            status="error",
            data={"error": str(e)},
            processing_time=processing_time,
            error=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Watchlist Screening Agent",
        "description": "AML watchlist screening for KYC compliance",
        "version": "1.0.0",
        "watchlists_available": list(watchlist_processor.watchlists.keys()),
        "endpoints": {
            "health": "/health",
            "process": "/process"
        }
    }

@app.get("/watchlists")
async def get_watchlists():
    """Get information about available watchlists"""
    watchlist_info = {}
    
    for name, df in watchlist_processor.watchlists.items():
        watchlist_info[name] = {
            "entries": len(df),
            "columns": list(df.columns),
            "last_updated": "2024-01-01"  # Would be actual update date in production
        }
    
    return {
        "watchlists": watchlist_info,
        "total_entries": sum(len(df) for df in watchlist_processor.watchlists.values())
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8003))
    
    # Run the service
    uvicorn.run(
        "watchlist_service:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
