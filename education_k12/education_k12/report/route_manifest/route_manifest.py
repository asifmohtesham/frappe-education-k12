import frappe
from frappe import _

from education_k12.k12_transport.manifest import get_route_manifest


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": _("Stop"), "fieldname": "stop_name", "fieldtype": "Data", "width": 180},
        {"label": _("Pickup"), "fieldname": "pickup_time", "fieldtype": "Data", "width": 100},
        {"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 160},
        {"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 200},
        {"label": _("Direction"), "fieldname": "direction", "fieldtype": "Data", "width": 110},
    ]
    if not (filters.get("route") and filters.get("academic_year")):
        return columns, []

    manifest = get_route_manifest(filters["route"], filters["academic_year"])
    rows = []
    for stop in manifest["stops"]:
        for student in stop["students"]:
            rows.append(
                {
                    "stop_name": stop["stop_name"],
                    "pickup_time": str(stop["pickup_time"] or ""),
                    "student": student.student,
                    "student_name": student.student_name,
                    "direction": student.direction,
                }
            )
    return columns, rows
