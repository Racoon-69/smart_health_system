"""Basic pixel observations for educational photo support."""

from PIL import Image, ImageFilter, ImageStat


def analyze_photo(path) -> dict:
    image = Image.open(path).convert("RGB")
    image.thumbnail((700, 700))
    pixels = list(image.getdata())
    total = max(len(pixels), 1)
    redness = sum(r > 110 and r > g * 1.25 and r > b * 1.18 for r, g, b in pixels) / total * 100
    dark = sum((r + g + b) / 3 < 55 for r, g, b in pixels) / total * 100
    gray = image.convert("L")
    contrast = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
    brightness = ImageStat.Stat(gray).mean[0]
    if redness > 22 and contrast > 25:
        condition = "Wound/infection possibility"
    elif redness > 12:
        condition = "Skin irritation / rash / allergy"
    elif dark > 18:
        condition = "Bruise/dark spot"
    else:
        condition = "Normal/unclear"
    observations = [
        f"Estimated reddish area: {redness:.1f}%",
        f"Estimated dark area: {dark:.1f}%",
        f"Average brightness: {brightness:.0f}/255",
        f"Edge contrast indicator: {contrast:.1f}",
    ]
    if brightness < 45 or brightness > 220:
        observations.append("Lighting may reduce the reliability of this simple visual check.")
    return {
        "condition": condition,
        "observations": observations,
        "redness": round(redness, 1),
        "dark_spots": round(dark, 1),
        "recommendation": "Keep the area clean, avoid scratching or unprescribed creams, and monitor for change.",
        "warnings": ["Spreading redness", "Pus or fever", "Severe pain", "Rapid swelling", "Breathing difficulty"],
        "specialist": "Dermatologist",
        "department": "Dermatology",
    }
