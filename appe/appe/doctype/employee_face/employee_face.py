# Copyright (c) 2025, kamesh and contributors
# For license information, please see license.txt

from io import BytesIO
import frappe
from frappe.model.document import Document
from appe.azure_face_api import create_person, add_face_to_person, train_group, get_group, create_group
import face_recognition
import requests
import numpy as np
import pickle
import base64



class EmployeeFace(Document):
    
	def before_insert(self):
		# Check if person group exists
		group = get_group("employees")
		if group.get("error"):
			frappe.log_error("Person group not found, creating: employees")
			created = create_group("employees", "Employees")
			frappe.log_error(f"Person group created", f"{created}")
		else:
			frappe.log_error("Person group found: employees",group)

		# Create Person in Azure
		person = create_person("employees", self.employee_id)
		frappe.log_error(f"Person created in Azure", f"{person}")

		# Add Face
		face_data = add_face_to_person("employees", person["personId"], self.face_image)
		frappe.log_error(f"Face added to person",f" {face_data}")

		# Start Training Group
		training_status = train_group("employees")
		frappe.log_error(f"Person group trained. Status",f" {training_status}")

		# Save Azure face id
		self.azure_face_id = face_data["persistedFaceId"]
		self.person_group_id = "employees"
		self.person_id = person["personId"]
    
	def before_save(self):
		try:
			face_image_path = self.face_image
			employee_id = self.employee_id

			if not face_image_path:
				frappe.msgprint("No face image found.")
				return

			# Construct full image URL
			site_url = frappe.utils.get_url()
			full_url = f"{site_url}{face_image_path}"

			# Download image
			response = requests.get(full_url)
			if response.status_code != 200:
				frappe.throw(f"Could not download image for employee {employee_id}")

			# Load image into memory (no need to save temp file)
			image = face_recognition.load_image_file(BytesIO(response.content))
			encodings = face_recognition.face_encodings(image)

			if not encodings:
				frappe.throw("No face detected in image.")

			encoding = encodings[0]

			# Save face encoding as base64(pickle)
			encoded_bytes = pickle.dumps(encoding)
			self.face_encoding = base64.b64encode(encoded_bytes).decode('utf-8')

			frappe.logger().info(f"✅ Face enrolled for {employee_id}")

		except Exception as e:
			frappe.log_error("Enroll Employee Error", f"❌ Error enrolling face for {self.employee_id}: {e}")
			frappe.throw(f"Face enrollment failed: {e}")
    