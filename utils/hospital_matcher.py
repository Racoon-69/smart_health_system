"""Compatibility wrappers around normalized hospital/doctor query services."""

from healthcare.services import doctor_search, hospital_search


def matching_hospitals(term: str = "", city: str = ""):
    return hospital_search(term, city)


def matching_doctors(specialty: str = "", hospital_id: str = ""):
    return doctor_search(specialty, int(hospital_id) if str(hospital_id).isdigit() else None)
