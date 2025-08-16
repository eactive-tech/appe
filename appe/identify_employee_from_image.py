# import base64
# import frappe
# import numpy as np
# import face_recognition
# import requests
# from io import BytesIO
# from PIL import Image

# def load_face_encodings():
#     encodings = []
#     records = frappe.get_all("Employee Face", fields=["employee_id", "face_encoding"])
#     for rec in records:
#         if not rec.face_encoding:
#             continue
#         try:
#             encoding_list = [float(x) for x in rec.face_encoding.split(",")]
#             encodings.append({
#                 "employee_id": rec.employee_id,
#                 "encoding": np.array(encoding_list)
#             })
#         except:
#             frappe.logger().error(f"Invalid encoding for {rec.employee_id}")
#     return encodings

# @frappe.whitelist()
# def identify_employee(image_url, tolerance=0.6):
#     """
#     Identify employee from an image URL (e.g. /files/abc.jpg or full URL).
#     """

#     # image_url = upload_file_in_doctype(image_base64)
#     if not image_url:
#         return {"status":False,"message":"❌ Could not upload image."}
#     known_faces = load_face_encodings()
#     if not known_faces:
#         return {"status":False,"message":"❌ No enrolled faces found."}

#     # Make sure the image_url is a full URL
#     if image_url.startswith("/"):
#         image_url = frappe.utils.get_url() + image_url

#     # Download image from the URL
#     response = requests.get(image_url)
#     if response.status_code != 200:
#         return {"status":False,
#                 "message":" Could not download image from the provided URL."}

#     # Load image directly from memory
#     unknown_image = face_recognition.load_image_file(BytesIO(response.content))
#     unknown_encodings = face_recognition.face_encodings(unknown_image)

#     if not unknown_encodings:
#         return {"status":False,
#                 "message":"No face found in the input image."}

#     unknown_encoding = unknown_encodings[0]

#     for known in known_faces:
#         match = face_recognition.compare_faces(
#             [known["encoding"]],
#             unknown_encoding,
#             tolerance=float(tolerance)
#         )[0]
#         if match:
#             return {"status":True,
#                     "message": f"✅ Identified as employee {known['employee_id']}",
#                     "employee":known['employee_id']}

#     return {"status":False,
#             "message": "❌ No matching employee found.",
#             "employee": None}



import base64
import frappe
import numpy as np
import face_recognition
import requests
from io import BytesIO
import pickle

def load_face_encodings():
    encodings = []
    records = frappe.get_all("Employee Face", fields=["employee_id", "face_encoding"])
    for rec in records:
        if not rec.face_encoding:
            continue
        try:
            # Load pickle-encoded base64 string
            encoding_data = base64.b64decode(rec.face_encoding)
            encoding_array = pickle.loads(encoding_data)
            encodings.append({
                "employee_id": rec.employee_id,
                "encoding": np.array(encoding_array)
            })
        except Exception as e:
            frappe.logger().error(f"[Face Encoding Error] Employee {rec.employee_id}: {e}")
    return encodings

@frappe.whitelist()
def identify_employee(image_url, tolerance=0.65):
    """
    Identify employee from an image URL.
    """
    # image_url = upload_file_in_doctype(image_base64)

    if not image_url:
        return {"status": False, "message": "No image URL provided."}

    known_faces = load_face_encodings()
    if not known_faces:
        return {"status": False, "message": "No enrolled faces found."}

    if image_url.startswith("/"):
        image_url = frappe.utils.get_url() + image_url

    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            return {"status": False, "message": "Could not download image from the provided URL."}
        
        unknown_image = face_recognition.load_image_file(BytesIO(response.content))
        unknown_encodings = face_recognition.face_encodings(unknown_image)

        if len(unknown_encodings) != 1:
            return {
                "status": False,
                "message": f"Expected 1 face, but found {len(unknown_encodings)}. Please use a clear image with one face."
            }

        unknown_encoding = unknown_encodings[0]

        for known in known_faces:
            distance = face_recognition.face_distance([known["encoding"]], unknown_encoding)[0]
            match = distance <= float(tolerance)
            frappe.logger().info(f"[Face Match Attempt] {known['employee_id']} distance: {distance}, match: {match}")
            
            if match:
                return {
                    "status": True,
                    "message": f"Identified as employee {known['employee_id']} (distance: {round(distance, 4)})",
                    "employee": known["employee_id"],
                    "user": known["employee_id"]
                }

        return {"status": False, "message": "No matching employee found.", "employee": None}

    except Exception as e:
        frappe.log_error(f"Face recognition error: {e}")
        return {"status": False, "message": f"Internal error: {str(e)}"}

@frappe.whitelist()
def upload_file_in_doctype(data):
    try:
        filename = frappe.generate_hash(length=10)
        # Detect file extension from base64 header
        if data.startswith('data:image/png'):
            ext = 'png'
            base64data = data.replace('data:image/png;base64,', '')
        else:
            ext = 'jpg'
            base64data = data.replace('data:image/jpeg;base64,', '')

        # Use Frappe's public files path
        from frappe.utils.file_manager import get_files_path
        filepath = f"{get_files_path(is_private=False)}/{filename}.{ext}"

        imgdata = base64.b64decode(base64data)
        with open(filepath, 'wb') as file:
            file.write(imgdata)

        doc = frappe.get_doc({
            "file_name": f'{filename}.{ext}',
            "is_private": 0,
            "file_url": f'/files/{filename}.{ext}',
            "doctype": "File",
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        return doc.file_url

    except Exception as e:
        frappe.log_error('ng_write_file', str(e))
        return str(e)



# @frappe.whitelist(allow_guest=True)
# def identify_employee(image_base64, tolerance=0.6):

#     """
#     Identify employee from base64-encoded image (sent from Flutter).
#     """
#     try:
#         # Decode base64 to image
#         image_data = base64.b64decode(image_base64)
#         image = Image.open(BytesIO(image_data))
#         image_np = np.array(image)

#         # Get face encodings
#         unknown_encodings = face_recognition.face_encodings(image_np)
#         if not unknown_encodings:
#             return "❌ No face found in the image."

#         unknown_encoding = unknown_encodings[0]

#         # Load known face encodings
#         known_faces = []
#         records = frappe.get_all("Employee Face", fields=["employee_id", "face_encoding"])
#         for rec in records:
#             if not rec.face_encoding:
#                 continue
#             try:
#                 encoding_array = [float(x) for x in rec.face_encoding.split(",")]
#                 known_faces.append({
#                     "employee_id": rec.employee_id,
#                     "encoding": np.array(encoding_array)
#                 })
#             except:
#                 frappe.logger().error(f"Invalid encoding for {rec.employee_id}")

#         if not known_faces:
#             return "❌ No enrolled faces found."

#         # Match
#         for known in known_faces:
#             match = face_recognition.compare_faces(
#                 [known["encoding"]],
#                 unknown_encoding,
#                 tolerance=float(tolerance)
#             )[0]
#             if match:
#                 return known["employee_id"]

#         return "❌ No match found."

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Face Recognition Error")
#         return f"❌ Error: {str(e)}"

