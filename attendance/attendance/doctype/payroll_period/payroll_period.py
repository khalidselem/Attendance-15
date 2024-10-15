# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import  formatdate

from hrms.payroll.doctype.payroll_period.payroll_period import PayrollPeriod

class CustomPayrollPeriod(PayrollPeriod):
    def validate_overlap(self):
        query = """
            select name
            from `tab{0}`
            where name != %(name)s
            and payroll_type = %(payroll_type)s
            and company = %(company)s and (start_date between %(start_date)s and %(end_date)s \
                or end_date between %(start_date)s and %(end_date)s \
                or (start_date < %(start_date)s and end_date > %(end_date)s))
            """
        if not self.name:
            # hack! if name is null, it could cause problems with !=
            self.name = "New " + self.doctype

        overlap_doc = frappe.db.sql(
            query.format(self.doctype),
            {
                "start_date": self.start_date,
                "end_date": self.end_date,
                "name": self.name,
                "company": self.company,
                "payroll_type": self.payroll_type
            },
            as_dict=1,
        )

        if overlap_doc:
            msg = (
                _("A {0} exists between {1} and {2} (").format(
                    self.doctype, formatdate(self.start_date), formatdate(self.end_date)
                )
                + """ <b><a href="/app/Form/{0}/{1}">{1}</a></b>""".format(self.doctype, overlap_doc[0].name)
                + _(") for {0}").format(self.company)
            )
            frappe.throw(msg)
