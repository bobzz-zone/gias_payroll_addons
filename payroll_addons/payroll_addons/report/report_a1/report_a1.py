# Copyright (c) 2013, das and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict
import datetime
from datetime import date

def execute(filters=None):
	columns, data = ["Masa Pajak:Data:100","Tahun Pajak:Data:100","Pembetulan:Data:100","Nomor Bukti Potong:Data:100","Masa Perolehan Awal:Data:100","Masa Perolehan Akhir:Data:100","NPWP:Data:100","NIK:Data:100","Nama:Data:100","Alamat:Data:100","Jenis Kelamin:Data:100","Status PTKP:Data:100","Jumlah Tanggungan:Data:100","Nama Jabatan:Data:100","WP Luar Negeri:Data:100","Kode Negara:Data:100","Kode Pajak:Data:100","Jumlah 1:Currency:100","Jumlah 2:Currency:100","Jumlah 3:Currency:100","Jumlah 4:Currency:100","Jumlah 5:Currency:100","Jumlah 6:Currency:100","Jumlah 7:Currency:100","Jumlah 8:Currency:100","Jumlah 9:Currency:100","Jumlah 10:Currency:100","Jumlah 11:Currency:100","Jumlah 12:Currency:100","Jumlah 13:Currency:100","Jumlah 14:Currency:100","Jumlah 15:Currency:100","Jumlah 16:Currency:100","Jumlah 17:Currency:100","Jumlah 18:Currency:100","Jumlah 19:Currency:100","Jumlah 20:Currency:100","Status Pindah:Data:100","NPWP Pemotong:Data:100","Nama Pemotong:Data:100","Tanggal Bukti Potong:Date:100"], []
	#get fiscal period
	fiscal=filters.get("year")
	period = frappe.get_doc("Fiscal Year",fiscal)
	#golongan A1 , 1 = jumlah 1 , 3 = jumlah 3 ,5 = jumlah 5,7 = jumlah 7
	slip_data=frappe.db.sql("""select c.golongan_a1,sum(sd.amount) as "total",sl.employee 
			from `tabSalary Detail` sd left join `tabSalary Component` c on sd.salary_component = c.name left join `tabSalary Slip` sl on sl.name=sd.parent
			where sd.parenttype="Salary Slip" and sl.docstatus=1 and c.golongan_a1 is not NULL and sl.end_date >= "{0}" and sl.end_date <= "{1}" and sl.branch="{2}"
			group by sl.employee,c.golongan_a1
			""".format(period.year_start_date,period.year_end_date, filters.get("branch")),as_dict=1)
	amount_detail={}
	for row in slip_data:
		if row.employee not in amount_detail:
			amount_detail[row.employee]={}
			amount_detail[row.employee]["1"]=0
			amount_detail[row.employee]["3"]=0
			amount_detail[row.employee]["5"]=0
			amount_detail[row.employee]["7"]=0
			amount_detail[row.employee]["17"]=0
			amount_detail[row.employee]["9"]=0
			amount_detail[row.employee]["10"]=0
		amount_detail[row.employee][cstr(row.golongan_a1)]=flt(row.total)
	#get employee dengan salary slip yang ada pada tahun terpilih, dan ambil bulan awal , dan akir salary slip pada cabang tersebut
	employee_list = frappe.db.sql(""" select MIN(MONTH(sl.end_date)) as "awal",MAX(MONTH(sl.end_date)) as "akhir",sl.employee,
				e.nomor_npwp,e.nomor_ktp,e.gender,e.employee_name,e.employment_type , e.permanent_address
			from `tabSalary Slip` sl
			left join tabEmployee e on sl.employee=e.name
			where sl.end_date >= "{0}" and sl.end_date <= "{1}" and sl.branch="{2}" and sl.docstatus=1
			group by sl.employee
		""".format(period.year_start_date,period.year_end_date, filters.get("branch")),as_dict=1)
	
	#get salary details untuk employee yang ada dan bentuk laporannya
	check_past=[]
	details={}
	for row in employee_list:
		details[row.employee]=row
		if flt(row.awal)>1:
			check_past.append([row.employee,row.awal])
	#get data PTKP
	employee_ptkp={}
	data_ptkp=frappe.db.sql("""select ssa.employee,ssa.from_date, ssa.income_tax_slab ,tss.from_amount
		from `tabSalary Structure Assignment` ssa left join tabEmployee e on e.name=ssa.employee left join `tabTaxable Salary Slab` tss on tss.parent=ssa.income_tax_slab and tss.idx=1
		where e.branch="{1}" and ssa.from_date <"{0}" and ssa.docstatus=1 and ssa.from_date in (select max(from_date) from `tabSalary Structure Assignment` ssa2 where ssa2.employee=ssa.employee and ssa2.from_date <"{0}" and ssa2.docstatus=1)
	""".format(period.year_end_date, filters.get("branch")),as_dict=1)
	for row in data_ptkp:
		employee_ptkp[row.employee]={}
		employee_ptkp[row.employee]["ptkp_value"]=row.from_amount
		employee_ptkp[row.employee]["tanggungan"]=row.income_tax_slab[-1:]
		employee_ptkp[row.employee]["ptkp"]=row.income_tax_slab.strip(employee_ptkp[row.employee]["tanggungan"])
	#get salary total untk gaji cabang sebelumnya jika ada yang start pointnya di bawah bulan mulainya
	past={}
	for row in check_past:
		past_slip_data=frappe.db.sql("""select c.golongan_a1,sum(sd.amount) as "total",sl.employee 
			from `tabSalary Detail` sd left join `tabSalary Component` c on sd.salary_component = c.name left join `tabSalary Slip` sl on sl.name=sd.parent
			where sd.parenttype="Salary Slip" and sd.docstatus=1 and c.golongan_a1 is not NULL and sl.end_date >= "{0}" and sl.end_date <= "{1}" and sl.branch!="{2}" and sl.employee="{3}" and month(sl.end_date) < {4}
			group by sl.employee,c.golongan_a1
			""".format(period.year_start_date,period.year_end_date, filters.get("branch"),row[0],row[1]),as_dict=1)
		past[row[0]]={}
		past[row[0]]["1"]=0
		past[row[0]]["3"]=0
		past[row[0]]["5"]=0
		past[row[0]]["7"]=0
		past[row[0]]["17"]=0
		past[row[0]]["9"]=0
		past[row[0]]["10"]=0
		for past_slip in past_slip_data:
			past[row[0]][cstr(past_slip.golongan_a1)]=flt(past_slip.total)
	format_bupot="1.1-12.{}-".format(cstr(fiscal)[-2:])
	n=1
	for row in details:
		#["Masa Pajak","Tahun Pajak,Pembetulan:Data:100","Nomor Bukti Potong:Data:100","Masa Perolehan Awal:Data:100","Masa Perolehan Akhir:Data:100","NPWP:Data:100","NIK:Data:100","Nama:Data:100","Alamat","Jenis Kelamin","Status","Jumlah Tanggungan","Nama Jabatan","WP Luar Negeri","Kode Negara","Kode Pajak","Jumlah 1:Currency:100","Jumlah 2:Currency:100","Jumlah 3:Currency:100","Jumlah 4:Currency:100","Jumlah 5:Currency:100","Jumlah 6:Currency:100","Jumlah 7:Currency:100","Jumlah 8:Currency:100","Jumlah 9:Currency:100","Jumlah 10:Currency:100","Jumlah 11:Currency:100","Jumlah 12:Currency:100","Jumlah 13:Currency:100","Jumlah 14:Currency:100","Jumlah 15:Currency:100","Jumlah 16:Currency:100","Jumlah 17:Currency:100","Jumlah 18:Currency:100","Jumlah 19:Currency:100","Jumlah 20:Currency:100","Status Pindah:Data:100","NPWP Pemotong:Data:100","Nama Pemotong:Data:100","Tanggal Bukti Potong:Date:100"]
		if not row in employee_ptkp:
			frappe.throw("PTKP Issue")
		if not row in amount_detail:
			frappe.throw("Amount Detail Issue")
		if not row in details:
			frappe.throw("Details Issue")
		if not row in past:
			past[row]={}
			past[row]["1"]=0
			past[row]["3"]=0
			past[row]["5"]=0
			past[row]["7"]=0
			past[row]["17"]=0
			past[row]["9"]=0
			past[row]["10"]=0
		row8=amount_detail[row]["1"]+amount_detail[row]["3"]+amount_detail[row]["5"]+amount_detail[row]["7"]
		row11=(amount_detail[row]["9"]+amount_detail[row]["10"])*-1
		row13=(past[row]["1"]+past[row]["3"]+past[row]["5"]+past[row]["7"])-((past[row]["9"]+past[row]["10"])*-1)
		row16=row8-row11+row13-flt(employee_ptkp[row]['ptkp_value'])
		if row16<0:
			row16=0
		data.append(["12",fiscal,"0","{}{:07n}".format(format_bupot,n),details[row].awal,details[row].akhir,details[row].nomor_npwp or "000000000000000",row,details[row].employee_name,details[row].permanent_address,details[row].gender[0],employee_ptkp[row]['ptkp'],employee_ptkp[row]['tanggungan'],details[row].employment_type,"N","0","21-100-01",amount_detail[row]["1"],"0",amount_detail[row]["3"],"0",amount_detail[row]["5"],"0",amount_detail[row]["7"],row8,(amount_detail[row]["9"]*-1),(amount_detail[row]["10"]*-1),row11,row8-row11,row13,row8-row11+row13,employee_ptkp[row]['ptkp_value'],row16,amount_detail[row]["17"],past[row]["17"],amount_detail[row]["17"]+past[row]["17"],amount_detail[row]["17"]+past[row]["17"],"","796000000000000","IRWAN RUSDI",period.year_end_date])
		n=n+1
	return columns, data
