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
		if (self.total_menit or 0) > 59 :
			frappe.throw("Total Menit Tidak boleh lebih dari 1 jam")
		#if self.est_menit and not self.total_menit:
		#	self.total_menit=self.est_menit
		#if self.est_jam and not self.total:
		#	self.total=self.est_jam
		out_time=frappe.db.sql("""select out_time,out_time_detail,in_time,in_time_detail from `tabAttendance` where employee="{}" and attendance_date="{}" and docstatus=1  """,as_list=1)
		if out_time and out_time[0]:
			self.checkout=out_time[0][0]
			self.checkin=in_time[0][2]
			ci=out_time[0][3].split(":")
			co=out_time[0][1].split(":")
			ji = emp.jam_masuk-int(ci[0])
			mi = 0
			if ji > 0:
				mi = emp.menit_masuk - int(ci[1])
			jo=int(co[0]) - 18
			mo=int(co[1])

			#buat jo jadi total
			jo=jo+ji
			if mo+mi <0:
				mo=60-(mo+mi)
				jo=jo-1
			if jo < 0:
				frappe.throw("Pada tanggal ini tidak terlihat lembur dari waktu absen lebih dari seharusnya")
			elif jo < self.total:
				frappe.throw("Pengajuan Lembur tidak boleh lebih dari jam attendance")
				#self.total=jo
				#self.total_menit=mo
			elif jo == self.total and mo < self.total_menit:
				frappe.throw("Pengajuan Lembur tidak boleh lebih dari jam attendance")
				#self.total_menit=mo
				#self.total=jo
