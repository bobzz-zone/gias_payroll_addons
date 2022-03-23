# Copyright (c) 2022, das and contributors
# For license information, please see license.txt

import frappe
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from frappe.model.document import Document

class PengajuanLembur(Document):
	def validate(self):
		emp = frappe.get_doc("Employee",self.employee)
		if is_holiday(emp.holiday_list,self.tanggal_lembur):
			self.is_holiday=1
		else:
			self.is_holiday=0
		if (self.total_menit or 0) > 59 or (self.est_menit or 0) > 59:
			frappe.throw("Total Menit Tidak boleh lebih dari 1 jam")
		if self.est_menit and not self.total_menit:
			self.total_menit=self.est_menit
		if self.est_jam and not self.total:
			self.total=self.est_jam
		
