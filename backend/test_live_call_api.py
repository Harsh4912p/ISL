#!/usr/bin/env python
"""Test live call room creation, signaling, and frame detection API"""
import sys
import os
import base64
import numpy as np
import cv2
from io import BytesIO
from PIL import Image

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app

app = create_app('development')
client = app.test_client()

print("=" * 60)
print("🧪 TESTING ISL LIVE VIDEO CALL & DETECTION API")
print("=" * 60)

# 1. Test Room Creation
res = client.post('/api/calls/room/create', json={'user_name': 'Aarav'})
print("1. Create Room Response:", res.status_code, res.get_json())
assert res.status_code == 200
data = res.get_json()
room_id = data['room_id']
peer1_id = data['peer_id']

# 2. Test Join Room
res2 = client.post('/api/calls/room/join', json={'room_id': room_id, 'user_name': 'Diya'})
print("2. Join Room Response:", res2.status_code, res2.get_json())
assert res2.status_code == 200
peer2_id = res2.get_json()['peer_id']

# 3. Test Signal Exchange (Offer from Peer 1 to Peer 2)
signal_res = client.post('/api/calls/signal/send', json={
    'room_id': room_id,
    'sender_id': peer1_id,
    'target_id': peer2_id,
    'type': 'offer',
    'payload': {'sdp': 'mock_offer_sdp', 'type': 'offer'}
})
print("3. Send Signal Response:", signal_res.status_code, signal_res.get_json())
assert signal_res.status_code == 200

# 4. Test Signal Polling (Peer 2 polls)
poll_res = client.get(f'/api/calls/signal/poll?room_id={room_id}&peer_id={peer2_id}')
print("4. Poll Signals Response:", poll_res.status_code, poll_res.get_json())
assert poll_res.status_code == 200
assert len(poll_res.get_json()['signals']) == 1

# 5. Test Live Frame Detection & Subtitle Generation
# Generate a test blank 320x240 image
dummy_img = np.ones((240, 320, 3), dtype=np.uint8) * 128
_, buf = cv2.imencode('.jpg', dummy_img)
b64_frame = base64.b64encode(buf.tobytes()).decode('utf-8')

detect_res = client.post('/api/calls/detect-live', json={
    'room_id': room_id,
    'user_name': 'Aarav',
    'frame': b64_frame
})
print("5. Live Detect Frame Response:", detect_res.status_code, detect_res.get_json())
assert detect_res.status_code == 200
detect_data = detect_res.get_json()
print("   Hand detected:", detect_data['hand_detected'])
print("   Face detected:", detect_data['face_detected'])

# 6. Test Subtitle retrieval for room
sub_res = client.get(f'/api/calls/subtitles/{room_id}')
print("6. Get Subtitles Response:", sub_res.status_code, sub_res.get_json())
assert sub_res.status_code == 200

print("\n" + "=" * 60)
print("🎉 ALL API TESTS PASSED 100% SUCCESSFULLY!")
print("=" * 60)
