import sys
import re
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

DARIJA_SIGNALS = [
    # Salutations / formules courantes (CRITIQUE — manquantes)
    "salam", "salamou", "salamoualikoum", "alikoum", "labas", "lhamdoulillah",
    "inchallah", "wllah", "yallah", "yalah", "marhba", "marhaba", "choukran", 
    "barakallah", "tbarkallah", "bslama", "beslama", "khoya", "khouya",
    # Mots interrogatifs / actions / communs
    "wach", "kifash", "kifach", "bghit", "bghiti", "kayn", "kayna", 
    "makaynsh", "nta", "nti", "fin", "dyal", "dyali", "chhal", "chehal",
    "wash", "ana", "hna", "ndir", "taman", "tamane", "thaman", "thman",
    "khsni", "3ndi", "3andi", "3ndek", "3andek", "khdma", "safi", "mzyan", 
    "mezyan", "ewa", "wakha", "bach", "mn", "men", "3ndkom", "3andkom",
    "bzzaf", "bzaf", "chno", "shnu", "chnou", "mnin", "fach", "lla", "la", "ah", "iyyeh",
    "yeh", "ach", "ash", "ghi", "walakin", "walakine", "ghadi", "ghy", "daba", "mera", "lmera", "lwla",
    "ila", "khdit", "khdito", "rani", "ranni", "smitek", "tcharafna", "kidayr", "kidayra",
    "fhamtek", "fhamt", "nch", "n9der", "n9dr", "m3ak", "3lik", "flous", "carte",
    "t9der", "t9dr", "y9der", "y9dr", "3la", "fe", "li", "liya", "lik", "charaf", "3tini", "t3tini",
]

def my_detect_language(text: str) -> str:
    text_lower = text.lower()
    clean_text = re.sub(r'[^\w\s]', '', text_lower)
    words = clean_text.split()
    
    darija_hits = 0
    for signal in DARIJA_SIGNALS:
        if len(signal) <= 2:
            if any(signal == word for word in words):
                darija_hits += 1
        else:
            if any(signal in word for word in words):
                darija_hits += 1
                
    if darija_hits >= 1:
        return "darija"
        
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar"
        
    try:
        lang = detect(text)
        if lang in ("fr", "ar", "en"): return lang
        if lang in ("ca", "es", "it", "pt", "ro"): return "fr"
        if lang in ("fa", "ur", "ps"): return "ar"
        return "fr"
    except LangDetectException:
        if "salam" in text_lower: return "darija"
        return "fr"
    except Exception:
        return "fr"

def determine_language(message: str, history: list[dict]) -> str:
    current_lang = my_detect_language(message)
    
    # If the user explicitly used Darija/Arabic/English in the current message, switch immediately
    if current_lang in ("darija", "ar", "en"):
        return current_lang
        
    # If current_lang is "fr", it could be a fallback.
    # Check if the current message is neutral (short or contains no letters)
    words = message.strip().split()
    letter_words = [w for w in words if any(c.isalpha() for c in w)]
    has_letters = len(letter_words) > 0
    is_neutral = not has_letters or len(letter_words) <= 3
    
    if is_neutral and history:
        # It's neutral, so we inherit the conversation language from history
        for msg in reversed(history):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                past_lang = my_detect_language(content)
                if past_lang in ("darija", "ar", "en"):
                    return past_lang
                
                # If we find a non-neutral French message f l'user, we know they spoke French
                past_words = content.strip().split()
                past_letter_words = [w for w in past_words if any(c.isalpha() for c in w)]
                if len(past_letter_words) > 3:
                    return "fr"
                    
    return "fr"

# Test 1: Flow where user speaks Darija, then enters details
history = [
    {"role": "user", "content": "bghit n3raf l'prix"},
    {"role": "assistant", "content": "Tcharafna. Naps 3ndha formule b 0 DH..."}
]

test_turns_1 = [
    "420 DH / mois",
    "Ah oui",
    "EL KHAMLICHI Khallid",
    "06787 79458"
]

print("--- Test 1 (Darija Flow) ---")
for t in test_turns_1:
    lang = determine_language(t, history)
    print(f"User: {t} -> Detected Lang: {lang}")
    history.append({"role": "user", "content": t})

# Test 2: Flow where user speaks French, then enters details
history_2 = [
    {"role": "user", "content": "Je voudrais connaitre les tarifs de Naps"},
    {"role": "assistant", "content": "Certainement. Nous avons 3 formules..."}
]

test_turns_2 = [
    "420 DH / mois",
    "Ah oui",
    "EL KHAMLICHI Khallid",
    "06787 79458"
]

print("\n--- Test 2 (French Flow) ---")
for t in test_turns_2:
    lang = determine_language(t, history_2)
    print(f"User: {t} -> Detected Lang: {lang}")
    history_2.append({"role": "user", "content": t})

# Test 3: Language switch flow
history_3 = [
    {"role": "user", "content": "bghit n3raf l'prix"},
    {"role": "assistant", "content": "Naps 3ndha formule..."}
]

print("\n--- Test 3 (Switch to French Flow) ---")
switch_msg = "Je préfère avoir les détails par écrit s'il vous plaît"
lang = determine_language(switch_msg, history_3)
print(f"User: {switch_msg} -> Detected Lang: {lang}")
