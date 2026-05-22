"""
Clean patch for pipeline.py:
- Reads the file in binary (preserves original encoding perfectly)
- Injects _strip_ai_watermark() before process_message
- Wraps call_llm and streaming join

Run from project root: python scratch/clean_patch.py
"""
import pathlib, re, ast

PIPELINE = pathlib.Path("core/pipeline.py")

# Read original bytes exactly
raw = PIPELINE.read_bytes()

# Decode safely — the file uses the system encoding (likely cp1252 on Windows)
# Try utf-8 first, then cp1252 fallback
for enc in ("utf-8", "utf-8-sig", "cp1252", "cp1256"):
    try:
        content = raw.decode(enc)
        print(f"[OK] Decoded with {enc}")
        break
    except Exception:
        continue
else:
    content = raw.decode("utf-8", errors="replace")
    print("[WARN] Decoded with utf-8 + errors=replace")

# ── Watermark function (ASCII-safe, no special chars) ─────────────────────────
WATERMARK = r'''

# === Anti-AI-Watermark Post-Processor ========================================

def _strip_ai_watermark(text):
    # type: (str) -> str
    """Strip AI-sounding patterns so responses read as natural human messages."""
    import re as _r

    # 1. Remove explicit AI identity phrases (case-insensitive)
    _ai_pats = [
        r"(?i)(as an? (ai|artificial intelligence|language model|llm)[,.]?\s*)",
        r"(?i)(en tant qu.{0,2}(ia|intelligence artificielle)[,.]?\s*)",
        r"(?i)(je suis (une? )?(ia|intelligence artificielle|assistant ia)[,.]?\s*)",
        r"(?i)(i('m| am) an? (ai|artificial intelligence|language model|chatbot)[,.]?\s*)",
        r"(?i)(ana (ai|bernamaj|chatbot)[,.]?\s*)",
    ]
    for _p in _ai_pats:
        text = _r.sub(_p, "", text)

    # 2. Remove markdown headings (## Title, ### Title)
    text = _r.sub(r"(?m)^#{1,4}\s+.+$", "", text)

    # 3. Convert bullet lists to flowing prose
    def _b2p(_m):
        _lines = [_r.sub(r"^\s*[-*\u2022]\s*", "", _l).strip()
                  for _l in _m.group(0).splitlines() if _l.strip()]
        return " ".join(_lines)
    text = _r.sub(r"(?m)(^\s*[-*\u2022]\s+.+\n?)+", _b2p, text)

    # 4. Remove numbered list markers, keep text
    text = _r.sub(r"(?m)^\s*\d+\.\s+", "", text)

    # 5. Keep only the first **bold**, strip the rest
    _cnt = [0]
    def _lb(_m):
        _cnt[0] += 1
        return _m.group(0) if _cnt[0] == 1 else _m.group(1)
    text = _r.sub(r"\*\*(.+?)\*\*", _lb, text)

    # 6. Remove italic underscore pseudo-headers
    text = _r.sub(r"_(.+?)_", r"\1", text)

    # 7. Collapse multiple blank lines
    text = _r.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

# =============================================================================

'''

# ── Inject before process_message ─────────────────────────────────────────────
INSERT_BEFORE = "async def process_message("
if "_strip_ai_watermark" not in content:
    idx = content.find(INSERT_BEFORE)
    if idx == -1:
        print("[ERROR] Cannot find 'async def process_message(' — aborting.")
        raise SystemExit(1)
    content = content[:idx] + WATERMARK + content[idx:]
    print("[OK] Injected _strip_ai_watermark() function.")
else:
    print("[SKIP] _strip_ai_watermark already present.")

# ── Wrap non-streaming answer ─────────────────────────────────────────────────
OLD_CALL = "answer = await call_llm(messages, max_tokens=800)"
NEW_CALL = "answer = _strip_ai_watermark(await call_llm(messages, max_tokens=800))"
if OLD_CALL in content and NEW_CALL not in content:
    content = content.replace(OLD_CALL, NEW_CALL)
    print("[OK] Wrapped call_llm with _strip_ai_watermark.")
else:
    print("[SKIP] call_llm already wrapped or not found.")

# ── Wrap streaming answer ─────────────────────────────────────────────────────
OLD_JOIN = 'answer = "".join(full_answer)'
NEW_JOIN = 'answer = _strip_ai_watermark("".join(full_answer))'
if OLD_JOIN in content and NEW_JOIN not in content:
    content = content.replace(OLD_JOIN, NEW_JOIN)
    print("[OK] Wrapped streaming join.")
else:
    print("[SKIP] Streaming join already wrapped or not found.")

# ── Write as UTF-8 ────────────────────────────────────────────────────────────
PIPELINE.write_text(content, encoding="utf-8")
print("[DONE] pipeline.py saved as UTF-8.")

# ── Syntax check ──────────────────────────────────────────────────────────────
try:
    ast.parse(content)
    print("[OK] Syntax valid — ready to run!")
except SyntaxError as e:
    print(f"[ERROR] Syntax error after patch: {e}")
