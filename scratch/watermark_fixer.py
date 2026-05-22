import re
import os

def patch_pipeline():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Aggressive humanizer function
    new_func = r'''def _strip_ai_watermark(text):
    """Deep-clean AI artifacts and formatting for a human-only feel."""
    import re as _r
    
    # 1. Remove explicit AI self-identity phrases
    _ai_pats = [
        r'(?i)(as an? (ai|artificial intelligence|language model|llm)[,.]?\s*)',
        r'(?i)(en tant qu.{0,2}(ia|intelligence artificielle)[,.]?\s*)',
        r'(?i)(je suis (une? )?(ia|intelligence artificielle|assistant ia)[,.]?\s*)',
        r'(?i)(i(\'m| am) an? (ai|artificial intelligence|language model|chatbot)[,.]?\s*)',
        r'(?i)(ana (ai|bernamaj|chatbot)[,.]?\s*)',
        r'(?i)(bien s[^a-zA-Z]r)',
        r'(?i)(voici)',
        r'(?i)(certainement)',
    ]
    for _p in _ai_pats:
        text = _r.sub(_p, '', text)

    # 2. Remove ALL markdown headings (##)
    text = _r.sub(r'(?m)^#{1,6}\s+', '', text)
    
    # 3. Strip ALL Emojis (👉, 🚀, ✅, etc.)
    emoji_pattern = _r.compile(
        u"["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E6-\U0001F1FF"
        u"\U00002600-\U000026FF"
        u"\U00002700-\U000027BF"
        u"\U0000FE00-\U0000FE0F"
        u"\U0001F900-\U0001F9FF"
        u"\U0001F170-\U0001F251"
        u"]+", flags=_r.UNICODE)
    text = emoji_pattern.sub('', text)

    # 4. Remove ALL Markdown bold, italic, and underline symbols
    text = _r.sub(r'\*\*', '', text)
    text = _r.sub(r'\*', '', text)
    text = _r.sub(r'__', '', text)
    text = _r.sub(r'_', '', text)

    # 5. Remove list markers (- * 1. 2.) and keep it as plain text blocks
    text = _r.sub(r'(?m)^\s*[-*•]\s+', '', text)
    text = _r.sub(r'(?m)^\s*\d+[.)\-]\s+', '', text)

    # 6. Remove PS/Note segments
    text = _r.sub(r'(?i)\(?P\.?S\.?:?.+', '', text)
    text = _r.sub(r'(?i)Note:?.+', '', text)

    # 7. Collapse spacing
    text = _r.sub(r' {2,}', ' ', text)
    text = _r.sub(r'\n{3,}', '\n\n', text)
    
    # 8. Moroccan-specific cleanups
    text = _r.sub(r'(?i)^(Chouf|Smeh li|Hanya|Mreba|Daccord),?\s*', '', text)

    return text.strip()'''

    # Identify the old function block
    pattern = r'def _strip_ai_watermark\(text\):.*?return text\.strip\(\)'
    
    if not re.search(pattern, content, flags=re.DOTALL):
        print("Error: Could not find _strip_ai_watermark in file")
        return

    # Using a lambda to avoid backslash escaping issues in the replacement string
    updated_content = re.sub(pattern, lambda m: new_func, content, flags=re.DOTALL)

    with open(path, 'wb') as f:
        f.write(updated_content.encode('utf-8'))
    print("Successfully patched pipeline.py with aggressive watermark removal.")

if __name__ == "__main__":
    patch_pipeline()
