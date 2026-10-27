import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:camera/camera.dart';
import 'dart:convert';
import 'dart:async';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/tts_service.dart';
import '../config/api_config.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;
import '../core/widgets/hand_skeleton.dart';

class TranslateScreen extends StatefulWidget {
  final bool isActive;
  const TranslateScreen({super.key, this.isActive = true});

  @override
  State<TranslateScreen> createState() => _TranslateScreenState();
}

class _TranslateScreenState extends State<TranslateScreen> {
  CameraController? _cameraController;
  List<CameraDescription>? cameras;
  Timer? _frameTimer;
  bool _isDetecting = false;
  String _detectedSign = 'No sign detected';
  double _confidence = 0.0;
  List<Map<String, dynamic>> _detectionHistory = [];
  
  // Hand movement tracking variables
  List<dynamic>? _liveHandLandmarks;
  bool _handDetected = false;

  // Face detection variables
  bool _faceDetected = false;
  Map<String, dynamic>? _faceBbox;
  String _expression = 'Unknown';

  // 🌟 Continuous Sentence Detection & Builder
  bool _sentenceMode = true; // Toggle between Sentence Mode and Word Mode
  bool _autoAddEnabled = true;
  List<String> _sentenceWords = [];
  String _englishSentence = '';
  String _hindiSentence = '';
  String _marathiSentence = '';
  String _candidateSign = '';
  int _candidateFrames = 0;
  String _lastCommittedWord = '';

  // Trilingual instant dictionary for all 95 ISL signs
  static const Map<String, Map<String, String>> _signDictionary = {
    'Hello': {'en': 'Hello', 'hi': 'नमस्ते', 'mr': 'नमस्कार'},
    'Goodbye': {'en': 'Goodbye', 'hi': 'अलविदा', 'mr': 'पुन्हा भेटू'},
    'Welcome': {'en': 'Welcome', 'hi': 'स्वागत है', 'mr': 'सुस्वागतम'},
    'Good Morning': {'en': 'Good Morning', 'hi': 'सुप्रभात', 'mr': 'शुभ सकाळ'},
    'Good Night': {'en': 'Good Night', 'hi': 'शुभ रात्रि', 'mr': 'शुभ रात्री'},
    'Yes': {'en': 'Yes', 'hi': 'हाँ', 'mr': 'होय'},
    'No': {'en': 'No', 'hi': 'नहीं', 'mr': 'नाही'},
    'Maybe': {'en': 'Maybe', 'hi': 'शायद', 'mr': 'कदाचित'},
    'OK': {'en': 'OK', 'hi': 'ठीक है', 'mr': 'ठीक आहे'},
    'Agree': {'en': 'Agree', 'hi': 'सहमत', 'mr': 'मान्य आहे'},
    'Happy': {'en': 'Happy', 'hi': 'खुश', 'mr': 'आनंदी'},
    'Sad': {'en': 'Sad', 'hi': 'दुःख', 'mr': 'दुःखी'},
    'Angry': {'en': 'Angry', 'hi': 'क्रोधित', 'mr': 'रागवला'},
    'Scared': {'en': 'Scared', 'hi': 'डरा हुआ', 'mr': 'घाबरलेला'},
    'Surprised': {'en': 'Surprised', 'hi': 'आश्चर्यचकित', 'mr': 'आश्चर्यचकित'},
    'Love': {'en': 'Love', 'hi': 'प्यार', 'mr': 'प्रेम'},
    'Tired': {'en': 'Tired', 'hi': 'थका हुआ', 'mr': 'थकलेला'},
    'Confused': {'en': 'Confused', 'hi': 'भ्रमित', 'mr': 'गोंधळलेला'},
    'Walk': {'en': 'Walk', 'hi': 'चलना', 'mr': 'चालणे'},
    'Run': {'en': 'Run', 'hi': 'दौड़ना', 'mr': 'धावणे'},
    'Jump': {'en': 'Jump', 'hi': 'कूदना', 'mr': 'उडी मारणे'},
    'Sit': {'en': 'Sit', 'hi': 'बैठना', 'mr': 'बसणे'},
    'Stand': {'en': 'Stand', 'hi': 'खड़ा होना', 'mr': 'उभे राहणे'},
    'Sleep': {'en': 'Sleep', 'hi': 'सोना', 'mr': 'झोपणे'},
    'Wake Up': {'en': 'Wake Up', 'hi': 'जागना', 'mr': 'उठणे'},
    'Dance': {'en': 'Dance', 'hi': 'नृत्य', 'mr': 'नाचणे'},
    'Eat': {'en': 'Eat', 'hi': 'खाना', 'mr': 'खाणे'},
    'Drink': {'en': 'Drink', 'hi': 'पीना', 'mr': 'पिणे'},
    'Work': {'en': 'Work', 'hi': 'काम', 'mr': 'काम करणे'},
    'Play': {'en': 'Play', 'hi': 'खेलना', 'mr': 'खेळणे'},
    'Read': {'en': 'Read', 'hi': 'पढ़ना', 'mr': 'वाचणे'},
    'Write': {'en': 'Write', 'hi': 'लिखना', 'mr': 'लिहीणे'},
    'Listen': {'en': 'Listen', 'hi': 'सुनना', 'mr': 'ऐकणे'},
    'Look': {'en': 'Look', 'hi': 'देखना', 'mr': 'पाहणे'},
    'Help': {'en': 'Help', 'hi': 'मदद', 'mr': 'मदत'},
    'Give': {'en': 'Give', 'hi': 'देना', 'mr': 'देणे'},
    'Take': {'en': 'Take', 'hi': 'लेना', 'mr': 'घेणे'},
    'Water': {'en': 'Water', 'hi': 'पानी', 'mr': 'पाणी'},
    'Food': {'en': 'Food', 'hi': 'खाना', 'mr': 'जेवण'},
    'House': {'en': 'House', 'hi': 'घर', 'mr': 'घर'},
    'Car': {'en': 'Car', 'hi': 'कार', 'mr': 'गाडी'},
    'Phone': {'en': 'Phone', 'hi': 'फोन', 'mr': 'फोन'},
    'Book': {'en': 'Book', 'hi': 'किताब', 'mr': 'पुस्तक'},
    'School': {'en': 'School', 'hi': 'स्कूल', 'mr': 'शाळा'},
    'Money': {'en': 'Money', 'hi': 'पैसा', 'mr': 'पैसे'},
    'Clock': {'en': 'Clock', 'hi': 'घड़ी', 'mr': 'घड्याळ'},
    'Doctor': {'en': 'Doctor', 'hi': 'डॉक्टर', 'mr': 'डॉक्टर'},
    'Good': {'en': 'Good', 'hi': 'अच्छा', 'mr': 'चांगले'},
    'Bad': {'en': 'Bad', 'hi': 'बुरा', 'mr': 'वाईट'},
    'Beautiful': {'en': 'Beautiful', 'hi': 'सुंदर', 'mr': 'सुंदर'},
    'Ugly': {'en': 'Ugly', 'hi': 'बदसूरत', 'mr': 'कुरूप'},
    'Big': {'en': 'Big', 'hi': 'बड़ा', 'mr': 'मोठे'},
    'Small': {'en': 'Small', 'hi': 'छोटा', 'mr': 'लहान'},
    'Hot': {'en': 'Hot', 'hi': 'गर्म', 'mr': 'गरम'},
    'Cold': {'en': 'Cold', 'hi': 'ठंडा', 'mr': 'थंड'},
    'Strong': {'en': 'Strong', 'hi': 'मजबूत', 'mr': 'मजबूत'},
    'Weak': {'en': 'Weak', 'hi': 'कमजोर', 'mr': 'कमकुवत'},
    'Fast': {'en': 'Fast', 'hi': 'तेज', 'mr': 'जलद'},
    'Slow': {'en': 'Slow', 'hi': 'धीमा', 'mr': 'हळू'},
    'Clean': {'en': 'Clean', 'hi': 'साफ', 'mr': 'स्वच्छ'},
    'Dirty': {'en': 'Dirty', 'hi': 'गंदा', 'mr': 'घाणेरडे'},
    'Mother': {'en': 'Mother', 'hi': 'माता', 'mr': 'आई'},
    'Father': {'en': 'Father', 'hi': 'पिता', 'mr': 'बाबा'},
    'Sister': {'en': 'Sister', 'hi': 'बहन', 'mr': 'बहीण'},
    'Brother': {'en': 'Brother', 'hi': 'भाई', 'mr': 'भाऊ'},
    'Baby': {'en': 'Baby', 'hi': 'बच्चा', 'mr': 'बाळ'},
    'Grandfather': {'en': 'Grandfather', 'hi': 'दादा', 'mr': 'आजोबा'},
    'Grandmother': {'en': 'Grandmother', 'hi': 'दादी', 'mr': 'आजी'},
    'Husband': {'en': 'Husband', 'hi': 'पति', 'mr': 'पती'},
    'Wife': {'en': 'Wife', 'hi': 'पत्नी', 'mr': 'पत्नी'},
    'Friend': {'en': 'Friend', 'hi': 'मित्र', 'mr': 'मित्र'},
    'Please': {'en': 'Please', 'hi': 'कृपया', 'mr': 'कृपया'},
    'Thank You': {'en': 'Thank You', 'hi': 'धन्यवाद', 'mr': 'धन्यवाद'},
    'Sorry': {'en': 'Sorry', 'hi': 'माफी', 'mr': 'माफ करा'},
    'Excuse Me': {'en': 'Excuse Me', 'hi': 'माफ कीजिए', 'mr': 'क्षमा करा'},
    'Learn': {'en': 'Learn', 'hi': 'सीखना', 'mr': 'शिकणे'},
    'Understand': {'en': 'Understand', 'hi': 'समझना', 'mr': 'समजणे'},
    'Forget': {'en': 'Forget', 'hi': 'भूलना', 'mr': 'विसरणे'},
    'Remember': {'en': 'Remember', 'hi': 'याद रखना', 'mr': 'आठवणे'},
    'Think': {'en': 'Think', 'hi': 'सोचना', 'mr': 'विचार करणे'},
    'Today': {'en': 'Today', 'hi': 'आज', 'mr': 'आज'},
    'Tomorrow': {'en': 'Tomorrow', 'hi': 'कल', 'mr': 'उद्या'},
    'Yesterday': {'en': 'Yesterday', 'hi': 'कल', 'mr': 'काल'},
    'Morning': {'en': 'Morning', 'hi': 'सुबह', 'mr': 'सकाळ'},
    'Evening': {'en': 'Evening', 'hi': 'शाम', 'mr': 'संध्याकाळ'},
    'Night': {'en': 'Night', 'hi': 'रात', 'mr': 'रात्र'},
    'One': {'en': 'One', 'hi': 'एक', 'mr': 'एक'},
    'Two': {'en': 'Two', 'hi': 'दो', 'mr': 'दोन'},
    'Three': {'en': 'Three', 'hi': 'तीन', 'mr': 'तीन'},
    'Five': {'en': 'Five', 'hi': 'पाँच', 'mr': 'पाच'},
    'Ten': {'en': 'Ten', 'hi': 'दस', 'mr': 'दहा'},
    'Pain': {'en': 'Pain', 'hi': 'दर्द', 'mr': 'दुखणे'},
    'Sick': {'en': 'Sick', 'hi': 'बीमार', 'mr': 'आजारी'},
    'Health': {'en': 'Health', 'hi': 'स्वास्थ्य', 'mr': 'आरोग्य'},
    'Hospital': {'en': 'Hospital', 'hi': 'अस्पताल', 'mr': 'रुग्णालय'},
  };

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  bool _isDisposed = false;
  bool _isLoopRunning = false;

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
          ResolutionPreset.low, // 320x240 for silky-smooth preview and rapid mobile AI inference
          enableAudio: false,
          imageFormatGroup: ImageFormatGroup.jpeg,
        );

        await _cameraController!.initialize();

        if (mounted) {
          setState(() {});
          if (widget.isActive) {
            _startDetectionLoop();
          }
        }
      }
    } catch (e) {
      print('Error initializing camera: $e');
    }
  }

  @override
  void didUpdateWidget(TranslateScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isActive != oldWidget.isActive) {
      if (widget.isActive) {
        _startDetectionLoop();
      } else {
        _isLoopRunning = false;
        _frameTimer?.cancel();
        _frameTimer = null;
      }
    }
  }

  void _startDetectionLoop() {
    if (_isLoopRunning) return;
    _isLoopRunning = true;
    _runContinuousDetection();
  }

  Future<void> _runContinuousDetection() async {
    while (mounted && !_isDisposed && widget.isActive && _isLoopRunning) {
      if (_cameraController != null &&
          _cameraController!.value.isInitialized &&
          !_isDetecting) {
        setState(() => _isDetecting = true);

        try {
          final imageFile = await _cameraController!.takePicture();
          final bytes = await imageFile.readAsBytes();

          // Downscale & compress to ultra-lightweight JPEG (~15KB) so mobile network never chokes
          String base64Image;
          if (bytes.length > 60 * 1024) {
            try {
              final decoded = img.decodeImage(bytes);
              if (decoded != null) {
                final resized = img.copyResize(decoded, width: 320);
                final compressed = img.encodeJpg(resized, quality: 55);
                base64Image = base64Encode(compressed);
              } else {
                base64Image = base64Encode(bytes);
              }
            } catch (_) {
              base64Image = base64Encode(bytes);
            }
          } else {
            base64Image = base64Encode(bytes);
          }

          await _detectSign(base64Image);
        } catch (e) {
          print('Frame capture/detection notice: $e');
        } finally {
          if (mounted) {
            setState(() => _isDetecting = false);
          }
        }
      }
      // Wait 700ms between frames to keep the camera preview buttery smooth
      await Future.delayed(const Duration(milliseconds: 700));
    }
    _isLoopRunning = false;
  }

  Future<void> _detectSign(String base64Image) async {
    try {
      final authService = context.read<AuthService>();
      final token = authService.accessToken;

      final headers = Map<String, String>.from(ApiConfig.defaultHeaders);
      if (token != null && token.isNotEmpty && token != 'null') {
        headers['Authorization'] = 'Bearer $token';
      }

      final response = await http.post(
        Uri.parse(ApiConfig.detectFrameEndpoint),
        headers: headers,
        body: jsonEncode({
          'frame': base64Image,
          'min_confidence': 0.20
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (mounted) {
          final landmarks = data['landmarks'] as List?;
          final handDetected = data['hand_detected'] == true || (landmarks != null && landmarks.isNotEmpty);
          final rawSign = data['sign'] ?? 'Unknown';
          final conf = (data['confidence'] ?? 0.0).toDouble();

          setState(() {
            _liveHandLandmarks = landmarks;
            _handDetected = handDetected;
            _detectedSign = rawSign;
            _confidence = conf;
            _faceDetected = data['face_detected'] ?? false;
            _faceBbox = data['face_bbox'];
            _expression = data['expression'] ?? 'Unknown';

            if (_detectedSign != 'Unknown' && _confidence > 0.35) {
              // Add to history
              final existingIndex = _detectionHistory.indexWhere((h) => h['sign'] == _detectedSign);
              if (existingIndex != -1) {
                _detectionHistory.removeAt(existingIndex);
              }
              _detectionHistory.insert(0, {
                'sign': _detectedSign,
                'confidence': _confidence,
                'expression': _expression,
                'timestamp': DateTime.now(),
              });
              if (_detectionHistory.length > 10) {
                _detectionHistory.removeLast();
              }

              // ⚡ Automatic Continuous Sentence Detection Debouncer
              if (_detectedSign == _candidateSign) {
                _candidateFrames++;
                // If held stably for 2 frames (~1.4s), commit to sentence
                if (_autoAddEnabled && _candidateFrames == 2 && _detectedSign != _lastCommittedWord) {
                  _addSignToSentence(_detectedSign);
                  _lastCommittedWord = _detectedSign;
                }
              } else {
                _candidateSign = _detectedSign;
                _candidateFrames = 1;
              }
            } else if (!handDetected) {
              _candidateSign = '';
              _candidateFrames = 0;
              _lastCommittedWord = ''; // Reset so same sign can be added again after rest
            }
          });
        }
      }
    } on TimeoutException {
      print('Frame detection timeout');
    } catch (e) {
      print('Detection request error: $e');
    }
  }

  void _addSignToSentence(String sign) {
    if (sign.isEmpty || sign == 'Unknown' || sign == 'No sign detected') return;
    setState(() {
      _sentenceWords.add(sign);
      _updateSentenceTranslations();
    });
  }

  void _removeLastWord() {
    if (_sentenceWords.isNotEmpty) {
      setState(() {
        _sentenceWords.removeLast();
        _lastCommittedWord = '';
        _updateSentenceTranslations();
      });
    }
  }

  void _clearSentence() {
    setState(() {
      _sentenceWords.clear();
      _englishSentence = '';
      _hindiSentence = '';
      _marathiSentence = '';
      _lastCommittedWord = '';
    });
  }

  void _updateSentenceTranslations() {
    if (_sentenceWords.isEmpty) {
      _englishSentence = '';
      _hindiSentence = '';
      _marathiSentence = '';
      return;
    }

    // Instant local translation
    _englishSentence = _sentenceWords.map((w) => _signDictionary[w]?['en'] ?? w).join(' ');
    _hindiSentence = _sentenceWords.map((w) => _signDictionary[w]?['hi'] ?? w).join(' ');
    _marathiSentence = _sentenceWords.map((w) => _signDictionary[w]?['mr'] ?? w).join(' ');

    // Grammar-smoothed backend translation
    _fetchGrammarSmoothedSentence();
  }

  Future<void> _fetchGrammarSmoothedSentence() async {
    try {
      final authService = context.read<AuthService>();
      final res = await http.post(
        Uri.parse(ApiConfig.sentenceEndpoint),
        headers: {
          ...ApiConfig.defaultHeaders,
          'Authorization': 'Bearer ${authService.accessToken}',
        },
        body: jsonEncode({'signs': _sentenceWords}),
      );

      if (res.statusCode == 200 && mounted) {
        final data = jsonDecode(res.body);
        setState(() {
          if (data['english'] != null && data['english'].toString().isNotEmpty) {
            _englishSentence = data['english'];
          }
          if (data['hindi'] != null && data['hindi'].toString().isNotEmpty) {
            _hindiSentence = data['hindi'];
          }
          if (data['marathi'] != null && data['marathi'].toString().isNotEmpty) {
            _marathiSentence = data['marathi'];
          }
        });
      }
    } catch (e) {
      print('Notice: grammar translation sync: $e');
    }
  }

  void _copySentence() {
    if (_englishSentence.isEmpty) return;
    final text = "ISL Translation:\n🇬🇧 $_englishSentence\n🇮🇳 $_hindiSentence\n🚩 $_marathiSentence";
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Sentence copied to clipboard! 📋'),
        backgroundColor: Colors.deepPurple,
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _clearHistory() {
    setState(() {
      _detectionHistory.clear();
      _detectedSign = 'No sign detected';
      _confidence = 0.0;
      _liveHandLandmarks = null;
      _handDetected = false;
      _faceDetected = false;
      _faceBbox = null;
      _expression = 'Unknown';
    });
  }

  String _getExpressionEmoji(String expression) {
    switch (expression.toLowerCase()) {
      case 'happy':
        return '😊';
      case 'sad':
        return '😢';
      case 'surprised':
        return '😲';
      case 'angry':
        return '😠';
      case 'wink left':
      case 'wink right':
        return '😜';
      case 'blink':
        return '😴';
      case 'neutral':
      default:
        return '😐';
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    _isLoopRunning = false;
    _frameTimer?.cancel();
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Live ISL Translation',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.deepPurple,
        foregroundColor: Colors.white,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Mode Switcher Banner (Sentence Mode vs Word Mode)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: Colors.deepPurple.shade50,
              child: Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () => setState(() => _sentenceMode = true),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: _sentenceMode ? Colors.deepPurple : Colors.transparent,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.auto_stories,
                              size: 16,
                              color: _sentenceMode ? Colors.white : Colors.deepPurple,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Sentence Mode 📝',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                                color: _sentenceMode ? Colors.white : Colors.deepPurple,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: InkWell(
                      onTap: () => setState(() => _sentenceMode = false),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: !_sentenceMode ? Colors.deepPurple : Colors.transparent,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.spellcheck,
                              size: 16,
                              color: !_sentenceMode ? Colors.white : Colors.deepPurple,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Word Mode 🔤',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                                color: !_sentenceMode ? Colors.white : Colors.deepPurple,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Camera Preview & Live Skeleton Movement Overlay
            Container(
              width: double.infinity,
              height: 340,
              decoration: BoxDecoration(
                color: Colors.black,
                border: Border.all(color: Colors.deepPurple, width: 2),
              ),
              child: Stack(
                children: [
                  Positioned.fill(
                    child: CameraPreview(_cameraController!),
                  ),

                  // Real-time Live Hand Skeleton Movement Tracking Overlay
                  if (_liveHandLandmarks != null && _liveHandLandmarks!.isNotEmpty)
                    Positioned.fill(
                      child: CustomPaint(
                        painter: LiveHandTrackingPainter(
                          keypoints: _liveHandLandmarks,
                          isMatched: _detectedSign != 'Unknown' && _confidence > 0.4,
                          mirrorFrontCamera: true,
                        ),
                      ),
                    ),

                  // Hand Tracking Pill Indicator (Top Right)
                  Positioned(
                    top: 10,
                    right: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.65),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: _handDetected ? Colors.cyanAccent : Colors.white24,
                          width: 1.0,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 7,
                            height: 7,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: _handDetected ? Colors.cyanAccent : Colors.grey,
                            ),
                          ),
                          const SizedBox(width: 5),
                          Text(
                            _handDetected ? 'Hand Tracking ✋' : 'No Hand',
                            style: TextStyle(
                              color: _handDetected ? Colors.cyanAccent : Colors.white70,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Face bounding box overlay
                  if (_faceDetected && _faceBbox != null)
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final w = constraints.maxWidth;
                        final h = constraints.maxHeight;
                        final boxX = _faceBbox!['x'] * w;
                        final boxY = _faceBbox!['y'] * h;
                        final boxW = _faceBbox!['w'] * w;
                        final boxH = _faceBbox!['h'] * h;
                        return Positioned(
                          left: boxX,
                          top: boxY,
                          width: boxW,
                          height: boxH,
                          child: Container(
                            decoration: BoxDecoration(
                              border: Border.all(color: Colors.green, width: 2),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Align(
                              alignment: Alignment.topLeft,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                color: Colors.green,
                                child: Text(
                                  _expression,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),

                  if (_isDetecting)
                    Positioned(
                      top: 10,
                      left: 10,
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.6),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.cyanAccent),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),

            // 🌟 LIVE SENTENCE BUILDER CARD (Visible in Sentence Mode or when words are formed)
            if (_sentenceMode || _sentenceWords.isNotEmpty)
              Container(
                margin: const EdgeInsets.all(16),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Colors.deepPurple.shade700, Colors.indigo.shade900],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.deepPurple.withOpacity(0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.auto_stories, color: Colors.cyanAccent, size: 20),
                            const SizedBox(width: 8),
                            const Text(
                              'Live Sentence / वाक्य रचना',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ],
                        ),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                '${_sentenceWords.length} Words',
                                style: const TextStyle(color: Colors.cyanAccent, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(width: 6),
                            InkWell(
                              onTap: () => setState(() => _autoAddEnabled = !_autoAddEnabled),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                                decoration: BoxDecoration(
                                  color: _autoAddEnabled ? Colors.green.shade700 : Colors.grey.shade700,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  _autoAddEnabled ? 'Auto ⚡' : 'Manual',
                                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Signs sequence chips
                    if (_sentenceWords.isNotEmpty) ...[
                      SizedBox(
                        height: 36,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount: _sentenceWords.length,
                          separatorBuilder: (context, index) => const Icon(Icons.chevron_right, color: Colors.white54, size: 16),
                          itemBuilder: (context, index) {
                            return Chip(
                              label: Text(
                                _sentenceWords[index],
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                              ),
                              backgroundColor: Colors.deepPurple.shade400,
                              padding: const EdgeInsets.symmetric(horizontal: 4),
                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            );
                          },
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],

                    // Multilingual Sentence Output Box
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white12),
                      ),
                      child: _sentenceWords.isEmpty
                          ? const Text(
                              'Perform signs in front of camera to form a sentence. Signs held stably are automatically assembled into natural speech.',
                              style: TextStyle(color: Colors.white60, fontSize: 13, fontStyle: FontStyle.italic),
                            )
                          : Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('🇬🇧 ', style: TextStyle(fontSize: 15)),
                                    Expanded(
                                      child: Text(
                                        _englishSentence,
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 16,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('🇮🇳 ', style: TextStyle(fontSize: 15)),
                                    Expanded(
                                      child: Text(
                                        _hindiSentence,
                                        style: const TextStyle(
                                          color: Colors.amberAccent,
                                          fontSize: 15,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('🚩 ', style: TextStyle(fontSize: 15)),
                                    Expanded(
                                      child: Text(
                                        _marathiSentence,
                                        style: const TextStyle(
                                          color: Colors.cyanAccent,
                                          fontSize: 15,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                    ),
                    const SizedBox(height: 12),

                    // Sentence Action Toolbar
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ElevatedButton.icon(
                          onPressed: (_detectedSign != 'Unknown' && _detectedSign != 'No sign detected')
                              ? () => _addSignToSentence(_detectedSign)
                              : null,
                          icon: const Icon(Icons.add, size: 16),
                          label: Text(_detectedSign != 'Unknown' && _detectedSign != 'No sign detected'
                              ? 'Add "$_detectedSign"'
                              : 'Add Word'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.cyanAccent.shade700,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _sentenceWords.isNotEmpty ? _removeLastWord : null,
                          icon: const Icon(Icons.backspace_outlined, size: 16),
                          label: const Text('Backspace'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.orange.shade700,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            textStyle: const TextStyle(fontSize: 12),
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _sentenceWords.isNotEmpty ? _clearSentence : null,
                          icon: const Icon(Icons.delete_sweep, size: 16),
                          label: const Text('Clear'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red.shade700,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            textStyle: const TextStyle(fontSize: 12),
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _sentenceWords.isNotEmpty ? _copySentence : null,
                          icon: const Icon(Icons.copy, size: 16),
                          label: const Text('Copy'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.blueGrey.shade700,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            textStyle: const TextStyle(fontSize: 12),
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _sentenceWords.isNotEmpty
                              ? () => TtsService.speak(_englishSentence, lang: 'en-US')
                              : null,
                          icon: const Icon(Icons.volume_up, size: 16),
                          label: const Text('Speak (EN)'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.teal.shade700,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            textStyle: const TextStyle(fontSize: 12),
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _sentenceWords.isNotEmpty
                              ? () => TtsService.speak(_hindiSentence, lang: 'hi-IN')
                              : null,
                          icon: const Icon(Icons.record_voice_over, size: 16),
                          label: const Text('बोलें (HI)'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.deepOrange.shade700,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            textStyle: const TextStyle(fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

            // Live Single Sign Detection Result Card
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.deepPurple.shade100.withOpacity(0.5),
                      Colors.blue.shade100.withOpacity(0.5),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: Colors.deepPurple.shade300),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Detected Sign / संकेत',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.black54,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (_faceDetected)
                          Row(
                            children: [
                              Text(
                                '${_getExpressionEmoji(_expression)} $_expression',
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.deepPurple,
                                ),
                              ),
                            ],
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _detectedSign,
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Colors.deepPurple,
                      ),
                    ),
                    if (_signDictionary[_detectedSign] != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        '🇮🇳 ${_signDictionary[_detectedSign]!['hi']}  •  🚩 ${_signDictionary[_detectedSign]!['mr']}',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.black87),
                      ),
                    ],
                    const SizedBox(height: 10),
                    LinearProgressIndicator(
                      value: _confidence,
                      minHeight: 6,
                      backgroundColor: Colors.grey.shade300,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        _confidence > 0.65 ? Colors.green : Colors.orange,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Confidence: ${(_confidence * 100).toStringAsFixed(1)}%',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Controls
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        if (_isLoopRunning) {
                          setState(() {
                            _isLoopRunning = false;
                            _detectedSign = 'Detection paused';
                            _confidence = 0.0;
                          });
                        } else {
                          setState(() {
                            _startDetectionLoop();
                          });
                        }
                      },
                      icon: Icon(
                        _isLoopRunning
                            ? Icons.pause
                            : Icons.play_arrow,
                      ),
                      label: Text(
                        _isLoopRunning
                            ? 'Pause Detection'
                            : 'Resume Detection',
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.deepPurple,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _clearHistory,
                      icon: const Icon(Icons.clear),
                      label: const Text('Clear History'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red.shade600,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // History
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Detection History',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (_detectionHistory.isEmpty)
                    Container(
                      padding: const EdgeInsets.all(16),
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Center(
                        child: Text('No detections yet', style: TextStyle(color: Colors.black54)),
                      ),
                    )
                  else
                    ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _detectionHistory.length,
                      itemBuilder: (context, index) {
                        final item = _detectionHistory[index];
                        return Container(
                          margin: const EdgeInsets.only(bottom: 6),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            border: Border.all(color: Colors.grey.shade300),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    item['sign'],
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 15,
                                    ),
                                  ),
                                  Text(
                                    '${_signDictionary[item['sign']]?['hi'] ?? ''} • ${((item['confidence'] as double) * 100).toStringAsFixed(1)}% • ${item['expression']}',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey.shade600,
                                    ),
                                  ),
                                ],
                              ),
                              Text(
                                '${(item['timestamp'] as DateTime).hour.toString().padLeft(2, '0')}:${(item['timestamp'] as DateTime).minute.toString().padLeft(2, '0')}:${(item['timestamp'] as DateTime).second.toString().padLeft(2, '0')}',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey.shade600,
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
