import frappe


def on_install_domain():
    pass


def after_migrate():
    try:
        update_visit_form()
    except Exception as e:
        print("Error update_visit_form ", e)
    try:
        add_custom_fields()
    except Exception as e:
        print("Error add_custom_fields ", e)


def update_visit_form():
    sql = f"""
        update `tabVisit Form` set to_date = `date` where ifnull(to_date,'') = ''
    """
    frappe.db.sql(sql)


def add_custom_fields():
    custom_fields = [
        {
            "dt": "Payroll Settings",
            "label": "Calculate Amount Based on Formula on Additional Salary",
            "fieldname": "calculate_amount_based_on_formula_on_additional_salary",
            "fieldtype": "Check",
            "insert_after": "show_leave_balances_in_salary_slip",
            "default":"0"
        }
    ]
    for field in custom_fields :
        field = frappe._dict(field)
        name = f"""{field.dt}-{field.fieldname}"""
        try : 
            doc = frappe.new_doc("Custom Field")
            if frappe.db.exists("Custom Field" , name):
                doc = frappe.get_doc("Custom Field" , name)
            doc.update(field)
            doc.save()
        except Exception as e :
            print(f"""Error while install custom field {name} :{e}""")

        
        
        
