import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.api import portal
from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student


def ensure_user(email, first_name, roles=()):
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "send_welcome_email": 0,
                "roles": [{"role": r} for r in roles],
            }
        ).insert(ignore_permissions=True)
    return email


def ensure_guardian(name, user_email):
    existing = frappe.db.get_value("Guardian", {"user": user_email})
    if existing:
        return existing
    return (
        frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_name": name,
                "email_address": user_email,
                "user": user_email,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def link_guardian_to_student(student, guardian):
    doc = frappe.get_doc("Student", student)
    if guardian not in [g.guardian for g in doc.guardians]:
        doc.append("guardians", {"guardian": guardian, "relation": "Father"})
        doc.save(ignore_permissions=True)


def ensure_teacher(name, user_email):
    existing = frappe.db.get_value("Instructor", {"user": user_email})
    if existing:
        return existing
    return (
        frappe.get_doc(
            {"doctype": "Instructor", "instructor_name": name, "user": user_email}
        )
        .insert(ignore_permissions=True)
        .name
    )


def make_homeroom(name, teacher, students=()):
    group = frappe.get_doc(
        {
            "doctype": "Student Group",
            "student_group_name": name,
            "academic_year": ensure_academic_year(),
            "group_based_on": "Activity",
            "is_homeroom": 1,
            "homeroom_teacher": teacher,
        }
    )
    for index, student in enumerate(students, start=1):
        group.append(
            "students", {"student": student, "group_roll_number": index, "active": 1}
        )
    group.insert(ignore_permissions=True)
    return group.name


class TestPortalAPI(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_guardian_sees_only_own_children(self):
        child_a = ensure_student("Portal Child A")
        child_b = ensure_student("Portal Child B")
        user_a = ensure_user("parent.a@test.k12.local", "Parent A", roles=("Guardian",))
        user_b = ensure_user("parent.b@test.k12.local", "Parent B", roles=("Guardian",))
        link_guardian_to_student(child_a, ensure_guardian("Parent A", user_a))
        link_guardian_to_student(child_b, ensure_guardian("Parent B", user_b))

        frappe.set_user(user_a)
        children = portal.get_children()
        names = [c["name"] for c in children]
        self.assertIn(child_a, names)
        self.assertNotIn(child_b, names)

    def test_guardian_cannot_read_other_child_profile(self):
        child_b = ensure_student("Portal Child B2")
        user_a = ensure_user("parent.a2@test.k12.local", "Parent A2", roles=("Guardian",))
        user_b = ensure_user("parent.b2@test.k12.local", "Parent B2", roles=("Guardian",))
        ensure_guardian("Parent A2", user_a)
        link_guardian_to_student(child_b, ensure_guardian("Parent B2", user_b))

        frappe.set_user(user_a)
        with self.assertRaises(frappe.PermissionError):
            portal.get_child_profile(child_b)

    def test_teacher_sees_only_own_homerooms(self):
        s1 = ensure_student("Roster Kid One")
        t1_user = ensure_user("teacher.one@test.k12.local", "Teacher One")
        t2_user = ensure_user("teacher.two@test.k12.local", "Teacher Two")
        t1 = ensure_teacher("Teacher One", t1_user)
        t2 = ensure_teacher("Teacher Two", t2_user)
        own = make_homeroom("HR Own 1", t1, students=(s1,))
        other = make_homeroom("HR Other 1", t2)

        frappe.set_user(t1_user)
        homerooms = [g["name"] for g in portal.get_homerooms()]
        self.assertIn(own, homerooms)
        self.assertNotIn(other, homerooms)

        roster = portal.get_homeroom_roster(own)
        self.assertIn(s1, [r["student"] for r in roster["students"]])

        with self.assertRaises(frappe.PermissionError):
            portal.get_homeroom_roster(other)

    def test_context_reports_role(self):
        t_user = ensure_user("teacher.ctx@test.k12.local", "Teacher Ctx")
        ensure_teacher("Teacher Ctx", t_user)
        frappe.set_user(t_user)
        context = portal.get_portal_context()
        self.assertTrue(context["is_teacher"])
        self.assertFalse(context["is_guardian"])

    def test_guest_is_rejected(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            portal.get_portal_context()

    def test_cross_role_calls_are_rejected(self):
        g_user = ensure_user("only.parent@test.k12.local", "Only Parent", roles=("Guardian",))
        ensure_guardian("Only Parent", g_user)
        t_user = ensure_user("only.teacher@test.k12.local", "Only Teacher")
        ensure_teacher("Only Teacher", t_user)

        frappe.set_user(g_user)
        with self.assertRaises(frappe.PermissionError):
            portal.get_homerooms()
        with self.assertRaises(frappe.PermissionError):
            portal.get_homeroom_roster("HR Own 1")

        frappe.set_user(t_user)
        with self.assertRaises(frappe.PermissionError):
            portal.get_children()
        with self.assertRaises(frappe.PermissionError):
            portal.get_child_profile("STU-0001")

    def test_guest_is_rejected_on_every_endpoint(self):
        frappe.set_user("Guest")
        for call in (
            portal.get_portal_context,
            portal.get_children,
            portal.get_homerooms,
        ):
            with self.assertRaises(frappe.PermissionError):
                call()
        with self.assertRaises(frappe.PermissionError):
            portal.get_child_profile("STU-0001")
        with self.assertRaises(frappe.PermissionError):
            portal.get_homeroom_roster("HR Own 1")

    def test_child_profile_includes_transport(self):
        from education_k12.k12_transport.tests.utils import ensure_route, ensure_vehicle

        child = ensure_student("Portal Bus Child")
        user = ensure_user("parent.bus@test.k12.local", "Parent Bus", roles=("Guardian",))
        link_guardian_to_student(child, ensure_guardian("Parent Bus", user))
        route = ensure_route(
            "Route Portal", ensure_vehicle("DXB P 40001", capacity=10)
        )
        frappe.get_doc(
            {
                "doctype": "K12 Transport Assignment",
                "student": child,
                "academic_year": ensure_academic_year(),
                "route": route,
                "stop_name": "Main Gate",
            }
        ).insert(ignore_permissions=True)

        frappe.set_user(user)
        profile = portal.get_child_profile(child)
        self.assertEqual(profile["transport"]["route"], route)
        self.assertEqual(profile["transport"]["stop"], "Main Gate")

        frappe.set_user("Administrator")
        child_no_bus = ensure_student("Portal Walk Child")
        link_guardian_to_student(
            child_no_bus, frappe.db.get_value("Guardian", {"user": user})
        )
        frappe.set_user(user)
        self.assertIsNone(portal.get_child_profile(child_no_bus)["transport"])
