"""ISL Sign Detection Service using MediaPipe + Scikit-Learn (Hybrid Engine)"""
import cv2
import numpy as np
import mediapipe as mp
import pickle
import json
import sys
import io
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import base64
from io import BytesIO
from PIL import Image, ImageOps

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import threading

class UniversalMediaPipeEngine:
    def __init__(self, models_dir: Path):
        self.lock = threading.Lock()
        self.mode = None
        self.models_dir = models_dir

        # Strategy 1: Try legacy mp.solutions
        try:
            if hasattr(mp, 'solutions'):
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=True, max_num_hands=2, min_detection_confidence=0.15, min_tracking_confidence=0.15
                )
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.15
                )
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detection = self.mp_face_detection.FaceDetection(
                    min_detection_confidence=0.25
                )
                self.mode = 'solutions'
                print("✅ MediaPipe Engine: initialized with legacy solutions API")
                return
        except Exception as e:
            print(f"Notice: mp.solutions unavailable ({e}). Trying Tasks API...")

    def _reinit_solutions(self):
        """Self-heal MediaPipe C++ graph if an internal graph error occurs"""
        try:
            if hasattr(self, 'hands') and self.hands:
                try: self.hands.close()
                except Exception: pass
            if hasattr(self, 'face_mesh') and self.face_mesh:
                try: self.face_mesh.close()
                except Exception: pass

            self.hands = self.mp_hands.Hands(
                static_image_mode=True, max_num_hands=2, min_detection_confidence=0.15, min_tracking_confidence=0.15
            )
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.15
            )
            print("🔄 MediaPipe Engine: graphs successfully refreshed")
        except Exception as re:
            print(f"⚠️ Error reinitializing MediaPipe: {re}")

        # Strategy 2: Try MediaPipe Tasks API (Python 3.12+)
        try:
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision
            import urllib.request

            hand_task_path = models_dir / 'hand_landmarker.task'
            if not hand_task_path.exists():
                print("⏬ Downloading hand_landmarker.task...")
                urllib.request.urlretrieve(
                    'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
                    str(hand_task_path)
                )

            face_task_path = models_dir / 'face_landmarker.task'
            if not face_task_path.exists():
                print("⏬ Downloading face_landmarker.task...")
                urllib.request.urlretrieve(
                    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
                    str(face_task_path)
                )

            hand_options = vision.HandLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_path=str(hand_task_path)),
                num_hands=2,
                min_hand_detection_confidence=0.2
            )
            self.hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)

            face_options = vision.FaceLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_path=str(face_task_path)),
                num_faces=1,
                min_face_detection_confidence=0.2
            )
            self.face_landmarker = vision.FaceLandmarker.create_from_options(face_options)
            self.mp_image_class = mp.Image
            self.mp_image_format = mp.ImageFormat
            self.mode = 'tasks'
            print("✅ MediaPipe Engine: initialized with Tasks API")
        except Exception as te:
            print(f"⚠️ Tasks API initialization notice: {te}")
            self.mode = 'none'

class ISLSignDetector:
    def __init__(self, model_name="ISL_Detection_V1"):
        self.model_name = model_name
        self.models_dir = Path('models')
        self.models_dir.mkdir(exist_ok=True)
        
        self.engine = UniversalMediaPipeEngine(self.models_dir)
        
        self.model = None
        self.label_encoder = None
        self.metadata = None
        self.landmarks_size = 42
        self.sign_templates = {}
        self._init_sign_templates()
        self._load_model()

    def _init_sign_templates(self):
        try:
            from dataset_loader import DatasetLoader
            loader = DatasetLoader()
            dataset = loader.load_sign_language_dataset()
            for s in dataset:
                name = s['name']
                kps = loader.generate_hand_landmarks(name)
                pts = np.array([[p['x'], p['y']] for p in kps[:21]])
                self.sign_templates[name.upper().replace('_', ' ').strip()] = self.normalize_landmarks(pts)
            print(f"✅ Loaded {len(self.sign_templates)} distinct ISL gesture templates")
        except Exception as e:
            print(f"Notice loading sign templates: {e}")

    def _load_model(self):
        model_path_sk = self.models_dir / f"{self.model_name}.pkl"
        encoder_path = self.models_dir / f"{self.model_name}_encoder.pkl"
        metadata_path = self.models_dir / f"{self.model_name}_metadata.json"

        try:
            if not model_path_sk.exists() or not encoder_path.exists():
                print(f"⚠️ Model file missing ({model_path_sk}). Training model now...")
                try:
                    from train_sign_detection_model import main as train_model_main
                    train_model_main()
                except Exception as te:
                    print(f"❌ Auto-training model failed: {te}")

            if model_path_sk.exists():
                with open(model_path_sk, 'rb') as f:
                    self.model = pickle.load(f)
                print(f"✅ Loaded Scikit-Learn RandomForest model")
            else:
                print(f"⚠️ RandomForest model not found: {model_path_sk}")
                return False

            if encoder_path.exists():
                with open(encoder_path, 'rb') as f:
                    self.label_encoder = pickle.load(f)
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False

    def extract_landmarks(self, frame: np.ndarray) -> Optional[np.ndarray]:
        with self.engine.lock:
            try:
                # Resize large camera frames to max 640px dimension for reliable & fast MediaPipe hand anchor detection
                h, w = frame.shape[:2]
                max_dim = 640
                proc_frame = frame
                if max(h, w) > max_dim:
                    scale = max_dim / float(max(h, w))
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    proc_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                rgb_frame = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)

                if self.engine.mode == 'solutions':
                    results = None
                    try:
                        results = self.engine.hands.process(rgb_frame)
                    except Exception as pe:
                        print(f"Notice: hands.process reset: {pe}")
                        self.engine._reinit_solutions()
                        try:
                            results = self.engine.hands.process(rgb_frame)
                        except Exception:
                            results = None

                    # Pass 2: If no hand detected, try CLAHE contrast enhancement for dim or backlit webcam frames
                    if not results or not results.multi_hand_landmarks:
                        try:
                            lab = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2LAB)
                            l, a, b = cv2.split(lab)
                            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                            cl = clahe.apply(l)
                            enhanced_rgb = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2RGB)
                            results = self.engine.hands.process(enhanced_rgb)
                        except Exception:
                            pass

                    # Pass 3: If still no hand detected, try brightness boost for dark shadows
                    if not results or not results.multi_hand_landmarks:
                        try:
                            bright_rgb = cv2.convertScaleAbs(rgb_frame, alpha=1.35, beta=35)
                            results = self.engine.hands.process(bright_rgb)
                        except Exception:
                            pass

                    if results and results.multi_hand_landmarks:
                        landmarks = []
                        for hand_landmarks in results.multi_hand_landmarks:
                            for landmark in hand_landmarks.landmark:
                                landmarks.extend([landmark.x, landmark.y])
                        if len(landmarks) == self.landmarks_size:
                            landmarks.extend([0] * self.landmarks_size)
                        return np.array(landmarks[:self.landmarks_size * 2])
                    return None
                elif self.engine.mode == 'tasks':
                    mp_img = self.engine.mp_image_class(image_format=self.engine.mp_image_format.SRGB, data=rgb_frame)
                    result = self.engine.hand_landmarker.detect(mp_img)
                    if result.hand_landmarks:
                        landmarks = []
                        for hand_landmarks in result.hand_landmarks:
                            for landmark in hand_landmarks:
                                landmarks.extend([landmark.x, landmark.y])
                        if len(landmarks) == self.landmarks_size:
                            landmarks.extend([0] * self.landmarks_size)
                        return np.array(landmarks[:self.landmarks_size * 2])
                    return None
                return None
            except Exception as e:
                print(f"❌ Error extracting landmarks: {e}")
                return None

    def process_face(self, frame: np.ndarray) -> Dict:
        """Detect face and analyze expressions and facial patterns using Face Mesh / Tasks"""
        with self.engine.lock:
            try:
                # Downscale large frames to max 640px for fast face mesh
                h, w = frame.shape[:2]
                proc_frame = frame
                if max(h, w) > 640:
                    scale = 640.0 / float(max(h, w))
                    proc_frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

                rgb_frame = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)
                landmarks = None
                if self.engine.mode == 'solutions':
                    try:
                        results = self.engine.face_mesh.process(rgb_frame)
                        if results and results.multi_face_landmarks:
                            landmarks = results.multi_face_landmarks[0].landmark
                    except Exception as pe:
                        print(f"Notice: face_mesh.process reset: {pe}")
                        self.engine._reinit_solutions()
                        try:
                            results = self.engine.face_mesh.process(rgb_frame)
                            if results and results.multi_face_landmarks:
                                landmarks = results.multi_face_landmarks[0].landmark
                        except Exception:
                            landmarks = None
                elif self.engine.mode == 'tasks':
                    mp_img = self.engine.mp_image_class(image_format=self.engine.mp_image_format.SRGB, data=rgb_frame)
                    result = self.engine.face_landmarker.detect(mp_img)
                    if result.face_landmarks and len(result.face_landmarks) > 0:
                        landmarks = result.face_landmarks[0]

                if landmarks:
                    # Calculate face bounding box in normalized coordinates
                    x_coords = [lm.x for lm in landmarks]
                    y_coords = [lm.y for lm in landmarks]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)

                    face_bbox = {
                        'x': max(0.0, x_min),
                        'y': max(0.0, y_min),
                        'w': min(1.0, x_max) - max(0.0, x_min),
                        'h': min(1.0, y_max) - max(0.0, y_min)
                    }

                    # 3D distance helper
                    def get_dist_3d(p1, p2):
                        p1_z = getattr(p1, 'z', 0.0)
                        p2_z = getattr(p2, 'z', 0.0)
                        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1_z - p2_z)**2)

                    # Normalize distances by cheek-to-cheek face width
                    face_width = get_dist_3d(landmarks[234], landmarks[454]) or 1.0

                    # Eyelid openness ratio (top-bottom eyelid distance normalized)
                    left_eye_open = get_dist_3d(landmarks[159], landmarks[145]) / face_width
                    right_eye_open = get_dist_3d(landmarks[386], landmarks[374]) / face_width

                    # Mouth width & height metrics
                    mouth_width = get_dist_3d(landmarks[61], landmarks[291]) / face_width
                    mouth_height = get_dist_3d(landmarks[0], landmarks[17]) / face_width

                    # Eyebrow raise distance
                    left_eyebrow_raise = get_dist_3d(landmarks[70], landmarks[159]) / face_width
                    right_eyebrow_raise = get_dist_3d(landmarks[300], landmarks[386]) / face_width
                    avg_eyebrow_raise = (left_eyebrow_raise + right_eyebrow_raise) / 2

                    # Eyebrow proximity (frown)
                    eyebrow_dist = get_dist_3d(landmarks[107], landmarks[336]) / face_width

                    # Classify expression/patterns
                    expression = 'Neutral'

                    if left_eye_open < 0.04 and right_eye_open > 0.07:
                        expression = 'Wink Left'
                    elif right_eye_open < 0.04 and left_eye_open > 0.07:
                        expression = 'Wink Right'
                    elif left_eye_open < 0.04 and right_eye_open < 0.04:
                        expression = 'Blink'
                    elif mouth_width > 0.35 and mouth_height < 0.15:
                        expression = 'Happy'
                    elif avg_eyebrow_raise > 0.22 and mouth_height > 0.06:
                        expression = 'Surprised'
                    elif eyebrow_dist < 0.18:
                        expression = 'Angry'
                    elif mouth_height > 0.05 and mouth_width < 0.35:
                        expression = 'Sad'

                    return {
                        'face_detected': True,
                        'face_bbox': face_bbox,
                        'expression': expression,
                        'facial_patterns': {
                            'left_eye_open': float(left_eye_open),
                            'right_eye_open': float(right_eye_open),
                            'mouth_width': float(mouth_width),
                            'mouth_height': float(mouth_height),
                            'eyebrow_raise': float(avg_eyebrow_raise),
                            'eyebrow_distance': float(eyebrow_dist),
                        }
                    }

                # Fallback: OpenCV Haar Cascade
                try:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    face_cascade = cv2.CascadeClassifier(cascade_path)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
                    if len(faces) > 0:
                        x, y, w, h = faces[0]
                        img_h, img_w = frame.shape[:2]
                        return {
                            'face_detected': True,
                            'face_bbox': {
                                'x': float(x / img_w),
                                'y': float(y / img_h),
                                'w': float(w / img_w),
                                'h': float(h / img_h)
                            },
                            'expression': 'Neutral',
                            'facial_patterns': {}
                        }
                except Exception:
                    pass

                return {'face_detected': False, 'face_bbox': None, 'expression': 'Unknown', 'facial_patterns': {}}
            except Exception as e:
                print(f"❌ Error processing face: {e}")
                return {'face_detected': False, 'face_bbox': None, 'expression': 'Unknown', 'facial_patterns': {}}

    @staticmethod
    def normalize_landmarks(pts_flat: np.ndarray) -> np.ndarray:
        """Normalize 21 hand points: translate wrist to (0,0), scale by wrist-to-middle MCP distance"""
        pts = np.array(pts_flat).reshape(-1, 2)
        if len(pts) < 21:
            return pts
        wrist = pts[0]
        centered = pts[:21] - wrist
        # Point 9 is middle finger MCP joint
        palm_size = float(np.linalg.norm(centered[9]))
        if palm_size < 1e-4:
            palm_size = 1.0
        return centered / palm_size

    def extract_gesture_features(self, landmarks_flat: np.ndarray) -> Dict:
        """Extract rotation/scale-invariant finger states and geometric gesture features"""
        try:
            norm = self.normalize_landmarks(landmarks_flat)
            if len(norm) < 21:
                return {}

            def get_dist(i, j):
                return float(np.linalg.norm(norm[i] - norm[j]))

            # Rotation-invariant finger extension metric:
            d_index_tip_wrist = get_dist(0, 8)
            d_index_pip_wrist = get_dist(0, 6)
            d_index_tip_mcp = get_dist(5, 8)
            d_index_pip_mcp = get_dist(5, 6)
            index_ext = bool(
                (d_index_tip_wrist > d_index_pip_wrist * 1.04) or
                (d_index_tip_mcp > d_index_pip_mcp * 1.15)
            )

            d_middle_tip_wrist = get_dist(0, 12)
            d_middle_pip_wrist = get_dist(0, 10)
            d_middle_tip_mcp = get_dist(9, 12)
            d_middle_pip_mcp = get_dist(9, 10)
            middle_ext = bool(
                (d_middle_tip_wrist > d_middle_pip_wrist * 1.04) or
                (d_middle_tip_mcp > d_middle_pip_mcp * 1.15)
            )

            d_ring_tip_wrist = get_dist(0, 16)
            d_ring_pip_wrist = get_dist(0, 14)
            d_ring_tip_mcp = get_dist(13, 16)
            d_ring_pip_mcp = get_dist(13, 14)
            ring_ext = bool(
                (d_ring_tip_wrist > d_ring_pip_wrist * 1.04) or
                (d_ring_tip_mcp > d_ring_pip_mcp * 1.15)
            )

            d_pinky_tip_wrist = get_dist(0, 20)
            d_pinky_pip_wrist = get_dist(0, 18)
            d_pinky_tip_mcp = get_dist(17, 20)
            d_pinky_pip_mcp = get_dist(17, 18)
            pinky_ext = bool(
                (d_pinky_tip_wrist > d_pinky_pip_wrist * 1.04) or
                (d_pinky_tip_mcp > d_pinky_pip_mcp * 1.15)
            )

            # Thumb extension: tip (4) distance from CMC (1) and MCP (2)
            d_thumb_tip_wrist = get_dist(0, 4)
            d_thumb_mcp_wrist = get_dist(0, 2)
            d_thumb_tip_mcp = get_dist(2, 4)
            d_thumb_ip_mcp = get_dist(2, 3)
            thumb_ext = bool(
                (d_thumb_tip_wrist > d_thumb_mcp_wrist * 1.10) or
                (d_thumb_tip_mcp > d_thumb_ip_mcp * 1.10)
            )

            ext_count = sum([index_ext, middle_ext, ring_ext, pinky_ext])
            all_four_curled = bool(ext_count == 0)

            # Directional thumb checks (in screen frame)
            thumb_down = bool(norm[4][1] > norm[0][1] + 0.1)
            thumb_up = bool(norm[4][1] < norm[0][1] - 0.15)

            # Distances between key fingertips
            d_thumb_index = get_dist(4, 8)
            d_thumb_middle = get_dist(4, 12)
            d_index_pinky = get_dist(8, 20)

            # High-level gesture classification
            is_thumbs_up = bool(all_four_curled and thumb_ext and not thumb_down)
            is_thumbs_down = bool(all_four_curled and thumb_ext and thumb_down)
            is_peace = bool(index_ext and middle_ext and not ring_ext and not pinky_ext)
            is_three = bool(
                (index_ext and middle_ext and ring_ext and not pinky_ext) or
                (thumb_ext and index_ext and middle_ext and not ring_ext and not pinky_ext)
            )
            is_point = bool(index_ext and not middle_ext and not ring_ext and not pinky_ext)
            is_pinch = bool((d_thumb_index < 0.40 and d_thumb_middle < 0.42) or (d_index_pinky < 0.38 and not all_four_curled))
            is_ok = bool((d_thumb_index < 0.45) and (d_thumb_middle > 0.40) and middle_ext)
            is_rock = bool(index_ext and pinky_ext and not middle_ext and not ring_ext)
            is_love = bool((thumb_ext or is_rock) and index_ext and pinky_ext and not middle_ext and not ring_ext)
            is_phone = bool(thumb_ext and pinky_ext and not index_ext and not middle_ext and not ring_ext)
            is_open = bool(ext_count >= 3 and not is_ok and not is_pinch and not is_peace and not is_rock)
            is_fist = bool(all_four_curled and not is_thumbs_up and not is_thumbs_down and not is_pinch)

            return {
                'thumb_up': is_thumbs_up,
                'thumb_down': is_thumbs_down,
                'peace': is_peace,
                'three': is_three,
                'point': is_point,
                'ok': is_ok,
                'pinch': is_pinch,
                'love': is_love,
                'rock': is_rock,
                'phone': is_phone,
                'open_palm': is_open,
                'fist': is_fist,
                'index_ext': index_ext,
                'middle_ext': middle_ext,
                'ring_ext': ring_ext,
                'pinky_ext': pinky_ext,
                'thumb_ext': thumb_ext,
                'ext_count': ext_count,
                'norm_coords': norm
            }
        except Exception as e:
            print(f"❌ Error extracting gesture features: {e}")
            return {}

    def heuristic_predict_sign(self, landmarks_flat: np.ndarray) -> Optional[Tuple[str, float]]:
        """Normalized gesture & template classifier matching against all 95 ISL distinct signs"""
        try:
            norm = self.normalize_landmarks(landmarks_flat)
            if len(norm) < 21:
                return None

            # 1. Vector Template Distance Matching against all 95 distinct ISL signs
            best_sign = None
            best_dist = 999.0
            for name, t_norm in self.sign_templates.items():
                dist = float(np.mean(np.linalg.norm(norm - t_norm, axis=1)))
                if dist < best_dist:
                    best_dist = dist
                    best_sign = name

            if best_sign and best_dist <= 0.36:
                conf = max(0.85, round(1.0 - (best_dist / 0.80), 2))
                return (best_sign.title(), conf)

            # 2. Rule-based geometric feature fallback
            feats = self.extract_gesture_features(landmarks_flat)
            if not feats:
                return None

            if feats.get('open_palm'):
                return ('Hello', 0.92)
            elif feats.get('thumb_up'):
                return ('Good', 0.95)
            elif feats.get('thumb_down'):
                return ('Bad', 0.95)
            elif feats.get('peace'):
                return ('Two', 0.94)
            elif feats.get('three'):
                return ('Three', 0.93)
            elif feats.get('point'):
                return ('One', 0.94)
            elif feats.get('ok'):
                return ('OK', 0.94)
            elif feats.get('love') or feats.get('rock'):
                return ('Love', 0.92)
            elif feats.get('phone'):
                return ('Phone', 0.93)
            elif feats.get('pinch'):
                return ('Eat', 0.91)
            elif feats.get('fist'):
                return ('Work', 0.90)

            # If closest template is reasonably close (< 0.45)
            if best_sign and best_dist <= 0.45:
                return (best_sign.title(), round(1.0 - (best_dist / 0.85), 2))

            return None
        except Exception as e:
            print(f"❌ Error in heuristics: {e}")
            return None

    def evaluate_target_sign_match(self, landmarks_flat: np.ndarray, target_sign_name: str, target_keypoints=None) -> Dict:
        """Directly compare detected landmarks against the learning target sign and template"""
        target_name_clean = target_sign_name.upper().replace('_', ' ').strip()
        feats = self.extract_gesture_features(landmarks_flat)
        if not feats:
            return {'matched': False, 'sign': None, 'confidence': 0.0, 'feedback': 'Position hand in camera'}

        norm_user = feats.get('norm_coords')
        if norm_user is None or len(norm_user) < 21:
            return {'matched': False, 'sign': None, 'confidence': 0.0, 'feedback': 'Hold hand clearly in front of camera'}

        # 1. Direct template matching distance to target sign
        target_template = self.sign_templates.get(target_name_clean)
        similarity = 0.0
        target_dist = 999.0

        if target_template is not None:
            target_dist = float(np.mean(np.linalg.norm(norm_user - target_template, axis=1)))
            similarity = max(0.0, float(1.0 - (target_dist / 0.85)))

        # Also check passed target_keypoints if available
        if target_keypoints is not None:
            try:
                pts_template = []
                if isinstance(target_keypoints, list):
                    for p in target_keypoints:
                        if isinstance(p, dict):
                            pts_template.append([p['x'], p['y']])
                        elif isinstance(p, (list, tuple)):
                            pts_template.append([p[0], p[1]])
                if len(pts_template) >= 21:
                    norm_custom = self.normalize_landmarks(np.array(pts_template[:21]))
                    dist_custom = float(np.mean(np.linalg.norm(norm_user - norm_custom, axis=1)))
                    sim_custom = max(0.0, float(1.0 - (dist_custom / 0.85)))
                    if sim_custom > similarity:
                        similarity = sim_custom
                        target_dist = min(target_dist, dist_custom)
            except Exception as e:
                print(f"Notice: custom template error: {e}")

        # 2. Comprehensive feature category mappings
        target_category_map = {
            'thumb_up': ['GOOD', 'YES', 'AGREE', 'STRONG', 'HEALTH', 'TOMORROW', 'YESTERDAY', 'HELP'],
            'thumb_down': ['BAD', 'WEAK', 'UGLY'],
            'peace': ['PEACE', 'TWO'],
            'three': ['THREE'],
            'point': ['ONE', 'TODAY', 'PAIN', 'FAST', 'THINK', 'REMEMBER', 'LEARN', 'FORGET', 'CLOCK', 'NO'],
            'ok': ['OK', 'UNDERSTAND'],
            'love': ['LOVE', 'BEAUTIFUL'],
            'rock': ['LOVE', 'BEAUTIFUL'],
            'phone': ['PHONE', 'PLAY'],
            'pinch': ['EAT', 'FOOD', 'SMALL', 'MONEY', 'WRITE', 'DRINK', 'BABY', 'LISTEN'],
            'open_palm': [
                'HELLO', 'GOODBYE', 'WELCOME', 'GOOD MORNING', 'HAPPY', 'SCARED', 'SURPRISED',
                'BIG', 'HOT', 'MOTHER', 'FATHER', 'GRANDFATHER', 'GRANDMOTHER', 'FIVE', 'TEN',
                'WAKE UP', 'PLEASE', 'THANK YOU', 'EXCUSE ME', 'CLEAN', 'SLOW', 'GIVE', 'READ',
                'BOOK', 'MORNING', 'EVENING', 'MAYBE', 'HOUSE', 'HOME', 'SCHOOL', 'HOSPITAL',
                'SLEEP', 'GOOD NIGHT', 'NIGHT'
            ],
            'fist': ['FIST', 'WORK', 'CAR', 'SICK', 'SORRY', 'ANGRY', 'COLD', 'TAKE', 'HUSBAND', 'WIFE', 'DIRTY', 'YES']
        }

        is_gesture_matched = False
        for feature_name, signs_list in target_category_map.items():
            if target_name_clean in signs_list:
                if feats.get(feature_name):
                    is_gesture_matched = True
                    break

        # Find closest active sign among templates for feedback
        closest_sign = None
        closest_dist = 999.0
        for name, t_norm in self.sign_templates.items():
            d = float(np.mean(np.linalg.norm(norm_user - t_norm, axis=1)))
            if d < closest_dist:
                closest_dist = d
                closest_sign = name.title()

        # Match condition: Target distance <= 0.44 OR similarity >= 0.44 OR gesture matched
        if target_dist <= 0.44 or similarity >= 0.44 or (is_gesture_matched and target_dist <= 0.52):
            conf = max(0.92, similarity, 0.95)
            return {
                'matched': True,
                'sign': target_sign_name,
                'confidence': conf,
                'similarity': similarity,
                'feedback': f'🎉 Excellent! Correct sign "{target_sign_name}" detected!'
            }
        else:
            conf = similarity if similarity > 0 else 0.4
            showing_text = f"Showing '{closest_sign}'" if closest_sign else "Hand detected"
            feedback = f"{showing_text}. Align hand to match '{target_sign_name}' template!"
            return {
                'matched': False,
                'sign': closest_sign or 'Unknown',
                'confidence': conf,
                'similarity': similarity,
                'feedback': feedback
            }

    def predict_sign(self, landmarks: np.ndarray) -> Dict:
        # 1. First pass: Normalized template & heuristic gesture engine
        heuristic_res = self.heuristic_predict_sign(landmarks)
        if heuristic_res:
            sign_name, conf = heuristic_res
            return {'success': True, 'sign': sign_name, 'confidence': conf}

        # 2. Second pass: Scikit-Learn RandomForest classifier ML model
        if self.model is not None and self.label_encoder is not None:
            try:
                landmarks_flat = np.array(landmarks).reshape(1, -1)
                if hasattr(self.model, 'predict_proba'):
                    proba = self.model.predict_proba(landmarks_flat)[0]
                    confidence = float(np.max(proba))
                    idx = np.argmax(proba)
                else:
                    idx = self.model.predict(landmarks_flat)[0]
                    confidence = 0.85

                raw_sign = self.label_encoder.inverse_transform([idx])[0]
                sign = str(raw_sign).title()
                return {'success': True, 'sign': sign, 'confidence': confidence}
            except Exception as e:
                print(f"Notice: model predict error: {e}")

        return {'success': False, 'error': 'No confident sign match', 'sign': 'Unknown', 'confidence': 0.0}

    def detect_from_image(self, image_data: str) -> Dict:
        try:
            image_bytes = base64.b64decode(image_data)
            # Force convert('RGB') and EXIF auto-rotation
            image = Image.open(BytesIO(image_bytes)).convert('RGB')
            image = ImageOps.exif_transpose(image)
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 1. Hands landmarks & sign prediction
            landmarks = self.extract_landmarks(frame)
            sign_res = None
            if landmarks is not None:
                sign_res = self.predict_sign(landmarks)
            
            # 2. Face & expression analysis
            face_res = self.process_face(frame)
            
            # Combine results
            return {
                'success': True,
                'sign': sign_res['sign'] if (sign_res and sign_res['success']) else None,
                'confidence': sign_res['confidence'] if (sign_res and sign_res['success']) else 0.0,
                'face_detected': face_res['face_detected'],
                'face_bbox': face_res['face_bbox'],
                'expression': face_res['expression'],
                'facial_patterns': face_res['facial_patterns']
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'sign': None}

    def process_video_frame(self, frame: np.ndarray, min_confidence: float = 0.2) -> tuple:
        """Process a video frame and return (sign, confidence, face_info, annotated_frame)"""
        try:
            # Face Mesh & Expression
            face_res = self.process_face(frame)
            
            # Hands & Sign Detection
            landmarks = self.extract_landmarks(frame)
            if landmarks is None:
                return None, 0.0, face_res, frame

            result = self.predict_sign(landmarks)
            if result['success']:
                sign = result['sign']
                confidence = result['confidence']
                if confidence >= min_confidence:
                    return sign, confidence, face_res, frame
            return None, 0.0, face_res, frame
        except Exception as e:
            print(f"Error processing frame: {e}")
            return None, 0.0, {'face_detected': False}, frame

def get_detector():
    global detector
    if detector is None:
        detector = ISLSignDetector()
    return detector

detector = None
