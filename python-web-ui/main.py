#!/usr/bin/env python3
"""
KYC Automation Platform - Production Web Interface
A modern FastAPI-based web interface for the KYC automation platform.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import uvicorn
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Application configuration"""
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    KAFKA_REQUEST_TOPIC = os.getenv('KAFKA_REQUEST_TOPIC', 'kyc_requests')
    KAFKA_RESULT_TOPIC = os.getenv('KAFKA_RESULT_TOPIC', 'kyc_results')
    KAFKA_CONSUMER_GROUP = os.getenv('KAFKA_CONSUMER_GROUP', 'web_ui_consumer')
    
    UPLOAD_DIR = Path('uploads')
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.txt'}
    
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))

# Data models
class KYCRequest(BaseModel):
    """KYC request model"""
    request_id: str
    customer_email: str
    timestamp: datetime
    file_id_path: str
    file_selfie_path: str

class KYCStatus(BaseModel):
    """KYC processing status model"""
    request_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    result: Optional[Dict] = None

# Global state
app = FastAPI(
    title="KYC Automation Platform",
    description="Production-grade KYC verification and compliance automation",
    version="1.0.0"
)

# In-memory storage for request status (in production, use Redis)
request_status: Dict[str, KYCStatus] = {}
kafka_producer: Optional[KafkaProducer] = None

# Setup directories
Config.UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Kafka producer initialization
async def init_kafka_producer():
    """Initialize Kafka producer"""
    global kafka_producer
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers=[Config.KAFKA_BOOTSTRAP_SERVERS],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            retry_backoff_ms=1000
        )
        logger.info("Kafka producer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Kafka producer: {e}")
        raise

async def kafka_consumer_task():
    """Background task to consume Kafka results"""
    try:
        consumer = KafkaConsumer(
            Config.KAFKA_RESULT_TOPIC,
            bootstrap_servers=[Config.KAFKA_BOOTSTRAP_SERVERS],
            group_id=Config.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=1000  # Add timeout to make it non-blocking
        )
        
        logger.info("Kafka consumer started, listening for results...")
        
        while True:
            try:
                # Poll for messages with timeout
                messages = consumer.poll(timeout_ms=1000)
                
                for topic_partition, records in messages.items():
                    for message in records:
                        try:
                            result = message.value
                            request_id = result.get('request_id')
                            
                            if request_id and request_id in request_status:
                                # Update status with result
                                request_status[request_id].status = 'completed'
                                request_status[request_id].progress = 100
                                request_status[request_id].message = 'KYC processing completed successfully'
                                request_status[request_id].result = result
                                
                                logger.info(f"Updated status for request {request_id}")
                            
                        except Exception as e:
                            logger.error(f"Error processing Kafka message: {e}")
                
                # Allow other tasks to run
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error polling Kafka: {e}")
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"Kafka consumer error: {e}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting KYC Automation Platform Web Interface")
    
    # Initialize Kafka producer
    await init_kafka_producer()
    
    # Start Kafka consumer in background
    asyncio.create_task(kafka_consumer_task())
    
    logger.info("Web interface startup completed")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Kafka connectivity
        kafka_healthy = kafka_producer is not None
        
        return {
            "status": "healthy" if kafka_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "kafka": "healthy" if kafka_healthy else "unhealthy",
                "web_server": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Main page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main KYC upload page"""
    return templates.TemplateResponse("index.html", {"request": request})

# File upload and KYC submission
@app.post("/submit")
async def submit_kyc(
    customer_email: str = Form(...),
    file_id: UploadFile = File(...),
    file_selfie: UploadFile = File(...)
):
    """Submit KYC request with document uploads"""
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Validate files
        for file in [file_id, file_selfie]:
            if not file.filename:
                raise HTTPException(status_code=400, detail="File name is required")
            
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in Config.ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type {file_ext} not allowed. Allowed: {Config.ALLOWED_EXTENSIONS}"
                )
        
        # Save uploaded files
        id_file_path = Config.UPLOAD_DIR / f"{request_id}_id{Path(file_id.filename).suffix}"
        selfie_file_path = Config.UPLOAD_DIR / f"{request_id}_selfie{Path(file_selfie.filename).suffix}"
        
        async with aiofiles.open(id_file_path, 'wb') as f:
            content = await file_id.read()
            if len(content) > Config.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")
            await f.write(content)
        
        async with aiofiles.open(selfie_file_path, 'wb') as f:
            content = await file_selfie.read()
            if len(content) > Config.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")
            await f.write(content)
        
        # Create KYC request
        kyc_request = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "customer_info": {
                "email": customer_email
            },
            "documents": {
                "id_document": {
                    "path": str(id_file_path),
                    "filename": file_id.filename,
                    "content_type": file_id.content_type
                },
                "selfie": {
                    "path": str(selfie_file_path),
                    "filename": file_selfie.filename,
                    "content_type": file_selfie.content_type
                }
            },
            "processing_config": {
                "risk_tolerance": "medium",
                "compliance_level": "standard"
            }
        }
        
        # Initialize request status
        request_status[request_id] = KYCStatus(
            request_id=request_id,
            status="pending",
            progress=0,
            message="KYC request submitted, waiting for processing..."
        )
        
        # Send to Kafka
        if kafka_producer:
            kafka_producer.send(Config.KAFKA_REQUEST_TOPIC, kyc_request)
            kafka_producer.flush()
            
            # Update status to processing
            request_status[request_id].status = "processing"
            request_status[request_id].progress = 10
            request_status[request_id].message = "KYC request sent for processing..."
            
            logger.info(f"KYC request {request_id} submitted successfully")
        else:
            raise HTTPException(status_code=503, detail="Kafka producer not available")
        
        return {
            "success": True,
            "request_id": request_id,
            "message": "KYC request submitted successfully",
            "status_url": f"/status/{request_id}",
            "result_url": f"/result/{request_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting KYC request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Status endpoint
@app.get("/status/{request_id}")
async def get_status(request_id: str):
    """Get KYC processing status"""
    if request_id not in request_status:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return request_status[request_id]

# Result page
@app.get("/result/{request_id}", response_class=HTMLResponse)
async def get_result(request: Request, request_id: str):
    """Display KYC results page"""
    if request_id not in request_status:
        raise HTTPException(status_code=404, detail="Request not found")
    
    status = request_status[request_id]
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "request_id": request_id,
        "status": status,
        "result": status.result
    })

# Processing page (shows real-time status)
@app.get("/processing/{request_id}", response_class=HTMLResponse)
async def processing_page(request: Request, request_id: str):
    """Processing status page with real-time updates"""
    if request_id not in request_status:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return templates.TemplateResponse("processing.html", {
        "request": request,
        "request_id": request_id
    })

# WebSocket endpoint for real-time status updates
@app.websocket("/ws/status/{request_id}")
async def websocket_status(websocket: WebSocket, request_id: str):
    """WebSocket endpoint for real-time status updates"""
    await websocket.accept()
    
    try:
        while True:
            if request_id in request_status:
                status = request_status[request_id]
                await websocket.send_json(status.dict())
                
                # If completed, close connection
                if status.status in ['completed', 'failed']:
                    break
            
            await asyncio.sleep(1)  # Update every second
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# User guide endpoint
@app.get("/userguide", response_class=HTMLResponse)
async def user_guide(request: Request):
    """User guide page"""
    return templates.TemplateResponse("userguide.html", {"request": request})

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False,
        log_level="info"
    )
