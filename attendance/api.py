
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date
from dateutil.parser import parse



field_dict = {
    "Leave Application":"from_date",
    "Daily Overtime Request":"date",
    "Visit Form":"date",
    "Permission Application":"day",
}

allowed_roles = ["System Manager","HR Manager"]

def before_insert (doc,fun=''):
    user_roles = frappe.get_roles()
    is_manger = any((x in allowed_roles) for x in user_roles)
    if is_manger:
                return True
    
    employee_request_max_limit = frappe.db.get_single_value("Attendance Settings","employee_request_max_limit") or 0
    if not employee_request_max_limit :
        return True

    field = field_dict.get(doc.doctype)
    posting_date = getattr(doc,field)
    if posting_date :
        posting_date = parse(str(posting_date)).date()
        diff_days = (date.today() - posting_date).days + 1
        # frappe.msgprint(str('diff_days'))
        # frappe.msgprint(str(diff_days))
        # frappe.msgprint(str('employee_request_max_limit'))
        # frappe.msgprint(str(employee_request_max_limit))
         
        if employee_request_max_limit < diff_days :
            frappe.throw(_("Can't Create Request after {} Days".format(employee_request_max_limit)))
        

def validate (doc,fun=''):
    user_roles = frappe.get_roles()
    # is_manger = any((x in allowed_roles) for x in user_roles)
    is_manger = ("System Manager" in user_roles)
    if is_manger:
                return True
    
    approve_request_max_limit = frappe.db.get_single_value("Attendance Settings","approve_request_max_limit") or 0
    if not approve_request_max_limit :
        return True

    field = field_dict.get(doc.doctype)
    posting_date = getattr(doc,field)
    if posting_date :
        posting_date = parse(str(posting_date)).date()
        diff_days = (date.today() - posting_date).days + 1
        # frappe.msgprint(str('diff_days'))
        # frappe.msgprint(str(diff_days))
        # frappe.msgprint(str('approve_request_max_limit'))
        # frappe.msgprint(str(approve_request_max_limit))
         
        if approve_request_max_limit < diff_days :
            frappe.throw(_("Can't Edit Request after {} Days".format(approve_request_max_limit)))




def validate_salary_slip(self,fun=''):
    for row in self.earnings :
        if getattr(row,'customer',None) :
            sql = f"""
            select count(*) from tabAttendance where customer = '{row.customer}' and docstatus = 1
            and date(attendance_date) between date('{self.start_date}') and  date('{self.end_date}')
            """
            res = frappe.db.sql(sql) or []
            row.no_of_visits = (res [0][0] or 0) if res else 0 

            sql =f"""
                update `tabSalary Detail` s 
                set s.no_of_visits = '{row.no_of_visits}' 
                where name = '{row.name}'
                
            """
            frappe.db.sql(sql)
            frappe.db.commit()


    update_salary_slip_remark(self.name)

def update_salary_slip_remark(name=None):
        conditions = "where ifnull(s.additional_salary,'') <> '' "
        if name : 
            conditions += f" and s.parent = '{name}'"

        sql =f"""
        update `tabSalary Detail` s 
        set s.remark = (select t.remark from `tabAdditional Salary` t where t.name = s.additional_salary order by name limit 1 )
        {conditions} 
        """
        # frappe.msgprint(sql)
        frappe.db.sql(sql)
        frappe.db.commit()



def update_employee_birth_date():
    employees = frappe.get_all("Employee")
    for employee in employees :
        employee = frappe.get_doc("Employee" , employee.name)
        employee.save()


def update_foreign_employee():
    sql = f"""
    select 
        employee.name 
    from 
        `tabEmployee` employee 
    inner join 
        `tabLeave Application` application
    on 
        application.employee = employee.name and application.docstatus = 1 and application.status = 'Approved'
    where 
        employee.status = 'Active' and employee.is_foreign = 1
        and CURDATE() BETWEEN application.from_date and application.to_date
    """
    
    employees = frappe.db.sql_list(sql)
    for employee in employees :
        employee = frappe.get_doc("Employee" , employee)
        employee.status = "Inactive"
        employee.save()