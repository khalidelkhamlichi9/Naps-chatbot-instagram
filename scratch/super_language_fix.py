import os
import re

def super_language_fix():
    pipeline_path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    
    with open(pipeline_path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Update the prompt building logic to be extremely explicit about translation
    new_prompt_logic = r'''    # 4. Build prompt
    custom_prompt   = await _get_active_system_prompt(session, language)
    base_system     = get_system_prompt(language)
    
    # Translate Context Instruction
    lang_map = {
        "fr": "en Français",
        "ar": "en Arabe classique",
        "darija": "en Darija Marocaine (phonétique)",
        "en": "in English"
    }
    target_lang = lang_map.get(language, "Français")
    
    translation_instr = f"\n\nINSTRUCTION CRITIQUE: Réponds EXCLUSIVEMENT {target_lang}. " \
                        f"Même si les informations ci-dessous (CONTEXTE) sont en Français, tu DOIS les traduire."
    
    full_system = f"{base_system}{translation_instr}"
    
    if context:
        full_system += f"\n\nINFORMATIONS NAPS (À TRADUIRE SI NÉCESSAIRE) :\n{context}"'''

    pattern_prompt = r'    custom_prompt   = await _get_active_system_prompt\(session, language\).*?if context:.*?\{context\}"'
    content = re.sub(pattern_prompt, lambda m: new_prompt_logic, content, flags=re.DOTALL)

    # Ensure no cache hit happens for now to test live
    content = content.replace('if _should_cache(message):', 'if False: # Disabled for testing')

    with open(pipeline_path, 'wb') as f:
        f.write(content.encode('utf-8'))
    print("Successfully updated pipeline with extreme translation instructions.")

if __name__ == "__main__":
    super_language_fix()
