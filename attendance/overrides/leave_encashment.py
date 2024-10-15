# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from attendance.attendance.doctype.attendance_calculation.attendance_calculation import get_employee_salary
import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from frappe.utils.data import flt, get_link_to_form
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	get_assigned_salary_structure,
)
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment


class CustomLeaveEncashment(LeaveEncashment):

	@frappe.whitelist()
	def get_leave_details_for_encashment(self):
		result = super(CustomLeaveEncashment,self).get_leave_details_for_encashment()
		salary_structure = get_assigned_salary_structure(
			self.employee, self.encashment_date or getdate(nowdate())
		)
		if not salary_structure:
			frappe.throw(
				_("No Salary Structure assigned for Employee {0} on given date {1}").format(
					self.employee, self.encashment_date
				)
			)
		employee = frappe.get_doc("Employee" , self.employee)
		employee_salary = get_employee_salary(employee , self.encashment_date)
		per_day_encashment = flt(employee_salary / 30)
		self.encashment_amount = (
			self.encashable_days * per_day_encashment if per_day_encashment > 0 else 0
		)

		return result

	def on_submit(self):
		if not self.leave_allocation:
			self.leave_allocation = self.get_leave_allocation().get("name")

		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.payment_type = 'Pay'
		payment_entry.party_type = 'Employee'
		payment_entry.company = frappe.get_value("Employee", self.employee, "company")
		payment_entry.party = self.employee
		payment_entry.party_name = self.employee_name
		payment_entry.posting_date = getdate(self.encashment_date)
		payment_entry.paid_amount = self.encashment_amount
		payment_entry.received_amount = self.encashment_amount
		payment_entry.flags.ignore_permissions = 1
		payment_entry.flags.ignore_mandatory = 1
		payment_entry.flags.ignore_validate = 1
		payment_entry.reference_doctype = self.doctype
		payment_entry.reference_name = self.name
		payment_entry.save()

		lnk = get_link_to_form(payment_entry.doctype , payment_entry.name)
		frappe.msgprint(_("{} {} was created").format(payment_entry.doctype , lnk))
                  
		self.db_set("payment_entry", payment_entry.name)

		# Set encashed leaves in Allocation
		frappe.db.set_value(
			"Leave Allocation",
			self.leave_allocation,
			"total_leaves_encashed",
			frappe.db.get_value("Leave Allocation", self.leave_allocation, "total_leaves_encashed")
			+ self.encashable_days,
		)

		self.create_leave_ledger_entry()
  
	def on_cancel(self):
		if self.payment_entry:
			payment_entry = frappe.get_doc("Payment Entry", self.payment_entry)
			self.db_set("payment_entry", "")
			payment_entry.db_set("reference_doctype" , "")
			payment_entry.db_set("reference_name" , "")

			if payment_entry.docstatus == 1 :
				payment_entry.cancel()
    
			payment_entry.delete()

		super(CustomLeaveEncashment,self).on_cancel()

