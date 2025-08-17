# Copyright (c) 2025, Kamesh and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MobileAppNotification(Document):
	def after_insert(self):
		try:
			onesignal_api_key = frappe.db.get_single_value('Appe Settings','onesignal_api_key')
			app_id = frappe.db.get_single_value('Appe Settings','onesignal_app_id')
			if onesignal_api_key and app_id:
				url = "https://api.onesignal.com/notifications?c=push"
				headers = {
					"Content-Type": "application/json; charset=utf-8",
					"Authorization": f"Basic {onesignal_api_key}"
				}
				receipt = [str(d.mobile_no) for d in doc.users if d.mobile_no]
				payload = {
					"app_id": app_id,
					"include_external_user_ids": receipt,
					"channel_for_external_user_ids": "push",
					
					"headings": {"en": str(doc.title)},
					"contents": {"en": str(doc.message)},
					"data": json.loads(doc.data)
				}
				
				if doc.big_picture:
					url = frappe.utils.get_url()
					payload["big_picture"] = f"{url}{str(doc.big_picture)}"
					payload["ios_attachments"] = {"id": f"{url}{str(doc.big_picture)}"}

				# frappe.log_error("Sending OneSignal Payload", json.dumps(payload))
				response = frappe.make_post_request(url, data=json.dumps(payload), headers=headers)
				# frappe.log_error("OneSignal Response", f"{response.status_code}: {response.text}")
			else:
				frappe.throw("OneSignal API Key or App ID not configured in Appe Settings")
				
		except Exception as e:
			frappe.log_error("Mobile app notification error", f"{e}")
			frappe.throw(f"{e}")