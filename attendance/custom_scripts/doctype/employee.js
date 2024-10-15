frappe.ui.form.on('Employee', {
  setup(frm) {
    setTimeout(() => frm.events.set_queries(frm), 100);
  },
  set_queries(frm) {
    frm.set_query('management', function () {
      return {
        filters: {
          is_group: 1,
          //   company: frm.doc.company,
        },
      };
    });
    frm.set_query('department', function () {
      return {
        filters: {
          is_group: 0,
          parent_department: frm.doc.management,
          company: frm.doc.company,
        },
      };
    });
    frm.set_query('unit', function () {
      return {
        filters: {
          department: frm.doc.department,
        },
      };
    });
    frm.set_query('designation', function () {
      return {
        filters: {
          department: ['in', ['', frm.doc.department]],
        },
      };
    });
  },
//   date_of_birth(frm) {
//     frm.call({
//       method: 'attendance.overrides.employee.set_employee_age',
//       args: { doc: frm.doc },
//       callback: function () {
//         frm.refresh_fields(['age_years', 'age_months', 'age_days']);
//       },
//     });
//   },
});
