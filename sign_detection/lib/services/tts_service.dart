import 'package:flutter/foundation.dart';
import 'tts_stub.dart' if (dart.library.js) 'tts_web.dart' as tts_impl;

class TtsService {
  static void speak(String text, {String lang = 'en-US'}) {
    if (kIsWeb) {
      tts_impl.speakWeb(text, lang: lang);
    }
  }
}
