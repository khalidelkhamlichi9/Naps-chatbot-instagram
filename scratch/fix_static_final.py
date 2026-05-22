import os
import re

def fix_static_responses_properly():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Find the start of STATIC_RESPONSES
    start_match = re.search(r'STATIC_RESPONSES: dict\[str, dict\[str, str\]\] = \{', content)
    if not start_match:
        print("Error: Could not find STATIC_RESPONSES start")
        return

    start_index = start_match.start()
    brace_start = start_match.end() - 1
    
    # Find the matching closing brace
    brace_count = 0
    end_index = -1
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_index = i + 1
                break
    
    if end_index == -1:
        print("Error: Could not find matching brace")
        return

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

    updated_content = content[:start_index] + new_static + content[end_index:]

    with open(path, 'wb') as f:
        f.write(updated_content.encode('utf-8'))
    print("Successfully fixed STATIC_RESPONSES properly in pipeline.py")

if __name__ == "__main__":
    fix_static_responses_properly()
