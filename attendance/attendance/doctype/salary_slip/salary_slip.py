# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import datetime
import math
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

import frappe
from frappe import _, msgprint
from frappe.model.naming import make_autoname
from frappe.utils import (
	add_days,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	get_first_day,
	getdate,
	money_in_words,
	rounded,
	get_link_to_form,
)
from frappe.utils.background_jobs import enqueue
from six import iteritems

import erpnext
from erpnext.accounts.utils import get_fiscal_year
from hrms.hr.utils import get_holiday_dates_for_employee, validate_active_employee
 from loans.loan_management.doctype.loan_repayment.loan_repayment import (
	calculate_amounts,
	create_repayment_entry,
) 
from hrms.payroll.doctype.additional_salary.additional_salary import get_additional_salaries
from hrms.payroll.doctype.employee_benefit_application.employee_benefit_application import (
	get_benefit_component_amount,
)
from hrms.payroll.doctype.employee_benefit_claim.employee_benefit_claim import (
	get_benefit_claim_amount,
	get_last_payroll_period_benefits,
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates
from hrms.payroll.doctype.payroll_period.payroll_period import (
	get_payroll_period,
	get_period_factor,
)
from erpnext.utilities.transaction_base import TransactionBase


class AttendanceSalarySlip(SalarySlip):

    def add_additional_salary_components(self, component_type):
        calculate_amount_based_on_formula = frappe.db.get_single_value(
            "Payroll Settings", "calculate_amount_based_on_formula_on_additional_salary")
        if not calculate_amount_based_on_formula:
            return super(AttendanceSalarySlip, self).add_additional_salary_components(component_type)
        else:
            additional_salaries = get_additional_salaries(
                self.employee, self.start_date, self.end_date, component_type
            )
            # frappe.msgprint(str(additional_salaries))
            data, default_data = self.get_data_for_eval()
            for additional_salary in additional_salaries:
                amount = 1
                additional_salary.condition, additional_salary.abbr = frappe.db.get_value(
                    "Salary Component", additional_salary.component, ["condition", "salary_component_abbr"])
                additional_salary.amount_based_on_formula, additional_salary.formula = frappe.db.get_value(
                    "Additional Salary", additional_salary.name, ["amount_based_on_formula", "formula"])
                try:
                    amount = self.eval_condition_and_formula(
                        additional_salary, data, precision=0)
                except Exception as e:
                    frappe.msgprint(_("Error While add Additional Salary {} , {}").format(
                        additional_salary.component, _(str(e))))
                amount *= additional_salary.amount
                self.update_component_row(
                    get_salary_component_data(additional_salary.component),
                    amount,
                    component_type,
                    additional_salary,
                    is_recurring=additional_salary.is_recurring,
                )
                default_data[additional_salary.abbr] = amount

    def eval_condition_and_formula(self, d, data, precision=1):
        # try:
        condition = d.condition.strip().replace("\n", " ") if d.condition else None
        if condition:
            if not frappe.safe_eval(condition, self.whitelisted_globals, data):
                return None
        amount = d.amount
        if d.amount_based_on_formula:
            formula = d.formula.strip().replace("\n", " ") if d.formula else None
            if formula:
                if precision:
                    amount = flt(frappe.safe_eval(
                        formula, self.whitelisted_globals, data), d.precision("amount"))
                else:
                    amount = flt(frappe.safe_eval(
                        formula, self.whitelisted_globals, data))
        if amount:
            data[d.abbr] = amount

        return amount

        # except NameError as err:
        # 	frappe.throw(
        # 		_("{0} <br> This error can be due to missing or deleted field.").format(err),
        # 		title=_("Name error"),
        # 	)
        # except SyntaxError as err:
        # 	frappe.throw(_("Syntax error in formula or condition: {0}").format(err))
        # except Exception as e:
        # 	frappe.throw(_("Error in formula or condition: {0}").format(e))
        # 	raise


    # def get_payment_days(self, include_holidays_in_total_working_days):
    #     if self.joining_date and self.joining_date > getdate(self.end_date):
    #         # employee joined after payroll date
    #         return 0
    #
    #     if self.relieving_date:
    #         employee_status = frappe.db.get_value("Employee", self.employee, "status")
    #         if self.relieving_date < getdate(self.start_date) and employee_status != "Left":
    #             frappe.throw(
    #                 _("Employee {0} relieved on {1} must be set as 'Left'").format(
    #                     get_link_to_form("Employee", self.employee), formatdate(self.relieving_date)
    #                 )
    #             )
    #
    #     payment_days = date_diff(self.actual_end_date, self.actual_start_date) + 1
    #
    #     if not cint(include_holidays_in_total_working_days):
    #         holidays = self.get_holidays_for_employee(self.actual_start_date, self.actual_end_date)
    #         payment_days -= len(holidays)
    #     frappe.msgprint(str(payment_days))
    #     return payment_days

def get_salary_component_data(component):
	return frappe.get_value(
		"Salary Component",
		component,
		[
			"name as salary_component",
			"depends_on_payment_days",
			"salary_component_abbr as abbr",
			"do_not_include_in_total",
			"is_tax_applicable",
			"is_flexible_benefit",
			"variable_based_on_taxable_salary",
		],
		as_dict=1,
	)

