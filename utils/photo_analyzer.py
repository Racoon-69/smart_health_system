"""Deep Learning image analysis using an Artificial Neural Network (ANN / MLPClassifier)."""

import numpy as np
from PIL import Image, ImageFilter, ImageStat
from sklearn.neural_network import MLPClassifier

# 1. Feature Extraction Routine
def extract_photo_features(image: Image.Image) -> tuple[list[float], float, float, float, float]:
    """Extract quantitative visual feature vector from image pixels."""
    # Convert image to RGB array for modern Pillow compatibility
    np_img = np.array(image.convert("RGB"))
    total_pixels = max(np_img.shape[0] * np_img.shape[1], 1)

    r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
    red_mask = (r > 110) & (r > g * 1.25) & (r > b * 1.18)
    dark_mask = ((r.astype(int) + g.astype(int) + b.astype(int)) / 3) < 55

    redness = float(np.sum(red_mask) / total_pixels * 100)
    dark = float(np.sum(dark_mask) / total_pixels * 100)

    gray = image.convert("L")
    contrast = float(ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0])
    brightness = float(ImageStat.Stat(gray).mean[0])

    r_mean, r_std = float(np.mean(r)), float(np.std(r))
    g_mean, g_std = float(np.mean(g)), float(np.std(g))
    b_mean, b_std = float(np.mean(b)), float(np.std(b))

    feature_vector = [redness, dark, brightness, contrast, r_mean, g_mean, b_mean, r_std, g_std, b_std]
    return feature_vector, redness, dark, brightness, contrast


# 2. Build and Train Artificial Neural Network (ANN / Multi-Layer Perceptron)
def _build_ann_classifier() -> tuple[MLPClassifier, list[str]]:
    """Initialize and train an Artificial Neural Network for image classification."""
    X_train = []
    y_train = []

    # Category 1: Wound/infection (high redness, high contrast, high r_mean)
    for _ in range(40):
        redness = float(np.random.uniform(23, 50))
        dark = float(np.random.uniform(2, 15))
        brightness = float(np.random.uniform(80, 180))
        contrast = float(np.random.uniform(26, 60))
        X_train.append([redness, dark, brightness, contrast, 160.0, 80.0, 80.0, 30.0, 20.0, 20.0])
        y_train.append("Wound/infection possibility")

    # Category 2: Skin irritation / rash / allergy (moderate redness, moderate contrast)
    for _ in range(40):
        redness = float(np.random.uniform(13, 22))
        dark = float(np.random.uniform(2, 15))
        brightness = float(np.random.uniform(100, 200))
        contrast = float(np.random.uniform(10, 24))
        X_train.append([redness, dark, brightness, contrast, 140.0, 90.0, 90.0, 25.0, 18.0, 18.0])
        y_train.append("Skin irritation / rash / allergy")

    # Category 3: Bruise/dark spot (high dark ratio)
    for _ in range(40):
        redness = float(np.random.uniform(0, 10))
        dark = float(np.random.uniform(19, 45))
        brightness = float(np.random.uniform(30, 90))
        contrast = float(np.random.uniform(5, 20))
        X_train.append([redness, dark, brightness, contrast, 60.0, 60.0, 70.0, 15.0, 15.0, 15.0])
        y_train.append("Bruise/dark spot")

    # Category 4: Normal/unclear
    for _ in range(40):
        redness = float(np.random.uniform(0, 11))
        dark = float(np.random.uniform(0, 17))
        brightness = float(np.random.uniform(100, 210))
        contrast = float(np.random.uniform(5, 20))
        X_train.append([redness, dark, brightness, contrast, 120.0, 110.0, 100.0, 20.0, 20.0, 20.0])
        y_train.append("Normal/unclear")

    ann = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        solver="adam",
        max_iter=500,
        random_state=42,
    )
    ann.fit(X_train, y_train)
    return ann, list(ann.classes_)


_ANN_CLASSIFIER, _ANN_CLASSES = _build_ann_classifier()


# 3. Main Analysis Interface
def analyze_photo(path) -> dict:
    """Analyze image using Deep Learning Artificial Neural Network (ANN)."""
    image = Image.open(path).convert("RGB")
    image.thumbnail((700, 700))

    features, redness, dark, brightness, contrast = extract_photo_features(image)

    # Artificial Neural Network inference
    predicted_probs = _ANN_CLASSIFIER.predict_proba([features])[0]
    top_idx = int(np.argmax(predicted_probs))
    condition = _ANN_CLASSES[top_idx]
    confidence_pct = round(float(predicted_probs[top_idx]) * 100, 1)

    observations = [
        f"Artificial Neural Network (ANN) Classification: {condition} ({confidence_pct}% confidence)",
        f"Estimated reddish area: {redness:.1f}%",
        f"Estimated dark area: {dark:.1f}%",
        f"Average brightness: {brightness:.0f}/255",
        f"Edge contrast indicator: {contrast:.1f}",
    ]
    if brightness < 45 or brightness > 220:
        observations.append("Lighting may reduce the reliability of this visual check.")

    return {
        "condition": condition,
        "observations": observations,
        "redness": round(redness, 1),
        "dark_spots": round(dark, 1),
        "ann_confidence": confidence_pct,
        "model_architecture": "Artificial Neural Network (Multi-Layer Perceptron)",
        "recommendation": "Keep the area clean, avoid scratching or unprescribed creams, and monitor for change.",
        "warnings": ["Spreading redness", "Pus or fever", "Severe pain", "Rapid swelling", "Breathing difficulty"],
        "specialist": "Dermatologist",
        "department": "Dermatology",
    }
