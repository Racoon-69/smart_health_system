"""Transparent educational health rules. These rules never provide a diagnosis."""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

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

_EMERGENCY_EXAMPLES = [
    "chest pain and sweating",
    "severe bleeding that will not stop",
    "the patient is unconscious",
    "difficulty breathing and blue lips",
    "possible stroke with one sided weakness",
    "severe allergic reaction with throat swelling",
    "severe headache with confusion",
    "I am fainting",
    "a severe burn needs urgent help",
    "unable to breathe normally",
]
_NON_EMERGENCY_EXAMPLES = [
    "mild cough for two days",
    "routine blood sugar follow up",
    "occasional heartburn after meals",
    "small itchy rash on my arm",
    "tired after a busy day",
    "mild headache that improves with rest",
    "schedule a regular appointment",
    "slight runny nose",
    "check my medication list",
    "minor muscle ache",
]

_EMERGENCY_SVM = Pipeline(
    [
        ("tfidf", TfidfVectorizer(ngram_range=(1, 3), lowercase=True, sublinear_tf=True)),
        ("classifier", LinearSVC(class_weight="balanced", random_state=42)),
    ]
)
_EMERGENCY_SVM.fit(_EMERGENCY_EXAMPLES + _NON_EMERGENCY_EXAMPLES, [1] * len(_EMERGENCY_EXAMPLES) + [0] * len(_NON_EMERGENCY_EXAMPLES))


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

# Build dataset to train Random Forest Classifier for Disease Prediction
_rf_samples = []
_rf_labels = []

for disease_key, profile in DISEASES.items():
    keywords = profile["keywords"]
    for kw in keywords:
        _rf_samples.append(f"patient has {kw}")
        _rf_samples.append(f"symptoms of {kw} and {keywords[0]}")
        _rf_samples.append(f"feeling {kw} {profile['description']}")
    _rf_samples.append(profile["name"].lower())
    _rf_labels.extend([disease_key] * (len(keywords) * 3 + 1))

_DISEASE_RF_PIPELINE = Pipeline(
    [
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True)),
        ("classifier", RandomForestClassifier(n_estimators=100, random_state=42)),
    ]
)
_DISEASE_RF_PIPELINE.fit(_rf_samples, _rf_labels)


def analyze_text(text: str) -> dict:
    clean = " ".join((text or "").lower().split())
    
    # 1. Random Forest Model Prediction
    rf_probs = _DISEASE_RF_PIPELINE.predict_proba([clean])[0]
    rf_classes = list(_DISEASE_RF_PIPELINE.classes_)
    
    # Keyword overlay for exact term detection
    scored = []
    for key, profile in DISEASES.items():
        found = [word for word in profile["keywords"] if word in clean]
        if found:
            scored.append((len(found), key, found))
    scored.sort(reverse=True)
    
    # Top predicted class from Random Forest
    rf_top_idx = int(rf_probs.argmax())
    rf_top_key = rf_classes[rf_top_idx]
    rf_top_prob = float(rf_probs[rf_top_idx])
    
    # If explicit keywords found, align primary prediction, else use Random Forest predicted key
    if scored:
        key = scored[0][1]
        found = scored[0][2]
    else:
        key = rf_top_key if clean else "infection"
        found = []
        
    # Order candidate alternatives using Random Forest probabilities
    prob_class_pairs = sorted(zip(rf_probs, rf_classes), reverse=True)
    alt_keys = [c for _, c in prob_class_pairs if c != key][:2]

    confidence = "High" if (len(found) >= 4 or rf_top_prob > 0.4) else "Medium" if (len(found) >= 2 or rf_top_prob > 0.2) else "Low"
    svm_emergency = bool(_EMERGENCY_SVM.predict([clean])[0])
    svm_score = float(_EMERGENCY_SVM.decision_function([clean])[0])
    
    return {
        "key": key,
        "profile": DISEASES[key],
        "keywords": found,
        "confidence": confidence,
        "emergency": svm_emergency,
        "emergency_score": round(svm_score, 4),
        "alternatives": [DISEASES[alt_key]["name"] for alt_key in alt_keys if alt_key in DISEASES],
        "model_used": "Random Forest Classifier",
        "rf_probability": round(rf_top_prob, 4),
    }
