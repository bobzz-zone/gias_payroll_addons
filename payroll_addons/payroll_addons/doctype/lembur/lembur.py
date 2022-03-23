# Copyright (c) 2022, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Lembur(Document):
	@frappe.whitelist()
	def get_data(self):
		frappe.msgprint("Called")
