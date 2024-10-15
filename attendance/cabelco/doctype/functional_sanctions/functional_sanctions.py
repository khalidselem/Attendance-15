# Copyright (c) 2022, Peter Maged and contributors
# For license information, please see license.txt

from datetime import date
from attendance.attendance.doctype.attendance_calculation.attendance_calculation import get_employee_salary
import frappe
from frappe import _
from frappe.model.document import Document

class Functionalsanctions(Document):
	def validate(self):
		self.validate_discount()
	def validate_discount (self):
		for row in getattr(self,'functional_sanctions',[]):
			if row.discount and not row.salary_component :
					frappe.throw(_("Please Set Salary Component in Row {}").format(row.idx))



	def on_submit(self) :
		self.submit_discounts()


	def submit_discounts(self):
		total_days = 30
		employee = frappe.get_doc("Employee",self.employee)
		if employee.attendance_rule :
			total_days = frappe.db.get_value("Attendance Rule",employee.attendance_rule,"working_days_per_month") or 30
		for row in getattr(self,'functional_sanctions',[]):

			calculate_amount_based_on_formula = frappe.db.get_single_value(
				"Payroll Settings", "calculate_amount_based_on_formula_on_additional_salary")
			if not calculate_amount_based_on_formula:
				total_salary = get_employee_salary(employee,row.date_ref or date.today())
				day_rate = total_salary / total_days
				amount = row.discount * day_rate
			else :
				amount = row.discount
			# if row.period > 0 :
			# 	amount += (row.period or 0) * day_rate
			
			if row.discount and row.salary_component :
					remark = (row.penalty or "") + " / " + (row.sanctions or "")
					self.submit_additional_salary(employee,amount,row.salary_component,"Deduction",row.date_ref,remark)





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
				doc.mark = remark
				doc.overwrite_salary_structure_amount = 0
				doc.ref_doctype = self.doctype
				doc.ref_docname = self.name
				doc.amount_based_on_formula , doc.formula = frappe.db.get_value("Salary Component" , doc.salary_component , ["amount_based_on_formula" , "formula"] )

				doc.payroll_date = payroll_effect_date
				doc.submit()
			except Exception as e :
				frappe.msgprint(_(str(e)))





	# def on_cancel(self) :
	# 	docs = frappe.db.sql_list(f"""
    #                         select name from `tabAdditional Salary`
    #                         where ref_doctype = '{self.doctype}' 
    #                         and  ref_docname = '{self.name}' 
    #                         and docstatus < 2  """) or []
	# 	for docname in docs :
	# 		doc = frappe.get_doc("Additional Salary",docname)
	# 		if 



