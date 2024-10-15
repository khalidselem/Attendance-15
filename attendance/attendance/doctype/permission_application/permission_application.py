# Copyright (c) 2021, Peter Maged and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import to_timedelta
from dateutil.parser import parse
from datetime import datetime,date,time,timedelta

from frappe.utils.data import add_months, now_datetime
class PermissionApplication(Document):
	def validate (self):
		self.set_total_minutes()
		self.validate_applicable_after()
		self.validate_last_permissions()
	@frappe.whitelist()
	def set_total_minutes(self):
		if self.from_time and self.to_time :
			self.to_time = to_timedelta(str(self.to_time))
			self.from_time = to_timedelta(str(self.from_time))
			if self.from_time < self.to_time :
				self.total_minutes = (self.to_time - self.from_time).seconds / 60
			else :
				self.from_time = None
				self.to_time = None
				self.total_minutes = 0
				frappe.throw(_("From To Time is after to Time"))

	def validate_applicable_after (self):
		permission_applicable_after = frappe.db.get_single_value("Attendance Settings","permission_applicable_after") or 0
		if permission_applicable_after :
			date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
			if date_of_joining :
				available_date = parse(str(date_of_joining)).date() + timedelta(days=permission_applicable_after)
				doc_date = parse(str(self.day)).date()
				if doc_date <= available_date :
					frappe.throw(_("Employee {} must exceed {} Days to proceed Permission").format(self.employee,permission_applicable_after))

	def validate_last_permissions (self):
		
		attendance_rule = frappe.db.get_value("Employee",self.employee,'attendance_rule')
		if not attendance_rule :
			frappe.throw(_(f"Employee {self.employee} doesn't have Attendance Rule"))
		attendance_rule = frappe.get_doc("Attendance Rule",attendance_rule)
		if not attendance_rule.enable_permission :
				frappe.throw(_(f"Employee {self.employee} doesn't have Permission Rule"))

		payroll_period = frappe.db.get_value("Payroll Period" , {'start_date':["<=",self.day],
															'end_date':[">=",self.day]},['name','start_date','end_date'],as_dict=1)
		
		settings = frappe.get_single("Attendance Settings")
		if settings and not settings.permission_payroll_period :
				req_day = parse(str(self.day))
				start_date = datetime(req_day.year, req_day.month, settings.permission_start_day or 1)
				if start_date > req_day :
					start_date = add_months(start_date,-1)

				end_date = add_months(start_date,1) +timedelta(days=-1)
		else :
			if not payroll_period :
					frappe.throw(_("Selected Date doesn't match any Payroll Period"))
			start_date,end_date = payroll_period.start_date ,  payroll_period.end_date
		# frappe.msgprint("start_date")
		# frappe.msgprint(str(start_date))
		# frappe.msgprint("end_date")
		# frappe.msgprint(str(end_date))
		sql = f"""
				select name , total_minutes , from_Time , to_time , day from `tabPermission Application` perm
				where perm.docstatus < 2 and
				date(day) between date('{start_date}') and  date('{end_date}')
				and status in ('Open','Approved') and name <> '{self.name}' and employee = '{self.employee}'
				"""
		# frappe.msgprint(sql)
		if self.total_minutes > attendance_rule.max_permission_per_time or 0 :
						frappe.throw(_(f"You can't exceed {attendance_rule.max_permission_per_time} minutes per time"))
				
		if self.total_minutes > attendance_rule.max_permissions_minutes or 0 :
			frappe.throw(_(f"You already exceed {attendance_rule.max_permissions_minutes} minutes"))

		permissions = frappe.db.sql(sql,as_dict=1)
		if permissions :
				same_date = [x for x in permissions if parse(str(x.day)) == parse(str(self.day)) ]
				if len(same_date) > 0:
						frappe.throw(_(f"You already have permission in same day"))
				
				if len(permissions) >= attendance_rule.max_permissions_times or 0 :
					frappe.throw(_(f"You can't exceed {attendance_rule.max_permissions_times} times of permission"))
				
				total_minutes = sum([x.total_minutes for x in permissions])
				if total_minutes + self.total_minutes > attendance_rule.max_permissions_minutes or 0 :
					frappe.throw(_(f"You already exceed {attendance_rule.max_permissions_minutes} minutes"))
						
						

	def on_cancel(self):
		self.status = "Cancelled"
	def on_submit(self):
				if self.status not in  ["Approved","Rejected"]:
					frappe.throw(_("Only Permission Applications with status 'Approved' and 'Rejected' can be submitted"))