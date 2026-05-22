"""
Fix pipeline.py:
1. Repair the broken line 35 (comment merged with STATIC_RESPONSES)
2. Ensure _strip_ai_watermark is injected and applied
Run from project root: python scratch/fix_pipeline.py
"""
import re
import pathlib

PIPELINE = pathlib.Path("core/pipeline.py")
raw = PIPELINE.read_bytes()
content = raw.decode("utf-8", errors="replace")

# ── 1. Fix the merged/broken line ─────────────────────────────────────────────
# Broken: "# Static responses - no LLM nSTATIC_RESPONSES: dict..."
# Should be two separate lines
broken = r"# Static responses - no LLM n(STATIC_RESPONSES)"
fixed  = "# Static responses - no LLM needed\n\\1"
content, n = re.subn(broken, fixed, content)
print(f"[{'OK' if n else 'SKIP'}] Fixed broken line 35 (n={n})")

# ── 2. Inject _strip_ai_watermark if missing ──────────────────────────────────
FUNC_MARKER = "def _strip_ai_watermark("
INSERT_BEFORE = "async def process_message("

if FUNC_MARKER not in content:
    WATERMARK_FUNC = '''
# === Anti-AI-Watermark Post-Processor ========================================

def _strip_ai_watermark(text: str) -> str:
    """Strip AI-sounding patterns so responses read as natural human messages."""
    import re as _r

    # 1. Remove explicit AI identity phrases
    for pat in [
        r"(?i)(as an? (ai|artificial intelligence|language model|llm)[,.]?\\s*)",
        r"(?i)(en tant qu[\'\\']?(ia|intelligence artificielle|mod.{1,20}le de langage)[,.]?\\s*)",
        r"(?i)(je suis (une? )?(ia|intelligence artificielle|assistant ia|mod.{1,20}le de langage)[,.]?\\s*)",
        r"(?i)(i(\\'m| am) an? (ai|artificial intelligence|language model|chatbot)[,.]?\\s*)",
        r"(?i)(ana (ai|bernamaj|chatbot)[,.]?\\s*)",
    ]:
        text = _r.sub(pat, "", text)

    # 2. Remove markdown headings
    text = _r.sub(r"(?m)^#{1,4}\\s+.+$", "", text)

    # 3. Convert bullet lists to flowing prose
    def _b2p(m):
        lines = [_r.sub(r"^\\s*[-*\\u2022]\\s*", "", l).strip()
                 for l in m.group(0).splitlines() if l.strip()]
        return " ".join(lines)
    text = _r.sub(r"(?m)(^\\s*[-*\\u2022]\\s+.+\\n?)+", _b2p, text)

    # 4. Remove numbered list markers (keep text)
    text = _r.sub(r"(?m)^\\s*\\d+\\.\\s+", "", text)

    # 5. Keep only the first **bold**, remove the rest
    count = [0]
    def _lb(m):
        count[0] += 1
        return m.group(0) if count[0] == 1 else m.group(1)
    text = _r.sub(r"\\*\\*(.+?)\\*\\*", _lb, text)

    # 6. Remove italic underscores used as pseudo-headers
    text = _r.sub(r"_(.+?)_", r"\\1", text)

    # 7. Collapse multiple blank lines
    text = _r.sub(r"\\n{3,}", "\\n\\n", text)

    return text.strip()

# =============================================================================

'''
    idx = content.find(INSERT_BEFORE)
    if idx == -1:
        print("[ERROR] Cannot find 'async def process_message(' — aborting.")
        raise SystemExit(1)
    content = content[:idx] + WATERMARK_FUNC + content[idx:]
    print("[OK] Injected _strip_ai_watermark() function.")
else:
    print("[SKIP] _strip_ai_watermark already present.")

# ── 3. Apply to non-streaming answer ─────────────────────────────────────────
OLD_CALL = "answer = await call_llm(messages, max_tokens=800)"
NEW_CALL = "answer = _strip_ai_watermark(await call_llm(messages, max_tokens=800))"
if OLD_CALL in content:
    content = content.replace(OLD_CALL, NEW_CALL)
    print("[OK] Wrapped call_llm with _strip_ai_watermark.")
elif NEW_CALL in content:
    print("[SKIP] call_llm already wrapped.")
else:
    print("[WARN] call_llm pattern not found.")

# ── 4. Apply to streaming answer ─────────────────────────────────────────────
OLD_JOIN = 'answer = "".join(full_answer)'
NEW_JOIN = 'answer = _strip_ai_watermark("".join(full_answer))'
if OLD_JOIN in content:
    content = content.replace(OLD_JOIN, NEW_JOIN)
    print("[OK] Wrapped streaming join with _strip_ai_watermark.")
elif NEW_JOIN in content:
    print("[SKIP] Streaming join already wrapped.")
else:
    print("[WARN] Streaming join pattern not found.")

# ── 5. Write back as UTF-8 ───────────────────────────────────────────────────
PIPELINE.write_text(content, encoding="utf-8")
print("[DONE] pipeline.py saved as UTF-8.")

# ── 6. Quick syntax check ─────────────────────────────────────────────────────
import ast
try:
    ast.parse(content)
    print("[OK] Syntax check passed.")
except SyntaxError as e:
    print(f"[ERROR] Syntax error: {e}")
