"""K-12 grade catalogue mapped onto upstream Programs."""

import frappe

GRADE_LEVELS = [
    ("KG 1", "KG", 1),
    ("KG 2", "KG", 2),
    ("Grade 1", "Primary", 3),
    ("Grade 2", "Primary", 4),
    ("Grade 3", "Primary", 5),
    ("Grade 4", "Primary", 6),
    ("Grade 5", "Primary", 7),
    ("Grade 6", "Middle", 8),
    ("Grade 7", "Middle", 9),
    ("Grade 8", "Middle", 10),
    ("Grade 9", "Secondary", 11),
    ("Grade 10", "Secondary", 12),
    ("Grade 11", "Secondary", 13),
    ("Grade 12", "Secondary", 14),
]


def create_default_grade_programs():
    """Create default K-12 grade Programs if they don't already exist.

    Skips existing Programs by name. Returns a list of created Program names.
    """
    created = []
    for name, band, order in GRADE_LEVELS:
        if frappe.db.exists("Program", name):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": name,
                "is_k12_grade": 1,
                "grade_band": band,
                "grade_order": order,
            }
        )
        doc.insert(ignore_permissions=True)
        created.append(name)
    return created
