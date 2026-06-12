import frappe


def ensure_academic_year(name="2026-27", start="2026-09-01", end="2027-06-30"):
    if frappe.db.exists("Academic Year", name):
        return name
    return (
        frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": name,
                "year_start_date": start,
                "year_end_date": end,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_student(first_name, **extra):
    existing = frappe.db.get_value("Student", {"first_name": first_name})
    if existing:
        return existing
    doc = frappe.get_doc(
        {
            "doctype": "Student",
            "first_name": first_name,
            "student_email_id": f"{first_name.lower().replace(' ', '.')}@test.k12.local",
            **extra,
        }
    )
    return doc.insert(ignore_permissions=True).name
