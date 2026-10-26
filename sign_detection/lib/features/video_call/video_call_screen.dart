import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:animate_do/animate_do.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import '../../config/api_config.dart';
import '../../core/widgets/cards.dart';
import '../../data/services/sign_detection_service.dart';
import '../call_summary/call_summary_screen.dart';

class VideoCallScreen extends StatefulWidget {
  final String? initialChannelName;
  final String? initialUserName;

  const VideoCallScreen({
    Key? key,
    this.initialChannelName,
    this.initialUserName,
  }) : super(key: key);

  @override
  State<VideoCallScreen> createState() => _VideoCallScreenState();
}

class _VideoCallScreenState extends State<VideoCallScreen> {
  final _signDetectionService = SignDetectionService();

  WebViewController? _webViewController;
  bool _isWebViewReady = false;
  bool _isLoading = true;

  CameraController? _cameraController;
  List<CameraDescription> _cameras = [];
  bool _isCameraInitialized = false;

  bool _isJoined = false;
  bool _isTranslationEnabled = true;
  bool _isMicEnabled = true;
  bool _isCameraEnabled = true;
  bool _isSpeakerEnabled = true;
  bool _showChannelInput = true;

  late TextEditingController _channelController;
  late TextEditingController _userNameController;

  DateTime? _callStartTime;
  Timer? _durationTimer;
  String _callDuration = '00:00';

  String? _currentDetectedSign;
  String? _currentTranslationEn;
  String? _currentTranslationHi;
  Timer? _detectionTimer;
  Timer? _subtitleSyncTimer;

  @override
  void initState() {
    super.initState();
    _channelController = TextEditingController(text: widget.initialChannelName ?? '');
    _userNameController = TextEditingController(text: widget.initialUserName ?? 'User123');

    if (widget.initialChannelName != null && widget.initialChannelName!.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _startCall();
      });
    }
  }

  Future<void> _startCall() async {
    if (_channelController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a channel name or room code')),
      );
      return;
    }

    // Request Camera and Microphone permissions
    try {
      await [Permission.camera, Permission.microphone].request();
    } catch (_) {}

    setState(() {
      _showChannelInput = false;
      _isJoined = true;
      _isLoading = true;
    });

    _callStartTime = DateTime.now();
    _startCallTimer();

    final roomCode = _channelController.text.trim().toUpperCase();
    final userName = _userNameController.text.trim().isEmpty ? 'User' : _userNameController.text.trim();
    final callUrl = '${ApiConfig.webVideoCallUrl}?room=${Uri.encodeComponent(roomCode)}&user=${Uri.encodeComponent(userName)}&autojoin=1&app=1';

    try {
      // Initialize WebRTC In-App Engine
      final controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(const Color(0xFF0A0B10))
        ..setNavigationDelegate(
          NavigationDelegate(
            onPageStarted: (url) {
              if (mounted) setState(() => _isLoading = true);
            },
            onPageFinished: (url) {
              if (mounted) {
                setState(() {
                  _isLoading = false;
                  _isWebViewReady = true;
                });
              }
            },
            onWebResourceError: (error) {
              debugPrint('WebView error: ${error.description}');
            },
          ),
        );

      // Grant WebRTC camera & mic permissions and allow video autoplay inside Android WebView
      if (controller.platform is AndroidWebViewController) {
        AndroidWebViewController.enableDebugging(true);
        final androidController = controller.platform as AndroidWebViewController;
        androidController.setMediaPlaybackRequiresUserGesture(false);
        androidController.setOnPlatformPermissionRequest((request) {
          request.grant();
        });
      }

      await controller.loadRequest(Uri.parse(callUrl));
      if (mounted) {
        setState(() {
          _webViewController = controller;
        });
      }
    } catch (e) {
      debugPrint('WebView initialization error: $e, falling back to camera stream');
      _initFallbackCamera();
    }
  }

  Future<void> _initFallbackCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isNotEmpty) {
        final frontCam = _cameras.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
          orElse: () => _cameras.first,
        );
        _cameraController = CameraController(
          frontCam,
          ResolutionPreset.medium,
          enableAudio: true,
        );
        await _cameraController!.initialize();
        if (mounted) {
          setState(() => _isCameraInitialized = true);
        }
        _startSignDetection();
      }
    } catch (e) {
      debugPrint('Camera fallback error: $e');
    }
  }

  void _startCallTimer() {
    _durationTimer?.cancel();
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && _callStartTime != null) {
        final duration = DateTime.now().difference(_callStartTime!);
        final minutes = duration.inMinutes;
        final seconds = duration.inSeconds % 60;
        setState(() {
          _callDuration =
              '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
        });
      }
    });
  }

  void _stopCallTimer() {
    _durationTimer?.cancel();
  }

  void _startSignDetection() {
    _detectionTimer?.cancel();
    _subtitleSyncTimer?.cancel();

    // Frame capture every 1.2s for live sign recognition
    _detectionTimer = Timer.periodic(const Duration(milliseconds: 1200), (_) async {
      if (!_isTranslationEnabled || !mounted) return;

      try {
        Uint8List? frameBytes;
        if (_cameraController != null && _cameraController!.value.isInitialized) {
          try {
            final image = await _cameraController!.takePicture();
            frameBytes = await image.readAsBytes();
          } catch (_) {}
        }

        final result = await _signDetectionService.detectSignFromFrame(
          frameBytes ?? Uint8List(0),
          roomId: _channelController.text,
        );

        if (mounted && result.sign.isNotEmpty) {
          setState(() {
            _currentDetectedSign = result.sign;
          });
        }
      } catch (e) {
        debugPrint('Sign detection error: $e');
      }
    });

    // Subtitle synchronization from room
    _subtitleSyncTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      if (!mounted || _channelController.text.isEmpty) return;
      try {
        final res = await http.get(
          Uri.parse('${ApiConfig.baseUrl}/calls/subtitles/${_channelController.text}'),
        ).timeout(const Duration(seconds: 2));

        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          if (data['caption'] != null && mounted) {
            final cap = data['caption'];
            setState(() {
              _currentDetectedSign = cap['sign'];
              _currentTranslationEn = cap['english'];
              _currentTranslationHi = cap['hindi'];
            });
          }
        }
      } catch (_) {}
    });
  }

  void _stopSignDetection() {
    _detectionTimer?.cancel();
    _subtitleSyncTimer?.cancel();
    setState(() => _currentDetectedSign = null);
  }

  void _endCall() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E1B4B),
        title: const Text('End Call?', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: const Text('Are you sure you want to leave this video call?', style: TextStyle(color: Colors.white70)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel', style: TextStyle(color: Colors.white60)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFEF4444)),
            onPressed: () {
              Navigator.of(context).pop();
              _stopCallTimer();
              _stopSignDetection();

              if (mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    builder: (_) => const CallSummaryScreen(),
                  ),
                );
              }
            },
            child: const Text('End Call', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _channelController.dispose();
    _userNameController.dispose();
    _stopCallTimer();
    _stopSignDetection();
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0B10),
      body: _showChannelInput
          ? _buildChannelSelectionScreen()
          : _buildInAppCallScreen(),
    );
  }

  Widget _buildChannelSelectionScreen() {
    return SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              FadeInDown(
                child: Container(
                  padding: const EdgeInsets.all(28),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF1E1B4B), Color(0xFF312E81)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF6366F1).withOpacity(0.25),
                        blurRadius: 30,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    children: [
                      Container(
                        width: 72,
                        height: 72,
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withOpacity(0.2),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: const Color(0xFF6366F1).withOpacity(0.4)),
                        ),
                        child: const Center(
                          child: Text('🤟', style: TextStyle(fontSize: 36)),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Live ISL Video Call',
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Two-Way Video Calling with Real-Time Sign Translation & Subtitles',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              FadeInUp(
                delay: const Duration(milliseconds: 100),
                child: TextField(
                  controller: _userNameController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'Your Name',
                    labelStyle: const TextStyle(color: Colors.white70),
                    prefixIcon: const Icon(Icons.person, color: Color(0xFF818CF8)),
                    filled: true,
                    fillColor: const Color(0xFF1E1B4B).withOpacity(0.6),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: Color(0xFF6366F1), width: 2),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              FadeInUp(
                delay: const Duration(milliseconds: 150),
                child: TextField(
                  controller: _channelController,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                  textCapitalization: TextCapitalization.characters,
                  decoration: InputDecoration(
                    labelText: 'Room Code / Channel',
                    labelStyle: const TextStyle(color: Colors.white70),
                    hintText: 'e.g. ISL-CALL',
                    hintStyle: const TextStyle(color: Colors.white30),
                    prefixIcon: const Icon(Icons.tag, color: Color(0xFF818CF8)),
                    filled: true,
                    fillColor: const Color(0xFF1E1B4B).withOpacity(0.6),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: Color(0xFF6366F1), width: 2),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),

              FadeInUp(
                delay: const Duration(milliseconds: 200),
                child: Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () {
                          final code = 'ISL-${DateTime.now().millisecondsSinceEpoch % 9000 + 1000}';
                          _channelController.text = code;
                          _startCall();
                        },
                        icon: const Icon(Icons.add_call, size: 20),
                        label: const Text('Create Room', style: TextStyle(fontWeight: FontWeight.bold)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          elevation: 6,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _startCall,
                        icon: const Icon(Icons.video_call, size: 20),
                        label: const Text('Join Call', style: TextStyle(fontWeight: FontWeight.bold)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF6366F1),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          elevation: 6,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              FadeInUp(
                delay: const Duration(milliseconds: 230),
                child: TextButton.icon(
                  onPressed: () {
                    _channelController.text = 'ISL-DEMO';
                    _startCall();
                  },
                  icon: const Icon(Icons.bolt, color: Color(0xFFFBBF24), size: 18),
                  label: const Text('Quick Test Room (ISL-DEMO)', style: TextStyle(color: Color(0xFFFBBF24))),
                ),
              ),
              const SizedBox(height: 8),

              FadeInUp(
                delay: const Duration(milliseconds: 250),
                child: OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white70,
                    side: BorderSide(color: Colors.white.withOpacity(0.2)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: const Text('Back to Home'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Full In-App WebRTC Video Call Screen with Live Subtitles Overlay
  Widget _buildInAppCallScreen() {
    return SafeArea(
      child: Stack(
        children: [
          // 1. Primary Video Viewport (WebRTC In-App Engine)
          if (_webViewController != null)
            WebViewWidget(controller: _webViewController!)
          else if (_isCameraInitialized && _cameraController != null)
            CameraPreview(_cameraController!)
          else
            const Center(
              child: CircularProgressIndicator(color: Color(0xFF6366F1)),
            ),

          // 2. Loading Indicator while connecting
          if (_isLoading)
            Container(
              color: const Color(0xFF0A0B10).withOpacity(0.85),
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Color(0xFF6366F1)),
                    SizedBox(height: 16),
                    Text(
                      'Connecting to live video call...',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Initializing camera & AI sign interpreter',
                      style: TextStyle(color: Colors.white60, fontSize: 13),
                    ),
                  ],
                ),
              ),
            ),

          // 3. Top Floating App Bar
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Room Code Chip
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A).withOpacity(0.85),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white.withOpacity(0.15)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.tag, size: 16, color: Color(0xFF818CF8)),
                      const SizedBox(width: 6),
                      Text(
                        _channelController.text.toUpperCase(),
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _callDuration,
                        style: const TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                    ],
                  ),
                ),

                // AI Active Badge & Leave Button
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withOpacity(0.2),
                        border: Border.all(color: const Color(0xFF10B981)),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.auto_awesome, size: 14, color: Color(0xFF10B981)),
                          SizedBox(width: 4),
                          Text('AI Live', style: TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white),
                      onPressed: _endCall,
                      style: IconButton.styleFrom(
                        backgroundColor: const Color(0xFFEF4444),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // 4. Fallback Native Sign Subtitles Card (when using native camera)
          if (!_isWebViewReady && _isTranslationEnabled && _currentDetectedSign != null)
            Positioned(
              bottom: 90,
              left: 20,
              right: 20,
              child: FadeInDown(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A).withOpacity(0.92),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFF6366F1).withOpacity(0.4)),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF6366F1).withOpacity(0.2),
                        blurRadius: 20,
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)]),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Text('🤟', style: TextStyle(fontSize: 24)),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _currentDetectedSign!,
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                            ),
                            if (_currentTranslationHi != null)
                              Text(
                                _currentTranslationHi!,
                                style: const TextStyle(fontSize: 16, color: Color(0xFFCBD5E1), fontWeight: FontWeight.w500),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
