# -*- coding: utf-8 -*-
# Copyright (c) 2021, KCSC and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import date, datetime
from attendance.attendance.doctype.attendance_calculation.attendance_calculation import get_employee_salary
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import dateutils, flt, cstr, nowdate, comma_and
from frappe import throw, msgprint, _
from frappe.utils.data import get_link_to_form, to_timedelta
from dateutil import parser
class HourlyLeave(Document):
	def validate(self):
		self.set_totals()
		self.validate_discount()
		self.validate_periods()
  
	@frappe.whitelist()
	def validate_periods(self):
		sql = f"""
			select name from `tabHourly Leave` where docstatus < 2 and name != '{self.name}' 
   			and employee = '{self.employee}'
			and transaction_date = date('{self.transaction_date}')
			and ( 
				(from_time BETWEEN '{self.from_time}' AND '{self.to_time}') or 
				(to_time BETWEEN '{self.from_time}' AND '{self.to_time}') or 
    			(from_time < '{self.from_time}' and to_time > '{self.to_time}')
       )
  			"""
		# frappe.msgprint(sql)
		exist = frappe.db.sql_list(sql)or []
		if len(exist) > 0:
			lnk = get_link_to_form (self.doctype,exist[0])
			frappe.throw(_("{} with same time").format(lnk))
	@frappe.whitelist()
	def set_totals(self):
		self.transaction_date = parser.parse(str(self.transaction_date)).date()
		self.from_time = to_timedelta(str(self.from_time))
		self.to_time = to_timedelta(str(self.to_time))
		if self.from_time > self.to_time :
			frappe.throw(_("from time must be less than to time"))
		self.duration = (self.to_time - self.from_time).seconds / 3600
	def validate_discount (self):
		if self.effecting_type == "Salary Deduction" and not self.salary_component :
				frappe.throw(_("Please Set Salary Component"))
		if self.effecting_type == "Leaves Balance Deduction" and not self.leave_component :
				frappe.throw(_("Please Set Leave Component"))

	def on_submit(self):
		self.submit_discounts()
  
	def on_cancel(self):
		self.cancel_leave_leadger_entry()
	def submit_discounts(self):
		if not self.duration :
			return
		total_days = 30
		total_hours = 8
		employee = frappe.get_doc("Employee",self.employee)
		calculate_amount_based_on_formula = frappe.db.get_single_value(
				"Payroll Settings", "calculate_amount_based_on_formula_on_additional_salary")
		if employee.attendance_rule :
			total_days,total_hours = frappe.db.get_value("Attendance Rule",employee.attendance_rule,["working_days_per_month" , "working_hours_per_day"])
			total_days = total_days or 30
			total_hours = total_hours or 8


		if self.effecting_type == "Salary Deduction" and self.salary_component :
				if not calculate_amount_based_on_formula:
					total_salary = get_employee_salary(employee,self.transaction_date or date.today())
					day_rate = total_salary / total_days
					hour_rate = day_rate / total_hours
					amount = (self.duration * hour_rate)
				else :
					amount = self.duration
				remark = self.justification or ""
				self.submit_additional_salary(employee,amount,self.salary_component,"Deduction",self.transaction_date,remark)

		elif self.effecting_type == "Leaves Balance Deduction" and self.leave_component :
				amount = (self.duration) / total_hours
				if self.check_leave_balance(employee.name,self.leave_component,amount,self.transaction_date) :
					self.submit_leave_balance(employee,-1*amount,self.leave_component,self.transaction_date)
				else :
					if not self.salary_component :
						frappe.throw(_("Please set Salary Component"))
					if not calculate_amount_based_on_formula :
						total_salary = get_employee_salary(employee,self.transaction_date or date.today())
						day_rate = total_salary / total_days
						hour_rate = day_rate / total_hours
						amount = (self.duration * hour_rate)
					else :
						amount = self.duration
					remark = self.justification or ""
					self.submit_additional_salary(employee,amount,self.salary_component,"Deduction",self.transaction_date,remark)

						

	def submit_additional_salary(self,employee,amount , salary_component , salary_component_type ,payroll_effect_date,remark):
			if not amount :
				return
			try:
				doctype = "Additional Salary"
				doc = frappe.new_doc(doctype)
				doc.naming_series = "HR-ADS-.YY.-.MM.-"
				doc.employee = employee.name
				doc.employee_name = employee.employee_name
				doc.department = employee.department
				doc.company = employee.company

				doc.salary_component = salary_component
				doc.type = salary_component_type
				doc.amount = amount
				doc.remark = remark
				doc.overwrite_salary_structure_amount = 0
				doc.ref_doctype = self.doctype
				doc.ref_docname = self.name
				doc.payroll_date = payroll_effect_date
				doc.amount_based_on_formula , doc.formula = frappe.db.get_value("Salary Component" , doc.salary_component , ["amount_based_on_formula" , "formula"] )

				doc.submit()
			except Exception as e :
				frappe.msgprint(_(str(e)))


	def submit_leave_balance(self,employee,amount , leave_component,transaction_date):
		if not amount :
			return
		try:
			doctype = "Leave Ledger Entry"
			doc = frappe.new_doc(doctype)
			doc.employee = employee.name
			doc.employee_name = employee.employee_name
			doc.leave_type = leave_component
			doc.transaction_type = "Leave Encashment"
			doc.reference_type = self.doctype
			doc.reference_name = self.name
			doc.leaves = amount
			doc.company = employee.company
			doc.from_date = transaction_date 
			doc.to_date = transaction_date 
			doc.submit()
		except Exception as e:
			frappe.msgprint(_(str(e)))

	@frappe.whitelist()
	def cancel_leave_leadger_entry(self):
			frappe.db.sql(f"""
                 update `tabLeave Ledger Entry`
                 set docstatus = 2 
                 where reference_type = '{self.doctype}'
                 and reference_name = '{self.name}'
                 """)
			frappe.db.commit()
			frappe.msgprint(_("All Leave Entries is cancelled"))
   
   
	def check_leave_balance (self,employee,leave_type,days,transaction_date):
		leave_balance = get_leave_balance_on(employee,leave_type, transaction_date, 
			consider_all_leaves_in_the_allocation_period=True)
		return ((leave_balance or 0 ) >=  days)
