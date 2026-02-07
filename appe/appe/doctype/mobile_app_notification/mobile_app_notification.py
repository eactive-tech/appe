# Copyright (c) 2025, Kamesh and contributors
# For license information, please see license.txt

import frappe
import json
import requests
from frappe.model.document import Document


class MobileAppNotification(Document):
	def before_submit(self):
		onesignal_api_key = frappe.db.get_single_value('Appe Settings','onesignal_api_key')
		app_id = frappe.db.get_single_value('Appe Settings','onesignal_app_id')

		if onesignal_api_key and app_id:
			url = "https://api.onesignal.com/notifications?c=push"
			headers = {
				"Content-Type": "application/json; charset=utf-8",
				"Authorization": f"Basic {onesignal_api_key}"
			}
			receipt = [str(d.user) for d in self.users if d.user]
			payload = {
				"app_id": app_id,
				"include_external_user_ids": receipt,
				"channel_for_external_user_ids": "push",
				
				"headings": {"en": self.title},
				"contents": {"en": self.message},
			}
			
			if self.big_picture:
				site_url = frappe.utils.get_url()
				big_picture = f"{site_url}{str(self.big_picture)}"
				payload["big_picture"] = big_picture
				payload["ios_attachments"] = {"id": big_picture}


			j = json.dumps(payload)
			# frappe.log_error("Sending OneSignal Payload", json.dumps(payload))
			response = requests.post(url, data=j, headers=headers)
			frappe.log_error("OneSignal Response", f"{response.status_code}: {response.text}")
		else:
			frappe.throw("OneSignal API Key or App ID not configured in Appe Settings")