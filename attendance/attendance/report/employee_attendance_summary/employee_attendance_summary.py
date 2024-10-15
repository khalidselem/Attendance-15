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
            "fieldname": "total_present",
            "label": _("Present"),
            "fieldtype": "Float",
            "precision":2,
            "width": 90
        },
        
        {
            "fieldname": "total_absent",
            "label": _("Absent"),
            "fieldtype": "Float",
            "precision":2,
            "width": 90
        },
        
        {
            "fieldname": "total_wfh",
            "label": _("WFH"),
            "fieldtype": "Float",
            "precision":2,
            "width": 90
        },
        
        {
            "fieldname": "total_leave",
            "label": _("Leaves"),
            "fieldtype": "Float",
            "precision":2,
            "width": 90
        },
        
        {
            "fieldname": "shift_hours",
            "label": _("Target Hours"),
            "fieldtype": "Float",
            "precision":2,
            "width": 110
        },
        
        {
            "fieldname": "working_hours",
            "label": _("Working Hours"),
            "fieldtype": "Float",
            "precision":2,
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
            "precision":2,
            "width": 120
        },
        {
            "fieldname": "fingerprint",
            "label": _("Forget Fingerprint"),
            "fieldtype": "Float",
            "precision":2,
            "width": 150
        },
        {
            "fieldname": "permissions",
            "label": _("Permissions"),
            "fieldtype": "Float",
            "precision":2,
            "width": 120
        },

    ]

    return columns


def get_data(filters):
	conditions = get_employee_filters(filters or {})
	sql = f"""
			select 
					sum(case when log.holiday = 1 and log.status = 'On Leave' then 1 ELSE 0 END) as total_holiday,
						
					sum(case when  log.status = 'Absent' then 1 ELSE 0 END) as total_absent,
					
					sum(case when  log.status = 'Work From Home' then 1 ELSE 0 END) as total_wfh,
					
					sum(case when log.holiday <> 1 and log.status = 'On Leave'   then 1
					when log.holiday <> 1 and log.status = 'Half Day'   then 0.5
					ELSE 0 END) as total_leave,
					
					sum(case when log.status = 'Present'   then 1
					when log.status = 'Half Day'   then 0.5
					ELSE 0 END) as total_present,
					
					
					SUM(ifnull(log.shift_hours,0)) as shift_hours,
					
     				sum(log.working_hours) as working_hours,
					
					                    
					ifnull(sec_to_time(SUM(time_to_sec(log.less_time))),SEC_TO_TIME(0) ) as less_time,
					ifnull(sec_to_time(SUM(time_to_sec(log.late_in))),SEC_TO_TIME(0) ) as late_in,
					ifnull(sec_to_time(SUM(time_to_sec(log.overtime))),SEC_TO_TIME(0) ) as overtime,
								
					ifnull(sec_to_time(SUM(ifnull(log.overtime_factor*60,0))),SEC_TO_TIME(0) ) as overtime_factor,
					ifnull(sec_to_time(SUM(ifnull(log.late_factor*60,0))),SEC_TO_TIME(0) ) as late_factor,
					ifnull(sec_to_time(SUM(ifnull(log.less_time_factor*60,0))),SEC_TO_TIME(0) ) as less_time_factor,
								
						
					 SUM(CASE when ifnull(log.permission,'') <> '' then 1 else 0 END) as permissions ,
					 SUM(ifnull(log.forget_fingerprint,0)) as fingerprint ,
					 SUM(case when log.forget_fingerprint <> 0 then log.fingerprint_factor else 0 end) as fingerprint_factor ,
					
						
						
					log.employee,
					emp.employee_name,
					emp.company,
					emp.branch,
					emp.grade,
					emp.designation,
					emp.department

			from tabEmployee emp 
			Inner join tabAttendance  log on log.employee  = emp.name 
			where log.docstatus = 1 
			{conditions}
			GROUP by emp.name  			
			ORDER by emp.name ASC 

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
