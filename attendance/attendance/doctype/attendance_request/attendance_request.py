# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate

from erpnext.setup.doctype.employee.employee import is_holiday
from hrms.hr.utils import validate_active_employee


class AttendanceRequest(Document):
    def validate(self):
        # frappe.msgprint('sss')
        validate_active_employee(self.employee)
        validate_dates(self, self.from_date, self.to_date)
        if self.half_day:
            if not getdate(self.from_date) <= getdate(self.half_day_date) <= getdate(self.to_date):
                frappe.throw(_("Half day date should be in between from date and to date"))

    # def on_submit(self):
    #     self.create_attendance()

    def on_cancel(self):
        attendance_list = frappe.get_list(
            "Attendance", {"employee": self.employee, "attendance_request": self.name}
        )
        if attendance_list:
            for attendance in attendance_list:
                attendance_obj = frappe.get_doc("Attendance", attendance["name"])
                attendance_obj.cancel()

    def create_attendance(self):
        request_days = date_diff(self.to_date, self.from_date) + 1
        for number in range(request_days):
            attendance_date = add_days(self.from_date, number)
            skip_attendance = self.validate_if_attendance_not_applicable(attendance_date)
            if not skip_attendance:
                attendance = frappe.new_doc("Attendance")
                attendance.employee = self.employee
                attendance.employee_name = self.employee_name
                if self.half_day and date_diff(getdate(self.half_day_date), getdate(attendance_date)) == 0:
                    attendance.status = "Half Day"
                elif self.reason == "Work From Home":
                    attendance.status = "Work From Home"
                else:
                    attendance.status = "Present"
                attendance.attendance_date = attendance_date
                attendance.company = self.company
                attendance.attendance_request = self.name
                attendance.save(ignore_permissions=True)
                attendance.submit()

    def validate_if_attendance_not_applicable(self, attendance_date):
        # Check if attendance_date is a Holiday
        if is_holiday(self.employee, attendance_date):
            frappe.msgprint(
                _("Attendance not submitted for {0} as it is a Holiday.").format(attendance_date), alert=1
            )
            return True

        # Check if employee on Leave
        leave_record = frappe.db.sql(
            """select half_day from `tabLeave Application`
            where employee = %s and %s between from_date and to_date
            and docstatus = 1""",
            (self.employee, attendance_date),
            as_dict=True,
        )
        if leave_record:
            frappe.msgprint(
                _("Attendance not submitted for {0} as {1} on leave.").format(attendance_date, self.employee),
                alert=1,
            )
            return True

        return False
def validate_dates(doc, from_date, to_date):
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", doc.employee, ["date_of_joining", "relieving_date"]
	)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	# elif getdate(from_date) > getdate(nowdate()):
	# 	frappe.throw(_("Future dates not allowed"))
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"))
