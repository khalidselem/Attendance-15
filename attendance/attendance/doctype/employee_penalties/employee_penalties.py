# Copyright (c) 2021, Peter Maged and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import to_timedelta , add_days , nowdate , get_link_to_form
from dateutil.parser import parse
from datetime import datetime,timedelta,date,time
from frappe.utils.data import flt, getdate
from babel.dates import format_date

class EmployeePenalties(Document):
	def validate(self):
		if (self.based_on == "Days"):
			calculate_amount_based_on_formula = frappe.db.get_single_value(
                    "Payroll Settings", "calculate_amount_based_on_formula_on_additional_salary")
			if not calculate_amount_based_on_formula :
				total_salary = get_employee_salary (frappe._dict({
									'name':self.employee , 
									"employee_name" : self.employee_name
									}),self.payroll_date)
				self.amount = (total_salary / 30) * self.days
			else :
				self.amount = self.days
		if not self.amount :
				frappe.throw(_("Amount can't be 0"))
 
	def on_submit (self) :
		self.submit_additional_salary()
	# def on_cancel (self):
	# 	self.cancel_additional_salary()

	def submit_additional_salary(self):
		if not self.amount :
			return

		doc = frappe.new_doc("Additional Salary")
		doc.naming_series = "HR-ADS-.YY.-.MM.-"
		doc.employee = self.employee
		doc.employee_name = self.employee_name
		doc.department = self.department
		doc.company = self.company

		doc.salary_component =self.salary_component
		doc.type = self.type
		doc.amount = self.amount
		doc.remark = self.penalty_type
		doc.overwrite_salary_structure_amount = 0
		doc.ref_doctype = self.doctype
		doc.ref_docname = self.name
		doc.payroll_date = self.payroll_date
		doc.amount_based_on_formula , doc.formula = frappe.db.get_value("Salary Component" , doc.salary_component , ["amount_based_on_formula" , "formula"] )

		doc.submit()
		self.ref_doctype = doc.doctype
		self.ref_docname = doc.name
		
	def cancel_additional_salary (self) :
		doc = frappe.get_doc(self.ref_doctype,self.ref_docname)
		if doc.docstatus == 1 :
			doc.cancel()
		doc.delete()
  
  
whitelisted_globals = {
			"int": int,
			"float": float,
			"long": int,
			"round": round,
			"date": datetime.date,
			"getdate": getdate
		}


def get_employee_salary (employee,payroll_date):
	total_salary = 0
	salary_structure , salary_structure_assignment = get_assigned_salary_structure(employee.name ,payroll_date)
	if salary_structure and salary_structure_assignment:
		salary_structure = frappe.get_doc("Salary Structure" , salary_structure)
		salary_structure_assignment = frappe.get_doc("Salary Structure Assignment" , salary_structure_assignment)
		comp_dict = frappe._dict()
			

		comp_dict.update(salary_structure_assignment.__dict__)
		comp_dict.update(salary_structure.__dict__)
		# frappe.msgprint(str(comp_dict))
		# comp_dict.update(employee)
		# comp_dict.update(self.as_dict())
		earnings_components = [x for x in salary_structure.get("earnings") if  not x.amount_based_on_formula]
		deductions_components = [x for x in salary_structure.get("deductions") if  not x.amount_based_on_formula]
		formula_earnings_components = [x for x in salary_structure.get("earnings") if x.amount_based_on_formula and x.formula]
		formula_deductions_components = [x for x in salary_structure.get("deductions") if x.amount_based_on_formula and x.formula]
		for row in earnings_components+formula_earnings_components:
			amount = (row.amount or 0) 
			if  row.amount_based_on_formula  :
				formula = row.formula.strip().replace("\n", " ") if row.formula else None
				if formula:
					try :
						amount = flt(frappe.safe_eval(formula, whitelisted_globals, comp_dict), row.precision("amount"))
					except :
						amount = 0
				else :
					amount = 0 
			comp_dict[row.abbr] = amount
			if row.consider_in_hour_rate : 
				total_salary += amount	

		for row in deductions_components+ formula_deductions_components:
			amount = ((row.amount or 0) * -1)
			if  row.amount_based_on_formula  :
				formula = row.formula.strip().replace("\n", " ") if row.formula else None
				if formula:
					try :
						amount = flt(frappe.safe_eval(formula, whitelisted_globals, comp_dict), row.precision("amount"))
					except :
						amount = 0
				else :
					amount = 0 
			comp_dict[row.abbr] = amount
			if row.consider_in_hour_rate : 
				total_salary += amount	
	else :
		frappe.throw(
				_("Please assign a Salary Structure for Employee {0} "
				"applicable from or before {1} first").format(
					frappe.bold(employee.employee_name),
					frappe.bold(format_date(payroll_date)),
				)
			)
	return total_salary



def get_assigned_salary_structure(employee, on_date):
	if not employee or not on_date:
		return None
	salary_structure = frappe.db.sql("""
		select salary_structure , name from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and %(on_date)s >= from_date order by from_date desc limit 1""", {
			'employee': employee,
			'on_date': on_date,
		})
	return (salary_structure[0][0] , salary_structure[0][1]) if salary_structure else (None ,None)