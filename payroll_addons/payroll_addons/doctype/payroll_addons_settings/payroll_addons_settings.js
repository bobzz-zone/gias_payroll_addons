// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payroll Addons Settings', {
	// refresh: function(frm) {

	// }
	validate: function(frm){
		if(frm.doc.tanggal_awal_tunjangan){
			if(frm.doc.tanggal_awal_tunjangan > 31){
				frappe.throw("Tanggal tidak boleh melebihi 31.")
			}
		}
		if(frm.doc.tanggal_akhir_tunjangan){
			if(frm.doc.tanggal_akhir_tunjangan > 31){
				frappe.throw("Tanggal tidak boleh melebihi 31.")
			}
		}

	}
});
