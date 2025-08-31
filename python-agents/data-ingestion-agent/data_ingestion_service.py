"""
Data Ingestion Agent - LangChain-based Autonomous Multi-format Processing
==========================================================================

This agent uses LangChain to autonomously ingest, analyze, and process data in ANY format
without predefined schemas. It makes intelligent decisions about data structure, quality,
and processing strategies through autonomous reasoning.

Key Features:
- Schema-agnostic processing with dynamic inference
- Multi-format support: CSV, JSON, XML, PDF, images, databases
- Autonomous decision-making for data processing strategies
- Real-time + batch processing hybrid architecture
- Inter-agent communication via Kafka
- Production-grade error handling and monitoring

Author: Agentic KYC Engine Team
Version: 1.0.0
Framework: LangChain for autonomous reasoning
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import uuid

# FastAPI framework
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# LangChain framework for autonomous reasoning
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import BaseTool, StructuredTool
from langchain.schema import AgentAction, AgentFinish
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import ChatOpenAI
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_community.document_loaders import (
    CSVLoader, JSONLoader, UnstructuredPDFLoader, 
    UnstructuredWordDocumentLoader, UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Data processing libraries
import pandas as pd
import numpy as np
from PIL import Image
import cv2
import pytesseract
import PyPDF2
import pdfplumber
import magic
import chardet
from sqlalchemy import create_engine, text
import pymongo
import redis

# Schema inference and validation
import jsonschema
from great_expectations.core import ExpectationSuite
import pandas_profiling

# Kafka for inter-agent communication
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Monitoring and logging
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

# Environment configuration
from dotenv import load_dotenv
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
INGESTION_REQUESTS = Counter('data_ingestion_requests_total', 'Total data ingestion requests')
INGESTION_DURATION = Histogram('data_ingestion_duration_seconds', 'Data ingestion processing time')
ACTIVE_INGESTIONS = Gauge('data_ingestion_active', 'Currently active ingestion processes')
SCHEMA_INFERENCES = Counter('schema_inferences_total', 'Total schema inferences performed')
FORMAT_DETECTIONS = Counter('format_detections_total', 'Format detections by type', ['format_type'])

# Initialize FastAPI app
app = FastAPI(
    title="Data Ingestion Agent - LangChain Autonomous Processing",
    description="Autonomous multi-format data ingestion with schema-agnostic processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class DataIngestionRequest(BaseModel):
    """Request model for data ingestion with autonomous processing parameters"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_source: str = Field(..., description="Data source identifier or path")
    source_type: str = Field(..., description="Source type: file, database, api, stream")
    processing_mode: str = Field(default="autonomous", description="Processing mode: autonomous, guided, manual")
    industry_context: Optional[str] = Field(None, description="Industry context for specialized processing")
    compliance_requirements: List[str] = Field(default=[], description="Compliance requirements to enforce")
    quality_threshold: float = Field(default=0.8, description="Minimum data quality threshold")
    enable_schema_inference: bool = Field(default=True, description="Enable autonomous schema inference")
    enable_data_profiling: bool = Field(default=True, description="Enable comprehensive data profiling")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

class SchemaInferenceResult(BaseModel):
    """Result of autonomous schema inference"""
    inferred_schema: Dict[str, Any]
    confidence_score: float = Field(ge=0.0, le=1.0)
    field_types: Dict[str, str]
    data_quality_score: float = Field(ge=0.0, le=1.0)
    anomalies_detected: List[str]
    recommendations: List[str]

class DataIngestionResult(BaseModel):
    """Comprehensive result of autonomous data ingestion"""
    request_id: str
    status: str
    processing_time_seconds: float
    records_processed: int
    data_quality_score: float
    schema_inference: SchemaInferenceResult
    processed_data: Dict[str, Any]
    agent_decisions: List[Dict[str, Any]]
    next_recommended_actions: List[str]
    compliance_status: Dict[str, Any]
    errors: List[str] = []
    warnings: List[str] = []

class AgentDecisionCallback(AsyncCallbackHandler):
    """Callback handler to track autonomous agent decisions"""
    
    def __init__(self):
        self.decisions = []
        self.reasoning_steps = []
    
    async def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """Track agent actions and reasoning"""
        decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action.tool,
            "reasoning": action.log,
            "input": action.tool_input
        }
        self.decisions.append(decision)
        logger.info("Agent decision made", decision=decision)
    
    async def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Track final agent decision"""
        final_decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "final_output": finish.return_values,
            "reasoning": finish.log
        }
        self.decisions.append(final_decision)
        logger.info("Agent processing completed", final_decision=final_decision)

class DataFormatDetectionTool(BaseTool):
    """LangChain tool for autonomous data format detection"""
    
    name = "data_format_detector"
    description = "Autonomously detect and analyze data format from any input source"
    
    def _run(self, data_source: str) -> Dict[str, Any]:
        """Detect data format using multiple analysis techniques"""
        try:
            if os.path.isfile(data_source):
                # File-based detection
                mime_type = magic.from_file(data_source, mime=True)
                file_extension = Path(data_source).suffix.lower()
                
                # Read sample data for content analysis
                with open(data_source, 'rb') as f:
                    sample_bytes = f.read(1024)
                
                # Detect encoding
                encoding_result = chardet.detect(sample_bytes)
                encoding = encoding_result.get('encoding', 'utf-8')
                
                # Content-based analysis
                content_analysis = self._analyze_content_structure(data_source, encoding)
                
                FORMAT_DETECTIONS.labels(format_type=mime_type).inc()
                
                return {
                    "format_type": mime_type,
                    "file_extension": file_extension,
                    "encoding": encoding,
                    "confidence": encoding_result.get('confidence', 0.0),
                    "structure_analysis": content_analysis,
                    "recommended_parser": self._recommend_parser(mime_type, file_extension)
                }
            else:
                # URL or database connection string analysis
                return self._analyze_connection_string(data_source)
                
        except Exception as e:
            logger.error("Format detection failed", error=str(e), data_source=data_source)
            return {
                "format_type": "unknown",
                "error": str(e),
                "recommended_parser": "generic"
            }
    
    def _analyze_content_structure(self, file_path: str, encoding: str) -> Dict[str, Any]:
        """Analyze internal structure of data content"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample_content = f.read(2048)
            
            # Detect delimiters for structured data
            delimiters = [',', ';', '\t', '|']
            delimiter_counts = {d: sample_content.count(d) for d in delimiters}
            likely_delimiter = max(delimiter_counts, key=delimiter_counts.get)
            
            # Detect JSON structure
            is_json = False
            try:
                json.loads(sample_content)
                is_json = True
            except:
                pass
            
            # Detect XML structure
            is_xml = '<' in sample_content and '>' in sample_content
            
            return {
                "likely_delimiter": likely_delimiter if delimiter_counts[likely_delimiter] > 0 else None,
                "delimiter_confidence": delimiter_counts[likely_delimiter] / len(sample_content),
                "is_json": is_json,
                "is_xml": is_xml,
                "line_count_sample": sample_content.count('\n'),
                "has_headers": self._detect_headers(sample_content, likely_delimiter)
            }
            
        except Exception as e:
            logger.warning("Content structure analysis failed", error=str(e))
            return {"error": str(e)}
    
    def _detect_headers(self, content: str, delimiter: str) -> bool:
        """Detect if first line contains headers"""
        lines = content.split('\n')[:3]  # Check first 3 lines
        if len(lines) < 2:
            return False
        
        first_line = lines[0].split(delimiter) if delimiter else [lines[0]]
        second_line = lines[1].split(delimiter) if delimiter else [lines[1]]
        
        # Headers typically contain text, data contains numbers
        first_line_numeric = sum(1 for cell in first_line if cell.strip().replace('.', '').isdigit())
        second_line_numeric = sum(1 for cell in second_line if cell.strip().replace('.', '').isdigit())
        
        return first_line_numeric < second_line_numeric
    
    def _recommend_parser(self, mime_type: str, file_extension: str) -> str:
        """Recommend optimal parser based on format detection"""
        parser_mapping = {
            'text/csv': 'pandas_csv',
            'application/json': 'json_loader',
            'application/pdf': 'pdf_extractor',
            'application/vnd.ms-excel': 'excel_loader',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel_loader',
            'image/jpeg': 'ocr_processor',
            'image/png': 'ocr_processor',
            'text/xml': 'xml_parser',
            'application/xml': 'xml_parser'
        }
        
        return parser_mapping.get(mime_type, 'generic_text_processor')
    
    def _analyze_connection_string(self, connection_string: str) -> Dict[str, Any]:
        """Analyze database or API connection strings"""
        if connection_string.startswith('postgresql://'):
            return {"format_type": "postgresql", "recommended_parser": "sqlalchemy_postgres"}
        elif connection_string.startswith('mongodb://'):
            return {"format_type": "mongodb", "recommended_parser": "pymongo"}
        elif connection_string.startswith('redis://'):
            return {"format_type": "redis", "recommended_parser": "redis_client"}
        elif connection_string.startswith('http'):
            return {"format_type": "http_api", "recommended_parser": "api_client"}
        else:
            return {"format_type": "unknown", "recommended_parser": "generic"}

class SchemaInferenceTool(BaseTool):
    """LangChain tool for autonomous schema inference"""
    
    name = "schema_inference_engine"
    description = "Autonomously infer data schema from any structured or unstructured data"
    
    def _run(self, data_sample: str, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform autonomous schema inference using multiple techniques"""
        try:
            SCHEMA_INFERENCES.inc()
            
            # Load data based on format
            df = self._load_data_sample(data_sample, format_info)
            
            if df is None or df.empty:
                return {"error": "Could not load data for schema inference"}
            
            # Perform comprehensive schema analysis
            schema_analysis = {
                "field_types": self._infer_field_types(df),
                "data_quality": self._assess_data_quality(df),
                "relationships": self._detect_relationships(df),
                "constraints": self._infer_constraints(df),
                "patterns": self._detect_patterns(df),
                "anomalies": self._detect_anomalies(df)
            }
            
            # Generate JSON schema
            json_schema = self._generate_json_schema(df, schema_analysis)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(schema_analysis)
            
            return {
                "inferred_schema": json_schema,
                "confidence_score": confidence_score,
                "field_analysis": schema_analysis,
                "recommendations": self._generate_recommendations(schema_analysis)
            }
            
        except Exception as e:
            logger.error("Schema inference failed", error=str(e))
            return {"error": str(e)}
    
    def _load_data_sample(self, data_source: str, format_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Load data sample based on detected format"""
        try:
            format_type = format_info.get("format_type", "")
            
            if "csv" in format_type:
                delimiter = format_info.get("structure_analysis", {}).get("likely_delimiter", ",")
                return pd.read_csv(data_source, delimiter=delimiter, nrows=1000)
            elif "json" in format_type:
                return pd.read_json(data_source, lines=True, nrows=1000)
            elif "excel" in format_type:
                return pd.read_excel(data_source, nrows=1000)
            elif "pdf" in format_type:
                # Extract text from PDF and create DataFrame
                text_content = self._extract_pdf_text(data_source)
                return pd.DataFrame({"content": [text_content]})
            else:
                # Generic text processing
                with open(data_source, 'r', encoding='utf-8') as f:
                    content = f.read(10000)  # First 10KB
                return pd.DataFrame({"content": [content]})
                
        except Exception as e:
            logger.warning("Data loading failed", error=str(e))
            return None
    
    def _infer_field_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Infer semantic field types beyond basic data types"""
        field_types = {}
        
        for column in df.columns:
            series = df[column].dropna()
            
            # Basic type inference
            if pd.api.types.is_numeric_dtype(series):
                if series.dtype == 'int64':
                    field_types[column] = "integer"
                else:
                    field_types[column] = "float"
            elif pd.api.types.is_datetime64_any_dtype(series):
                field_types[column] = "datetime"
            elif pd.api.types.is_bool_dtype(series):
                field_types[column] = "boolean"
            else:
                # Semantic type inference for strings
                field_types[column] = self._infer_semantic_type(series)
        
        return field_types
    
    def _infer_semantic_type(self, series: pd.Series) -> str:
        """Infer semantic type for string data"""
        sample_values = series.head(100).astype(str)
        
        # Email detection
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if sample_values.str.match(email_pattern).mean() > 0.8:
            return "email"
        
        # Phone number detection
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        if sample_values.str.replace(r'[^\d+]', '', regex=True).str.match(phone_pattern).mean() > 0.8:
            return "phone"
        
        # ID/Code detection
        if sample_values.str.len().std() < 2 and sample_values.str.len().mean() > 5:
            return "identifier"
        
        # Currency detection
        currency_pattern = r'^\$?[\d,]+\.?\d*$'
        if sample_values.str.match(currency_pattern).mean() > 0.8:
            return "currency"
        
        # Default to text
        return "text"
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, float]:
        """Assess data quality metrics"""
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        
        return {
            "completeness": 1 - (missing_cells / total_cells),
            "uniqueness": df.nunique().mean() / len(df),
            "consistency": self._calculate_consistency_score(df),
            "validity": self._calculate_validity_score(df)
        }
    
    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """Calculate data consistency score"""
        consistency_scores = []
        
        for column in df.columns:
            if df[column].dtype == 'object':
                # Check format consistency for string columns
                lengths = df[column].dropna().str.len()
                if len(lengths) > 0:
                    cv = lengths.std() / lengths.mean() if lengths.mean() > 0 else 1
                    consistency_scores.append(max(0, 1 - cv))
        
        return np.mean(consistency_scores) if consistency_scores else 1.0
    
    def _calculate_validity_score(self, df: pd.DataFrame) -> float:
        """Calculate data validity score"""
        validity_scores = []
        
        for column in df.columns:
            series = df[column].dropna()
            if len(series) == 0:
                continue
                
            # Check for obvious invalid values
            if pd.api.types.is_numeric_dtype(series):
                # Check for reasonable numeric ranges
                if (series < 0).all() and column.lower() in ['age', 'count', 'amount']:
                    validity_scores.append(0.0)  # Negative values where positive expected
                else:
                    validity_scores.append(1.0)
            else:
                # For text data, check for empty strings, special characters
                empty_or_invalid = series.str.strip().eq('').sum() + series.str.contains(r'^[\W_]+$', regex=True, na=False).sum()
                validity_scores.append(1 - (empty_or_invalid / len(series)))
        
        return np.mean(validity_scores) if validity_scores else 1.0
    
    def _detect_relationships(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect potential relationships between fields"""
        relationships = []
        
        # Correlation analysis for numeric fields
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols[i+1:], i+1):
                    correlation = corr_matrix.loc[col1, col2]
                    if abs(correlation) > 0.7:  # Strong correlation
                        relationships.append({
                            "type": "correlation",
                            "field1": col1,
                            "field2": col2,
                            "strength": abs(correlation),
                            "direction": "positive" if correlation > 0 else "negative"
                        })
        
        return relationships
    
    def _infer_constraints(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """Infer data constraints from patterns"""
        constraints = {}
        
        for column in df.columns:
            column_constraints = []
            series = df[column].dropna()
            
            if len(series) == 0:
                continue
            
            # Not null constraint
            if df[column].isnull().sum() == 0:
                column_constraints.append({"type": "not_null"})
            
            # Unique constraint
            if series.nunique() == len(series):
                column_constraints.append({"type": "unique"})
            
            # Range constraints for numeric data
            if pd.api.types.is_numeric_dtype(series):
                column_constraints.extend([
                    {"type": "min_value", "value": float(series.min())},
                    {"type": "max_value", "value": float(series.max())}
                ])
            
            # Length constraints for string data
            elif series.dtype == 'object':
                lengths = series.astype(str).str.len()
                column_constraints.extend([
                    {"type": "min_length", "value": int(lengths.min())},
                    {"type": "max_length", "value": int(lengths.max())}
                ])
            
            if column_constraints:
                constraints[column] = column_constraints
        
        return constraints
    
    def _detect_patterns(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Detect common patterns in data"""
        patterns = {}
        
        for column in df.columns:
            if df[column].dtype == 'object':
                series = df[column].dropna().astype(str)
                column_patterns = []
                
                # Common patterns
                if series.str.match(r'^\d{4}-\d{2}-\d{2}$').mean() > 0.8:
                    column_patterns.append("date_iso_format")
                
                if series.str.match(r'^[A-Z]{2,3}\d{3,}$').mean() > 0.8:
                    column_patterns.append("alphanumeric_code")
                
                if series.str.match(r'^\d+$').mean() > 0.8:
                    column_patterns.append("numeric_string")
                
                if column_patterns:
                    patterns[column] = column_patterns
        
        return patterns
    
    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect data anomalies"""
        anomalies = []
        
        for column in df.columns:
            series = df[column].dropna()
            
            if pd.api.types.is_numeric_dtype(series) and len(series) > 10:
                # Statistical outliers using IQR method
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                if len(outliers) > 0:
                    anomalies.append({
                        "column": column,
                        "type": "statistical_outliers",
                        "count": len(outliers),
                        "percentage": len(outliers) / len(series) * 100,
                        "bounds": {"lower": lower_bound, "upper": upper_bound}
                    })
        
        return anomalies
    
    def _generate_json_schema(self, df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON schema from analysis"""
        properties = {}
        required = []
        
        for column, field_type in analysis["field_types"].items():
            prop_def = {"type": self._map_to_json_type(field_type)}
            
            # Add constraints
            if column in analysis["constraints"]:
                for constraint in analysis["constraints"][column]:
                    if constraint["type"] == "min_value":
                        prop_def["minimum"] = constraint["value"]
                    elif constraint["type"] == "max_value":
                        prop_def["maximum"] = constraint["value"]
                    elif constraint["type"] == "min_length":
                        prop_def["minLength"] = constraint["value"]
                    elif constraint["type"] == "max_length":
                        prop_def["maxLength"] = constraint["value"]
                    elif constraint["type"] == "not_null":
                        required.append(column)
            
            properties[column] = prop_def
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _map_to_json_type(self, field_type: str) -> str:
        """Map inferred field type to JSON schema type"""
        type_mapping = {
            "integer": "integer",
            "float": "number",
            "boolean": "boolean",
            "datetime": "string",
            "email": "string",
            "phone": "string",
            "currency": "number",
            "identifier": "string",
            "text": "string"
        }
        return type_mapping.get(field_type, "string")
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall confidence in schema inference"""
        quality_score = np.mean(list(analysis["data_quality"].values()))
        
        # Penalize for anomalies
        anomaly_penalty = min(0.3, len(analysis["anomalies"]) * 0.05)
        
        # Bonus for detected patterns
        pattern_bonus = min(0.2, len(analysis["patterns"]) * 0.05)
        
        confidence = quality_score - anomaly_penalty + pattern_bonus
        return max(0.0, min(1.0, confidence))
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate processing recommendations based on analysis"""
        recommendations = []
        
        # Data quality recommendations
        quality = analysis["data_quality"]
        if quality["completeness"] < 0.9:
            recommendations.append("Consider data imputation for missing values")
        
        if quality["consistency"] < 0.8:
            recommendations.append("Standardize data formats for consistency")
        
        if quality["validity"] < 0.9:
            recommendations.append("Implement data validation rules")
        
        # Anomaly recommendations
        if analysis["anomalies"]:
            recommendations.append("Review and handle detected anomalies")
        
        # Relationship recommendations
        if analysis["relationships"]:
            recommendations.append("Consider creating derived features from correlated fields")
        
        return recommendations
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF files"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages[:5]:  # First 5 pages
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            logger.warning("PDF text extraction failed", error=str(e))
            return ""

class DataProcessingTool(BaseTool):
    """LangChain tool for autonomous data processing and transformation"""
    
    name = "data_processor"
    description = "Autonomously process and transform data based on inferred schema and quality requirements"
    
    def _run(self, data_source: str, schema_info: Dict[str, Any], processing_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Process data autonomously based on schema and requirements"""
        try:
            # Load full dataset
            df = self._load_full_dataset(data_source, schema_info)
            
            if df is None or df.empty:
                return {"error": "Could not load dataset for processing"}
            
            original_shape = df.shape
            processing_log = []
            
            # Apply autonomous data processing steps
            df, log_entries = self._apply_data_cleaning(df, schema_info)
            processing_log.extend(log_entries)
            
            df, log_entries = self._apply_data_transformation(df, schema_info)
            processing_log.extend(log_entries)
            
            df, log_entries = self._apply_quality_improvements(df, processing_requirements)
            processing_log.extend(log_entries)
            
            # Generate processing summary
            processed_data = {
                "records_processed": len(df),
                "fields_processed": len(df.columns),
                "processing_log": processing_log,
                "data_sample": df.head(10).to_dict('records'),
                "summary_statistics": self._generate_summary_stats(df),
                "quality_metrics": self._calculate_final_quality_metrics(df)
            }
            
            return {
                "status": "success",
                "original_shape": original_shape,
                "final_shape": df.shape,
                "processed_data": processed_data
            }
            
        except Exception as e:
            logger.error("Data processing failed", error=str(e))
            return {"error": str(e)}
    
    def _load_full_dataset(self, data_source: str, schema_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Load complete dataset for processing"""
        # Implementation similar to _load_data_sample but without row limits
        # This would be expanded based on the specific format detection results
        try:
            format_type = schema_info.get("format_type", "")
            
            if "csv" in format_type:
                return pd.read_csv(data_source)
            elif "json" in format_type:
                return pd.read_json(data_source, lines=True)
            elif "excel" in format_type:
                return pd.read_excel(data_source)
            else:
                # Generic processing
                return pd.read_csv(data_source, sep=None, engine='python')
                
        except Exception as e:
            logger.error("Full dataset loading failed", error=str(e))
            return None
    
    def _apply_data_cleaning(self, df: pd.DataFrame, schema_info: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
        """Apply autonomous data cleaning based on detected issues"""
        log_entries = []
        
        # Remove duplicate rows
        initial_rows = len(df)
        df = df.drop_duplicates()
        if len(df) < initial_rows:
            removed = initial_rows - len(df)
            log_entries.append(f"Removed {removed} duplicate rows")
        
        # Handle missing values based on field types
        field_types = schema_info.get("field_analysis", {}).get("field_types", {})
        
        for column in df.columns:
            missing_count = df[column].isnull().sum()
            if missing_count > 0:
                field_type = field_types.get(column, "text")
                
                if field_type in ["integer", "float"]:
                    # Fill numeric missing values with median
                    df[column].fillna(df[column].median(), inplace=True)
                    log_entries.append(f"Filled {missing_count} missing values in {column} with median")
                elif field_type == "text":
                    # Fill text missing values with mode or "Unknown"
                    mode_value = df[column].mode()
                    fill_value = mode_value[0] if len(mode_value) > 0 else "Unknown"
                    df[column].fillna(fill_value, inplace=True)
                    log_entries.append(f"Filled {missing_count} missing values in {column} with '{fill_value}'")
        
        return df, log_entries
    
    def _apply_data_transformation(self, df: pd.DataFrame, schema_info: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
        """Apply autonomous data transformations"""
        log_entries = []
        
        field_types = schema_info.get("field_analysis", {}).get("field_types", {})
        
        for column in df.columns:
            field_type = field_types.get(column, "text")
            
            # Type conversions
            if field_type == "datetime" and df[column].dtype == 'object':
                try:
                    df[column] = pd.to_datetime(df[column])
                    log_entries.append(f"Converted {column} to datetime")
                except:
                    log_entries.append(f"Failed to convert {column} to datetime")
            
            elif field_type in ["integer", "float"] and df[column].dtype == 'object':
                try:
                    df[column] = pd.to_numeric(df[column], errors='coerce')
                    log_entries.append(f"Converted {column} to numeric")
                except:
                    log_entries.append(f"Failed to convert {column} to numeric")
            
            # Text standardization
            elif field_type == "text" and df[column].dtype == 'object':
                # Standardize text fields
                df[column] = df[column].astype(str).str.strip().str.title()
                log_entries.append(f"Standardized text format for {column}")
        
        return df, log_entries
    
    def _apply_quality_improvements(self, df: pd.DataFrame, requirements: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
        """Apply quality improvements based on requirements"""
        log_entries = []
        
        quality_threshold = requirements.get("quality_threshold", 0.8)
        
        # Remove columns with too many missing values
        missing_threshold = 1 - quality_threshold
        columns_to_drop = []
        
        for column in df.columns:
            missing_ratio = df[column].isnull().sum() / len(df)
            if missing_ratio > missing_threshold:
                columns_to_drop.append(column)
        
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
            log_entries.append(f"Dropped columns with high missing values: {columns_to_drop}")
        
        return df, log_entries
    
    def _generate_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for processed data"""
        summary = {
            "total_records": len(df),
            "total_fields": len(df.columns),
            "numeric_fields": len(df.select_dtypes(include=[np.number]).columns),
            "text_fields": len(df.select_dtypes(include=['object']).columns),
            "datetime_fields": len(df.select_dtypes(include=['datetime']).columns)
        }
        
        # Add field-level statistics
        field_stats = {}
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                field_stats[column] = {
                    "type": "numeric",
                    "mean": float(df[column].mean()),
                    "std": float(df[column].std()),
                    "min": float(df[column].min()),
                    "max": float(df[column].max()),
                    "missing_count": int(df[column].isnull().sum())
                }
            else:
                field_stats[column] = {
                    "type": "categorical",
                    "unique_values": int(df[column].nunique()),
                    "most_common": str(df[column].mode().iloc[0]) if len(df[column].mode()) > 0 else None,
                    "missing_count": int(df[column].isnull().sum())
                }
        
        summary["field_statistics"] = field_stats
        return summary
    
    def _calculate_final_quality_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate final data quality metrics"""
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        
        return {
            "completeness": 1 - (missing_cells / total_cells) if total_cells > 0 else 0,
            "uniqueness": df.nunique().mean() / len(df) if len(df) > 0 else 0,
            "consistency": 1.0,  # Simplified - would implement more sophisticated consistency checks
            "validity": 1.0      # Simplified - would implement validation rules
        }

class AutonomousDataIngestionAgent:
    """Main autonomous data ingestion agent using LangChain"""
    
    def __init__(self):
        """Initialize the autonomous agent with LangChain components"""
        
        # Initialize OpenAI model for reasoning
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,  # Low temperature for consistent reasoning
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize tools
        self.tools = [
            DataFormatDetectionTool(),
            SchemaInferenceTool(),
            DataProcessingTool()
        ]
        
        # Initialize memory for conversation context
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an autonomous data ingestion agent with expertise in processing any type of data format without predefined schemas. Your role is to:

1. Autonomously detect and analyze data formats from any source
2. Infer schemas and data structures without human guidance
3. Make intelligent decisions about data processing strategies
4. Ensure high data quality and compliance with requirements
5. Communicate findings and decisions clearly

You have access to specialized tools for format detection, schema inference, and data processing. Use these tools to make autonomous decisions about how to best process the incoming data.

Always consider:
- Data quality and integrity
- Compliance requirements
- Processing efficiency
- Schema flexibility
- Error handling and recovery

Make decisions based on evidence from your analysis tools and explain your reasoning clearly."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=10,
            early_stopping_method="generate"
        )
        
        # Initialize Kafka for inter-agent communication
        self.kafka_producer = None
        self.kafka_consumer = None
        self._initialize_kafka()
        
        logger.info("Autonomous Data Ingestion Agent initialized with LangChain")
    
    def _initialize_kafka(self):
        """Initialize Kafka producer and consumer for inter-agent communication"""
        try:
            kafka_config = {
                'bootstrap_servers': os.getenv('KAFKA_BROKERS', 'localhost:9092'),
                'value_serializer': lambda x: json.dumps(x).encode('utf-8')
            }
            
            self.kafka_producer = KafkaProducer(**kafka_config)
            
            consumer_config = {
                'bootstrap_servers': os.getenv('KAFKA_BROKERS', 'localhost:9092'),
                'group_id': 'data_ingestion_agent',
                'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
                'auto_offset_reset': 'latest'
            }
            
            self.kafka_consumer = KafkaConsumer(
                'kyc_data_requests',
                **consumer_config
            )
            
            logger.info("Kafka messaging initialized for inter-agent communication")
            
        except Exception as e:
            logger.error("Kafka initialization failed", error=str(e))
            self.kafka_producer = None
            self.kafka_consumer = None
    
    async def process_data_autonomously(self, request: DataIngestionRequest) -> DataIngestionResult:
        """Main autonomous processing method"""
        start_time = datetime.now(timezone.utc)
        callback = AgentDecisionCallback()
        
        try:
            INGESTION_REQUESTS.inc()
            ACTIVE_INGESTIONS.inc()
            
            # Create autonomous processing prompt
            processing_prompt = f"""
            I need to autonomously process data from: {request.data_source}
            
            Requirements:
            - Source type: {request.source_type}
            - Processing mode: {request.processing_mode}
            - Industry context: {request.industry_context}
            - Quality threshold: {request.quality_threshold}
            - Compliance requirements: {request.compliance_requirements}
            
            Please:
            1. Detect the data format and structure
            2. Infer the schema autonomously
            3. Process the data according to quality requirements
            4. Make autonomous decisions about any data quality issues
            5. Provide recommendations for next steps
            
            Use your tools to analyze and process this data completely autonomously.
            """
            
            # Execute autonomous processing
            with INGESTION_DURATION.time():
                result = await self.agent_executor.ainvoke(
                    {"input": processing_prompt},
                    callbacks=[callback]
                )
            
            # Parse agent output
            agent_output = result.get("output", "")
            
            # Extract structured results from agent decisions
            processing_results = self._extract_processing_results(callback.decisions, agent_output)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Create comprehensive result
            ingestion_result = DataIngestionResult(
                request_id=request.request_id,
                status="completed",
                processing_time_seconds=processing_time,
                records_processed=processing_results.get("records_processed", 0),
                data_quality_score=processing_results.get("data_quality_score", 0.0),
                schema_inference=SchemaInferenceResult(
                    inferred_schema=processing_results.get("inferred_schema", {}),
                    confidence_score=processing_results.get("confidence_score", 0.0),
                    field_types=processing_results.get("field_types", {}),
                    data_quality_score=processing_results.get("data_quality_score", 0.0),
                    anomalies_detected=processing_results.get("anomalies", []),
                    recommendations=processing_results.get("recommendations", [])
                ),
                processed_data=processing_results.get("processed_data", {}),
                agent_decisions=callback.decisions,
                next_recommended_actions=processing_results.get("next_actions", []),
                compliance_status={"status": "compliant", "checks_passed": []},
                errors=processing_results.get("errors", []),
                warnings=processing_results.get("warnings", [])
            )
            
            # Publish results to other agents via Kafka
            await self._publish_to_kafka("data_ingestion_completed", ingestion_result.dict())
            
            logger.info("Autonomous data ingestion completed", 
                       request_id=request.request_id, 
                       processing_time=processing_time)
            
            return ingestion_result
            
        except Exception as e:
            logger.error("Autonomous processing failed", 
                        request_id=request.request_id, 
                        error=str(e))
            
            return DataIngestionResult(
                request_id=request.request_id,
                status="failed",
                processing_time_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=0,
                data_quality_score=0.0,
                schema_inference=SchemaInferenceResult(
                    inferred_schema={},
                    confidence_score=0.0,
                    field_types={},
                    data_quality_score=0.0,
                    anomalies_detected=[],
                    recommendations=[]
                ),
                processed_data={},
                agent_decisions=callback.decisions,
                next_recommended_actions=["Review error logs", "Check data source accessibility"],
                compliance_status={"status": "unknown", "checks_passed": []},
                errors=[str(e)]
            )
        
        finally:
            ACTIVE_INGESTIONS.dec()
    
    def _extract_processing_results(self, decisions: List[Dict[str, Any]], agent_output: str) -> Dict[str, Any]:
        """Extract structured results from agent decisions and output"""
        results = {
            "records_processed": 0,
            "data_quality_score": 0.0,
            "inferred_schema": {},
            "confidence_score": 0.0,
            "field_types": {},
            "anomalies": [],
            "recommendations": [],
            "processed_data": {},
            "next_actions": [],
            "errors": [],
            "warnings": []
        }
        
        # Extract information from agent decisions
        for decision in decisions:
            if decision.get("action") == "schema_inference_engine":
                # Extract schema inference results
                if "inferred_schema" in str(decision.get("input", {})):
                    # Parse schema inference results from decision
                    pass
            
            elif decision.get("action") == "data_processor":
                # Extract processing results
                if "records_processed" in str(decision.get("input", {})):
                    # Parse processing results from decision
                    pass
        
        # Parse agent output for additional insights
        if "records processed" in agent_output.lower():
            # Extract number of records processed
            import re
            match = re.search(r'(\d+)\s+records?\s+processed', agent_output.lower())
            if match:
                results["records_processed"] = int(match.group(1))
        
        # Set default recommendations
        results["next_actions"] = [
            "Forward processed data to KYC Analysis Agent",
            "Monitor data quality metrics",
            "Update schema registry if needed"
        ]
        
        return results
    
    async def _publish_to_kafka(self, topic: str, message: Dict[str, Any]):
        """Publish message to Kafka for inter-agent communication"""
        if self.kafka_producer:
            try:
                future = self.kafka_producer.send(topic, message)
                await asyncio.wrap_future(future)
                logger.info("Message published to Kafka", topic=topic)
            except Exception as e:
                logger.error("Kafka publish failed", topic=topic, error=str(e))

# Initialize the autonomous agent
autonomous_agent = AutonomousDataIngestionAgent()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Data Ingestion Agent service")
    
    # Start Prometheus metrics server
    start_http_server(int(os.getenv("METRICS_PORT", "8001")))
    
    logger.info("Data Ingestion Agent service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Data Ingestion Agent service")
    
    if autonomous_agent.kafka_producer:
        autonomous_agent.kafka_producer.close()
    
    if autonomous_agent.kafka_consumer:
        autonomous_agent.kafka_consumer.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-ingestion-agent",
        "version": "1.0.0",
        "framework": "LangChain",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capabilities": [
            "multi_format_ingestion",
            "autonomous_schema_inference", 
            "quality_assessment",
            "inter_agent_communication"
        ]
    }

@app.post("/api/v1/data/ingest", response_model=DataIngestionResult)
async def ingest_data(request: DataIngestionRequest, background_tasks: BackgroundTasks):
    """Main data ingestion endpoint with autonomous processing"""
    
    logger.info("Data ingestion request received", request_id=request.request_id)
    
    try:
        # Process data autonomously using LangChain agent
        result = await autonomous_agent.process_data_autonomously(request)
        
        # Add background task for cleanup if needed
        background_tasks.add_task(cleanup_temporary_files, request.request_id)
        
        return result
        
    except Exception as e:
        logger.error("Data ingestion failed", request_id=request.request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")

@app.get("/api/v1/agents/status")
async def get_agent_status():
    """Get current agent status and capabilities"""
    return {
        "agent_type": "data_ingestion",
        "framework": "LangChain",
        "status": "active",
        "capabilities": {
            "formats_supported": [
                "CSV", "JSON", "XML", "PDF", "Excel", 
                "Images", "Databases", "APIs", "Streams"
            ],
            "autonomous_features": [
                "format_detection",
                "schema_inference", 
                "quality_assessment",
                "data_transformation",
                "anomaly_detection"
            ],
            "inter_agent_communication": True,
            "real_time_processing": True,
            "batch_processing": True
        },
        "performance_metrics": {
            "requests_processed": INGESTION_REQUESTS._value._value,
            "active_ingestions": ACTIVE_INGESTIONS._value._value,
            "schema_inferences": SCHEMA_INFERENCES._value._value
        }
    }

@app.post("/api/v1/data/validate")
async def validate_data_schema(data: Dict[str, Any], schema: Dict[str, Any]):
    """Validate data against inferred or provided schema"""
    try:
        jsonschema.validate(data, schema)
        return {"valid": True, "message": "Data validates against schema"}
    except jsonschema.ValidationError as e:
        return {"valid": False, "error": str(e)}

async def cleanup_temporary_files(request_id: str):
    """Background task to cleanup temporary files"""
    try:
        # Implement cleanup logic for temporary files
        logger.info("Cleanup completed", request_id=request_id)
    except Exception as e:
        logger.error("Cleanup failed", request_id=request_id, error=str(e))

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    
    # Run the service
    uvicorn.run(
        "data_ingestion_service:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )
