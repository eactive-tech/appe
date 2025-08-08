import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.desk.query_report import run
from frappe.core.doctype.prepared_report.prepared_report import make_prepared_report
import json
from datetime import date



class AppePreparedReport(Document):
	def after_insert(self):
		try:
			report_name = self.report
			filters = json.loads(self.filters or "{}") if isinstance(self.filters, str) else self.filters
			report_doc = frappe.get_doc("Report", report_name)

			self.queued_by = frappe.session.user
			self.queued_at = now_datetime()

			if report_doc.prepared_report:
				# Prepared Report (Queued)
				try:
					prepared_doc = make_prepared_report(report_name, filters)
					frappe.log_error("Prepare report data",prepared_doc)
					self.prepared_report = prepared_doc.get('name')
					self.status = "Queued"
				except Exception as e:
					self.status = "Error"
					self.error_message = str(e)
					frappe.log_error("Appe Prepared Report: make_prepared_report failed", str(e))

			else:
				# Standard Report (Run Immediately)
				try:
					result = run(report_name, filters)
					frappe.log_error("Appe Prepared Report: run failed",result)
					# self.results = json.dumps(result)
					def date_converter(o):
						if isinstance(o, date):
							return o.isoformat()  # Convert date to ISO format string
					# Convert JSON object to string
					self.results = json.dumps(result, default=date_converter)


					self.status = "Completed"
					self.finished_at = now_datetime()
				except Exception as e:
					self.status = "Error"
					self.error_message = str(e)
					frappe.log_error("Appe Prepared Report: run failed", str(e))

		except Exception as outer_e:
			self.status = "Error"
			self.error_message = str(outer_e)
			frappe.log_error("Appe Prepared Report: general failure",str(outer_e))

		# Finally save the doc with updated status, result, etc.
		self.db_update()
