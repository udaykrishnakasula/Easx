#!/usr/bin/env python3
"""
Comprehensive test suite for audit logging + admin reports/exports.

Tests:
- PART A: Audit logging (admin.login, deposit.approve/reject, kyc.approve/reject, existing actions)
- PART B: Exports (8 datasets in CSV & XLSX formats)
- PART C: Access control (401 without auth, 403 for non-admin)
- Regression: rewards feed, notifications, investment detail, security hardening
"""
import os
import sys
import time
import uuid
import requests
from io import BytesIO

# Backend URL from environment
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "https://easyx-loader.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Admin credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test counters
tests_run = 0
tests_passed = 0
tests_failed = 0


def log_test(name, passed, details=""):
    global tests_run, tests_passed, tests_failed
    tests_run += 1
    if passed:
        tests_passed += 1
        print(f"✅ TEST {tests_run}: {name}")
    else:
        tests_failed += 1
        print(f"❌ TEST {tests_run} FAILED: {name}")
    if details:
        print(f"   {details}")


def create_test_user(email_suffix=None):
    """Register a new test user and return (user, token)."""
    if email_suffix is None:
        email_suffix = str(int(time.time() * 1000))
    email = f"audituser{email_suffix}@easyx.com"
    password = "Passw0rd!"
    
    # Generate a valid 10-digit phone number from timestamp
    phone_digits = str(int(time.time() * 1000))[-10:]
    
    resp = requests.post(f"{API_BASE}/auth/register", json={
        "name": f"Audit Test User {email_suffix}",
        "email": email,
        "phone": f"+91{phone_digits}",
        "password": password,
        "password_confirm": password,
    })
    
    if resp.status_code != 201:
        print(f"⚠️  Failed to create test user: {resp.status_code} {resp.text}")
        return None, None
    
    data = resp.json()
    return data["user"], data["access_token"]


def admin_login():
    """Login as admin and return token."""
    resp = requests.post(f"{API_BASE}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    
    if resp.status_code != 200:
        print(f"⚠️  Admin login failed: {resp.status_code} {resp.text}")
        return None
    
    return resp.json()["access_token"]


def get_audit_logs(token, action=None, entity_type=None):
    """Fetch audit logs with optional filters."""
    params = {}
    if action:
        params["action"] = action
    if entity_type:
        params["entity_type"] = entity_type
    
    resp = requests.get(f"{API_BASE}/admin/audit-logs", headers={"Authorization": f"Bearer {token}"}, params=params)
    
    if resp.status_code != 200:
        return None
    
    return resp.json()


def find_audit_entry(logs, action, entity_id=None):
    """Find an audit entry matching action and optionally entity_id."""
    if not logs:
        return None
    
    for entry in logs:
        if entry.get("action") == action:
            if entity_id is None or entry.get("entity_id") == entity_id:
                return entry
    
    return None


def main():
    print("=" * 80)
    print("AUDIT LOGGING + ADMIN REPORTS/EXPORTS TEST SUITE")
    print("=" * 80)
    print()
    
    # ========== PART A: AUDIT LOGGING ==========
    print("=" * 80)
    print("PART A: AUDIT LOGGING")
    print("=" * 80)
    print()
    
    # A1: admin.login audit entry
    print("--- A1: admin.login audit entry ---")
    admin_token = admin_login()
    log_test("Admin login successful", admin_token is not None)
    
    if admin_token:
        # Fetch audit logs
        audit_logs = get_audit_logs(admin_token, action="admin.login")
        log_test("GET /api/admin/audit-logs returns 200", audit_logs is not None)
        
        if audit_logs:
            # Find admin.login entry
            login_entry = find_audit_entry(audit_logs, "admin.login")
            log_test("admin.login entry exists", login_entry is not None)
            
            if login_entry:
                # Verify fields
                has_action = login_entry.get("action") == "admin.login"
                has_actor_email = login_entry.get("actor_email") == ADMIN_EMAIL
                has_entity_type = login_entry.get("entity_type") == "user"
                has_meta_ip = "ip" in login_entry.get("meta", {})
                has_created_at = "created_at" in login_entry
                
                log_test("admin.login has action field", has_action, f"action={login_entry.get('action')}")
                log_test("admin.login has actor_email", has_actor_email, f"actor_email={login_entry.get('actor_email')}")
                log_test("admin.login has entity_type", has_entity_type, f"entity_type={login_entry.get('entity_type')}")
                log_test("admin.login has meta.ip", has_meta_ip, f"meta.ip={login_entry.get('meta', {}).get('ip')}")
                log_test("admin.login has created_at", has_created_at)
    
    print()
    
    # A2: deposit.approve and deposit.reject audit entries
    print("--- A2: deposit.approve and deposit.reject audit entries ---")
    
    # Create two test users for deposits
    user1, token1 = create_test_user(f"dep1_{int(time.time() * 1000)}")
    user2, token2 = create_test_user(f"dep2_{int(time.time() * 1000) + 1}")
    
    log_test("Created test user 1 for deposit", user1 is not None)
    log_test("Created test user 2 for deposit", user2 is not None)
    
    if user1 and token1 and user2 and token2:
        # Create two deposits with unique tx_hash
        tx_hash1 = f"0xdeposit{uuid.uuid4().hex[:20]}"
        tx_hash2 = f"0xdeposit{uuid.uuid4().hex[:20]}"
        
        resp1 = requests.post(f"{API_BASE}/deposits", headers={"Authorization": f"Bearer {token1}"}, json={
            "network": "TRC20",
            "amount": "300.00",
            "tx_hash": tx_hash1,
        })
        
        resp2 = requests.post(f"{API_BASE}/deposits", headers={"Authorization": f"Bearer {token2}"}, json={
            "network": "BEP20",
            "amount": "500.00",
            "tx_hash": tx_hash2,
        })
        
        log_test("User 1 created deposit", resp1.status_code == 201, f"status={resp1.status_code}, error={resp1.text if resp1.status_code != 201 else ''}")
        log_test("User 2 created deposit", resp2.status_code == 201, f"status={resp2.status_code}, error={resp2.text if resp2.status_code != 201 else ''}")
        
        if resp1.status_code == 201 and resp2.status_code == 201:
            deposit1_id = resp1.json().get("id")
            deposit2_id = resp2.json().get("id")
            
            # Admin approve deposit 1
            approve_resp = requests.post(
                f"{API_BASE}/admin/deposits/{deposit1_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"approved_amount": "300.00", "note": "Test approval"}
            )
            
            log_test("Admin approved deposit 1", approve_resp.status_code == 200, f"status={approve_resp.status_code}")
            
            # Admin reject deposit 2
            reject_resp = requests.post(
                f"{API_BASE}/admin/deposits/{deposit2_id}/reject",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"note": "Test rejection"}
            )
            
            log_test("Admin rejected deposit 2", reject_resp.status_code == 200, f"status={reject_resp.status_code}")
            
            # Verify audit entries
            time.sleep(0.5)  # Brief delay for audit log writes
            
            approve_logs = get_audit_logs(admin_token, action="deposit.approve")
            reject_logs = get_audit_logs(admin_token, action="deposit.reject")
            
            approve_entry = find_audit_entry(approve_logs, "deposit.approve", deposit1_id)
            reject_entry = find_audit_entry(reject_logs, "deposit.reject", deposit2_id)
            
            log_test("deposit.approve audit entry exists", approve_entry is not None)
            log_test("deposit.reject audit entry exists", reject_entry is not None)
            
            if approve_entry:
                has_actor = approve_entry.get("actor_email") == ADMIN_EMAIL
                has_entity = approve_entry.get("entity_type") == "deposit" and approve_entry.get("entity_id") == deposit1_id
                has_meta_amount = "approved_amount" in approve_entry.get("meta", {})
                
                log_test("deposit.approve has correct actor", has_actor)
                log_test("deposit.approve has correct entity", has_entity)
                log_test("deposit.approve has meta.approved_amount", has_meta_amount)
            
            if reject_entry:
                has_actor = reject_entry.get("actor_email") == ADMIN_EMAIL
                has_entity = reject_entry.get("entity_type") == "deposit" and reject_entry.get("entity_id") == deposit2_id
                has_meta_reason = "reason" in reject_entry.get("meta", {})
                
                log_test("deposit.reject has correct actor", has_actor)
                log_test("deposit.reject has correct entity", has_entity)
                log_test("deposit.reject has meta.reason", has_meta_reason)
    
    print()
    
    # A3: kyc.approve and kyc.reject audit entries
    print("--- A3: kyc.approve and kyc.reject audit entries ---")
    
    # Create two test users for KYC
    user3, token3 = create_test_user(f"kyc1_{int(time.time() * 1000)}")
    user4, token4 = create_test_user(f"kyc2_{int(time.time() * 1000) + 1}")
    
    log_test("Created test user 3 for KYC", user3 is not None)
    log_test("Created test user 4 for KYC", user4 is not None)
    
    if user3 and token3 and user4 and token4:
        # Create a real 1x1 PNG image (smallest valid PNG)
        png_bytes = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001"
            "08060000001f15c4890000000a49444154789c6300010000"
            "00050001d5a2f5e90000000049454e44ae426082"
        )
        
        # Submit KYC for user 3
        files1 = {
            "id_document": ("id.png", BytesIO(png_bytes), "image/png"),
            "selfie": ("selfie.png", BytesIO(png_bytes), "image/png"),
        }
        data1 = {
            "id_type": "passport",
            "id_number": "KYC123456",
        }
        
        kyc_resp1 = requests.post(
            f"{API_BASE}/kyc/submit",
            headers={"Authorization": f"Bearer {token3}"},
            files=files1,
            data=data1
        )
        
        # Submit KYC for user 4
        files2 = {
            "id_document": ("id.png", BytesIO(png_bytes), "image/png"),
            "selfie": ("selfie.png", BytesIO(png_bytes), "image/png"),
        }
        data2 = {
            "id_type": "aadhaar",
            "id_number": "KYC789012",
        }
        
        kyc_resp2 = requests.post(
            f"{API_BASE}/kyc/submit",
            headers={"Authorization": f"Bearer {token4}"},
            files=files2,
            data=data2
        )
        
        log_test("User 3 submitted KYC", kyc_resp1.status_code == 200, f"status={kyc_resp1.status_code}")
        log_test("User 4 submitted KYC", kyc_resp2.status_code == 200, f"status={kyc_resp2.status_code}")
        
        if kyc_resp1.status_code == 200 and kyc_resp2.status_code == 200:
            # Get KYC record IDs from admin list (since submit doesn't return record ID)
            time.sleep(0.5)  # Brief delay for DB writes
            
            admin_kyc_list = requests.get(
                f"{API_BASE}/admin/kyc",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"status": "pending"}
            )
            
            if admin_kyc_list.status_code == 200:
                kyc_records = admin_kyc_list.json()
                
                # Find our test users' KYC records
                kyc1_id = None
                kyc2_id = None
                
                for record in kyc_records:
                    if record.get("user_id") == user3["id"]:
                        kyc1_id = record.get("id")
                    elif record.get("user_id") == user4["id"]:
                        kyc2_id = record.get("id")
            else:
                kyc1_id = None
                kyc2_id = None
            
            if not kyc1_id or not kyc2_id:
                log_test("Found KYC record IDs from admin list", False, f"kyc1_id={kyc1_id}, kyc2_id={kyc2_id}")
                print()
                return
            
            # Admin approve KYC 1
            approve_resp = requests.post(
                f"{API_BASE}/admin/kyc/{kyc1_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            log_test("Admin approved KYC 1", approve_resp.status_code == 200, f"status={approve_resp.status_code}, error={approve_resp.text if approve_resp.status_code != 200 else ''}")
            
            # Admin reject KYC 2
            reject_resp = requests.post(
                f"{API_BASE}/admin/kyc/{kyc2_id}/reject",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"reason": "Document unclear"}
            )
            
            log_test("Admin rejected KYC 2", reject_resp.status_code == 200, f"status={reject_resp.status_code}, error={reject_resp.text if reject_resp.status_code != 200 else ''}")
            
            # Verify audit entries
            time.sleep(0.5)
            
            approve_logs = get_audit_logs(admin_token, action="kyc.approve")
            reject_logs = get_audit_logs(admin_token, action="kyc.reject")
            
            approve_entry = find_audit_entry(approve_logs, "kyc.approve", kyc1_id)
            reject_entry = find_audit_entry(reject_logs, "kyc.reject", kyc2_id)
            
            log_test("kyc.approve audit entry exists", approve_entry is not None)
            log_test("kyc.reject audit entry exists", reject_entry is not None)
            
            if approve_entry:
                has_actor = approve_entry.get("actor_email") == ADMIN_EMAIL
                has_entity = approve_entry.get("entity_type") == "kyc_record" and approve_entry.get("entity_id") == kyc1_id
                
                log_test("kyc.approve has correct actor", has_actor)
                log_test("kyc.approve has correct entity", has_entity)
            
            if reject_entry:
                has_actor = reject_entry.get("actor_email") == ADMIN_EMAIL
                has_entity = reject_entry.get("entity_type") == "kyc_record" and reject_entry.get("entity_id") == kyc2_id
                has_meta_reason = "reason" in reject_entry.get("meta", {})
                
                log_test("kyc.reject has correct actor", has_actor)
                log_test("kyc.reject has correct entity", has_entity)
                log_test("kyc.reject has meta.reason", has_meta_reason)
    
    print()
    
    # A4: Existing audit actions
    print("--- A4: Existing audit actions ---")
    
    # Check that existing actions CAN be logged (we've already tested wallet.adjust, deposit.approve/reject, kyc.approve/reject)
    # We don't need to test every single action - just verify the audit system is working
    all_logs = get_audit_logs(admin_token)
    
    # Verify we have audit logs
    log_test("Audit logging system is working", all_logs is not None and len(all_logs) > 0, f"found {len(all_logs) if all_logs else 0} total audit entries")
    
    # Check for the actions we've already triggered in this test
    actions_we_triggered = [
        "admin.login",
        "deposit.approve",
        "deposit.reject",
        "kyc.approve",
        "kyc.reject",
        "wallet.adjust",
        "report.export"
    ]
    
    for action in actions_we_triggered:
        entries = [e for e in all_logs if e.get("action") == action]
        log_test(f"Audit action '{action}' logged correctly", len(entries) > 0, f"found {len(entries)} entries")
    
    print()
    
    # ========== PART B: EXPORTS ==========
    print("=" * 80)
    print("PART B: ADMIN REPORTS/EXPORTS")
    print("=" * 80)
    print()
    
    # B1: GET /api/admin/reports lists datasets and formats
    print("--- B1: GET /api/admin/reports ---")
    
    reports_resp = requests.get(f"{API_BASE}/admin/reports", headers={"Authorization": f"Bearer {admin_token}"})
    
    log_test("GET /api/admin/reports returns 200", reports_resp.status_code == 200, f"status={reports_resp.status_code}")
    
    if reports_resp.status_code == 200:
        reports_data = reports_resp.json()
        datasets = reports_data.get("datasets", [])
        formats = reports_data.get("formats", [])
        
        expected_datasets = [
            "users", "deposits", "investments", "matured_investments",
            "withdrawals", "referral_commissions", "wallet_transactions", "kyc"
        ]
        
        has_all_datasets = all(ds in datasets for ds in expected_datasets)
        has_csv = "csv" in formats
        has_xlsx = "xlsx" in formats
        
        log_test("Reports response has 8 datasets", len(datasets) == 8 and has_all_datasets, f"datasets={datasets}")
        log_test("Reports response has csv format", has_csv, f"formats={formats}")
        log_test("Reports response has xlsx format", has_xlsx, f"formats={formats}")
    
    print()
    
    # B2: Export each dataset in CSV and XLSX formats
    print("--- B2: Export each dataset in CSV and XLSX ---")
    
    datasets_to_test = [
        "users", "deposits", "investments", "matured_investments",
        "withdrawals", "referral_commissions", "wallet_transactions", "kyc"
    ]
    
    for dataset in datasets_to_test:
        # Test CSV export
        csv_resp = requests.get(
            f"{API_BASE}/admin/reports/{dataset}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"format": "csv"}
        )
        
        csv_ok = csv_resp.status_code == 200
        csv_content_type = csv_resp.headers.get("Content-Type", "")
        csv_disposition = csv_resp.headers.get("Content-Disposition", "")
        csv_has_content = len(csv_resp.content) > 0
        csv_has_header = b"\n" in csv_resp.content or b"\r\n" in csv_resp.content
        
        log_test(
            f"Export {dataset} as CSV returns 200",
            csv_ok,
            f"status={csv_resp.status_code}"
        )
        
        if csv_ok:
            log_test(
                f"CSV {dataset} has correct Content-Type",
                "text/csv" in csv_content_type,
                f"Content-Type={csv_content_type}"
            )
            log_test(
                f"CSV {dataset} has Content-Disposition attachment",
                "attachment" in csv_disposition and "filename" in csv_disposition,
                f"Content-Disposition={csv_disposition}"
            )
            log_test(
                f"CSV {dataset} has non-empty body",
                csv_has_content,
                f"size={len(csv_resp.content)} bytes"
            )
            log_test(
                f"CSV {dataset} has header row",
                csv_has_header,
                "first line contains header"
            )
        
        # Test XLSX export
        xlsx_resp = requests.get(
            f"{API_BASE}/admin/reports/{dataset}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"format": "xlsx"}
        )
        
        xlsx_ok = xlsx_resp.status_code == 200
        xlsx_content_type = xlsx_resp.headers.get("Content-Type", "")
        xlsx_disposition = xlsx_resp.headers.get("Content-Disposition", "")
        xlsx_has_content = len(xlsx_resp.content) > 0
        xlsx_is_valid = xlsx_resp.content[:2] == b"PK"  # XLSX files start with PK (ZIP format)
        
        log_test(
            f"Export {dataset} as XLSX returns 200",
            xlsx_ok,
            f"status={xlsx_resp.status_code}"
        )
        
        if xlsx_ok:
            log_test(
                f"XLSX {dataset} has correct Content-Type",
                "spreadsheetml.sheet" in xlsx_content_type,
                f"Content-Type={xlsx_content_type}"
            )
            log_test(
                f"XLSX {dataset} has Content-Disposition attachment",
                "attachment" in xlsx_disposition and "filename" in xlsx_disposition,
                f"Content-Disposition={xlsx_disposition}"
            )
            log_test(
                f"XLSX {dataset} has non-empty body",
                xlsx_has_content,
                f"size={len(xlsx_resp.content)} bytes"
            )
            log_test(
                f"XLSX {dataset} is valid (starts with PK)",
                xlsx_is_valid,
                f"first 2 bytes={xlsx_resp.content[:2]}"
            )
    
    print()
    
    # B3: Error cases (404 for unknown dataset, 400 for invalid format)
    print("--- B3: Export error cases ---")
    
    not_found_resp = requests.get(
        f"{API_BASE}/admin/reports/not_a_dataset",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"format": "csv"}
    )
    
    log_test("Unknown dataset returns 404", not_found_resp.status_code == 404, f"status={not_found_resp.status_code}")
    
    invalid_format_resp = requests.get(
        f"{API_BASE}/admin/reports/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"format": "pdf"}
    )
    
    log_test("Invalid format returns 400", invalid_format_resp.status_code == 400, f"status={invalid_format_resp.status_code}")
    
    print()
    
    # B4: Verify report.export audit entries
    print("--- B4: report.export audit entries ---")
    
    time.sleep(0.5)
    export_logs = get_audit_logs(admin_token, action="report.export")
    
    log_test("report.export audit entries exist", export_logs is not None and len(export_logs) > 0, f"found {len(export_logs) if export_logs else 0} entries")
    
    if export_logs and len(export_logs) > 0:
        sample_entry = export_logs[0]
        has_format = "format" in sample_entry.get("meta", {})
        has_row_count = "row_count" in sample_entry.get("meta", {})
        
        log_test("report.export has meta.format", has_format, f"meta={sample_entry.get('meta')}")
        log_test("report.export has meta.row_count", has_row_count, f"meta={sample_entry.get('meta')}")
    
    print()
    
    # ========== PART C: ACCESS CONTROL ==========
    print("=" * 80)
    print("PART C: ACCESS CONTROL")
    print("=" * 80)
    print()
    
    # C1: 401 without auth token
    print("--- C1: 401 without auth token ---")
    
    no_auth_reports = requests.get(f"{API_BASE}/admin/reports/users", params={"format": "csv"})
    no_auth_logs = requests.get(f"{API_BASE}/admin/audit-logs")
    
    log_test("GET /api/admin/reports/users without auth returns 401", no_auth_reports.status_code == 401, f"status={no_auth_reports.status_code}")
    log_test("GET /api/admin/audit-logs without auth returns 401", no_auth_logs.status_code == 401, f"status={no_auth_logs.status_code}")
    
    print()
    
    # C2: 403 for non-admin user
    print("--- C2: 403 for non-admin user ---")
    
    # Create a regular user
    regular_user, regular_token = create_test_user(f"regular_{int(time.time() * 1000)}")
    
    log_test("Created regular (non-admin) user", regular_user is not None)
    
    if regular_token:
        non_admin_reports = requests.get(
            f"{API_BASE}/admin/reports/users",
            headers={"Authorization": f"Bearer {regular_token}"},
            params={"format": "csv"}
        )
        
        non_admin_logs = requests.get(
            f"{API_BASE}/admin/audit-logs",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        
        log_test("Non-admin GET /api/admin/reports/users returns 403", non_admin_reports.status_code == 403, f"status={non_admin_reports.status_code}")
        log_test("Non-admin GET /api/admin/audit-logs returns 403", non_admin_logs.status_code == 403, f"status={non_admin_logs.status_code}")
    
    print()
    
    # ========== REGRESSION TESTS ==========
    print("=" * 80)
    print("REGRESSION TESTS")
    print("=" * 80)
    print()
    
    # Create a funded user for regression tests
    reg_user, reg_token = create_test_user(f"reg_{int(time.time() * 1000)}")
    
    if reg_user and reg_token:
        # Fund the user
        adjust_resp = requests.post(
            f"{API_BASE}/admin/wallet/adjust",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_id": reg_user["id"],
                "amount": "1000.00",
                "direction": "credit",
                "note": "Regression test funding"
            }
        )
        
        log_test("Funded regression test user", adjust_resp.status_code == 200)
        
        if adjust_resp.status_code == 200:
            # Test rewards feed
            rewards_resp = requests.get(
                f"{API_BASE}/rewards/feed",
                headers={"Authorization": f"Bearer {reg_token}"}
            )
            
            log_test("GET /api/rewards/feed works", rewards_resp.status_code == 200, f"status={rewards_resp.status_code}")
            
            # Test notifications
            notif_resp = requests.get(
                f"{API_BASE}/notifications",
                headers={"Authorization": f"Bearer {reg_token}"}
            )
            
            log_test("GET /api/notifications works", notif_resp.status_code == 200, f"status={notif_resp.status_code}")
            
            # Create an investment and test investment detail
            invest_resp = requests.post(
                f"{API_BASE}/investments",
                headers={"Authorization": f"Bearer {reg_token}"},
                json={
                    "plan_key": "silver",
                    "idempotency_key": f"reg-invest-{uuid.uuid4()}"
                }
            )
            
            log_test("POST /api/investments works", invest_resp.status_code == 201, f"status={invest_resp.status_code}")
            
            if invest_resp.status_code == 201:
                inv_id = invest_resp.json().get("id")
                
                detail_resp = requests.get(
                    f"{API_BASE}/investments/{inv_id}",
                    headers={"Authorization": f"Bearer {reg_token}"}
                )
                
                log_test("GET /api/investments/{id} works", detail_resp.status_code == 200, f"status={detail_resp.status_code}")
                
                if detail_resp.status_code == 200:
                    inv_data = detail_resp.json()
                    has_profit_pct = "profit_percentage" in inv_data
                    has_maturity_pct = "maturity_percentage" in inv_data
                    
                    log_test("Investment detail has profit_percentage", has_profit_pct)
                    log_test("Investment detail has maturity_percentage", has_maturity_pct)
            
            # Test rate limiting (security hardening regression)
            # Note: We won't actually trigger rate limits to avoid blocking, just verify endpoint works
            login_resp = requests.post(f"{API_BASE}/auth/login", json={
                "email": reg_user["email"],
                "password": "WrongPassword123!"
            })
            
            log_test("Rate limiting endpoint accessible (login with wrong password)", login_resp.status_code == 401, f"status={login_resp.status_code}")
    
    print()
    
    # ========== SUMMARY ==========
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests run: {tests_run}")
    print(f"Tests passed: {tests_passed} ✅")
    print(f"Tests failed: {tests_failed} ❌")
    print(f"Success rate: {(tests_passed / tests_run * 100) if tests_run > 0 else 0:.1f}%")
    print()
    
    if tests_failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
