"""
Patch pipeline.py to add _strip_ai_watermark() post-processor.
Run once from the project root:
    python scratch/patch_pipeline.py
"""
import re
import pathlib

PIPELINE = pathlib.Path("core/pipeline.py")

# Read raw bytes, decode with error replacement so we don't crash on bad chars
raw = PIPELINE.read_bytes()
content = raw.decode("utf-8", errors="replace")

# ── 1. The function to inject ─────────────────────────────────────────────────
WATERMARK_FUNC = '''

# === Anti-AI-Watermark Post-Processor ========================================

def _strip_ai_watermark(text: str) -> str:
    """
    Remove AI-sounding patterns so the response reads like a natural
    human message, not a generated document.
    """
    import re as _re

    # 1. Remove explicit AI declarations
    ai_patterns = [
        r"(?i)(as an? (ai|artificial intelligence|language model|llm)[,.]?\\s*)",
        r"(?i)(en tant qu[\'\\']?(ia|intelligence artificielle|mod.*?le de langage)[,.]?\\s*)",
        r"(?i)(je suis (une? )?(ia|intelligence artificielle|assistant ia|mod.*?le de langage)[,.]?\\s*)",
        r"(?i)(i(\\'m| am) an? (ai|artificial intelligence|language model|chatbot)[,.]?\\s*)",
        r"(?i)(ana (ai|bernamaj|chatbot)[,.]?\\s*)",
    ]
    for pat in ai_patterns:
        text = _re.sub(pat, "", text)

    # 2. Remove markdown headings (## Title)
    text = _re.sub(r"(?m)^#{1,4}\\s+.+$", "", text)

    # 3. Convert bullet lists into flowing prose
    def _bullets_to_prose(m):
        lines = [_re.sub(r"^\\s*[-*\\u2022]\\s*", "", ln).strip()
                 for ln in m.group(0).splitlines() if ln.strip()]
        return " ".join(lines)
    text = _re.sub(r"(?m)(^\\s*[-*\\u2022]\\s+.+\\n?)+", _bullets_to_prose, text)

    # 4. Remove numbered list markers
    text = _re.sub(r"(?m)^\\s*\\d+\\.\\s+", "", text)

    # 5. Keep only the FIRST **bold**, strip the rest
    bold_count = [0]
    def _limit_bold(m):
        bold_count[0] += 1
        return m.group(0) if bold_count[0] == 1 else m.group(1)
    text = _re.sub(r"\\*\\*(.+?)\\*\\*", _limit_bold, text)

    # 6. Remove italic underscores used as pseudo-headers
    text = _re.sub(r"_(.+?)_", r"\\1", text)

    # 7. Collapse excessive blank lines
    text = _re.sub(r"\\n{3,}", "\\n\\n", text)

    return text.strip()

# =============================================================================
'''

# ── 2. Find insertion point: just before "async def process_message" ──────────
INSERT_MARKER = "async def process_message("
if WATERMARK_FUNC.strip()[:40] in content:
    print("[OK] _strip_ai_watermark already present, skipping injection.")
else:
    idx = content.find(INSERT_MARKER)
    if idx == -1:
        print("[ERROR] Could not find 'async def process_message(' in pipeline.py")
        raise SystemExit(1)
    content = content[:idx] + WATERMARK_FUNC + "\n" + content[idx:]
    print("[OK] Injected _strip_ai_watermark() function.")

# ── 3. Wrap every LLM answer with _strip_ai_watermark() ──────────────────────
# Pattern: answer = await call_llm(...)  -> answer = _strip_ai_watermark(await call_llm(...))
def wrap_call_llm(m):
    line = m.group(0)
    if "_strip_ai_watermark" in line:
        return line  # already wrapped
    return line.replace("await call_llm(", "_strip_ai_watermark(await call_llm(", 1).rstrip() + ")"

content = re.sub(r".*answer\s*=\s*await call_llm\(.*", wrap_call_llm, content)

# Pattern: full_answer.append(chunk) in the streaming generator
# We strip after collecting full answer, before saving
STREAM_SAVE_OLD = "            answer = \"\".join(full_answer)"
STREAM_SAVE_NEW = "            answer = _strip_ai_watermark(\"\".join(full_answer))"
if STREAM_SAVE_OLD in content and STREAM_SAVE_NEW not in content:
    content = content.replace(STREAM_SAVE_OLD, STREAM_SAVE_NEW)
    print("[OK] Applied _strip_ai_watermark to streaming path.")
else:
    print("[INFO] Streaming path: already patched or pattern not found.")

# ── 4. Write back ─────────────────────────────────────────────────────────────
PIPELINE.write_text(content, encoding="utf-8")
print("[DONE] pipeline.py patched successfully.")
