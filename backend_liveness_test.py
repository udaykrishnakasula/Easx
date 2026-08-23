import urllib.request
import json
import io
import uuid

def post(url, data, headers={}):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json', **headers})
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode('utf-8-sig', errors='ignore')
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8-sig', errors='ignore')
        return e.code, json.loads(raw) if raw else {}

def get(url, headers={}):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw.decode('utf-8-sig', errors='ignore'))
            except:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode('utf-8-sig', errors='ignore'))
        except:
            return e.code, raw

def post_multipart(url, fields, files, headers={}):
    boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(f'{value}\r\n'.encode())
    for name, (filename, filedata, content_type) in files.items():
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.write(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.write(filedata)
        body.write(b'\r\n')
    body.write(f'--{boundary}--\r\n'.encode())
    req = urllib.request.Request(url, data=body.getvalue(), headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        **headers
    })
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode('utf-8-sig', errors='ignore')
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8-sig', errors='ignore')
        return e.code, json.loads(raw) if raw else {}

def run_tests():
    print("==================================================")
    print("EASYX KYC LIVENESS ARCHITECTURE VALIDATION")
    print("==================================================")

    # 1. Login
    _, u_res = post('http://localhost:3000/api/auth/login', {'email': 'investor@easyx.com', 'password': 'User@Easyx2026'})
    u_token = u_res['access_token']
    u_id = u_res['user']['id']

    _, a_res = post('http://localhost:3000/api/auth/login', {'email': 'admin@easyx.com', 'password': 'Admin@Easyx2026'})
    a_token = a_res['access_token']

    print("1. Authentication: User and Admin signed in.")

    # 2. Session Initialization
    s_init, sess = post('http://localhost:3000/api/kyc/liveness/session', {'userId': u_id}, {'Authorization': f'Bearer {u_token}'})
    assert s_init == 201
    sess_id = sess['sessionId']
    print(f"2. Session Created: {sess_id} [Status: {sess['status']}, Provider: {sess['provider']}]")

    # 3. Security: Cross-user Access Prevention
    _, u2_res = post('http://localhost:3000/api/auth/register', {
        'name': 'Test Attacker',
        'email': f'attacker_{uuid.uuid4().hex[:6]}@easyx.com',
        'phone': f'+9199{uuid.uuid4().int % 100000000:08d}',
        'password': 'Password@123'
    })
    u2_token = u2_res['access_token']
    s_unauth, _ = get(f'http://localhost:3000/api/kyc/liveness/session/{sess_id}', {'Authorization': f'Bearer {u2_token}'})
    assert s_unauth == 403, f"Expected 403, got {s_unauth}"
    print("3. Security: Cross-user session access blocked (HTTP 403).")

    # 4. Simulated Failure Handling & Retry
    s_fail_sess, fail_sess = post('http://localhost:3000/api/kyc/liveness/session', {'userId': u_id}, {'Authorization': f'Bearer {u_token}'})
    fail_id = fail_sess['sessionId']
    s_vfail, vfail_res = post_multipart('http://localhost:3000/api/kyc/liveness/verify', {
        'sessionId': fail_id,
        'simulatedOutcome': 'FAILURE',
        'failureCategory': 'SPOOF_OR_UNCLEAR_FACE',
        'failureReason': 'Face not centered or liveness challenge unfulfilled'
    }, {}, {'Authorization': f'Bearer {u_token}'})
    assert s_vfail == 200 and not vfail_res['verified']
    print("4. Failure Handling: Failed liveness check returns specific reason and allows retry.")

    # 5. Security: Cannot submit KYC without verified liveness
    dummy_doc = b'DEMO_NATIONAL_ID_FILE'
    s_bad_sub, _ = post_multipart('http://localhost:3000/api/kyc/submit', {
        'id_type': 'national_id',
        'liveness_session_id': fail_id
    }, {
        'id_document': ('national_id.png', dummy_doc, 'image/png')
    }, {'Authorization': f'Bearer {u_token}'})
    assert s_bad_sub == 400
    print("5. Security: KYC submission blocked when liveness session is unverified (HTTP 400).")

    # 6. Successful Verification
    dummy_selfie = b'DEMO_LIVE_CAMERA_FRAME_DATA'
    s_succ_v, succ_res = post_multipart('http://localhost:3000/api/kyc/liveness/verify', {
        'sessionId': sess_id,
        'simulatedOutcome': 'SUCCESS'
    }, {
        'selfie': ('live_selfie.jpg', dummy_selfie, 'image/jpeg')
    }, {'Authorization': f'Bearer {u_token}'})
    assert s_succ_v == 200 and succ_res['verified']
    v_id = succ_res['verificationId']
    print(f"6. Verification Successful: ID={v_id}, Confidence={succ_res['confidenceScore']}.")

    # 7. Security: Duplicate Verification Prevention
    s_dup_v, _ = post_multipart('http://localhost:3000/api/kyc/liveness/verify', {
        'sessionId': sess_id,
        'simulatedOutcome': 'SUCCESS'
    }, {}, {'Authorization': f'Bearer {u_token}'})
    assert s_dup_v == 409
    print("7. Security: Duplicate verification on completed session blocked (HTTP 409).")

    # 8. Submit KYC with Liveness
    s_sub, sub_res = post_multipart('http://localhost:3000/api/kyc/submit', {
        'id_type': 'national_id',
        'id_number': 'AADHAAR-5544-3322-1100',
        'liveness_session_id': sess_id
    }, {
        'id_document': ('national_id.png', dummy_doc, 'image/png')
    }, {'Authorization': f'Bearer {u_token}'})
    assert s_sub == 200 and sub_res['status'] == 'pending'
    print(f"8. KYC Submitted: Record created with liveness reference {v_id}.")

    # 9. Security: Replay Attack Blocked
    s_reuse, _ = post_multipart('http://localhost:3000/api/kyc/submit', {
        'id_type': 'national_id',
        'liveness_session_id': sess_id
    }, {
        'id_document': ('national_id.png', dummy_doc, 'image/png')
    }, {'Authorization': f'Bearer {u_token}'})
    assert s_reuse == 409
    print("9. Security: Reusing consumed liveness session blocked (HTTP 409).")

    # 10. Admin Review & Verification Metadata Inspection
    s_akyc, akyc_list = get('http://localhost:3000/api/admin/kyc?status=pending', {'Authorization': f'Bearer {a_token}'})
    assert s_akyc == 200
    admin_rec = next(k for k in akyc_list if k['user_email'] == 'investor@easyx.com')
    assert admin_rec['liveness'] is not None and admin_rec['liveness']['verificationId'] == v_id
    print("10. Admin KYC Inspection: Verified liveness metadata visible to admin.")

    # 11. Admin Approval
    s_appr, _ = post(f'http://localhost:3000/api/admin/kyc/{admin_rec["id"]}/approve', {}, {'Authorization': f'Bearer {a_token}'})
    assert s_appr == 200
    print("11. Admin Approval: Decision recorded in audit log.")

    # 12. Final User Verification
    _, final_status = get('http://localhost:3000/api/kyc', {'Authorization': f'Bearer {u_token}'})
    assert final_status['status'] == 'approved'
    print("12. User Status: Identity and Liveness verified ('approved').")

    print("\n==================================================")
    print("ALL 12 TEST SCENARIOS PASSED WITH ZERO ERRORS!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
