import frappe
import requests
from frappe import _
from frappe.model.document import Document


AZURE_ENDPOINT = "https://centralindia.api.cognitive.microsoft.com/face/v1.0"
AZURE_KEY = "58c1f31f11884c3882bee8540e49e3c4"
PERSON_GROUP_ID = "employees"

headers = {
    "Ocp-Apim-Subscription-Key": AZURE_KEY,
    "Content-Type": "application/json"
}

def create_group(group_id, name):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}"
    body = { "name": name }
    res = requests.put(url, headers=headers, json=body)
    return res.status_code == 200

def get_group(group_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}"
    res = requests.get(url, headers=headers)
    return res.json()
def list_groups():
    url = f"{AZURE_ENDPOINT}/persongroups"
    res = requests.get(url, headers=headers)
    return res.json()
def delete_group(group_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}"
    res = requests.delete(url, headers=headers)
    return res.status_code == 200
def create_person(group_id, name, user_data=""):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/persons"
    body = { "name": name, "userData": user_data }
    res = requests.post(url, headers=headers, json=body)
    return res.json()  # personId
def get_person(group_id, person_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/persons/{person_id}"
    res = requests.get(url, headers=headers)
    return res.json()
def list_persons(group_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/persons"
    res = requests.get(url, headers=headers)
    return res.json()
def delete_person(group_id, person_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/persons/{person_id}"
    res = requests.delete(url, headers=headers)
    return res.status_code == 200
def add_face_to_person(group_id, person_id, image_url):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/persons/{person_id}/persistedFaces"
    body = { "url": image_url }
    res = requests.post(url, headers=headers, json=body)
    return res.json()  # persistedFaceId
def delete_face(group_id, person_id, face_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/persons/{person_id}/persistedFaces/{face_id}"
    res = requests.delete(url, headers=headers)
    return res.status_code == 200

def train_group(group_id):
    url = f"{AZURE_ENDPOINT}/persongroups/{group_id}/train"
    response = requests.post(url, headers=headers)
    return response.status_code

@frappe.whitelist()
def create_employee_face(employee_id, image_url):
    person = create_person("employees", employee_id)
    face_data = add_face_to_person("employees", person["personId"], image_url)
    train_group("employees")

    doc = frappe.new_doc("Employee Face")
    doc.employee_id = employee_id
    doc.face_image = image_url
    doc.azure_face_id = person["personId"]
    doc.insert()
    return doc

def detect_face(image_url):
    url = f"{AZURE_ENDPOINT}/detect"
    params = {
        "returnFaceId": "true"
    }
    body = { "url": image_url }
    res = requests.post(url, headers=headers, params=params, json=body)
    return res.json()

def identify_face(group_id, face_ids, max_candidates=1):
    url = f"{AZURE_ENDPOINT}/identify"
    body = {
        "personGroupId": group_id,
        "faceIds": face_ids,
        "maxNumOfCandidatesReturned": max_candidates
    }
    res = requests.post(url, headers=headers, json=body)
    return res.json()

@frappe.whitelist(allow_guest=True)
def authenticate_employee_face(image_url):
    # Step 1: Detect face in the image
    detected = detect_face(image_url)
    if not detected or "error" in detected or len(detected) == 0:
        return {"success": False, "message": "No face detected or invalid image."}
    face_ids = [face["faceId"] for face in detected]

    # Step 2: Identify face in the employees group
    identified = identify_face("employees", face_ids)
    if not identified or len(identified) == 0:
        return {"success": False, "message": "Face not recognized."}
    return identified

    candidates = identified[0].get("candidates", [])
    if not candidates:
        return {"success": False, "message": "No matching employee found."}

    person_id = candidates[0]["personId"]
    confidence = candidates[0].get("confidence", 0)

    # Optionally, get employee details from your Employee Face doctype
    employee_face = frappe.get_all(
        "Employee Face",
        filters={"person_id": person_id},
        fields=["employee_id", "employee_name", "azure_face_id"]
    )
    if not employee_face:
        return {"success": False, "message": "Employee record not found."}

    return {
        "success": True,
        "employee_id": employee_face[0]["employee_id"],
        "employee_name": employee_face[0].get("employee_name"),
        "confidence": confidence
    }
