import frappe
import requests
from frappe import _
from frappe.model.document import Document

AZURE_FACE_API_KEY = "ASRHyGHeb535SMMrPxwpsaPyw6FfLtEG4v9zcfgpv3fGCEsy3B3vJQQJ99BCACGhslBXJ3w3AAAKACOGJdtK"
AZURE_FACE_ENDPOINT = "https://mkameshinstance.cognitiveservices.azure.com/"
HEADERS = {"Ocp-Apim-Subscription-Key": AZURE_FACE_API_KEY, "Content-Type": "application/json"}

@frappe.whitelist(allow_guest=True)
def create_person_group(group_id, group_name):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}"
    payload = {"name": group_name}
    response = requests.put(url, json=payload, headers=HEADERS)
    return response.json()

@frappe.whitelist()
def update_person_group(group_id, group_name=None, user_data=None):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}"
    payload = {}
    if group_name:
        payload["name"] = group_name
    if user_data:
        payload["userData"] = user_data
    response = requests.patch(url, json=payload, headers=HEADERS)
    return response.json()

@frappe.whitelist()
def delete_person_group(group_id):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}"
    response = requests.delete(url, headers=HEADERS)
    return response.json()

@frappe.whitelist()
def add_person(group_id, person_name, user_data=None):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}/persons"
    payload = {"name": person_name, "userData": user_data}
    response = requests.post(url, json=payload, headers=HEADERS)
    return response.json()

@frappe.whitelist()
def add_face(group_id, person_id, image_url):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}/persons/{person_id}/persistedFaces"
    payload = {"url": image_url}
    response = requests.post(url, json=payload, headers=HEADERS)
    return response.json()

@frappe.whitelist()
def update_person(group_id, person_id, person_name=None, user_data=None):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}/persons/{person_id}"
    payload = {}
    if person_name:
        payload["name"] = person_name
    if user_data:
        payload["userData"] = user_data
    response = requests.patch(url, json=payload, headers=HEADERS)
    return response.json()

@frappe.whitelist()
def delete_person(group_id, person_id):
    url = f"{AZURE_FACE_ENDPOINT}/face/v1.0/persongroups/{group_id}/persons/{person_id}"
    response = requests.delete(url, headers=HEADERS)
    return response.json()
