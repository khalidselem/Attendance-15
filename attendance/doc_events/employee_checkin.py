import dateutil
import frappe
import frappe.utils
from frappe.utils.data import getdate, nowdate

def on_change(doc,fun=''):
    calc_attendance_for_employee(doc.employee , doc.time)


def on_trash(doc,fun=''):
    calc_attendance_for_employee(doc.employee , doc.time)


def calc_attendance_for_employee(employee,day_date=None):
    args = {
        "employee" :employee ,
        "day_date" :str(day_date or nowdate()) ,
    }
    frappe.enqueue(async_calc_attendance_for_employee, args=args , queue="default",is_async=0,
        timeout=60000, now=0, job_name=f"Update Employee {employee} Attendance For {day_date}")


def async_calc_attendance_for_employee(args={}):
    employee = args.get("employee")
    day_date = args.get("day_date") or getdate()
    day_date = getdate(day_date)
    
    attendance_calculations = frappe.db.sql_list(f"""
    select name from `tabAttendance Calculation` where date('{day_date}') Between date(payroll_start_date) and date(payroll_end_date)
    """)

   
    for attendance_calculation in attendance_calculations :
        try :
            if attendance_calculation :
                attendance_calculation = frappe.get_doc("Attendance Calculation" , attendance_calculation)
                attendance_calculation.employee = employee
                attendance_calculation.start_date = day_date
                attendance_calculation.end_date = day_date
                attendance_calculation.calculate_attendance(is_save=0 , show_progress=0)
                print("attendance_calculation  " , attendance_calculation.name , "  Done")
                frappe.db.commit()

        except Exception as e :
            error_log = frappe.new_doc("Error Log")
            error_log.title = f"Update Employee {employee} Attendance For {day_date}"
            error_log.error = e
            error_log.save(ignore_permissions=1)