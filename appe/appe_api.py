from datetime import datetime
import json
import random
import frappe
import base64
import os
from frappe.utils import get_files_path, get_site_name, now
import requests
from frappe.utils.password import check_password, get_password_reset_limit
import gzip

@frappe.whitelist()
def create_appe_report_print():
    try:
        frappe.log_error('create report',frappe.form_dict)

    except Exception as e:
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }

@frappe.whitelist()
def update_appe_reports(doc,event):
    # frappe.log_error("status update_appe_reports doc",doc)
    try:
        
        if frappe.db.exists("Appe Prepared Report", {"prepared_report": doc.name}):
            reports = frappe.get_list(
                "Appe Prepared Report",
                filters={"prepared_report": doc.name},
                fields=["name"]
            )

            if reports:
                report = frappe.get_doc("Appe Prepared Report", reports[0]["name"])
                report.status = doc.status
                report.save()

                files = frappe.get_all(
                    "File",
                    filters={
                        "attached_to_doctype": "Prepared Report",
                        "attached_to_name": doc.name
                    },
                    fields=["file_url", "file_name"]
                )
                if files:
                    # Get the full path on the server
                    file_path = os.path.join(frappe.get_site_path("private", "files"), os.path.basename(files[0].file_url))

                    # Read and decompress .gz file
                    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                        file_content = f.read()

                    # Example: store this content in a field `json_data` in some Doctype (replace accordingly)
                    report.results = file_content
                    report.status = doc.status
                    report.finished_at = doc.report_end_time
                    report.error = doc.error_message or ""
                    report.save()
                    frappe.db.commit()
                    frappe.log_error("file_content update_appe_reports doc",file_content)
                else:
                    report.status = doc.status
                    report.error = doc.error_message or ""
                    report.finished_at = doc.report_end_time
                    report.save()
                    frappe.db.commit()
                    frappe.log_error("file_content not found doc",report.status)
            else:
                frappe.log_error("No Appe Prepared Report found for the given prepared_report", doc.name)
        else:
            frappe.log_error("No Appe Prepared Report", doc.name)

    except Exception as e:
        frappe.log_error("update_appe_reports error", str(e))
    
@frappe.whitelist(allow_guest=True)
def receive_message():
    try:
        message = frappe.form_dict
        frappe.publish_realtime(event='new_chat_message', user= message.get('receiverId'), message={'user': message.get('receiverId'), 'message': message})
        frappe.response.message={
            'status':True,
            'messgae':'inserted'
        }

    except Exception as e:
        frappe.response.message={
            'status':False,
            'messgae':f"{e}"
        }

    
@frappe.whitelist()
def upload_file_in_doctype(datas, filename, docname, doctype):
   for data in datas:
        try:
            filename_ext = f'/home/frappe/frappe-bench/sites/ss.erpdesks.com/private/files/{filename}.png'
            base64data = data.replace('data:image/jpeg;base64,', '')
            imgdata = base64.b64decode(base64data)
            with open(filename_ext, 'wb') as file:
                file.write(imgdata)

            doc = frappe.get_doc(
                {
                    "file_name": f'{filename}.png',
                    "is_private": 1,
                    "file_url": f'/private/files/{filename}.png',
                    "attached_to_doctype": doctype if doctype else "Geo Mitra Ledger Report",
                    "attached_to_name": docname,
                    "doctype": "File",
                }
            )
            doc.flags.ignore_permissions = True
            doc.insert()
            frappe.db.commit()
            return doc.file_url

        except Exception as e:
            frappe.log_error('ng_write_file', str(e))
            return e


@frappe.whitelist()
def get_doctype_images(doctype, docname, is_private):
    attachments = frappe.db.get_all("File",
        fields=["attached_to_name", "file_name", "file_url", "is_private"],
        filters={"attached_to_name": docname, "attached_to_doctype": doctype}
    )
    resp = []
    for attachment in attachments:
        # file_path = site_path + attachment["file_url"]
        x = get_files_path(attachment['file_name'], is_private=is_private)
        with open(x, "rb") as f:
            # encoded_string = base64.b64encode(image_file.read())
            img_content = f.read()
            img_base64 = base64.b64encode(img_content).decode()
            img_base64 = 'data:image/jpeg;base64,' + img_base64
        resp.append({"image": img_base64})

    return resp

@frappe.whitelist()
def generate_keys(user):
    user_details = frappe.get_doc("User", user)
    api_secret = frappe.generate_hash(length=15)
    
    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
    
    user_details.api_secret = api_secret

    user_details.flags.ignore_permissions = True
    user_details.save(ignore_permissions = True)
    frappe.db.commit()
    
    return user_details.api_key, api_secret


@frappe.whitelist(allow_guest=True)
def login_user(usr, pwd):

    if not usr or not pwd:
        frappe.local.response["message"] = {
            "status": False,
            "message": "invalid inputs"
        }
        return
    user_email = ""
    user_exist = frappe.db.count("User",{'email': usr})
    if user_exist > 0:
        userm = frappe.db.get_all('User', filters={'email': usr}, fields=['*'])
        user_email = userm[0].name
        try:
            check_password(user_email, pwd)
        except Exception as e:
            frappe.local.response["message"] = {
                "status": False,
                "message": "User Password  Is Not Correct",
            }
            return



        api_key, api_secret = generate_keys(user_email)
        # frappe.local.login_manager.user = user_email
        # frappe.local.login_manager.post_login()
        employee_data = frappe.db.get_all('Employee', filters={'user_id': user_email}, fields=['*'])
        if employee_data :
            settings = frappe.get_doc('Appe Settings')

            frappe.log_error("appe_api.py login_user employee_data", {
                "status": True,
                "message": "User Already Exists",
                "data":{
                "token" :f"token {api_key}:{api_secret}",
                "user": employee_data[0].user_id,
                "settings": settings.as_dict()
                }
            })

            frappe.local.response["message"] = {
                "status": True,
                "message": "Employee Login Successful",
                "data":{
                    "token" :f"token {api_key}:{api_secret}",
                    "user": employee_data[0].user_id,
                    "settings": settings,
                    "userData": userm[0]
                }
            }
            return 
        else:
            frappe.local.response["message"] = {
                "status": True,
                "message": "User Login Successful",
                "data":{
                    "token" :f"token {api_key}:{api_secret}",
                    "user": userm[0].name,
                    "userData": userm[0],
                }

            }
            return    

    frappe.local.response["message"] = {
        "status": False,
        "message": "User Not Exists",
    }

@frappe.whitelist(allow_guest=True)
def sendOTP():
    frappe.local.response["message"] = {
        "status": True,
        "message": "OTP sent successfully",  
    }
    return

@frappe.whitelist(allow_guest=True)
def verifyOTP(usr, pwd):

    if not usr or not pwd:
        frappe.local.response["message"] = {
            "status": False,
            "message": "invalid inputs"
        }
        return
    user_email = ""
    user_exist = frappe.db.count("User",{'email': usr})
    if user_exist > 0:
        userm = frappe.db.get_all('User', filters={'email': usr}, fields=['*'])
        user_email = userm[0].name
        try:
            check_password(user_email, pwd)
        except Exception as e:
            frappe.local.response["message"] = {
                "status": False,
                "message": "User Password  Is Not Correct",
            }
            return



        api_key, api_secret = generate_keys(user_email)
        # frappe.local.login_manager.user = user_email
        # frappe.local.login_manager.post_login()
        employee_data = frappe.db.get_all('Employee', filters={'user_id': user_email}, fields=['*'])
        if employee_data :
            settings = frappe.get_doc('Appe Settings')

            frappe.log_error("appe_api.py login_user employee_data", {
                "status": True,
                "message": "User Already Exists",
                "data":{
                "token" :f"token {api_key}:{api_secret}",
                "user": employee_data[0].user_id,
                "settings": settings
                }
            })

            frappe.local.response["message"] = {
                "status": True,
                "message": "User Already Exists",
                "data":{
                "token" :f"token {api_key}:{api_secret}",
                "user": employee_data[0].user_id,
                "settings": settings
                }
            }
            return        

    frappe.local.response["message"] = {
        "status": False,
        "message": "User Not Exists",
    }





@frappe.whitelist()
def storelocation():
    try:
        latitude = frappe.form_dict.get('latitude')
        longitude = frappe.form_dict.get('longitude')
        device_info = frappe.form_dict.get('device_info') or {}
        timestamp = frappe.form_dict.get('timestamp')

        if not latitude or not longitude:
            frappe.throw(_("Latitude and Longitude are required."))

        current_timestamp = frappe.utils.format_datetime(frappe.utils.get_datetime(timestamp), 'YYYY-MM-dd HH:mm:ss')

        user = frappe.session.user

        if frappe.db.exists("Employee", {"user_id": user}):
            employee = frappe.get_doc("Employee", {"user_id": user})
            two_days_ago = frappe.utils.add_days(frappe.utils.now_datetime(), -2)

            recent_timestamps = frappe.db.get_all(
                "Employee Location",
                filters={"employee": employee.name, "timestamp": [">=", two_days_ago]},
                fields=["timestamp"],
                order_by="timestamp DESC"
            )

            for record in recent_timestamps:
                if record["timestamp"]:
                    last_timestamp = frappe.utils.get_datetime(record["timestamp"])
                    if frappe.utils.time_diff_in_seconds(current_timestamp, last_timestamp) < 120:
                        frappe.response.message = {
                            'status': False,
                            'message': 'Location update too frequent. Please wait at least 2 minutes.'
                        }
                        return
                        # frappe.throw('Location update too frequent. Please wait at least 2 minutes.')

            # Insert new location
            location_doc = frappe.get_doc({
                "doctype": "Employee Location",
                "latitude": latitude,
                "longitude": longitude,
                "employee": employee.name,
                "battery_level": device_info.get('battery_level'),
                "gps": device_info.get('gps_status'),
                "wifi_status": device_info.get('wifi_status'),
                "airplane_mode": device_info.get('airplane_mode_status'),
                "mobile_ip_address": device_info.get('mobile_ip_address'),
                "sdk_version": device_info.get('sdk_version'),
                "brand": device_info.get('brand'),
                "model": device_info.get('model'),
                "mobile_data_status": device_info.get('mobile_data_status'),
                "user": user,
                "timestamp": current_timestamp
            })
            location_doc.insert()
            frappe.db.commit()

            frappe.response.message = {
                'status': True,
                'message': 'Location stored successfully.'
            }
            return

    except Exception as e:
        frappe.log_error("Location Error", e)
        frappe.response.message = {
            'status': False,
            'message': f'Error: {str(e)}'
        }
        return


@frappe.whitelist()
def gettasks_and_request_and_attendancedata():
    try:
        user = frappe.session.user
        emp = frappe.get_list(
            "Employee",
            filters={"user_id": user},
            fields=["*"]
        )

        if len(emp):
            frappe.response.message = {
                "status": False,
                "message": "No employee record found for the current user.",
                "data": {}
            }
            return
        
        emp_data = emp[0] 
        emp_id = emp_data["name"]

        last_30_days = frappe.utils.add_days(frappe.utils.today(), -30)

        pending_tasks = frappe.db.sql(f"""
            SELECT 
                todo.name AS todo_id,
                todo.allocated_to AS assigned_to,
                todo.status AS todo_status,
                todo.priority AS priority,
                task.name AS name,
                u.full_name AS created_by,
                task.subject AS description,
                task.status AS status,
                task.modified AS modified,
                task.exp_end_date AS task_due_date,
                task.project AS title
            FROM 
                `tabToDo` todo
            JOIN 
                `tabTask` task ON todo.reference_name = task.name
            JOIN `tabUser` u ON u.name=task.owner
            WHERE 
                todo.allocated_to = %s 
                # AND todo.date = CURDATE()
                AND todo.reference_type = 'Task'
            ORDER BY 
                todo.priority DESC, task.exp_end_date ASC;
        """, (user), as_dict=True)


        roles = frappe.get_all("Has Role", filters={"parent": user}, fields=["role"], as_list=True)
        roles = [r[0] for r in roles]
        
        pending_approvals = frappe.get_all(
            "Workflow Action",
            fields=["*"],
            filters={"status": "Open", "user":user},
            or_filters=[["Workflow Action Permitted Role","role", "in", roles]],
            distinct=True
        )

        # Fetch attendance data for the last 30 days
        attendance_data = frappe.get_list(
            "Attendance",
            filters={
                "employee": emp_id,
                "attendance_date": [">=", last_30_days]
            },
            fields=["*"],
            order_by="attendance_date desc"
        )

        # # Fetch leave balance (if applicable)
        # leave_balance = frappe.get_list(
        #     "Leave Balance",
        #     filters={"employee": emp_id},
        #     fields=["*"]
        # )

        # Send response
        frappe.response.message = {
            "status": True,
            "message": "Employee data fetched successfully",
            "data": {
                # "employee": emp,
                "tasks": pending_tasks,
                "approvals": pending_approvals,
                # "attendance_data": attendance_data,
                # "leave_balance": leave_balance,
            }
        }
        return

    except Exception as e:
        frappe.response.message = {
            "status": False,
            "error": str(e)
        }
        return


@frappe.whitelist()
def get_module_data():
    try:
        app_modules = frappe.db.get_all('Mobile App Module', fields=['*'])
        results = []
        for module in app_modules:
            module_items = frappe.get_all('Mobile App Module Items', filters={'parent': module.name}, fields=['*'])
            results.append({'module_name': module.get('module_name'),'image': module.get('image'),'items': module_items})
        frappe.response.message={'status':True,'message':'','data':results}
        return
    except Exception as e:
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }
        return

@frappe.whitelist()
def get_dashboard_sections():
    try:
        app_sections = frappe.db.get_all('Mobile App Dashboard', filters={'status':'Active'}, fields=['*'])
        results = []
        for section in app_sections:
            section_items = frappe.get_all('Mobile App Dashboard Items', filters={'parent': section.name}, fields=['*'])
            results.append({'section_view': section.get('section_view'),'section_name': section.get('section_name'),'image': section.get('image'),'items': section_items})
        frappe.response.message={'status':True,'message':'','data':results}
        return
    except Exception as e:
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }
        return


@frappe.whitelist()
def share_remove():
    try:
        share_name = frappe.db.get_value("DocShare", {"user": frappe.form_dict.user, "share_name": frappe.form_dict.name, "share_doctype": frappe.form_dict.doctype})
        if share_name:
            frappe.delete_doc("DocShare", share_name, flags=None)
            frappe.response.message={
                'status':True,
                'message':f"User successfully removed"
            }
            return
        else:
            frappe.response.message={
                'status':False,
                'message':"document not found"
            }
            return
    except Exception as e:
        frappe.response.message={
            'status':False,
            'message':f"{e}"
        }
        return


@frappe.whitelist()
def remove_assignment():
    try:
        name = frappe.form_dict.name
        if name :
            doc =frappe.get_doc('ToDo',name)
            doc.status = "Cancelled"
            doc.save()
        frappe.response.message={
            'status':True,
            'message':'User assigment is cancelled'
        }
        return
    except Exception as e:
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }
        return


@frappe.whitelist()
def employee_details():
    try:
        # frappe.log_error('employee_checkin_status',frappe.form_dict)
        employee = frappe.get_doc("Employee",{"user_id":frappe.session.user})
        if employee:
            frappe.response.message={
                'status':True,
                'message':'Successfully find employee_details',
                'data':employee
            }
            return
        else:
            frappe.response.message={
                'status':False,
                'message':'No employee_details'
            }
            return
    except Exception as e:
        frappe.log_error("employee_details error",f"{e}")
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }
        return



@frappe.whitelist()
def employee_checkin_status():  
    try:
        frappe.log_error('employee_checkin_status',frappe.form_dict)
        employee = frappe.get_doc("Employee",{"user_id":frappe.session.user})
        data = frappe.get_list("Appy Check-in", filters=[["Appy Check-in","event_date","Timespan","today"],["employee","=",employee.get("name")]], fields=["*"])
        if data:
            frappe.response.message={
                'status':True,
                'message':'Successfully find checkin today',
                'data':data[0]
            }
            return
        else:
            frappe.response.message={
                'status':False,
                'message':'No checkin today'
            }
            return
    except Exception as e:
        frappe.log_error("employee checkin status error",f"{e}")
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }
        return


@frappe.whitelist()
def employee_checkin():
    try:
        # frappe.log_error('employee_checkin',frappe.form_dict)
        employee = frappe.get_doc("Employee",{"user_id":frappe.session.user})
        newdoc= frappe.get_doc({'doctype':'Appy Check-in',
            'employee':employee.get('name'),
            'user':frappe.session.user,
            'event_date':frappe.utils.now_datetime(),
            'device_ip':'',
            'log_type':frappe.form_dict.log_type,
            'latlong':frappe.form_dict.latlong
        }).insert()
        frappe.db.commit()
        frappe.response.message={
            'status':True,
            'message':'Successfully inserted',
            'data':newdoc
        }
        return
    except Exception as e:
        # frappe.log_error("employee checkin error",f"{e}")
        frappe.response.message={
            'status':True,
            'message':f'{e}'
        }
        return


