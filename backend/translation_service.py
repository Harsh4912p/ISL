import json
from pathlib import Path
from typing import Dict, List, Tuple

class TranslationService:
    def __init__(self):
        self.translations = self._load_translations()
        self.sign_to_words = self._build_sign_to_words_map()

    def _load_translations(self) -> Dict:
        translations = {}
        try:
            from dataset_loader import DatasetLoader
            loader = DatasetLoader()
            dataset = loader.load_sign_language_dataset()
            for idx, item in enumerate(dataset):
                translations[str(idx)] = {
                    'english': item['name'],
                    'hindi': item.get('hindi_translation', item['name']),
                    'marathi': item.get('marathi_translation', item['name']),
                    'words': [item['name'].lower()]
                }
            if translations:
                return translations
        except Exception as e:
            print(f"Notice loading dataset translations: {e}")
        return self._get_default_translations()

    def _get_default_translations(self) -> Dict:
        return {
            '0': {'english': 'Hello', 'hindi': 'नमस्ते', 'marathi': 'नमस्कार', 'words': ['hello', 'greetings', 'hi']},
            '1': {'english': 'Thank You', 'hindi': 'धन्यवाद', 'marathi': 'धन्यवाद', 'words': ['thank', 'thanks']},
            '2': {'english': 'Yes', 'hindi': 'हाँ', 'marathi': 'होय', 'words': ['yes']},
            '3': {'english': 'No', 'hindi': 'नहीं', 'marathi': 'नाही', 'words': ['no']},
            '4': {'english': 'Water', 'hindi': 'पानी', 'marathi': 'पाणी', 'words': ['water']},
            '5': {'english': 'Food', 'hindi': 'खाना', 'marathi': 'जेवण', 'words': ['food', 'eat']},
            '6': {'english': 'Good', 'hindi': 'अच्छा', 'marathi': 'चांगले', 'words': ['good']},
            '7': {'english': 'Bad', 'hindi': 'बुरा', 'marathi': 'वाईट', 'words': ['bad']},
            '8': {'english': 'Help', 'hindi': 'मदद', 'marathi': 'मदत', 'words': ['help']},
            '9': {'english': 'Please', 'hindi': 'कृपया', 'marathi': 'कृपया', 'words': ['please']},
        }

    def _build_sign_to_words_map(self) -> Dict[str, Dict]:
        sign_map = {}
        for sign_id, trans in self.translations.items():
            english = trans.get('english', '')
            words = trans.get('words', [english.lower()])
            sign_map[english.lower()] = {
                'english': english,
                'hindi': trans.get('hindi', english),
                'marathi': trans.get('marathi', english),
                'variations': words
            }
        return sign_map

    def translate_sign(self, sign_name: str, target_language: str = 'english') -> str:
        """Translate a single sign to target language ('english', 'hindi', 'marathi')"""
        sign_lower = sign_name.lower().strip()

        for sign_id, trans in self.translations.items():
            if trans.get('english', '').lower() == sign_lower:
                return trans.get(target_language, sign_name)

        for sign_lower_map, trans_map in self.sign_to_words.items():
            if sign_lower_map == sign_lower:
                return trans_map.get(target_language, sign_name)

        return sign_name

    def build_sentence(self, signs: List[str], target_language: str = 'english') -> str:
        """Build a smooth, natural sentence from detected signs"""
        if not signs:
            return ""

        clean_signs = [s.strip() for s in signs if s.strip()]
        if not clean_signs:
            return ""

        upper_seq = " ".join([s.upper() for s in clean_signs])

        # Common ISL idiom patterns smoothed to natural sentences
        idioms = {
            'WATER DRINK': {
                'english': 'I want to drink water.',
                'hindi': 'मुझे पानी पीना है।',
                'marathi': 'मला पाणी प्यायचे आहे.'
            },
            'FOOD EAT': {
                'english': 'I want to eat food.',
                'hindi': 'मुझे खाना खाना है।',
                'marathi': 'मला जेवण करायचे आहे.'
            },
            'PLEASE HELP': {
                'english': 'Please help me.',
                'hindi': 'कृपया मेरी मदद करें।',
                'marathi': 'कृपया मला मदत करा.'
            },
            'HELLO DOCTOR HELP': {
                'english': 'Hello Doctor, please help me.',
                'hindi': 'नमस्ते डॉक्टर, कृपया मेरी मदद करें।',
                'marathi': 'नमस्कार डॉक्टर, कृपया मला मदत करा.'
            },
            'HELLO HOW ARE YOU': {
                'english': 'Hello, how are you?',
                'hindi': 'नमस्ते, आप कैसे हैं?',
                'marathi': 'नमस्कार, तुम्ही कसे आहात?'
            },
            'THANK YOU GOODBYE': {
                'english': 'Thank you and goodbye!',
                'hindi': 'धन्यवाद और अलविदा!',
                'marathi': 'धन्यवाद आणि पुन्हा भेटू!'
            }
        }

        for idiom_key, idiom_trans in idioms.items():
            if idiom_key in upper_seq:
                return idiom_trans.get(target_language, idiom_trans['english'])

        # General word-by-word sentence formation
        translated_words = []
        for sign in clean_signs:
            t = self.translate_sign(sign, target_language)
            if t:
                translated_words.append(t)

        sentence = " ".join(translated_words)
        if target_language == 'english' and sentence:
            sentence = sentence[0].upper() + sentence[1:]
        return sentence

    def translate_all(self, signs: List[str]) -> Dict[str, str]:
        """Translate a sign sequence into English, Hindi, and Marathi sentences"""
        return {
            'english': self.build_sentence(signs, 'english'),
            'hindi': self.build_sentence(signs, 'hindi'),
            'marathi': self.build_sentence(signs, 'marathi')
        }

    def detect_paragraph_signs(self, detected_signs: List[Dict]) -> Dict:
        """Process multiple detected signs and build a paragraph"""
        unique_signs = []
        seen = set()

        for detection in detected_signs:
            sign = detection.get('sign')
            if sign and sign.lower() not in seen:
                unique_signs.append(sign)
                seen.add(sign.lower())

        english_paragraph = self.build_sentence(unique_signs, 'english')
        hindi_paragraph = self.build_sentence(unique_signs, 'hindi')
        marathi_paragraph = self.build_sentence(unique_signs, 'marathi')

        return {
            'signs': unique_signs,
            'english_paragraph': english_paragraph,
            'hindi_paragraph': hindi_paragraph,
            'marathi_paragraph': marathi_paragraph,
            'total_signs': len(unique_signs),
            'total_detections': len(detected_signs)
        }

    def get_sign_details(self, sign_name: str) -> Dict:
        """Get detailed information about a sign including translations"""
        sign_lower = sign_name.lower()

        for sign_id, trans in self.translations.items():
            if trans.get('english', '').lower() == sign_lower:
                return {
                    'id': sign_id,
                    'english': trans.get('english'),
                    'hindi': trans.get('hindi'),
                    'variations': trans.get('words', []),
                    'confidence': 0.0
                }

        return {
            'english': sign_name,
            'hindi': sign_name,
            'variations': [sign_name.lower()],
            'confidence': 0.0
        }

    def get_all_signs(self) -> List[Dict]:
        """Get all available signs with translations"""
        signs = []
        for sign_id, trans in self.translations.items():
            signs.append({
                'id': sign_id,
                'english': trans.get('english'),
                'hindi': trans.get('hindi'),
                'variations': trans.get('words', [])
            })
        return signs

    def fuzzy_match_sign(self, input_text: str) -> Tuple[str, float]:
        """Find closest matching sign for input text"""
        from difflib import SequenceMatcher

        input_lower = input_text.lower().strip()
        best_match = None
        best_ratio = 0.0

        for sign_lower_map, trans_map in self.sign_to_words.items():
            ratio = SequenceMatcher(None, input_lower, sign_lower_map).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = trans_map.get('english')

        return (best_match, best_ratio) if best_match else (input_text, 0.0)

    def expand_abbreviations(self, text: str) -> str:
        """Expand common abbreviations in sign language"""
        expansions = {
            'u': 'you',
            'r': 'are',
            'ur': 'your',
            'b4': 'before',
            '2': 'to',
            'c': 'see',
            '4u': 'for you'
        }

        words = text.split()
        expanded = []

        for word in words:
            expanded.append(expansions.get(word.lower(), word))

        return ' '.join(expanded)

    def validate_sign_sequence(self, signs: List[str]) -> Dict:
        """Validate if a sequence of signs makes sense"""
        analysis = {
            'valid_signs': [],
            'invalid_signs': [],
            'confidence': 0.0,
            'suggestions': []
        }

        for sign in signs:
            details = self.get_sign_details(sign)
            if details and details.get('english') != sign:
                analysis['valid_signs'].append(details)
            else:
                closest, ratio = self.fuzzy_match_sign(sign)
                if ratio > 0.7:
                    analysis['suggestions'].append({
                        'original': sign,
                        'suggested': closest,
                        'confidence': ratio
                    })
                    analysis['valid_signs'].append(self.get_sign_details(closest))
                else:
                    analysis['invalid_signs'].append(sign)

        analysis['confidence'] = len(analysis['valid_signs']) / max(len(signs), 1)

        return analysis
