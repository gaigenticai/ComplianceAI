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
import json
import requests
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
        """Load watchlist databases from real external sources and APIs"""
        try:
            # Initialize empty watchlists dictionary
            self.watchlists = {}
            self.last_updated = {}
            
            # Load OFAC Sanctions List from official API
            ofac_data = self._load_ofac_sanctions()
            if ofac_data is not None and not ofac_data.empty:
                self.watchlists['ofac_sanctions'] = ofac_data
                self.last_updated['ofac_sanctions'] = datetime.now()
                logger.info(f"Loaded {len(ofac_data)} OFAC sanctions entries")
            
            # Load EU Sanctions List from official API
            eu_data = self._load_eu_sanctions()
            if eu_data is not None and not eu_data.empty:
                self.watchlists['eu_sanctions'] = eu_data
                self.last_updated['eu_sanctions'] = datetime.now()
                logger.info(f"Loaded {len(eu_data)} EU sanctions entries")
            
            # Load UN Sanctions List from official API
            un_data = self._load_un_sanctions()
            if un_data is not None and not un_data.empty:
                self.watchlists['un_sanctions'] = un_data
                self.last_updated['un_sanctions'] = datetime.now()
                logger.info(f"Loaded {len(un_data)} UN sanctions entries")
            
            # Load PEP Database from commercial provider
            pep_data = self._load_pep_database()
            if pep_data is not None and not pep_data.empty:
                self.watchlists['pep_database'] = pep_data
                self.last_updated['pep_database'] = datetime.now()
                logger.info(f"Loaded {len(pep_data)} PEP database entries")
            
            # Load World-Check data if available
            worldcheck_data = self._load_worldcheck_data()
            if worldcheck_data is not None and not worldcheck_data.empty:
                self.watchlists['worldcheck'] = worldcheck_data
                self.last_updated['worldcheck'] = datetime.now()
                logger.info(f"Loaded {len(worldcheck_data)} World-Check entries")
            
            # Load Dow Jones Risk & Compliance data
            dowjones_data = self._load_dowjones_data()
            if dowjones_data is not None and not dowjones_data.empty:
                self.watchlists['dowjones'] = dowjones_data
                self.last_updated['dowjones'] = datetime.now()
                logger.info(f"Loaded {len(dowjones_data)} Dow Jones entries")
            
            total_entries = sum(len(df) for df in self.watchlists.values())
            logger.info(f"Successfully loaded {len(self.watchlists)} watchlist databases with {total_entries} total entries")
            
            # Schedule periodic updates
            self._schedule_database_updates()
            
        except Exception as e:
            logger.error(f"Failed to load watchlist databases: {str(e)}")
            # Initialize with empty dataframes to prevent crashes
            self.watchlists = {}
            self.last_updated = {}
    
    def _load_ofac_sanctions(self) -> Optional[pd.DataFrame]:
        """Load OFAC Sanctions List from official Treasury API"""
        try:
            ofac_api_key = os.getenv('OFAC_API_KEY')
            ofac_base_url = os.getenv('OFAC_BASE_URL', 'https://api.treasury.gov/ofac')
            
            if not ofac_api_key:
                logger.warning("OFAC API key not configured, skipping OFAC sanctions load")
                return None
            
            headers = {
                'Authorization': f'Bearer {ofac_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get SDN (Specially Designated Nationals) list
            response = requests.get(
                f'{ofac_base_url}/sdn/list',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse OFAC data into standardized format
                records = []
                for entry in data.get('entries', []):
                    # Extract names and aliases
                    primary_name = entry.get('name', '').upper()
                    aliases = []
                    
                    for aka in entry.get('akas', []):
                        aliases.append(aka.get('name', '').upper())
                    
                    # Extract other details
                    record = {
                        'name': primary_name,
                        'aliases': ';'.join(aliases) if aliases else '',
                        'date_of_birth': entry.get('dateOfBirth'),
                        'nationality': entry.get('nationality'),
                        'list_type': 'sanctions',
                        'program': entry.get('program', 'OFAC SDN'),
                        'added_date': entry.get('dateAdded'),
                        'entity_id': entry.get('id'),
                        'entity_type': entry.get('type', 'individual'),
                        'addresses': json.dumps(entry.get('addresses', [])),
                        'identifications': json.dumps(entry.get('identifications', []))
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                logger.info(f"Successfully loaded {len(df)} OFAC sanctions entries")
                return df
            else:
                logger.error(f"OFAC API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load OFAC sanctions: {str(e)}")
            return None
    
    def _load_eu_sanctions(self) -> Optional[pd.DataFrame]:
        """Load EU Sanctions List from official EU API"""
        try:
            eu_api_key = os.getenv('EU_SANCTIONS_API_KEY')
            eu_base_url = os.getenv('EU_SANCTIONS_BASE_URL', 'https://webgate.ec.europa.eu/fsd/fsf')
            
            if not eu_api_key:
                logger.warning("EU Sanctions API key not configured, skipping EU sanctions load")
                return None
            
            headers = {
                'Authorization': f'Bearer {eu_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get EU consolidated sanctions list
            response = requests.get(
                f'{eu_base_url}/api/v1/export/consolidated',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                records = []
                for entry in data.get('entities', []):
                    # Extract entity information
                    primary_name = entry.get('name', '').upper()
                    aliases = []
                    
                    for alias in entry.get('aliases', []):
                        aliases.append(alias.get('name', '').upper())
                    
                    record = {
                        'name': primary_name,
                        'aliases': ';'.join(aliases) if aliases else '',
                        'date_of_birth': entry.get('birthDate'),
                        'nationality': entry.get('nationality'),
                        'list_type': 'sanctions',
                        'program': 'EU Sanctions',
                        'added_date': entry.get('listingDate'),
                        'entity_id': entry.get('euReferenceNumber'),
                        'entity_type': entry.get('subjectType', 'individual'),
                        'regulation': entry.get('regulation'),
                        'reason': entry.get('reasonForListing')
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                logger.info(f"Successfully loaded {len(df)} EU sanctions entries")
                return df
            else:
                logger.error(f"EU Sanctions API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load EU sanctions: {str(e)}")
            return None
    
    def _load_un_sanctions(self) -> Optional[pd.DataFrame]:
        """Load UN Sanctions List from official UN API"""
        try:
            un_api_key = os.getenv('UN_SANCTIONS_API_KEY')
            un_base_url = os.getenv('UN_SANCTIONS_BASE_URL', 'https://scsanctions.un.org/api')
            
            if not un_api_key:
                logger.warning("UN Sanctions API key not configured, skipping UN sanctions load")
                return None
            
            headers = {
                'Authorization': f'Bearer {un_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get UN consolidated sanctions list
            response = requests.get(
                f'{un_base_url}/v1/consolidated',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                records = []
                for entry in data.get('results', []):
                    # Extract individual or entity information
                    primary_name = entry.get('first_name', '') + ' ' + entry.get('second_name', '')
                    if not primary_name.strip():
                        primary_name = entry.get('name', '')
                    primary_name = primary_name.upper().strip()
                    
                    aliases = []
                    for alias in entry.get('aliases', []):
                        alias_name = alias.get('name', '').upper()
                        if alias_name and alias_name != primary_name:
                            aliases.append(alias_name)
                    
                    record = {
                        'name': primary_name,
                        'aliases': ';'.join(aliases) if aliases else '',
                        'date_of_birth': entry.get('date_of_birth'),
                        'nationality': entry.get('nationality'),
                        'list_type': 'sanctions',
                        'program': 'UN Sanctions',
                        'added_date': entry.get('listed_on'),
                        'entity_id': entry.get('dataid'),
                        'entity_type': entry.get('entity_type', 'individual'),
                        'committee': entry.get('committee'),
                        'un_list_type': entry.get('un_list_type')
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                logger.info(f"Successfully loaded {len(df)} UN sanctions entries")
                return df
            else:
                logger.error(f"UN Sanctions API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load UN sanctions: {str(e)}")
            return None
    
    def _load_pep_database(self) -> Optional[pd.DataFrame]:
        """Load PEP Database from commercial provider"""
        try:
            pep_api_key = os.getenv('PEP_DATABASE_API_KEY')
            pep_base_url = os.getenv('PEP_DATABASE_BASE_URL', 'https://api.pepdatabase.com')
            
            if not pep_api_key:
                logger.warning("PEP Database API key not configured, skipping PEP database load")
                return None
            
            headers = {
                'Authorization': f'Bearer {pep_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get PEP database entries
            response = requests.get(
                f'{pep_base_url}/v1/pep/list',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                records = []
                for entry in data.get('peps', []):
                    primary_name = entry.get('name', '').upper()
                    aliases = []
                    
                    for alias in entry.get('aliases', []):
                        aliases.append(alias.upper())
                    
                    record = {
                        'name': primary_name,
                        'aliases': ';'.join(aliases) if aliases else '',
                        'date_of_birth': entry.get('dateOfBirth'),
                        'nationality': entry.get('nationality'),
                        'list_type': 'pep',
                        'position': entry.get('position'),
                        'country': entry.get('country'),
                        'added_date': entry.get('addedDate'),
                        'entity_id': entry.get('id'),
                        'status': entry.get('status', 'active'),
                        'risk_level': entry.get('riskLevel', 'medium'),
                        'source': entry.get('source')
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                logger.info(f"Successfully loaded {len(df)} PEP database entries")
                return df
            else:
                logger.error(f"PEP Database API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load PEP database: {str(e)}")
            return None
    
    def _load_worldcheck_data(self) -> Optional[pd.DataFrame]:
        """Load World-Check data from Refinitiv"""
        try:
            worldcheck_api_key = os.getenv('WORLD_CHECK_API_KEY')
            worldcheck_base_url = os.getenv('WORLD_CHECK_BASE_URL', 'https://api.refinitiv.com/world-check')
            worldcheck_client_id = os.getenv('WORLD_CHECK_CLIENT_ID')
            
            if not worldcheck_api_key or not worldcheck_client_id:
                logger.warning("World-Check API credentials not configured, skipping World-Check load")
                return None
            
            # Authenticate with World-Check API
            auth_response = requests.post(
                f'{worldcheck_base_url}/v1/authenticate',
                json={
                    'clientId': worldcheck_client_id,
                    'apiKey': worldcheck_api_key
                },
                timeout=30
            )
            
            if auth_response.status_code != 200:
                logger.error(f"World-Check authentication failed: {auth_response.status_code}")
                return None
            
            access_token = auth_response.json().get('access_token')
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Get World-Check screening data
            response = requests.get(
                f'{worldcheck_base_url}/v1/reference-data/profiles',
                headers=headers,
                params={'limit': 10000},  # Adjust based on needs
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                records = []
                for entry in data.get('profiles', []):
                    primary_name = entry.get('primaryName', '').upper()
                    aliases = []
                    
                    for alias in entry.get('aliases', []):
                        aliases.append(alias.get('name', '').upper())
                    
                    record = {
                        'name': primary_name,
                        'aliases': ';'.join(aliases) if aliases else '',
                        'date_of_birth': entry.get('dateOfBirth'),
                        'nationality': entry.get('nationality'),
                        'list_type': entry.get('category', 'worldcheck'),
                        'program': 'World-Check',
                        'added_date': entry.get('provisioningDate'),
                        'entity_id': entry.get('profileId'),
                        'entity_type': entry.get('entityType', 'individual'),
                        'categories': json.dumps(entry.get('categories', [])),
                        'sources': json.dumps(entry.get('sources', []))
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                logger.info(f"Successfully loaded {len(df)} World-Check entries")
                return df
            else:
                logger.error(f"World-Check API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load World-Check data: {str(e)}")
            return None
    
    def _load_dowjones_data(self) -> Optional[pd.DataFrame]:
        """Load Dow Jones Risk & Compliance data"""
        try:
            dowjones_api_key = os.getenv('DOW_JONES_API_KEY')
            dowjones_base_url = os.getenv('DOW_JONES_BASE_URL', 'https://api.dowjones.com/risk')
            dowjones_client_id = os.getenv('DOW_JONES_CLIENT_ID')
            
            if not dowjones_api_key or not dowjones_client_id:
                logger.warning("Dow Jones API credentials not configured, skipping Dow Jones load")
                return None
            
            headers = {
                'Authorization': f'Bearer {dowjones_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Client-ID': dowjones_client_id
            }
            
            # Get Dow Jones risk data
            response = requests.get(
                f'{dowjones_base_url}/v1/entities',
                headers=headers,
                params={'limit': 10000},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                records = []
                for entry in data.get('entities', []):
                    primary_name = entry.get('name', '').upper()
                    aliases = []
                    
                    for alias in entry.get('aliases', []):
                        aliases.append(alias.upper())
                    
                    record = {
                        'name': primary_name,
                        'aliases': ';'.join(aliases) if aliases else '',
                        'date_of_birth': entry.get('birthDate'),
                        'nationality': entry.get('nationality'),
                        'list_type': entry.get('riskType', 'dowjones'),
                        'program': 'Dow Jones Risk & Compliance',
                        'added_date': entry.get('addedDate'),
                        'entity_id': entry.get('entityId'),
                        'entity_type': entry.get('entityType', 'individual'),
                        'risk_score': entry.get('riskScore'),
                        'categories': json.dumps(entry.get('categories', []))
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                logger.info(f"Successfully loaded {len(df)} Dow Jones entries")
                return df
            else:
                logger.error(f"Dow Jones API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load Dow Jones data: {str(e)}")
            return None
    
    def _schedule_database_updates(self):
        """Schedule periodic updates of watchlist databases"""
        try:
            # Schedule updates based on environment variables
            ofac_update_hours = int(os.getenv('OFAC_UPDATE_FREQUENCY_HOURS', '24'))
            eu_update_hours = int(os.getenv('EU_SANCTIONS_UPDATE_FREQUENCY_HOURS', '24'))
            un_update_hours = int(os.getenv('UN_SANCTIONS_UPDATE_FREQUENCY_HOURS', '24'))
            pep_update_hours = int(os.getenv('PEP_DATABASE_UPDATE_FREQUENCY_HOURS', '168'))  # Weekly
            
            # In a production environment, you would use a proper scheduler like Celery
            # For now, we'll just log the intended schedule
            logger.info(f"Scheduled database updates: OFAC every {ofac_update_hours}h, "
                       f"EU every {eu_update_hours}h, UN every {un_update_hours}h, "
                       f"PEP every {pep_update_hours}h")
            
        except Exception as e:
            logger.error(f"Failed to schedule database updates: {str(e)}")

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
            "last_updated": watchlist_processor.last_updated.get(name, datetime.now()).isoformat() if hasattr(watchlist_processor, 'last_updated') else datetime.now().isoformat()
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
