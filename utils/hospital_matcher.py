"""Content-Based Filtering recommendation engine for hospitals and doctors."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from healthcare.services import doctor_search, hospital_search


def recommend_hospitals_content_based(term: str = "", city: str = ""):
    """Recommend hospitals using Content-Based Filtering (TF-IDF + Cosine Similarity)."""
    hospitals = hospital_search("", city)
    if not hospitals or not term.strip():
        return hospital_search(term, city)

    # Construct content profile text for each hospital
    content_corpus = []
    for h in hospitals:
        dept_names = " ".join(d.name for d in getattr(h, "departments_rel", []))
        cond_names = " ".join(c.name for c in getattr(h, "conditions_rel", []))
        text = f"{h.name} {h.city} {dept_names} {cond_names}".lower()
        content_corpus.append(text)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(content_corpus)
        query_vec = vectorizer.transform([term.lower()])
        sim_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

        # Combine content similarity score with rating for hybrid ranking
        scored = []
        for idx, score in enumerate(sim_scores):
            rating_boost = (hospitals[idx].rating or 0.0) / 10.0
            total_score = score + rating_boost
            scored.append((total_score, hospitals[idx]))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [h for score, h in scored if score > 0 or not term]
    except Exception:
        return hospital_search(term, city)


def recommend_doctors_content_based(specialty: str = "", hospital_id: str = ""):
    """Recommend doctors using Content-Based Filtering (TF-IDF + Cosine Similarity)."""
    h_id = int(hospital_id) if str(hospital_id).isdigit() else None
    doctors = doctor_search("", h_id)
    if not doctors or not specialty.strip():
        return doctor_search(specialty, h_id)

    content_corpus = []
    for doc in doctors:
        dept = doc.department.name if doc.department else ""
        bio = doc.bio or ""
        text = f"{doc.display_name} {dept} {bio}".lower()
        content_corpus.append(text)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(content_corpus)
        query_vec = vectorizer.transform([specialty.lower()])
        sim_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

        scored = []
        for idx, score in enumerate(sim_scores):
            rating_boost = (doctors[idx].rating or 0.0) / 10.0
            total_score = score + rating_boost
            scored.append((total_score, doctors[idx]))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [d for score, d in scored]
    except Exception:
        return doctor_search(specialty, h_id)


def matching_hospitals(term: str = "", city: str = ""):
    return recommend_hospitals_content_based(term, city)


def matching_doctors(specialty: str = "", hospital_id: str = ""):
    return recommend_doctors_content_based(specialty, hospital_id)
