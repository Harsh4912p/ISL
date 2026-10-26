"""
Real-Time Video Call Signaling & Live ISL Sign Translation Service
Supports WebRTC peer-to-peer video calls with real-time AI sign detection & live subtitles.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, CallRequest, User, Sign
from datetime import datetime
import threading
import time
import base64
import cv2
import numpy as np
from PIL import Image, ImageOps
from io import BytesIO

call_bp = Blueprint("calls", __name__, url_prefix="/api/calls")

# Thread-safe in-memory room signaling store
_rooms_lock = threading.Lock()
active_rooms = {}

# Clean up stale rooms older than 4 hours
def _cleanup_stale_rooms():
    now = time.time()
    stale_keys = []
    with _rooms_lock:
        for rid, room in active_rooms.items():
            if now - room.get('last_activity', now) > 14400:
                stale_keys.append(rid)
        for rid in stale_keys:
            active_rooms.pop(rid, None)

@call_bp.route("/room/create", methods=["POST"])
def create_room():
    """Create a new WebRTC video call room with optional custom ID"""
    _cleanup_stale_rooms()
    data = request.get_json() or {}
    user_name = data.get("user_name", "Host")
    custom_id = data.get("room_id")
    
    if custom_id and custom_id.strip():
        room_id = custom_id.strip().upper()
    else:
        import uuid
        room_id = f"ISL-{uuid.uuid4().hex[:6].upper()}"
        
    peer_id = f"peer_{int(time.time() * 1000) % 1000000}"
    
    with _rooms_lock:
        active_rooms[room_id] = {
            "id": room_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "participants": {
                peer_id: {
                    "id": peer_id,
                    "name": user_name,
                    "role": "host",
                    "joined_at": time.time(),
                    "last_seen": time.time()
                }
            },
            "signals": {peer_id: []},
            "current_caption": None,
            "subtitles_history": []
        }
        
    return jsonify({
        "success": True,
        "room_id": room_id,
        "peer_id": peer_id,
        "role": "host",
        "message": f"Room {room_id} created successfully"
    }), 200

@call_bp.route("/room/join", methods=["POST"])
def join_room():
    """Join an existing WebRTC video call room"""
    _cleanup_stale_rooms()
    data = request.get_json() or {}
    room_id = data.get("room_id", "").strip().upper()
    user_name = data.get("user_name", "Guest")
    
    if not room_id:
        return jsonify({"error": "Room ID required"}), 400
        
    peer_id = f"peer_{int(time.time() * 1000) % 1000000}"
    
    with _rooms_lock:
        if room_id not in active_rooms:
            # Auto-create room if not found to prevent room code mismatch
            active_rooms[room_id] = {
                "id": room_id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "participants": {},
                "signals": {},
                "current_caption": None,
                "subtitles_history": []
            }
            role = "host"
        else:
            role = "participant"
            
        room = active_rooms[room_id]
        room["last_activity"] = time.time()
        room["participants"][peer_id] = {
            "id": peer_id,
            "name": user_name,
            "role": role,
            "joined_at": time.time(),
            "last_seen": time.time()
        }
        room["signals"][peer_id] = []
        
        # Collect existing peers
        existing_peers = [
            {"id": pid, "name": p["name"], "role": p["role"]}
            for pid, p in room["participants"].items()
            if pid != peer_id
        ]
        
    return jsonify({
        "success": True,
        "room_id": room_id,
        "peer_id": peer_id,
        "role": role,
        "existing_peers": existing_peers,
        "message": f"Joined room {room_id}"
    }), 200

@call_bp.route("/room/info/<room_id>", methods=["GET"])
def get_room_info(room_id):
    """Get active room details and participant count"""
    room_id = room_id.strip().upper()
    with _rooms_lock:
        room = active_rooms.get(room_id)
        if not room:
            return jsonify({"found": False, "room_id": room_id}), 404
            
        return jsonify({
            "found": True,
            "room_id": room_id,
            "participants": list(room["participants"].values()),
            "created_at": room["created_at"],
            "current_caption": room.get("current_caption")
        }), 200

@call_bp.route("/signal/send", methods=["POST"])
def send_signal():
    """Send WebRTC signal (offer, answer, or candidate) to a peer in the room"""
    data = request.get_json() or {}
    room_id = data.get("room_id", "").strip().upper()
    sender_id = data.get("sender_id")
    target_id = data.get("target_id")
    signal_type = data.get("type")  # 'offer', 'answer', 'candidate'
    payload = data.get("payload")
    
    if not room_id or not sender_id or not signal_type or payload is None:
        return jsonify({"error": "Missing signaling fields"}), 400
        
    with _rooms_lock:
        room = active_rooms.get(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
            
        room["last_activity"] = time.time()
        if sender_id in room["participants"]:
            room["participants"][sender_id]["last_seen"] = time.time()
            
        signal_msg = {
            "sender_id": sender_id,
            "sender_name": room["participants"].get(sender_id, {}).get("name", "Peer"),
            "type": signal_type,
            "payload": payload,
            "timestamp": time.time()
        }
        
        # Route signal to target peer, or broadcast to all other peers if target_id not specified
        if target_id:
            if target_id in room["signals"]:
                room["signals"][target_id].append(signal_msg)
        else:
            for pid in room["signals"]:
                if pid != sender_id:
                    room["signals"][pid].append(signal_msg)
                    
    return jsonify({"status": "signal_delivered"}), 200

@call_bp.route("/signal/poll", methods=["GET"])
def poll_signals():
    """Long-polling/poll endpoint for peer to receive pending WebRTC signals"""
    room_id = request.args.get("room_id", "").strip().upper()
    peer_id = request.args.get("peer_id", "")
    
    if not room_id or not peer_id:
        return jsonify({"error": "room_id and peer_id required"}), 400
        
    with _rooms_lock:
        room = active_rooms.get(room_id)
        if not room:
            return jsonify({"error": "Room not found", "signals": []}), 404
            
        room["last_activity"] = time.time()
        if peer_id in room["participants"]:
            room["participants"][peer_id]["last_seen"] = time.time()
            
        signals_queue = room["signals"].get(peer_id, [])
        # Drain queue
        room["signals"][peer_id] = []
        
        # Check active peers in room
        active_peers = [
            {"id": pid, "name": p["name"], "role": p["role"]}
            for pid, p in room["participants"].items()
            if pid != peer_id and (time.time() - p.get("last_seen", 0) < 60)
        ]
        
        caption = room.get("current_caption")
        
    return jsonify({
        "signals": signals_queue,
        "peers": active_peers,
        "caption": caption
    }), 200

@call_bp.route("/room/leave", methods=["POST"])
def leave_room():
    """Leave a video call room"""
    data = request.get_json() or {}
    room_id = data.get("room_id", "").strip().upper()
    peer_id = data.get("peer_id")
    
    with _rooms_lock:
        room = active_rooms.get(room_id)
        if room:
            room["participants"].pop(peer_id, None)
            room["signals"].pop(peer_id, None)
            # Remove room if empty
            if not room["participants"]:
                active_rooms.pop(room_id, None)
                
    return jsonify({"status": "left"}), 200

# Cache for sign translations
_sign_translation_cache = {}

def _get_sign_translations(sign_name: str):
    """Retrieve English and Hindi translations for a sign"""
    clean_name = sign_name.upper().strip()
    if clean_name in _sign_translation_cache:
        return _sign_translation_cache[clean_name]
        
    # Dictionary fallback for common ISL signs
    fallback_map = {
        'HELLO': ('Hello', 'नमस्ते'),
        'GOODBYE': ('Goodbye', 'अलविदा'),
        'THANK YOU': ('Thank You', 'धन्यवाद'),
        'PLEASE': ('Please', 'कृपया'),
        'YES': ('Yes', 'हाँ'),
        'NO': ('No', 'नहीं'),
        'GOOD': ('Good', 'अच्छा'),
        'BAD': ('Bad', 'बुरा'),
        'HELP': ('Help', 'मदद'),
        'SORRY': ('Sorry', 'क्षमा करें'),
        'LOVE': ('Love', 'प्यार'),
        'HAPPY': ('Happy', 'खुश'),
        'SAD': ('Sad', 'उदास'),
        'WATER': ('Water', 'पानी'),
        'FOOD': ('Food', 'खाना'),
        'WORK': ('Work', 'काम'),
        'OK': ('OK', 'ठीक है'),
        'PEACE': ('Peace', 'शांति'),
        'ONE': ('One', 'एक'),
        'TWO': ('Two', 'दो'),
        'THREE': ('Three', 'तीन'),
        'FIVE': ('Five', 'पाँच'),
        'TEN': ('Ten', 'दस'),
        'PHONE': ('Phone', 'फोन'),
        'DOCTOR': ('Doctor', 'डॉक्टर'),
        'HOSPITAL': ('Hospital', 'अस्पताल'),
        'HOME': ('Home', 'घर'),
        'SCHOOL': ('School', 'स्कूल'),
        'FRIEND': ('Friend', 'दोस्त'),
        'EAT': ('Eat', 'खाना'),
        'DRINK': ('Drink', 'पीना'),
        'SLEEP': ('Sleep', 'सोना'),
        'FIST': ('Fist / Action', 'मुट्ठी / काम'),
    }
    
    if clean_name in fallback_map:
        res = fallback_map[clean_name]
        _sign_translation_cache[clean_name] = res
        return res
        
    try:
        sign_obj = Sign.query.filter(Sign.name.ilike(clean_name)).first()
        if sign_obj:
            res = (sign_obj.english_translation or clean_name.title(), sign_obj.hindi_translation or clean_name)
            _sign_translation_cache[clean_name] = res
            return res
    except Exception:
        pass
        
    res = (clean_name.title(), clean_name)
    _sign_translation_cache[clean_name] = res
    return res

@call_bp.route("/detect-live", methods=["POST"])
def detect_live_call_frame():
    """
    Live frame detection endpoint for Video Calls.
    Analyzes hand landmarks, facial expression, and generates real-time subtitles
    with English and Hindi text translations.
    """
    try:
        data = request.get_json() or {}
        frame_data = data.get("frame")
        room_id = data.get("room_id", "").strip().upper()
        speaker_name = data.get("user_name", "Caller")
        min_conf = float(data.get("min_confidence", 0.20))
        
        if not frame_data:
            return jsonify({"error": "No frame provided"}), 400
            
        # Decode base64 image frame
        if isinstance(frame_data, str):
            if "base64," in frame_data:
                frame_data = frame_data.split("base64,")[1]
            try:
                frame_bytes = base64.b64decode(frame_data)
                img = Image.open(BytesIO(frame_bytes)).convert("RGB")
                img = ImageOps.exif_transpose(img)
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            except Exception as de:
                return jsonify({"error": f"Invalid frame image data: {str(de)}"}), 400
        else:
            return jsonify({"error": "frame must be base64 string"}), 400
            
        # Use singleton detector for optimal latency and memory
        from sign_detector import get_detector
        detector = get_detector()
        
        landmarks = detector.extract_landmarks(frame)
        face_res = detector.process_face(frame)
        
        detected_sign = None
        confidence = 0.0
        
        if landmarks is not None:
            pred = detector.predict_sign(landmarks)
            if pred.get("success") and pred.get("confidence", 0.0) >= min_conf:
                detected_sign = pred.get("sign")
                confidence = float(pred.get("confidence", 0.0))
                
        # Format translation and subtitle
        caption_data = None
        if detected_sign and detected_sign != "Unknown":
            en_trans, hi_trans = _get_sign_translations(detected_sign)
            caption_data = {
                "sign": detected_sign,
                "english": en_trans,
                "hindi": hi_trans,
                "confidence": round(confidence * 100),
                "expression": face_res.get("expression", "Neutral"),
                "speaker": speaker_name,
                "timestamp": time.time()
            }
            
            # If room_id is valid, broadcast caption to the room
            if room_id:
                with _rooms_lock:
                    if room_id in active_rooms:
                        active_rooms[room_id]["current_caption"] = caption_data
                        # Keep last 15 subtitles in history
                        hist = active_rooms[room_id]["subtitles_history"]
                        hist.append(caption_data)
                        if len(hist) > 15:
                            active_rooms[room_id]["subtitles_history"] = hist[-15:]
                            
        landmarks_list = None
        if landmarks is not None and len(landmarks) >= 42:
            landmarks_list = [
                {"x": round(float(landmarks[i * 2]), 4), "y": round(float(landmarks[i * 2 + 1]), 4)}
                for i in range(21)
            ]
            
        return jsonify({
            "success": True,
            "hand_detected": landmarks is not None,
            "sign": detected_sign,
            "translation_en": caption_data["english"] if caption_data else None,
            "translation_hi": caption_data["hindi"] if caption_data else None,
            "confidence": confidence,
            "face_detected": face_res.get("face_detected", False),
            "expression": face_res.get("expression", "Neutral"),
            "caption": caption_data,
            "landmarks": landmarks_list
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Live detection error: {str(e)}"}), 500

@call_bp.route("/subtitles/<room_id>", methods=["GET"])
def get_room_subtitles(room_id):
    """Retrieve current active subtitle caption and recent history for a call room"""
    room_id = room_id.strip().upper()
    with _rooms_lock:
        room = active_rooms.get(room_id)
        if not room:
            return jsonify({"found": False, "caption": None, "history": []}), 404
            
        caption = room.get("current_caption")
        # Auto-expire captions after 6 seconds of no new signs
        if caption and (time.time() - caption.get("timestamp", 0) > 6):
            caption = None
            room["current_caption"] = None
            
        return jsonify({
            "found": True,
            "room_id": room_id,
            "caption": caption,
            "history": room.get("subtitles_history", [])[-5:]
        }), 200

# User-to-User Database Integration (for Flutter mobile calls)
@call_bp.route("/initiate", methods=["POST"])
@jwt_required()
def initiate_call():
    caller_id = get_jwt_identity()
    data = request.get_json() or {}
    receiver_id = data.get("receiver_id")
    
    if not receiver_id:
        return jsonify({"error": "Receiver ID required"}), 400
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({"error": "Receiver not found"}), 404
        
    import uuid
    generated_room_id = f"CALL-{uuid.uuid4().hex[:6].upper()}"
    
    call = CallRequest(
        caller_id=caller_id,
        receiver_id=receiver_id,
        status="pending",
        call_type="video"
    )
    db.session.add(call)
    db.session.commit()
    
    # Pre-create room for this call
    peer_id = f"peer_{caller_id[:6]}"
    with _rooms_lock:
        active_rooms[generated_room_id] = {
            "id": generated_room_id,
            "call_id": call.id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "participants": {
                peer_id: {
                    "id": peer_id,
                    "name": getattr(call.caller, "first_name", "Caller"),
                    "role": "host",
                    "joined_at": time.time(),
                    "last_seen": time.time()
                }
            },
            "signals": {peer_id: []},
            "current_caption": None,
            "subtitles_history": []
        }
    
    return jsonify({
        "call_id": call.id,
        "room_id": generated_room_id,
        "peer_id": peer_id,
        "status": "pending",
        "receiver": receiver.to_dict()
    }), 200

@call_bp.route("/answer", methods=["POST"])
@jwt_required()
def answer_call():
    receiver_id = get_jwt_identity()
    data = request.get_json() or {}
    call_id = data.get("call_id")
    call = CallRequest.query.get(call_id)
    
    if not call or call.receiver_id != receiver_id or call.status != "pending":
        return jsonify({"error": "Invalid call"}), 400
    
    call.status = "active"
    call.started_at = datetime.utcnow()
    db.session.commit()
    
    # Locate room ID
    matched_room = None
    with _rooms_lock:
        for rid, room in active_rooms.items():
            if room.get("call_id") == call.id:
                matched_room = rid
                break
                
    if not matched_room:
        matched_room = f"CALL-{call.id[:6].upper()}"
        with _rooms_lock:
            active_rooms[matched_room] = {
                "id": matched_room,
                "call_id": call.id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "participants": {},
                "signals": {},
                "current_caption": None,
                "subtitles_history": []
            }
            
    peer_id = f"peer_{receiver_id[:6]}"
    with _rooms_lock:
        room = active_rooms[matched_room]
        room["participants"][peer_id] = {
            "id": peer_id,
            "name": getattr(call.receiver, "first_name", "Receiver"),
            "role": "participant",
            "joined_at": time.time(),
            "last_seen": time.time()
        }
        room["signals"][peer_id] = []
    
    return jsonify({
        "call_id": call.id,
        "room_id": matched_room,
        "peer_id": peer_id,
        "status": "active"
    }), 200

@call_bp.route("/end", methods=["POST"])
@jwt_required()
def end_call():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    call_id = data.get("call_id")
    call = CallRequest.query.get(call_id)
    
    if not call:
        return jsonify({"error": "Call not found"}), 404
    
    call.status = "ended"
    call.ended_at = datetime.utcnow()
    if call.started_at:
        call.duration = int((call.ended_at - call.started_at).total_seconds())
    db.session.commit()
    
    # Close signaling room
    with _rooms_lock:
        to_del = [rid for rid, r in active_rooms.items() if r.get("call_id") == call.id]
        for rid in to_del:
            active_rooms.pop(rid, None)
    
    return jsonify({"status": "ended", "duration": call.duration}), 200

@call_bp.route("/pending", methods=["GET"])
@jwt_required()
def get_pending_calls():
    user_id = get_jwt_identity()
    calls = CallRequest.query.filter(CallRequest.receiver_id == user_id, CallRequest.status == "pending").all()
    return jsonify({"calls": [c.to_dict() for c in calls]}), 200

@call_bp.route("/history", methods=["GET"])
@jwt_required()
def get_call_history():
    user_id = get_jwt_identity()
    limit = request.args.get("limit", 20, type=int)
    calls = CallRequest.query.filter((CallRequest.caller_id == user_id) | (CallRequest.receiver_id == user_id)).order_by(CallRequest.created_at.desc()).limit(limit).all()
    return jsonify({"history": [c.to_dict() for c in calls]}), 200
