import re
import os

def patch_sales_injection():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Define the new sales injection dictionary
    new_sales_dict = r'''    _SALES_INJECTION = {
        "fr": (
            "\n\nIMPORTANT : Sois extrêmement persuasif. Ne donne pas seulement le prix, "
            "souligne le gain de temps et l'agilité de NAPS (installation en 48h). "
            "Termine par une question directe pour conclure."
        ),
        "ar": (
            "\n\nهام: كن مقنعاً جداً. لا تكتفِ بالثمن، بل أكد على ربح الوقت وسرعة NAPS (التركيب في 48 ساعة). "
            "اختم بسؤال مباشر لإتمام العملية."
        ),
        "darija": (
            "\n\nMHIM: Khssk tkon mo9ni3 bzzaf. Mat3tich ghir l-taman, rkezz 3la rbe7 l-wa9t w sro3a dyal NAPS (installation f 48h). "
            "Sali b so2al direct bach tsali l-bi3a."
        ),
        "en": (
            "\n\nIMPORTANT: Be highly persuasive. Don't just give the price, "
            "emphasize time savings and NAPS speed (48h setup). "
            "End with a direct closing question."
        ),
    }'''

    # Pattern to find the _SALES_INJECTION block
    pattern = r'    _SALES_INJECTION = \{.*?\}'
    
    if not re.search(pattern, content, flags=re.DOTALL):
        print("Error: Could not find _SALES_INJECTION in pipeline.py")
        return

    updated_content = re.sub(pattern, lambda m: new_sales_dict, content, flags=re.DOTALL)

    with open(path, 'wb') as f:
        f.write(updated_content.encode('utf-8'))
    print("Successfully updated _SALES_INJECTION in pipeline.py")

if __name__ == "__main__":
    patch_sales_injection()
