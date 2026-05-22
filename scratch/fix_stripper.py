import os
import re

def fix_stripper():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Better _strip_ai_watermark that converts lists to paragraphs
    new_func = r'''def _strip_ai_watermark(text):
    """Clean AI artifacts while preserving the core message content."""
    if not text: return ""
    import re as _r
    
    # 1. Remove ALL emojis and special symbols
    text = _r.sub(r'[^\w\s\.,!\?:\-\(\)\'\"\u0600-\u06FF\u0100-\u017FÀ-ÿ]+', ' ', text)
    
    # 2. Convert bullet lists to flowing text instead of deleting them
    def _bullet_to_prose(m):
        lines = [l.strip() for l in m.group(0).splitlines() if l.strip()]
        # Remove the actual bullet char from each line
        clean_lines = [_r.sub(r'^\s*[-*•]\s*', '', l) for l in lines]
        return " ".join(clean_lines) + " "
    
    # Match blocks of bullet points
    text = _r.sub(r'(?m)(^\s*[-*•]\s+.+\n?)+', _bullet_to_prose, text)
    
    # 3. Remove numbered list markers but keep the text
    text = _r.sub(r'(?m)^\s*\d+[.)\-]\s+', ' ', text)
    
    # 4. Remove Markdown bold/italic
    text = _r.sub(r'\*\*|\*|__|_', '', text)
    
    # 5. Collapse extra whitespace
    text = _r.sub(r' {2,}', ' ', text)
    text = _r.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()'''

    pattern = r'def _strip_ai_watermark\(text\):.*?return text\.strip\(\)'
    
    updated_content = re.sub(pattern, lambda m: new_func, content, flags=re.DOTALL)

    with open(path, 'wb') as f:
        f.write(updated_content.encode('utf-8'))
    print("Successfully updated watermark stripper to preserve list content.")

if __name__ == "__main__":
    fix_stripper()
