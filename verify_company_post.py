import json
import uuid
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000/api"

def make_request(method, url, data=None, headers=None):
    if headers is None:
        headers = {}
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            response_body = response.read().decode('utf-8')
            return status, json.loads(response_body) if response_body else None
    except urllib.error.HTTPError as e:
        response_body = e.read().decode('utf-8')
        return e.code, json.loads(response_body) if response_body else {"error": str(e)}

def print_result(step, status, data):
    print(f"--- {step} ---")
    print(f"Status: {status}")
    print(json.dumps(data, indent=2) if data else "None")
    print("\n")

# 1. Login as Admin
print("Logging in as admin...")
admin_data = {"username": "rishitha", "password": "admin123"}
status, admin_res = make_request("POST", f"{BASE_URL}/auth/login", data=admin_data)
if status != 200:
    print(f"Failed to login as admin: {status} - {admin_res}")
    exit(1)
admin_token = admin_res.get("access_token")

# Create a test company
company_username = f"test_company_{uuid.uuid4().hex[:6]}"
company_pass = "company123"
print(f"Creating test company: {company_username}")
status, create_res = make_request(
    "POST",
    f"{BASE_URL}/admin/users",
    headers={"Authorization": f"Bearer {admin_token}"},
    data={"username": company_username, "email": f"{company_username}@example.com", "password": company_pass, "role": "company"}
)
print_result("Create Company", status, create_res)

# 2. Login as the new company
print("Logging in as company...")
company_login_data = {"username": company_username, "password": company_pass}
status, company_login_res = make_request("POST", f"{BASE_URL}/auth/login", data=company_login_data)
if status != 200:
    print(f"Failed to login as company: {status} - {company_login_res}")
    exit(1)
company_token = company_login_res.get("access_token")

company_headers = {
    "Authorization": f"Bearer {company_token}",
    "Content-Type": "application/json"
}

# 3. Create a placement as company
print("Creating placement as company...")
placement_data = {
    "company_name": company_username,
    "role_title": "Software Engineer",
    "package": "15 LPA",
    "min_cgpa": 7.5,
    "eligibility_criteria": "B.Tech CSE",
    "required_skills": ["Python", "Flask", "React"],
    "deadline": "2026-12-31T00:00:00"
}
status, create_opp_res = make_request("POST", f"{BASE_URL}/company/placements", headers=company_headers, data=placement_data)
print_result("Create Placement", status, create_opp_res)
opp_id = create_opp_res.get("opportunity", {}).get("id")

# 4. List placements as company
print("Listing company placements...")
status, list_res = make_request("GET", f"{BASE_URL}/company/placements", headers=company_headers)
print_result("List Placements", status, list_res)

# 5. Edit placement as company
if opp_id:
    print(f"Editing placement {opp_id} as company...")
    edit_data = {
        "role_title": "Senior Software Engineer",
        "package": "20 LPA"
    }
    status, edit_res = make_request("PUT", f"{BASE_URL}/company/placements/{opp_id}", headers=company_headers, data=edit_data)
    print_result("Edit Placement", status, edit_res)

# 6. Delete placement as company
if opp_id:
    print(f"Deleting placement {opp_id} as company...")
    status, delete_res = make_request("DELETE", f"{BASE_URL}/company/placements/{opp_id}", headers=company_headers)
    print_result("Delete Placement", status, delete_res)

# 7. List again to ensure it's gone
print("Listing company placements again...")
status, final_list_res = make_request("GET", f"{BASE_URL}/company/placements", headers=company_headers)
print_result("List Placements Final", status, final_list_res)
