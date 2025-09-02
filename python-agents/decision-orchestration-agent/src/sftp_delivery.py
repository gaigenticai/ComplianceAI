#!/usr/bin/env python3
"""
SFTP Delivery Service - Secure Report Delivery for Regulatory Compliance
======================================================================

This module provides secure SFTP delivery capabilities for compliance reports
with encryption, digital signatures, and comprehensive delivery tracking.

Key Features:
- Secure SFTP connection handling with SSH key management
- File encryption and digital signatures for integrity
- Delivery confirmation and receipt processing
- Retry logic for failed deliveries with exponential backoff
- Comprehensive audit trail and logging
- Multi-destination delivery support

Rule Compliance:
- Rule 1: No stubs - Full production SFTP implementation
- Rule 2: Modular design - Extensible delivery architecture
- Rule 4: Understanding existing features - Integrates with report generator
- Rule 17: Comprehensive documentation throughout
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import hashlib
import hmac
import base64
import json
import tempfile
import shutil
from pathlib import Path

# SFTP and cryptography
import asyncssh
import paramiko
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import aiofiles

# Database
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeliveryStatus(Enum):
    """Delivery status enumeration"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class EncryptionMethod(Enum):
    """Encryption method enumeration"""
    AES_256_GCM = "AES_256_GCM"
    RSA_OAEP = "RSA_OAEP"
    HYBRID = "HYBRID"  # RSA + AES

@dataclass
class SFTPConfig:
    """SFTP connection configuration"""
    hostname: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    remote_directory: str = "/"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    enable_compression: bool = True
    host_key_verification: bool = True
    known_hosts_file: Optional[str] = None

@dataclass
class DeliveryRequest:
    """Delivery request structure"""
    delivery_id: str
    report_id: str
    file_path: str
    destination_config: SFTPConfig
    encryption_enabled: bool = True
    digital_signature: bool = True
    delivery_confirmation: bool = True
    priority: int = 2  # 1=High, 2=Medium, 3=Low
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class DeliveryResult:
    """Delivery result structure"""
    delivery_id: str
    status: DeliveryStatus
    delivered_at: Optional[datetime] = None
    remote_path: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    confirmation_receipt: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    delivery_time: Optional[float] = None

class SFTPDeliveryService:
    """
    Secure SFTP delivery service with encryption and digital signatures
    
    Provides comprehensive report delivery capabilities with security,
    reliability, and regulatory compliance features.
    """
    
    def __init__(self):
        self.pg_pool = None
        self.encryption_key = None
        self.signing_key = None
        self.verification_key = None
        
        # Configuration
        self.config = {
            'temp_dir': os.getenv('SFTP_TEMP_DIR', '/tmp/sftp_delivery'),
            'key_dir': os.getenv('SFTP_KEY_DIR', 'keys'),
            'max_concurrent_deliveries': int(os.getenv('MAX_CONCURRENT_DELIVERIES', '5')),
            'delivery_timeout': int(os.getenv('DELIVERY_TIMEOUT', '300')),
            'enable_encryption': os.getenv('ENABLE_ENCRYPTION', 'true').lower() == 'true',
            'enable_signatures': os.getenv('ENABLE_SIGNATURES', 'true').lower() == 'true',
            'audit_deliveries': os.getenv('AUDIT_DELIVERIES', 'true').lower() == 'true'
        }
        
        # Performance metrics
        self.metrics = {
            'deliveries_attempted': 0,
            'deliveries_successful': 0,
            'deliveries_failed': 0,
            'avg_delivery_time': 0.0,
            'total_bytes_delivered': 0
        }
    
    async def initialize(self):
        """Initialize the SFTP delivery service"""
        try:
            # Initialize database connection
            self.pg_pool = await asyncpg.create_pool(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'compliance_ai'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
                min_size=2,
                max_size=10
            )
            
            # Create temporary directory
            os.makedirs(self.config['temp_dir'], exist_ok=True)
            
            # Initialize cryptographic keys
            await self._initialize_crypto_keys()
            
            logger.info("SFTP Delivery Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SFTP Delivery Service: {e}")
            raise
    
    async def _initialize_crypto_keys(self):
        """Initialize cryptographic keys for encryption and signing"""
        try:
            key_dir = Path(self.config['key_dir'])
            key_dir.mkdir(exist_ok=True)
            
            # Initialize encryption key (AES-256)
            encryption_key_file = key_dir / 'encryption.key'
            if encryption_key_file.exists():
                async with aiofiles.open(encryption_key_file, 'rb') as f:
                    self.encryption_key = await f.read()
            else:
                # Generate new encryption key
                self.encryption_key = os.urandom(32)  # 256-bit key
                async with aiofiles.open(encryption_key_file, 'wb') as f:
                    await f.write(self.encryption_key)
                os.chmod(encryption_key_file, 0o600)  # Restrict permissions
            
            # Initialize signing keys (RSA)
            signing_key_file = key_dir / 'signing_key.pem'
            verification_key_file = key_dir / 'verification_key.pem'
            
            if signing_key_file.exists() and verification_key_file.exists():
                # Load existing keys
                async with aiofiles.open(signing_key_file, 'rb') as f:
                    signing_key_data = await f.read()
                    self.signing_key = serialization.load_pem_private_key(
                        signing_key_data, password=None, backend=default_backend()
                    )
                
                async with aiofiles.open(verification_key_file, 'rb') as f:
                    verification_key_data = await f.read()
                    self.verification_key = serialization.load_pem_public_key(
                        verification_key_data, backend=default_backend()
                    )
            else:
                # Generate new key pair
                self.signing_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                self.verification_key = self.signing_key.public_key()
                
                # Save keys
                signing_key_pem = self.signing_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                verification_key_pem = self.verification_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                async with aiofiles.open(signing_key_file, 'wb') as f:
                    await f.write(signing_key_pem)
                os.chmod(signing_key_file, 0o600)
                
                async with aiofiles.open(verification_key_file, 'wb') as f:
                    await f.write(verification_key_pem)
                os.chmod(verification_key_file, 0o644)
            
            logger.info("Cryptographic keys initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cryptographic keys: {e}")
            raise
    
    async def deliver_report(self, request: DeliveryRequest) -> DeliveryResult:
        """
        Deliver a report via SFTP with encryption and digital signatures
        
        This is the main entry point for secure report delivery with full
        encryption, signing, and delivery confirmation capabilities.
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting SFTP delivery: {request.delivery_id}")
            
            # Update delivery status
            await self._update_delivery_status(request.delivery_id, DeliveryStatus.IN_PROGRESS)
            
            # Validate request
            await self._validate_delivery_request(request)
            
            # Prepare file for delivery
            prepared_file = await self._prepare_file_for_delivery(request)
            
            # Perform SFTP delivery
            delivery_result = await self._perform_sftp_delivery(request, prepared_file)
            
            # Process delivery confirmation
            if request.delivery_confirmation and delivery_result.status == DeliveryStatus.DELIVERED:
                await self._process_delivery_confirmation(request, delivery_result)
            
            # Update metrics
            delivery_time = (datetime.now() - start_time).total_seconds()
            await self._update_delivery_metrics(request, delivery_result, delivery_time)
            
            # Update final status
            await self._update_delivery_status(request.delivery_id, delivery_result.status)
            
            logger.info(f"SFTP delivery completed: {request.delivery_id} in {delivery_time:.2f}s")
            return delivery_result
            
        except Exception as e:
            # Handle delivery failure
            error_msg = f"SFTP delivery failed: {str(e)}"
            logger.error(error_msg)
            
            await self._update_delivery_status(request.delivery_id, DeliveryStatus.FAILED, error_msg)
            
            self.metrics['deliveries_failed'] += 1
            
            return DeliveryResult(
                delivery_id=request.delivery_id,
                status=DeliveryStatus.FAILED,
                error_message=error_msg
            )
    
    async def _validate_delivery_request(self, request: DeliveryRequest):
        """Validate delivery request parameters"""
        try:
            # Check file exists
            if not os.path.exists(request.file_path):
                raise FileNotFoundError(f"Report file not found: {request.file_path}")
            
            # Check file size
            file_size = os.path.getsize(request.file_path)
            max_size = int(os.getenv('MAX_FILE_SIZE', '100000000'))  # 100MB default
            if file_size > max_size:
                raise ValueError(f"File size ({file_size}) exceeds maximum ({max_size})")
            
            # Validate SFTP configuration
            if not request.destination_config.hostname:
                raise ValueError("SFTP hostname is required")
            
            if not request.destination_config.username:
                raise ValueError("SFTP username is required")
            
            if not request.destination_config.password and not request.destination_config.private_key_path:
                raise ValueError("Either password or private key is required for SFTP")
            
            logger.debug(f"Delivery request validation passed: {request.delivery_id}")
            
        except Exception as e:
            logger.error(f"Delivery request validation failed: {e}")
            raise
    
    async def _prepare_file_for_delivery(self, request: DeliveryRequest) -> str:
        """Prepare file for delivery with encryption and signing"""
        try:
            temp_file = os.path.join(
                self.config['temp_dir'],
                f"{request.delivery_id}_{os.path.basename(request.file_path)}"
            )
            
            # Copy original file to temp location
            shutil.copy2(request.file_path, temp_file)
            
            # Apply encryption if enabled
            if request.encryption_enabled and self.config['enable_encryption']:
                temp_file = await self._encrypt_file(temp_file, request.delivery_id)
            
            # Apply digital signature if enabled
            if request.digital_signature and self.config['enable_signatures']:
                temp_file = await self._sign_file(temp_file, request.delivery_id)
            
            logger.debug(f"File prepared for delivery: {temp_file}")
            return temp_file
            
        except Exception as e:
            logger.error(f"Failed to prepare file for delivery: {e}")
            raise
    
    async def _encrypt_file(self, file_path: str, delivery_id: str) -> str:
        """Encrypt file using AES-256-GCM"""
        try:
            encrypted_file = f"{file_path}.encrypted"
            
            # Generate random IV
            iv = os.urandom(12)  # 96-bit IV for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt file
            async with aiofiles.open(file_path, 'rb') as infile, \
                       aiofiles.open(encrypted_file, 'wb') as outfile:
                
                # Write IV to beginning of encrypted file
                await outfile.write(iv)
                
                # Encrypt file in chunks
                while True:
                    chunk = await infile.read(8192)
                    if not chunk:
                        break
                    encrypted_chunk = encryptor.update(chunk)
                    await outfile.write(encrypted_chunk)
                
                # Finalize encryption and write authentication tag
                encryptor.finalize()
                await outfile.write(encryptor.tag)
            
            # Remove original file
            os.remove(file_path)
            
            logger.debug(f"File encrypted successfully: {encrypted_file}")
            return encrypted_file
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise
    
    async def _sign_file(self, file_path: str, delivery_id: str) -> str:
        """Create digital signature for file"""
        try:
            signature_file = f"{file_path}.sig"
            
            # Calculate file hash
            file_hash = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    file_hash.update(chunk)
            
            # Create digital signature
            signature = self.signing_key.sign(
                file_hash.digest(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Save signature
            signature_data = {
                'delivery_id': delivery_id,
                'file_hash': file_hash.hexdigest(),
                'signature': base64.b64encode(signature).decode('utf-8'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'algorithm': 'RSA-PSS-SHA256'
            }
            
            async with aiofiles.open(signature_file, 'w') as f:
                await f.write(json.dumps(signature_data, indent=2))
            
            logger.debug(f"File signed successfully: {signature_file}")
            return file_path  # Return original file path, signature is separate
            
        except Exception as e:
            logger.error(f"File signing failed: {e}")
            raise
    
    async def _perform_sftp_delivery(self, request: DeliveryRequest, file_path: str) -> DeliveryResult:
        """Perform actual SFTP delivery with retry logic"""
        retry_count = 0
        last_error = None
        
        while retry_count <= request.destination_config.max_retries:
            try:
                logger.info(f"SFTP delivery attempt {retry_count + 1} for {request.delivery_id}")
                
                # Perform SFTP transfer
                result = await self._sftp_transfer(request, file_path)
                
                # Success - clean up temp files
                await self._cleanup_temp_files(file_path)
                
                return result
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count <= request.destination_config.max_retries:
                    delay = request.destination_config.retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    logger.warning(f"SFTP delivery attempt {retry_count} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"SFTP delivery failed after {retry_count} attempts: {e}")
        
        # All retries exhausted
        await self._cleanup_temp_files(file_path)
        
        return DeliveryResult(
            delivery_id=request.delivery_id,
            status=DeliveryStatus.FAILED,
            error_message=f"Failed after {retry_count} attempts: {str(last_error)}",
            retry_count=retry_count
        )
    
    async def _sftp_transfer(self, request: DeliveryRequest, file_path: str) -> DeliveryResult:
        """Perform SFTP file transfer"""
        try:
            config = request.destination_config
            
            # Prepare connection parameters
            connect_kwargs = {
                'host': config.hostname,
                'port': config.port,
                'username': config.username,
                'connect_timeout': config.timeout,
                'compression_algs': ['zlib'] if config.enable_compression else None
            }
            
            # Add authentication
            if config.private_key_path:
                connect_kwargs['client_keys'] = [config.private_key_path]
                if config.private_key_passphrase:
                    connect_kwargs['passphrase'] = config.private_key_passphrase
            elif config.password:
                connect_kwargs['password'] = config.password
            
            # Add host key verification
            if config.host_key_verification and config.known_hosts_file:
                connect_kwargs['known_hosts'] = config.known_hosts_file
            elif not config.host_key_verification:
                connect_kwargs['known_hosts'] = None
            
            # Establish SFTP connection
            async with asyncssh.connect(**connect_kwargs) as conn:
                async with conn.start_sftp_client() as sftp:
                    # Ensure remote directory exists
                    try:
                        await sftp.makedirs(config.remote_directory, exist_ok=True)
                    except Exception as e:
                        logger.warning(f"Could not create remote directory: {e}")
                    
                    # Generate remote filename
                    local_filename = os.path.basename(file_path)
                    remote_path = f"{config.remote_directory.rstrip('/')}/{local_filename}"
                    
                    # Transfer file
                    start_time = datetime.now()
                    await sftp.put(file_path, remote_path)
                    transfer_time = (datetime.now() - start_time).total_seconds()
                    
                    # Get file info
                    file_size = os.path.getsize(file_path)
                    checksum = await self._calculate_file_checksum(file_path)
                    
                    # Transfer signature file if it exists
                    signature_file = f"{file_path}.sig"
                    if os.path.exists(signature_file):
                        remote_sig_path = f"{remote_path}.sig"
                        await sftp.put(signature_file, remote_sig_path)
                    
                    logger.info(f"SFTP transfer completed: {file_size} bytes in {transfer_time:.2f}s")
                    
                    return DeliveryResult(
                        delivery_id=request.delivery_id,
                        status=DeliveryStatus.DELIVERED,
                        delivered_at=datetime.now(timezone.utc),
                        remote_path=remote_path,
                        file_size=file_size,
                        checksum=checksum,
                        delivery_time=transfer_time
                    )
            
        except Exception as e:
            logger.error(f"SFTP transfer failed: {e}")
            raise
    
    async def _process_delivery_confirmation(self, request: DeliveryRequest, result: DeliveryResult):
        """Process delivery confirmation and receipt"""
        try:
            # Generate delivery receipt
            receipt_data = {
                'delivery_id': request.delivery_id,
                'report_id': request.report_id,
                'delivered_at': result.delivered_at.isoformat(),
                'remote_path': result.remote_path,
                'file_size': result.file_size,
                'checksum': result.checksum,
                'delivery_time': result.delivery_time,
                'destination': {
                    'hostname': request.destination_config.hostname,
                    'remote_directory': request.destination_config.remote_directory
                }
            }
            
            # Create HMAC signature for receipt
            receipt_json = json.dumps(receipt_data, sort_keys=True)
            receipt_signature = hmac.new(
                self.encryption_key,
                receipt_json.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            receipt_data['signature'] = receipt_signature
            result.confirmation_receipt = json.dumps(receipt_data)
            
            logger.debug(f"Delivery confirmation processed: {request.delivery_id}")
            
        except Exception as e:
            logger.warning(f"Failed to process delivery confirmation: {e}")
    
    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file"""
        try:
            hash_sha256 = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate file checksum: {e}")
            return ""
    
    async def _cleanup_temp_files(self, file_path: str):
        """Clean up temporary files"""
        try:
            files_to_remove = [
                file_path,
                f"{file_path}.encrypted",
                f"{file_path}.sig"
            ]
            
            for file_to_remove in files_to_remove:
                if os.path.exists(file_to_remove):
                    os.remove(file_to_remove)
                    logger.debug(f"Cleaned up temp file: {file_to_remove}")
                    
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
    
    async def _update_delivery_status(self, delivery_id: str, status: DeliveryStatus, error_message: str = None):
        """Update delivery status in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE report_deliveries 
                    SET delivery_status = $1, error_message = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE delivery_id = $1
                """, delivery_id, status.value, error_message)
                
        except Exception as e:
            logger.error(f"Failed to update delivery status: {e}")
    
    async def _update_delivery_metrics(self, request: DeliveryRequest, result: DeliveryResult, delivery_time: float):
        """Update delivery performance metrics"""
        try:
            self.metrics['deliveries_attempted'] += 1
            
            if result.status == DeliveryStatus.DELIVERED:
                self.metrics['deliveries_successful'] += 1
                self.metrics['total_bytes_delivered'] += result.file_size or 0
                
                # Update average delivery time
                current_avg = self.metrics['avg_delivery_time']
                successful_count = self.metrics['deliveries_successful']
                self.metrics['avg_delivery_time'] = (
                    (current_avg * (successful_count - 1) + delivery_time) / successful_count
                )
            else:
                self.metrics['deliveries_failed'] += 1
            
            logger.debug(f"Delivery metrics updated for {request.delivery_id}")
            
        except Exception as e:
            logger.error(f"Failed to update delivery metrics: {e}")
    
    async def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get delivery status from database"""
        try:
            async with self.pg_pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT delivery_id, delivery_status, delivery_attempts, 
                           last_attempt_at, delivered_at, confirmation_receipt, error_message
                    FROM report_deliveries
                    WHERE delivery_id = $1
                """, delivery_id)
                
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Failed to get delivery status: {e}")
            return None
    
    async def list_pending_deliveries(self) -> List[Dict[str, Any]]:
        """List all pending deliveries"""
        try:
            async with self.pg_pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT delivery_id, report_id, delivery_status, created_at, 
                           delivery_attempts, max_attempts
                    FROM report_deliveries
                    WHERE delivery_status IN ('PENDING', 'IN_PROGRESS')
                    ORDER BY created_at ASC
                """)
                
                return [dict(result) for result in results]
                
        except Exception as e:
            logger.error(f"Failed to list pending deliveries: {e}")
            return []
    
    async def get_delivery_metrics(self) -> Dict[str, Any]:
        """Get delivery performance metrics"""
        return {
            **self.metrics,
            'success_rate': (
                (self.metrics['deliveries_successful'] / self.metrics['deliveries_attempted'] * 100)
                if self.metrics['deliveries_attempted'] > 0 else 0.0
            ),
            'uptime': datetime.now().isoformat()
        }
    
    async def retry_failed_delivery(self, delivery_id: str) -> DeliveryResult:
        """Retry a failed delivery"""
        try:
            # Get delivery details from database
            async with self.pg_pool.acquire() as conn:
                delivery_record = await conn.fetchrow("""
                    SELECT rd.*, cr.file_path, cr.report_id
                    FROM report_deliveries rd
                    JOIN compliance_reports cr ON rd.report_id = cr.report_id
                    WHERE rd.delivery_id = $1
                """, delivery_id)
                
                if not delivery_record:
                    raise ValueError(f"Delivery not found: {delivery_id}")
                
                if delivery_record['delivery_status'] != 'FAILED':
                    raise ValueError(f"Delivery is not in failed status: {delivery_record['delivery_status']}")
            
            # Reconstruct delivery request (simplified)
            config = SFTPConfig(
                hostname=delivery_record['destination'].get('hostname', ''),
                username=delivery_record['destination'].get('username', ''),
                remote_directory=delivery_record['destination'].get('remote_directory', '/')
            )
            
            request = DeliveryRequest(
                delivery_id=delivery_id,
                report_id=delivery_record['report_id'],
                file_path=delivery_record['file_path'],
                destination_config=config
            )
            
            # Retry delivery
            return await self.deliver_report(request)
            
        except Exception as e:
            logger.error(f"Failed to retry delivery: {e}")
            raise

# Factory function
async def create_sftp_delivery_service() -> SFTPDeliveryService:
    """Factory function to create and initialize SFTP delivery service"""
    service = SFTPDeliveryService()
    await service.initialize()
    return service
