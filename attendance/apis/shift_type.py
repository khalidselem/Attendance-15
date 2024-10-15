import frappe
from frappe import _
from frappe.utils.data import getdate


@frappe.whitelist()
def assign_shift_type(
    shift_type=None,
    company=None,
    grade=None,
    department=None,
    designation=None,
    employee=None,
    from_date=None,
    to_date=None,
):
    employees = get_employees(
        company=company, grade=grade, department=department, designation=designation, name=employee
    )

    if employees:
        if len(employees) > 50:
            frappe.enqueue(
                assign_shift_type_for_employees,
                timeout=600,
                employees=employees,
                shift_type=shift_type,
                start_date=from_date,
                end_date=to_date,
            )
        else:
            assign_shift_type_for_employees(
                employees=employees,
                shift_type=shift_type,
                start_date=from_date,
                end_date=to_date,
            )
    else:
        frappe.msgprint(_("No Employee Found"))


def assign_shift_type_for_employees(
        employees,
        shift_type,
        start_date=None,
        end_date=None,
):
    shift_assignments = []
    count = 0
    for employee in employees:
        count += 1

        employee_doc = frappe.get_doc("Employee", employee)
        shift_assignment = frappe.new_doc("Shift Assignment")
        shift_assignment.employee = employee
        shift_assignment.employee_name = employee_doc.employee_name
        shift_assignment.shift_type = shift_type
        shift_assignment.start_date = getdate(start_date)
        shift_assignment.end_date = end_date
        shift_assignment.company = employee_doc.company
        shift_assignment.status = 'Active'
        try:
            shift_assignment.submit()
            shift_assignments.append(shift_assignments)
        except Exception as e:
            frappe.msgprint(
                _(f"Error While Shift Assignment for Employee {employee_doc.employee_name} at day {start_date} <br/>{e}"), indicator='red')

        frappe.publish_progress(
            count * 100 / len(set(employees)),
            title=_("Assigning Shift..."),
        )

        if shift_assignments:
            frappe.msgprint(_("Shift has been assigned successfully"))


def get_employees(**kwargs):
    conditions, values = [], []
    for field, value in kwargs.items():
        if value:
            conditions.append("{0}=%s".format(field))
            values.append(value)

    condition_str = " and " + " and ".join(conditions) if conditions else ""

    employees = frappe.db.sql_list(
        "select name from tabEmployee where status='Active' {condition}".format(
            condition=condition_str
        ),
        tuple(values),
    )

    return employees
