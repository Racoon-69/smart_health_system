"""Safe rule-based automated health guidance."""

from .health_rules import analyze_text


def bot_reply(message: str) -> str:
    result = analyze_text(message)
    if result["emergency"]:
        return (
            "Your symptoms may require urgent medical attention. Please visit the nearest emergency "
            "department or call local emergency services immediately."
        )
    profile = result["profile"]
    tips = "; ".join(profile["care"][:2])
    return (
        f"Based on the symptoms you described, this may be related to {profile['name']}. "
        f"{tips}. Please monitor your symptoms and consult a doctor if it worsens. "
        "This is an educational suggestion only, not a diagnosis."
    )
