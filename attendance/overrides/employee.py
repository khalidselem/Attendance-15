import json
import frappe 
from frappe.utils import getdate , nowdate
def validate(doc,method=''):
    set_employee_age(doc)
    


@frappe.whitelist()
def set_employee_age(doc):
    if doc.date_of_birth :
        date_of_birth = getdate(doc.date_of_birth)
        today = getdate()
        age = today - date_of_birth
        doc.age_years = age.days // 365
        doc.age_months = (age.days % 365) // 30
        doc.age_days = (age.days % 365) % 30