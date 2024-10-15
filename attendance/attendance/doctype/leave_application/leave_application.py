# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import (
	cint,
	cstr,
	date_diff,
	flt,
	getdate,
	nowdate,
)

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from dateutil.relativedelta import relativedelta


class LeaveDayBlockedError(frappe.ValidationError): pass
class OverlapError(frappe.ValidationError): pass
class AttendanceAlreadyMarkedError(frappe.ValidationError): pass
class NotAnOptionalHoliday(frappe.ValidationError): pass

from frappe.model.document import Document



from hrms.hr.doctype.leave_application.leave_application import LeaveApplication

class AttendanceLeaveApplication(LeaveApplication):
	def update_attendance(self):
		return
	def validate_attendance(self):
		return
	def validate_salary_processed_days(self):
		return

	def before_save(self):

		self.set_leave_balance_on_date()

	# def on_submit(self):
	# 	super(AttendanceLeaveApplication, self).on_submit()
	# 	self.disbale_leave_allocation_for_foreign_employee()

	def disbale_leave_allocation_for_foreign_employee(self) :
		employee = frappe.get_doc("Employee" , self.employee)

		if not employee.is_foreign :
			return

		allocations = get_leave_allocations(employee.name , self.from_date , self.leave_type)
		for allocation in allocations :
			allocation = frappe.get_doc("Leave Allocation", allocation.name)
			ledger_entries = frappe.get_all("Leave Ledger Entry", {
       													"transaction_type" : "Leave Allocation" ,
       													"transaction_name" : allocation.name ,
             										}
                                   ,pluck='name')

			if allocation.leave_policy_assignment :
				leave_policy_assignment = frappe.get_doc("Leave Policy Assignment", allocation.leave_policy_assignment)
				leave_policy_assignment.db_set("effective_to" , self.to_date)

			for leave_ledger_entry in ledger_entries :
				doc = frappe.get_doc("Leave Ledger Entry" , leave_ledger_entry)
				doc.db_set("to_date" , self.to_date)

			allocation.db_set("to_date" , self.to_date)

	@frappe.whitelist()
	def set_leave_balance_on_date(self):
		leave_balance_on_date = 0
		if self.leave_type :
			allocations = get_leave_allocations(self.employee , self.from_date , self.leave_type)
			for allocation in allocations :
				allocation = frappe.get_doc("Leave Allocation", allocation.name)

				if allocation.leave_policy_assignment :
					leave_policy_assignment = frappe.get_doc("Leave Policy Assignment", allocation.leave_policy_assignment)
					leave_policy = frappe.get_doc("Leave Policy", leave_policy_assignment.leave_policy)
					total_days = sum([(x.annual_allocation or 0) for x in (leave_policy.leave_policy_details or [])])
					# Calculate the difference in months
					diff = relativedelta(getdate(leave_policy_assignment.effective_to), getdate(leave_policy_assignment.effective_from))
					total_months = diff.years * 12 + diff.months + 1 

					# Calculate the difference in months
					diff = relativedelta(getdate(self.to_date), getdate(leave_policy_assignment.effective_from))
					actual_months = diff.years * 12 + diff.months + 1
					if total_months :
						leave_balance_on_date = total_days * actual_months / total_months
						# frappe.msgprint(str(total_days))
						# frappe.msgprint(str(actual_months))
						# frappe.msgprint(str(total_months))




		self.leave_balance_on_date = leave_balance_on_date

def get_leave_allocations(employee,date, leave_type):
	return frappe.db.sql(
		"""select name, employee, from_date, to_date, leave_policy_assignment, leave_policy
		from `tabLeave Allocation`
		where
  			employee=%s 
     		and %s between from_date and to_date and docstatus=1
			and leave_type=%s""",
		(employee , date, leave_type),
		as_dict=1,
	)
 
 
 
def get_allocation_expiry(employee, leave_type, to_date, from_date):
	''' Returns expiry of carry forward allocation in leave ledger entry '''
	expiry =  frappe.get_all("Leave Ledger Entry",
		filters={
			'employee': employee,
			'leave_type': leave_type,
			'is_carry_forward': 1,
			'transaction_type': 'Leave Allocation',
			'to_date': ['between', (from_date, to_date)]
		},fields=['to_date'])
	return expiry[0]['to_date'] if expiry else None

@frappe.whitelist()
def get_number_of_leave_days(employee, leave_type, from_date, to_date, half_day = None, half_day_date = None, holiday_list = None):
	number_of_days = 0
	if cint(half_day) == 1:
		if from_date == to_date:
			number_of_days = 0.5
		elif half_day_date and half_day_date <= to_date:
			number_of_days = date_diff(to_date, from_date) + .5
		else:
			number_of_days = date_diff(to_date, from_date) + 1

	else:
		number_of_days = date_diff(to_date, from_date) + 1

	if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
		number_of_days = flt(number_of_days) - flt(get_holidays(employee, from_date, to_date, holiday_list=holiday_list))
	return number_of_days

@frappe.whitelist()
def get_leave_details(employee, date):
	allocation_records = get_leave_allocation_records(employee, date)
	leave_allocation = {}
	for d in allocation_records:
		allocation = allocation_records.get(d, frappe._dict())

		total_allocated_leaves = frappe.db.get_value('Leave Allocation', {
			'from_date': ('<=', date),
			'to_date': ('>=', date),
			'employee': employee,
			'leave_type': allocation.leave_type,
		}, 'SUM(total_leaves_allocated)') or 0

		remaining_leaves = get_leave_balance_on(employee, d, date, to_date = allocation.to_date,
			consider_all_leaves_in_the_allocation_period=True)

		end_date = allocation.to_date
		leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
		leaves_pending = get_pending_leaves_for_period(employee, d, allocation.from_date, end_date)

		leave_allocation[d] = {
			"total_leaves": total_allocated_leaves,
			"expired_leaves": total_allocated_leaves - (remaining_leaves + leaves_taken),
			"leaves_taken": leaves_taken,
			"pending_leaves": leaves_pending,
			"remaining_leaves": remaining_leaves}

	#is used in set query
	lwps = frappe.get_list("Leave Type", filters = {"is_lwp": 1})
	lwps = [lwp.name for lwp in lwps]

	ret = {
		'leave_allocation': leave_allocation,
		'leave_approver': get_leave_approver(employee),
		'lwps': lwps
	}

	return ret

@frappe.whitelist()
def get_leave_balance_on(employee, leave_type, date, to_date=None, consider_all_leaves_in_the_allocation_period=False):
	'''
		Returns leave balance till date
		:param employee: employee name
		:param leave_type: leave type
		:param date: date to check balance on
		:param to_date: future date to check for allocation expiry
		:param consider_all_leaves_in_the_allocation_period: consider all leaves taken till the allocation end date
	'''

	if not to_date:
		to_date = nowdate()

	allocation_records = get_leave_allocation_records(employee, date, leave_type)
	allocation = allocation_records.get(leave_type, frappe._dict())

	end_date = allocation.to_date if consider_all_leaves_in_the_allocation_period else date
	expiry = get_allocation_expiry(employee, leave_type, to_date, date)

	leaves_taken = get_leaves_for_period(employee, leave_type, allocation.from_date, end_date)

	return get_remaining_leaves(allocation, leaves_taken, date, expiry)

def get_leave_allocation_records(employee, date, leave_type=None):
	''' returns the total allocated leaves and carry forwarded leaves based on ledger entries '''

	conditions = ("and leave_type='%s'" % leave_type) if leave_type else ""
	allocation_details = frappe.db.sql("""
		SELECT
			SUM(CASE WHEN is_carry_forward = 1 THEN leaves ELSE 0 END) as cf_leaves,
			SUM(CASE WHEN is_carry_forward = 0 THEN leaves ELSE 0 END) as new_leaves,
			MIN(from_date) as from_date,
			MAX(to_date) as to_date,
			leave_type
		FROM `tabLeave Ledger Entry`
		WHERE
			from_date <= %(date)s
			AND to_date >= %(date)s
			AND docstatus=1
			AND transaction_type="Leave Allocation"
			AND employee=%(employee)s
			AND is_expired=0
			AND is_lwp=0
			{0}
		GROUP BY employee, leave_type
	""".format(conditions), dict(date=date, employee=employee), as_dict=1) #nosec

	allocated_leaves = frappe._dict()
	for d in allocation_details:
		allocated_leaves.setdefault(d.leave_type, frappe._dict({
			"from_date": d.from_date,
			"to_date": d.to_date,
			"total_leaves_allocated": flt(d.cf_leaves) + flt(d.new_leaves),
			"unused_leaves": d.cf_leaves,
			"new_leaves_allocated": d.new_leaves,
			"leave_type": d.leave_type
		}))
	return allocated_leaves

def get_pending_leaves_for_period(employee, leave_type, from_date, to_date):
	''' Returns leaves that are pending approval '''
	leaves = frappe.get_all("Leave Application",
		filters={
			"employee": employee,
			"leave_type": leave_type,
			"status": "Open"
		},
		or_filters={
			"from_date": ["between", (from_date, to_date)],
			"to_date": ["between", (from_date, to_date)]
		}, fields=['SUM(total_leave_days) as leaves'])[0]
	return leaves['leaves'] if leaves['leaves'] else 0.0

def get_remaining_leaves(allocation, leaves_taken, date, expiry):
	''' Returns minimum leaves remaining after comparing with remaining days for allocation expiry '''
	def _get_remaining_leaves(remaining_leaves, end_date):

		if remaining_leaves > 0:
			remaining_days = date_diff(end_date, date) + 1
			remaining_leaves = min(remaining_days, remaining_leaves)

		return remaining_leaves

	total_leaves = flt(allocation.total_leaves_allocated) + flt(leaves_taken)

	if expiry and allocation.unused_leaves:
		remaining_leaves = flt(allocation.unused_leaves) + flt(leaves_taken)
		remaining_leaves = _get_remaining_leaves(remaining_leaves, expiry)

		total_leaves = flt(allocation.new_leaves_allocated) + flt(remaining_leaves)

	return _get_remaining_leaves(total_leaves, allocation.to_date)

def get_leaves_for_period(employee, leave_type, from_date, to_date, do_not_skip_expired_leaves=False):
	leave_entries = get_leave_entries(employee, leave_type, from_date, to_date)
	leave_days = 0

	for leave_entry in leave_entries:
		inclusive_period = leave_entry.from_date >= getdate(from_date) and leave_entry.to_date <= getdate(to_date)

		if  inclusive_period and leave_entry.transaction_type == 'Leave Encashment':
			leave_days += leave_entry.leaves

		elif inclusive_period and leave_entry.transaction_type == 'Leave Allocation' and leave_entry.is_expired \
			and (do_not_skip_expired_leaves or not skip_expiry_leaves(leave_entry, to_date)):
			leave_days += leave_entry.leaves

		elif leave_entry.transaction_type == 'Leave Application':
			if leave_entry.from_date < getdate(from_date):
				leave_entry.from_date = from_date
			if leave_entry.to_date > getdate(to_date):
				leave_entry.to_date = to_date

			half_day = 0
			half_day_date = None
			# fetch half day date for leaves with half days
			if leave_entry.leaves % 1:
				half_day = 1
				half_day_date = frappe.db.get_value('Leave Application',
					{'name': leave_entry.transaction_name}, ['half_day_date'])

			leave_days += get_number_of_leave_days(employee, leave_type,
				leave_entry.from_date, leave_entry.to_date, half_day, half_day_date, holiday_list=leave_entry.holiday_list) * -1

	return leave_days

def skip_expiry_leaves(leave_entry, date):
	''' Checks whether the expired leaves coincide with the to_date of leave balance check.
		This allows backdated leave entry creation for non carry forwarded allocation '''
	end_date = frappe.db.get_value("Leave Allocation", {'name': leave_entry.transaction_name}, ['to_date'])
	return True if end_date == date and not leave_entry.is_carry_forward else False

def get_leave_entries(employee, leave_type, from_date, to_date):
	''' Returns leave entries between from_date and to_date. '''
	return frappe.db.sql("""
		SELECT
			employee, leave_type, from_date, to_date, leaves, transaction_name, transaction_type, holiday_list,
			is_carry_forward, is_expired
		FROM `tabLeave Ledger Entry`
		WHERE employee=%(employee)s AND leave_type=%(leave_type)s
			AND docstatus=1
			AND (leaves<0
				OR is_expired=1)
			AND (from_date between %(from_date)s AND %(to_date)s
				OR to_date between %(from_date)s AND %(to_date)s
				OR (from_date < %(from_date)s AND to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"employee": employee,
		"leave_type": leave_type
	}, as_dict=1)

@frappe.whitelist()
def get_holidays(employee, from_date, to_date, holiday_list = None):
	'''get holidays between two dates for the given employee'''
	if not holiday_list:
		holiday_list = get_holiday_list_for_employee(employee)

	holidays = frappe.db.sql("""select count(distinct holiday_date) from `tabHoliday` h1, `tabHoliday List` h2
		where h1.parent = h2.name and h1.holiday_date between %s and %s
		and h2.name = %s""", (from_date, to_date, holiday_list))[0][0]

	return holidays

def is_lwp(leave_type):
	lwp = frappe.db.sql("select is_lwp from `tabLeave Type` where name = %s", leave_type)
	return lwp and cint(lwp[0][0]) or 0

@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.desk.reportview import get_filters_cond
	events = []

	employee = frappe.db.get_value("Employee",
		filters={"user_id": frappe.session.user},
		fieldname=["name", "company"],
		as_dict=True
	)

	if employee:
		employee, company = employee.name, employee.company
	else:
		employee = ''
		company = frappe.db.get_value("Global Defaults", None, "default_company")

	conditions = get_filters_cond("Leave Application", filters, [])
	# show department leaves for employee
	if "Employee" in frappe.get_roles():
		add_department_leaves(events, start, end, employee, company)

	add_leaves(events, start, end, conditions)
	add_block_dates(events, start, end, employee, company)
	add_holidays(events, start, end, employee, company)

	return events

def add_department_leaves(events, start, end, employee, company):
	department = frappe.db.get_value("Employee", employee, "department")

	if not department:
		return

	# department leaves
	department_employees = frappe.db.sql_list("""select name from tabEmployee where department=%s
		and company=%s""", (department, company))

	filter_conditions = " and employee in (\"%s\")" % '", "'.join(department_employees)
	add_leaves(events, start, end, filter_conditions=filter_conditions)


def add_leaves(events, start, end, filter_conditions=None):
	from frappe.desk.reportview import build_match_conditions
	conditions = []

	if not cint(frappe.db.get_value("HR Settings", None, "show_leaves_of_all_department_members_in_calendar")):
		match_conditions = build_match_conditions("Leave Application")

		if match_conditions:
			conditions.append(match_conditions)

	query = """SELECT
		docstatus,
		name,
		employee,
		employee_name,
		leave_type,
		from_date,
		to_date,
		half_day,
		status,
		color
	FROM `tabLeave Application`
	WHERE
		from_date <= %(end)s AND to_date >= %(start)s <= to_date
		AND docstatus < 2
		AND status != 'Rejected'
	"""

	if conditions:
		query += ' AND ' + ' AND '.join(conditions)

	if filter_conditions:
		query += filter_conditions

	for d in frappe.db.sql(query, {"start":start, "end": end}, as_dict=True):
		e = {
			"name": d.name,
			"doctype": "Leave Application",
			"from_date": d.from_date,
			"to_date": d.to_date,
			"docstatus": d.docstatus,
			"color": d.color,
			"all_day": int(not d.half_day),
			"title": cstr(d.employee_name) + f' ({cstr(d.leave_type)})' + (' ' + _('(Half Day)') if d.half_day else ''),
		}
		if e not in events:
			events.append(e)


def add_block_dates(events, start, end, employee, company):
	# block days
	from hrms.hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

	cnt = 0
	block_dates = get_applicable_block_dates(start, end, employee, company, all_lists=True)

	for block_date in block_dates:
		events.append({
			"doctype": "Leave Block List Date",
			"from_date": block_date.block_date,
			"to_date": block_date.block_date,
			"title": _("Leave Blocked") + ": " + block_date.reason,
			"name": "_" + str(cnt),
		})
		cnt+=1

def add_holidays(events, start, end, employee, company):
	applicable_holiday_list = get_holiday_list_for_employee(employee, company)
	if not applicable_holiday_list:
		return

	for holiday in frappe.db.sql("""select name, holiday_date, description
		from `tabHoliday` where parent=%s and holiday_date between %s and %s""",
		(applicable_holiday_list, start, end), as_dict=True):
			events.append({
				"doctype": "Holiday",
				"from_date": holiday.holiday_date,
				"to_date":  holiday.holiday_date,
				"title": _("Holiday") + ": " + cstr(holiday.description),
				"name": holiday.name
			})

@frappe.whitelist()
def get_mandatory_approval(doctype):
	mandatory = ""
	if doctype == "Leave Application":
		mandatory = frappe.db.get_single_value('HR Settings',
				'leave_approver_mandatory_in_leave_application')
	else:
		mandatory = frappe.db.get_single_value('HR Settings',
				'expense_approver_mandatory_in_expense_claim')

	return mandatory

def get_approved_leaves_for_period(employee, leave_type, from_date, to_date):
	query = """
		select employee, leave_type, from_date, to_date, total_leave_days
		from `tabLeave Application`
		where employee=%(employee)s
			and docstatus=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	"""
	if leave_type:
		query += "and leave_type=%(leave_type)s"

	leave_applications = frappe.db.sql(query,{
		"from_date": from_date,
		"to_date": to_date,
		"employee": employee,
		"leave_type": leave_type
	}, as_dict=1)

	leave_days = 0
	for leave_app in leave_applications:
		if leave_app.from_date >= getdate(from_date) and leave_app.to_date <= getdate(to_date):
			leave_days += leave_app.total_leave_days
		else:
			if leave_app.from_date < getdate(from_date):
				leave_app.from_date = from_date
			if leave_app.to_date > getdate(to_date):
				leave_app.to_date = to_date

			leave_days += get_number_of_leave_days(employee, leave_type,
				leave_app.from_date, leave_app.to_date)

	return leave_days

@frappe.whitelist()
def get_leave_approver(employee):
	leave_approver, department = frappe.db.get_value("Employee",
		employee, ["leave_approver", "department"])

	if not leave_approver and department:
		leave_approver = frappe.db.get_value('Department Approver', {'parent': department,
			'parentfield': 'leave_approvers', 'idx': 1}, 'approver')

	return leave_approver
