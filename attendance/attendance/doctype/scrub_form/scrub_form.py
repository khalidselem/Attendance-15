# Copyright (c) 2023, Peter Maged and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate, add_months
from dateutil.parser import parse


class ScrubForm(Document):

    def validate(self):
        self.set_return_date()
        self.set_totals()

    @frappe.whitelist()
    def get_default_settings(self):
        settings = frappe.get_single("Scrub Settings")
        self.months = settings.months or 0
        self.scrub_component = settings.scrub_component or ''
        self.warehouse = settings.default_warehouse or ''
        self.return_component = settings.return_component or ''
        self.set_return_date()

    @frappe.whitelist()
    def set_return_date(self):
        self.posting_date = parse(self.posting_date or nowdate()).date()
        self.due_date = parse(self.due_date or nowdate()).date()
        self.return_date = add_months(self.due_date, self.months or 0)

    @frappe.whitelist()
    def set_totals(self):
        self.total_amount = 0
        for item in self.items:
            item.rate = item.rate or 0
            item.qty = item.qty or 0
            item.total_amount = item.rate * item.qty
            self.total_amount += item.total_amount

    def on_submit(self):
        self.create_additional_salary()
        # self.create_stock_entry()

    @frappe.whitelist()
    def create_additional_salary(self, is_return=0):

        if not self.add_additional_salary and self.status != "Delivered":
            return

        doctype = "Additional Salary"
        doc = frappe.new_doc(doctype)
        doc.naming_series = "HR-ADS-.YY.-.MM.-"
        doc.employee = self.employee
        doc.employee_name = self.employee_name
        doc.department = self.department
        doc.company = self.company

        doc.salary_component = self.scrub_component if not is_return else self.return_component
        doc.type = "Deduction" if not is_return else "Earning"

        doc.amount = self.total_amount or 0
        doc.remark = self.notes or ''
        doc.mark = self.notes or ''
        doc.overwrite_salary_structure_amount = 0
        doc.ref_doctype = self.doctype
        doc.ref_docname = self.name
        doc.payroll_date = self.due_date if not is_return else self.return_date
        doc.submit()

        if is_return:
            self.db_set("status", "Returned")
        
        return doc

    @frappe.whitelist()
    def create_stock_entry(self):
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.company = self.company
        stock_entry.posting_date = self.due_date
        stock_entry.from_warehouse = self.warehouse
        stock_entry.scrub_form = self.name
        stock_entry.remarks = self.notes or ''
        for item in self.items:
            item_doc = frappe.get_doc("Item", item.item_code)
            item_row = {
                "s_warehouse": self.warehouse,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "basic_rate": item.rate,
                "conversion_factor": 1,
                "uom": item_doc.stock_uom,
                "stock_uom": item_doc.stock_uom,
            }

            stock_entry.append('items', item_row)

        stock_entry.set_missing_values()
        # stock_entry.submit()

        return stock_entry.as_dict()


@frappe.whitelist()
def create_stock_entry(source_name):
    scrub = frappe.get_doc("Scrub Form", source_name)
    return scrub.create_stock_entry()

@frappe.whitelist()
def return_additional_salary(source_name):
    scrub = frappe.get_doc("Scrub Form", source_name)
    return scrub.create_additional_salary(is_return = 1)


def on_submit_stock_entry(self, fun=''):
    if getattr(self, 'scrub_form', None):
        scrub_form = frappe.get_doc("Scrub Form", self.scrub_form)
        if scrub_form.status == "New":
            scrub_form.db_set("status", "Delivered")


def return_scrub_forms():
	sql = f"""
	select name from `tabScrub Form` where docstatus = 1 and status = "Delivered"
	and date(return_date) <= CURDATE()
	"""
	scrubs = frappe.db.sql_list(sql) or []

	for scrub in scrubs :
		print("scrub")
		scrub_doc = frappe.get_doc("Scrub Form",scrub)
		scrub_doc.create_additional_salary(is_return = 1)

def set_payroll_entry_status(doc,method=None):
    if method=="on_submit":
        doc.db_set("status","Submitted")
    elif method=="on_cancel":
        doc.db_set("status","Cancelled")

