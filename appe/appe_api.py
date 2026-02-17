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
from frappe.utils import get_url


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
    
@frappe.whitelist()
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
    user_exist = frappe.db.count("User",{'email': usr,'enabled':1})
    if user_exist > 0:
        userm = frappe.db.get_all('User', filters={'email': usr,'enabled':1}, fields=['name','email','username','full_name','user_image','mobile_no','location','gender','language','time_zone','enabled','user_type'])
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
        employee_data = frappe.db.get_all('Appe Employee', filters={'user_id': user_email}, fields=['*'])
        if employee_data :
            settings = frappe.get_doc('Appe Settings')
            userm[0]['checkin_mandatory']= employee_data[0].checkin_mandatory or 0
            userm[0]['enable_live_location_tracking']= employee_data[0].enable_live_location_tracking or 0
            userm[0]['enable_faceid']= 0
            frappe.local.response["message"] = {
                "status": True,
                "type": "employee",
                "message": "Employee Login Successful",
                "data":{
                    "token" :f"token {api_key}:{api_secret}",
                    "user": employee_data[0].user_id,
                    "settings": settings,
                    "userData": userm[0],
                }
            }
            return 
        else:
            settings = frappe.get_doc('Appe Settings')
            frappe.local.response["message"] = {
                "status": True,
                "type":"User",
                "message": "User Login Successful",
                "data":{
                    "token" :f"token {api_key}:{api_secret}",
                    "user": userm[0].name,
                    "settings": settings,
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
        # frappe.log_error("location",frappe.form_dict)
        locations = frappe.form_dict.get('locations') or []

        for loc in locations:
            latitude = loc.get('latitude')
            longitude = loc.get('longitude')
            device_info = loc.get('device_info') or {}
            timestamp = loc.get('timestamp')

            # latitude = frappe.form_dict.get('latitude')
            # longitude = frappe.form_dict.get('longitude')
            # device_info = frappe.form_dict.get('device_info') or {}
            # timestamp = frappe.form_dict.get('timestamp')

            if not latitude or not longitude:
                frappe.throw(_("Latitude and Longitude are required."))

            current_timestamp = frappe.utils.format_datetime(frappe.utils.get_datetime(timestamp), 'YYYY-MM-dd HH:mm:ss')

            user = frappe.session.user

            if frappe.db.exists("Appe Employee", {"user_id": user}):
                employee = frappe.get_doc("Appe Employee", {"user_id": user})
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
            "Appe Employee",
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
            filters=[["Workflow Action","user","=",user],["Workflow Action","status","=","Open"]],
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
        app_modules = frappe.db.get_all('Mobile App Module', fields=['*'], order_by="sequence_id asc")
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
        app_sections = frappe.db.get_all('Mobile App Dashboard', filters={'status':'Active'}, fields=['*'], order_by="sequence_id asc")
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
def leave_balance():
    try:
        employee = frappe.get_doc("Appe Employee", {"user_id": frappe.session.user})
        if employee:
            frappe.response.message = {
                'status': True,
                'message': 'Successfully find employee',
                'data': [
                    {
                        "type": "Annual Leave",
                        "total": 20,
                        "used": 8,
                        "remaining": 12,
                        "color": "0xFF3B82F6",  # Blue
                    },
                    {
                        "type": "Sick Leave",
                        "total": 10,
                        "used": 3,
                        "remaining": 7,
                        "color": "0xFFEF4444",  # Red
                    },
                    {
                        "type": "Casual Leave",
                        "total": 12,
                        "used": 5,
                        "remaining": 7,
                        "color": "0xFF10B981",  # Green
                    },
                    {
                        "type": "Work From Home",
                        "total": 15,
                        "used": 6,
                        "remaining": 9,
                        "color": "0xFFF59E0B",  # Orange
                    },
                ]
            }
            return
        else:
            frappe.response.message = {
                'status': False,
                'message': 'No employee found'
            }
            return
    except Exception as e:
        frappe.log_error("leave_balance error", f"{e}")
        frappe.response.message = {
            'status': False,
            'message': f'{e}'
        }
        return

@frappe.whitelist()
def employee_details():
    try:
        # frappe.log_error('employee_checkin_status',frappe.form_dict)
        employee = frappe.get_doc("Appe Employee",{"user_id":frappe.session.user})
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
def user_details():
    try:
        user = frappe.db.get_all('User', filters={'email': frappe.session.user}, fields=['name','email','username','full_name','user_image','mobile_no','location','gender','language','time_zone','enabled','user_type'])
        
        if user:
            employee_data = frappe.db.get_all('Appe Employee', filters={'user_id': frappe.session.user}, fields=['*'])
            if employee_data :
                settings = frappe.get_doc('Appe Settings')
                user[0]['checkin_mandatory']= employee_data[0].checkin_mandatory or 0
                user[0]['enable_live_location_tracking']= employee_data[0].enable_live_location_tracking or 0
                user[0]['enable_faceid']= 0
            frappe.response.message={
                'status':True,
                'message':'Successfully find user_details',
                'data':user[0]
            }
            return
        else:
            frappe.response.message={
                'status':False,
                'message':'No user details'
            }
            return
    except Exception as e:
        frappe.log_error("user_details error",f"{e}")
        frappe.response.message={
            'status':False,
            'message':f'{e}'
        }
        return



@frappe.whitelist()
def employee_checkin_status():  
    try:
        frappe.log_error('employee_checkin_status',frappe.form_dict)
        employee = frappe.get_doc("Appe Employee",{"user_id":frappe.session.user})
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
        employee = frappe.get_doc("Appe Employee",{"user_id":frappe.session.user})
        newdoc= frappe.get_doc({'doctype':'Appy Check-in',
            'employee':employee.get('name'),
            'user':frappe.session.user,
            'event_date':frappe.utils.now_datetime(),
            'device_ip':'',
            'log_type':frappe.form_dict.log_type,
            'latlong':frappe.form_dict.latlong,
            "latitude": frappe.form_dict.latitude or "",
            "longitude": frappe.form_dict.longitude or "",
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


@frappe.whitelist()
def create_appe_post(title: str, content: str):
    doc = frappe.get_doc({"doctype": "Appe Post", "title": title, "content": content})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": True, "name": doc.name}


@frappe.whitelist()
def get_appe_posts(limit_start: int = 0, limit_page_length: int = 10):
    try:
        posts = frappe.get_all(
        "Appe Post",
        fields=["name", "title", "content", "owner", "modified_by", "creation","_liked_by"],
        order_by="creation desc",
        limit_start=int(limit_start),
        limit_page_length=int(limit_page_length),
        )

        if not posts:
            return {"status": True, "data": []}
        post_names = [p["name"] for p in posts]

        files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Appe Post",
                "attached_to_name": ["in", post_names],
            },
            fields=["file_name", "file_url", "attached_to_name"],
            limit_page_length=10000,
        )

        base = get_url()
        files_by_post = {}
        for f in files:
            post = f["attached_to_name"]
            files_by_post.setdefault(post, [])
            url = f.get("file_url") or ""
            if url and not url.lower().startswith("http"):
                if not url.startswith("/"):
                    url = f"/{url}"
                url = f"{base}{url}"
            files_by_post[post].append({
                "file_name": f["file_name"],
                "file_url": url
            })

        for p in posts:
            attachments = files_by_post.get(p["name"], [])
            image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")
            p["images"] = [a["file_url"] for a in attachments
                        if a["file_name"].lower().endswith(image_exts)]
            p["files"] = attachments

        return {"status": True, "data": posts}
    except Exception as e:
        return {"status": False, "message": str(e)}

