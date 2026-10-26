// ignore: avoid_web_libraries_in_flutter
import 'dart:js' as js;

void speakWeb(String text, {String lang = 'en-US'}) {
  try {
    final sanitized = text.replaceAll("'", "\\'").replaceAll('"', '\\"');
    js.context.callMethod('eval', [
      "if ('speechSynthesis' in window) { "
      "  window.speechSynthesis.cancel(); "
      "  const u = new SpeechSynthesisUtterance('$sanitized'); "
      "  u.lang = '$lang'; "
      "  u.rate = 0.95; "
      "  window.speechSynthesis.speak(u); "
      "}"
    ]);
  } catch (e) {
    // ignore: avoid_print
    print('Web TTS error: $e');
  }
}
