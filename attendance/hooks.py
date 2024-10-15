from . import __version__ as app_version

app_name = "attendance"
app_title = "Attendance"
app_publisher = "Peter Maged"
app_description = "Attendance"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "eng.peter.maged@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/attendance/css/attendance.css"
# app_include_js = "/assets/attendance/js/attendance.js"

# include js, css files in header of web template
# web_include_css = "/assets/attendance/css/attendance.css"
# web_include_js = "/assets/attendance/js/attendance.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "attendance/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Attendance": "attendance/doctype/attendance/attendance.js",
    # "Payroll Entry": "attendance/doctype/payroll_entry/payroll_entry.js",
    "Shift Type": "custom_scripts/doctype/shift_type.js",
    "Employee": "custom_scripts/doctype/employee.js"
}
doctype_list_js = {
    "Attendance": "attendance/doctype/attendance/attendance_list.js",
    "Leave Policy Assignment": "attendance/doctype/leave_policy_assignment/leave_policy_assignment_list.js"
    }
doctype_calendar_js = {
    "Attendance": "attendance/doctype/attendance/attendance_calender.js"}


# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "attendance.install.before_install"
# after_install = "attendance.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "attendance.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes
override_doctype_dashboards = {
    "Attendance": "attendance.attendance.doctype.attendance.attendance_dashboard.get_data"
}
override_doctype_class = {
    "Attendance": "attendance.attendance.doctype.attendance.attendance.Attendance",
    # "Salary Slip": "attendance.attendance.doctype.salary_slip.salary_slip.SalarySlip",
    "Salary Slip": "attendance.attendance.doctype.salary_slip.salary_slip.AttendanceSalarySlip",
    # "Payroll Entry": "attendance.attendance.doctype.payroll_entry.payroll_entry.PayrollEntry",
    "Leave Application": "attendance.attendance.doctype.leave_application.leave_application.AttendanceLeaveApplication",
    # "Payroll Entry": "attendance.attendance.doctype.payroll_entry.payroll_entry.PayrollEntry",
    # "Payroll Entry": "attendance.attendance.doctype.payroll_entry.attendance_payroll_entry.PayrollEntry",
    "Attendance Request": "attendance.attendance.doctype.attendance_request.attendance_request.AttendanceRequest",
    # "Leave Policy Assignment": "attendance.attendance.doctype.leave_policy_assignment.leave_policy_assignment.LeavePolicyAssignment",
    "Payroll Period": "attendance.attendance.doctype.payroll_period.payroll_period.CustomPayrollPeriod" ,
    "Loan Repayment" : "attendance.overrides.loan_repayment.CustomLoanRepayment" ,
    "Leave Encashment" : "attendance.overrides.leave_encashment.CustomLeaveEncashment"
}


after_migrate = [
    "attendance.attendance.setup.after_migrate"]

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Activity Type": {
        "validate": "attendance.utils.utils.add_salary_component_from_activity_type",
    },
    "Timesheet": {
        "on_submit": "attendance.utils.utils.add_additional_salary_component_from_activity_type",
        "on_cancel": "attendance.utils.utils.cancel_additional_salary_component_from_activity_type",
    },
    "Employee": {
        "validate": "attendance.overrides.employee.validate",
    },
    "Employee Checkin": {
        "on_change": "attendance.doc_events.employee_checkin.on_change",
        "on_trash": "attendance.doc_events.employee_checkin.on_trash",
    },
    "Leave Application": {
        "before_insert": "attendance.api.before_insert",
        "validate": "attendance.api.validate",
    },
    "Daily Overtime Request": {
        "before_insert": "attendance.api.before_insert",
        "validate": "attendance.api.validate",
    },
    "Visit Form": {
        "before_insert": "attendance.api.before_insert",
        "validate": "attendance.api.validate",
    },
    "Permission Application": {
        "before_insert": "attendance.api.before_insert",
        "validate": "attendance.api.validate",
    },
    "Salary Slip": {
        "validate": "attendance.api.validate_salary_slip",
        "on_update": "attendance.api.validate_salary_slip",
    },
    "Stock Entry": {
        "on_submit": "attendance.attendance.doctype.scrub_form.scrub_form.on_submit_stock_entry"
    },
    "Payroll Entry": {
        "on_submit": "attendance.attendance.doctype.scrub_form.scrub_form.set_payroll_entry_status",
        "on_cancel": "attendance.attendance.doctype.scrub_form.scrub_form.set_payroll_entry_status"
    }

}

# Scheduled Tasks
# ---------------

scheduler_events = {
    # 	"all": [
    # 		"attendance.tasks.all"
    # 	],
    "daily": [
        "attendance.api.update_employee_birth_date",
    ],
    "hourly": [
            "attendance.attendance.doctype.leave_policy_assignment.leave_policy_assignment.renew_expired_allocation" ,
            "attendance.doc_events.employee_checkin.async_calc_attendance_for_employee"
        # "attendance.attendance.doctype.scrub_form.scrub_form.return_scrub_forms"
    ],
    # 	"weekly": [
    # 		"attendance.tasks.weekly"
    # 	]
    # 	"monthly": [
    # 		"attendance.tasks.monthly"
    # 	]
    "cron": {
        "* */1 * * *": [
            "attendance.api.update_salary_slip_remark",
            "attendance.api.update_foreign_employee"

        ]
    }


}

# Testing
# -------

# before_tests = "attendance.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "attendance.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps


# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
    {
        "doctype": "{doctype_1}",
        "filter_by": "{filter_by}",
        "redact_fields": ["{field_1}", "{field_2}"],
        "partial": 1,
    },
    {
        "doctype": "{doctype_2}",
        "filter_by": "{filter_by}",
        "partial": 1,
    },
    {
        "doctype": "{doctype_3}",
        "strict": False,
    },
    {
        "doctype": "{doctype_4}"
    }
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"attendance.auth.validate"
# ]
