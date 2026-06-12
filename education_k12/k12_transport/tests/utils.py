import frappe


def ensure_staff(name, role="Driver"):
    existing = frappe.db.get_value(
        "K12 Transport Staff", {"staff_name": name, "role": role}
    )
    if existing:
        return existing
    return (
        frappe.get_doc(
            {"doctype": "K12 Transport Staff", "staff_name": name, "role": role}
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_vehicle(vehicle_number, capacity=4, **extra):
    if frappe.db.exists("K12 Vehicle", vehicle_number):
        return vehicle_number
    return (
        frappe.get_doc(
            {
                "doctype": "K12 Vehicle",
                "vehicle_number": vehicle_number,
                "capacity": capacity,
                **extra,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_route(route_name, vehicle, stops=None, **extra):
    if frappe.db.exists("K12 Transport Route", route_name):
        return route_name
    doc = frappe.get_doc(
        {
            "doctype": "K12 Transport Route",
            "route_name": route_name,
            "vehicle": vehicle,
            **extra,
        }
    )
    for index, stop in enumerate(stops or [("Main Gate", "07:00:00")], start=1):
        stop_name, pickup_time = stop
        doc.append(
            "stops",
            {"stop_name": stop_name, "sequence": index, "pickup_time": pickup_time},
        )
    return doc.insert(ignore_permissions=True).name
