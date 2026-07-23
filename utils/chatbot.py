"""Real-time Intelligent AI Chatbot module with LLM Integration and Generative Health Reasoning."""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.parse
from .health_rules import analyze_text, EMERGENCY_KEYWORDS, DISEASES

# NLP Intent RegEx Patterns
GREETING_RE = re.compile(r"\b(hi|hello|hey|greetings|good morning|good afternoon|good evening|namaste)\b", re.IGNORECASE)
HELP_RE = re.compile(r"\b(help|support|info|what can you do|features|guide)\b", re.IGNORECASE)
FEVER_RE = re.compile(r"\b(fever|temperature|chills|cold|flu|infection|cough)\b", re.IGNORECASE)
PAIN_RE = re.compile(r"\b(pain|ache|sore|hurt|burning|discomfort)\b", re.IGNORECASE)
DIET_RE = re.compile(r"\b(diet|food|eat|nutrition|drink|avoid)\b", re.IGNORECASE)


def _call_gemini_api(prompt: str, api_key: str) -> str | None:
    """Call Google Gemini REST API directly for real-time generative AI responses."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "You are an intelligent, empathetic medical AI assistant for Smart Health System. "
                                "Provide clear, accurate, multi-paragraph educational health responses. "
                                "Include symptom guidance, lifestyle tips, when to see a doctor, and emergency warnings if needed. "
                                f"User query: {prompt}"
                            )
                        }
                    ]
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception as exc:
        print(f"Gemini API Call Exception: {exc}")
    return None


def bot_reply(message: str) -> str:
    """Real-time intelligent AI response generator for general health questions and symptoms."""
    text = (message or "").strip()
    if not text:
        return "Please describe your health query or symptoms so I can assist you."

    # 1. Try real-time LLM API if key is set in environment
    api_key = (
        os.getenv("ANTIGRAVITY_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if api_key:
        llm_response = _call_gemini_api(text, api_key)
        if llm_response:
            return llm_response

    # 2. Greeting Handling
    if GREETING_RE.search(text) and len(text.split()) <= 4:
        return (
            "Hello! I am your Smart Health Assistant. I am here to help you understand your symptoms, "
            "review hospital reports, and suggest lifestyle recommendations.\n\n"
            "How are you feeling today? Please describe any symptoms or questions you have."
        )

    # 3. Help Inquiry
    if HELP_RE.search(text) and len(text.split()) <= 4:
        return (
            "I am equipped to provide comprehensive health guidance!\n\n"
            "• Symptom Analysis & Risk Evaluation\n"
            "• Medical Report & Lab Result Summaries\n"
            "• Diet, Exercise & Care Recommendations\n"
            "• Specialist & Hospital Matching\n\n"
            "Feel free to type your health concern or upload a medical document."
        )

    # 4. Perform Advanced Health Analysis
    analysis = analyze_text(text)
    profile = analysis["profile"]
    matched_keywords = analysis["keywords"]
    confidence = analysis["confidence"]
    model_name = "Antigravity AI Engine (" + analysis.get("model_used", "Random Forest Classifier") + ")"

    # Emergency check
    if analysis["emergency"]:
        return (
            "🚨 URGENT HEALTH SAFETY ALERT 🚨\n\n"
            f"Your message contains symptoms that suggest a potential medical emergency requiring urgent medical attention (Emergency Score: {analysis['emergency_score']}).\n\n"
            "Immediate Actions Required:\n"
            "1. Do not wait for an online reply.\n"
            "2. Contact local emergency medical services or visit the nearest hospital emergency room immediately.\n"
            "3. If you are experiencing chest pain, severe shortness of breath, sudden numbness, or heavy bleeding, seek emergency care right away."
        )

    # Build rich conversational response
    matched_str = ", ".join(matched_keywords) if matched_keywords else "reported health symptoms"
    care_steps = "\n".join([f"  • {item}" for item in profile["care"]])
    diet_steps = "\n".join([f"  • {item}" for item in profile["diet"]])
    warnings = "\n".join([f"  • {item}" for item in profile["warnings"]])

    response = (
        f"✨ {model_name} · Confidence: {confidence}\n\n"
        f"Based on your query regarding '{matched_str}', the symptoms align closely with {profile['name']}.\n\n"
        f"📋 Overview:\n{profile['description']}\n\n"
        f"💊 Recommended Care & Next Steps:\n{care_steps}\n\n"
        f"🥗 Dietary & Lifestyle Advice:\n{diet_steps}\n\n"
        f"⚠️ Warning Signs to Watch For:\n{warnings}\n\n"
        f"🏥 Recommended Specialist: {profile['specialist']} ({profile['department']} department).\n\n"
        "This is educational feedback for support. Please consult a qualified clinician for formal diagnosis and treatment."
    )
    return response


def report_chat_reply(report_text: str, question: str) -> str:
    """Real-time intelligent AI feedback on uploaded medical report documents."""
    combined = f"{report_text}\n{question}"
    
    # 1. Try real-time LLM API if key is set in environment
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    if gemini_key:
        prompt = f"Medical Report Extracted Text:\n{report_text}\n\nUser Question: {question}"
        llm_response = _call_gemini_api(prompt, gemini_key)
        if llm_response:
            return llm_response

    # 2. Perform Advanced Analysis
    analysis = analyze_text(combined)
    profile = analysis["profile"]
    keywords = analysis["keywords"]

    if analysis["emergency"]:
        return (
            "🚨 CRITICAL REPORT ALERT 🚨\n\n"
            "The uploaded medical document contains parameters indicating a critical health risk requiring urgent medical attention.\n"
            "Please seek immediate medical evaluation at an emergency care center or hospital."
        )

    matched_str = ", ".join(keywords[:6]) if keywords else "general diagnostic metrics"
    care_summary = "; ".join(profile["care"][:2])

    return (
        f"📑 Medical Report AI Synthesis\n\n"
        f"I have reviewed the uploaded document alongside your query: \"{question}\".\n\n"
        f"• Identified Diagnostic Terms: {matched_str}\n"
        f"• Primary Health Association: {profile['name']}\n\n"
        f"💡 Key Insights & Next Steps:\n"
        f"1. The report text reflects findings consistent with {profile['description']}.\n"
        f"2. Practical guidance: {care_summary}.\n"
        f"3. We recommend scheduling a follow-up consultation with a {profile['specialist']} to review reference ranges and personalized medical history.\n\n"
        "This is educational feedback for support. AI analysis explains medical terms and reference findings; it does not replace professional clinical diagnosis."
    )
