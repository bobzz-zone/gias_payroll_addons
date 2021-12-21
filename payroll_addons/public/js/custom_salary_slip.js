frappe.ui.form.on('Salary Slip', {
	refresh(frm) {
		frm.doc.ijin_unpaid_days = 0
	}
})