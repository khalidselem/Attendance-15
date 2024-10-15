frappe.ui.form.on('Shift Type', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__('Assign to Employees'), function () {
        frm.trigger('assign_to_employees');
      });
    }
  },
  assign_to_employees: function (frm) {
    var d = new frappe.ui.Dialog({
      title: __('Assign to Employees'),
      fields: [
        {
          fieldname: 'sec_break',
          fieldtype: 'Section Break',
          label: __('Filter Employees By (Optional)'),
        },
        {
          fieldname: 'company',
          fieldtype: 'Link',
          options: 'Company',
          label: __('Company'),
        },
        {
          fieldname: 'grade',
          fieldtype: 'Link',
          options: 'Employee Grade',
          label: __('Employee Grade'),
        },
        {
          fieldname: 'department',
          fieldtype: 'Link',
          options: 'Department',
          label: __('Department'),
        },
        {
          fieldname: 'designation',
          fieldtype: 'Link',
          options: 'Designation',
          label: __('Designation'),
        },
        {
          fieldname: 'employee',
          fieldtype: 'Link',
          options: 'Employee',
          label: __('Employee'),
        },
        { fieldname: 'period_section', fieldtype: 'Section Break' },
        {
          fieldname: 'from_date',
          fieldtype: 'Date',
          label: __('From Date'),
          reqd: 1,
        },
        { fieldname: 'to_date_col_br', fieldtype: 'Column Break' },
        {
          fieldname: 'to_date',
          fieldtype: 'Date',
          label: __('To Date'),
          reqd: 0,
        },
      ],
      primary_action: function () {
        var data = d.get_values();
        data.shift_type = frm.doc.name;
        frappe.call({
          method: 'attendance.apis.shift_type.assign_shift_type',
          args: data,
          callback: function (r) {
            if (!r.exc) {
              d.hide();
              frm.reload_doc();
            }
          },
        });
      },
      primary_action_label: __('Assign'),
    });

    d.show();
  },
});
