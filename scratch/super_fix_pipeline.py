import os
import re

def super_fix_pipeline():
    path = r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot\core\pipeline.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='replace')

    # Identify the start of STATIC_RESPONSES and the start of process_message
    static_start = content.find('STATIC_RESPONSES: dict')
    if static_start == -1:
        static_start = content.find('STATIC_RESPONSES = {')
    
    process_message_start = content.find('async def process_message')
    
    if static_start == -1 or process_message_start == -1:
        print(f"Error: Could not find markers (static_start={static_start}, process_message_start={process_message_start})")
        return

    # Everything before STATIC_RESPONSES
    head = content[:static_start]
    
    # Everything from process_message onwards
    tail = content[process_message_start:]

    # Clean Middle Section
    middle = r'''STATIC_RESPONSES: dict[str, dict[str, str]] = {
    "greeting": {
        "fr":     "Bonjour, je suis Karim de NAPS. Comment puis-je vous aider à booster votre activité aujourd'hui ?",
        "ar":     "مرحباً، أنا كريم من NAPS. كيف يمكنني مساعدتك في تطوير تجارتك اليوم؟",
        "darija": "Salam, ana Karim mn NAPS. Kifach n9der n3awnk tkhdem mzyan f l-bi3 dyalk l-youm?",
        "en":     "Hello, I'm Karim from NAPS. How can I help you grow your business today?",
    },
    "farewell": {
        "fr":     "Merci de votre confiance. Je reste à votre disposition pour toute autre question.",
        "ar":     "شكراً لثقتكم. أنا رهن إشارتكم لأي سؤال آخر.",
        "darija": "Shokran 3la ti9a dyalk. Ana hna ila htajiti chi 7aja khora.",
        "en":     "Thank you for your trust. I'm here if you have any other questions.",
    },
    "thanks": {
        "fr":     "Avec plaisir ! C'est ma mission de vous accompagner vers le succès. Avez-vous d'autres questions ?",
        "ar":     "بكل سرور! مهمتي هي مواكبتكم نحو النجاح. هل لديكم أسئلة أخرى؟",
        "darija": "B kol srour! Hada houwa l-hadaf dyali. 3ndek chi soual akhor?",
        "en":     "You're welcome! My mission is to support your success. Any other questions?",
    },
    "out_of_scope": {
        "fr":     "Je suis expert des solutions NAPS (TPE, Ecommerce). Pour tout ce qui concerne vos paiements, je suis là. Souhaitez-vous découvrir nos offres ?",
        "ar":     "أنا خبير في حلول NAPS. أنا هنا لكل ما يتعلق بمدفوعاتكم. هل تودون اكتشاف عروضنا؟",
        "darija": "Ana expert f les solutions NAPS. Bach tkhdem mzyan f l-bi3 dyalk ana hna. Bghiti nchofou l-offres li 3ndna?",
        "en":     "I am an expert in NAPS solutions. I'm here for all your payment needs. Would you like to explore our offers?",
    },
}

async def _get_active_system_prompt(session, language: str) -> str | None:
    """Fetch the active system prompt for a specific language from DB."""
    from database.models import SystemPrompt
    from sqlalchemy import select
    result = await session.execute(
        select(SystemPrompt)
        .where(SystemPrompt.is_active == True)
        .where(SystemPrompt.language == language)
        .order_by(SystemPrompt.id.desc())
        .limit(1)
    )
    prompt = result.scalar_one_or_none()
    return prompt.content if prompt else None

async def _detect_intent(message: str, language: str) -> str:
    """Lightweight intent detection via keyword matching."""
    msg = message.lower().strip()
    words = set(msg.split())

    greeting_signals = {"bonjour", "salam", "hello", "hi", "bonsoir", "ahlan", "labas", "allo", "salut"}
    farewell_signals = {"au revoir", "beslama", "bye", "goodbye", "bslama"}
    thanks_signals   = {"merci", "choukran", "thank", "shokran", "3afak"}
    oos_signals      = {"météo", "foot", "sport", "recette", "cuisine", "blague", "politique"}

    if len(words) <= 3:
        if any(s in words for s in greeting_signals): return "greeting"
        if any(s in words for s in thanks_signals): return "thanks"
    if any(s in msg for s in farewell_signals) and len(words) <= 3: return "farewell"
    if any(s in msg for s in oos_signals): return "out_of_scope"
    return "faq"

async def _log_conversation(session, user_id, language, latency_ms, cache_hit):
    """Log conversation metadata."""
    from database.models import Conversation
    log = Conversation(
        user_id=user_id,
        platform="instagram",
        language=language,
        latency_ms=latency_ms,
        cache_hit=cache_hit,
    )
    session.add(log)
    await session.commit()

def _should_cache(message: str) -> bool:
    """Determine if a message is 'static/general' enough to be cached."""
    import re as _re
    msg = message.lower()
    if _re.search(r'\d{4,}', msg): return False
    personal_keywords = ["mon ", "ma ", "mes ", "mon compte", "ma carte", "virement", "recharge"]
    if any(k in msg for k in personal_keywords): return False
    return True

def _strip_ai_watermark(text):
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
    for _p in _ai_pats: text = _r.sub(_p, '', text)

    # 2. Remove ALL markdown and emojis
    text = _r.sub(r'(?m)^#{1,6}\s+', '', text)
    emoji_pattern = _r.compile(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E6-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF\U0000FE00-\U0000FE0F\U0001F900-\U0001F9FF\U0001F170-\U0001F251]+", flags=_r.UNICODE)
    text = emoji_pattern.sub('', text)
    text = _r.sub(r'\*\*|\*|__||_', '', text)

    # 3. Remove lists and PS
    text = _r.sub(r'(?m)^\s*[-*•\d+[.)\-]]\s+', '', text)
    text = _r.sub(r'(?i)(\(?P\.?S\.?:?.+|Note:?.+)', '', text)

    # 4. Collapse spacing
    text = _r.sub(r' {2,}', ' ', text)
    text = _r.sub(r'\n{3,}', '\n\n', text)
    text = _r.sub(r'(?i)^(Chouf|Smeh li|Hanya|Mreba|Daccord),?\s*', '', text)

    return text.strip()

'''

    final_content = head + middle + tail

    with open(path, 'wb') as f:
        f.write(final_content.encode('utf-8'))
    print("Successfully rebuilt pipeline.py structure.")

if __name__ == "__main__":
    super_fix_pipeline()
