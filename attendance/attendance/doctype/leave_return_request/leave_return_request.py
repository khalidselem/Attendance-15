# Copyright (c) 2024, Peter Maged and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import add_days, add_years, get_link_to_form, getdate

class LeaveReturnRequest(Document):
	def validate(self):
		self.validate_employee()

	def validate_employee(self):
		employee = frappe.get_doc("Employee" , self.employee)

		if not employee.is_foreign :
			frappe.throw(_("Employee {} is not foreign").format(self.employee))

		if employee.status != "Inactive" :
			frappe.throw(_("Employee {} status is {} , should be Inactive").format(self.employee , _(employee.status)))
		
	def on_submit(self):
		if self.status in ["Open", "Cancelled"]:
			frappe.throw(
				_("Only Leave Return Applications with status 'Approved' and 'Rejected' can be submitted")
			)
		self.disbale_leave_allocation_for_foreign_employee()
  
		
		effective_from = getdate(self.return_date)
		effective_to   = add_days(add_years(effective_from , 1) , -1)

		leave_policy = get_leave_policy_based_on_years(self.employee)

		assignment = frappe.new_doc("Leave Policy Assignment")

		assignment.assignment_based_on = "Date of Rejoining"
		assignment.employee = self.employee
		assignment.effective_from = effective_from
		assignment.effective_to = effective_to
		assignment.leave_policy = leave_policy 
		assignment.submit()

		lnk = get_link_to_form(assignment.doctype , assignment.name)
		frappe.msgprint(_("{} {} was created".format(assignment.doctype , lnk)))

		self.db_set("leave_policy_assignment" , assignment.name)


		employee = frappe.get_doc("Employee" , self.employee)

		employee.status = 'Active'
		employee.date_of_rejoining = getdate(self.return_date)
		
		employee.db_set("status", employee.status)
		employee.db_set("date_of_rejoining", employee.date_of_rejoining)


	def on_cancel(self) : 
		if self.leave_policy_assignment : 
			leave_policy_assignment = frappe.get_doc("Leave Policy Assignment" , self.leave_policy_assignment)
			self.db_set("leave_policy_assignment" , "")

			if leave_policy_assignment.docstatus == 1 :
				allocations = frappe.get_all("Leave Allocation" , {
      								"leave_policy_assignment": leave_policy_assignment.name ,
									"docstatus" : 1 ,
             					} , pluck='name' )

				for allocation in allocations :
					allocation = frappe.get_doc("Leave Allocation" , allocation)

					if allocation.docstatus == 1 :
						allocation.cancel()
				leave_policy_assignment.reload()
				leave_policy_assignment.cancel()

		employee = frappe.get_doc("Employee" , self.employee)

		employee.status = 'Inactive'
		employee.date_of_rejoining = None
		
		employee.db_set("status", employee.status)
		employee.db_set("date_of_rejoining", employee.date_of_rejoining)


	def disbale_leave_allocation_for_foreign_employee(self) :
		employee = frappe.get_doc("Employee" , self.employee)

		if not employee.is_foreign :
			return
		to_date = add_days(getdate(self.return_date) , -1)
  
		allocations = get_leave_allocations(employee.name , self.return_date)
		for allocation in allocations :
			allocation = frappe.get_doc("Leave Allocation", allocation.name)
			ledger_entries = frappe.get_all("Leave Ledger Entry", {
       													"transaction_type" : "Leave Allocation" ,
       													"transaction_name" : allocation.name ,
             										}
                                   ,pluck='name')

			if allocation.leave_policy_assignment :
				leave_policy_assignment = frappe.get_doc("Leave Policy Assignment", allocation.leave_policy_assignment)
				leave_policy_assignment.db_set("effective_to" , to_date)

			for leave_ledger_entry in ledger_entries :
				doc = frappe.get_doc("Leave Ledger Entry" , leave_ledger_entry)
				doc.db_set("to_date" , to_date)

			allocation.db_set("to_date" , to_date)


def get_leave_policy_based_on_years(employee , years_of_service = 0):
    employee = frappe.get_doc("Employee" , employee)
    
    return_date  = employee.date_of_joining
    
    years_of_service = years_of_service or get_year_diff(getdate(return_date) , getdate())
    
    leave_policy_rule = frappe.get_single("Leave Policy Rule")
    if not (leave_policy_rule and leave_policy_rule.rules) :
        return 
    
    rules = [x.leave_policy for x in leave_policy_rule.rules if x.leave_policy and x.from_year <= int(years_of_service) <= x.to_year]
    
    if not rules :
        return 
    
    return rules[-1]
    
    

def get_leave_allocations(employee,date):
	return frappe.db.sql(
		"""select name, employee, from_date, to_date, leave_policy_assignment, leave_policy
		from `tabLeave Allocation`
		where
  			employee=%s 
     		and %s between from_date and to_date and docstatus=1
			""",
		(employee , date),
		as_dict=1,
	)
 


def get_year_diff(start_date, end_date):
    # Convert strings to datetime objects
    start_date = getdate(start_date)
    end_date = getdate(end_date)


    # Calculate the difference in years
    year_diff = end_date.year - start_date.year

    # Adjust for cases where the second date's month and day are earlier than the first date
    if (end_date.month, end_date.day) < (start_date.month, start_date.day):
        year_diff -= 1

    return year_diff