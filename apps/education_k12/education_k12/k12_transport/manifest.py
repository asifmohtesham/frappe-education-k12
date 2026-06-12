"""Printable route manifests: who boards where, per route and year."""

import frappe


def get_route_manifest(route, academic_year):
    route_doc = frappe.get_doc("K12 Transport Route", route)
    vehicle = frappe.db.get_value(
        "K12 Vehicle",
        route_doc.vehicle,
        ["vehicle_number", "capacity", "driver", "attendant"],
        as_dict=True,
    )
    vehicle["driver_name"] = (
        frappe.db.get_value("K12 Transport Staff", vehicle.driver, "staff_name")
        if vehicle.driver
        else None
    )
    vehicle["attendant_name"] = (
        frappe.db.get_value("K12 Transport Staff", vehicle.attendant, "staff_name")
        if vehicle.attendant
        else None
    )

    assignments = frappe.get_all(
        "K12 Transport Assignment",
        filters={"route": route, "academic_year": academic_year, "active": 1},
        fields=["student", "student_name", "stop_name", "direction"],
        order_by="student_name asc",
    )
    by_stop = {}
    for assignment in assignments:
        by_stop.setdefault(assignment.stop_name, []).append(assignment)

    stops = [
        {
            "stop_name": stop.stop_name,
            "sequence": stop.sequence,
            "pickup_time": stop.pickup_time,
            "drop_time": stop.drop_time,
            "students": by_stop.get(stop.stop_name, []),
        }
        for stop in sorted(route_doc.stops, key=lambda s: s.sequence)
    ]

    return {
        "route": route_doc.name,
        "academic_year": academic_year,
        "vehicle": vehicle,
        "stops": stops,
    }
