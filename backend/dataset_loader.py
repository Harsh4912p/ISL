import json
import os
from pathlib import Path
from models import db, Sign
import random

class DatasetLoader:
    def __init__(self):
        self.datasets_path = Path('datasets')

    def load_sign_language_dataset(self):
        large_dataset = self._generate_comprehensive_dataset()
        return large_dataset

    def _generate_comprehensive_dataset(self):
        dataset = [
            # Greetings & Communication
            {'name': 'Hello', 'english_translation': 'Hello / Greetings', 'hindi_translation': 'नमस्ते', 'marathi_translation': 'नमस्कार', 'description': 'Waving hand gesture to greet someone', 'category': 'Greetings', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Goodbye', 'english_translation': 'Goodbye / Farewell', 'hindi_translation': 'अलविदा', 'marathi_translation': 'पुन्हा भेटू', 'description': 'Waving hand while moving it side to side', 'category': 'Greetings', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Welcome', 'english_translation': 'Welcome', 'hindi_translation': 'स्वागत है', 'marathi_translation': 'सुस्वागतम', 'description': 'Both hands open gesturing inward', 'category': 'Greetings', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Good Morning', 'english_translation': 'Good Morning', 'hindi_translation': 'सुप्रभात', 'marathi_translation': 'शुभ सकाळ', 'description': 'Open hand to sky then greeting gesture', 'category': 'Greetings', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Good Night', 'english_translation': 'Good Night', 'hindi_translation': 'शुभ रात्रि', 'marathi_translation': 'शुभ रात्री', 'description': 'Hand to face like sleeping then wave', 'category': 'Greetings', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},

            # Responses & Affirmations
            {'name': 'Yes', 'english_translation': 'Yes / Affirmation', 'hindi_translation': 'हाँ', 'marathi_translation': 'होय', 'description': 'Nodding head or fist bouncing up and down', 'category': 'Response', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'No', 'english_translation': 'No / Denial', 'hindi_translation': 'नहीं', 'marathi_translation': 'नाही', 'description': 'Shaking head side to side or crossed hands', 'category': 'Response', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Maybe', 'english_translation': 'Maybe / Perhaps', 'hindi_translation': 'शायद', 'marathi_translation': 'कदाचित', 'description': 'Hand tilts side to side with uncertain expression', 'category': 'Response', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'OK', 'english_translation': 'OK / Agreed', 'hindi_translation': 'ठीक है', 'marathi_translation': 'ठीक आहे', 'description': 'Thumb and finger circle with other fingers up', 'category': 'Response', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Agree', 'english_translation': 'Agree / Understand', 'hindi_translation': 'सहमत', 'marathi_translation': 'मान्य आहे', 'description': 'Fist on chest then nod', 'category': 'Response', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},

            # Emotions
            {'name': 'Happy', 'english_translation': 'Happy / Joy', 'hindi_translation': 'खुश', 'marathi_translation': 'आनंदी', 'description': 'Hands move up along face with smile', 'category': 'Emotions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Sad', 'english_translation': 'Sad / Unhappy', 'hindi_translation': 'दुःख', 'marathi_translation': 'दुःखी', 'description': 'Fingers trace down face with sad expression', 'category': 'Emotions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Angry', 'english_translation': 'Angry / Upset', 'hindi_translation': 'क्रोधित', 'marathi_translation': 'रागवला', 'description': 'Claw hands moving down face forcefully', 'category': 'Emotions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Scared', 'english_translation': 'Scared / Afraid', 'hindi_translation': 'डरा हुआ', 'marathi_translation': 'घाबरलेला', 'description': 'Hands to chest with fearful expression', 'category': 'Emotions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Surprised', 'english_translation': 'Surprised / Shocked', 'hindi_translation': 'आश्चर्यचकित', 'marathi_translation': 'आश्चर्यचकित', 'description': 'Hands to mouth with wide eyes', 'category': 'Emotions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Love', 'english_translation': 'Love / Care', 'hindi_translation': 'प्यार', 'marathi_translation': 'प्रेम', 'description': 'Both hands crossed on chest', 'category': 'Emotions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Tired', 'english_translation': 'Tired / Exhausted', 'hindi_translation': 'थका हुआ', 'marathi_translation': 'थकलेला', 'description': 'Hands dropping from shoulders', 'category': 'Emotions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Confused', 'english_translation': 'Confused / Puzzled', 'hindi_translation': 'भ्रमित', 'marathi_translation': 'गोंधळलेला', 'description': 'Hand to head with tilted head', 'category': 'Emotions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},

            # Actions & Verbs
            {'name': 'Walk', 'english_translation': 'Walk / Move', 'hindi_translation': 'चलना', 'marathi_translation': 'चालणे', 'description': 'Two fingers walking on palm', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Run', 'english_translation': 'Run / Sprint', 'hindi_translation': 'दौड़ना', 'marathi_translation': 'धावणे', 'description': 'Arms bent at elbow moving back and forth quickly', 'category': 'Actions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Jump', 'english_translation': 'Jump / Leap', 'hindi_translation': 'कूदना', 'marathi_translation': 'उडी मारणे', 'description': 'Two fingers jumping upward', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Sit', 'english_translation': 'Sit / Settle', 'hindi_translation': 'बैठना', 'marathi_translation': 'बसणे', 'description': 'Two fingers sit on other two fingers', 'category': 'Actions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Stand', 'english_translation': 'Stand / Rise', 'hindi_translation': 'खड़ा होना', 'marathi_translation': 'उभे राहणे', 'description': 'Two fingers standing on palm', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Sleep', 'english_translation': 'Sleep / Rest', 'hindi_translation': 'सोना', 'marathi_translation': 'झोपणे', 'description': 'Hands on cheek moving to palm as if sleeping', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Wake Up', 'english_translation': 'Wake Up / Awaken', 'hindi_translation': 'जागना', 'marathi_translation': 'उठणे', 'description': 'Eyes open gesture with both hands opening from sides', 'category': 'Actions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Dance', 'english_translation': 'Dance / Move', 'hindi_translation': 'नृत्य', 'marathi_translation': 'नाचणे', 'description': 'Both hands swaying side to side rhythmically', 'category': 'Actions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Eat', 'english_translation': 'Eat / Consume', 'hindi_translation': 'खाना', 'marathi_translation': 'खाणे', 'description': 'Fingers to mouth repeatedly', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Drink', 'english_translation': 'Drink / Consume', 'hindi_translation': 'पीना', 'marathi_translation': 'पिणे', 'description': 'Hand in C shape to mouth as drinking', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Work', 'english_translation': 'Work / Labour', 'hindi_translation': 'काम', 'marathi_translation': 'काम करणे', 'description': 'Both fists tapping together alternately', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Play', 'english_translation': 'Play / Fun', 'hindi_translation': 'खेलना', 'marathi_translation': 'खेळणे', 'description': 'Both pinky fingers wiggling', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Read', 'english_translation': 'Read / Study', 'hindi_translation': 'पढ़ना', 'marathi_translation': 'वाचणे', 'description': 'Open hand moving downward on palm', 'category': 'Actions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Write', 'english_translation': 'Write / Pen', 'hindi_translation': 'लिखना', 'marathi_translation': 'लिहीणे', 'description': 'Finger gesture of writing on palm', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Listen', 'english_translation': 'Listen / Hear', 'hindi_translation': 'सुनना', 'marathi_translation': 'ऐकणे', 'description': 'Hand cupped behind ear', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Look', 'english_translation': 'Look / See', 'hindi_translation': 'देखना', 'marathi_translation': 'पाहणे', 'description': 'Index and middle finger to eyes', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Help', 'english_translation': 'Help / Assist', 'hindi_translation': 'मदद', 'marathi_translation': 'मदत', 'description': 'Hand under fist lifting up', 'category': 'Actions', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Give', 'english_translation': 'Give / Offer', 'hindi_translation': 'देना', 'marathi_translation': 'देणे', 'description': 'Open hand moving forward', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Take', 'english_translation': 'Take / Accept', 'hindi_translation': 'लेना', 'marathi_translation': 'घेणे', 'description': 'Hand closing into fist as grasping', 'category': 'Actions', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},

            # Objects & Things
            {'name': 'Water', 'english_translation': 'Water / Drink', 'hindi_translation': 'पानी', 'marathi_translation': 'पाणी', 'description': 'W hand gesture to lips', 'category': 'Objects', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Food', 'english_translation': 'Food / Meal', 'hindi_translation': 'खाना', 'marathi_translation': 'जेवण', 'description': 'Open hand to mouth as eating', 'category': 'Objects', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'House', 'english_translation': 'House / Home', 'hindi_translation': 'घर', 'marathi_translation': 'घर', 'description': 'Hands form roof shape then lower', 'category': 'Objects', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Car', 'english_translation': 'Car / Vehicle', 'hindi_translation': 'कार', 'marathi_translation': 'गाडी', 'description': 'Hands stacked and moving forward', 'category': 'Objects', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Phone', 'english_translation': 'Phone / Telephone', 'hindi_translation': 'फोन', 'marathi_translation': 'फोन', 'description': 'Hand in L shape to ear', 'category': 'Objects', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Book', 'english_translation': 'Book / Text', 'hindi_translation': 'किताब', 'marathi_translation': 'पुस्तक', 'description': 'Open hands like opening a book', 'category': 'Objects', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'School', 'english_translation': 'School / Academy', 'hindi_translation': 'स्कूल', 'marathi_translation': 'शाळा', 'description': 'Hands clapping together', 'category': 'Objects', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Money', 'english_translation': 'Money / Currency', 'hindi_translation': 'पैसा', 'marathi_translation': 'पैसे', 'description': 'Rubbing fingers together', 'category': 'Objects', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Clock', 'english_translation': 'Clock / Time', 'hindi_translation': 'घड़ी', 'marathi_translation': 'घड्याळ', 'description': 'Circular motion with index finger', 'category': 'Objects', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Doctor', 'english_translation': 'Doctor / Physician', 'hindi_translation': 'डॉक्टर', 'marathi_translation': 'डॉक्टर', 'description': 'Hand to arm checking pulse', 'category': 'Objects', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},

            # Adjectives & Descriptions
            {'name': 'Good', 'english_translation': 'Good / Great', 'hindi_translation': 'अच्छा', 'marathi_translation': 'छाण / चांगले', 'description': 'Thumb up or hand on chin moving away', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Bad', 'english_translation': 'Bad / Evil', 'hindi_translation': 'बुरा', 'marathi_translation': 'वाईट', 'description': 'Hand to lips and turned down', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Beautiful', 'english_translation': 'Beautiful / Pretty', 'hindi_translation': 'सुंदर', 'marathi_translation': 'सुंदर', 'description': 'Hand traces face then opens', 'category': 'Adjectives', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Ugly', 'english_translation': 'Ugly / Unattractive', 'hindi_translation': 'बदसूरत', 'marathi_translation': 'कुरूप', 'description': 'Hand to face with disgusted expression', 'category': 'Adjectives', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Big', 'english_translation': 'Big / Large', 'hindi_translation': 'बड़ा', 'marathi_translation': 'मोठे', 'description': 'Both hands spread wide apart', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Small', 'english_translation': 'Small / Tiny', 'hindi_translation': 'छोटा', 'marathi_translation': 'लहान', 'description': 'Hands close together indicating small', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Hot', 'english_translation': 'Hot / Warm', 'hindi_translation': 'गर्म', 'marathi_translation': 'गरम', 'description': 'Hand away from mouth as hot', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Cold', 'english_translation': 'Cold / Freezing', 'hindi_translation': 'ठंडा', 'marathi_translation': 'थंड', 'description': 'Shivering gesture with hands', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Strong', 'english_translation': 'Strong / Powerful', 'hindi_translation': 'मजबूत', 'marathi_translation': 'मजबूत', 'description': 'Flexing biceps or fists clenched', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Weak', 'english_translation': 'Weak / Feeble', 'hindi_translation': 'कमजोर', 'marathi_translation': 'कमकुवत', 'description': 'Hands dropping down limp', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Fast', 'english_translation': 'Fast / Quick', 'hindi_translation': 'तेज', 'marathi_translation': 'जलद', 'description': 'Hand moving quickly forward', 'category': 'Adjectives', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Slow', 'english_translation': 'Slow / Sluggish', 'hindi_translation': 'धीमा', 'marathi_translation': 'हळू', 'description': 'Hand moving slowly forward', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Clean', 'english_translation': 'Clean / Neat', 'hindi_translation': 'साफ', 'marathi_translation': 'स्वच्छ', 'description': 'Wiping motion across palm', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Dirty', 'english_translation': 'Dirty / Messy', 'hindi_translation': 'गंदा', 'marathi_translation': 'घाणेरडे', 'description': 'Hand wiggling with disgusted look', 'category': 'Adjectives', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},

            # Family & Relationships
            {'name': 'Mother', 'english_translation': 'Mother / Mom', 'hindi_translation': 'माता', 'marathi_translation': 'आई', 'description': 'Thumb on chin, hand opens', 'category': 'Family', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Father', 'english_translation': 'Father / Dad', 'hindi_translation': 'पिता', 'marathi_translation': 'बाबा / वडील', 'description': 'Thumb on forehead, hand opens', 'category': 'Family', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Sister', 'english_translation': 'Sister', 'hindi_translation': 'बहन', 'marathi_translation': 'बहीण', 'description': 'Pinky finger on cheek then hand opens', 'category': 'Family', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Brother', 'english_translation': 'Brother', 'hindi_translation': 'भाई', 'marathi_translation': 'भाऊ', 'description': 'Index finger on temple then opens', 'category': 'Family', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Baby', 'english_translation': 'Baby / Infant', 'hindi_translation': 'बच्चा', 'marathi_translation': 'बाळ', 'description': 'Rocking motion as holding baby', 'category': 'Family', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Grandfather', 'english_translation': 'Grandfather', 'hindi_translation': 'दादा', 'marathi_translation': 'आजोबा', 'description': 'Father sign then beard gesture', 'category': 'Family', 'difficulty_level': 'hard', 'dataset_source': 'ISL'},
            {'name': 'Grandmother', 'english_translation': 'Grandmother', 'hindi_translation': 'दादी', 'marathi_translation': 'आजी', 'description': 'Mother sign then beard gesture', 'category': 'Family', 'difficulty_level': 'hard', 'dataset_source': 'ISL'},
            {'name': 'Husband', 'english_translation': 'Husband / Spouse', 'hindi_translation': 'पति', 'marathi_translation': 'पती', 'description': 'Male sign then marriage gesture', 'category': 'Family', 'difficulty_level': 'hard', 'dataset_source': 'ISL'},
            {'name': 'Wife', 'english_translation': 'Wife / Spouse', 'hindi_translation': 'पत्नी', 'marathi_translation': 'पत्नी', 'description': 'Female sign then marriage gesture', 'category': 'Family', 'difficulty_level': 'hard', 'dataset_source': 'ISL'},
            {'name': 'Friend', 'english_translation': 'Friend / Companion', 'hindi_translation': 'मित्र', 'marathi_translation': 'मित्र', 'description': 'Two fingers linking together', 'category': 'Relationships', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},

            # Requests & Social
            {'name': 'Please', 'english_translation': 'Please / Request', 'hindi_translation': 'कृपया', 'marathi_translation': 'कृपया', 'description': 'Hand on chest in circular motion', 'category': 'Requests', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Thank You', 'english_translation': 'Thank You / Thanks', 'hindi_translation': 'धन्यवाद', 'marathi_translation': 'धन्यवाद', 'description': 'Hand touching chest and moving forward', 'category': 'Requests', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Sorry', 'english_translation': 'Sorry / Apology', 'hindi_translation': 'माफी', 'marathi_translation': 'माफ करा', 'description': 'Hand on chest with sorry expression', 'category': 'Requests', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Excuse Me', 'english_translation': 'Excuse Me', 'hindi_translation': 'माफ कीजिए', 'marathi_translation': 'क्षमा करा', 'description': 'Hand gesture seeking attention', 'category': 'Requests', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},

            # Education & Cognition
            {'name': 'Learn', 'english_translation': 'Learn / Study', 'hindi_translation': 'सीखना', 'marathi_translation': 'शिकणे', 'description': 'Hand to head then to open palm', 'category': 'Education', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Understand', 'english_translation': 'Understand / Comprehend', 'hindi_translation': 'समझना', 'marathi_translation': 'समजणे', 'description': 'Pinching hand to head', 'category': 'Education', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Forget', 'english_translation': 'Forget / Neglect', 'hindi_translation': 'भूलना', 'marathi_translation': 'विसरणे', 'description': 'Hand wiping across forehead', 'category': 'Education', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Remember', 'english_translation': 'Remember / Recall', 'hindi_translation': 'याद रखना', 'marathi_translation': 'आठवणे', 'description': 'Finger to temple indicating thinking', 'category': 'Education', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Think', 'english_translation': 'Think / Ponder', 'hindi_translation': 'सोचना', 'marathi_translation': 'विचार करणे', 'description': 'Circular motion at temple', 'category': 'Education', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},

            # Time & Numbers
            {'name': 'Today', 'english_translation': 'Today / Now', 'hindi_translation': 'आज', 'marathi_translation': 'आज', 'description': 'Both hands down pointing to present', 'category': 'Time', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Tomorrow', 'english_translation': 'Tomorrow', 'hindi_translation': 'कल', 'marathi_translation': 'उद्या', 'description': 'Thumb pointing forward indicating future', 'category': 'Time', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Yesterday', 'english_translation': 'Yesterday', 'hindi_translation': 'कल', 'marathi_translation': 'काल', 'description': 'Thumb pointing backward indicating past', 'category': 'Time', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Morning', 'english_translation': 'Morning / Dawn', 'hindi_translation': 'सुबह', 'marathi_translation': 'सकाळ', 'description': 'Arm rising indicating sun coming up', 'category': 'Time', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Evening', 'english_translation': 'Evening / Dusk', 'hindi_translation': 'शाम', 'marathi_translation': 'संध्याकाळ', 'description': 'Arm lowering indicating sun going down', 'category': 'Time', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Night', 'english_translation': 'Night / Dark', 'hindi_translation': 'रात', 'marathi_translation': 'रात्र', 'description': 'Both hands moving over head in arc', 'category': 'Time', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'One', 'english_translation': 'One / Single', 'hindi_translation': 'एक', 'marathi_translation': 'एक', 'description': 'Index finger up', 'category': 'Numbers', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Two', 'english_translation': 'Two / Couple', 'hindi_translation': 'दो', 'marathi_translation': 'दोन', 'description': 'Index and middle finger up', 'category': 'Numbers', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Three', 'english_translation': 'Three', 'hindi_translation': 'तीन', 'marathi_translation': 'तीन', 'description': 'Three fingers up', 'category': 'Numbers', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Five', 'english_translation': 'Five / Hand', 'hindi_translation': 'पाँच', 'marathi_translation': 'पाच', 'description': 'All five fingers spread', 'category': 'Numbers', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Ten', 'english_translation': 'Ten / Both Hands', 'hindi_translation': 'दस', 'marathi_translation': 'दहा', 'description': 'Both hands with all fingers spread', 'category': 'Numbers', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},

            # Health & Body
            {'name': 'Pain', 'english_translation': 'Pain / Hurt', 'hindi_translation': 'दर्द', 'marathi_translation': 'दुखणे', 'description': 'Fingers pointing inward at body area', 'category': 'Health', 'difficulty_level': 'easy', 'dataset_source': 'ISL'},
            {'name': 'Sick', 'english_translation': 'Sick / Ill', 'hindi_translation': 'बीमार', 'marathi_translation': 'आजारी', 'description': 'Hand to forehead and stomach', 'category': 'Health', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Health', 'english_translation': 'Health / Wellness', 'hindi_translation': 'स्वास्थ्य', 'marathi_translation': 'आरोग्य', 'description': 'Both hands on chest indicating strong', 'category': 'Health', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
            {'name': 'Hospital', 'english_translation': 'Hospital / Medical', 'hindi_translation': 'अस्पताल', 'marathi_translation': 'रुग्णालय', 'description': 'Cross gesture with hands on arm', 'category': 'Health', 'difficulty_level': 'medium', 'dataset_source': 'ISL'},
        ]

        return dataset

    def generate_hand_landmarks(self, sign_name):
        """Generate clean, non-overlapping 2D hand skeleton points (21 landmarks) for visualization & learning"""
        n = sign_name.upper().replace('_', ' ').strip()
        wrist = [0.50, 0.86]

        # 1. THUMBS UP (Good, Agree, Strong, Health, Tomorrow, Yesterday, Help)
        if n in ['GOOD', 'AGREE', 'STRONG', 'HEALTH', 'TOMORROW', 'YESTERDAY', 'HELP']:
            thumb = [[0.42, 0.76], [0.36, 0.62], [0.32, 0.44], [0.32, 0.26]]
            index = [[0.44, 0.60], [0.50, 0.58], [0.55, 0.62], [0.50, 0.66]]
            middle = [[0.48, 0.63], [0.53, 0.62], [0.57, 0.65], [0.52, 0.69]]
            ring = [[0.52, 0.68], [0.56, 0.67], [0.59, 0.70], [0.54, 0.74]]
            pinky = [[0.56, 0.73], [0.59, 0.72], [0.61, 0.75], [0.57, 0.79]]

        # 2. THUMBS DOWN (Bad, Weak, Ugly)
        elif n in ['BAD', 'WEAK', 'UGLY']:
            thumb = [[0.42, 0.76], [0.36, 0.84], [0.32, 0.92], [0.32, 0.99]]
            index = [[0.44, 0.60], [0.50, 0.58], [0.55, 0.62], [0.50, 0.66]]
            middle = [[0.48, 0.63], [0.53, 0.62], [0.57, 0.65], [0.52, 0.69]]
            ring = [[0.52, 0.68], [0.56, 0.67], [0.59, 0.70], [0.54, 0.74]]
            pinky = [[0.56, 0.73], [0.59, 0.72], [0.61, 0.75], [0.57, 0.79]]

        # 3. PEACE / V-SHAPE (Peace, Two)
        elif n in ['PEACE', 'TWO']:
            thumb = [[0.44, 0.74], [0.48, 0.68], [0.52, 0.66], [0.55, 0.66]]
            index = [[0.44, 0.58], [0.38, 0.44], [0.32, 0.30], [0.26, 0.16]]
            middle = [[0.50, 0.56], [0.56, 0.42], [0.62, 0.28], [0.68, 0.16]]
            ring = [[0.55, 0.62], [0.57, 0.66], [0.59, 0.70], [0.56, 0.72]]
            pinky = [[0.60, 0.66], [0.62, 0.70], [0.64, 0.74], [0.61, 0.76]]

        # 4. INVERTED WALKING LEGS (Walk, Run, Jump, Dance)
        elif n in ['WALK', 'RUN', 'JUMP', 'DANCE']:
            thumb = [[0.42, 0.66], [0.45, 0.60], [0.48, 0.58], [0.52, 0.58]]
            index = [[0.45, 0.64], [0.42, 0.74], [0.40, 0.84], [0.38, 0.95]]
            middle = [[0.52, 0.64], [0.55, 0.74], [0.58, 0.84], [0.60, 0.95]]
            ring = [[0.55, 0.60], [0.56, 0.54], [0.54, 0.50], [0.50, 0.52]]
            pinky = [[0.59, 0.62], [0.60, 0.56], [0.58, 0.52], [0.54, 0.54]]

        # 5. STANDING LEGS ON PALM (Stand)
        elif n in ['STAND']:
            thumb = [[0.40, 0.64], [0.42, 0.58], [0.46, 0.55], [0.50, 0.55]]
            index = [[0.46, 0.60], [0.46, 0.70], [0.46, 0.80], [0.46, 0.92]]
            middle = [[0.52, 0.60], [0.52, 0.70], [0.52, 0.80], [0.52, 0.92]]
            ring = [[0.56, 0.58], [0.56, 0.52], [0.53, 0.48], [0.50, 0.50]]
            pinky = [[0.60, 0.60], [0.60, 0.54], [0.57, 0.50], [0.53, 0.52]]

        # 6. SITTING BENT KNEES (Sit)
        elif n in ['SIT']:
            thumb = [[0.42, 0.72], [0.46, 0.68], [0.50, 0.65], [0.54, 0.65]]
            index = [[0.45, 0.60], [0.45, 0.50], [0.52, 0.50], [0.58, 0.52]]
            middle = [[0.50, 0.60], [0.50, 0.48], [0.57, 0.48], [0.63, 0.50]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.56, 0.72], [0.54, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.61, 0.74], [0.59, 0.76]]

        # 7. LOOK / VISION FORWARD (Look)
        elif n in ['LOOK']:
            thumb = [[0.42, 0.74], [0.46, 0.70], [0.50, 0.68], [0.54, 0.68]]
            index = [[0.46, 0.58], [0.56, 0.55], [0.68, 0.53], [0.80, 0.52]]
            middle = [[0.48, 0.64], [0.58, 0.63], [0.70, 0.62], [0.82, 0.62]]
            ring = [[0.54, 0.68], [0.56, 0.72], [0.57, 0.75], [0.54, 0.77]]
            pinky = [[0.59, 0.71], [0.61, 0.74], [0.62, 0.77], [0.59, 0.79]]

        # 8. POINTING INDEX UP (One, Today, Pain, Fast)
        elif n in ['ONE', 'TODAY', 'PAIN', 'FAST']:
            thumb = [[0.42, 0.76], [0.46, 0.70], [0.50, 0.68], [0.54, 0.68]]
            index = [[0.46, 0.58], [0.46, 0.44], [0.46, 0.30], [0.46, 0.16]]
            middle = [[0.50, 0.62], [0.53, 0.65], [0.55, 0.69], [0.52, 0.71]]
            ring = [[0.55, 0.65], [0.57, 0.68], [0.59, 0.72], [0.56, 0.74]]
            pinky = [[0.60, 0.68], [0.62, 0.71], [0.64, 0.75], [0.61, 0.77]]

        # 9. THINKING / TEMPLE TOUCH (Think, Remember, Learn, Forget)
        elif n in ['THINK', 'REMEMBER', 'LEARN', 'FORGET']:
            thumb = [[0.40, 0.74], [0.34, 0.68], [0.30, 0.62], [0.28, 0.56]]
            index = [[0.46, 0.58], [0.42, 0.44], [0.38, 0.30], [0.34, 0.16]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.54, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 10. CLOCK / WRIST TAP (Clock)
        elif n in ['CLOCK']:
            thumb = [[0.42, 0.74], [0.44, 0.68], [0.48, 0.65], [0.52, 0.65]]
            index = [[0.46, 0.60], [0.52, 0.68], [0.58, 0.76], [0.64, 0.85]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.53, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 11. NO SNAP (No)
        elif n in ['NO']:
            thumb = [[0.40, 0.74], [0.46, 0.70], [0.54, 0.66], [0.60, 0.60]]
            index = [[0.45, 0.60], [0.50, 0.56], [0.56, 0.56], [0.62, 0.58]]
            middle = [[0.48, 0.62], [0.52, 0.59], [0.57, 0.60], [0.62, 0.62]]
            ring = [[0.55, 0.65], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 12. THREE FINGERS (Three)
        elif n in ['THREE']:
            thumb = [[0.40, 0.76], [0.34, 0.68], [0.28, 0.60], [0.22, 0.52]]
            index = [[0.44, 0.58], [0.42, 0.44], [0.40, 0.30], [0.38, 0.16]]
            middle = [[0.50, 0.56], [0.52, 0.42], [0.54, 0.28], [0.56, 0.16]]
            ring = [[0.55, 0.62], [0.57, 0.66], [0.59, 0.70], [0.56, 0.72]]
            pinky = [[0.60, 0.66], [0.62, 0.70], [0.64, 0.74], [0.61, 0.76]]

        # 13. OK SIGN (OK, Understand)
        elif n in ['OK', 'UNDERSTAND']:
            thumb = [[0.38, 0.74], [0.35, 0.64], [0.36, 0.54], [0.40, 0.48]]
            index = [[0.44, 0.58], [0.45, 0.50], [0.43, 0.46], [0.40, 0.48]]
            middle = [[0.50, 0.56], [0.50, 0.40], [0.50, 0.28], [0.50, 0.16]]
            ring = [[0.56, 0.58], [0.58, 0.44], [0.60, 0.32], [0.62, 0.20]]
            pinky = [[0.62, 0.62], [0.66, 0.50], [0.69, 0.40], [0.72, 0.30]]

        # 14. I LOVE YOU / HEART (Love, Beautiful)
        elif n in ['LOVE', 'BEAUTIFUL']:
            thumb = [[0.40, 0.76], [0.32, 0.70], [0.25, 0.64], [0.18, 0.58]]
            index = [[0.44, 0.58], [0.42, 0.44], [0.40, 0.30], [0.38, 0.16]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.54, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.62, 0.62], [0.66, 0.50], [0.70, 0.38], [0.74, 0.26]]

        # 15. PHONE / Y-SHAPE (Phone, Play)
        elif n in ['PHONE', 'PLAY']:
            thumb = [[0.40, 0.76], [0.30, 0.72], [0.20, 0.66], [0.12, 0.58]]
            index = [[0.44, 0.62], [0.46, 0.66], [0.47, 0.70], [0.45, 0.72]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.53, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.64], [0.68, 0.54], [0.76, 0.44], [0.84, 0.34]]

        # 16. EATING PINCH CONE (Eat, Food)
        elif n in ['EAT', 'FOOD']:
            thumb = [[0.42, 0.76], [0.45, 0.65], [0.48, 0.54], [0.50, 0.44]]
            index = [[0.45, 0.58], [0.47, 0.52], [0.49, 0.47], [0.50, 0.44]]
            middle = [[0.50, 0.56], [0.50, 0.50], [0.50, 0.46], [0.50, 0.44]]
            ring = [[0.54, 0.58], [0.53, 0.52], [0.51, 0.47], [0.50, 0.44]]
            pinky = [[0.58, 0.62], [0.56, 0.55], [0.53, 0.48], [0.50, 0.44]]

        # 17. DRINK / CUP C-SHAPE (Drink, Baby, Listen)
        elif n in ['DRINK', 'BABY', 'LISTEN']:
            thumb = [[0.40, 0.74], [0.32, 0.68], [0.30, 0.56], [0.34, 0.46]]
            index = [[0.46, 0.58], [0.52, 0.50], [0.58, 0.46], [0.66, 0.50]]
            middle = [[0.48, 0.60], [0.54, 0.53], [0.60, 0.50], [0.67, 0.54]]
            ring = [[0.51, 0.63], [0.56, 0.57], [0.62, 0.55], [0.67, 0.60]]
            pinky = [[0.54, 0.66], [0.58, 0.62], [0.63, 0.61], [0.67, 0.66]]

        # 18. WATER / W-SHAPE (Water)
        elif n in ['WATER']:
            thumb = [[0.42, 0.76], [0.48, 0.72], [0.54, 0.70], [0.58, 0.70]]
            index = [[0.44, 0.58], [0.38, 0.44], [0.32, 0.30], [0.26, 0.16]]
            middle = [[0.50, 0.56], [0.50, 0.40], [0.50, 0.25], [0.50, 0.13]]
            ring = [[0.56, 0.58], [0.62, 0.44], [0.68, 0.30], [0.74, 0.16]]
            pinky = [[0.60, 0.64], [0.61, 0.68], [0.60, 0.72], [0.58, 0.74]]

        # 19. HOUSE / ROOF PEAK (House, Home, School, Hospital)
        elif n in ['HOUSE', 'HOME', 'SCHOOL', 'HOSPITAL']:
            thumb = [[0.44, 0.76], [0.40, 0.68], [0.38, 0.60], [0.38, 0.54]]
            index = [[0.44, 0.58], [0.42, 0.46], [0.44, 0.34], [0.48, 0.22]]
            middle = [[0.48, 0.56], [0.48, 0.42], [0.49, 0.28], [0.50, 0.16]]
            ring = [[0.53, 0.58], [0.52, 0.46], [0.51, 0.34], [0.50, 0.22]]
            pinky = [[0.58, 0.62], [0.57, 0.52], [0.55, 0.42], [0.52, 0.32]]

        # 20. BOOK / OPEN PAGES (Book)
        elif n in ['BOOK']:
            thumb = [[0.40, 0.76], [0.30, 0.70], [0.22, 0.62], [0.15, 0.54]]
            index = [[0.44, 0.60], [0.38, 0.48], [0.32, 0.36], [0.26, 0.24]]
            middle = [[0.48, 0.58], [0.44, 0.45], [0.40, 0.32], [0.36, 0.20]]
            ring = [[0.52, 0.60], [0.50, 0.48], [0.48, 0.36], [0.46, 0.24]]
            pinky = [[0.56, 0.63], [0.55, 0.52], [0.54, 0.42], [0.53, 0.32]]

        # 21. CAR / STEERING WHEEL (Car)
        elif n in ['CAR']:
            thumb = [[0.42, 0.74], [0.42, 0.64], [0.42, 0.52], [0.42, 0.40]]
            index = [[0.46, 0.58], [0.52, 0.56], [0.58, 0.58], [0.54, 0.62]]
            middle = [[0.49, 0.62], [0.55, 0.60], [0.60, 0.62], [0.56, 0.66]]
            ring = [[0.52, 0.66], [0.57, 0.65], [0.62, 0.67], [0.58, 0.71]]
            pinky = [[0.55, 0.70], [0.59, 0.69], [0.63, 0.72], [0.59, 0.76]]

        # 22. SISTER / L-SHAPE EARRING (Sister)
        elif n in ['SISTER']:
            thumb = [[0.40, 0.76], [0.32, 0.74], [0.24, 0.72], [0.15, 0.70]]
            index = [[0.46, 0.58], [0.46, 0.44], [0.46, 0.30], [0.46, 0.16]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.53, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 23. BROTHER / HOOKED INDEX (Brother)
        elif n in ['BROTHER']:
            thumb = [[0.40, 0.76], [0.44, 0.70], [0.48, 0.66], [0.52, 0.66]]
            index = [[0.46, 0.58], [0.46, 0.46], [0.52, 0.40], [0.56, 0.46]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.53, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 24. FRIEND / CHAIN HOOKS (Friend)
        elif n in ['FRIEND']:
            thumb = [[0.38, 0.74], [0.35, 0.64], [0.38, 0.54], [0.44, 0.48]]
            index = [[0.45, 0.58], [0.45, 0.44], [0.52, 0.38], [0.58, 0.44]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.54, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 25. DOCTOR / WRIST PULSE (Doctor)
        elif n in ['DOCTOR']:
            thumb = [[0.42, 0.68], [0.44, 0.62], [0.46, 0.58], [0.48, 0.58]]
            index = [[0.47, 0.58], [0.47, 0.68], [0.47, 0.78], [0.47, 0.90]]
            middle = [[0.52, 0.58], [0.52, 0.68], [0.52, 0.78], [0.52, 0.90]]
            ring = [[0.56, 0.62], [0.56, 0.56], [0.54, 0.52], [0.50, 0.54]]
            pinky = [[0.60, 0.64], [0.60, 0.58], [0.58, 0.54], [0.54, 0.56]]

        # 26. MOTHER / CHIN TOUCH (Mother, Grandmother)
        elif n in ['MOTHER', 'GRANDMOTHER']:
            thumb = [[0.42, 0.76], [0.38, 0.66], [0.36, 0.54], [0.36, 0.42]]
            index = [[0.46, 0.58], [0.48, 0.46], [0.50, 0.36], [0.52, 0.26]]
            middle = [[0.50, 0.58], [0.52, 0.46], [0.54, 0.36], [0.56, 0.26]]
            ring = [[0.54, 0.60], [0.56, 0.48], [0.58, 0.38], [0.60, 0.28]]
            pinky = [[0.58, 0.62], [0.60, 0.52], [0.62, 0.42], [0.64, 0.32]]

        # 27. FATHER / FOREHEAD SALUTE (Father, Grandfather)
        elif n in ['FATHER', 'GRANDFATHER']:
            thumb = [[0.42, 0.76], [0.38, 0.64], [0.36, 0.50], [0.35, 0.35]]
            index = [[0.45, 0.58], [0.44, 0.44], [0.43, 0.30], [0.42, 0.16]]
            middle = [[0.49, 0.56], [0.49, 0.42], [0.49, 0.28], [0.49, 0.14]]
            ring = [[0.54, 0.58], [0.55, 0.44], [0.56, 0.30], [0.57, 0.16]]
            pinky = [[0.59, 0.62], [0.61, 0.50], [0.63, 0.38], [0.65, 0.26]]

        # 28. MONEY / FRICTION PINCH (Money, Write)
        elif n in ['MONEY', 'WRITE']:
            thumb = [[0.42, 0.76], [0.44, 0.66], [0.47, 0.58], [0.50, 0.52]]
            index = [[0.46, 0.58], [0.48, 0.54], [0.50, 0.52], [0.52, 0.52]]
            middle = [[0.50, 0.58], [0.51, 0.55], [0.52, 0.53], [0.52, 0.52]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 29. SMALL / TINY GAP (Small)
        elif n in ['SMALL']:
            thumb = [[0.42, 0.76], [0.44, 0.66], [0.46, 0.56], [0.48, 0.48]]
            index = [[0.48, 0.58], [0.50, 0.52], [0.51, 0.48], [0.52, 0.48]]
            middle = [[0.50, 0.62], [0.52, 0.66], [0.53, 0.70], [0.51, 0.72]]
            ring = [[0.55, 0.64], [0.56, 0.68], [0.57, 0.72], [0.55, 0.74]]
            pinky = [[0.60, 0.66], [0.61, 0.70], [0.62, 0.74], [0.60, 0.76]]

        # 30. BIG / WIDE SPREAD (Big)
        elif n in ['BIG']:
            thumb = [[0.38, 0.78], [0.28, 0.72], [0.18, 0.65], [0.08, 0.58]]
            index = [[0.42, 0.58], [0.36, 0.42], [0.28, 0.28], [0.20, 0.14]]
            middle = [[0.48, 0.56], [0.48, 0.38], [0.48, 0.24], [0.48, 0.10]]
            ring = [[0.55, 0.58], [0.61, 0.42], [0.68, 0.28], [0.76, 0.14]]
            pinky = [[0.62, 0.62], [0.70, 0.50], [0.78, 0.38], [0.88, 0.26]]

        # 31. SLEEP TILT (Sleep, Good Night, Night)
        elif n in ['SLEEP', 'GOOD NIGHT', 'NIGHT']:
            thumb = [[0.44, 0.78], [0.38, 0.72], [0.34, 0.64], [0.30, 0.58]]
            index = [[0.46, 0.60], [0.42, 0.48], [0.38, 0.36], [0.34, 0.24]]
            middle = [[0.50, 0.58], [0.46, 0.46], [0.42, 0.34], [0.38, 0.22]]
            ring = [[0.54, 0.60], [0.50, 0.48], [0.46, 0.36], [0.42, 0.24]]
            pinky = [[0.58, 0.64], [0.54, 0.52], [0.50, 0.40], [0.46, 0.28]]

        # 32. FLAT PALM ON CHEST (Please, Thank You, Excuse Me, Clean, Slow, Give, Read)
        elif n in ['PLEASE', 'THANK YOU', 'EXCUSE ME', 'CLEAN', 'SLOW', 'GIVE', 'READ']:
            thumb = [[0.42, 0.78], [0.38, 0.70], [0.36, 0.62], [0.36, 0.54]]
            index = [[0.45, 0.58], [0.45, 0.44], [0.45, 0.32], [0.45, 0.20]]
            middle = [[0.50, 0.56], [0.50, 0.42], [0.50, 0.30], [0.50, 0.18]]
            ring = [[0.55, 0.58], [0.55, 0.44], [0.55, 0.32], [0.55, 0.20]]
            pinky = [[0.60, 0.62], [0.60, 0.50], [0.60, 0.38], [0.60, 0.26]]

        # 33. FIST (Fist, Work, Sick, Sorry, Angry, Cold, Take, Husband, Wife, Dirty, Yes)
        elif n in ['FIST', 'WORK', 'SICK', 'SORRY', 'ANGRY', 'COLD', 'TAKE', 'HUSBAND', 'WIFE', 'DIRTY', 'YES']:
            thumb = [[0.38, 0.76], [0.42, 0.68], [0.48, 0.64], [0.54, 0.65]]
            index = [[0.43, 0.60], [0.45, 0.66], [0.46, 0.72], [0.43, 0.75]]
            middle = [[0.48, 0.59], [0.50, 0.65], [0.51, 0.71], [0.48, 0.74]]
            ring = [[0.53, 0.60], [0.55, 0.66], [0.56, 0.72], [0.53, 0.75]]
            pinky = [[0.58, 0.63], [0.60, 0.68], [0.61, 0.74], [0.58, 0.76]]

        # 34. NATURAL OPEN PALM GREETING (Hello, Goodbye, Welcome, Good Morning, Happy, Scared, Surprised, Five, Ten, Wake Up, Morning, Evening, Maybe, Hot, Tired, Confused)
        else:
            thumb = [[0.40, 0.78], [0.32, 0.72], [0.26, 0.66], [0.20, 0.60]]
            index = [[0.43, 0.58], [0.40, 0.44], [0.38, 0.32], [0.36, 0.20]]
            middle = [[0.48, 0.56], [0.48, 0.40], [0.48, 0.28], [0.48, 0.16]]
            ring = [[0.54, 0.58], [0.56, 0.44], [0.58, 0.32], [0.60, 0.20]]
            pinky = [[0.60, 0.62], [0.64, 0.50], [0.67, 0.40], [0.70, 0.30]]

        points = [wrist] + thumb + index + middle + ring + pinky
        return [{'x': round(float(p[0]), 3), 'y': round(float(p[1]), 3)} for p in points]

    def insert_signs_into_db(self):
        try:
            dataset = self.load_sign_language_dataset()

            for sign_data in dataset:
                existing = Sign.query.filter_by(name=sign_data['name']).first()

                if existing:
                    existing.keypoints_data = self.generate_hand_landmarks(sign_data['name'])
                    existing.english_translation = sign_data['english_translation']
                    existing.hindi_translation = sign_data.get('hindi_translation')
                    existing.marathi_translation = sign_data.get('marathi_translation')
                    existing.description = sign_data.get('description')
                    existing.category = sign_data.get('category')
                    existing.difficulty_level = sign_data.get('difficulty_level')
                else:
                    sign = Sign(
                        name=sign_data['name'],
                        english_translation=sign_data['english_translation'],
                        hindi_translation=sign_data.get('hindi_translation'),
                        marathi_translation=sign_data.get('marathi_translation'),
                        description=sign_data.get('description'),
                        category=sign_data.get('category'),
                        difficulty_level=sign_data.get('difficulty_level'),
                        dataset_source=sign_data.get('dataset_source'),
                        confidence_score=random.uniform(0.85, 0.99),
                        keypoints_data=self.generate_hand_landmarks(sign_data['name'])
                    )
                    db.session.add(sign)

            db.session.commit()
            return len(dataset), "Dataset loaded and updated successfully"

        except Exception as e:
            db.session.rollback()
            return 0, f"Error loading dataset: {str(e)}"

    def get_dataset_statistics(self):
        try:
            total_signs = Sign.query.count()
            categories = db.session.query(
                Sign.category,
                db.func.count(Sign.id).label('count')
            ).group_by(Sign.category).all()

            difficulty_distribution = db.session.query(
                Sign.difficulty_level,
                db.func.count(Sign.id).label('count')
            ).group_by(Sign.difficulty_level).all()

            return {
                'total_signs': total_signs,
                'categories': {cat: count for cat, count in categories},
                'difficulty_distribution': {diff: count for diff, count in difficulty_distribution}
            }

        except Exception as e:
            return {'error': str(e)}
