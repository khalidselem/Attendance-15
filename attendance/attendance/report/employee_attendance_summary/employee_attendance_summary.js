// Copyright (c) 2022, Peter Maged and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Attendance Summary"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      reqd: 1,
    },
    {
      fieldname: "attendance_calculation",
      label: __("Attendance Calculation"),
      fieldtype: "Link",
      options: "Attendance Calculation",
      reqd: 1,
      on_change: function (query_report) {
        var attendance_calculation =
          query_report.get_values().attendance_calculation;
        if (!attendance_calculation) {
          return;
        }
        frappe.model.with_doc(
          "Attendance Calculation",
          attendance_calculation,
          function (r) {
            var fy = frappe.model.get_doc(
              "Attendance Calculation",
              attendance_calculation
            );
            frappe.query_report.set_filter_value({
              from_date: fy.payroll_start_date,
              to_date: fy.payroll_end_date,
            });
          }
        );
      },
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      read_only: 1,
      // reqd: 1,
      // default: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      read_only: 1,
      // reqd: 1,
      // default: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0),
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee",
      get_query: () => {
        var company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            company: company,
          },
        };
      },
    },

    {
      fieldname: "branch",
      label: __("Branch"),
      fieldtype: "Link",
      options: "Branch",
    },

    {
      fieldname: "department",
      label: __("Department"),
      fieldtype: "Link",
      options: "Department",
    },

    {
      fieldname: "grade",
      label: __("Grade"),
      fieldtype: "Link",
      options: "Grade",
    },
    {
      fieldname: "designation",
      label: __("Designation"),
      fieldtype: "Link",
      options: "Designation",
    },
  ],
};
