import re
import os

def clean_static_responses():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # New Clean Static Responses
    new_static = r'''STATIC_RESPONSES: dict[str, dict[str, str]] = {
    "greeting": {
        "fr":     "Bonjour, je suis Karim de NAPS. Comment puis-je vous aider à booster votre activité aujourd'hui ?",
        "ar":     "مرحباً، أنا كريم من NAPS. كيف يمكنني مساعدتك في تطوير تجارتك اليوم؟",
        "darija": "Salam, ana Karim mn NAPS. Kifach n9der n3awnk tkhdem mzyan f l-bi3 dyalk l-youm?",
        "en":     "Hello, I'm Karim from NAPS. How can I help you grow your business today?",
    },
    "farewell": {
        "fr":     "Merci de votre confiance. Je reste à votre disposition pour toute autre question.",
        "ar":     "شكراً لثقتكم. أنا رهن إشارتكم لأي سؤال آخر.",
        "darija": "Shokran 3la ti9a dyalk. Ana hna ila htajiti chi 7aja khora.",
        "en":     "Thank you for your trust. I'm here if you have any other questions.",
    },
}'''

    # Find the whole STATIC_RESPONSES block
    pattern = r'STATIC_RESPONSES: dict\[str, dict\[str, str\]\] = \{.*?\}'
    
    if not re.search(pattern, content, flags=re.DOTALL):
        print("Error: Could not find STATIC_RESPONSES block")
        return

    updated_content = re.sub(pattern, lambda m: new_static, content, flags=re.DOTALL)

    with open(path, 'wb') as f:
        f.write(updated_content.encode('utf-8'))
    print("Successfully cleaned STATIC_RESPONSES in pipeline.py")

if __name__ == "__main__":
    clean_static_responses()
