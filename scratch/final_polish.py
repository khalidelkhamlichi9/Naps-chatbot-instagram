import os
import re

def final_polish_pipeline():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # 1. Update _strip_ai_watermark to be even more aggressive and robust
    new_strip_func = r'''def _strip_ai_watermark(text):
    """Aggressively remove all AI signatures, emojis, and formatting."""
    if not text: return ""
    import re as _r
    
    # Remove ALL emojis and special symbols
    text = _r.sub(r'[^\w\s\.,!\?:\-\(\)\'\"\u0600-\u06FF\u0100-\u017FÀ-ÿ]+', ' ', text)
    
    # Remove Markdown (bold, italic, headers)
    text = _r.sub(r'\*\*|\*|__|_', '', text)
    text = _r.sub(r'(?m)^#{1,6}\s+', '', text)
    
    # Remove list markers at start of lines
    text = _r.sub(r'(?m)^\s*[-*•]\s+', '', text)
    text = _r.sub(r'(?m)^\s*\d+[.)\-]\s+', '', text)
    
    # Remove common AI intros
    _intros = [r'(?i)^voici\s*:?\s*', r'(?i)^certainement\s*,?\s*', r'(?i)^bien s[^a-zA-Z]r\s*,?\s*']
    for _i in _intros: text = _r.sub(_i, '', text)
    
    # Collapse multiple spaces and newlines
    text = _r.sub(r' {2,}', ' ', text)
    text = _r.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()'''

    # Replace the existing _strip_ai_watermark
    pattern_strip = r'def _strip_ai_watermark\(text\):.*?return text\.strip\(\)'
    content = re.sub(pattern_strip, new_strip_func, content, flags=re.DOTALL)

    # 2. Ensure _strip_ai_watermark is called on ALL return paths
    # Fix static responses
    content = re.sub(r'return answer\s+# Static', 'return _strip_ai_watermark(answer)', content)
    # Fix cache hits
    content = re.sub(r'return cached\s+# Cache', 'return _strip_ai_watermark(cached)', content)
    
    # 3. Force Language instruction in the prompt building part
    lang_force = r'''    # Sales injection
    sales_keywords = ["tpe", "terminal", "pack", "carte", "prix", "taman", "chehal", "offre", "commander", "acheter", "devenir client"]
    sales_injection = ""
    if any(k in message.lower() for k in sales_keywords):
        sales_injection = _SALES_INJECTION.get(language, _SALES_INJECTION["fr"])

    # FORCE LANGUAGE RULE
    lang_name = {"fr": "français", "ar": "arabe", "darija": "darija marocain", "en": "anglais"}.get(language, language)
    force_lang = f"\n\nTU DOIS RÉPONDRE EXCLUSIVEMENT EN {lang_name.upper()} car l'utilisateur t'a parlé dans cette langue."
    
    full_system = f"{base_system}{sales_injection}{force_lang}"'''

    # Find the sales injection part and replace it
    pattern_sales = r'sales_keywords = \[.*?\n\s+full_system = f"\{base_system\}\{sales_injection\}"'
    content = re.sub(pattern_sales, lambda m: lang_force, content, flags=re.DOTALL)

    with open(path, 'wb') as f:
        f.write(content.encode('utf-8'))
    print("Successfully polished pipeline.py for language and watermark consistency.")

if __name__ == "__main__":
    final_polish_pipeline()
