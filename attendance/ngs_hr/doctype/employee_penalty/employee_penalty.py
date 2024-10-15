# Copyright (c) 2022, Peter Maged and contributors
# For license information, please see license.txt

from attendance.attendance.doctype.attendance_calculation.attendance_calculation import get_employee_salary
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import getdate

class EmployeePenalty(Document):
	
	def validate(self):
		self.set_penalty_details()
	def on_submit(self):
		self.submit_additional_salary()
	def on_cancel(self):
		self.cancel_additional_salary()
	
	@frappe.whitelist()
	def set_penalty_details(self):
		previous_times = 0
		current_time = 1
		factor = 0 
		penalty_amount = 0

		if self.penalty_type and self.employee and self.payroll_effect_date and self.penalty_date and (not self.based_on_payroll_period or self.payroll_period) :	
			penalty_type = frappe.get_doc("Penalty Type",self.penalty_type)	
			employee = frappe.get_doc("Employee",self.employee)
			
			payroll_condition = ""
			if self.based_on_payroll_period :
				payroll_condition = f"and payroll_period = '{self.payroll_period}'"
			
			sql = f"""
				select * from `tab{self.doctype}`
				where name <> '{self.name}' and docstatus = 1 and date(penalty_date) <= date('{self.penalty_date}')
				and employee = '{self.employee}' and penalty_type = '{self.penalty_type}'
				{payroll_condition}
			""" 
			prev_penalties = frappe.db.sql(sql,as_dict=1) or []
			
			# print("prev_penalties ===========================================> " , prev_penalties)
			if penalty_type.continuous_penalty :
				prev_penalty_date = None if not prev_penalties else getdate(prev_penalties[0].penalty_date)
				prev_penalties.append(self)
				for row in prev_penalties :
					if prev_penalty_date and (getdate(row.penalty_date) - getdate(prev_penalty_date)).days > 1:
						previous_times +=1

					prev_penalty_date = getdate(row.penalty_date)

			else :
				previous_times = int(0 if not prev_penalties else len(prev_penalties))



			current_time = previous_times + 1
			row = penalty_type.penalties [-1]
			if current_time < len(penalty_type.penalties) :
				row = penalty_type.penalties[current_time-1]

			factor = row.factor if not self.edit_penalty_amount else (self.factor or row.factor)
			total_hourly_salary = get_employee_salary(employee,self.payroll_effect_date)
			if not total_hourly_salary :
					frappe.throw(_(f"Employee {employee.employee_name} has no components Consider in Hour Rate"))

			working_days_per_month = 30
			# working_hours_per_day = 8
			if employee.attendance_rule :
				attendance_rule = frappe.get_doc("Attendance Rule",employee.attendance_rule)
				working_days_per_month = attendance_rule.working_days_per_month or 30
				# working_hours_per_day = attendance_rule.working_hours_per_day or 8

			day_rate = total_hourly_salary / ( working_days_per_month )
			penalty_amount = factor * day_rate 
			
			# hour_rate = day_rate / (working_hours_per_day )





		self.previous_times = previous_times
		self.current_time = current_time
		self.factor = factor
		self.penalty_amount = penalty_amount


	def submit_additional_salary(self):
		# try:
			employee = frappe.get_doc("Employee",self.employee)
			penalty_type = frappe.get_doc("Penalty Type",self.penalty_type)
			doc = frappe.new_doc("Additional Salary")
			doc.naming_series = "HR-ADS-.YY.-.MM.-"
			doc.employee = employee.name
			doc.employee_name = employee.employee_name
			doc.department = employee.department
			doc.company = employee.company
			doc.salary_component = penalty_type.salary_component
			doc.type = "Deduction"
			doc.amount = self.penalty_amount
			doc.attendance_calculation = self.attendance_calculation
			doc.remark = _("Employee Penalty with {} Days for {}").format(self.factor,self.penalty_type) + "\n" +(self.notes or "")
			doc.mark = self.penalty_type
			doc.overwrite_salary_structure_amount = 0
			doc.ref_doctype = self.doctype
			doc.ref_docname = self.name
			doc.payroll_date = self.payroll_effect_date
			doc.submit()
			self.salary_slip = doc.name 
			self.update_salary_slip_ref()
		# except Exception as e :
		# 	frappe.msgprint(_(str(e)))
		
		
	def cancel_additional_salary(self):
		if self.salary_slip and frappe.db.exists("Additional Salary",self.salary_slip):
			doc = frappe.get_doc("Additional Salary",self.salary_slip)
			if doc.docstatus == 1 :
				doc.cancel()
			doc.delete()
			self.salary_slip = ''
			self.update_salary_slip_ref()

	def update_salary_slip_ref(self):
		frappe.db.sql(f"""
		update `tab{self.doctype}`
		set salary_slip = '{self.salary_slip}'
		where name = '{self.name}'
		""")
		frappe.db.commit()
		


