import os

def fix_indentation():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Fix the merged comment and variable
    # We look for the pattern where STATIC_RESPONSES is stuck to the comment
    bad_line_pattern = r'# Static responses.*?STATIC_RESPONSES'
    
    # We'll replace it with a clean version
    fixed_content = re.sub(bad_line_pattern, '# Static responses - no LLM needed\nSTATIC_RESPONSES', content)

    # Also check if there are other indentation errors introduced
    # For example, ensure the whole STATIC_RESPONSES block is properly formatted
    
    with open(path, 'wb') as f:
        f.write(fixed_content.encode('utf-8'))
    print("Successfully fixed indentation in pipeline.py")

import re
if __name__ == "__main__":
    fix_indentation()
