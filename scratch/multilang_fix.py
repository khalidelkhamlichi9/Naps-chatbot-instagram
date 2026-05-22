"""
Full multilingual + anti-AI-watermark fix:
1. Expand Darija detection signals
2. Strengthen _strip_ai_watermark (emoji lists, ### etc.)
3. Fix DB custom prompt to APPEND, not REPLACE language system prompt

Run: python scratch/multilang_fix.py
"""
import pathlib, re, ast

pipeline = pathlib.Path("core/pipeline.py")
src = pipeline.read_text(encoding="utf-8")

# ══════════════════════════════════════════════════════════════════════════════
# FIX 1: Strengthen _strip_ai_watermark
# ══════════════════════════════════════════════════════════════════════════════
OLD_FUNC = 'def _strip_ai_watermark(text):'
NEW_FUNC = '''def _strip_ai_watermark(text):'''

WATERMARK_BODY_OLD = r"""    # type: (str) -> str
    \"\"\"Strip AI-sounding patterns so responses read as natural human messages.\"\"\"
    import re as _r

    # 1. Remove explicit AI identity phrases (case-insensitive)
    _ai_pats = [
        r"(?i)(as an? (ai|artificial intelligence|language model|llm)[,.]?\\s*)",
        r"(?i)(en tant qu.{0,2}(ia|intelligence artificielle)[,.]?\\s*)",
        r"(?i)(je suis (une? )?(ia|intelligence artificielle|assistant ia)[,.]?\\s*)",
        r"(?i)(i('m| am) an? (ai|artificial intelligence|language model|chatbot)[,.]?\\s*)",
        r"(?i)(ana (ai|bernamaj|chatbot)[,.]?\\s*)",
    ]
    for _p in _ai_pats:
        text = _r.sub(_p, "", text)

    # 2. Remove markdown headings (## Title, ### Title)
    text = _r.sub(r"(?m)^#{1,4}\\s+.+$", "", text)

    # 3. Convert bullet lists to flowing prose
    def _b2p(_m):
        _lines = [_r.sub(r"^\\s*[-*\\u2022]\\s*", "", _l).strip()
                  for _l in _m.group(0).splitlines() if _l.strip()]
        return " ".join(_lines)
    text = _r.sub(r"(?m)(^\\s*[-*\\u2022]\\s+.+\\n?)+", _b2p, text)

    # 4. Remove numbered list markers, keep text
    text = _r.sub(r"(?m)^\\s*\\d+\\.\\s+", "", text)

    # 5. Keep only the first **bold**, strip the rest
    _cnt = [0]
    def _lb(_m):
        _cnt[0] += 1
        return _m.group(0) if _cnt[0] == 1 else _m.group(1)
    text = _r.sub(r"\\*\\*(.+?)\\*\\*", _lb, text)

    # 6. Remove italic underscore pseudo-headers
    text = _r.sub(r"_(.+?)_", r"\\1", text)

    # 7. Collapse multiple blank lines
    text = _r.sub(r"\\n{3,}", "\\n\\n", text)

    return text.strip()"""

WATERMARK_BODY_NEW = r"""    # type: (str) -> str
    \"\"\"Strip AI-sounding patterns so responses read as natural human messages.\"\"\"
    import re as _r

    # 1. Remove explicit AI identity phrases
    _ai_pats = [
        r"(?i)(as an? (ai|artificial intelligence|language model|llm)[,.]?\\s*)",
        r"(?i)(en tant qu.{0,2}(ia|intelligence artificielle)[,.]?\\s*)",
        r"(?i)(je suis (une? )?(ia|intelligence artificielle|assistant ia)[,.]?\\s*)",
        r"(?i)(i('m| am) an? (ai|artificial intelligence|language model|chatbot)[,.]?\\s*)",
        r"(?i)(ana (ai|bernamaj|chatbot)[,.]?\\s*)",
    ]
    for _p in _ai_pats:
        text = _r.sub(_p, "", text)

    # 2. Remove markdown headings (## ### ####)
    text = _r.sub(r"(?m)^#{1,4}\\s+.+$", "", text)

    # 3. Strip emoji-numbered list lines (1️⃣ ... , 🔹 ..., ✅ ... at line start)
    # Keep the text, remove the emoji prefix
    text = _r.sub(
        r"(?m)^[\\U0001F300-\\U0001FFFE\\u2600-\\u26FF\\u2700-\\u27BF]+\\s*",
        "", text
    )

    # 4. Convert bullet lists (- * •) to flowing prose
    def _b2p(_m):
        _lines = [_r.sub(r"^\\s*[-*\\u2022]\\s*", "", _l).strip()
                  for _l in _m.group(0).splitlines() if _l.strip()]
        return " ".join(_lines)
    text = _r.sub(r"(?m)(^\\s*[-*\\u2022]\\s+.+\\n?)+", _b2p, text)

    # 5. Remove numbered list markers (1. 2. 3.) — keep text
    text = _r.sub(r"(?m)^\\s*\\d+[.)\\-]\\s+", "", text)

    # 6. Keep only the FIRST **bold**, remove the rest
    _cnt = [0]
    def _lb(_m):
        _cnt[0] += 1
        return _m.group(0) if _cnt[0] == 1 else _m.group(1)
    text = _r.sub(r"\\*\\*(.+?)\\*\\*", _lb, text)

    # 7. Remove italic underscore pseudo-headers
    text = _r.sub(r"_(.+?)_", r"\\1", text)

    # 8. Remove "(P.S. : ...)" or "P.S. ..." at end
    text = _r.sub(r"(?i)\\(?P\\.?S\\.?:?.+", "", text)

    # 9. Collapse multiple blank lines
    text = _r.sub(r"\\n{3,}", "\\n\\n", text)

    return text.strip()"""

if WATERMARK_BODY_OLD in src:
    src = src.replace(WATERMARK_BODY_OLD, WATERMARK_BODY_NEW)
    print("[OK] _strip_ai_watermark strengthened.")
else:
    print("[WARN] Could not find old watermark body to replace.")

# ══════════════════════════════════════════════════════════════════════════════
# FIX 2: DB custom prompt APPENDS to language prompt, not replaces
# ══════════════════════════════════════════════════════════════════════════════
OLD_PROMPT_LOGIC = (
    "    custom_prompt   = await _get_active_system_prompt(session, language)\n"
    "    base_system     = get_system_prompt(language, custom_prompt)"
)
NEW_PROMPT_LOGIC = (
    "    custom_prompt   = await _get_active_system_prompt(session, language)\n"
    "    # Always use language-specific system prompt; append DB custom instructions\n"
    "    base_system     = get_system_prompt(language)\n"
    "    if custom_prompt:\n"
    "        base_system = base_system + \"\\n\\nInstructions supplementaires:\\n\" + custom_prompt"
)

if OLD_PROMPT_LOGIC in src:
    src = src.replace(OLD_PROMPT_LOGIC, NEW_PROMPT_LOGIC)
    print("[OK] DB prompt now appends to language prompt instead of replacing it.")
else:
    print("[WARN] Could not find custom_prompt logic block.")

# ══════════════════════════════════════════════════════════════════════════════
# Save + syntax check
# ══════════════════════════════════════════════════════════════════════════════
pipeline.write_text(src, encoding="utf-8")
print("[OK] pipeline.py saved.")

try:
    ast.parse(src)
    print("[OK] Syntax valid.")
except SyntaxError as e:
    print(f"[ERR] Syntax error: {e}")
