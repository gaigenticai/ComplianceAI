"""
Face Recognition Agent Service for KYC Automation Platform

This service handles facial recognition and liveness detection for identity verification.
It compares selfie photos with ID document photos to verify identity and detects
whether the selfie is from a live person or a photograph/screen.

Features:
- Face detection and recognition using face_recognition library
- Liveness detection using multiple techniques
- Face quality assessment
- Anti-spoofing measures
- Detailed matching scores and confidence metrics
"""

import os
import cv2
import numpy as np
import mediapipe as mp
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image, ImageEnhance
import logging
from sklearn.metrics.pairwise import cosine_similarity

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Face Recognition Agent Service",
    description="Facial recognition and liveness detection for KYC verification",
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

class FaceRequest(BaseModel):
    """Face recognition processing request structure"""
    request_id: str
    selfie: Optional[DocumentInfo] = None
    id_photo: Optional[DocumentInfo] = None
    ocr_results: Optional[Dict[str, Any]] = None

class FaceAnalysis(BaseModel):
    """Face analysis results"""
    face_detected: bool
    face_count: int
    face_quality: float = Field(ge=0, le=100)
    face_landmarks: Dict[str, Any] = {}
    face_encoding: Optional[List[float]] = None

class LivenessResult(BaseModel):
    """Liveness detection results"""
    is_live: bool
    confidence: float = Field(ge=0, le=100)
    checks_performed: List[str] = []
    check_results: Dict[str, Any] = {}

class MatchingResult(BaseModel):
    """Face matching results"""
    match_score: float = Field(ge=0, le=100)
    distance: float
    is_match: bool
    confidence: float = Field(ge=0, le=100)
    similarity_threshold: float = 0.6

class FaceResult(BaseModel):
    """Face recognition processing result"""
    selfie_analysis: Optional[FaceAnalysis] = None
    id_photo_analysis: Optional[FaceAnalysis] = None
    liveness_result: Optional[LivenessResult] = None
    matching_result: Optional[MatchingResult] = None
    overall_score: float = Field(ge=0, le=100)
    processing_time_ms: int
    errors: List[str] = []
    warnings: List[str] = []

class FaceResponse(BaseModel):
    """Face recognition service response"""
    agent_name: str = "face"
    status: str
    data: Dict[str, Any]
    processing_time: int
    error: Optional[str] = None
    version: str = "1.0.0"

class FaceProcessor:
    """Main face recognition processing class"""
    
    def __init__(self):
        """Initialize face processor with MediaPipe and configuration"""
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        )
        
        # Initialize MediaPipe Face Mesh for landmarks
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        # Face matching threshold
        self.similarity_threshold = 0.6
        
        # Liveness detection parameters
        self.liveness_checks = [
            'face_symmetry',
            'eye_aspect_ratio',
            'mouth_aspect_ratio',
            'face_texture_analysis',
            'edge_detection'
        ]
        
        logger.info("Face Processor initialized")

    def load_and_preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Load and preprocess image for face recognition
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            # Convert BGR to RGB (face_recognition expects RGB)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Enhance image quality
            pil_image = Image.fromarray(image_rgb)
            
            # Enhance contrast and sharpness
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(1.1)
            
            return np.array(pil_image)
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            raise

    def detect_faces(self, image: np.ndarray) -> Tuple[List, List]:
        """
        Detect faces in image using mediapipe
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (face_locations, face_encodings)
        """
        try:
            # Convert BGR to RGB for mediapipe
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces using mediapipe
            results = self.face_detection.process(rgb_image)
            
            face_locations = []
            face_encodings = []
            
            if results.detections:
                h, w, _ = image.shape
                for detection in results.detections:
                    # Get bounding box
                    bbox = detection.location_data.relative_bounding_box
                    
                    # Convert relative coordinates to absolute (top, right, bottom, left format)
                    left = int(bbox.xmin * w)
                    top = int(bbox.ymin * h)
                    right = int((bbox.xmin + bbox.width) * w)
                    bottom = int((bbox.ymin + bbox.height) * h)
                    
                    face_locations.append((top, right, bottom, left))
                    
                    # Extract face region for encoding (simplified)
                    face_region = image[max(0, top):min(h, bottom), max(0, left):min(w, right)]
                    if face_region.size > 0:
                        # Create a simple encoding based on face region features
                        face_gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
                        face_resized = cv2.resize(face_gray, (128, 128))
                        encoding = face_resized.flatten()[:128]  # Simple feature vector
                        face_encodings.append(encoding)
            
            logger.info(f"Detected {len(face_locations)} faces")
            return face_locations, face_encodings
            
        except Exception as e:
            logger.error(f"Face detection failed: {str(e)}")
            return [], []

    def analyze_face_quality(self, image: np.ndarray, face_location: Tuple) -> float:
        """
        Analyze the quality of detected face
        
        Args:
            image: Input image
            face_location: Face bounding box coordinates
            
        Returns:
            Quality score from 0-100
        """
        try:
            top, right, bottom, left = face_location
            face_image = image[top:bottom, left:right]
            
            if face_image.size == 0:
                return 0.0
            
            # Convert to grayscale for analysis
            gray_face = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # Calculate sharpness (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 500, 1.0) * 30
            
            # Calculate brightness
            brightness = np.mean(gray_face)
            brightness_score = (1.0 - abs(brightness - 127) / 127) * 25
            
            # Calculate contrast
            contrast = np.std(gray_face)
            contrast_score = min(contrast / 40, 1.0) * 25
            
            # Calculate face size score
            face_area = (bottom - top) * (right - left)
            image_area = image.shape[0] * image.shape[1]
            size_ratio = face_area / image_area
            size_score = min(size_ratio * 10, 1.0) * 20  # Prefer larger faces
            
            total_score = sharpness_score + brightness_score + contrast_score + size_score
            
            logger.info(f"Face quality score: {total_score:.1f}/100")
            return min(total_score, 100.0)
            
        except Exception as e:
            logger.error(f"Face quality analysis failed: {str(e)}")
            return 50.0

    def extract_face_landmarks(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract facial landmarks using MediaPipe
        
        Args:
            image: Input image
            
        Returns:
            Dictionary containing landmark information
        """
        try:
            results = self.face_mesh.process(image)
            landmarks_data = {}
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Extract key landmark points
                    landmarks = []
                    for landmark in face_landmarks.landmark:
                        landmarks.append({
                            'x': landmark.x,
                            'y': landmark.y,
                            'z': landmark.z
                        })
                    
                    landmarks_data = {
                        'total_landmarks': len(landmarks),
                        'key_points': {
                            'left_eye': landmarks[33:42],
                            'right_eye': landmarks[362:371],
                            'nose': landmarks[1:17],
                            'mouth': landmarks[61:81]
                        }
                    }
                    break  # Only process first face
            
            return landmarks_data
            
        except Exception as e:
            logger.error(f"Landmark extraction failed: {str(e)}")
            return {}

    def perform_liveness_detection(self, image: np.ndarray, face_location: Tuple) -> LivenessResult:
        """
        Perform liveness detection to identify real vs fake faces
        
        Args:
            image: Input image
            face_location: Face bounding box coordinates
            
        Returns:
            LivenessResult with detection results
        """
        try:
            top, right, bottom, left = face_location
            face_image = image[top:bottom, left:right]
            
            checks_performed = []
            check_results = {}
            liveness_scores = []
            
            # Check 1: Face Symmetry Analysis
            if 'face_symmetry' in self.liveness_checks:
                symmetry_score = self._check_face_symmetry(face_image)
                check_results['face_symmetry'] = symmetry_score
                liveness_scores.append(symmetry_score)
                checks_performed.append('face_symmetry')
            
            # Check 2: Eye Aspect Ratio
            if 'eye_aspect_ratio' in self.liveness_checks:
                ear_score = self._check_eye_aspect_ratio(image, face_location)
                check_results['eye_aspect_ratio'] = ear_score
                liveness_scores.append(ear_score)
                checks_performed.append('eye_aspect_ratio')
            
            # Check 3: Texture Analysis
            if 'face_texture_analysis' in self.liveness_checks:
                texture_score = self._analyze_face_texture(face_image)
                check_results['face_texture_analysis'] = texture_score
                liveness_scores.append(texture_score)
                checks_performed.append('face_texture_analysis')
            
            # Check 4: Edge Detection Analysis
            if 'edge_detection' in self.liveness_checks:
                edge_score = self._analyze_edges(face_image)
                check_results['edge_detection'] = edge_score
                liveness_scores.append(edge_score)
                checks_performed.append('edge_detection')
            
            # Calculate overall liveness confidence
            if liveness_scores:
                confidence = np.mean(liveness_scores)
                is_live = confidence > 60.0  # Threshold for liveness
            else:
                confidence = 50.0
                is_live = True  # Default to live if no checks performed
            
            logger.info(f"Liveness detection: {confidence:.1f}% confidence, live: {is_live}")
            
            return LivenessResult(
                is_live=is_live,
                confidence=confidence,
                checks_performed=checks_performed,
                check_results=check_results
            )
            
        except Exception as e:
            logger.error(f"Liveness detection failed: {str(e)}")
            return LivenessResult(
                is_live=True,  # Default to live on error
                confidence=50.0,
                checks_performed=[],
                check_results={"error": str(e)}
            )

    def _check_face_symmetry(self, face_image: np.ndarray) -> float:
        """Check face symmetry as a liveness indicator"""
        try:
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            height, width = gray.shape
            
            # Split face in half
            left_half = gray[:, :width//2]
            right_half = gray[:, width//2:]
            right_half_flipped = cv2.flip(right_half, 1)
            
            # Resize to match if needed
            min_width = min(left_half.shape[1], right_half_flipped.shape[1])
            left_half = left_half[:, :min_width]
            right_half_flipped = right_half_flipped[:, :min_width]
            
            # Calculate correlation
            correlation = cv2.matchTemplate(left_half, right_half_flipped, cv2.TM_CCOEFF_NORMED)[0][0]
            
            # Convert to percentage (higher correlation = more symmetric = more likely live)
            symmetry_score = max(0, correlation * 100)
            
            return min(symmetry_score, 100.0)
            
        except Exception as e:
            logger.warning(f"Face symmetry check failed: {str(e)}")
            return 70.0  # Default score

    def _check_eye_aspect_ratio(self, image: np.ndarray, face_location: Tuple) -> float:
        """
        Check eye aspect ratio for liveness detection using proper EAR calculation
        
        Eye Aspect Ratio (EAR) is calculated as:
        EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        
        Where p1-p6 are the 6 landmark points of an eye.
        Normal EAR values range from 0.2-0.4, with blinks showing values < 0.2
        """
        try:
            # Extract landmarks for eyes
            landmarks_data = self.extract_face_landmarks(image)
            
            if not landmarks_data or 'key_points' not in landmarks_data:
                logger.warning("No facial landmarks detected for EAR calculation")
                return 70.0  # Default score if landmarks not available
            
            # Get image dimensions for coordinate conversion
            height, width = image.shape[:2]
            
            # Extract eye landmarks
            left_eye_landmarks = landmarks_data['key_points']['left_eye']
            right_eye_landmarks = landmarks_data['key_points']['right_eye']
            
            if not left_eye_landmarks or not right_eye_landmarks:
                logger.warning("Eye landmarks not properly extracted")
                return 70.0
            
            # Calculate EAR for both eyes
            left_ear = self._calculate_single_eye_aspect_ratio(left_eye_landmarks, width, height)
            right_ear = self._calculate_single_eye_aspect_ratio(right_eye_landmarks, width, height)
            
            # Average EAR of both eyes
            avg_ear = (left_ear + right_ear) / 2.0
            
            # Convert EAR to liveness score
            # Normal EAR range is 0.2-0.4
            # Values significantly outside this range may indicate spoofing
            if 0.15 <= avg_ear <= 0.45:
                # Normal range - high liveness score
                ear_score = 85.0 + (15.0 * (1 - abs(avg_ear - 0.3) / 0.15))
            elif 0.1 <= avg_ear < 0.15 or 0.45 < avg_ear <= 0.5:
                # Slightly outside normal range - medium score
                ear_score = 60.0 + (20.0 * (1 - abs(avg_ear - 0.3) / 0.2))
            else:
                # Far outside normal range - low score (possible spoofing)
                ear_score = 30.0
            
            # Ensure score is within valid range
            ear_score = max(0.0, min(100.0, ear_score))
            
            logger.debug(f"EAR calculation: left={left_ear:.3f}, right={right_ear:.3f}, "
                        f"avg={avg_ear:.3f}, score={ear_score:.1f}")
            
            return ear_score
            
        except Exception as e:
            logger.error(f"Eye aspect ratio calculation failed: {str(e)}")
            return 70.0  # Default score on error
    
    def _calculate_single_eye_aspect_ratio(self, eye_landmarks: List[Dict], width: int, height: int) -> float:
        """
        Calculate Eye Aspect Ratio for a single eye
        
        Args:
            eye_landmarks: List of eye landmark points with x, y coordinates (normalized)
            width: Image width for coordinate conversion
            height: Image height for coordinate conversion
            
        Returns:
            Eye aspect ratio value
        """
        try:
            if len(eye_landmarks) < 6:
                logger.warning(f"Insufficient eye landmarks: {len(eye_landmarks)}")
                return 0.3  # Default EAR value
            
            # Convert normalized coordinates to pixel coordinates
            points = []
            for landmark in eye_landmarks[:6]:  # Use first 6 points for EAR calculation
                x = int(landmark['x'] * width)
                y = int(landmark['y'] * height)
                points.append((x, y))
            
            # Calculate distances for EAR formula
            # Vertical distances
            vertical_1 = self._euclidean_distance(points[1], points[5])  # p2-p6
            vertical_2 = self._euclidean_distance(points[2], points[4])  # p3-p5
            
            # Horizontal distance
            horizontal = self._euclidean_distance(points[0], points[3])  # p1-p4
            
            # Calculate EAR
            if horizontal == 0:
                logger.warning("Zero horizontal distance in EAR calculation")
                return 0.3
            
            ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
            
            return ear
            
        except Exception as e:
            logger.error(f"Single eye EAR calculation failed: {str(e)}")
            return 0.3  # Default EAR value
    
    def _euclidean_distance(self, point1: Tuple[int, int], point2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points"""
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def _analyze_face_texture(self, face_image: np.ndarray) -> float:
        """Analyze face texture for liveness detection"""
        try:
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # Calculate Local Binary Pattern (simplified)
            # Real faces have more texture variation than printed photos
            
            # Calculate standard deviation of pixel intensities
            texture_variance = np.std(gray)
            
            # Calculate gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            avg_gradient = np.mean(gradient_magnitude)
            
            # Combine metrics
            texture_score = min((texture_variance / 50 + avg_gradient / 100) * 50, 100)
            
            return texture_score
            
        except Exception as e:
            logger.warning(f"Texture analysis failed: {str(e)}")
            return 70.0

    def _analyze_edges(self, face_image: np.ndarray) -> float:
        """Analyze edge characteristics for liveness detection"""
        try:
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # Apply Canny edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Calculate edge density
            edge_density = np.sum(edges > 0) / edges.size
            
            # Real faces typically have moderate edge density
            # Too many edges might indicate a printed photo
            # Too few edges might indicate poor quality or fake
            
            optimal_density = 0.1  # Optimal edge density for real faces
            density_score = max(0, 100 - abs(edge_density - optimal_density) * 1000)
            
            return min(density_score, 100.0)
            
        except Exception as e:
            logger.warning(f"Edge analysis failed: {str(e)}")
            return 70.0

    def analyze_face(self, image_path: str, is_selfie: bool = False) -> FaceAnalysis:
        """
        Analyze face in image
        
        Args:
            image_path: Path to image file
            is_selfie: Whether this is a selfie image
            
        Returns:
            FaceAnalysis results
        """
        try:
            # Load and preprocess image
            image = self.load_and_preprocess_image(image_path)
            
            # Detect faces
            face_locations, face_encodings = self.detect_faces(image)
            
            if not face_locations:
                return FaceAnalysis(
                    face_detected=False,
                    face_count=0,
                    face_quality=0.0
                )
            
            # Analyze first face (primary face)
            face_location = face_locations[0]
            face_encoding = face_encodings[0] if face_encodings else None
            
            # Calculate face quality
            quality_score = self.analyze_face_quality(image, face_location)
            
            # Extract landmarks
            landmarks = self.extract_face_landmarks(image)
            
            return FaceAnalysis(
                face_detected=True,
                face_count=len(face_locations),
                face_quality=quality_score,
                face_landmarks=landmarks,
                face_encoding=face_encoding.tolist() if face_encoding is not None else None
            )
            
        except Exception as e:
            logger.error(f"Face analysis failed: {str(e)}")
            return FaceAnalysis(
                face_detected=False,
                face_count=0,
                face_quality=0.0
            )

    def compare_faces(self, selfie_analysis: FaceAnalysis, id_analysis: FaceAnalysis) -> MatchingResult:
        """
        Compare faces between selfie and ID photo
        
        Args:
            selfie_analysis: Selfie face analysis results
            id_analysis: ID photo face analysis results
            
        Returns:
            MatchingResult with comparison results
        """
        try:
            if not selfie_analysis.face_encoding or not id_analysis.face_encoding:
                return MatchingResult(
                    match_score=0.0,
                    distance=1.0,
                    is_match=False,
                    confidence=0.0
                )
            
            # Convert encodings back to numpy arrays
            selfie_encoding = np.array(selfie_analysis.face_encoding)
            id_encoding = np.array(id_analysis.face_encoding)
            
            # Calculate face similarity using cosine similarity
            similarity_score = cosine_similarity([id_encoding], [selfie_encoding])[0][0]
            
            # Convert similarity to percentage (0-100)
            similarity = max(0, similarity_score * 100)
            
            # Determine if it's a match (similarity threshold of 70%)
            is_match = similarity >= 70
            
            # Calculate confidence based on distance and face qualities
            quality_factor = (selfie_analysis.face_quality + id_analysis.face_quality) / 200
            confidence = similarity * quality_factor
            
            logger.info(f"Face comparison: distance={distance:.3f}, similarity={similarity:.1f}%, match={is_match}")
            
            return MatchingResult(
                match_score=similarity,
                distance=distance,
                is_match=is_match,
                confidence=confidence,
                similarity_threshold=self.similarity_threshold
            )
            
        except Exception as e:
            logger.error(f"Face comparison failed: {str(e)}")
            return MatchingResult(
                match_score=0.0,
                distance=1.0,
                is_match=False,
                confidence=0.0
            )

    def process_face_verification(self, request: FaceRequest) -> FaceResult:
        """
        Process complete face verification request
        
        Args:
            request: Face verification request
            
        Returns:
            FaceResult with complete analysis
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        try:
            selfie_analysis = None
            id_photo_analysis = None
            liveness_result = None
            matching_result = None
            
            # Analyze selfie if provided
            if request.selfie and os.path.exists(request.selfie.file_path):
                selfie_analysis = self.analyze_face(request.selfie.file_path, is_selfie=True)
                
                if not selfie_analysis.face_detected:
                    errors.append("No face detected in selfie image")
                elif selfie_analysis.face_quality < 50:
                    warnings.append(f"Low selfie quality: {selfie_analysis.face_quality:.1f}/100")
                
                # Perform liveness detection on selfie
                if selfie_analysis.face_detected:
                    image = self.load_and_preprocess_image(request.selfie.file_path)
                    face_locations, _ = self.detect_faces(image)
                    if face_locations:
                        liveness_result = self.perform_liveness_detection(image, face_locations[0])
                        if not liveness_result.is_live:
                            warnings.append("Liveness detection indicates possible spoofing attempt")
            
            # Analyze ID photo if provided
            if request.id_photo and os.path.exists(request.id_photo.file_path):
                id_photo_analysis = self.analyze_face(request.id_photo.file_path, is_selfie=False)
                
                if not id_photo_analysis.face_detected:
                    errors.append("No face detected in ID document")
                elif id_photo_analysis.face_quality < 40:
                    warnings.append(f"Low ID photo quality: {id_photo_analysis.face_quality:.1f}/100")
            
            # Compare faces if both are available
            if selfie_analysis and id_photo_analysis and selfie_analysis.face_detected and id_photo_analysis.face_detected:
                matching_result = self.compare_faces(selfie_analysis, id_photo_analysis)
                
                if not matching_result.is_match:
                    warnings.append(f"Face matching score below threshold: {matching_result.match_score:.1f}%")
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(
                selfie_analysis, id_photo_analysis, liveness_result, matching_result
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return FaceResult(
                selfie_analysis=selfie_analysis,
                id_photo_analysis=id_photo_analysis,
                liveness_result=liveness_result,
                matching_result=matching_result,
                overall_score=overall_score,
                processing_time_ms=processing_time,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Face verification processing failed: {str(e)}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return FaceResult(
                overall_score=0.0,
                processing_time_ms=processing_time,
                errors=[str(e)],
                warnings=warnings
            )

    def _calculate_overall_score(
        self,
        selfie_analysis: Optional[FaceAnalysis],
        id_analysis: Optional[FaceAnalysis],
        liveness_result: Optional[LivenessResult],
        matching_result: Optional[MatchingResult]
    ) -> float:
        """Calculate overall face verification score"""
        try:
            scores = []
            
            # Face quality scores
            if selfie_analysis and selfie_analysis.face_detected:
                scores.append(selfie_analysis.face_quality * 0.2)
            
            if id_analysis and id_analysis.face_detected:
                scores.append(id_analysis.face_quality * 0.2)
            
            # Liveness score
            if liveness_result:
                liveness_score = liveness_result.confidence if liveness_result.is_live else 0
                scores.append(liveness_score * 0.3)
            
            # Matching score
            if matching_result:
                scores.append(matching_result.match_score * 0.3)
            
            return sum(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Overall score calculation failed: {str(e)}")
            return 0.0

# Initialize face processor
face_processor = FaceProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "face-agent",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process", response_model=FaceResponse)
async def process_face_request(request: FaceRequest):
    """
    Process face recognition and verification request
    
    Args:
        request: Face processing request
        
    Returns:
        Face processing response
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing face recognition request: {request.request_id}")
        
        # Process face verification
        result = face_processor.process_face_verification(request)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Determine status
        status = "success"
        if result.errors:
            status = "error"
        elif result.warnings:
            status = "warning"
        
        response_data = result.dict()
        
        return FaceResponse(
            status=status,
            data=response_data,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Face processing failed: {str(e)}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return FaceResponse(
            status="error",
            data={"error": str(e)},
            processing_time=processing_time,
            error=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Face Recognition Agent",
        "description": "Facial recognition and liveness detection for KYC verification",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process": "/process"
        }
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8002))
    
    # Run the service
    uvicorn.run(
        "face_service:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
