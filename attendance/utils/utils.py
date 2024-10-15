import frappe, erpnext
from frappe.model.naming import make_autoname






def insert_component_from_activity_type():
    for activity in frappe.db.get_all("Activity Type", filters={}, fields="*"):
        activity = frappe._dict(activity)
        print("=========================" + str(activity.name))
        activity_doc = frappe.get_doc("Activity Type", activity.name)
        add_salary_component_from_activity_type(activity_doc)


def add_salary_component_from_activity_type(doc, method=None):
    component = frappe.db.get_value("Salary Component", {"name": doc.name}, "name")
    # print("component=========================" + str(component))
    if not component:
        salary_component = frappe.new_doc("Salary Component")

        salary_component.salary_component = doc.name
        salary_component.type = "Earning"
        salary_component.depends_on_payment_days = 1
        salary_component.custom_for = "OUT"
        salary_component.salary_component_abbr = make_autoname("ACTV.#####")

        # salary_component.append(
        #     "accounts",
        #     dict(
        #         company=erpnext.get_default_company(),
        #         # account="510068 - Employee Other Deductions - PT",
        #     ),
        # )
        try:
            salary_component.insert()
            frappe.db.commit()
            print("======" + str(doc.name) + "==========Inserted")
        except Exception as e:
            print("Error======" + str(e) + "======")

def add_additional_salary_component_from_activity_type(doc,method=None):
    if doc.time_logs:
        for row in doc.time_logs:
            add_additional_salary_component(doc.employee,row.activity_type,row.costing_amount,doc.start_date,doc.doctype,doc.name)

def cancel_additional_salary_component_from_activity_type(doc,method=None):
    sals = frappe.db.get_all("Additional Salary",filters={"ref_doctype":doc.doctype,"ref_docname":doc.name},fields="*")
    if sals:
        for row in sals:
            doc = frappe.get_doc("Additional Salary",row.name)
            if doc.docstatus == 1:
                doc.cancel()
                frappe.db.commit()
            frappe.delete_doc("Additional Salary", doc.name, ignore_on_trash=True, force=True)
            frappe.db.commit()
def add_additional_salary_component(employee,salary_component,amount,payroll_date,doctype,doc_name):
    additional_salary = frappe.new_doc("Additional Salary")
    additional_salary.employee = employee
    additional_salary.currency = erpnext.get_default_currency()
    additional_salary.salary_component = salary_component
    additional_salary.overwrite_salary_structure_amount = 0
    additional_salary.payroll_date = payroll_date
    additional_salary.company = erpnext.get_default_company()
    additional_salary.ref_doctype = doctype
    additional_salary.ref_docname = doc_name
    additional_salary.amount = amount
    additional_salary.insert()
    additional_salary.submit()
    frappe.db.commit()
