"""Simple NLP Chatbot module for automated health guidance and intent processing."""

import re
from .health_rules import analyze_text

# Simple NLP Intent Patterns
GREETING_RE = re.compile(r"\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b", re.IGNORECASE)
HELP_RE = re.compile(r"\b(help|support|info|what can you do|features|guide)\b", re.IGNORECASE)


def bot_reply(message: str) -> str:
    """Simple NLP Chatbot intent classification and response generator."""
    text = (message or "").strip()
    if not text:
        return "Please type a symptom or health query so I can assist you."

    # 1. NLP Intent Recognition: Greeting & General Inquiry
    if GREETING_RE.search(text) and len(text.split()) <= 4:
        return (
            "Hello! I am your Smart Health Assistant. Describe any symptoms you are experiencing "
            "(e.g., fever, headache, high blood pressure) and I will provide educational guidance."
        )
    if HELP_RE.search(text) and len(text.split()) <= 4:
        return (
            "I can assist with symptom analysis, educational health information, report feedback, "
            "and hospital recommendations. Please describe your symptoms or ask a medical question."
        )

    # 2. NLP Health Analysis (TF-IDF + LinearSVC + Random Forest NLP model)
    result = analyze_text(text)
    if result["emergency"]:
        return (
            "URGENT NOTICE: Your description contains symptoms that may require urgent medical attention. "
            "Please visit the nearest emergency department or call local emergency services immediately."
        )

    profile = result["profile"]
    matched = ", ".join(result["keywords"]) if result["keywords"] else "general health symptoms"
    tips = "; ".join(profile["care"][:2])
    model = result.get("model_used", "Random Forest NLP Model")
    confidence = result.get("confidence", "Medium")

    return (
        f"NLP Analysis ({model}, {confidence} Confidence): Based on the terms '{matched}', "
        f"your query relates to {profile['name']}. {tips}. "
        f"Please monitor your health and consult a physician if symptoms persist or worsen. "
        "This is educational feedback, not a medical diagnosis."
    )


def report_chat_reply(report_text: str, question: str) -> str:
    """Give conservative, readable educational feedback on extracted report text using Simple NLP."""
    combined = f"{report_text}\n{question}"
    result = analyze_text(combined)
    profile = result["profile"]
    matched = ", ".join(result["keywords"][:6]) or "no supported health keywords"

    if result["emergency"]:
        return (
            "The uploaded report or question contains a possible urgent warning sign. Please contact local "
            "emergency services or go to the nearest emergency department now. An AI cannot safely interpret "
            "an urgent result."
        )

    return (
        f"I found these relevant terms in the report: {matched}. They may relate to {profile['name']}. "
        f"For your question, \"{question}\", a useful next step is to review the original values, reference "
        f"ranges, symptoms, and medical history with a licensed clinician. {'; '.join(profile['care'][:2])}. "
        "This is educational feedback, not a medical diagnosis or a doctor's opinion."
    )
