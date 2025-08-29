"""
Data Integration Agent Service for KYC Automation Platform

This service handles integration with external data sources for enhanced KYC verification.
It connects to various APIs and databases to enrich customer data and perform additional
verification checks including credit bureau data, social media verification, and
public records searches.

Features:
- Credit bureau integration (mock implementation)
- Social media profile verification
- Public records and business registry searches
- Address verification services
- Phone number validation and carrier lookup
- Email verification and domain analysis
- Risk scoring based on external data sources
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import phonenumbers
from phonenumbers import carrier, geocoder
from email_validator import validate_email, EmailNotValidError
import requests
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
import uvicorn
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Data Integration Agent Service",
    description="External data integration for enhanced KYC verification",
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

class DataIntegrationRequest(BaseModel):
    """Data integration processing request structure"""
    request_id: str
    timestamp: datetime
    customer_info: CustomerInfo
    documents: List[Dict[str, Any]] = []
    processing_config: Dict[str, Any] = {}
    previous_results: Dict[str, Any] = {}

class EmailVerification(BaseModel):
    """Email verification results"""
    is_valid: bool
    is_deliverable: bool
    domain_exists: bool
    is_disposable: bool
    domain_reputation: str  # good, neutral, poor
    mx_records: List[str] = []
    confidence_score: float = Field(ge=0, le=100)

class PhoneVerification(BaseModel):
    """Phone number verification results"""
    is_valid: bool
    country_code: str
    national_number: str
    carrier: Optional[str] = None
    line_type: Optional[str] = None  # mobile, fixed_line, voip, etc.
    location: Optional[str] = None
    is_possible: bool
    confidence_score: float = Field(ge=0, le=100)

class CreditBureauData(BaseModel):
    """Credit bureau data (mock implementation)"""
    credit_score: Optional[int] = None
    credit_history_length: Optional[int] = None  # months
    active_accounts: Optional[int] = None
    delinquent_accounts: Optional[int] = None
    bankruptcy_records: Optional[int] = None
    risk_category: str = "unknown"  # low, medium, high, unknown
    last_updated: Optional[datetime] = None

class SocialMediaProfile(BaseModel):
    """Social media profile information"""
    platform: str
    profile_exists: bool
    profile_age_days: Optional[int] = None
    follower_count: Optional[int] = None
    activity_level: str = "unknown"  # low, medium, high, unknown
    verification_status: str = "unknown"  # verified, unverified, unknown
    risk_indicators: List[str] = []

class AddressVerification(BaseModel):
    """Address verification results"""
    is_valid: bool
    is_deliverable: bool
    address_type: str = "unknown"  # residential, commercial, po_box, unknown
    geocoded_location: Optional[Dict[str, float]] = None  # lat, lng
    confidence_score: float = Field(ge=0, le=100)

class PublicRecordsData(BaseModel):
    """Public records search results"""
    criminal_records: List[Dict[str, Any]] = []
    civil_records: List[Dict[str, Any]] = []
    business_registrations: List[Dict[str, Any]] = []
    property_records: List[Dict[str, Any]] = []
    professional_licenses: List[Dict[str, Any]] = []
    risk_score: float = Field(ge=0, le=100)

class DataIntegrationResult(BaseModel):
    """Data integration processing result"""
    email_verification: Optional[EmailVerification] = None
    phone_verification: Optional[PhoneVerification] = None
    credit_bureau_data: Optional[CreditBureauData] = None
    social_media_profiles: List[SocialMediaProfile] = []
    address_verification: Optional[AddressVerification] = None
    public_records: Optional[PublicRecordsData] = None
    overall_risk_score: float = Field(ge=0, le=100)
    data_completeness_score: float = Field(ge=0, le=100)
    processing_time_ms: int
    errors: List[str] = []
    warnings: List[str] = []

class DataIntegrationResponse(BaseModel):
    """Data integration service response"""
    agent_name: str = "data_integration"
    status: str
    data: Dict[str, Any]
    processing_time: int
    error: Optional[str] = None
    version: str = "1.0.0"

class DataIntegrationProcessor:
    """Main data integration processor"""
    
    def __init__(self):
        """Initialize data integration processor"""
        # API configurations (would be loaded from environment in production)
        self.api_configs = {
            'credit_bureau': {
                'enabled': True,
                'mock_mode': True,  # Use mock data for demo
                'timeout': 10
            },
            'social_media': {
                'enabled': True,
                'mock_mode': True,
                'timeout': 15
            },
            'address_verification': {
                'enabled': True,
                'mock_mode': True,
                'timeout': 10
            },
            'public_records': {
                'enabled': True,
                'mock_mode': True,
                'timeout': 20
            }
        }
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        logger.info("Data Integration Processor initialized")

    async def verify_email(self, email: str) -> EmailVerification:
        """
        Verify email address validity and deliverability
        
        Args:
            email: Email address to verify
            
        Returns:
            EmailVerification results
        """
        try:
            if not email:
                return EmailVerification(
                    is_valid=False,
                    is_deliverable=False,
                    domain_exists=False,
                    is_disposable=False,
                    domain_reputation="poor",
                    confidence_score=0.0
                )
            
            # Basic email validation
            try:
                validated_email = validate_email(email)
                email_address = validated_email.email
                domain = validated_email.domain
                is_valid = True
            except EmailNotValidError:
                return EmailVerification(
                    is_valid=False,
                    is_deliverable=False,
                    domain_exists=False,
                    is_disposable=False,
                    domain_reputation="poor",
                    confidence_score=0.0
                )
            
            # Check for disposable email domains
            disposable_domains = [
                '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
                'mailinator.com', 'throwaway.email', 'temp-mail.org'
            ]
            is_disposable = domain.lower() in disposable_domains
            
            # Domain reputation check (simplified)
            trusted_domains = [
                'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
                'icloud.com', 'protonmail.com', 'aol.com'
            ]
            
            if domain.lower() in trusted_domains:
                domain_reputation = "good"
            elif is_disposable:
                domain_reputation = "poor"
            else:
                domain_reputation = "neutral"
            
            # Mock MX record lookup (in production, would use DNS lookup)
            mx_records = [f"mx1.{domain}", f"mx2.{domain}"]
            domain_exists = True
            is_deliverable = not is_disposable
            
            # Calculate confidence score
            confidence_score = 90.0
            if is_disposable:
                confidence_score = 20.0
            elif domain_reputation == "neutral":
                confidence_score = 70.0
            
            return EmailVerification(
                is_valid=is_valid,
                is_deliverable=is_deliverable,
                domain_exists=domain_exists,
                is_disposable=is_disposable,
                domain_reputation=domain_reputation,
                mx_records=mx_records,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            return EmailVerification(
                is_valid=False,
                is_deliverable=False,
                domain_exists=False,
                is_disposable=False,
                domain_reputation="unknown",
                confidence_score=0.0
            )

    async def verify_phone(self, phone: str) -> PhoneVerification:
        """
        Verify phone number validity and get carrier information
        
        Args:
            phone: Phone number to verify
            
        Returns:
            PhoneVerification results
        """
        try:
            if not phone:
                return PhoneVerification(
                    is_valid=False,
                    country_code="",
                    national_number="",
                    is_possible=False,
                    confidence_score=0.0
                )
            
            # Parse phone number
            try:
                parsed_number = phonenumbers.parse(phone, None)
            except phonenumbers.NumberParseException:
                return PhoneVerification(
                    is_valid=False,
                    country_code="",
                    national_number="",
                    is_possible=False,
                    confidence_score=0.0
                )
            
            # Validate phone number
            is_valid = phonenumbers.is_valid_number(parsed_number)
            is_possible = phonenumbers.is_possible_number(parsed_number)
            
            # Get country code and national number
            country_code = f"+{parsed_number.country_code}"
            national_number = str(parsed_number.national_number)
            
            # Get carrier information
            carrier_name = carrier.name_for_number(parsed_number, "en")
            
            # Get location information
            location = geocoder.description_for_number(parsed_number, "en")
            
            # Determine line type (simplified)
            number_type = phonenumbers.number_type(parsed_number)
            line_type_map = {
                phonenumbers.PhoneNumberType.MOBILE: "mobile",
                phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
                phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
                phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
                phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
                phonenumbers.PhoneNumberType.VOIP: "voip",
                phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal",
                phonenumbers.PhoneNumberType.PAGER: "pager",
                phonenumbers.PhoneNumberType.UAN: "uan",
                phonenumbers.PhoneNumberType.VOICEMAIL: "voicemail",
                phonenumbers.PhoneNumberType.UNKNOWN: "unknown"
            }
            line_type = line_type_map.get(number_type, "unknown")
            
            # Calculate confidence score
            confidence_score = 50.0
            if is_valid:
                confidence_score = 90.0
            elif is_possible:
                confidence_score = 70.0
            
            return PhoneVerification(
                is_valid=is_valid,
                country_code=country_code,
                national_number=national_number,
                carrier=carrier_name if carrier_name else None,
                line_type=line_type,
                location=location if location else None,
                is_possible=is_possible,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Phone verification failed: {str(e)}")
            return PhoneVerification(
                is_valid=False,
                country_code="",
                national_number="",
                is_possible=False,
                confidence_score=0.0
            )

    async def get_credit_bureau_data(self, customer_info: CustomerInfo) -> CreditBureauData:
        """
        Get credit bureau data (mock implementation)
        
        Args:
            customer_info: Customer information
            
        Returns:
            CreditBureauData results
        """
        try:
            if not self.api_configs['credit_bureau']['enabled']:
                return CreditBureauData()
            
            # Mock credit bureau data (in production, would call actual credit bureau APIs)
            if self.api_configs['credit_bureau']['mock_mode']:
                # Generate mock data based on customer info
                import random
                random.seed(hash(customer_info.email or customer_info.phone or "default"))
                
                credit_score = random.randint(300, 850)
                credit_history_length = random.randint(6, 240)  # 6 months to 20 years
                active_accounts = random.randint(1, 15)
                delinquent_accounts = random.randint(0, 3)
                bankruptcy_records = random.randint(0, 1)
                
                # Determine risk category based on credit score
                if credit_score >= 750:
                    risk_category = "low"
                elif credit_score >= 650:
                    risk_category = "medium"
                else:
                    risk_category = "high"
                
                return CreditBureauData(
                    credit_score=credit_score,
                    credit_history_length=credit_history_length,
                    active_accounts=active_accounts,
                    delinquent_accounts=delinquent_accounts,
                    bankruptcy_records=bankruptcy_records,
                    risk_category=risk_category,
                    last_updated=datetime.now()
                )
            
            # In production, would make actual API calls here
            return CreditBureauData()
            
        except Exception as e:
            logger.error(f"Credit bureau data retrieval failed: {str(e)}")
            return CreditBureauData()

    async def search_social_media_profiles(self, customer_info: CustomerInfo) -> List[SocialMediaProfile]:
        """
        Search for social media profiles (mock implementation)
        
        Args:
            customer_info: Customer information
            
        Returns:
            List of SocialMediaProfile results
        """
        try:
            if not self.api_configs['social_media']['enabled']:
                return []
            
            profiles = []
            
            if self.api_configs['social_media']['mock_mode']:
                # Mock social media profile data
                import random
                
                platforms = ['facebook', 'twitter', 'linkedin', 'instagram']
                
                for platform in platforms:
                    # Simulate profile existence probability
                    if random.random() > 0.3:  # 70% chance of having a profile
                        profile_age_days = random.randint(30, 3650)  # 1 month to 10 years
                        follower_count = random.randint(10, 5000)
                        
                        activity_levels = ['low', 'medium', 'high']
                        activity_level = random.choice(activity_levels)
                        
                        verification_statuses = ['verified', 'unverified']
                        verification_status = random.choice(verification_statuses)
                        
                        # Generate risk indicators
                        risk_indicators = []
                        if random.random() < 0.1:  # 10% chance
                            risk_indicators.append("suspicious_activity")
                        if random.random() < 0.05:  # 5% chance
                            risk_indicators.append("fake_followers")
                        
                        profiles.append(SocialMediaProfile(
                            platform=platform,
                            profile_exists=True,
                            profile_age_days=profile_age_days,
                            follower_count=follower_count,
                            activity_level=activity_level,
                            verification_status=verification_status,
                            risk_indicators=risk_indicators
                        ))
                    else:
                        profiles.append(SocialMediaProfile(
                            platform=platform,
                            profile_exists=False
                        ))
            
            return profiles
            
        except Exception as e:
            logger.error(f"Social media profile search failed: {str(e)}")
            return []

    async def verify_address(self, address: str) -> AddressVerification:
        """
        Verify address validity and deliverability (mock implementation)
        
        Args:
            address: Address to verify
            
        Returns:
            AddressVerification results
        """
        try:
            if not address or not self.api_configs['address_verification']['enabled']:
                return AddressVerification(
                    is_valid=False,
                    is_deliverable=False,
                    confidence_score=0.0
                )
            
            if self.api_configs['address_verification']['mock_mode']:
                # Mock address verification
                import random
                
                # Simple validation based on address format
                has_number = bool(re.search(r'\d+', address))
                has_street = len(address.split()) >= 3
                
                is_valid = has_number and has_street
                is_deliverable = is_valid and random.random() > 0.1  # 90% deliverable if valid
                
                address_types = ['residential', 'commercial', 'po_box']
                address_type = random.choice(address_types)
                
                # Mock geocoded location
                geocoded_location = {
                    'lat': random.uniform(25.0, 49.0),  # US latitude range
                    'lng': random.uniform(-125.0, -66.0)  # US longitude range
                } if is_valid else None
                
                confidence_score = 85.0 if is_valid else 20.0
                
                return AddressVerification(
                    is_valid=is_valid,
                    is_deliverable=is_deliverable,
                    address_type=address_type,
                    geocoded_location=geocoded_location,
                    confidence_score=confidence_score
                )
            
            return AddressVerification(
                is_valid=False,
                is_deliverable=False,
                confidence_score=0.0
            )
            
        except Exception as e:
            logger.error(f"Address verification failed: {str(e)}")
            return AddressVerification(
                is_valid=False,
                is_deliverable=False,
                confidence_score=0.0
            )

    async def search_public_records(self, customer_info: CustomerInfo, identity_data: Dict[str, Any]) -> PublicRecordsData:
        """
        Search public records (mock implementation)
        
        Args:
            customer_info: Customer information
            identity_data: Identity data from previous agents
            
        Returns:
            PublicRecordsData results
        """
        try:
            if not self.api_configs['public_records']['enabled']:
                return PublicRecordsData(risk_score=50.0)
            
            if self.api_configs['public_records']['mock_mode']:
                # Mock public records data
                import random
                
                criminal_records = []
                civil_records = []
                business_registrations = []
                property_records = []
                professional_licenses = []
                
                # Generate mock criminal records (low probability)
                if random.random() < 0.05:  # 5% chance
                    criminal_records.append({
                        'type': 'misdemeanor',
                        'date': '2020-03-15',
                        'jurisdiction': 'County Court',
                        'status': 'resolved'
                    })
                
                # Generate mock civil records (low probability)
                if random.random() < 0.1:  # 10% chance
                    civil_records.append({
                        'type': 'civil_lawsuit',
                        'date': '2019-08-22',
                        'court': 'District Court',
                        'status': 'settled'
                    })
                
                # Generate mock business registrations (medium probability)
                if random.random() < 0.3:  # 30% chance
                    business_registrations.append({
                        'business_name': 'Sample LLC',
                        'registration_date': '2018-01-10',
                        'state': 'CA',
                        'status': 'active'
                    })
                
                # Generate mock property records (medium probability)
                if random.random() < 0.4:  # 40% chance
                    property_records.append({
                        'property_type': 'residential',
                        'purchase_date': '2017-06-30',
                        'value': 450000,
                        'county': 'Sample County'
                    })
                
                # Generate mock professional licenses (low probability)
                if random.random() < 0.2:  # 20% chance
                    professional_licenses.append({
                        'license_type': 'Real Estate',
                        'issue_date': '2016-04-12',
                        'expiry_date': '2024-04-12',
                        'status': 'active'
                    })
                
                # Calculate risk score based on records
                risk_score = 10.0  # Base low risk
                
                if criminal_records:
                    risk_score += 40.0
                if len(civil_records) > 1:
                    risk_score += 20.0
                if len(business_registrations) > 3:
                    risk_score += 10.0
                
                risk_score = min(risk_score, 100.0)
                
                return PublicRecordsData(
                    criminal_records=criminal_records,
                    civil_records=civil_records,
                    business_registrations=business_registrations,
                    property_records=property_records,
                    professional_licenses=professional_licenses,
                    risk_score=risk_score
                )
            
            return PublicRecordsData(risk_score=50.0)
            
        except Exception as e:
            logger.error(f"Public records search failed: {str(e)}")
            return PublicRecordsData(risk_score=50.0)

    def calculate_overall_risk_score(self, result: DataIntegrationResult) -> float:
        """
        Calculate overall risk score based on all data sources
        
        Args:
            result: Data integration result
            
        Returns:
            Overall risk score (0-100)
        """
        try:
            risk_factors = []
            
            # Email verification risk
            if result.email_verification:
                if result.email_verification.is_disposable:
                    risk_factors.append(80.0)
                elif result.email_verification.domain_reputation == "poor":
                    risk_factors.append(60.0)
                elif result.email_verification.domain_reputation == "neutral":
                    risk_factors.append(30.0)
                else:
                    risk_factors.append(10.0)
            
            # Phone verification risk
            if result.phone_verification:
                if not result.phone_verification.is_valid:
                    risk_factors.append(70.0)
                elif result.phone_verification.line_type == "voip":
                    risk_factors.append(40.0)
                else:
                    risk_factors.append(15.0)
            
            # Credit bureau risk
            if result.credit_bureau_data and result.credit_bureau_data.risk_category:
                risk_mapping = {
                    'low': 10.0,
                    'medium': 40.0,
                    'high': 80.0
                }
                risk_factors.append(risk_mapping.get(result.credit_bureau_data.risk_category, 50.0))
            
            # Social media risk
            social_media_risk = 20.0  # Default medium risk
            if result.social_media_profiles:
                profile_count = sum(1 for p in result.social_media_profiles if p.profile_exists)
                if profile_count == 0:
                    social_media_risk = 60.0  # No social media presence is suspicious
                elif profile_count >= 3:
                    social_media_risk = 10.0  # Good social media presence
                
                # Check for risk indicators
                all_risk_indicators = []
                for profile in result.social_media_profiles:
                    all_risk_indicators.extend(profile.risk_indicators)
                
                if all_risk_indicators:
                    social_media_risk += len(all_risk_indicators) * 20.0
            
            risk_factors.append(min(social_media_risk, 100.0))
            
            # Address verification risk
            if result.address_verification:
                if not result.address_verification.is_valid:
                    risk_factors.append(50.0)
                elif not result.address_verification.is_deliverable:
                    risk_factors.append(30.0)
                else:
                    risk_factors.append(10.0)
            
            # Public records risk
            if result.public_records:
                risk_factors.append(result.public_records.risk_score)
            
            # Calculate weighted average
            if risk_factors:
                return min(sum(risk_factors) / len(risk_factors), 100.0)
            else:
                return 50.0  # Default medium risk if no data
                
        except Exception as e:
            logger.error(f"Risk score calculation failed: {str(e)}")
            return 50.0

    def calculate_data_completeness_score(self, result: DataIntegrationResult) -> float:
        """
        Calculate data completeness score
        
        Args:
            result: Data integration result
            
        Returns:
            Data completeness score (0-100)
        """
        try:
            completeness_factors = []
            
            # Email verification completeness
            if result.email_verification:
                completeness_factors.append(100.0 if result.email_verification.is_valid else 50.0)
            else:
                completeness_factors.append(0.0)
            
            # Phone verification completeness
            if result.phone_verification:
                completeness_factors.append(100.0 if result.phone_verification.is_valid else 50.0)
            else:
                completeness_factors.append(0.0)
            
            # Credit bureau data completeness
            if result.credit_bureau_data and result.credit_bureau_data.credit_score:
                completeness_factors.append(100.0)
            else:
                completeness_factors.append(0.0)
            
            # Social media completeness
            if result.social_media_profiles:
                profile_count = sum(1 for p in result.social_media_profiles if p.profile_exists)
                completeness_factors.append(min(profile_count * 25.0, 100.0))
            else:
                completeness_factors.append(0.0)
            
            # Address verification completeness
            if result.address_verification:
                completeness_factors.append(100.0 if result.address_verification.is_valid else 50.0)
            else:
                completeness_factors.append(0.0)
            
            # Public records completeness
            if result.public_records:
                record_count = (
                    len(result.public_records.criminal_records) +
                    len(result.public_records.civil_records) +
                    len(result.public_records.business_registrations) +
                    len(result.public_records.property_records) +
                    len(result.public_records.professional_licenses)
                )
                completeness_factors.append(min(record_count * 20.0, 100.0))
            else:
                completeness_factors.append(0.0)
            
            return sum(completeness_factors) / len(completeness_factors) if completeness_factors else 0.0
            
        except Exception as e:
            logger.error(f"Data completeness calculation failed: {str(e)}")
            return 0.0

    async def process_data_integration(self, request: DataIntegrationRequest) -> DataIntegrationResult:
        """
        Process complete data integration request
        
        Args:
            request: Data integration request
            
        Returns:
            DataIntegrationResult with all external data
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        try:
            # Initialize result
            result = DataIntegrationResult(
                processing_time_ms=0,
                overall_risk_score=50.0,
                data_completeness_score=0.0
            )
            
            # Parallel execution of data integration tasks
            tasks = []
            
            # Email verification
            if request.customer_info.email:
                tasks.append(self.verify_email(request.customer_info.email))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
            
            # Phone verification
            if request.customer_info.phone:
                tasks.append(self.verify_phone(request.customer_info.phone))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
            
            # Credit bureau data
            tasks.append(self.get_credit_bureau_data(request.customer_info))
            
            # Social media profiles
            tasks.append(self.search_social_media_profiles(request.customer_info))
            
            # Address verification (extract from OCR results if available)
            address = None
            if 'ocr' in request.previous_results:
                ocr_data = request.previous_results['ocr']
                if 'data' in ocr_data and 'results' in ocr_data['data']:
                    for ocr_result in ocr_data['data']['results']:
                        if 'extracted_data' in ocr_result:
                            address = ocr_result['extracted_data'].get('address')
                            if address:
                                break
            
            if address:
                tasks.append(self.verify_address(address))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
            
            # Public records search
            identity_data = {}
            if 'ocr' in request.previous_results:
                identity_data = request.previous_results['ocr']
            
            tasks.append(self.search_public_records(request.customer_info, identity_data))
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            if request.customer_info.email and not isinstance(results[0], Exception):
                result.email_verification = results[0]
            elif request.customer_info.email and isinstance(results[0], Exception):
                errors.append(f"Email verification failed: {str(results[0])}")
            
            if request.customer_info.phone and not isinstance(results[1], Exception):
                result.phone_verification = results[1]
            elif request.customer_info.phone and isinstance(results[1], Exception):
                errors.append(f"Phone verification failed: {str(results[1])}")
            
            if not isinstance(results[2], Exception):
                result.credit_bureau_data = results[2]
            else:
                errors.append(f"Credit bureau data retrieval failed: {str(results[2])}")
            
            if not isinstance(results[3], Exception):
                result.social_media_profiles = results[3]
            else:
                errors.append(f"Social media search failed: {str(results[3])}")
            
            if address and not isinstance(results[4], Exception):
                result.address_verification = results[4]
            elif address and isinstance(results[4], Exception):
                errors.append(f"Address verification failed: {str(results[4])}")
            
            if not isinstance(results[5], Exception):
                result.public_records = results[5]
            else:
                errors.append(f"Public records search failed: {str(results[5])}")
            
            # Calculate overall scores
            result.overall_risk_score = self.calculate_overall_risk_score(result)
            result.data_completeness_score = self.calculate_data_completeness_score(result)
            
            # Add warnings based on findings
            if result.email_verification and result.email_verification.is_disposable:
                warnings.append("Customer is using a disposable email address")
            
            if result.phone_verification and not result.phone_verification.is_valid:
                warnings.append("Customer phone number is invalid")
            
            if result.credit_bureau_data and result.credit_bureau_data.risk_category == "high":
                warnings.append("Customer has high credit risk profile")
            
            if result.public_records and result.public_records.criminal_records:
                warnings.append("Customer has criminal records on file")
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            result.processing_time_ms = processing_time
            result.errors = errors
            result.warnings = warnings
            
            return result
            
        except Exception as e:
            logger.error(f"Data integration processing failed: {str(e)}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return DataIntegrationResult(
                processing_time_ms=processing_time,
                overall_risk_score=100.0,  # High risk on error
                data_completeness_score=0.0,
                errors=[str(e)],
                warnings=warnings
            )

# Initialize data integration processor
data_integration_processor = DataIntegrationProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-integration-agent",
        "version": "1.0.0",
        "api_configs": {k: v['enabled'] for k, v in data_integration_processor.api_configs.items()},
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process", response_model=DataIntegrationResponse)
async def process_data_integration_request(request: DataIntegrationRequest):
    """
    Process data integration request
    
    Args:
        request: Data integration request
        
    Returns:
        Data integration response
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing data integration request: {request.request_id}")
        
        # Process data integration
        result = await data_integration_processor.process_data_integration(request)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Determine status
        status = "success"
        if result.errors:
            status = "error"
        elif result.warnings:
            status = "warning"
        
        response_data = result.dict()
        
        return DataIntegrationResponse(
            status=status,
            data=response_data,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Data integration processing failed: {str(e)}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return DataIntegrationResponse(
            status="error",
            data={"error": str(e)},
            processing_time=processing_time,
            error=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Data Integration Agent",
        "description": "External data integration for enhanced KYC verification",
        "version": "1.0.0",
        "data_sources": list(data_integration_processor.api_configs.keys()),
        "endpoints": {
            "health": "/health",
            "process": "/process"
        }
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8004))
    
    # Run the service
    uvicorn.run(
        "data_integration_service:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
