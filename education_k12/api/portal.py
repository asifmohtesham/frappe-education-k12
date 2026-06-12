"""Whitelisted portal endpoints.

Authorization model: the session user is mapped to a Guardian (via
Guardian.user) or an Instructor (via the Instructor.user custom field).
Every endpoint authorizes per record — a guardian can only read their own
children; a teacher only their own homerooms. Data reads use frappe.db
directly (bypassing role permissions) AFTER the explicit ownership check.
"""

import frappe
from frappe import _


def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.PermissionError)


def _guardian():
    _require_login()
    name = frappe.db.get_value("Guardian", {"user": frappe.session.user})
    if not name:
        frappe.throw(_("Not registered as a guardian"), frappe.PermissionError)
    return name


def _instructor():
    _require_login()
    name = frappe.db.get_value("Instructor", {"user": frappe.session.user})
    if not name:
        frappe.throw(_("Not registered as an instructor"), frappe.PermissionError)
    return name


def _children_of(guardian):
    return frappe.get_all(
        "Student Guardian",
        filters={"guardian": guardian, "parenttype": "Student"},
        pluck="parent",
    )


@frappe.whitelist()
def get_portal_context():
    _require_login()
    user = frappe.session.user
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name"),
        "is_teacher": bool(frappe.db.get_value("Instructor", {"user": user})),
        "is_guardian": bool(frappe.db.get_value("Guardian", {"user": user})),
    }


@frappe.whitelist()
def get_children():
    guardian = _guardian()
    students = frappe.get_all(
        "Student",
        filters={"name": ("in", _children_of(guardian)), "enabled": 1},
        fields=["name", "student_name", "image", "date_of_birth"],
        order_by="student_name asc",
    )
    for student in students:
        student["enrollment"] = _current_enrollment(student["name"])
    return students


def _current_enrollment(student):
    rows = frappe.get_all(
        "Program Enrollment",
        filters={"student": student, "docstatus": 1},
        fields=["program", "academic_year"],
        order_by="enrollment_date desc",
        limit=1,
    )
    return rows[0] if rows else None


@frappe.whitelist()
def get_child_profile(student):
    guardian = _guardian()
    if student not in _children_of(guardian):
        frappe.throw(_("Not your child"), frappe.PermissionError)
    profile = frappe.db.get_value(
        "Student",
        student,
        [
            "name",
            "student_name",
            "image",
            "date_of_birth",
            "nationality",
            "blood_group",
            "medical_conditions",
            "emergency_contact_name",
            "emergency_contact_phone",
        ],
        as_dict=True,
    )
    profile["enrollment"] = _current_enrollment(student)
    profile["homeroom"] = frappe.db.get_value(
        "Student Group Student",
        {"student": student, "parenttype": "Student Group", "active": 1},
        "parent",
    )
    profile["transport"] = _transport_for(student)
    return profile


def _transport_for(student):
    rows = frappe.get_all(
        "K12 Transport Assignment",
        filters={"student": student, "active": 1},
        fields=["route", "stop_name", "direction"],
        order_by="creation desc",
        limit=1,
    )
    assignment = rows[0] if rows else None
    if not assignment:
        return None
    stop = (
        frappe.db.get_value(
            "K12 Route Stop",
            {
                "parent": assignment.route,
                "parenttype": "K12 Transport Route",
                "stop_name": assignment.stop_name,
            },
            ["pickup_time", "drop_time"],
            as_dict=True,
        )
        or frappe._dict()
    )
    return {
        "route": assignment.route,
        "stop": assignment.stop_name,
        "direction": assignment.direction,
        "pickup_time": str(stop.pickup_time) if stop.get("pickup_time") else None,
        "drop_time": str(stop.drop_time) if stop.get("drop_time") else None,
    }


@frappe.whitelist()
def get_homerooms():
    instructor = _instructor()
    return frappe.get_all(
        "Student Group",
        filters={"homeroom_teacher": instructor, "is_homeroom": 1, "disabled": 0},
        fields=["name", "student_group_name", "program", "batch", "academic_year"],
        order_by="student_group_name asc",
    )


@frappe.whitelist()
def get_homeroom_roster(student_group):
    instructor = _instructor()
    group = frappe.db.get_value(
        "Student Group",
        student_group,
        ["name", "student_group_name", "homeroom_teacher", "is_homeroom", "program"],
        as_dict=True,
    )
    if not group or not group.is_homeroom or group.homeroom_teacher != instructor:
        frappe.throw(_("Not your homeroom"), frappe.PermissionError)
    students = frappe.get_all(
        "Student Group Student",
        filters={"parent": student_group, "parenttype": "Student Group", "active": 1},
        fields=["student", "student_name", "group_roll_number"],
        order_by="group_roll_number asc",
    )
    return {"group": group, "students": students}
