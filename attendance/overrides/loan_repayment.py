# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import getdate

from erpnext.accounts.general_ledger import make_gl_entries

from lending.loan_management.doctype.loan_repayment.loan_repayment import LoanRepayment


class CustomLoanRepayment(LoanRepayment):

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		if self.shortfall_amount and self.amount_paid > self.shortfall_amount:
			remarks = "Shortfall repayment of {0}.<br>Repayment against loan {1}".format(
				self.shortfall_amount, self.against_loan
			)
		elif self.shortfall_amount:
			remarks = "Shortfall repayment of {0} against loan {1}".format(
				self.shortfall_amount, self.against_loan
			)
		else:
			remarks = "Repayment against loan " + self.against_loan

		if self.reference_number:
			remarks += "with reference no. {}".format(self.reference_number)

		if hasattr(self, "repay_from_salary") and self.repay_from_salary:
			payment_account = self.payroll_payable_account
		else:
			payment_account = self.payment_account

		payment_party_type = ""
		payment_party = ""

		if (
			hasattr(self, "process_payroll_accounting_entry_based_on_employee")
			and self.process_payroll_accounting_entry_based_on_employee
		):
			payment_party_type = "Employee"
			payment_party = self.applicant

		if self.total_penalty_paid:
			gle_map.append(
				self.get_gl_dict(
					{
						"account": self.loan_account,
						"against": payment_account,
						"debit": self.total_penalty_paid,
						"debit_in_account_currency": self.total_penalty_paid,
						"against_voucher_type": "Loan",
						"against_voucher": self.against_loan,
						"remarks": _("Penalty against loan:") + self.against_loan,
						"cost_center": self.cost_center,
						"party_type": self.applicant_type,
						"party": self.applicant,
						"posting_date": getdate(self.posting_date),
					}
				)
			)

			gle_map.append(
				self.get_gl_dict(
					{
						"account": self.penalty_income_account,
						"against": self.loan_account,
						"credit": self.total_penalty_paid,
						"credit_in_account_currency": self.total_penalty_paid,
						"against_voucher_type": "Loan",
						"against_voucher": self.against_loan,
						"remarks": _("Penalty against loan:") + self.against_loan,
						"cost_center": self.cost_center,
						"posting_date": getdate(self.posting_date),
					}
				)
			)

		gle_map.append(
			self.get_gl_dict(
				{
					"account": payment_account,
					"against": self.loan_account + ", " + self.penalty_income_account,
					"debit": self.amount_paid,
					"debit_in_account_currency": self.amount_paid,
					"against_voucher_type": "Loan",
					"against_voucher": self.against_loan,
					"remarks": _(remarks),
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date),
					"party_type": payment_party_type,
					"party": payment_party,
				}
			)
		)

		gle_map.append(
			self.get_gl_dict(
				{
					"account": self.loan_account,
					"party_type": self.applicant_type,
					"party": self.applicant,
					"against": payment_account,
					"credit": self.amount_paid,
					"credit_in_account_currency": self.amount_paid,
					"against_voucher_type": "Loan",
					"against_voucher": self.against_loan,
					"remarks": _(remarks),
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date),
				}
			)
		)

		if gle_map:
			for row in gle_map :
				row.party_type = payment_party_type
				row.party = payment_party
    
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj, merge_entries=False)



