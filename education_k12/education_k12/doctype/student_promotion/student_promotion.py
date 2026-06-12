import frappe
from frappe import _
from frappe.model.document import Document


class StudentPromotion(Document):
    def validate(self):
        if self.from_academic_year == self.to_academic_year:
            frappe.throw(_("From and To academic years must differ"))
        promote_rows = [r for r in self.students if r.action == "Promote"]
        if promote_rows:
            if not self.to_program:
                frappe.throw(_("To Grade/Program is required to promote students"))
            if self.to_program == self.from_program:
                frappe.throw(_("To Grade/Program must differ from the current grade"))

    @frappe.whitelist()
    def get_students(self):
        enrollments = frappe.get_all(
            "Program Enrollment",
            filters={
                "program": self.from_program,
                "academic_year": self.from_academic_year,
                "docstatus": 1,
            },
            fields=["name", "student", "student_name"],
            order_by="student_name asc",
        )
        self.set("students", [])
        for enrollment in enrollments:
            self.append(
                "students",
                {
                    "student": enrollment.student,
                    "student_name": enrollment.student_name,
                    "current_enrollment": enrollment.name,
                    "action": "Promote",
                },
            )
        return self

    def on_submit(self):
        for row in self.students:
            if row.action == "Exit":
                continue
            target_program = (
                self.to_program if row.action == "Promote" else self.from_program
            )
            if frappe.db.exists(
                "Program Enrollment",
                {
                    "student": row.student,
                    "program": target_program,
                    "academic_year": self.to_academic_year,
                    "docstatus": ("<", 2),
                },
            ):
                continue
            enrollment = frappe.get_doc(
                {
                    "doctype": "Program Enrollment",
                    "student": row.student,
                    "program": target_program,
                    "academic_year": self.to_academic_year,
                    "enrollment_date": frappe.utils.today(),
                }
            )
            enrollment.insert(ignore_permissions=True)
            enrollment.submit()
