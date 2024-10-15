# Copyright (c) 2022, Peter MAged and contributors
# For license information, please see license.txt


from ast import And
import frappe
from frappe import _
from unittest import result
from datetime import *
from time import strftime
from time import gmtime

def execute(filters=None):
    columns, data = [], []
    columns = get_columns()
    data = get_data(filters)
    for d in data:
        if d["actual_start"] and d["actual_end"] :
            m1 = d["actual_start"]
            m1 = datetime.strptime(m1, '%I:%M:%S %p')
            m2 = d["actual_end"]
            m2 = datetime.strptime(m2, '%I:%M:%S %p')
            m3 = d["shift_start"]
            m3 = datetime.strptime(m3, '%I:%M:%S %p')
            m4 = d["shift_end"]
            m4 = datetime.strptime(m4, '%I:%M:%S %p')

            duration = m1-m3
            duration_in_s = duration.total_seconds()  
            if duration_in_s < 0 :
                d["start"] = "-" +str(strftime("%H:%M:%S", gmtime(abs(duration_in_s))))
            else :
                d["start"] = strftime("%H:%M:%S", gmtime(abs(duration_in_s)))

            duration = m2-m4
            duration_in_s = duration.total_seconds()  
            if duration_in_s < 0 :
                d["end"] = "-" +str(strftime("%H:%M:%S", gmtime(abs(duration_in_s))))
            else :
                d["end"] = strftime("%H:%M:%S", gmtime(abs(duration_in_s)))

            shift_hours_s = int(d["shift_hours"]) *60*60
            d["shift_hours"] = strftime("%H:%M:%S", gmtime(abs(shift_hours_s)))

            duration = m2-m1
            duration_in_s = duration.total_seconds() 
            working_hours_s = duration.total_seconds()
            d["working_hours"]= strftime("%H:%M:%S", gmtime(abs(duration_in_s)))
            total_s = shift_hours_s - working_hours_s

            if total_s < 0 :
                d["diff"] = strftime("%H:%M:%S", gmtime(abs(total_s)))
            else :
                d["diff"] = "-" +str(strftime("%H:%M:%S", gmtime(abs(total_s))))


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
            "fieldname": "actual_start",
            "label": _("CHECK IN"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "actual_end",
            "label": _("CHECK OUT"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "start",
            "label": _("Late/Attend"),
            "fieldtype": "Data",
            "width": 120
        },
         {
            "fieldname": "end",
            "label": _("Early/Leave"),
            "fieldtype": "Data",
            "width": 120
        },
         
        {
            "fieldname": "shift_hours",
            "label": _("Shift Hours"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "working_hours",
            "label": _("Actual Hours"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "diff",
            "label": _("Difference Hours"),
            "fieldtype": "Data",
            "width": 120
        },
    ]

    return columns




def get_data(filters):
        conditions = get_employee_filters(filters or {})
        sql = f"""select 
    emp.employee_name,
    log.attendance_date ,
    DAYNAME(log.attendance_date) as day_name,
    (case when log.holiday and log.status = 'On Leave' then "Holiday" ELSE log.status END) as status,
    log.holiday,
    log.leave_type,
    DATE_FORMAT(log.shift_start, '%r') as shift_start ,DATE_FORMAT(log.shift_end, '%r') as shift_end,
    log.attend_time,
    (select 
        CONCAT(CONVERT(ddlog.time,time),SUBSTRING(ddlog.name FROM -3 FOR 3)) 
    from `tabDevice Log` as ddlog 
    where ddlog.employee  = emp.name 
    AND ddlog.date = log.attendance_date 
    AND ddlog.name like "%AM" LIMIT 1) as actual_start ,
    (select 
        CONCAT(CONVERT(ddlog.time,time),SUBSTRING(ddlog.name FROM -3 FOR 3)) 
    from `tabDevice Log` as ddlog 
    where ddlog.employee  = emp.name 
    AND ddlog.date = log.attendance_date 
    AND ddlog.name like "%PM" LIMIT 1) as actual_end ,

    log.less_time,log.late_in,
    TIMESTAMPDIFF(HOUR ,log.shift_start ,log.shift_end) as shift_hours,log.working_hours,
    log.employee,
    emp.company,
    emp.branch,
    emp.grade,
    emp.designation,
    emp.department

    from `tabEmployee` as emp 
        Inner join `tabAttendance` as log 
    ON log.employee  = emp.name 
        
    where log.docstatus = 1 
    {conditions}
    ORDER by emp.name ASC , log.attendance_date asc ;
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