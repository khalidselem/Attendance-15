# Copyright (c) 2022, Peter MAged and contributors
# For license information, please see license.txt

from unittest import result
import frappe
from frappe import _


def execute(filters=None):
    columns, data = [], []
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    columns = [
        {
            "fieldname": "employee",
            "label": _("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 250
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150
        },
        # {
        #     "fieldname": "department",
        #     "label": _("Department"),
        #     "fieldtype": "Link",
        #     "options": "Department",
        #     "width": 120
        # },
        # {
        #     "fieldname": "grade",
        #     "label": _("Grade"),
        #     "fieldtype": "Link",
        #     "options": "Employee Grade",
        #     "width": 120
        # },
        # {
        #     "fieldname": "branch",
        #     "label": _("Branch"),
        #     "fieldtype": "Link",
        #     "options": "Branch",
        #     "width": 120
        # },
        # {
        #     "fieldname": "designation",
        #     "label": _("Designation"),
        #     "fieldtype": "Link",
        #     "options": "Designation",
        #     "width": 120
        # },

        {
            "fieldname": "attendance_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "day_name",
            "label": _("Day"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "shift_start",
            "label": _("Shift Start"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "shift_end",
            "label": _("Shift End"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "attend_time",
            "label": _("Check IN"),
            "fieldtype": "Data",
            "width": 120
        },
        
        {
            "fieldname": "leave_time",
            "label": _("Check OUT"),
            "fieldtype": "Data",
            "width": 120
        },
        
        {
            "fieldname": "fingerprint_type",
            "label": _("Forget Fingerprint"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "late_in",
            "label": _("Late"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "less_time",
            "label": _("Less"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "overtime",
            "label": _("Overtime"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "leave_type",
            "label": _("Leave Type"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "shift_hours",
            "label": _("Shift Hours"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "working_hours",
            "label": _("Actual Hours"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "leave_application",
            "label": _("Leave"),
            "fieldtype": "Link",
            "options":"Leave Application",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "overtime_request",
            "label": _("Overtime Request"),
            "fieldtype": "Link",
            "options":"Daily Overtime request",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "permission",
            "label": _("Permission"),
            "fieldtype": "Link",
            "options":"Permission Application",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "permission",
            "label": _("Permission"),
            "fieldtype": "Link",
            "options":"Permission Application",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "visit_form",
            "label": _("Visit"),
            "fieldtype": "Link",
            "options":"Visit Form",
            "precision": 2,
            "width": 120
        },
        {
            "fieldname": "visit_type",
            "label": _("Visit Type"),
            "fieldtype": "Link",
            "options":"Visit Type",
            "precision": 2,
            "width": 120
        },

    ]

    return columns


def get_data(filters):
	conditions = get_employee_filters(filters or {})
	sql = f"""
				select 
						emp.employee_name,
						log.attendance_date ,
						DAYNAME(log.attendance_date) as day_name,
						(case when log.holiday and log.status = 'On Leave' then "Holiday" ELSE log.status END) as status,
						log.holiday,
						log.leave_type,
						log.shift_start,log.shift_end,
                        (case when forget_fingerprint = 1 and fingerprint_type = "IN" then '' else log.attend_time end ) as attend_time ,
                        (case when forget_fingerprint = 1 and fingerprint_type = "OUT" then '' else log.leave_time end ) as leave_time ,
						# log.attend_time,
                        # log.leave_time,
                        forget_fingerprint,
                        fingerprint_type,
						log.less_time,log.late_in,log.overtime,
						log.shift_hours as shift_hours,
                        log.working_hours,
                        log.working_hours,
                        log.leave_application,
                        log.permission,
                        log.visit_form,
                        visit.visit_type,
                        log.overtime_request,
						log.employee,
						emp.company,
						emp.branch,
						emp.grade,
						emp.designation,
						emp.department

				from tabEmployee emp 
				Inner join tabAttendance  log on log.employee  = emp.name 
				left join `tabVisit Form` visit on log.visit_form  = visit.name 
				where log.docstatus = 1 
				{conditions}
				ORDER by emp.name ASC , log.attendance_date asc

	"""
	# frappe.throw(sql)
	result = frappe.db.sql(sql,as_dict=1)
	data = result
	return data

def get_employee_filters(filters):
    from_date, to_date = filters.get('from_date'), filters.get('to_date')

    conditions = f" and log.attendance_date Between date('{from_date}') And date('{to_date}') "
    data = filters.get("company")
    if data:
        conditions += f" and emp.company = '{data}' "

    data = filters.get("employee")
    if data:
        conditions += f" and emp.name = '{data}' "

    data = filters.get("branch")
    if data:
        conditions += f" and emp.branch = '{data}' "
    data = filters.get("grade")
    if data:
        conditions += f" and emp.grade = '{data}' "
    data = filters.get("designation")
    if data:
        conditions += f" and emp.designation = '{data}' "
    data = filters.get("department")
    if data:
        conditions += f" and emp.department = '{data}' "
    return conditions
