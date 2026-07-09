"""Compatibility exports for the transactional slot service."""

from datetime import date

from healthcare.services import slot_details


def check_slot(hospital_id: int, doctor_id: int, selected_date: str, time: str) -> dict:
    slots = slot_details(hospital_id, doctor_id, date.fromisoformat(selected_date))
    item = next(slot for slot in slots if slot["time"] == time)
    return {
        "booked": item["booked"],
        "remaining": item["remaining"],
        "full": item["full"],
        "state": "Full" if item["full"] else "Empty" if item["booked"] == 0 else "Available",
    }
