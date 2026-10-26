import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'dart:convert';
import 'dart:async';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:animate_do/animate_do.dart';
import '../services/auth_service.dart';
import '../config/api_config.dart';
import '../core/widgets/hand_skeleton.dart';

class PracticeScreen extends StatefulWidget {
  final Map<String, dynamic> sign;

  const PracticeScreen({Key? key, required this.sign}) : super(key: key);

  @override
  State<PracticeScreen> createState() => _PracticeScreenState();
}

class _PracticeScreenState extends State<PracticeScreen> {
  CameraController? _cameraController;
  List<CameraDescription>? cameras;
  Timer? _frameTimer;
  bool _isDetecting = false;
  bool _success = false;
  bool _showGuideOverlay = true;
  double _confidence = 0.0;
  String _currentFeedback = 'Position your hand inside the guide pattern';

  List<dynamic>? _liveHandLandmarks;
  bool _handDetected = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      cameras = await availableCameras();
      if (cameras != null && cameras!.isNotEmpty) {
        final frontCamera = cameras!.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.front,
          orElse: () => cameras![0],
        );

        _cameraController = CameraController(
          frontCamera,
          ResolutionPreset.medium,
          enableAudio: false,
        );

        await _cameraController!.initialize();

        if (mounted) {
          setState(() {});
          _startPracticeTimer();
        }
      }
    } catch (e) {
      setState(() => _currentFeedback = 'Camera error: $e');
    }
  }

  void _startPracticeTimer() {
    _frameTimer = Timer.periodic(const Duration(milliseconds: 700), (timer) async {
      if (_isDetecting || _success || _cameraController == null || !_cameraController!.value.isInitialized) {
        return;
      }

      setState(() => _isDetecting = true);

      try {
        final imageFile = await _cameraController!.takePicture();
        final bytes = await imageFile.readAsBytes();
        final base64Image = base64Encode(bytes);

        await _validateGesture(base64Image);
      } catch (e) {
        print('Practice frame capture error: $e');
      } finally {
        if (mounted) {
          setState(() => _isDetecting = false);
        }
      }
    });
  }

  Future<void> _validateGesture(String base64Image) async {
    try {
      final authService = context.read<AuthService>();

      final response = await http.post(
        Uri.parse(ApiConfig.detectFrameEndpoint),
        headers: {
          ...ApiConfig.defaultHeaders,
          'Authorization': 'Bearer ${authService.accessToken}',
        },
        body: jsonEncode({
          'frame': base64Image,
          'min_confidence': 0.15,
          'target_sign': widget.sign['name']
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final detectedSign = data['sign'];
        final conf = (data['confidence'] ?? 0.0).toDouble();
        final isMatched = data['matched'] == true ||
            (detectedSign != null && detectedSign.toString().toUpperCase() == widget.sign['name'].toString().toUpperCase());
        final feedbackMsg = data['feedback'];
        final landmarks = data['landmarks'] as List?;
        final handDetected = data['hand_detected'] == true || (landmarks != null && landmarks.isNotEmpty);

        if (mounted) {
          setState(() {
            _practiceAttempts++;
            _liveHandLandmarks = landmarks;
            _handDetected = handDetected;
          });

          if (isMatched) {
            // Target sign correctly detected!
            setState(() {
              _success = true;
              _confidence = conf > 0 ? conf : 0.95;
              _currentFeedback = feedbackMsg ?? 'Excellent! Correct sign "${widget.sign['name']}" detected! 🎉';
            });

            _frameTimer?.cancel();
            await _recordProgress(true);

            // Auto close after 2.5 seconds
            Future.delayed(const Duration(milliseconds: 2500), () {
              if (mounted) {
                Navigator.of(context).pop(true);
              }
            });
          } else if (detectedSign != null && detectedSign != 'Unknown') {
            setState(() {
              _confidence = conf;
              _currentFeedback = feedbackMsg ?? 'Detected "$detectedSign". Keep trying to make "${widget.sign['name']}"!';
            });
          } else {
            setState(() {
              _confidence = conf;
              _currentFeedback = feedbackMsg ?? 'No hand shape detected. Align your hand with the guide pattern!';
            });
          }
        }
      }
    } on TimeoutException {
      print('Practice frame timeout (skipped frame)');
    } catch (e) {
      print('Practice validation error: $e');
    }
  }

  bool _hasRecordedProgress = false;
  int _practiceAttempts = 0;

  Future<void> _recordProgress(bool correct) async {
    _hasRecordedProgress = true;
    try {
      final authService = context.read<AuthService>();
      final payload = jsonEncode({
        'correct': correct,
        'times_practiced': 1,
        'times_detected_correctly': correct ? 1 : 0,
        'mastered': correct,
      });

      // Try primary learning route
      final res1 = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/learning/progress/${widget.sign['id']}'),
        headers: {
          ...ApiConfig.defaultHeaders,
          'Authorization': 'Bearer ${authService.accessToken}',
        },
        body: payload,
      );

      if (res1.statusCode != 200) {
        // Fallback to utils route
        await http.post(
          Uri.parse('${ApiConfig.utilsUrl}/learning-progress/${widget.sign['id']}'),
          headers: {
            ...ApiConfig.defaultHeaders,
            'Authorization': 'Bearer ${authService.accessToken}',
          },
          body: payload,
        );
      }
    } catch (e) {
      print('Error saving practice progress: $e');
    }
  }

  @override
  void dispose() {
    _frameTimer?.cancel();
    if (!_hasRecordedProgress && _practiceAttempts > 0) {
      _recordProgress(false);
    }
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'Practice: ${widget.sign['name']}',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
          backgroundColor: Colors.deepPurple,
          foregroundColor: Colors.white,
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(
          'Practice: ${widget.sign['name']}',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.deepPurple,
        foregroundColor: Colors.white,
        centerTitle: true,
        actions: [
          IconButton(
            icon: Icon(_showGuideOverlay ? Icons.grid_on : Icons.grid_off),
            tooltip: 'Toggle Hand Pattern Guide',
            onPressed: () => setState(() => _showGuideOverlay = !_showGuideOverlay),
          )
        ],
      ),
      body: Column(
        children: [
          // Target template header with realistic skeleton guide
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Colors.deepPurple.shade900,
            child: Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: HandSkeletonWidget(
                    keypoints: widget.sign['keypoints_data'],
                    width: 75,
                    height: 75,
                    backgroundColor: const Color(0xFFFAF5F0),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            widget.sign['name'] ?? '',
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.deepPurple.shade400,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              (widget.sign['difficulty_level'] ?? 'EASY').toUpperCase(),
                              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        widget.sign['description'] ?? 'Position your hand matching the template guide.',
                        style: const TextStyle(fontSize: 12, color: Colors.white70),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Camera View with Interactive Guide Overlay
          Expanded(
            child: Stack(
              children: [
                Positioned.fill(
                  child: CameraPreview(_cameraController!),
                ),

                // 🌟 Real-time Live Hand Skeleton Movement Tracking Overlay
                if (_liveHandLandmarks != null && _liveHandLandmarks!.isNotEmpty)
                  Positioned.fill(
                    child: CustomPaint(
                      painter: LiveHandTrackingPainter(
                        keypoints: _liveHandLandmarks,
                        isMatched: _success,
                        mirrorFrontCamera: true,
                      ),
                    ),
                  ),

                // ✋ Luminous AR Hand Guide Overlay on Camera Preview (User can toggle or use as reference)
                if (_showGuideOverlay)
                  Center(
                    child: Container(
                      width: 250,
                      height: 310,
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: _success
                              ? Colors.greenAccent
                              : Colors.cyanAccent.withOpacity(0.55),
                          width: 2.2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: (_success ? Colors.greenAccent : Colors.cyanAccent).withOpacity(0.18),
                            blurRadius: 18,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Expanded(
                            child: HandSkeletonWidget(
                              keypoints: widget.sign['keypoints_data'],
                              width: 210,
                              height: 250,
                              isGuideOverlay: true,
                              guideColor: _success ? Colors.greenAccent : Colors.cyanAccent,
                              backgroundColor: Colors.transparent,
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
                            margin: const EdgeInsets.only(bottom: 10),
                            decoration: BoxDecoration(
                              color: Colors.black.withOpacity(0.65),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: Colors.white24, width: 0.8),
                            ),
                            child: Text(
                              'Target Sign: "${widget.sign['name']}"',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                // Live Tracking Status Pill (Top Right)
                Positioned(
                  top: 14,
                  right: 14,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.65),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _handDetected ? (_success ? Colors.greenAccent : Colors.cyanAccent) : Colors.white24,
                        width: 1.2,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _handDetected ? (_success ? Colors.greenAccent : Colors.cyanAccent) : Colors.redAccent,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _handDetected
                              ? (_success ? 'Sign Matched! 🎉' : 'Tracking Hand ✋')
                              : 'No Hand Detected',
                          style: TextStyle(
                            color: _handDetected ? (_success ? Colors.greenAccent : Colors.cyanAccent) : Colors.white70,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Guide Toggle Button Pill
                Positioned(
                  top: 14,
                  left: 14,
                  child: GestureDetector(
                    onTap: () => setState(() => _showGuideOverlay = !_showGuideOverlay),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _showGuideOverlay ? Colors.cyanAccent.withOpacity(0.6) : Colors.white24,
                          width: 1,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _showGuideOverlay ? Icons.visibility : Icons.visibility_off,
                            color: _showGuideOverlay ? Colors.cyanAccent : Colors.white70,
                            size: 14,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            _showGuideOverlay ? 'Pattern ON' : 'Pattern OFF',
                            style: TextStyle(
                              color: _showGuideOverlay ? Colors.cyanAccent : Colors.white70,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

                // Feedback Overlay at bottom
                Positioned(
                  left: 16,
                  right: 16,
                  bottom: 24,
                  child: ZoomIn(
                    duration: const Duration(milliseconds: 300),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                      decoration: BoxDecoration(
                        color: _success
                            ? Colors.green.shade700.withOpacity(0.95)
                            : Colors.black.withOpacity(0.8),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: _success ? Colors.greenAccent : Colors.white24,
                          width: 1.5,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.3),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          )
                        ],
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _currentFeedback,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          if (_confidence > 0.0) ...[
                            const SizedBox(height: 8),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: _confidence.clamp(0.0, 1.0),
                                backgroundColor: Colors.white24,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  _success ? Colors.greenAccent : Colors.cyanAccent,
                                ),
                                minHeight: 6,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Match Accuracy: ${(_confidence * 100).toStringAsFixed(0)}%',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),

                // Success Splash Celebration
                if (_success)
                  Positioned.fill(
                    child: Container(
                      color: Colors.green.withOpacity(0.35),
                      child: Center(
                        child: BounceInDown(
                          child: Container(
                            padding: const EdgeInsets.all(24),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.greenAccent.withOpacity(0.6),
                                  blurRadius: 30,
                                  spreadRadius: 8,
                                )
                              ],
                            ),
                            child: const Icon(
                              Icons.check_circle,
                              color: Colors.green,
                              size: 80,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),

                // Loading Frame Processing Spinner
                if (_isDetecting && !_success)
                  const Positioned(
                    top: 16,
                    right: 16,
                    child: SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.cyanAccent),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
