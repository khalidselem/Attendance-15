# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime
import frappe
from frappe import _

from frappe.utils.data import getdate

from dateutil.parser import parse


def execute(filters=None):
    if not filters:
        filters = {}
    data = []

    bet_dates = get_period_date_ranges(filters.get("period"),
                                       filters.get("from_date"), filters.get("to_date"))
    columns = get_columns(filters, bet_dates)
    data = get_data(filters, bet_dates)

    return columns, data


def get_columns(filters, bet_dates):
    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Link",
            "options": "Branch",
            "width": 120
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 120
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 120
        },
    ]

    for period in bet_dates:
        # 			_(get_mon(bet_dates[0])) + "-" + _(get_mon(bet_dates[1])) + " (" + _("Qty") + "):Float:120",
        # [datetime.date(2022, 1, 1), datetime.date(2022, 1, 31), 'Jan', 'January', 1],
        columns.append(
            {
                "label": _(period[3]),
                "fieldname": period[2],
                "fieldtype": "Float",
                "width": 100
            }
        )

    columns.extend([
        {
            "label": _("Total Visits"),
            "fieldname": "total_visits",
            "fieldtype": "Float",
            "width": 100
        },

    ])

    return columns


def get_conditions(filters={}):
    filters = frappe._dict(filters or {})
    conditions = ""

    data = filters.company
    if data:
        conditions += f" and emp.company = '{data}' "

    data = filters.branch
    if data:
        conditions += f" and emp.branch = '{data}' "

    data = filters.department
    if data:
        conditions += f" and emp.department = '{data}' "

    data = filters.designation
    if data:
        conditions += f" and emp.designation = '{data}' "

    data = filters.employee
    if data:
        conditions += f" and emp.name = '{data}' "

    return conditions


def get_data(filters, bet_dates):
    data = []
    columns_sql = ""
    conditions = get_conditions(filters)

    for period in bet_dates:
        columns_sql += f"""
			, SUM(IF(log.date  BETWEEN date('{period[0]}') AND date('{period[1]}'), 1, NULL)) as `{period[2]}`
		"""

    columns_sql += f"""
				, SUM(1) as total_visits
		"""

    sql = f"""
		select 
		 emp.name as employee 
		, emp.branch 
		, emp.department 
		, emp.designation 
		 {columns_sql}
		from `tabVisit Form` log 
		inner join tabEmployee emp on emp.name = log.employee_name  
		where log.approved = 1  and log.docstatus =1 
		and (
            (log.date   BETWEEN date('{bet_dates[0][0]}') and date('{bet_dates[-1][1]}'))
            or (log.to_date   BETWEEN date('{bet_dates[0][0]}') and date('{bet_dates[-1][1]}'))
            )   
				{conditions}
		group by emp.name
		order by emp.name asc

	"""
    # frappe.msgprint(sql)
    # return []
    result = frappe.db.sql(sql, as_dict=1) or []
    return result


@frappe.whitelist(allow_guest=True)
def get_period_date_ranges(period, year_start_date, year_end_date):
    from dateutil.relativedelta import relativedelta
    year_start_date = parse(year_start_date).date()
    year_end_date = parse(year_end_date).date()
    if (year_start_date >= year_end_date):
        frappe.throw(_("From Date Must be before To Date"))
    # if not year_start_date:
    #     year_start_date, year_end_date = frappe.db.get_value(
    #         "Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"]
    #     )

    increment = {"Monthly": 1, "Quarterly": 3,
                 "Half-Yearly": 6, "Yearly": 12}.get(period)

    period_date_ranges = []
    for i in range(1, 13, increment):
        period_end_date = getdate(year_start_date) + \
            relativedelta(months=increment, days=-1)
        if period_end_date > getdate(year_end_date):
            period_end_date = year_end_date
        period_date_ranges.append([year_start_date, period_end_date, get_mon(
            year_start_date), get_mon_b(year_start_date), i])
        year_start_date = period_end_date + relativedelta(days=1)
        if period_end_date >= year_end_date or period_end_date >= datetime.now().date():
            break

    return period_date_ranges


def get_mon(dt):
    return getdate(dt).strftime("%b %y")


def get_mon_b(dt):
    return getdate(dt).strftime("%b %Y")
