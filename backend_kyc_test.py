"""
Comprehensive KYC System Backend Test Suite
Tests all 14 scenarios specified in the review request.
"""
import io
import requests
from PIL import Image

# Backend base URL
BASE_URL = "https://easyx-loader.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test counters
tests_passed = 0
tests_failed = 0
test_results = []

def log_test(scenario, test_name, passed, details=""):
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        status = "✅ PASS"
    else:
        tests_failed += 1
        status = "❌ FAIL"
    result = f"{status} - Scenario {scenario}: {test_name}"
    if details:
        result += f" | {details}"
    test_results.append(result)
    print(result)

def create_test_image(size_kb=10):
    """Create a small valid PNG image for testing."""
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()

def register_user(name, email, phone, password):
    """Register a new user and return access token."""
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": name,
        "email": email,
        "phone": phone,
        "password": password
    })
    if resp.status_code == 201:
        return resp.json()["access_token"]
    return None

def login_admin():
    """Login as admin and return access token."""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return None

print("=" * 80)
print("KYC SYSTEM BACKEND TEST SUITE")
print("=" * 80)

# Get admin token
admin_token = login_admin()
if not admin_token:
    print("❌ FAILED TO LOGIN AS ADMIN")
    exit(1)
print(f"✅ Admin logged in successfully\n")

# ============================================================================
# SCENARIO 1: New user GET /api/kyc -> status='none', can_submit=true
# ============================================================================
print("\n--- SCENARIO 1: New user KYC status ---")
user_a_email = f"kyc_user_a_{requests.get('https://httpbin.org/uuid').json()['uuid'][:8]}@easyx.com"
user_a_token = register_user("KYC User A", user_a_email, f"+91{9000000000 + tests_passed}", "Password123!")

if user_a_token:
    resp = requests.get(f"{BASE_URL}/kyc", headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        log_test(1, "GET /api/kyc returns 200", True)
        log_test(1, "status='none'", data.get("status") == "none", f"Got: {data.get('status')}")
        log_test(1, "can_submit=true", data.get("can_submit") == True, f"Got: {data.get('can_submit')}")
        log_test(1, "documents=[]", data.get("documents") == [], f"Got: {len(data.get('documents', []))} docs")
    else:
        log_test(1, "GET /api/kyc", False, f"Status: {resp.status_code}")
else:
    log_test(1, "Register user A", False, "Registration failed")

# ============================================================================
# SCENARIO 2: Submit valid PNG id_document + selfie -> status='pending', 2 docs
# ============================================================================
print("\n--- SCENARIO 2: Submit valid KYC documents ---")
if user_a_token:
    id_image = create_test_image(10)
    selfie_image = create_test_image(8)
    
    files = {
        'id_document': ('id_aadhaar.png', id_image, 'image/png'),
        'selfie': ('selfie.png', selfie_image, 'image/png')
    }
    data = {
        'id_type': 'aadhaar',
        'id_number': '1234-5678-9012'
    }
    
    resp = requests.post(
        f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {user_a_token}"},
        files=files,
        data=data
    )
    
    if resp.status_code == 200:
        result = resp.json()
        log_test(2, "POST /api/kyc/submit returns 200", True)
        log_test(2, "status='pending'", result.get("status") == "pending", f"Got: {result.get('status')}")
        log_test(2, "documents length == 2", len(result.get("documents", [])) == 2, f"Got: {len(result.get('documents', []))} docs")
        log_test(2, "id_number_present=true", result.get("id_number_present") == True, f"Got: {result.get('id_number_present')}")
        
        # Store document IDs for later tests
        doc_ids = [d["id"] for d in result.get("documents", [])]
        if len(doc_ids) >= 1:
            user_a_doc_id = doc_ids[0]
        else:
            user_a_doc_id = None
    else:
        log_test(2, "POST /api/kyc/submit", False, f"Status: {resp.status_code}, Body: {resp.text}")
        user_a_doc_id = None

# ============================================================================
# SCENARIO 3: Owner GET /api/kyc/documents/{doc_id} -> 200 with image
# ============================================================================
print("\n--- SCENARIO 3: Owner can access their document ---")
if user_a_token and user_a_doc_id:
    resp = requests.get(
        f"{BASE_URL}/kyc/documents/{user_a_doc_id}",
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    
    if resp.status_code == 200:
        log_test(3, "GET /api/kyc/documents/{doc_id} returns 200", True)
        content_type = resp.headers.get('Content-Type', '')
        log_test(3, "Content-Type is image", 'image' in content_type, f"Got: {content_type}")
        log_test(3, "Body is non-empty", len(resp.content) > 0, f"Got: {len(resp.content)} bytes")
    else:
        log_test(3, "GET /api/kyc/documents/{doc_id}", False, f"Status: {resp.status_code}")
else:
    log_test(3, "Owner document access", False, "Missing token or doc_id")

# ============================================================================
# SCENARIO 4: SECURITY - Different user cannot access another user's document
# ============================================================================
print("\n--- SCENARIO 4: SECURITY - Cross-user document access blocked ---")
user_b_email = f"kyc_user_b_{requests.get('https://httpbin.org/uuid').json()['uuid'][:8]}@easyx.com"
user_b_token = register_user("KYC User B", user_b_email, f"+91{9000000000 + tests_passed + 100}", "Password123!")

if user_b_token and user_a_doc_id:
    resp = requests.get(
        f"{BASE_URL}/kyc/documents/{user_a_doc_id}",
        headers={"Authorization": f"Bearer {user_b_token}"}
    )
    
    log_test(4, "Different user GET document returns 403", resp.status_code == 403, f"Got: {resp.status_code}")
else:
    log_test(4, "Cross-user access test", False, "Missing user B token or doc_id")

# ============================================================================
# SCENARIO 5: SECURITY - Unauthenticated request -> 401
# ============================================================================
print("\n--- SCENARIO 5: SECURITY - Unauthenticated access blocked ---")
if user_a_doc_id:
    resp = requests.get(f"{BASE_URL}/kyc/documents/{user_a_doc_id}")
    log_test(5, "No token GET document returns 401", resp.status_code == 401, f"Got: {resp.status_code}")
else:
    log_test(5, "Unauthenticated access test", False, "Missing doc_id")

# ============================================================================
# SCENARIO 6: Admin GET /api/admin/kyc?status=pending -> includes record, NO plaintext ID
# ============================================================================
print("\n--- SCENARIO 6: Admin list KYC records - NO plaintext ID number ---")
resp = requests.get(
    f"{BASE_URL}/admin/kyc?status=pending",
    headers={"Authorization": f"Bearer {admin_token}"}
)

if resp.status_code == 200:
    records = resp.json()
    log_test(6, "GET /api/admin/kyc?status=pending returns 200", True)
    
    # Find user A's record
    user_a_record = None
    for rec in records:
        if rec.get("user_email") == user_a_email:
            user_a_record = rec
            break
    
    if user_a_record:
        log_test(6, "Record includes user_email", user_a_record.get("user_email") == user_a_email, f"Got: {user_a_record.get('user_email')}")
        log_test(6, "id_number_present=true", user_a_record.get("id_number_present") == True, f"Got: {user_a_record.get('id_number_present')}")
        
        # CRITICAL: Verify plaintext ID number '1234-5678-9012' does NOT appear
        response_text = resp.text
        has_plaintext_id = '1234-5678-9012' in response_text or '1234' in response_text
        log_test(6, "CRITICAL: NO plaintext ID number in admin response", not has_plaintext_id, f"Found plaintext: {has_plaintext_id}")
        
        # Also check user's own GET /api/kyc response
        user_resp = requests.get(f"{BASE_URL}/kyc", headers={"Authorization": f"Bearer {user_a_token}"})
        if user_resp.status_code == 200:
            user_response_text = user_resp.text
            has_plaintext_in_user = '1234-5678-9012' in user_response_text or '1234' in user_response_text
            log_test(6, "CRITICAL: NO plaintext ID number in user response", not has_plaintext_in_user, f"Found plaintext: {has_plaintext_in_user}")
        
        user_a_record_id = user_a_record.get("id")
    else:
        log_test(6, "Find user A's record", False, "Record not found in admin list")
        user_a_record_id = None
else:
    log_test(6, "GET /api/admin/kyc", False, f"Status: {resp.status_code}")
    user_a_record_id = None

# ============================================================================
# SCENARIO 7: Submit again while status is pending -> 409
# ============================================================================
print("\n--- SCENARIO 7: Cannot submit while pending ---")
if user_a_token:
    id_image = create_test_image(10)
    selfie_image = create_test_image(8)
    
    files = {
        'id_document': ('id_new.png', id_image, 'image/png'),
        'selfie': ('selfie_new.png', selfie_image, 'image/png')
    }
    data = {
        'id_type': 'passport',
        'id_number': '9999-9999-9999'
    }
    
    resp = requests.post(
        f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {user_a_token}"},
        files=files,
        data=data
    )
    
    log_test(7, "Submit while pending returns 409", resp.status_code == 409, f"Got: {resp.status_code}")

# ============================================================================
# SCENARIO 8: Admin approve -> status='approved', approve again -> 409
# ============================================================================
print("\n--- SCENARIO 8: Admin approve flow ---")
if user_a_record_id:
    # First approval
    resp = requests.post(
        f"{BASE_URL}/admin/kyc/{user_a_record_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if resp.status_code == 200:
        result = resp.json()
        log_test(8, "POST /api/admin/kyc/{id}/approve returns 200", True)
        log_test(8, "Response status='approved'", result.get("status") == "approved", f"Got: {result.get('status')}")
        
        # Check user's status
        user_resp = requests.get(f"{BASE_URL}/kyc", headers={"Authorization": f"Bearer {user_a_token}"})
        if user_resp.status_code == 200:
            user_data = user_resp.json()
            log_test(8, "User GET /api/kyc status='approved'", user_data.get("status") == "approved", f"Got: {user_data.get('status')}")
        
        # Try to approve again
        resp2 = requests.post(
            f"{BASE_URL}/admin/kyc/{user_a_record_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        log_test(8, "Approve again returns 409", resp2.status_code == 409, f"Got: {resp2.status_code}")
    else:
        log_test(8, "Admin approve", False, f"Status: {resp.status_code}")
else:
    log_test(8, "Admin approve flow", False, "Missing record_id")

# ============================================================================
# SCENARIO 9: Reject flow - fresh user D
# ============================================================================
print("\n--- SCENARIO 9: Admin reject flow ---")
user_d_email = f"kyc_user_d_{requests.get('https://httpbin.org/uuid').json()['uuid'][:8]}@easyx.com"
user_d_token = register_user("KYC User D", user_d_email, f"+91{9000000000 + tests_passed + 200}", "Password123!")

if user_d_token:
    # Submit KYC
    id_image = create_test_image(10)
    selfie_image = create_test_image(8)
    
    files = {
        'id_document': ('id_d.png', id_image, 'image/png'),
        'selfie': ('selfie_d.png', selfie_image, 'image/png')
    }
    data = {
        'id_type': 'national_id',
        'id_number': '5555-5555-5555'
    }
    
    resp = requests.post(
        f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {user_d_token}"},
        files=files,
        data=data
    )
    
    if resp.status_code == 200:
        log_test(9, "User D submits KYC successfully", True)
        
        # Get record ID from admin list
        admin_resp = requests.get(
            f"{BASE_URL}/admin/kyc?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        user_d_record_id = None
        if admin_resp.status_code == 200:
            for rec in admin_resp.json():
                if rec.get("user_email") == user_d_email:
                    user_d_record_id = rec.get("id")
                    break
        
        if user_d_record_id:
            # Reject with reason
            reject_resp = requests.post(
                f"{BASE_URL}/admin/kyc/{user_d_record_id}/reject",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"reason": "Blurry photo"}
            )
            
            if reject_resp.status_code == 200:
                result = reject_resp.json()
                log_test(9, "Admin reject with reason returns 200", True)
                log_test(9, "Response status='rejected'", result.get("status") == "rejected", f"Got: {result.get('status')}")
                
                # Check user's status
                user_resp = requests.get(f"{BASE_URL}/kyc", headers={"Authorization": f"Bearer {user_d_token}"})
                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    log_test(9, "User status='rejected'", user_data.get("status") == "rejected", f"Got: {user_data.get('status')}")
                    log_test(9, "reject_reason='Blurry photo'", user_data.get("reject_reason") == "Blurry photo", f"Got: {user_data.get('reject_reason')}")
                    log_test(9, "can_submit=true after rejection", user_data.get("can_submit") == True, f"Got: {user_data.get('can_submit')}")
            else:
                log_test(9, "Admin reject with reason", False, f"Status: {reject_resp.status_code}")
            
            # Test reject WITHOUT reason (should fail)
            # Create another user for this test
            user_e_email = f"kyc_user_e_{requests.get('https://httpbin.org/uuid').json()['uuid'][:8]}@easyx.com"
            user_e_token = register_user("KYC User E", user_e_email, f"+91{9000000000 + tests_passed + 300}", "Password123!")
            
            if user_e_token:
                # Submit KYC
                files_e = {
                    'id_document': ('id_e.png', create_test_image(10), 'image/png'),
                    'selfie': ('selfie_e.png', create_test_image(8), 'image/png')
                }
                data_e = {'id_type': 'passport'}
                
                submit_resp = requests.post(
                    f"{BASE_URL}/kyc/submit",
                    headers={"Authorization": f"Bearer {user_e_token}"},
                    files=files_e,
                    data=data_e
                )
                
                if submit_resp.status_code == 200:
                    # Get record ID
                    admin_resp2 = requests.get(
                        f"{BASE_URL}/admin/kyc?status=pending",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
                    
                    user_e_record_id = None
                    if admin_resp2.status_code == 200:
                        for rec in admin_resp2.json():
                            if rec.get("user_email") == user_e_email:
                                user_e_record_id = rec.get("id")
                                break
                    
                    if user_e_record_id:
                        # Try to reject without reason
                        reject_no_reason = requests.post(
                            f"{BASE_URL}/admin/kyc/{user_e_record_id}/reject",
                            headers={"Authorization": f"Bearer {admin_token}"},
                            json={"reason": ""}
                        )
                        log_test(9, "Reject without reason returns 400", reject_no_reason.status_code == 400, f"Got: {reject_no_reason.status_code}")
                        
                        # Try with reason too short
                        reject_short = requests.post(
                            f"{BASE_URL}/admin/kyc/{user_e_record_id}/reject",
                            headers={"Authorization": f"Bearer {admin_token}"},
                            json={"reason": "ab"}
                        )
                        log_test(9, "Reject with short reason returns 422", reject_short.status_code == 422, f"Got: {reject_short.status_code}")
        else:
            log_test(9, "Find user D record", False, "Record not found")
    else:
        log_test(9, "User D submit KYC", False, f"Status: {resp.status_code}")
else:
    log_test(9, "Register user D", False, "Registration failed")

# ============================================================================
# SCENARIO 10: Resubmit after rejection -> pending, then approve -> approved
# ============================================================================
print("\n--- SCENARIO 10: Resubmit after rejection ---")
if user_d_token:
    # Resubmit
    id_image = create_test_image(10)
    selfie_image = create_test_image(8)
    
    files = {
        'id_document': ('id_d_new.png', id_image, 'image/png'),
        'selfie': ('selfie_d_new.png', selfie_image, 'image/png')
    }
    data = {
        'id_type': 'national_id',
        'id_number': '6666-6666-6666'
    }
    
    resp = requests.post(
        f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {user_d_token}"},
        files=files,
        data=data
    )
    
    if resp.status_code == 200:
        result = resp.json()
        log_test(10, "Resubmit after rejection returns 200", True)
        log_test(10, "Status='pending' after resubmit", result.get("status") == "pending", f"Got: {result.get('status')}")
        
        # Get new record ID
        admin_resp = requests.get(
            f"{BASE_URL}/admin/kyc?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        user_d_new_record_id = None
        if admin_resp.status_code == 200:
            for rec in admin_resp.json():
                if rec.get("user_email") == user_d_email:
                    user_d_new_record_id = rec.get("id")
                    break
        
        if user_d_new_record_id:
            # Approve
            approve_resp = requests.post(
                f"{BASE_URL}/admin/kyc/{user_d_new_record_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if approve_resp.status_code == 200:
                log_test(10, "Admin approve after resubmit returns 200", True)
                
                # Check user status
                user_resp = requests.get(f"{BASE_URL}/kyc", headers={"Authorization": f"Bearer {user_d_token}"})
                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    log_test(10, "User status='approved' after resubmit+approve", user_data.get("status") == "approved", f"Got: {user_data.get('status')}")
            else:
                log_test(10, "Admin approve after resubmit", False, f"Status: {approve_resp.status_code}")
        else:
            log_test(10, "Find user D new record", False, "Record not found")
    else:
        log_test(10, "Resubmit after rejection", False, f"Status: {resp.status_code}")

# ============================================================================
# SCENARIO 11: VALIDATION - Submit with text/plain file -> 400 invalid_file_type
# ============================================================================
print("\n--- SCENARIO 11: VALIDATION - Invalid file type ---")
user_f_email = f"kyc_user_f_{requests.get('https://httpbin.org/uuid').json()['uuid'][:8]}@easyx.com"
user_f_token = register_user("KYC User F", user_f_email, f"+91{9000000000 + tests_passed + 400}", "Password123!")

if user_f_token:
    text_content = b"This is a text file, not an image"
    
    files = {
        'id_document': ('id.txt', text_content, 'text/plain'),
        'selfie': ('selfie.png', create_test_image(8), 'image/png')
    }
    data = {'id_type': 'passport'}
    
    resp = requests.post(
        f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {user_f_token}"},
        files=files,
        data=data
    )
    
    log_test(11, "Submit text/plain file returns 400", resp.status_code == 400, f"Got: {resp.status_code}")
    if resp.status_code == 400:
        try:
            error = resp.json()
            detail = error.get("detail", {})
            if isinstance(detail, dict):
                log_test(11, "Error code='invalid_file_type'", detail.get("code") == "invalid_file_type", f"Got: {detail.get('code')}")
            else:
                log_test(11, "Error code='invalid_file_type'", False, f"Detail is not dict: {detail}")
        except Exception:
            log_test(11, "Parse error response", False, "Could not parse JSON")
else:
    log_test(11, "Register user F", False, "Registration failed")

# ============================================================================
# SCENARIO 12: VALIDATION - Submit >5MB file -> 400 file_too_large
# ============================================================================
print("\n--- SCENARIO 12: VALIDATION - File too large ---")
user_g_email = f"kyc_user_g_{requests.get('https://httpbin.org/uuid').json()['uuid'][:8]}@easyx.com"
user_g_token = register_user("KYC User G", user_g_email, f"+91{9000000000 + tests_passed + 500}", "Password123!")

if user_g_token:
    # Create a >5MB file (5MB + 1KB)
    large_content = b"X" * (5 * 1024 * 1024 + 1024)
    
    files = {
        'id_document': ('id_large.png', large_content, 'image/png'),
        'selfie': ('selfie.png', create_test_image(8), 'image/png')
    }
    data = {'id_type': 'passport'}
    
    resp = requests.post(
        f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {user_f_token}"},
        files=files,
        data=data
    )
    
    log_test(12, "Submit >5MB file returns 400", resp.status_code == 400, f"Got: {resp.status_code}")
    if resp.status_code == 400:
        try:
            error = resp.json()
            detail = error.get("detail", {})
            if isinstance(detail, dict):
                log_test(12, "Error code='file_too_large'", detail.get("code") == "file_too_large", f"Got: {detail.get('code')}")
            else:
                log_test(12, "Error code='file_too_large'", False, f"Detail is not dict: {detail}")
        except Exception:
            log_test(12, "Parse error response", False, "Could not parse JSON")
else:
    log_test(12, "Register user G", False, "Registration failed")

# ============================================================================
# SCENARIO 13: AUTH - Normal user calling admin endpoint -> 403, no token -> 401
# ============================================================================
print("\n--- SCENARIO 13: AUTH - Admin endpoint access control ---")
if user_a_token:
    # Normal user calling admin endpoint
    resp = requests.get(
        f"{BASE_URL}/admin/kyc",
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    log_test(13, "Normal user calling admin endpoint returns 403", resp.status_code == 403, f"Got: {resp.status_code}")
    
    # No token
    resp2 = requests.get(f"{BASE_URL}/admin/kyc")
    log_test(13, "No token calling admin endpoint returns 401", resp2.status_code == 401, f"Got: {resp2.status_code}")
else:
    log_test(13, "AUTH tests", False, "Missing user token")

# ============================================================================
# SCENARIO 14: Admin can fetch document via GET /api/admin/kyc/documents/{doc_id}
# ============================================================================
print("\n--- SCENARIO 14: Admin can access KYC documents ---")
if user_a_doc_id:
    resp = requests.get(
        f"{BASE_URL}/admin/kyc/documents/{user_a_doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if resp.status_code == 200:
        log_test(14, "Admin GET /api/admin/kyc/documents/{doc_id} returns 200", True)
        content_type = resp.headers.get('Content-Type', '')
        log_test(14, "Content-Type is image", 'image' in content_type, f"Got: {content_type}")
        log_test(14, "Body is non-empty", len(resp.content) > 0, f"Got: {len(resp.content)} bytes")
    else:
        log_test(14, "Admin document access", False, f"Status: {resp.status_code}")
else:
    log_test(14, "Admin document access", False, "Missing doc_id")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total tests: {tests_passed + tests_failed}")
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"Success rate: {(tests_passed / (tests_passed + tests_failed) * 100):.1f}%")
print("=" * 80)

if tests_failed > 0:
    print("\n❌ FAILED TESTS:")
    for result in test_results:
        if "❌ FAIL" in result:
            print(result)

print("\n✅ ALL TESTS COMPLETED")
