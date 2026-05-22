"""
Main pipeline orchestration for Chatbot NAPS.
"""

import time
import asyncio
import os
import logging
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from rag.embedder import embed
from rag.retriever import retrieve, build_context
from llm.deepseek import call_llm, stream_llm
from cache.redis_client import (
    search_cache, save_to_cache,
    get_history, save_history,
)
from core.language import detect_language, determine_language
from database.models import SystemPrompt, Conversation

logger = logging.getLogger("naps-chatbot")

MAX_HISTORY_TURNS  = int(os.getenv("MAX_HISTORY_TURNS", "10"))
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "3500"))

# Static responses - no LLM needed
STATIC_RESPONSES: dict[str, dict[str, str]] = {
    "greeting": {
        "fr":     "Bonjour. Je suis Yasmine de Naps. Comment puis-je vous aider ?",
        "ar":     "مرحباً. أنا ياسمين من Naps. كيف يمكنني مساعدتك ؟",
        "darija": "Wa alaykoum salam. Ana Yasmine men Naps. Kifash n9der n3awnek ?",
        "en":     "Hello. I'm Yasmine from Naps. How can I help you ?",
    },
    "farewell": {
        "fr":     "Merci pour cet échange. À très vite.",
        "ar":     "شكراً على هذا التواصل. إلى اللقاء قريباً.",
        "darija": "Choukran 3la had l'échange. Nchoufouk 9rib.",
        "en":     "Thanks for the chat. Talk soon.",
    },
    "thanks": {
        "fr":     "Avec plaisir. Y a-t-il autre chose que je peux vérifier pour vous ?",
        "ar":     "بكل سرور. هل هناك شيء آخر يمكنني التحقق منه لك ؟",
        "darija": "Bla jamil. Wash kayna chi 7aja okhra n9der nchouf lik ?",
        "en":     "You're welcome. Anything else I can check for you ?",
    },
    "out_of_scope": {
        "fr":     "Je suis spécialisée sur les solutions de paiement Naps (TPE, e-commerce). Sur ce sujet précis, je ne suis pas la mieux placée. Vous avez une question paiement ?",
        "ar":     "أنا متخصصة في حلول الدفع Naps. حول هذا الموضوع، لست الأنسب. هل لديك سؤال حول الدفع ؟",
        "darija": "Ana spécialisée f les solutions dyal paiement Naps. F had l'sujet machi ana l'meilleure. 3andek chi soual 3la paiement ?",
        "en":     "I'm specialized in Naps payment solutions (POS, e-commerce). On this specific topic, I'm not the best fit. Any payment question ?",
    },
    "services": {
        "fr":     "NAPS propose une large gamme de solutions de paiement électronique sécurisé au Maroc :\n- **Terminaux de Paiement (TPE) :** Fixes ou Mobiles déployés sous 48h, avec paiement en plusieurs fois (BNPL / N fois), gestion dématérialisée des pourboires, et monétique intégrée avec votre logiciel de caisse.\n- **Paiement E-commerce :** Passerelle de paiement sécurisée pour accepter les règlements par carte bancaire sur vos sites internet et boutiques en ligne.\n- **Cartes de Paiement & Retraits :** Cartes bancaires prépayées, cartes notes de frais pour collaborateurs, cartes salaires pour employés non bancarisés, et programmes de fidélité avec cashback.\n- **Smart City & Solutions Institutionnelles :** Intégration de solutions monétiques intelligentes dans le quotidien (universités, transports, stades, etc.).",
    },
    "contact": {
        "fr":     "Pour contacter NAPS :\n- **Téléphone :** 05 22 91 74 74\n- **E-mail :** contact@naps.ma\n- **Siège social :** Technopole Aéroport Mohamed V, Nouaceur, Maroc",
    },
    "horaires": {
        "fr":     "Nos services et support client sont disponibles :\n- **En ligne et Assistance :** 24h/24 et 7j/7\n- **Centre de Relation Client :** Par téléphone au 05 22 91 74 74",
    },
    "a_propos": {
        "fr":     "NAPS est le premier opérateur financier indépendant au Maroc, agréé par Bank Al-Maghrib.\nFiliale de **M2M Group** (expert monétique coté en bourse depuis plus de 35 ans), NAPS a pour mission de démocratiser le paiement électronique sécurisé pour les particuliers, les professionnels et les entreprises.",
    },
}

async def _get_active_system_prompt(session) -> str:
    """Fetch the active global system prompt from DB or return default."""
    result = await session.execute(
        select(SystemPrompt)
        .where(SystemPrompt.is_active == True)
        .order_by(SystemPrompt.id.desc())
        .limit(1)
    )
    prompt = result.scalar_one_or_none()
    if prompt and prompt.content:
        return prompt.content
    return "Tu es l'assistant virtuel de NAPS. Réponds aux questions sur les produits NAPS (TPE, Ecommerce, Cartes)."

async def _detect_intent(message: str, language: str) -> str:
    """Lightweight intent detection via keyword matching."""
    msg = message.lower().strip()
    
    # 1. Exact match (e.g. for button clicks)
    if msg in ("vos services", "services", "solutions", "produits"):
        return "services"
    if msg in ("nous contacter", "contact", "contacter", "telephone", "adresse", "email", "mail"):
        return "contact"
    if msg in ("horaires", "horaire", "ouverture", "support client", "relation client"):
        return "horaires"
    if msg in ("à propos de naps", "a propos de naps", "a propos", "à propos", "qui sommes-nous", "qui sommes nous", "c'est quoi naps"):
        return "a_propos"
        
    import re
    clean_msg = re.sub(r'[^\w\s]', ' ', msg)
    msg_words = clean_msg.split()
    
    # 2. Short queries (<= 3 words)
    if len(msg_words) <= 3:
        if any(w in msg_words for w in ("services", "solutions", "produits", "خدمات", "khedmat")):
            return "services"
        if any(w in msg_words for w in ("contacter", "contact", "telephone", "adresse", "email", "mail", "tassal", "tasslo")):
            return "contact"
        if any(w in msg_words for w in ("horaires", "horaire", "ouverture", "lweqt", "wa9t", "w9t")):
            return "horaires"
        if "propos" in msg_words or ("qui" in msg_words and "sommes" in msg_words) or "chkon" in msg_words or "chkoune" in msg_words:
            return "a_propos"

    words = set(msg_words)
    greeting_signals = {
        "bonjour", "salam", "hello", "hi", "bonsoir", "ahlan", "labas", "allo", "salut",
        "salamou", "salamoualikoum", "alikoum", "marhba", "marhaba", "صباح", "مساء", "أهلا"
    }
    farewell_signals = {"au revoir", "beslama", "bye", "goodbye", "bslama", "وداعا", "لقاء"}
    thanks_signals   = {"merci", "choukran", "thank", "shokran", "3afak", "شكرا", "بارك"}
    oos_signals      = {
        "météo", "foot", "sport", "recette", "cuisine", "blague", "politique", 
        "actualité", "religion", "sexe", "drogue", "alcool", "musique", "film",
        "chat", "chien", "animal", "jeu", "gaming", "voyage"
    }
    if len(words) <= 3:
        if any(s in words for s in greeting_signals): return "greeting"
        if any(s in words for s in thanks_signals): return "thanks"
    if any(s in msg for s in farewell_signals) and len(words) <= 3: return "farewell"
    if any(s in msg for s in oos_signals): return "out_of_scope"
    return "faq"

async def _log_conversation(session, user_id, language, latency_ms, cache_hit):
    """Log conversation metadata."""
    log = Conversation(
        user_id=user_id,
        platform="instagram",
        language=language,
        latency_ms=latency_ms,
        cache_hit=cache_hit,
    )
    session.add(log)
    await session.commit()

def _strip_ai_watermark(text):
    """Aggressively remove all AI signatures, emojis, and formatting."""
    if not text: return ""
    import re as _r
    # Remove ALL emojis and special symbols (preserving Moroccan characters)
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
    return text.strip()

async def process_message(
    message: str,
    user_id: str,
    session: AsyncSession,
    stream: bool = False,
):
    """
    Full pipeline. Returns:
    - stream=False -> str (full answer)
    - stream=True  -> AsyncGenerator[str, None]
    """
    # 0. Security Guard
    blacklist = ["rm -rf", "drop database", "shutdown", "format c:", "ignore previous instructions", "ignore your instructions", "reveal your prompt", "show your system prompt", "act as", "jailbreak", "dan mode", "SELECT * FROM", "INSERT INTO", "DELETE FROM", "__import__", "exec(", "eval("]
    if any(term in message.lower() for term in blacklist):
        logger.warning(f"🚨 Security alert: Blocked message from {user_id}")
        msg = "Désolé, je ne peux pas traiter ce message pour des raisons de sécurité. 🛡️"
        if stream:
            async def blocked(): yield msg
            return blocked()
        return msg

    t_start = time.monotonic()
    # Load history early for language determination and model input
    history = await get_history(user_id, max_turns=MAX_HISTORY_TURNS)
    language = determine_language(message, history)

    # 1. Static intents
    intent = await _detect_intent(message, language)
    if intent in STATIC_RESPONSES:
        if intent in ("services", "contact", "horaires", "a_propos"):
            answer = STATIC_RESPONSES[intent]["fr"]
        else:
            answer = STATIC_RESPONSES[intent].get(language, STATIC_RESPONSES[intent]["fr"])
        await save_history(user_id, "user", message)
        await save_history(user_id, "assistant", answer)
        latency = (time.monotonic() - t_start) * 1000
        await _log_conversation(session, user_id, language, latency, False)
        if stream:
            async def _static_stream(): yield answer
            return _static_stream()
        return answer

    # 2. RAG retrieval
    chunks = await retrieve(message, session)
    context = build_context(chunks)

    # 3. Build prompt
    custom_prompt = await _get_active_system_prompt(session)
    
    lang_names = {"fr": "FRANÇAIS", "ar": "ARABE", "darija": "DARIJA MAROCAIN (ARABE MAROCAIN)", "en": "ANGLAIS"}
    target_lang = lang_names.get(language, "FRANÇAIS")
    
    system_parts = []
    
    if context:
        system_parts.append("### BACKGROUND KNOWLEDGE CONTEXT ###")
        system_parts.append("Use the following information to answer the user if relevant. If it conflicts with the instructions below, follow the instructions below.")
        system_parts.append(context)
        system_parts.append("---")
        system_parts.append("")

    # Determine dynamic language instruction to override the DB prompt rules
    if language == "darija":
        lang_instruction = (
            "1. FORCE MOROCCAN DARIJA (LATIN LETTERS / ARABIZI) :\n"
            "   - The user is speaking Moroccan Darija in Latin script (Arabizi).\n"
            "   - You MUST translate the French context and reply ONLY in Moroccan Darija Arabizi (e.g., using words like: 't9der', '3ndna', 'taman', 'bghit', 'mzyan', 'charaf', 'safi', 'khoya').\n"
            "   - STRICT PROHIBITION: Do NOT reply in French. Do NOT output French sentences (like 'Bien sûr', 'On a 3 formules principales', 'Laquelle vous intéresse').\n"
            "   - OVERRIDE DATABASE PROMPT: Even if the instructions below say 'Mix français + darija : réponds au même ratio', you must NOT reply in French. Respond 100% in Darija Arabizi, only keeping technical terms like 'TPE' or 'frais' in French."
        )
    elif language == "ar":
        lang_instruction = (
            "1. FORCE ARABIC / MOROCCAN DARIJA (ARABIC SCRIPT) :\n"
            "   - The user is speaking in Arabic or Darija with Arabic letters.\n"
            "   - You MUST respond in Arabic or Moroccan Darija using Arabic letters only.\n"
            "   - STRICT PROHIBITION: Do NOT reply in French."
        )
    elif language == "en":
        lang_instruction = (
            "1. FORCE ENGLISH : The user is speaking in English. You MUST respond in English only."
        )
    else: # Default to French
        lang_instruction = (
            "1. FORCE FRENCH : L'utilisateur parle en Français. Réponds en Français uniquement."
        )

    # CRITICAL: System overrides must be at the ABSOLUTE BOTTOM to override everything else
    system_parts.extend([
        "### CRITICAL SYSTEM OVERRIDES (PRIORITY #1) ###",
        lang_instruction,
        "",
        "2. CONCISION ABSOLUE :",
        "   - Rédige des messages ULTRA-COURTS et simples (1 ou 2 phrases maximum, comme un SMS sur WhatsApp).",
        "   - Pose UNE SEULE question à la fois. INTERDICTION ABSOLUE de lister plusieurs questions d'un coup.",
        "",
        "3. PERSONA HUMAIN (ZÉRO SIGNATURE IA) :",
        "   - Tu es Yasmine, une vraie conseillère commerciale humaine de Naps.",
        "   - N'utilise JAMAIS de phrases du style : 'En tant qu'IA', 'En tant qu'assistant de paiement', 'Je suis un modèle de langage', etc.",
        "   - Ne sois pas robotique. Sois chaleureuse et va droit au but.",
        "",
        "4. QUALIFICATION STRICTE (RÈGLE #4 DU PROMPT DE BASE) :",
        "   - Tu as l'INTERDICTION ABSOLUE de donner les tarifs, les prix, les formules ou les commissions (ex: 0 DH, 290 DH, commission 1.98%) tant que tu n'as pas collecté dans l'ordre : la Ville, le Secteur d'activité, et si le prospect possède déjà un TPE.",
        "   - Si l'utilisateur pose une question sur les TPE, les formules ou demande les prix, tu ne dois pas répondre directement avec les détails techniques ou les prix du RAG. Tu DOIS d'abord le qualifier en lui posant la première question de qualification manquante (ex: 'Vous êtes basé dans quelle ville ?' ou sa traduction en Darija).",
        "   - N'affiche pas les informations du RAG (prix, commissions) si l'utilisateur n'est pas qualifié.",
        "---",
        "",
        "### PRIMARY MISSION INSTRUCTIONS",
        custom_prompt,
        "",
        "### ADDITIONAL CONSTRAINTS",
        "SCOPE: Réponds uniquement sur les solutions de paiement Naps (TPE, e-commerce, cartes). Pour tout autre sujet, redirige vers l'offre Naps en restant fidèle au persona Yasmine.",
    ])

    full_system = "\n".join(system_parts)

    messages = [{"role": "system", "content": full_system}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    # 4. Call LLM
    if stream:
        async def _stream_and_save():
            full_answer_list = []
            async for chunk in stream_llm(messages, max_tokens=300):
                full_answer_list.append(chunk)
                yield chunk
            answer = _strip_ai_watermark("".join(full_answer_list))
            await save_history(user_id, "user", message)
            await save_history(user_id, "assistant", answer)
            latency = (time.monotonic() - t_start) * 1000
            await _log_conversation(session, user_id, language, latency, False)
        return _stream_and_save()

    answer = _strip_ai_watermark(await call_llm(messages, max_tokens=300))
    await save_history(user_id, "user", message)
    await save_history(user_id, "assistant", answer)
    latency = (time.monotonic() - t_start) * 1000
    await _log_conversation(session, user_id, language, latency, False)
    return answer
