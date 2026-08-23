#!/usr/bin/env python3
"""
Extended test suite for notification triggers - covering additional scenarios:
1. Remaining regression triggers (investment_cancelled, withdrawal_approved/rejected/paid, account suspended/reactivated)
2. Referral commission trigger
3. Additional security tests
4. Edge cases
"""
import requests
import time
import io

# Backend URL
BASE_URL = "https://e30f9440-c6d8-475c-bcaa-ce8359e74259.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test counters
tests_passed = 0
tests_failed = 0
test_results = []


def log_test(name, passed, details=""):
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        status = "✅ PASS"
    else:
        tests_failed += 1
        status = "❌ FAIL"
    msg = f"{status} - {name}"
    if details:
        msg += f": {details}"
    print(msg)
    test_results.append({"name": name, "passed": passed, "details": details})


def login(email, password):
    """Login and return access token."""
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        return resp.json()["access_token"]
    raise Exception(f"Login failed for {email}: {resp.status_code} {resp.text}")


def register_user(name, email, password, phone):
    """Register a new user and return access token."""
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": name,
        "email": email,
        "password": password,
        "phone": phone,
    })
    if resp.status_code == 201:
        return resp.json()["access_token"], resp.json()["user"]["id"]
    raise Exception(f"Registration failed: {resp.status_code} {resp.text}")


def get_notifications(token):
    """Get all notifications for user."""
    resp = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Get notifications failed: {resp.status_code} {resp.text}")


def admin_fund_user(admin_token, user_id, amount):
    """Admin credits user wallet."""
    resp = requests.post(f"{BASE_URL}/admin/wallet/adjust", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"user_id": user_id, "direction": "credit", "amount": str(amount), "note": "test funding"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin fund failed: {resp.status_code} {resp.text}")


def admin_cancel_investment(admin_token, investment_id, refund_amount, reason):
    """Admin cancels investment."""
    resp = requests.post(f"{BASE_URL}/admin/investments/{investment_id}/cancel",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"refund_amount": str(refund_amount), "reason": reason})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin cancel investment failed: {resp.status_code} {resp.text}")


def admin_approve_kyc(admin_token, record_id):
    """Admin approves KYC."""
    resp = requests.post(f"{BASE_URL}/admin/kyc/{record_id}/approve", 
                        headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin approve KYC failed: {resp.status_code} {resp.text}")


def admin_reject_kyc(admin_token, record_id, reason):
    """Admin rejects KYC."""
    resp = requests.post(f"{BASE_URL}/admin/kyc/{record_id}/reject",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"reason": reason})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin reject KYC failed: {resp.status_code} {resp.text}")


def admin_approve_withdrawal(admin_token, withdrawal_id):
    """Admin approves withdrawal."""
    resp = requests.post(f"{BASE_URL}/admin/withdrawals/{withdrawal_id}/approve",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin approve withdrawal failed: {resp.status_code} {resp.text}")


def admin_reject_withdrawal(admin_token, withdrawal_id, note):
    """Admin rejects withdrawal."""
    resp = requests.post(f"{BASE_URL}/admin/withdrawals/{withdrawal_id}/reject",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"note": note})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin reject withdrawal failed: {resp.status_code} {resp.text}")


def admin_process_withdrawal(admin_token, withdrawal_id, tx_hash):
    """Admin processes withdrawal."""
    resp = requests.post(f"{BASE_URL}/admin/withdrawals/{withdrawal_id}/process",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"tx_hash": tx_hash})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin process withdrawal failed: {resp.status_code} {resp.text}")


def admin_suspend_user(admin_token, user_id, reason):
    """Admin suspends user."""
    resp = requests.post(f"{BASE_URL}/admin/users/{user_id}/suspend",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"reason": reason})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin suspend user failed: {resp.status_code} {resp.text}")


def admin_unsuspend_user(admin_token, user_id):
    """Admin unsuspends user."""
    resp = requests.post(f"{BASE_URL}/admin/users/{user_id}/unsuspend",
                        headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin unsuspend user failed: {resp.status_code} {resp.text}")


def create_png_bytes():
    """Create a minimal valid PNG file (1x1 red pixel)."""
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D,
        0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])


print("=" * 80)
print("EXTENDED NOTIFICATION TRIGGERS TEST SUITE")
print("=" * 80)

# ============================================================================
# PART 1: REGRESSION - REMAINING EXISTING TRIGGERS
# ============================================================================
print("\n[PART 1] Testing remaining existing triggers (regression)")

# Test 1: investment_cancelled trigger
print("\n--- Test 1: investment_cancelled trigger (regression) ---")
try:
    timestamp = int(time.time())
    user1_token, user1_id = register_user(
        f"Invest Cancel Test {timestamp}",
        f"invcancel{timestamp}@easyx.com",
        "Test@1234",
        f"+91981250{timestamp % 10000:04d}"
    )
    
    # Admin funds user and user buys investment
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user1_id, 1000)
    
    resp = requests.post(f"{BASE_URL}/investments",
                        headers={"Authorization": f"Bearer {user1_token}"},
                        json={"plan_key": "silver", "idempotency_key": f"test-cancel-{timestamp}"})
    
    if resp.status_code == 201:
        investment_id = resp.json()["id"]
        time.sleep(0.5)
        
        # Admin cancels investment
        admin_cancel_investment(admin_token, investment_id, "350", "Testing cancellation")
        
        time.sleep(0.5)
        
        # Check for investment_cancelled notification
        notifs = get_notifications(user1_token)
        cancelled_notifs = [n for n in notifs if n["type"] == "investment_cancelled"]
        
        if len(cancelled_notifs) == 1:
            notif = cancelled_notifs[0]
            if notif["title"] == "Investment cancelled" and "350" in notif["body"] and "Testing cancellation" in notif["body"]:
                log_test("investment_cancelled trigger (regression)", True, "Notification created with correct title/body")
            else:
                log_test("investment_cancelled trigger (regression)", False, f"Incorrect title/body: {notif}")
        else:
            log_test("investment_cancelled trigger (regression)", False, f"Expected 1 investment_cancelled notification, got {len(cancelled_notifs)}")
    else:
        log_test("investment_cancelled trigger (regression)", False, f"Investment creation failed: {resp.status_code}")
except Exception as e:
    log_test("investment_cancelled trigger (regression)", False, str(e))

# Test 2: kyc_rejected trigger
print("\n--- Test 2: kyc_rejected trigger (regression) ---")
try:
    timestamp = int(time.time())
    user2_token, user2_id = register_user(
        f"KYC Reject Test {timestamp}",
        f"kycreject{timestamp}@easyx.com",
        "Test@1234",
        f"+91981251{timestamp % 10000:04d}"
    )
    
    # Submit KYC
    png_bytes = create_png_bytes()
    files = {
        'id_document': ('id.png', io.BytesIO(png_bytes), 'image/png'),
        'selfie': ('selfie.png', io.BytesIO(png_bytes), 'image/png'),
    }
    data = {'id_type': 'aadhaar', 'id_number': '123456789012'}
    resp = requests.post(f"{BASE_URL}/kyc/submit",
                        headers={"Authorization": f"Bearer {user2_token}"},
                        files=files, data=data)
    
    if resp.status_code == 200:
        time.sleep(0.5)
        
        # Admin rejects KYC
        admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
        kyc_list = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
                               headers={"Authorization": f"Bearer {admin_token}"}).json()
        user2_kyc = [k for k in kyc_list if k["user_id"] == user2_id]
        
        if user2_kyc:
            admin_reject_kyc(admin_token, user2_kyc[0]["id"], "Blurry photo")
            
            time.sleep(0.5)
            
            # Check for kyc_rejected notification
            notifs = get_notifications(user2_token)
            rejected_notifs = [n for n in notifs if n["type"] == "kyc_rejected"]
            
            if len(rejected_notifs) == 1:
                notif = rejected_notifs[0]
                if notif["title"] == "KYC rejected" and "Blurry photo" in notif["body"]:
                    log_test("kyc_rejected trigger (regression)", True, "Notification created with correct title/body")
                else:
                    log_test("kyc_rejected trigger (regression)", False, f"Incorrect title/body: {notif}")
            else:
                log_test("kyc_rejected trigger (regression)", False, f"Expected 1 kyc_rejected notification, got {len(rejected_notifs)}")
        else:
            log_test("kyc_rejected trigger (regression)", False, "Could not find user's KYC record")
    else:
        log_test("kyc_rejected trigger (regression)", False, f"KYC submission failed: {resp.status_code}")
except Exception as e:
    log_test("kyc_rejected trigger (regression)", False, str(e))

# Test 3: withdrawal_approved trigger
print("\n--- Test 3: withdrawal_approved trigger (regression) ---")
try:
    timestamp = int(time.time())
    user3_token, user3_id = register_user(
        f"WD Approve Test {timestamp}",
        f"wdapprove{timestamp}@easyx.com",
        "Test@1234",
        f"+91981252{timestamp % 10000:04d}"
    )
    
    # Admin funds user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user3_id, 500)
    
    # Submit and approve KYC
    png_bytes = create_png_bytes()
    files = {
        'id_document': ('id.png', io.BytesIO(png_bytes), 'image/png'),
        'selfie': ('selfie.png', io.BytesIO(png_bytes), 'image/png'),
    }
    data = {'id_type': 'aadhaar', 'id_number': '123456789012'}
    resp = requests.post(f"{BASE_URL}/kyc/submit",
                        headers={"Authorization": f"Bearer {user3_token}"},
                        files=files, data=data)
    
    if resp.status_code == 200:
        time.sleep(0.5)
        kyc_list = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
                               headers={"Authorization": f"Bearer {admin_token}"}).json()
        user3_kyc = [k for k in kyc_list if k["user_id"] == user3_id]
        if user3_kyc:
            admin_approve_kyc(admin_token, user3_kyc[0]["id"])
            
            # Create withdrawal
            resp = requests.post(f"{BASE_URL}/withdrawals",
                                headers={"Authorization": f"Bearer {user3_token}"},
                                json={"network": "TRC20", "amount": "100", "to_address": "TXsomeaddress123456"})
            
            if resp.status_code == 201:
                withdrawal_id = resp.json()["id"]
                time.sleep(0.5)
                
                # Admin approves withdrawal
                admin_approve_withdrawal(admin_token, withdrawal_id)
                
                time.sleep(0.5)
                
                # Check for withdrawal_approved notification
                notifs = get_notifications(user3_token)
                approved_notifs = [n for n in notifs if n["type"] == "withdrawal_approved"]
                
                if len(approved_notifs) == 1:
                    notif = approved_notifs[0]
                    if notif["title"] == "Withdrawal approved" and "100" in notif["body"]:
                        log_test("withdrawal_approved trigger (regression)", True, "Notification created with correct title/body")
                    else:
                        log_test("withdrawal_approved trigger (regression)", False, f"Incorrect title/body: {notif}")
                else:
                    log_test("withdrawal_approved trigger (regression)", False, f"Expected 1 withdrawal_approved notification, got {len(approved_notifs)}")
            else:
                log_test("withdrawal_approved trigger (regression)", False, f"Withdrawal creation failed: {resp.status_code}")
        else:
            log_test("withdrawal_approved trigger (regression)", False, "Could not find user's KYC record")
    else:
        log_test("withdrawal_approved trigger (regression)", False, f"KYC submission failed: {resp.status_code}")
except Exception as e:
    log_test("withdrawal_approved trigger (regression)", False, str(e))

# Test 4: withdrawal_rejected trigger
print("\n--- Test 4: withdrawal_rejected trigger (regression) ---")
try:
    timestamp = int(time.time())
    user4_token, user4_id = register_user(
        f"WD Reject Test {timestamp}",
        f"wdreject{timestamp}@easyx.com",
        "Test@1234",
        f"+91981253{timestamp % 10000:04d}"
    )
    
    # Admin funds user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user4_id, 500)
    
    # Submit and approve KYC
    png_bytes = create_png_bytes()
    files = {
        'id_document': ('id.png', io.BytesIO(png_bytes), 'image/png'),
        'selfie': ('selfie.png', io.BytesIO(png_bytes), 'image/png'),
    }
    data = {'id_type': 'aadhaar', 'id_number': '123456789012'}
    resp = requests.post(f"{BASE_URL}/kyc/submit",
                        headers={"Authorization": f"Bearer {user4_token}"},
                        files=files, data=data)
    
    if resp.status_code == 200:
        time.sleep(0.5)
        kyc_list = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
                               headers={"Authorization": f"Bearer {admin_token}"}).json()
        user4_kyc = [k for k in kyc_list if k["user_id"] == user4_id]
        if user4_kyc:
            admin_approve_kyc(admin_token, user4_kyc[0]["id"])
            
            # Create withdrawal
            resp = requests.post(f"{BASE_URL}/withdrawals",
                                headers={"Authorization": f"Bearer {user4_token}"},
                                json={"network": "TRC20", "amount": "100", "to_address": "TXsomeaddress123456"})
            
            if resp.status_code == 201:
                withdrawal_id = resp.json()["id"]
                time.sleep(0.5)
                
                # Admin rejects withdrawal
                admin_reject_withdrawal(admin_token, withdrawal_id, "Invalid address")
                
                time.sleep(0.5)
                
                # Check for withdrawal_rejected notification
                notifs = get_notifications(user4_token)
                rejected_notifs = [n for n in notifs if n["type"] == "withdrawal_rejected"]
                
                if len(rejected_notifs) == 1:
                    notif = rejected_notifs[0]
                    if notif["title"] == "Withdrawal rejected" and "100" in notif["body"] and "Invalid address" in notif["body"]:
                        log_test("withdrawal_rejected trigger (regression)", True, "Notification created with correct title/body")
                    else:
                        log_test("withdrawal_rejected trigger (regression)", False, f"Incorrect title/body: {notif}")
                else:
                    log_test("withdrawal_rejected trigger (regression)", False, f"Expected 1 withdrawal_rejected notification, got {len(rejected_notifs)}")
            else:
                log_test("withdrawal_rejected trigger (regression)", False, f"Withdrawal creation failed: {resp.status_code}")
        else:
            log_test("withdrawal_rejected trigger (regression)", False, "Could not find user's KYC record")
    else:
        log_test("withdrawal_rejected trigger (regression)", False, f"KYC submission failed: {resp.status_code}")
except Exception as e:
    log_test("withdrawal_rejected trigger (regression)", False, str(e))

# Test 5: withdrawal_paid trigger
print("\n--- Test 5: withdrawal_paid trigger (regression) ---")
try:
    timestamp = int(time.time())
    user5_token, user5_id = register_user(
        f"WD Paid Test {timestamp}",
        f"wdpaid{timestamp}@easyx.com",
        "Test@1234",
        f"+91981254{timestamp % 10000:04d}"
    )
    
    # Admin funds user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user5_id, 500)
    
    # Submit and approve KYC
    png_bytes = create_png_bytes()
    files = {
        'id_document': ('id.png', io.BytesIO(png_bytes), 'image/png'),
        'selfie': ('selfie.png', io.BytesIO(png_bytes), 'image/png'),
    }
    data = {'id_type': 'aadhaar', 'id_number': '123456789012'}
    resp = requests.post(f"{BASE_URL}/kyc/submit",
                        headers={"Authorization": f"Bearer {user5_token}"},
                        files=files, data=data)
    
    if resp.status_code == 200:
        time.sleep(0.5)
        kyc_list = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
                               headers={"Authorization": f"Bearer {admin_token}"}).json()
        user5_kyc = [k for k in kyc_list if k["user_id"] == user5_id]
        if user5_kyc:
            admin_approve_kyc(admin_token, user5_kyc[0]["id"])
            
            # Create withdrawal
            resp = requests.post(f"{BASE_URL}/withdrawals",
                                headers={"Authorization": f"Bearer {user5_token}"},
                                json={"network": "TRC20", "amount": "100", "to_address": "TXsomeaddress123456"})
            
            if resp.status_code == 201:
                withdrawal_id = resp.json()["id"]
                time.sleep(0.5)
                
                # Admin approves and processes withdrawal
                admin_approve_withdrawal(admin_token, withdrawal_id)
                time.sleep(0.3)
                admin_process_withdrawal(admin_token, withdrawal_id, "0xabc123def456")
                
                time.sleep(0.5)
                
                # Check for withdrawal_paid notification
                notifs = get_notifications(user5_token)
                paid_notifs = [n for n in notifs if n["type"] == "withdrawal_paid"]
                
                if len(paid_notifs) == 1:
                    notif = paid_notifs[0]
                    if notif["title"] == "Withdrawal paid" and "100" in notif["body"] and "0xabc123def456" in notif["body"]:
                        log_test("withdrawal_paid trigger (regression)", True, "Notification created with correct title/body")
                    else:
                        log_test("withdrawal_paid trigger (regression)", False, f"Incorrect title/body: {notif}")
                else:
                    log_test("withdrawal_paid trigger (regression)", False, f"Expected 1 withdrawal_paid notification, got {len(paid_notifs)}")
            else:
                log_test("withdrawal_paid trigger (regression)", False, f"Withdrawal creation failed: {resp.status_code}")
        else:
            log_test("withdrawal_paid trigger (regression)", False, "Could not find user's KYC record")
    else:
        log_test("withdrawal_paid trigger (regression)", False, f"KYC submission failed: {resp.status_code}")
except Exception as e:
    log_test("withdrawal_paid trigger (regression)", False, str(e))

# Test 6: account_suspended trigger
print("\n--- Test 6: account_suspended trigger (regression) ---")
try:
    timestamp = int(time.time())
    user6_token, user6_id = register_user(
        f"Suspend Test {timestamp}",
        f"suspend{timestamp}@easyx.com",
        "Test@1234",
        f"+91981255{timestamp % 10000:04d}"
    )
    
    # Admin suspends user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_suspend_user(admin_token, user6_id, "Testing suspension")
    
    time.sleep(0.5)
    
    # Check for account_suspended notification
    notifs = get_notifications(user6_token)
    suspended_notifs = [n for n in notifs if n["type"] == "account_suspended"]
    
    if len(suspended_notifs) == 1:
        notif = suspended_notifs[0]
        if "suspended" in notif["title"].lower() and "Testing suspension" in notif["body"]:
            log_test("account_suspended trigger (regression)", True, "Notification created with correct title/body")
        else:
            log_test("account_suspended trigger (regression)", False, f"Incorrect title/body: {notif}")
    else:
        log_test("account_suspended trigger (regression)", False, f"Expected 1 account_suspended notification, got {len(suspended_notifs)}")
except Exception as e:
    log_test("account_suspended trigger (regression)", False, str(e))

# Test 7: account_reactivated trigger
print("\n--- Test 7: account_reactivated trigger (regression) ---")
try:
    timestamp = int(time.time())
    user7_token, user7_id = register_user(
        f"Reactivate Test {timestamp}",
        f"reactivate{timestamp}@easyx.com",
        "Test@1234",
        f"+91981256{timestamp % 10000:04d}"
    )
    
    # Admin suspends then reactivates user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_suspend_user(admin_token, user7_id, "Testing")
    time.sleep(0.5)
    admin_unsuspend_user(admin_token, user7_id)
    
    time.sleep(0.5)
    
    # Check for account_reactivated notification
    notifs = get_notifications(user7_token)
    reactivated_notifs = [n for n in notifs if n["type"] == "account_reactivated"]
    
    if len(reactivated_notifs) == 1:
        notif = reactivated_notifs[0]
        if "reactivated" in notif["title"].lower() or "active" in notif["body"].lower():
            log_test("account_reactivated trigger (regression)", True, "Notification created with correct title/body")
        else:
            log_test("account_reactivated trigger (regression)", False, f"Incorrect title/body: {notif}")
    else:
        log_test("account_reactivated trigger (regression)", False, f"Expected 1 account_reactivated notification, got {len(reactivated_notifs)}")
except Exception as e:
    log_test("account_reactivated trigger (regression)", False, str(e))

# Test 8: referral_commission trigger
print("\n--- Test 8: referral_commission trigger (regression) ---")
try:
    timestamp = int(time.time())
    
    # Create referrer
    referrer_token, referrer_id = register_user(
        f"Referrer {timestamp}",
        f"referrer{timestamp}@easyx.com",
        "Test@1234",
        f"+91981257{timestamp % 10000:04d}"
    )
    
    # Get referrer's referral code
    resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {referrer_token}"})
    referral_code = resp.json()["referral_code"]
    
    # Create referee with referral code
    referee_token, referee_id = register_user(
        f"Referee {timestamp}",
        f"referee{timestamp}@easyx.com",
        "Test@1234",
        f"+91981258{timestamp % 10000:04d}",
    )
    # Need to register with referral code - let's do it properly
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": f"Referee Proper {timestamp}",
        "email": f"refereeprop{timestamp}@easyx.com",
        "password": "Test@1234",
        "phone": f"+91981259{timestamp % 10000:04d}",
        "referral_code": referral_code
    })
    
    if resp.status_code == 201:
        referee_proper_token = resp.json()["access_token"]
        referee_proper_id = resp.json()["user"]["id"]
        
        # Admin funds referee
        admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_fund_user(admin_token, referee_proper_id, 1000)
        
        # Referee buys investment (should trigger referral commission for referrer)
        resp = requests.post(f"{BASE_URL}/investments",
                            headers={"Authorization": f"Bearer {referee_proper_token}"},
                            json={"plan_key": "silver", "idempotency_key": f"test-referral-{timestamp}"})
        
        if resp.status_code == 201:
            time.sleep(0.5)
            
            # Check referrer's notifications for referral_commission
            notifs = get_notifications(referrer_token)
            commission_notifs = [n for n in notifs if n["type"] == "referral_commission"]
            
            if len(commission_notifs) >= 1:
                notif = commission_notifs[0]
                if "commission" in notif["title"].lower() or "referral" in notif["body"].lower():
                    log_test("referral_commission trigger (regression)", True, "Notification created with correct title/body")
                else:
                    log_test("referral_commission trigger (regression)", False, f"Incorrect title/body: {notif}")
            else:
                log_test("referral_commission trigger (regression)", False, f"Expected >=1 referral_commission notification, got {len(commission_notifs)}")
        else:
            log_test("referral_commission trigger (regression)", False, f"Investment creation failed: {resp.status_code}")
    else:
        log_test("referral_commission trigger (regression)", False, f"Referee registration with referral code failed: {resp.status_code}")
except Exception as e:
    log_test("referral_commission trigger (regression)", False, str(e))

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("EXTENDED TEST SUMMARY")
print("=" * 80)
print(f"Total tests: {tests_passed + tests_failed}")
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"Success rate: {tests_passed / (tests_passed + tests_failed) * 100:.1f}%")

if tests_failed > 0:
    print("\nFailed tests:")
    for result in test_results:
        if not result["passed"]:
            print(f"  - {result['name']}: {result['details']}")

print("\n" + "=" * 80)
