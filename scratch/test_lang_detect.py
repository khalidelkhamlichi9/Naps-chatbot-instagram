import sys
sys.path.append('.')
from core.language import detect_language

texts = [
    "Chara f liya",
    "t9der t3tini bref 3la les tpes li 3ndkom fe naps ?",
    "ok chno kaymyzkom ntoma 3la lokhrin"
]

for t in texts:
    print(f"Text: {t} -> Detected: {detect_language(t)}")
