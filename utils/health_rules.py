"""Transparent educational health rules. These rules never provide a diagnosis."""

from __future__ import annotations

EMERGENCY_KEYWORDS = [
    "chest pain",
    "severe bleeding",
    "unconscious",
    "difficulty breathing",
    "stroke",
    "severe allergic reaction",
    "severe headache",
    "fainting",
    "blue lips",
    "severe burn",
]


def _profile(name, keywords, description, care, diet, lifestyle, avoid, warnings, specialist, department):
    return {
        "name": name,
        "keywords": keywords,
        "description": description,
        "care": care,
        "diet": diet,
        "lifestyle": lifestyle,
        "avoid": avoid,
        "warnings": warnings,
        "specialist": specialist,
        "department": department,
    }


DISEASES = {
    "diabetes": _profile(
        "Diabetes",
        ["glucose", "blood sugar", "hba1c", "insulin", "frequent urination", "thirst"],
        "A metabolic condition involving blood glucose regulation.",
        ["Monitor blood sugar as advised", "Take medicine only as prescribed", "Check slow-healing wounds"],
        ["Choose fiber-rich vegetables, pulses and whole grains", "Limit added sugar and refined carbohydrates"],
        ["Exercise regularly if medically safe", "Keep follow-up records"],
        ["Sugary drinks", "Skipping prescribed treatment"],
        ["Fainting", "Blurred vision", "Very high blood sugar", "Wounds not healing"],
        "Endocrinologist",
        "Endocrinology",
    ),
    "hypertension": _profile(
        "Hypertension",
        ["blood pressure", "high bp", "bp", "headache", "dizziness", "systolic", "diastolic"],
        "Persistently raised blood pressure can affect the heart and blood vessels.",
        ["Monitor blood pressure", "Continue prescribed medicine", "Arrange clinical review"],
        ["Reduce salt", "Choose fresh, minimally processed food"],
        ["Exercise regularly", "Use stress-management techniques"],
        ["Smoking", "High-salt packaged food"],
        ["Chest pain", "Severe headache", "Shortness of breath", "One-sided weakness"],
        "Cardiologist",
        "Cardiology",
    ),
    "asthma": _profile(
        "Asthma",
        ["wheezing", "shortness of breath", "inhaler", "cough", "chest tightness"],
        "An airway condition that may cause episodic breathing symptoms.",
        ["Follow an asthma action plan", "Use inhalers only as directed", "Track triggers"],
        ["Stay hydrated", "Choose balanced meals"],
        ["Keep rooms dust-free", "Carry a prescribed reliever inhaler"],
        ["Smoke", "Known triggers"],
        ["Blue lips", "Unable to speak normally", "Severe breathlessness", "No relief from inhaler"],
        "Pulmonologist",
        "Pulmonology",
    ),
    "kidney": _profile(
        "Kidney disease",
        ["creatinine", "kidney", "renal", "protein urine", "swollen feet", "low egfr"],
        "Kidney-related findings need clinician interpretation and repeat testing.",
        ["Review results with a doctor", "Monitor blood pressure", "Take only prescribed medicines"],
        ["Ask a clinician about salt, protein and fluid needs"],
        ["Attend follow-ups", "Track swelling and urine changes"],
        ["Unsupervised painkillers", "Herbal remedies without review"],
        ["Very low urine", "Severe swelling", "Confusion", "Breathing difficulty"],
        "Nephrologist",
        "Nephrology",
    ),
    "heart": _profile(
        "Heart disease",
        ["chest pain", "cardiac", "ecg", "troponin", "palpitation", "coronary"],
        "Heart-related symptoms can be urgent and require professional evaluation.",
        ["Seek prompt evaluation for new chest symptoms", "Take cardiac medicines only as prescribed"],
        ["Reduce salt and trans fats", "Choose vegetables and whole grains"],
        ["Follow an approved activity plan", "Avoid tobacco"],
        ["Smoking", "Ignoring chest pain"],
        ["Chest pain", "Sweating", "Fainting", "Breathing difficulty"],
        "Cardiologist",
        "Cardiology",
    ),
    "liver": _profile(
        "Liver disease",
        ["bilirubin", "jaundice", "alt", "ast", "fatty liver", "liver"],
        "Abnormal liver findings have many causes and need clinical review.",
        ["Discuss liver tests with a doctor", "Review all medicines and supplements"],
        ["Eat balanced meals", "Follow clinician guidance on fats"],
        ["Maintain a healthy weight", "Attend repeat testing"],
        ["Alcohol", "Unreviewed supplements"],
        ["Confusion", "Vomiting blood", "Severe abdominal swelling", "Deep jaundice"],
        "Gastroenterologist",
        "Gastroenterology",
    ),
    "thyroid": _profile(
        "Thyroid problem",
        ["thyroid", "tsh", "t3", "t4", "thyroxine", "neck swelling"],
        "Thyroid hormones influence energy, heart rate and metabolism.",
        ["Get thyroid tests interpreted clinically", "Take thyroid medicine consistently if prescribed"],
        ["Use a balanced diet", "Do not self-start iodine supplements"],
        ["Track symptoms", "Keep regular tests"],
        ["Changing medicine dose yourself"],
        ["Severe palpitations", "Confusion", "Breathing or swallowing difficulty"],
        "Endocrinologist",
        "Endocrinology",
    ),
    "anemia": _profile(
        "Anemia",
        ["anemia", "anaemia", "hemoglobin", "haemoglobin", "low hb", "iron deficiency", "pale"],
        "Low hemoglobin may have nutritional or other causes.",
        ["Ask about blood tests and the underlying cause", "Use supplements only when advised"],
        ["Choose iron-rich foods with vitamin C"],
        ["Rest as needed", "Attend follow-up testing"],
        ["Tea immediately with iron-rich meals"],
        ["Fainting", "Chest pain", "Severe breathlessness"],
        "General Physician",
        "General Medicine",
    ),
    "skin": _profile(
        "Skin infection",
        ["skin infection", "wound", "pus", "redness", "rash", "swelling"],
        "Skin changes may result from irritation, allergy or infection.",
        ["Keep the area clean and dry", "Avoid scratching", "Seek review if spreading"],
        ["Stay hydrated and eat balanced meals"],
        ["Use fragrance-free products", "Photograph changes for comparison"],
        ["Sharing towels", "Unprescribed steroid creams"],
        ["Rapidly spreading redness", "Fever", "Severe pain", "Face swelling"],
        "Dermatologist",
        "Dermatology",
    ),
    "gastric": _profile(
        "Gastric problem",
        ["acidity", "heartburn", "stomach pain", "gastric", "reflux", "bloating", "indigestion"],
        "Upper digestive symptoms can have dietary, medication or medical causes.",
        ["Eat smaller meals", "Seek review if persistent"],
        ["Choose mild foods and adequate fluids"],
        ["Avoid lying down after meals", "Track triggers"],
        ["Late heavy meals", "Trigger foods", "Unnecessary painkillers"],
        ["Vomiting blood", "Black stool", "Severe abdominal pain"],
        "Gastroenterologist",
        "Gastroenterology",
    ),
    "infection": _profile(
        "Fever/infection",
        ["fever", "infection", "temperature", "cough", "body pain", "chills", "sore throat"],
        "Fever and flu-like symptoms may have several infectious and non-infectious causes.",
        ["Rest and monitor temperature", "Seek review for persistent or worsening fever"],
        ["Drink enough fluids", "Choose light nutritious meals"],
        ["Wash hands", "Limit close contact while febrile"],
        ["Self-starting antibiotics"],
        ["Breathing difficulty", "Confusion", "Dehydration", "Persistent high fever"],
        "General Physician",
        "General Medicine",
    ),
    "migraine": _profile(
        "Migraine",
        ["migraine", "severe headache", "headache", "aura", "vomiting", "light sensitivity"],
        "Recurring headaches may be migraine, but new or severe patterns need assessment.",
        ["Rest in a dark quiet room", "Track headache patterns"],
        ["Maintain regular meals and hydration"],
        ["Keep consistent sleep", "Manage known triggers"],
        ["Excess caffeine", "Frequent unreviewed painkillers"],
        ["Sudden worst headache", "Weakness", "Confusion", "Fever with stiff neck"],
        "Neurologist",
        "Neurology",
    ),
    "allergy": _profile(
        "Allergy",
        ["allergy", "rash", "itching", "hives", "sneezing", "face swelling"],
        "Allergic symptoms may affect skin, nose, eyes or breathing.",
        ["Avoid suspected triggers", "Seek medical advice for persistent symptoms"],
        ["Keep a food/symptom diary if relevant"],
        ["Use gentle skin products", "Note new medicines or products"],
        ["Known triggers", "Scratching"],
        ["Throat tightness", "Face swelling", "Breathing difficulty", "Fainting"],
        "Dermatologist",
        "Dermatology",
    ),
}


def analyze_text(text: str) -> dict:
    clean = " ".join((text or "").lower().split())
    scored = []
    for key, profile in DISEASES.items():
        found = [word for word in profile["keywords"] if word in clean]
        if found:
            scored.append((len(found), key, found))
    scored.sort(reverse=True)
    if not scored:
        key, found, score = "infection", [], 0
    else:
        score, key, found = scored[0]
    confidence = "High" if score >= 4 else "Medium" if score >= 2 else "Low"
    return {
        "key": key,
        "profile": DISEASES[key],
        "keywords": found,
        "confidence": confidence,
        "emergency": any(word in clean for word in EMERGENCY_KEYWORDS),
        "alternatives": [DISEASES[item[1]]["name"] for item in scored[1:3]],
    }
