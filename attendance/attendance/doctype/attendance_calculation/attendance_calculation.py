# Copyright (c) 2021, Peter Maged and contributors
# For license information, please see license.txt

# import frappe
from babel.dates import format_date
import dateutil
from erpnext.setup.doctype.holiday_list.holiday_list import HolidayList
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on, is_lwp
import frappe
from frappe import _, has_permission, msgprint, new_doc
from frappe.model.document import Document
from dateutil.parser import parse
# from frappe.query_builder.utils import DocType
from frappe.sessions import get
from frappe.utils import to_timedelta, add_days, nowdate, get_link_to_form
# from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee, is_holiday
from datetime import datetime, timedelta, date, time
# from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure
from frappe.utils.data import flt, getdate
# from pandas.core.tools.datetimes import to_time

whitelisted_globals = {
    "int": int,
    "float": float,
    "long": int,
    "round": round,
    "date": datetime.date,
    "getdate": getdate
}


class AttendanceCalculation(Document):
    def __init__(self, *args, **kwargs):
        super(AttendanceCalculation, self).__init__(*args, **kwargs)

    @frappe.whitelist()
    def validate(self):
        self.validate_dates()

    @frappe.whitelist()
    def validate_dates(self):
        self.start_date = parse(str(self.start_date)).date()
        self.end_date = parse(str(self.end_date)).date()
        self.payroll_start_date = parse(str(self.payroll_start_date)).date()
        self.payroll_end_date = parse(str(self.payroll_end_date)).date()

        if not (self.payroll_start_date <= self.start_date <= self.payroll_end_date):
            frappe.throw(_("Start Date is Not in Payroll Period Date Range"))

        if not (self.payroll_start_date <= self.end_date <= self.payroll_end_date):
            frappe.throw(_("End Date is Not in Payroll Period Date Range"))

    @frappe.whitelist()
    def calculate_attendance(self , is_save = 1 , show_progress = 1):
        
        if is_save :
            self.save()
            
        self.start_date = parse(str(self.start_date)).date()
        self.end_date = parse(str(self.end_date)).date()
        self.payroll_start_date = parse(str(self.payroll_start_date)).date()
        self.payroll_end_date = parse(str(self.payroll_end_date)).date()
        employee_filters = self.get_employees_filters()
        self.employees = frappe.db.sql_list(f"""
										select emp.name from tabEmployee emp where 1=1
										{employee_filters}
										""")
        frappe.db.sql(f"""
					delete from tabAttendance where attendance_calculation = '{self.name}' 
					and attendance_date BETWEEN date('{self.start_date}') and date('{self.end_date}') 
					and employee in (
						select name from tabEmployee emp where 1=1
										{employee_filters}
					)
					""")
        frappe.db.commit()
        self.employees_logs = frappe.db.sql(f"""
			select log.employee , time(log.time) as time ,log.time as log_time
			, date(log.time) as day , log.log_type , 
            '' as for_date
			from `tabEmployee Checkin` log
			inner join tabEmployee emp on emp.name = log.employee
			where date(log.time)  
			BETWEEN DATE_SUB(date('{self.start_date}'), interval 1 DAY ) 
			and DATE_SUB(date('{self.end_date}'), interval -1 DAY )
										{employee_filters}
			order by employee asc , log.time asc
										""", as_dict=1) or []
        self.permissions = frappe.db.sql(f"""       
					select permission.name , permission.permission_type 
					, permission.employee , permission.day , permission.total_minutes 
					, permission.from_time , permission.to_time
					from `tabPermission Application` permission
					inner join tabEmployee emp on permission.employee = emp.name
					where permission.docstatus = 1 and permission.status='Approved' 
					and permission.day BETWEEN  date('{self.start_date}')  and date('{self.end_date}')  
										{employee_filters}
										""", as_dict=1) or []
        self.leaves = frappe.db.sql(f"""       
					select  application.name , application.employee , application.from_date , application.half_day 
				, ifnull(application.half_day_date,application.from_date) as half_day_date , application.half_day_type 
					, application.to_date ,application.leave_type from `tabLeave Application` application
					inner join tabEmployee emp on application.employee = emp.name
					where application.docstatus = 1 and application.status='Approved'
					and (
                            (application.from_date BETWEEN  date('{self.start_date}')  and date('{self.end_date}') )  
					    or  (application.to_date BETWEEN  date('{self.start_date}')  and date('{self.end_date}') ) 
					    or  (date('{self.start_date}') BETWEEN  date(application.from_date)  and date(application.to_date) ) 
					    or  (date('{self.end_date}') BETWEEN  date(application.from_date)  and date(application.to_date) ) 
                        )  
										{employee_filters}
										""", as_dict=1) or []
        # count =1
        self.overtime_requests = frappe.db.sql(f"""
			select log.name , log.employee_id as employee , log.date , log.time_from, log.time_to 
			, log.office , log.outside from `tabDaily Overtime Request` log 
			inner join tabEmployee emp on emp.name = log.employee_id  
			where log.approved = 1 and log.docstatus =1 
			and log.date   BETWEEN date('{self.start_date}') and date('{self.end_date}')   
							{employee_filters}
			
			order by log.employee_id asc  
											""", as_dict=1) or []
        self.visits = frappe.db.sql(f"""
			select log.name , log.employee_name as employee , log.date , log.to_date , log.from_time , log.to_time
			from `tabVisit Form` log 
			inner join tabEmployee emp on emp.name = log.employee_name  
			where log.approved = 1  and log.docstatus =1 
			# and log.date   BETWEEN date('{self.start_date}') and date('{self.end_date}')  
			and ((log.date BETWEEN  date('{self.start_date}')  and date('{self.end_date}') )  
			or  (log.to_date BETWEEN  date('{self.start_date}')  and date('{self.end_date}') ) ) 
							{employee_filters}

			order by log.employee_name asc  
											""", as_dict=1) or []

        self.attendance_requests = frappe.db.sql(f"""
					select log.* from `tabAttendance Request` log
					inner join tabEmployee emp on emp.name = log.employee
					where log.docstatus = 1  {employee_filters}
					
					and (log.from_date between date('{self.start_date}') and date('{self.end_date}') 
						or log.to_date between date('{self.start_date}') and date('{self.end_date}') 
						or (log.from_date < date('{self.start_date}') and log.to_date > date('{self.end_date}')))
					order by log.employee asc


							
				
											""", as_dict=1) or []
        for emp in self.employees:
            # frappe.publish_progress(count*100/len(self.employees), title = _("Submitting Salary Slips..."))
            self.calculate(emp , show_progress)
            # count += 1

    def calculate(self, emp , show_progress = 1):
        day = self.start_date
        employee = frappe.get_doc("Employee", emp)
        count = self.employees.index(emp) + 1
        total = len(self.employees)
        attendance_rule = frappe.get_doc(
            "Attendance Rule", employee.attendance_rule)
        while day <= self.end_date:
            if show_progress :
                frappe.publish_realtime("attendance_calculation_progress",
                                        frappe._dict({
                                            "count": count,
                                            "total": total,
                                            "message": employee.employee_name + "  " + _("for Day") + "  " + str(day)+"    " + _(f"Calculate {count}/{total} employees"),
                                            "title": _("Attendance Calculation ..."),

                                        }), user=frappe.session.user)
            # frappe.publish_progress(count*100/len(self.employees), title =
            # _("Attendance Calculation ..."))
            try:
                # if 1 :
                self.calculate_day(employee, day, attendance_rule)
            except Exception as e:
                error_title = f"Error While Calculate Attendance for Employee {employee.employee_name} at day {day}"
                error_message = frappe.get_traceback()
                frappe.log_error(title = error_title , message=error_message)
                frappe.msgprint(
                    _(f"Error While Calculate Attendance for Employee {employee.employee_name} at day {day} <br/>{e}"), indicator='red')
            day = add_days(day, 1)

    #    {
    # 		'shift_type': shift_type,
    # 		'start_datetime': start_datetime,
    # 		'end_datetime': end_datetime,
    # 		'actual_start': actual_start,
    # 		'actual_end': actual_end
    # 	}
    def calculate_day(self, employee, day, attendance_rule):
        
        if getdate(day) < getdate(employee.date_of_joining):
            return
        
        if employee.relieving_date:
            if getdate(day) > getdate(employee.relieving_date):
                return
        
        doc = self.get_attendance(employee.name, day)
        shift = get_employee_shift(
            employee=employee.name, for_date=day, consider_default_shift=True)
        # frappe.msgprint(str(shift))
        if not shift:
            frappe.throw(
                _(f"Please Assign Shift to Employee {employee.employee_name} for day {day}"))
        holiday = is_holiday(employee=employee.name, date=day)
        doc.holiday = holiday
        # frappe.msgprint( shift.shift_type.name)
        doc.employee = employee.name
        doc.employee_doc = employee
        doc.attendance_rule = attendance_rule
        doc.attendance_calculation = self.name
        doc.attendance_date = day
        doc.shift = shift.shift_type.name
        doc.shift_start = shift.shift_type.start_time
        doc.shift_end = shift.shift_type.end_time
        doc.early_out = timedelta(minutes=0)
        doc.early_in = timedelta(minutes=0)
        doc.late_in = timedelta(minutes=0)
        doc.attend_time = timedelta(minutes=0)
        doc.leave_time = timedelta(minutes=0)
        doc.overtime = timedelta(minutes=0)
        doc.late = timedelta(minutes=0)
        doc.less_time = timedelta(minutes=0)
        doc.less_time_factor = timedelta(minutes=0)
        doc.late_out = timedelta(minutes=0)
        doc.visit_factor = 0
        doc.fingerprint_factor = 0
        doc.shift_hours = 0
        doc.has_shift_bonus = 0
        doc.has_visit_bonus = 0
        doc.half_day_type = ""
        doc.overtime_requests = [
            x for x in self.overtime_requests if x.date == day and x.employee == doc.employee]
        doc.visits = [x for x in self.visits if x.date <= day <= x.to_date
                     and x.employee == doc.employee]
        doc.logs = [x for x in self.employees_logs if shift.actual_start <=
                    x.log_time <= shift.actual_end and x.employee == doc.employee and not x.for_date]
        for log in doc.logs :
            log.for_date = doc.attendance_date
        # print("Employee logs ====> " , self.employees_logs)
        # print ("attendance_requests ==========================================================================> " , self.attendance_requests)
        # frappe.msgprint(str(doc.attendance_date))
        doc.attendance_requests = [x for x in self.attendance_requests if x.from_date <=
                                   doc.attendance_date <= x.to_date and x.employee == doc.employee]
        doc.has_request = 1 if len(doc.attendance_requests) > 0 else 0
        # doc.logs = [x for x in self.employees_logs if  x.day == doc.attendance_date and x.employee == doc.employee]
        # print ("doc.logs => " , doc.logs)
        # frappe.msgprint(str(doc.attendance_date))
        # for log in doc.logs  :
        # datetime.combine(shift.actual_start.date() , time())
        doc.shift_start_datetime = shift.start_datetime
        # datetime.combine(shift.actual_end.date() , time())
        doc.shift_end_datetime = shift.end_datetime
        # doc.shift_hours = (doc.shift_end_datetime - doc.shift_start_datetime).seconds /3600
        # 	frappe.msgprint(str(log.log_time))
        # doc.attend_datetime =
        doc.permissions = [
            x for x in self.permissions if x.day == day and x.employee == doc.employee]
        doc.leaves = [x for x in self.leaves if x.from_date <=
                      day <= x.to_date and x.employee == doc.employee]
        doc.has_logs = 1 if len(doc.logs) > 0 else 0
        doc.has_leaves = 1 if len(doc.leaves) > 0 else 0
        doc.has_permissions = 1 if len(doc.permissions) > 0 else 0
        doc.has_overtime = 1 if len(doc.overtime_requests) > 0 else 0
        doc.has_visit = 1 if len(doc.visits) > 0 else 0

        if not doc.has_logs and not doc.has_leaves and not doc.holiday and not doc.has_overtime and not doc.has_visit and not doc.has_request:
            # Absent
            doc = self.Absent(doc)
        else:

            if doc.has_leaves:
                # leave Case
                half_day_leave = [
                    x for x in doc.leaves if x.half_day_date == doc.attendance_date and x.half_day]
                if len(half_day_leave) == 0:
                    # Normal Leave
                    doc = self.onLeave(doc, doc.leaves)
                else:
                    if not doc.has_logs and not doc.has_overtime:
                        # leave without any log
                        doc = self.Absent(doc)
                    else:
                        # Present Half Day
                        doc = self.HalfDay(doc, half_day_leave)
            else:
                if doc.holiday and not doc.has_logs and not doc.has_overtime and not doc.has_visit:
                    # Holiday
                    doc = self.Holiday(doc)
                elif doc.has_logs or doc.has_overtime or doc.has_visit or doc.has_request or doc.has_visit:
                    # Normal Day or Working in Holiday
                    doc = self.Present(doc)
                elif doc.has_visit:
                    pass
        # doc.save()
        doc.submit()

    def Absent(self, doc):
        doc.status = "Absent"
        doc.shift_hours = (doc.shift_end_datetime -
                           doc.shift_start_datetime).seconds / 3600
        return doc

    def Present(self, doc):
        doc.status = "Present"
        return self.calculate_in_out(doc)

    # def attendance_request (self,doc):
    # 	attendance_request = doc.attendance_requests[0]
    # 	doc.status =  "Present" if attendance_request.reason != "Work From Home" else attendance_request.reason
    # 	doc.attendance_request = attendance_request.name
    # 	# doc.status = "Present"
    # 	return self.calculate_in_out(doc)

    def HalfDay(self, doc, leaves):
        doc.status = "Half Day"
        doc.leave_application = leaves[0].name
        doc.leave_type = leaves[0].leave_type
        doc.half_day_type = leaves[0].half_day_type or "Morning"
        # frappe.msgprint("Leaves")
        # frappe.msgprint(doc.leave_application)
        return self.calculate_in_out(doc)

    def onLeave(self, doc, leaves):
        doc.status = "On Leave"
        doc.leave_application = leaves[0].name
        doc.leave_type = leaves[0].leave_type
        doc.shift_hours = (doc.shift_end_datetime -
                           doc.shift_start_datetime).seconds / 3600
        return doc

    def Holiday(self, doc):
        doc.status = "On Leave"
        return doc

    def calculate_in_out(self, doc):
        # doc.has_logs or doc.has_overtime or  doc.has_visit
        half_day = (doc.status == "Half Day")
        doc.daily_target_hour = doc.attendance_rule and doc.attendance_rule.working_type in [
            "Daily Target Hour"]
        if doc.has_logs:
            # doc.attend_time,doc.leave_time = doc.logs[0].time , doc.logs[-1].time
            doc.actual_start_datetime, doc.actual_end_datetime = doc.logs[
                0].log_time, doc.logs[-1].log_time
            if doc.has_visit:
                in_times = [datetime.combine(doc.attendance_date, to_time(str(x.from_time))) for x in (
                    doc.visits or []) if x.from_time] + [doc.actual_start_datetime]

                out_times = [datetime.combine(doc.attendance_date, to_time(str(x.to_time))) for x in (
                    doc.visits or []) if x.to_time]  + [doc.actual_end_datetime]
                doc.actual_start_datetime, doc.actual_end_datetime = min(
                    in_times), max(out_times)

        elif doc.has_request:
            attendance_request = doc.attendance_requests[0]
            doc.status = "Present" if attendance_request.reason != "Work From Home" else attendance_request.reason
            doc.attendance_request = attendance_request.name
            # frappe.msgprint(str(doc.attendance_request))
            doc.actual_start_datetime, doc.actual_end_datetime = datetime.combine(doc.attendance_date, to_time(str(
                attendance_request.start_time))), datetime.combine(doc.attendance_date, to_time(str(attendance_request.end_time)))
            half_day = half_day or (
                attendance_request.half_day_date == doc.attendance_date)
        elif doc.has_visit:
            # doc.attend_time,doc.leave_time = doc.shift_start , doc.shift_end
            in_times = [datetime.combine(doc.attendance_date, to_time(str(x.from_time))) for x in (
                doc.visits or []) if x.from_time]

            out_times = [datetime.combine(doc.attendance_date, to_time(str(x.to_time))) for x in (
                doc.visits or []) if x.to_time]

            # frappe.msgprint(str(out_times))
            # frappe.msgprint(str(in_times))
            doc.actual_start_datetime, doc.actual_end_datetime = min(
                in_times), max(out_times)

        elif doc.has_overtime:
            overtime_request = doc.overtime_requests[-1]
            doc.overtime_request = overtime_request.name
            doc.actual_start_datetime, doc.actual_end_datetime = datetime.combine(overtime_request.date, to_time(str(
                overtime_request.time_from))), datetime.combine(overtime_request.date, to_time(str(overtime_request.time_to)))

        if doc.has_visit:
            doc.visit_form = doc.visits[-1].name
            if doc.attendance_rule.enable_site_visit:
                doc.visit_factor = doc.attendance_rule.visit_factor_in_holiday if doc.holiday else doc.attendance_rule.visit_factor_in_normal_day

        # elif doc.has_overtime :
        # 		doc.attend_time,doc.leave_time = to_timedelta(str(doc.overtime_requests [-1].time_from)) , to_timedelta(str(doc.overtime_requests [-1].time_to))
        # doc.actual_start = datetime.combine(doc.actual_start , doc.leave_time)
        # doc.actual_end = datetime.combine(doc.actual_end , doc.attend_time)
        permission_in_minutes = sum(
            [x.total_minutes for x in doc.permissions if x.permission_type == 'Late in']) or 0
        permission_out_minutes = sum(
            [x.total_minutes for x in doc.permissions if x.permission_type == 'Early Out']) or 0
        if doc.permissions and len(doc.permissions) > 0:
            doc.permission = doc.permissions[-1].name
        if doc.actual_start_datetime == doc.actual_end_datetime:
            doc = self.forget_fingerpenalty(doc)
        doc.attend_time, doc.leave_time = doc.actual_start_datetime.time(
        ), doc.actual_end_datetime.time()

        doc.working_hours = (doc.actual_end_datetime -
                             doc.actual_start_datetime).seconds / 3600
        if doc.daily_target_hour:
            doc.shift_hours = doc.attendance_rule.working_hours_per_day  # in Hours
        else:
            doc.shift_hours = (doc.shift_end_datetime -
                               doc.shift_start_datetime).seconds / 3600  # in Hours

        doc.early_in = doc.shift_start_datetime - doc.actual_start_datetime
        doc.late_in = doc.actual_start_datetime - doc.shift_start_datetime - \
            timedelta(minutes=permission_in_minutes)
        doc.early_out = doc.shift_end_datetime - doc.actual_end_datetime - \
            timedelta(minutes=permission_out_minutes)

        doc.late_out = doc.actual_end_datetime - doc.shift_end_datetime

        # if doc.status == "Half Day" :
        if half_day:
            doc.shift_hours /= 2
            half_day_minutes = doc.shift_hours * 60
            if doc.late_in >= timedelta(minutes=0) and doc.half_day_type == "Morning":
                doc.late_in -= timedelta(minutes=half_day_minutes)
            if doc.early_out >= timedelta(minutes=0) and doc.half_day_type == "Evening":
                doc.early_out -= timedelta(minutes=half_day_minutes)

        # Daily Target Hour
        if doc.daily_target_hour:
            # Daily Target Hour Lates
            doc.late_in = timedelta(minutes=0)

            # Daily Target Hour Less
            if doc.shift_hours > doc.working_hours:
                doc.early_out = timedelta(
                    hours=doc.shift_hours) - timedelta(hours=doc.working_hours)
            else:
                doc.early_out = timedelta(minutes=0)

        if doc.early_in <= timedelta(minutes=0):
            doc.early_in = timedelta(minutes=0)

        if doc.late_in <= timedelta(minutes=0):
            doc.late_in = timedelta(minutes=0)

        if doc.early_out <= timedelta(minutes=0):
            doc.early_out = timedelta(minutes=0)

        if doc.late_out <= timedelta(minutes=0):
            doc.late_out = timedelta(minutes=0)

        if doc.holiday:
            doc.late_in = timedelta(minutes=0)
            doc.early_out = timedelta(minutes=0)

        doc.late = doc.late_in

        if doc.has_overtime:
            doc.overtime_request = doc.overtime_requests[-1].name
            for row in doc.overtime_requests:
                doc.overtime += to_timedelta(str(row.time_to)) - \
                    to_timedelta(str(row.time_from))
            # if not doc.holiday :
            # 	doc.overtime = to_timedelta(str(doc.overtime_requests[-1].time_to)) - doc.shift_end
            # else :
            # 	doc.overtime = to_timedelta(str(doc.overtime_requests[-1].time_to)) - to_timedelta(str(doc.overtime_requests[-1].time_from))
        else:
            if not (doc.attendance_rule and doc.attendance_rule.overtime_depend_on_requests_only):
                if doc.holiday:
                    doc.overtime = timedelta(hours=doc.working_hours)
                elif doc.daily_target_hour:

                    # Daily Target Hour Less
                    if doc.shift_hours < doc.working_hours:
                        doc.overtime = timedelta(
                            hours=doc.working_hours) - timedelta(hours=doc.shift_hours)
                    else:
                        doc.overtime = timedelta(minutes=0)

                else:
                    doc.overtime = doc.late_out

                # if not doc.holiday:
                # 	doc.overtime = doc.late_out
                # else:
                # 	doc.overtime = timedelta(hours=doc.working_hours)

        
        # deduct break from overtime
        if doc.holiday and doc.attendance_rule.deduct_break_from_overtime and doc.attendance_rule.break_start and doc.attendance_rule.break_end :
            break_start = to_time(str(doc.attendance_rule.break_start))
            break_start = datetime.combine(doc.attendance_date,break_start)
            break_end = to_time(str(doc.attendance_rule.break_end))
            break_end = datetime.combine(doc.attendance_date,break_end)
            
            break_mins = min(doc.actual_end_datetime , break_end) - max(doc.actual_start_datetime , break_start)
            break_mins = max(break_mins , timedelta(minutes=0)).seconds/60

            doc.overtime -= timedelta(minutes=flt(break_mins))
        
        
        if doc.overtime <= timedelta(minutes=0):
            doc.overtime = timedelta(minutes=0)
        doc.less_time = doc.early_out

        if doc.late > timedelta(minutes=0):
            doc = self.calculate_late(doc)
            doc = self.calculate_late_penalty(doc)

        if doc.overtime > timedelta(minutes=0):
            doc = self.calculate_overtime(doc)
        if doc.less_time >= timedelta(minutes=0):

            doc = self.calculate_less_time(doc)
            doc = self.calculate_less_time_penalty(doc)

        doc = self.calculate_shift_bonus(doc)
        doc = self.calculate_visit_bonus(doc)
        return doc

    def calculate_overtime(self, doc):
        if doc.attendance_rule.working_type in ["Monthly Target Hour"]:
            return doc
        if doc.overtime > timedelta(minutes=0) and doc.attendance_rule.enable_overtime:

            overtime_factor = 0
            if not doc.holiday:
                overtime_minutes = (doc.overtime.seconds / 60) if doc.attendance_rule.overtime_maximum_per_day >= (
                    doc.overtime.seconds / 3600) else doc.attendance_rule.overtime_maximum_per_day * 60
                doc.early_exit = 0
                if doc.attendance_rule.enable_overtime_morining_evening and doc.attendance_rule.morining_overtime_start and doc.attendance_rule.evening_overtime_start :
                    morining_overtime_start = to_timedelta(str(doc.attendance_rule.morining_overtime_start))
                    evening_overtime_start = to_timedelta(str(doc.attendance_rule.evening_overtime_start))
                    overtime_start = to_timedelta(str(doc.shift_end_datetime.time()))
                    overtime_end = overtime_start + timedelta(minutes=overtime_minutes)
                    morining_overtime   = min(evening_overtime_start , overtime_end) - max(overtime_start , morining_overtime_start)
                    morining_overtime   = (morining_overtime.seconds / 60)
                    evening_overtime    = overtime_minutes - morining_overtime 

                    overtime_factor     = (morining_overtime * (doc.attendance_rule.morining_overtime_factor or 0)) + (evening_overtime * (doc.attendance_rule.evening_overtime_factor or 0))

                    print("doc.overtime ===> " , doc.overtime)
                    print("overtime_minutes ===> " , overtime_minutes)
                    print("morining_overtime ===> " , morining_overtime)
                    print("evening_overtime ===> " , evening_overtime)
                    print("overtime_factor ===> " , overtime_factor)


                else :
                    for row in doc.attendance_rule.overtime_rules:
                        if row.from_min <= overtime_minutes <= row.to_min:
                            overtime_factor = row.factor * overtime_minutes
            else:
                overtime_factor = ((doc.overtime.seconds / 60)
                                   * doc.attendance_rule.overtime_holiday_factor)
            doc.overtime_factor = overtime_factor

        return doc

    def calculate_late(self, doc):
        if doc.attendance_rule.working_type in ["Monthly Target Hour"]:
            return doc
        if doc.late > timedelta(minutes=0) and doc.attendance_rule.enable_late_rule:
            late_factor = 0
            late_minutes = doc.late.seconds / 60
            doc.late_entry = 1
            for row in doc.attendance_rule.late_rules:
                if row.from_min <= late_minutes <= row.to_min:
                    late_factor = row.factor
            doc.late_factor = late_factor * late_minutes

        return doc

    def calculate_shift_bonus(self, doc):
        if doc.shift and doc.attendance_rule.enable_shift_bonus:
            shift_bonus = 0
            doc.has_shift_bonus = 1
            for row in doc.attendance_rule.shift_bonus_rule:
                if row.shift_type == doc.shift:
                    shift_bonus = row.amount
            doc.shift_bonus = shift_bonus
            doc.has_shift_bonus = 1 if shift_bonus else 0
        return doc

    def calculate_visit_bonus(self, doc):
        if doc.visit_form and doc.attendance_rule.enable_visit_bonus:
            visit_type = frappe.db.get_value(
                "Visit Form", doc.visit_form, "visit_type")
            if visit_type:
                visit_bonus = 0
                doc.has_visit_bonus = 1
                for row in doc.attendance_rule.visit_bonus_rule:
                    if visit_type == row.visit_type:
                        visit_bonus = row.amount
                doc.visit_bonus = visit_bonus
                doc.has_visit_bonus = 1 if visit_bonus else 0
        return doc

    def calculate_late_penalty(self, doc):
        if doc.attendance_rule.working_type in ["Monthly Target Hour"]:
            return doc
        if doc.late > timedelta(minutes=0) and doc.attendance_rule.enable_late_penalty:
            late_penalty_factor = 0
            late_minutes = doc.late.seconds / 60

            doc.late_entry = 1
            for row in doc.attendance_rule.late_penalty_rules:
                if row.from_min <= late_minutes <= row.to_min:
                    late_penalty_factor = row.factor
                    if row.penalty_type:
                        doc.late_penalty_type = row.penalty_type
            doc.late_penalty_factor = late_penalty_factor * 60

        return doc

    def calculate_less_time_penalty(self, doc):
        if doc.attendance_rule.working_type in ["Monthly Target Hour"]:
            return doc

        if doc.less_time > timedelta(minutes=0) and doc.attendance_rule.enable_less_time_penalty:
            doc.early_exit = 1
            less_minutes = doc.less_time.seconds / 60
            for row in (doc.attendance_rule.less_time_penalties or []):
                if row.from_min <= less_minutes <= row.to_min:
                    if row.penalty_type:
                        doc.less_penalty_type = row.penalty_type

        return doc

    def calculate_less_time(self, doc):
        if doc.attendance_rule.working_type in ["Monthly Target Hour"]:
            return doc
        doc.early_exit = 1
        if doc.less_time > timedelta(minutes=0) and doc.attendance_rule.less_time:
            less_time_factor = doc.attendance_rule.less_time_factor
            less_time_minutes = doc.less_time.seconds / 60

            doc.less_time_factor = less_time_factor * less_time_minutes

        return doc

    def forget_fingerpenalty(self, doc):
        if doc.actual_start_datetime == doc.actual_end_datetime and not doc.holiday:
            doc.forget_fingerprint = 1 and not doc.has_visit
            in_minutes = abs((doc.actual_start_datetime -
                              doc.shift_start_datetime)).seconds / 60
            out_minutes = abs(
                (doc.actual_end_datetime - doc.shift_end_datetime)).seconds / 60
            if in_minutes < out_minutes:
                doc.fingerprint_type = 'OUT'
                doc.actual_end_datetime = doc.shift_end_datetime
                doc.fingerprint_factor = doc.attendance_rule.fingerprint_penalty_factor_out
            else:
                doc.fingerprint_type = 'IN'
                doc.actual_start_datetime = doc.shift_start_datetime
                doc.fingerprint_factor = doc.attendance_rule.fingerprint_penalty_factor
            if doc.has_visit:
                doc.fingerprint_type = ''

        return doc

    def get_attendance(self, employee, day):
        return frappe.new_doc("Attendance")
        exist = frappe.db.get_value("Attendance", {
            "employee": employee,
            "attendance_date": day,
            "docstatus": ["<=", 2]

        }, 'name')
        if exist:
            doc = frappe.get_doc("Attendance", exist)
            if doc.attendance_calculation:
                if doc.docstatus == 1:
                    doc.cancel()
                    doc.delete()
                    return frappe.new_doc("Attendance")

                return doc
            else:
                link = get_link_to_form("Attendance", doc.name)
                frappe.throw(_(f"Please delete Attendace {link} First"))
        else:
            return frappe.new_doc("Attendance")

    @frappe.whitelist()
    def post_attendance(self):
        self.delete_Additional_salary()
        self.delete_leave_entries()
        self.delete_employee_penalties()

        employee_filters = self.get_employees_filters()
        self.start_date = parse(str(self.start_date)).date()
        self.end_date = parse(str(self.end_date)).date()
        self.payroll_effect_date = parse(str(self.payroll_effect_date)).date()
        self.payroll_start_date = parse(str(self.payroll_start_date)).date()
        self.payroll_end_date = parse(str(self.payroll_end_date)).date()

        sql = f"""
	select log.employee
		, SUM(log.working_hours) as working_hours
		, SUM(case when log.status = 'Absent' then 1 else 0 end) as absent
		, SUM(case when log.holiday <> 1 then ifnull(log.overtime_factor,0) else 0 end) as normal_overtime
		, SUM(case when log.holiday <> 0 then ifnull(log.overtime_factor,0) else 0 end) as holiday_overtime
		, SUM(case when log.holiday <> 1 then ifnull(log.late_factor,0) else 0 end) as late
		, SUM(case when log.holiday <> 1 then ifnull(log.late_penalty_factor,0) else 0 end) as late_penalty
		, SUM(case when log.holiday <> 1 then ifnull(log.less_time_factor,0) else 0 end) as less_time
	#  , SUM(case when log.holiday <> 1 then ifnull(log.less_time_factor,0) else 0 end) as less_time
		, SUM(case when log.forget_fingerprint <> 0 then log.fingerprint_factor else 0 end) as forget_fingerprint
		, SUM(case when log.forget_fingerprint <> 0 and log.fingerprint_type = 'IN' then log.fingerprint_factor else 0 end) as forget_fingerprint_in
		, SUM(case when log.forget_fingerprint <> 0 and log.fingerprint_type = 'OUT' then log.fingerprint_factor else 0 end) as forget_fingerprint_out
		, SUM(case when log.has_shift_bonus <> 0 then log.shift_bonus else 0 end) as shift_bonus
		, SUM(case when log.has_visit_bonus <> 0 then log.visit_bonus else 0 end) as visit_bonus
		, SUM(case when ifnull(log.visit_form,'') <> '' and log.holiday = 1 then log.visit_factor else 0 end) as holiday_visit_factor
		, SUM(case when ifnull(log.visit_form,'') <> '' and log.holiday <> 1 then log.visit_factor else 0 end) as normal_visit_factor
		, SUM(case when log.status='Absent' then 1 else 0 end) as total_absent
	#        , SUM(CAST(  ifnull(log.overtime , 0)  AS TIME)) / 60
		, SUM(case 
		when leave_type.is_lwp = 1 and log.holiday <> 1 and log.status = 'On Leave' then 1 
		when leave_type.is_lwp = 1 and log.holiday <> 1 and log.status = 'Half Day' then 0.5
		else 0 end

		) as total_lwp

	from tabAttendance log inner join tabEmployee emp on emp.name = log.employee
	left join `tabLeave Application` leave_application on log.leave_application = leave_application.name
	left join `tabLeave Type`leave_type on leave_type.name = leave_application.leave_type
	where log.docstatus = 1
	and date(log.attendance_date) BETWEEN date('{self.payroll_start_date}') and date('{self.payroll_end_date}')
		{employee_filters}
	group by emp.name asc
			"""
        attendances = frappe.db.sql(sql, as_dict=1) or []

        count = 1
        total = len(attendances)
        # frappe.msgprint(str(total))
        for log in attendances:
            employee = frappe.get_doc("Employee", log.employee)
            attendance_rule = frappe.get_doc(
                "Attendance Rule", employee.attendance_rule)
            frappe.publish_realtime("attendance_calculation_progress",
                                    frappe._dict({
                                        "count": count,
                                        "total": total,
                                        "message": employee.employee_name + "    " + _(f"Calculate {count}/{total} employees"),
                                        "title": _("Post Additional Salaries ..."),

                                    }), user=frappe.session.user)
            try:
                # if 1 :
                # frappe.msgprint('str(day_rate)')
                day_rate = 1
                hour_rate = 1
                calculate_amount_based_on_formula = frappe.db.get_single_value(
                    "Payroll Settings", "calculate_amount_based_on_formula_on_additional_salary")
                if not calculate_amount_based_on_formula:
                    total_hourly_salary = get_employee_salary(
                        employee, self.payroll_effect_date)
                    if not total_hourly_salary:
                        frappe.throw(
                            _(f"Employee {employee.employee_name} has no components Consider in Hour Rate"))

                    day_rate = total_hourly_salary / \
                        (attendance_rule.working_days_per_month)
                    hour_rate = day_rate / \
                        (attendance_rule.working_hours_per_day)

                # Normal Overtime
                if attendance_rule.enable_overtime:
                    if attendance_rule.working_type in ["Monthly Target Hour"]:
                        total_working_hours = log.working_hours or 0
                        target_hours = attendance_rule.working_days_per_month or 0
                        log.normal_overtime = 0
                        if total_working_hours > target_hours:
                            overtime_factor = 0
                            overtime_minutes = (
                                total_working_hours - target_hours) / 60
                            for row in attendance_rule.overtime_rules:
                                if row.from_min <= overtime_minutes <= row.to_min:
                                    overtime_factor = row.factor

                            log.normal_overtime = overtime_minutes * overtime_factor

                    if log.normal_overtime:
                        overtime = (log.normal_overtime / 60) if attendance_rule.overtime_maximum_per_month >= (
                            log.normal_overtime / 60) else attendance_rule.overtime_maximum_per_month
                        amount = overtime * hour_rate
                        salary_component = attendance_rule.normal_overtime_salary_component
                        mark = "normal overtime"
                        remark = f"Normal Overtime : {overtime} Hours"
                        salary_component_type = "Earning"
                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                    # Holiday Overtime
                    if log.holiday_overtime:
                        overtime = (log.holiday_overtime / 60)
                        amount = overtime * hour_rate
                        salary_component = attendance_rule.holiday_overtime_salary_component
                        mark = "Holiday overtime"
                        remark = f"Holiday Overtime : {overtime} Hours"
                        salary_component_type = "Earning"
                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                # Absent
                if attendance_rule.enable_absent:
                    # frappe.msgprint(str(log.absent))
                    # frappe.msgprint(str(day_rate))
                    if log.absent:
                        absent = log.absent * attendance_rule.absent_factor
                        amount = absent * day_rate
                        salary_component = attendance_rule.absent_salary_component
                        leave_component = attendance_rule.absent_leave_component
                        mark = "Absent"
                        remark = f"Absen : {absent} Days"
                        salary_component_type = "Deduction"
                        if attendance_rule.absent_salary and attendance_rule.absent_leave_balance:
                            if self.check_leave_balance(employee.name, leave_component, absent):
                                if absent and leave_component and attendance_rule.absent_leave_balance:
                                    # frappe.msgprint('str(day_rate)')
                                    self.submit_leave_balance(
                                        employee, -1 * absent, leave_component, mark)
                            else:

                                if amount and salary_component and attendance_rule.absent_salary:
                                    # frappe.msgprint(str(amount))
                                    self.submit_additional_salary(
                                        employee, amount, salary_component, salary_component_type, remark, mark)

                        else:
                            if amount and salary_component and attendance_rule.absent_salary:
                                # frappe.msgprint(str(amount))
                                self.submit_additional_salary(
                                    employee, amount, salary_component, salary_component_type, remark, mark)

                            if absent and leave_component and attendance_rule.absent_leave_balance:
                                # frappe.msgprint('str(day_rate)')
                                self.submit_leave_balance(
                                    employee, -1 * absent, leave_component, mark)
                # Absent Penalty
                if attendance_rule.enable_absent_penalty:
                    absent_sql = f"""

							select 
							log.employee ,
							(case when log.status='Absent' then 1 else 0 end) as absent 
							, date(log.attendance_date) as attendance_date
							from tabAttendance log inner join tabEmployee emp on emp.name = log.employee
							where log.docstatus = 1
							and date(log.attendance_date) BETWEEN date('{self.payroll_start_date}') and date('{self.payroll_end_date}')
								and log.employee = '{log.employee}'
							order by emp.name ASC , date(log.attendance_date) ASC
						"""
                    employee_absent = frappe.db.sql(
                        absent_sql, as_dict=1) or []

                    # employee_absent = [x or 0 for x in absent_days if x.employee == log.employee]
                    # absents = []
                    # size = len(employee_absent)
                    # idx_list = [idx + 1 for idx, val in enumerate(employee_absent) if val.absent == 0]
                    # absents_totals = [sum(absents[i: j]) for i, j in zip([0] + idx_list, idx_list +  ([size] if idx_list[-1] != size else []))]
                    # absent_sum = [x for x in absents_totals if x]
                    total_absent = 0
                    last_date = None
                    # frappe.msgprint(str(employee_absent))
                    for absent_row in employee_absent:
                        total_absent += absent_row.absent
                        if absent_row.absent:
                            last_date = absent_row.attendance_date
                        # frappe.msgprint(str(total_absent))
                        if ((not absent_row.absent) or (absent_row == employee_absent[-1])) and total_absent:
                            for penalty_row in attendance_rule.absent_penalty_detail:
                                if (penalty_row.from_day <= total_absent <= penalty_row.to_day) and penalty_row.penalty_type:
                                    self.submit_employee_penalty(
                                        log.employee, last_date, penalty_row.penalty_type)
                            total_absent = 0

                    # for absent in absent_sum :
                    # 	for penalty_row in attendance_rule.absent_penalty_detail :
                    # 		if (penalty_row.from_day <= absent <=  penalty_row.to_day) and penalty_row.penalty_type:
                    # 				self.submit_employee_penalty(
                    # 					log.employee, row.attendance_date, penalty_row.penalty_type)

                # Late
                if attendance_rule.enable_late_rule:
                    if log.late:
                        late = (log.late / 60)
                        late_in_day = late / \
                            (attendance_rule.working_hours_per_day or 1)
                        amount = late * hour_rate
                        salary_component = attendance_rule.salary_component
                        leave_component = attendance_rule.late_leave_component
                        mark = "Lates"
                        remark = f"Lates : {late} Hours"
                        salary_component_type = "Deduction"

                        if attendance_rule.late_salary and attendance_rule.late_leave_balance:
                            if self.check_leave_balance(employee.name, leave_component, late_in_day):
                                if late_in_day and leave_component and attendance_rule.late_leave_balance:
                                    self.submit_leave_balance(
                                        employee, -1 * late_in_day, leave_component, mark)
                            else:
                                if amount and salary_component and attendance_rule.late_salary:
                                    self.submit_additional_salary(
                                        employee, amount, salary_component, salary_component_type, remark, mark)

                        else:
                            if amount and salary_component and attendance_rule.late_salary:
                                self.submit_additional_salary(
                                    employee, amount, salary_component, salary_component_type, remark, mark)

                            if late_in_day and leave_component and attendance_rule.late_leave_balance:
                                self.submit_leave_balance(
                                    employee, -1 * late_in_day, leave_component, mark)

                # Late Penalty
                if attendance_rule.enable_late_penalty:
                    if log.late_penalty:
                        late_penalty = (log.late_penalty / 60)
                        late_in_day = late_penalty / \
                            (attendance_rule.working_hours_per_day or 1)
                        amount = late_penalty * hour_rate
                        salary_component = attendance_rule.late_penalty_salary_component
                        leave_component = attendance_rule.late_penalty_leave_type
                        mark = "Late Penalty"
                        remark = f"Late Penalty : {late_penalty} Hours"
                        salary_component_type = "Deduction"

                        if attendance_rule.deduct_late_penalty_from_salary and attendance_rule.deduct_late_penalty_from_leave_balance:
                            if self.check_leave_balance(employee.name, leave_component, late_in_day):

                                if amount and salary_component and attendance_rule.deduct_late_penalty_from_salary:
                                    self.submit_additional_salary(
                                        employee, amount, salary_component, salary_component_type, remark, mark)

                            else:

                                if late_in_day and leave_component and attendance_rule.deduct_late_penalty_from_leave_balance:
                                    self.submit_leave_balance(
                                        employee, -1 * late_in_day, leave_component, mark)

                        else:
                            if amount and salary_component and attendance_rule.deduct_late_penalty_from_salary:
                                self.submit_additional_salary(
                                    employee, amount, salary_component, salary_component_type, remark, mark)

                            if late_in_day and leave_component and attendance_rule.deduct_late_penalty_from_leave_balance:
                                self.submit_leave_balance(
                                    employee, -1 * late_in_day, leave_component, mark)

                # Less Time
                if attendance_rule.less_time:
                    if attendance_rule.working_type in ["Monthly Target Hour"]:
                        total_working_hours = log.working_hours or 0
                        target_hours = attendance_rule.working_days_per_month or 0
                        log.less_time = 0
                        if total_working_hours < target_hours:
                            less_time_factor = attendance_rule.less_time_factor
                            less_time_minutes = (
                                target_hours - total_working_hours) / 60

                            log.less_time = less_time_minutes * less_time_factor

                    if log.less_time:
                        less_time = (log.less_time / 60)
                        less_time_in_day = less_time / \
                            (attendance_rule.working_hours_per_day or 1)
                        amount = less_time * hour_rate
                        salary_component = attendance_rule.less_time_salary_component
                        leave_component = attendance_rule.less_leave_component
                        mark = "Less Time"
                        remark = f"Less Time : {less_time} Hours"
                        salary_component_type = "Deduction"

                        if attendance_rule.less_salary and attendance_rule.less_leave_balance:
                            if self.check_leave_balance(employee.name, leave_component, less_time_in_day):
                                if less_time_in_day and leave_component and attendance_rule.less_leave_balance:
                                    self.submit_leave_balance(
                                        employee, -1 * less_time_in_day, leave_component, mark)
                            else:
                                if amount and salary_component and attendance_rule.less_salary:
                                    self.submit_additional_salary(
                                        employee, amount, salary_component, salary_component_type, remark, mark)

                        else:
                            if amount and salary_component and attendance_rule.less_salary:
                                self.submit_additional_salary(
                                    employee, amount, salary_component, salary_component_type, remark, mark)
                            if less_time_in_day and leave_component and attendance_rule.less_leave_balance:
                                self.submit_leave_balance(
                                    employee, -1 * less_time_in_day, leave_component, mark)

                # Forget Fingerprint
                if attendance_rule.enable_fingerprint_penalty:
                    # if log.forget_fingerprint :
                    # 	forget_fingerprint = log.forget_fingerprint # * attendance_rule.fingerprint_penalty_factor
                    # 	amount = forget_fingerprint * hour_rate
                    # 	salary_component = attendance_rule.fingerprint_penalty_salary_component
                    # 	mark = "Forget Fingerprint Penalty"
                    # 	remark = f"Forget Fingerprint : {log.forget_fingerprint} Times"
                    # 	salary_component_type = "Deduction"
                    # 	if amount and salary_component :
                    # 			self.submit_additional_salary(employee,amount,salary_component,salary_component_type,remark,mark)

                    if log.forget_fingerprint_in:
                        # * attendance_rule.fingerprint_penalty_factor
                        forget_fingerprint = log.forget_fingerprint_in
                        amount = forget_fingerprint * hour_rate
                        salary_component = attendance_rule.fingerprint_penalty_salary_component
                        mark = "Forget Fingerprint IN Penalty"
                        remark = f"Forget Fingerprint IN : {log.forget_fingerprint_in} Hours"
                        salary_component_type = "Deduction"
                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                    if log.forget_fingerprint_out:
                        # * attendance_rule.fingerprint_penalty_factor
                        forget_fingerprint = log.forget_fingerprint_out
                        amount = forget_fingerprint * hour_rate
                        salary_component = attendance_rule.fingerprint_penalty_out_salary_component
                        mark = "Forget Fingerprint OUT Penalty"
                        remark = f"Forget Fingerprint OUT : {log.forget_fingerprint_out} Hours"
                        salary_component_type = "Deduction"
                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                # Shift Type Bonus
                if attendance_rule.enable_shift_bonus and log.shift_bonus:
                    amount = log.shift_bonus
                    salary_component = attendance_rule.shift_bonus_component
                    mark = "Shift Bonus"
                    remark = f"Shift Bonus : {log.shift_bonus} "
                    salary_component_type = "Earning"
                    if amount and salary_component:
                        self.submit_additional_salary(
                            employee, amount, salary_component, salary_component_type, remark, mark)

                # Visit Bonus
                if attendance_rule.enable_visit_bonus and log.visit_bonus:
                    amount = log.visit_bonus
                    salary_component = attendance_rule.visit_bonus_salary_component
                    mark = "Visit Bonus"
                    remark = f"Visit Bonus : {log.visit_bonus} "
                    salary_component_type = "Earning"
                    if amount and salary_component:
                        self.submit_additional_salary(
                            employee, amount, salary_component, salary_component_type, remark, mark)

                # Visit Form Earning
                if attendance_rule.enable_site_visit:
                    if log.holiday_visit_factor:
                        amount = log.holiday_visit_factor
                        salary_component = attendance_rule.visit_form_salary_component
                        mark = "Holiday Visit"
                        remark = f"Holiday Visit : {log.holiday_visit_factor} "
                        salary_component_type = "Earning"
                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                    if log.normal_visit_factor:
                        amount = log.normal_visit_factor
                        salary_component = attendance_rule.visit_form_salary_component
                        mark = "Normal Visit"
                        remark = f"Normal Visit : {log.normal_visit_factor} "
                        salary_component_type = "Earning"
                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                # Leave Witout Pay
                if attendance_rule.enable_leaves:
                    if log.total_lwp:

                        total_lwp = log.total_lwp

                        amount = total_lwp * day_rate
                        salary_component = attendance_rule.leaves_salary_component
                        mark = "Leave Without Pay"
                        remark = f"Leave Without Pay : {total_lwp} Days"
                        salary_component_type = "Deduction"

                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)

                
                # Joining / Exiting Period 
                if attendance_rule.joining_exiting_period_salary_component :
                    actual_working_days = 0
                    
                    employee.relieving_date = getdate(employee.relieving_date) if employee.relieving_date else employee.relieving_date
                    employee.date_of_joining = getdate(employee.date_of_joining)

                    is_joined = self.payroll_start_date < employee.date_of_joining <= self.payroll_end_date
                    is_leaved = employee.relieving_date and (self.payroll_start_date <= employee.relieving_date < self.payroll_end_date)

                    if is_leaved and is_joined:
                        actual_working_days = (employee.relieving_date - employee.date_of_joining).days + 1
                        
                    elif is_joined:
                        actual_working_days += (self.payroll_end_date - employee.date_of_joining).days + 1
                        
                    elif is_leaved:
                        actual_working_days += (self.payroll_end_date - employee.relieving_date).days + 1
                        
                    actual_working_days = min(actual_working_days , 30)
                    
                    total_days = 30 - actual_working_days
                    
                    if total_days > 0 :
                        amount = total_days * day_rate
                        salary_component = attendance_rule.joining_exiting_period_salary_component
                        mark = "Joining / Exiting Period "
                        remark = f"Joining / Exiting Period : {total_days} Days"
                        salary_component_type = "Deduction"

                        if amount and salary_component:
                            self.submit_additional_salary(
                                employee, amount, salary_component, salary_component_type, remark, mark)
                    
                frappe.db.commit()
            except Exception as e:
                frappe.throw(
                    _(f"Error While Posting Attendance For Employee {employee.employee_name} <BR/>'{e}'"))

            count += 1

        self.submit_employee_penalties()

    def get_employees_filters(self):
        conditions = " and ifnull(emp.attendance_rule,'') <> '' and emp.status in ('Active' , 'Suspended') "
        if self.company:
            conditions += f" and emp.company = '{self.company}' "
        if self.department:
            conditions += f" and emp.department = '{self.department}' "
        if self.grade:
            conditions += f" and emp.grade = '{self.grade}' "
        if self.employee:
            conditions += f" and emp.name = '{self.employee}' "
        if self.designation:
            conditions += f" and emp.designation = '{self.designation}' "
        if self.branch:
            conditions += f" and emp.branch = '{self.branch}' "
        if self.project:
            conditions += f" and emp.project = '{self.project}' "
        if self.cost_center:
            conditions += f" and emp.cost_center = '{self.cost_center}' "
        return conditions

    def submit_additional_salary(self, employee, amount, salary_component, salary_component_type, remark, mark):
        if not amount:
            return
        try:
            doctype = "Additional Salary"
            doc = frappe.db.get_value(doctype, {
                "mark": mark,
                # "salary_component":salary_component,
                "employee": employee.name,
                "attendance_calculation": self.name,
                # "docstatus" : ["<",2]} , ['name','salary_slip'] , as_dict=1)
                "docstatus": ["<", 2]}, ['name'], as_dict=1)

            if doc:
                if doc.salary_slip:
                    lnk = get_link_to_form(doctype, doc.name)
                    frappe.throw(
                        _(f"Can't Cancel Additional Salary {lnk} is assigned to salary slip for employee {employee.employee_name}"))
                else:
                    doc = frappe.get_doc(doctype, doc.name)
                    doc.cancel()
                    doc.delete()

            doc = frappe.new_doc(doctype)
            doc.naming_series = "HR-ADS-.YY.-.MM.-"
            doc.employee = employee.name
            doc.employee_name = employee.employee_name
            doc.department = employee.department
            doc.company = employee.company

            doc.salary_component = salary_component
            doc.type = salary_component_type
            doc.amount = amount
            doc.attendance_calculation = self.name
            doc.remark = remark
            doc.mark = mark
            doc.overwrite_salary_structure_amount = 0
            doc.ref_doctype = "Attendance Calculation"
            doc.ref_docname = self.name
            doc.payroll_date = (self.payroll_effect_date) if not employee.relieving_date else min(getdate(employee.relieving_date) , getdate(self.payroll_effect_date))
            doc.amount_based_on_formula, doc.formula = frappe.db.get_value(
                "Salary Component", doc.salary_component, ["amount_based_on_formula", "formula"])

            doc.submit()
        except Exception as e:
            frappe.msgprint(_(str(e)))

    def check_leave_balance(self, employee, leave_type, days):
        leave_balance = get_leave_balance_on(employee, leave_type, self.payroll_effect_date,
                                             consider_all_leaves_in_the_allocation_period=True)
        return ((leave_balance or 0) >= days)

    def submit_leave_balance(self, employee, amount, leave_component, mark):
        if not amount:
            return
        try:
            doctype = "Leave Ledger Entry"
            doc = frappe.db.get_value(doctype, {
                "mark": mark,
                # "salary_component":salary_component,
                "employee": employee.name,
                "reference_type": self.doctype,
                "reference_name": self.name,
                "docstatus": ["<", 2]}, ['name'], as_dict=1)

            if doc:
                try:
                    doc = frappe.get_doc(doctype, doc.name)
                    doc.cancel()
                    # doc.delete()
                except Exception as e:
                    frappe.msgprint(_(str(e)))

            doc = frappe.new_doc(doctype)
            doc.employee = employee.name
            doc.employee_name = employee.employee_name
            doc.leave_type = leave_component
            doc.transaction_type = "Leave Encashment"
            doc.reference_type = self.doctype
            doc.reference_name = self.name
            doc.leaves = amount
            doc.company = employee.company
            doc.from_date = self.payroll_effect_date
            doc.to_date = self.payroll_effect_date
            doc.mark = mark
            doc.submit()
        except Exception as e:
            frappe.msgprint(_(str(e)))

    def submit_employee_penalties(self):
        employee_filters = self.get_employees_filters()
        penalties_sql = f"""
		select log.employee , date(log.attendance_date) as attendance_date ,log.late_penalty_type , log.less_penalty_type 
		from tabAttendance log inner join tabEmployee emp on emp.name = log.employee
		where log.docstatus = 1
		and date(log.attendance_date) BETWEEN date('{self.payroll_start_date}') and date('{self.payroll_end_date}')
		and (ifnull(log.late_penalty_type , '') <> '' or ifnull(log.less_penalty_type , ''))
		{employee_filters}
		order by employee ASC, log.attendance_date ASC
		"""
        penalties = frappe.db.sql(penalties_sql, as_dict=1)
        for row in penalties:
            if row.late_penalty_type:
                self.submit_employee_penalty(
                    row.employee, row.attendance_date, row.late_penalty_type)
            if row.less_penalty_type:
                self.submit_employee_penalty(
                    row.employee, row.attendance_date, row.less_penalty_type)

    def submit_employee_penalty(self, employee, day_date, penalty_type):
        employee = frappe.get_doc("Employee", employee)
        penalty_type = frappe.get_doc("Penalty Type", penalty_type)
        doc = frappe.new_doc("Employee Penalty")
        doc.penalty_date = day_date
        doc.payroll_effect_date = self.payroll_effect_date
        doc.payroll_period = self.payroll_period

        doc.employee = employee.name
        doc.employee_name = employee.employee_name
        doc.designation = employee.designation
        doc.department = employee.department
        doc.branch = employee.branch

        doc.penalty_type = penalty_type.name
        doc.based_on_payroll_period = penalty_type.based_on_payroll_period

        doc.notes = f"Penalty For Attendance Day {day_date}"

        doc.attendance_calculation = self.name
        doc.submit()

    def delete_Additional_salary(self):
        employee_filters = self.get_employees_filters()
        frappe.db.sql(f"""
		delete from `tabAdditional Salary`
		where  attendance_calculation= '{self.name}' 
		and name not in (
			select tsd.additional_salary  from `tabSalary Detail` tsd inner join `tabSalary Slip` tss
				on tss.name = tsd.parent and tss.docstatus < 2 and IFNULL(tsd.additional_salary ,'') <> ''
		)
		and employee in (
			select name from tabEmployee emp 
			where 1 = 1 
			{employee_filters}
		)
		""")

    def delete_leave_entries(self):
        employee_filters = self.get_employees_filters()
        frappe.db.sql(f"""
		delete from `tabLeave Ledger Entry`
		where  reference_type = '{self.doctype}' and  reference_name= '{self.name}' 
		and employee in (
			select name from tabEmployee emp
			where 1 = 1 
			{employee_filters}
		)
		""")

    def delete_employee_penalties(self):
        employee_filters = self.get_employees_filters()
        frappe.db.sql(f"""
		delete from `tabEmployee Penalty`
		where  attendance_calculation = '{self.name}' 
		and employee in (
			select name from tabEmployee emp
			where 1 = 1 
			{employee_filters}
		)
		""")


def get_employee_shift(employee, for_date=None, consider_default_shift=False, next_shift_direction=None):
    """Returns a Shift Type for the given employee on the given date. (excluding the holidays)

    :param employee: Employee for which shift is required.
    :param for_date: Date on which shift are required
    :param consider_default_shift: If set to true, default shift is taken when no shift assignment is found.
    :param next_shift_direction: One of: None, 'forward', 'reverse'. Direction to look for next shift if shift not found on given date.
    """
    if for_date is None:
        for_date = nowdate()
    default_shift = frappe.db.get_value('Employee', employee, 'default_shift')
    shift_type_name = None
    shift_assignment_details = frappe.db.get_value('Shift Assignment', {'employee': employee, 'start_date': (
        '<=', for_date), 'docstatus': '1', 'status': "Active"}, ['shift_type', 'end_date'])

    if shift_assignment_details:
        shift_type_name = shift_assignment_details[0]

        # if end_date present means that shift is over after end_date else it is a ongoing shift.
        if shift_assignment_details[1] and for_date > shift_assignment_details[1]:
            shift_type_name = None

    if not shift_type_name and consider_default_shift:
        shift_type_name = default_shift
    # if shift_type_name:
    # 	holiday_list_name = frappe.db.get_value('Shift Type', shift_type_name, 'holiday_list')
    # 	if not holiday_list_name:
    # 		holiday_list_name = get_holiday_list_for_employee(employee, False)
    # 	if holiday_list_name and is_holiday(holiday_list_name, for_date):
    # 		shift_type_name = None

    return get_shift_details(shift_type_name, for_date)


def get_shift_details(shift_type_name, for_date=None):
    """Returns Shift Details which contain some additional information as described below.
    'shift_details' contains the following keys:
            'shift_type' - Object of DocType Shift Type,
            'start_datetime' - Date and Time of shift start on given date,
            'end_datetime' - Date and Time of shift end on given date,
            'actual_start' - datetime of shift start after adding 'begin_check_in_before_shift_start_time',
            'actual_end' - datetime of shift end after adding 'allow_check_out_after_shift_end_time'(None is returned if this is zero)

    :param shift_type_name: shift type name for which shift_details is required.
    :param for_date: Date on which shift_details are required
    """
    if not shift_type_name:
        return None
    if not for_date:
        for_date = nowdate()
    shift_type = frappe.get_doc('Shift Type', shift_type_name)
    start_datetime = datetime.combine(
        for_date, datetime.min.time()) + shift_type.start_time
    for_date = for_date + \
        timedelta(
            days=1) if shift_type.start_time > shift_type.end_time else for_date
    end_datetime = datetime.combine(
        for_date, datetime.min.time()) + shift_type.end_time

    actual_start = datetime.combine(for_date, datetime.min.time())
    actual_end = datetime.combine(
        for_date, datetime.min.time()) + timedelta(days=1)
    if shift_type.min_check_in:
        actual_start = start_datetime - \
            timedelta(minutes=shift_type.min_check_in or 0)
    if shift_type.max_check_out:
        actual_end = end_datetime + \
            timedelta(minutes=shift_type.max_check_out or 0)

    # actual_end = end_datetime + timedelta(minutes=shift_type.max_check_out or 0)
    # frappe.msgprint('str(actual_start)')
    # frappe.msgprint(str(for_date))
    # frappe.msgprint(str(actual_start))
    # frappe.msgprint(str(actual_end))
    # frappe.msgprint('str(start_datetime)')
    # frappe.msgprint(str(start_datetime))
    # frappe.msgprint(str(end_datetime))
    return frappe._dict({
        'shift_type': shift_type,
        'start_datetime': start_datetime,
        'end_datetime': end_datetime,
        'actual_start': actual_start,
        'actual_end': actual_end
    })


def get_assigned_salary_structure(employee, on_date):
    if not employee or not on_date:
        return None
    salary_structure = frappe.db.sql("""
		select salary_structure , name from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and %(on_date)s >= from_date order by from_date desc limit 1""", {
        'employee': employee,
        'on_date': on_date,
    })
    return (salary_structure[0][0], salary_structure[0][1]) if salary_structure else (None, None)


def get_employee_salary(employee, payroll_effect_date):
    total_salary = 0
    salary_structure, salary_structure_assignment = get_assigned_salary_structure(
        employee.name, payroll_effect_date)
    if salary_structure and salary_structure_assignment:
        salary_structure = frappe.get_doc("Salary Structure", salary_structure)
        salary_structure_assignment = frappe.get_doc(
            "Salary Structure Assignment", salary_structure_assignment)
        comp_dict = frappe._dict()

        comp_dict.update(salary_structure_assignment.__dict__)
        comp_dict.update(salary_structure.__dict__)
        comp_dict.update(employee.__dict__)
        earnings_components = [x for x in salary_structure.get(
            "earnings") if not x.amount_based_on_formula]
        deductions_components = [x for x in salary_structure.get(
            "deductions") if not x.amount_based_on_formula]
        formula_earnings_components = [x for x in salary_structure.get(
            "earnings") if x.amount_based_on_formula and x.formula]
        formula_deductions_components = [x for x in salary_structure.get(
            "deductions") if x.amount_based_on_formula and x.formula]
        for row in earnings_components+formula_earnings_components:
            amount = (row.amount or 0)
            if row.amount_based_on_formula:
                formula = row.formula.strip().replace("\n", " ") if row.formula else None
                if formula:
                    try:
                        amount = flt(frappe.safe_eval(
                            formula, whitelisted_globals, comp_dict), row.precision("amount"))
                    except:
                        amount = 0
                else:
                    amount = 0
                try:
                    condition = row.condition.strip().replace("\n", " ") if row.condition else None
                    if condition:
                        if not frappe.safe_eval(condition, whitelisted_globals, comp_dict):
                            amount = 0
                except:
                    pass
                    amount = 0
            comp_dict[row.abbr] = amount
            if row.consider_in_hour_rate:
                total_salary += amount
                print(
                    f"component ===> {row.salary_component} , amount ===> {amount}")

        for row in deductions_components + formula_deductions_components:
            amount = (row.amount or 0)
            if row.amount_based_on_formula:
                formula = row.formula.strip().replace("\n", " ") if row.formula else None
                if formula:
                    try:
                        amount = flt(frappe.safe_eval(
                            formula, whitelisted_globals, comp_dict), row.precision("amount"))
                    except:
                        amount = 0
                else:
                    amount = 0
                try:
                    condition = row.condition.strip().replace("\n", " ") if row.condition else None
                    if condition:
                        if not frappe.safe_eval(condition, whitelisted_globals, comp_dict):
                            amount = 0
                except:
                    pass
                    amount = 0
            comp_dict[row.abbr] = amount
            if row.consider_in_hour_rate:
                print(
                    f"component ===> {row.salary_component} , amount ===> {-1*amount}")
                total_salary += amount
        print(f"total salary ===> {total_salary}")
        for k, v in comp_dict.items():
            print(f"{k} ===> {v}")
    else:
        frappe.throw(
            _("Please assign a Salary Structure for Employee {0} "
              "applicable from or before {1} first").format(
                frappe.bold(employee.employee_name),
                frappe.bold(payroll_effect_date),
            )
        )
    return total_salary



def to_time(time_str):
    return dateutil.parser.parse(str(time_str)).time()
