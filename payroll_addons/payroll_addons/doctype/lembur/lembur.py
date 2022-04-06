# Copyright (c) 2022, das and contributors
# For license information, please see license.txt

import frappe
import math
from frappe.model.document import Document

class Lembur(Document):
	@frappe.whitelist()
	def on_submit(self):
		sc = frappe.get_doc("Salary Component",self.salary_component)
		for row in self.data_lembur:
			employee = frappe.get_doc("Employee",row.employee)
			ads = frappe.new_doc("Additional Salary")
			ads.employee=employee.name
			ads.employee_name=employee.employee_name
			ads.company=employee.company
			ads.department=employee.department
			ads.salary_component=self.salary_component
			ads.type=sc.type
			ads.currency="IDR"
			ads.amount=row.total_value
			ads.payroll_date=self.payroll_date
			ads.deduct_full_tax_on_selected_payroll_date=self.deduct_full
			ads.is_recurring=0
			ads.ref_doctype="Lembur"
			ads.ref_docname=self.name
			#ads.save()
			ads.submit()
	def on_cancel(self):
		list_ads=frappe.db.sql("""select name from `tabAdditional Salary` where ref_doctype="Lembur" and ref_docname="{}" and docstatus=1 """.format(self.name),as_list=1)
		for row in list_ads:
			ads = frappe.get_doc("Additional Salary",row[0])
			ads.cancel()

	@frappe.whitelist()
	def get_data(self):
		if not self.from_date:
			frappe.throw("Siliahkan isi Periode Terlebih Dahulu")
		if not self.to_date:
			frappe.throw("Siliahkan isi Periode Terlebih Dahulu")
		if not self.branch:
			frappe.throw("Siliahkan isi data cabang Terlebih Dahulu")
		department=""
		if self.department:
			department=""" and department="{}" """.format(self.department)
		#get data pengajuan lembur yang ter approve
		data_lembur=frappe.db.sql("""select employee,employee_name,
			sum(IF(is_holiday=0,IF(total<2,total,2),0)) as biasa_jam_awal,sum(IF(is_holiday=0,IF(total<2,total_menit,0),0)) as biasa_menit_awal,
			sum(IF(is_holiday=0,IF(total<2,0,total-2),0)) as biasa_jam_akhir,sum(IF(is_holiday=0,IF(total<2,0,total_menit),0)) as biasa_menit_akhir,
			sum(IF(is_holiday=1,IF(total<2,total,2),0)) as libur_jam_awal,sum(IF(is_holiday=1,IF(total<2,total_menit,0),0)) as libur_menit_awal,
			sum(IF(is_holiday=1,IF(total<2,0,total-2),0)) as libur_jam_akhir,sum(IF(is_holiday=1,IF(total<2,0,total_menit),0)) as libur_menit_akhir
		 from `tabPengajuan Lembur` 
			where docstatus=1 and (lembur is NULL or lembur ="") and (tanggal_lembur >= "{}" and tanggal_lembur<="{}") and branch="{}" {} 
			group by employee""".format(self.from_date,self.to_date,self.branch,department),as_list=1)
		#clear data before set
		self.data_lembur_karyawan=[]
		grand_total=0
		data_nilai = frappe.get_single("Setting Biaya Lembur")
		for row in data_lembur:
			row_data={}
			#normalize value menit
			row_data["employee"]=row[0]
			row_data["employee_name"]=row[1]
			row_data["jam_hari_biasa_awal"]=row[2]+math.floor(row[3]/60)
			row_data["menit_hari_biasa_awal"]=row[3]%60
			row_data["jam_hari_biasa_akhir"]=row[4]+math.floor(row[5]/60)
			row_data["menit_hari_biasa_akhir"]=row[5]%60
			row_data["jam_hari_libur_awal"]=row[6]+math.floor(row[7]/60)
			row_data["menit_hari_libur_awal"]=row[7]%60
			row_data["jam_hari_libur_akhir"]=row[8]+math.floor(row[9]/60)
			row_data["menit_hari_libur_akhir"]=row[9]%60

			total_value=0
			total_value+=data_nilai.biasa_jam_awal*row_data["jam_hari_biasa_awal"]
			total_value+=data_nilai.biasa_menit_awal*row_data["menit_hari_biasa_awal"]
			total_value+=data_nilai.biasa_jam_akhir*row_data["jam_hari_biasa_akhir"]
			total_value+=data_nilai.biasa_menit_akhir*row_data["menit_hari_biasa_akhir"]
			total_value+=data_nilai.libur_jam_awal*row_data["jam_hari_libur_awal"]
			total_value+=data_nilai.libur_menit_awal*row_data["menit_hari_libur_awal"]
			total_value+=data_nilai.libur_jam_akhir*row_data["jam_hari_libur_akhir"]
			total_value+=data_nilai.libur_menit_akhir*row_data["menit_hari_libur_akhir"]

			row_data["total_value"]=total_value
			grand_total+=total_value
			self.append("data_lembur_karyawan",row_data)
		self.total_cost=grand_total

