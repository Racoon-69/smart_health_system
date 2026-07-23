"""First-Come, First-Served (FCFS) Scheduling utility for appointment bookings."""

from datetime import date
from healthcare.services import slot_details


def check_slot(hospital_id: int, doctor_id: int, selected_date: str, time: str) -> dict:
    """Check appointment slot capacity under FCFS (First-Come, First-Served) scheduling rules."""
    slots = slot_details(hospital_id, doctor_id, date.fromisoformat(selected_date))
    item = next(slot for slot in slots if slot["time"] == time)
    return {
        "booked": item["booked"],
        "remaining": item["remaining"],
        "full": item["full"],
        "state": "Full" if item["full"] else "Empty" if item["booked"] == 0 else "Available",
        "scheduling_algorithm": "First-Come, First-Served (FCFS)",
    }


def fcfs_schedule_summary(hospital_id: int, doctor_id: int, selected_date: str) -> list[dict]:
    """Retrieve all slots ordered for FCFS scheduling processing."""
    slots = slot_details(hospital_id, doctor_id, date.fromisoformat(selected_date))
    for s in slots:
        s["algorithm"] = "FCFS"
    return slots
