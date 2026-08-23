#!/usr/bin/env python3
"""
Comprehensive test suite for in-app notification triggers + read_at exposure.

Tests:
1. New notification triggers (deposit_submitted, investment_purchased, kyc_submitted, withdrawal_submitted)
2. read_at field exposure in GET /api/notifications
3. GET /api/notifications/unread-count increments
4. POST /api/notifications/{id}/read sets is_read=true AND read_at to non-null timestamp
5. POST /api/notifications/read-all marks all read
6. SECURITY: users can only see their own notifications
7. IDEMPOTENCY: no duplicate notifications
8. REGRESSION: existing triggers still fire
9. GET /api/rewards/feed still works
"""
import requests
import time
import io
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://e30f9440-c6d8-475c-bcaa-ce8359e74259.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"
EXISTING_USER_EMAIL = "belltester@easyx.com"
EXISTING_USER_PASSWORD = "Test@1234"

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


def get_unread_count(token):
    """Get unread notification count."""
    resp = requests.get(f"{BASE_URL}/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()["count"]
    raise Exception(f"Get unread count failed: {resp.status_code} {resp.text}")


def mark_notification_read(token, notif_id):
    """Mark a single notification as read."""
    resp = requests.post(f"{BASE_URL}/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Mark read failed: {resp.status_code} {resp.text}")


def mark_all_read(token):
    """Mark all notifications as read."""
    resp = requests.post(f"{BASE_URL}/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Mark all read failed: {resp.status_code} {resp.text}")


def admin_fund_user(admin_token, user_id, amount):
    """Admin credits user wallet."""
    resp = requests.post(f"{BASE_URL}/admin/wallet/adjust", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"user_id": user_id, "direction": "credit", "amount": str(amount), "note": "test funding"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin fund failed: {resp.status_code} {resp.text}")


def admin_approve_kyc(admin_token, record_id):
    """Admin approves KYC."""
    resp = requests.post(f"{BASE_URL}/admin/kyc/{record_id}/approve", 
                        headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin approve KYC failed: {resp.status_code} {resp.text}")


def admin_approve_deposit(admin_token, deposit_id):
    """Admin approves deposit."""
    resp = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin approve deposit failed: {resp.status_code} {resp.text}")


def admin_reject_deposit(admin_token, deposit_id, note):
    """Admin rejects deposit."""
    resp = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/reject",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"note": note})
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Admin reject deposit failed: {resp.status_code} {resp.text}")


def create_png_bytes():
    """Create a minimal valid PNG file (1x1 red pixel)."""
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D,
        0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])


print("=" * 80)
print("NOTIFICATION TRIGGERS + read_at EXPOSURE TEST SUITE")
print("=" * 80)

# ============================================================================
# PART 1: NEW NOTIFICATION TRIGGERS
# ============================================================================
print("\n[PART 1] Testing NEW notification triggers")

# Test 1: deposit_submitted trigger
print("\n--- Test 1: deposit_submitted trigger ---")
try:
    timestamp = int(time.time())
    user1_token, user1_id = register_user(
        f"Deposit Tester {timestamp}",
        f"deptest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981230{timestamp % 10000:04d}"
    )
    
    # Get initial notification count
    initial_count = get_unread_count(user1_token)
    
    # Create deposit
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {user1_token}"},
                        json={"network": "TRC20", "amount": "500", "tx_hash": f"0xdeposittest{timestamp}"})
    
    if resp.status_code == 201:
        deposit_id = resp.json()["id"]
        
        # Wait a moment for notification to be created
        time.sleep(0.5)
        
        # Check notifications
        notifs = get_notifications(user1_token)
        deposit_notifs = [n for n in notifs if n["type"] == "deposit_submitted"]
        
        if len(deposit_notifs) == 1:
            notif = deposit_notifs[0]
            if notif["title"] == "Deposit submitted" and "500" in notif["body"] and "TRC20" in notif["body"]:
                new_count = get_unread_count(user1_token)
                if new_count == initial_count + 1:
                    log_test("deposit_submitted trigger", True, f"Created 1 notification, unread count increased from {initial_count} to {new_count}")
                else:
                    log_test("deposit_submitted trigger", False, f"Unread count mismatch: expected {initial_count + 1}, got {new_count}")
            else:
                log_test("deposit_submitted trigger", False, f"Incorrect title/body: {notif}")
        else:
            log_test("deposit_submitted trigger", False, f"Expected 1 deposit_submitted notification, got {len(deposit_notifs)}")
    else:
        log_test("deposit_submitted trigger", False, f"Deposit creation failed: {resp.status_code} {resp.text}")
except Exception as e:
    log_test("deposit_submitted trigger", False, str(e))

# Test 2: investment_purchased trigger
print("\n--- Test 2: investment_purchased trigger ---")
try:
    timestamp = int(time.time())
    user2_token, user2_id = register_user(
        f"Invest Tester {timestamp}",
        f"investtest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981231{timestamp % 10000:04d}"
    )
    
    # Admin funds user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user2_id, 1000)
    
    # Get initial notification count
    initial_count = get_unread_count(user2_token)
    
    # Buy investment
    resp = requests.post(f"{BASE_URL}/investments",
                        headers={"Authorization": f"Bearer {user2_token}"},
                        json={"plan_key": "silver", "idempotency_key": f"test-invest-{timestamp}"})
    
    if resp.status_code == 201:
        investment_id = resp.json()["id"]
        
        # Wait a moment for notification to be created
        time.sleep(0.5)
        
        # Check notifications
        notifs = get_notifications(user2_token)
        invest_notifs = [n for n in notifs if n["type"] == "investment_purchased"]
        
        if len(invest_notifs) == 1:
            notif = invest_notifs[0]
            if notif["title"] == "Investment purchased" and "Silver" in notif["body"]:
                new_count = get_unread_count(user2_token)
                if new_count == initial_count + 1:
                    log_test("investment_purchased trigger", True, f"Created 1 notification, unread count increased from {initial_count} to {new_count}")
                else:
                    log_test("investment_purchased trigger", False, f"Unread count mismatch: expected {initial_count + 1}, got {new_count}")
            else:
                log_test("investment_purchased trigger", False, f"Incorrect title/body: {notif}")
        else:
            log_test("investment_purchased trigger", False, f"Expected 1 investment_purchased notification, got {len(invest_notifs)}")
    else:
        log_test("investment_purchased trigger", False, f"Investment creation failed: {resp.status_code} {resp.text}")
except Exception as e:
    log_test("investment_purchased trigger", False, str(e))

# Test 3: kyc_submitted trigger
print("\n--- Test 3: kyc_submitted trigger ---")
try:
    timestamp = int(time.time())
    user3_token, user3_id = register_user(
        f"KYC Tester {timestamp}",
        f"kyctest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981232{timestamp % 10000:04d}"
    )
    
    # Get initial notification count
    initial_count = get_unread_count(user3_token)
    
    # Submit KYC
    png_bytes = create_png_bytes()
    files = {
        'id_document': ('id.png', io.BytesIO(png_bytes), 'image/png'),
        'selfie': ('selfie.png', io.BytesIO(png_bytes), 'image/png'),
    }
    data = {
        'id_type': 'aadhaar',
        'id_number': '123456789012'
    }
    resp = requests.post(f"{BASE_URL}/kyc/submit",
                        headers={"Authorization": f"Bearer {user3_token}"},
                        files=files,
                        data=data)
    
    if resp.status_code == 200:
        # Wait a moment for notification to be created
        time.sleep(0.5)
        
        # Check notifications
        notifs = get_notifications(user3_token)
        kyc_notifs = [n for n in notifs if n["type"] == "kyc_submitted"]
        
        if len(kyc_notifs) == 1:
            notif = kyc_notifs[0]
            if notif["title"] == "KYC submitted" and "pending review" in notif["body"]:
                new_count = get_unread_count(user3_token)
                if new_count == initial_count + 1:
                    log_test("kyc_submitted trigger", True, f"Created 1 notification, unread count increased from {initial_count} to {new_count}")
                else:
                    log_test("kyc_submitted trigger", False, f"Unread count mismatch: expected {initial_count + 1}, got {new_count}")
            else:
                log_test("kyc_submitted trigger", False, f"Incorrect title/body: {notif}")
        else:
            log_test("kyc_submitted trigger", False, f"Expected 1 kyc_submitted notification, got {len(kyc_notifs)}")
    else:
        log_test("kyc_submitted trigger", False, f"KYC submission failed: {resp.status_code} {resp.text}")
except Exception as e:
    log_test("kyc_submitted trigger", False, str(e))

# Test 4: withdrawal_submitted trigger
print("\n--- Test 4: withdrawal_submitted trigger ---")
try:
    timestamp = int(time.time())
    user4_token, user4_id = register_user(
        f"Withdraw Tester {timestamp}",
        f"wdtest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981233{timestamp % 10000:04d}"
    )
    
    # Admin funds user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user4_id, 500)
    
    # Submit KYC and get it approved
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
        # Get KYC record ID and approve it
        kyc_list = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
                               headers={"Authorization": f"Bearer {admin_token}"}).json()
        user4_kyc = [k for k in kyc_list if k["user_id"] == user4_id]
        if user4_kyc:
            admin_approve_kyc(admin_token, user4_kyc[0]["id"])
            
            # Get initial notification count (should have kyc_submitted + kyc_approved)
            initial_count = get_unread_count(user4_token)
            
            # Create withdrawal
            resp = requests.post(f"{BASE_URL}/withdrawals",
                                headers={"Authorization": f"Bearer {user4_token}"},
                                json={"network": "TRC20", "amount": "100", "to_address": "TXsomeaddress123456"})
            
            if resp.status_code == 201:
                withdrawal_id = resp.json()["id"]
                
                # Wait a moment for notification to be created
                time.sleep(0.5)
                
                # Check notifications
                notifs = get_notifications(user4_token)
                wd_notifs = [n for n in notifs if n["type"] == "withdrawal_submitted"]
                
                if len(wd_notifs) == 1:
                    notif = wd_notifs[0]
                    if notif["title"] == "Withdrawal submitted" and "100" in notif["body"] and "TRC20" in notif["body"]:
                        new_count = get_unread_count(user4_token)
                        if new_count == initial_count + 1:
                            log_test("withdrawal_submitted trigger", True, f"Created 1 notification, unread count increased from {initial_count} to {new_count}")
                        else:
                            log_test("withdrawal_submitted trigger", False, f"Unread count mismatch: expected {initial_count + 1}, got {new_count}")
                    else:
                        log_test("withdrawal_submitted trigger", False, f"Incorrect title/body: {notif}")
                else:
                    log_test("withdrawal_submitted trigger", False, f"Expected 1 withdrawal_submitted notification, got {len(wd_notifs)}")
            else:
                log_test("withdrawal_submitted trigger", False, f"Withdrawal creation failed: {resp.status_code} {resp.text}")
        else:
            log_test("withdrawal_submitted trigger", False, "Could not find user's KYC record")
    else:
        log_test("withdrawal_submitted trigger", False, f"KYC submission failed: {resp.status_code} {resp.text}")
except Exception as e:
    log_test("withdrawal_submitted trigger", False, str(e))

# ============================================================================
# PART 2: read_at FIELD EXPOSURE
# ============================================================================
print("\n[PART 2] Testing read_at field exposure")

# Test 5: read_at field present in GET /api/notifications
print("\n--- Test 5: read_at field in notifications ---")
try:
    # Use existing user with notifications
    existing_token = login(EXISTING_USER_EMAIL, EXISTING_USER_PASSWORD)
    notifs = get_notifications(existing_token)
    
    if len(notifs) > 0:
        # Check all notifications have read_at field
        all_have_read_at = all("read_at" in n for n in notifs)
        
        if all_have_read_at:
            # Check unread notifications have read_at=null
            unread = [n for n in notifs if not n["is_read"]]
            read = [n for n in notifs if n["is_read"]]
            
            unread_null = all(n["read_at"] is None for n in unread)
            read_non_null = all(n["read_at"] is not None for n in read)
            
            if unread_null and (len(read) == 0 or read_non_null):
                log_test("read_at field exposure", True, f"All {len(notifs)} notifications have read_at field (unread={len(unread)} with null, read={len(read)} with timestamp)")
            else:
                log_test("read_at field exposure", False, f"read_at values incorrect: unread_null={unread_null}, read_non_null={read_non_null}")
        else:
            log_test("read_at field exposure", False, "Not all notifications have read_at field")
    else:
        log_test("read_at field exposure", False, "No notifications found for existing user")
except Exception as e:
    log_test("read_at field exposure", False, str(e))

# ============================================================================
# PART 3: MARK READ FUNCTIONALITY
# ============================================================================
print("\n[PART 3] Testing mark read functionality")

# Test 6: POST /api/notifications/{id}/read sets is_read=true AND read_at
print("\n--- Test 6: Mark single notification as read ---")
try:
    # Create a fresh user with a notification
    timestamp = int(time.time())
    user5_token, user5_id = register_user(
        f"Read Test {timestamp}",
        f"readtest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981234{timestamp % 10000:04d}"
    )
    
    # Create a deposit to trigger notification
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {user5_token}"},
                        json={"network": "TRC20", "amount": "500", "tx_hash": f"0xreadtest{timestamp}"})
    
    if resp.status_code == 201:
        time.sleep(0.5)
        
        # Get the notification
        notifs = get_notifications(user5_token)
        if len(notifs) > 0:
            notif = notifs[0]
            
            # Verify it's unread with read_at=null
            if not notif["is_read"] and notif["read_at"] is None:
                # Mark it as read
                result = mark_notification_read(user5_token, notif["id"])
                
                if result["ok"]:
                    # Re-fetch to verify
                    time.sleep(0.3)
                    notifs_after = get_notifications(user5_token)
                    notif_after = [n for n in notifs_after if n["id"] == notif["id"]][0]
                    
                    if notif_after["is_read"] and notif_after["read_at"] is not None:
                        # Verify read_at is a valid timestamp
                        try:
                            datetime.fromisoformat(notif_after["read_at"].replace('Z', '+00:00'))
                            log_test("Mark notification read", True, f"is_read=true, read_at={notif_after['read_at']}")
                        except (ValueError, AttributeError):
                            log_test("Mark notification read", False, f"read_at is not a valid timestamp: {notif_after['read_at']}")
                    else:
                        log_test("Mark notification read", False, f"After marking read: is_read={notif_after['is_read']}, read_at={notif_after['read_at']}")
                else:
                    log_test("Mark notification read", False, "Mark read returned ok=false")
            else:
                log_test("Mark notification read", False, f"Notification already read or read_at not null: is_read={notif['is_read']}, read_at={notif['read_at']}")
        else:
            log_test("Mark notification read", False, "No notifications found")
    else:
        log_test("Mark notification read", False, f"Deposit creation failed: {resp.status_code}")
except Exception as e:
    log_test("Mark notification read", False, str(e))

# Test 7: POST /api/notifications/read-all marks all read
print("\n--- Test 7: Mark all notifications as read ---")
try:
    # Create a fresh user with multiple notifications
    timestamp = int(time.time())
    user6_token, user6_id = register_user(
        f"Read All Test {timestamp}",
        f"readalltest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981235{timestamp % 10000:04d}"
    )
    
    # Create 2 deposits to trigger 2 notifications
    resp1 = requests.post(f"{BASE_URL}/deposits",
                         headers={"Authorization": f"Bearer {user6_token}"},
                         json={"network": "TRC20", "amount": "500", "tx_hash": f"0xreadall1{timestamp}"})
    time.sleep(0.3)
    resp2 = requests.post(f"{BASE_URL}/deposits",
                         headers={"Authorization": f"Bearer {user6_token}"},
                         json={"network": "BEP20", "amount": "600", "tx_hash": f"0xreadall2{timestamp}"})
    
    if resp1.status_code == 201 and resp2.status_code == 201:
        time.sleep(0.5)
        
        # Get notifications
        notifs_before = get_notifications(user6_token)
        unread_before = [n for n in notifs_before if not n["is_read"]]
        
        if len(unread_before) >= 2:
            # Mark all as read
            result = mark_all_read(user6_token)
            
            if result["updated"] >= 2:
                # Re-fetch to verify
                time.sleep(0.3)
                notifs_after = get_notifications(user6_token)
                unread_after = [n for n in notifs_after if not n["is_read"]]
                all_have_read_at = all(n["read_at"] is not None for n in notifs_after)
                
                if len(unread_after) == 0 and all_have_read_at:
                    log_test("Mark all notifications read", True, f"Marked {result['updated']} notifications as read, all have read_at timestamp")
                else:
                    log_test("Mark all notifications read", False, f"After mark all: unread={len(unread_after)}, all_have_read_at={all_have_read_at}")
            else:
                log_test("Mark all notifications read", False, f"Expected updated>=2, got {result['updated']}")
        else:
            log_test("Mark all notifications read", False, f"Expected >=2 unread notifications, got {len(unread_before)}")
    else:
        log_test("Mark all notifications read", False, "Deposit creation failed")
except Exception as e:
    log_test("Mark all notifications read", False, str(e))

# ============================================================================
# PART 4: SECURITY - USER ISOLATION
# ============================================================================
print("\n[PART 4] Testing security - user isolation")

# Test 8: Users can only see their own notifications
print("\n--- Test 8: User notification isolation ---")
try:
    timestamp = int(time.time())
    userA_token, userA_id = register_user(
        f"User A {timestamp}",
        f"usera{timestamp}@easyx.com",
        "Test@1234",
        f"+91981236{timestamp % 10000:04d}"
    )
    userB_token, userB_id = register_user(
        f"User B {timestamp}",
        f"userb{timestamp}@easyx.com",
        "Test@1234",
        f"+91981237{timestamp % 10000:04d}"
    )
    
    # Create deposit for user A
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {userA_token}"},
                        json={"network": "TRC20", "amount": "500", "tx_hash": f"0xusera{timestamp}"})
    
    if resp.status_code == 201:
        time.sleep(0.5)
        
        # Get user A's notifications
        notifs_a = get_notifications(userA_token)
        
        # Get user B's notifications
        notifs_b = get_notifications(userB_token)
        
        # User A should have at least 1 notification
        # User B should have 0 notifications
        if len(notifs_a) >= 1 and len(notifs_b) == 0:
            # Try to mark user A's notification as read using user B's token
            notif_a_id = notifs_a[0]["id"]
            result = mark_notification_read(userB_token, notif_a_id)
            
            # Should return ok=false (user B cannot mark user A's notification)
            if not result["ok"]:
                # Verify user A's notification is still unread
                notifs_a_after = get_notifications(userA_token)
                notif_a_after = [n for n in notifs_a_after if n["id"] == notif_a_id][0]
                
                if not notif_a_after["is_read"]:
                    log_test("User notification isolation", True, "User B cannot mark user A's notification as read")
                else:
                    log_test("User notification isolation", False, "User A's notification was marked as read by user B")
            else:
                log_test("User notification isolation", False, "User B was able to mark user A's notification (ok=true)")
        else:
            log_test("User notification isolation", False, f"User A has {len(notifs_a)} notifications, User B has {len(notifs_b)} (expected A>=1, B=0)")
    else:
        log_test("User notification isolation", False, "Deposit creation failed")
except Exception as e:
    log_test("User notification isolation", False, str(e))

# ============================================================================
# PART 5: IDEMPOTENCY
# ============================================================================
print("\n[PART 5] Testing idempotency")

# Test 9: No duplicate notifications for same event
print("\n--- Test 9: Idempotency - no duplicate notifications ---")
try:
    timestamp = int(time.time())
    user7_token, user7_id = register_user(
        f"Idempotency Test {timestamp}",
        f"idemptest{timestamp}@easyx.com",
        "Test@1234",
        f"+91981238{timestamp % 10000:04d}"
    )
    
    # Admin funds user
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_fund_user(admin_token, user7_id, 1000)
    
    # Buy investment with idempotency key
    idempotency_key = f"test-idempotent-{timestamp}"
    
    # First purchase
    resp1 = requests.post(f"{BASE_URL}/investments",
                         headers={"Authorization": f"Bearer {user7_token}"},
                         json={"plan_key": "silver", "idempotency_key": idempotency_key})
    
    time.sleep(0.5)
    
    # Second purchase with SAME idempotency key (should return same investment, no new notification)
    resp2 = requests.post(f"{BASE_URL}/investments",
                         headers={"Authorization": f"Bearer {user7_token}"},
                         json={"plan_key": "silver", "idempotency_key": idempotency_key})
    
    if resp1.status_code == 201 and resp2.status_code == 201:
        # Both should return the same investment ID
        if resp1.json()["id"] == resp2.json()["id"]:
            time.sleep(0.5)
            
            # Check notifications - should have exactly 1 investment_purchased notification
            notifs = get_notifications(user7_token)
            invest_notifs = [n for n in notifs if n["type"] == "investment_purchased"]
            
            if len(invest_notifs) == 1:
                log_test("Idempotency - no duplicates", True, f"Replaying investment with same idempotency_key created only 1 notification")
            else:
                log_test("Idempotency - no duplicates", False, f"Expected 1 investment_purchased notification, got {len(invest_notifs)}")
        else:
            log_test("Idempotency - no duplicates", False, f"Different investment IDs returned: {resp1.json()['id']} vs {resp2.json()['id']}")
    else:
        log_test("Idempotency - no duplicates", False, f"Investment creation failed: resp1={resp1.status_code}, resp2={resp2.status_code}")
except Exception as e:
    log_test("Idempotency - no duplicates", False, str(e))

# ============================================================================
# PART 6: REGRESSION - EXISTING TRIGGERS
# ============================================================================
print("\n[PART 6] Testing regression - existing triggers still fire")

# Test 10: deposit_approved trigger
print("\n--- Test 10: deposit_approved trigger (regression) ---")
try:
    timestamp = int(time.time())
    user8_token, user8_id = register_user(
        f"Deposit Approve Test {timestamp}",
        f"depapprove{timestamp}@easyx.com",
        "Test@1234",
        f"+91981239{timestamp % 10000:04d}"
    )
    
    # Create deposit
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {user8_token}"},
                        json={"network": "TRC20", "amount": "500", "tx_hash": f"0xdepapprove{timestamp}"})
    
    if resp.status_code == 201:
        deposit_id = resp.json()["id"]
        time.sleep(0.5)
        
        # Admin approves deposit
        admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_approve_deposit(admin_token, deposit_id)
        
        time.sleep(0.5)
        
        # Check for deposit_approved notification
        notifs = get_notifications(user8_token)
        approved_notifs = [n for n in notifs if n["type"] == "deposit_approved"]
        
        if len(approved_notifs) == 1:
            notif = approved_notifs[0]
            if notif["title"] == "Deposit approved" and "500" in notif["body"]:
                log_test("deposit_approved trigger (regression)", True, "Notification created with correct title/body")
            else:
                log_test("deposit_approved trigger (regression)", False, f"Incorrect title/body: {notif}")
        else:
            log_test("deposit_approved trigger (regression)", False, f"Expected 1 deposit_approved notification, got {len(approved_notifs)}")
    else:
        log_test("deposit_approved trigger (regression)", False, f"Deposit creation failed: {resp.status_code}")
except Exception as e:
    log_test("deposit_approved trigger (regression)", False, str(e))

# Test 11: deposit_rejected trigger
print("\n--- Test 11: deposit_rejected trigger (regression) ---")
try:
    timestamp = int(time.time())
    user9_token, user9_id = register_user(
        f"Deposit Reject Test {timestamp}",
        f"depreject{timestamp}@easyx.com",
        "Test@1234",
        f"+91981240{timestamp % 10000:04d}"
    )
    
    # Create deposit
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {user9_token}"},
                        json={"network": "TRC20", "amount": "500", "tx_hash": f"0xdepreject{timestamp}"})
    
    if resp.status_code == 201:
        deposit_id = resp.json()["id"]
        time.sleep(0.5)
        
        # Admin rejects deposit
        admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_reject_deposit(admin_token, deposit_id, "Invalid transaction")
        
        time.sleep(0.5)
        
        # Check for deposit_rejected notification
        notifs = get_notifications(user9_token)
        rejected_notifs = [n for n in notifs if n["type"] == "deposit_rejected"]
        
        if len(rejected_notifs) == 1:
            notif = rejected_notifs[0]
            if notif["title"] == "Deposit rejected" and "500" in notif["body"] and "Invalid transaction" in notif["body"]:
                log_test("deposit_rejected trigger (regression)", True, "Notification created with correct title/body")
            else:
                log_test("deposit_rejected trigger (regression)", False, f"Incorrect title/body: {notif}")
        else:
            log_test("deposit_rejected trigger (regression)", False, f"Expected 1 deposit_rejected notification, got {len(rejected_notifs)}")
    else:
        log_test("deposit_rejected trigger (regression)", False, f"Deposit creation failed: {resp.status_code}")
except Exception as e:
    log_test("deposit_rejected trigger (regression)", False, str(e))

# Test 12: kyc_approved trigger
print("\n--- Test 12: kyc_approved trigger (regression) ---")
try:
    timestamp = int(time.time())
    user10_token, user10_id = register_user(
        f"KYC Approve Test {timestamp}",
        f"kycapprove{timestamp}@easyx.com",
        "Test@1234",
        f"+91981241{timestamp % 10000:04d}"
    )
    
    # Submit KYC
    png_bytes = create_png_bytes()
    files = {
        'id_document': ('id.png', io.BytesIO(png_bytes), 'image/png'),
        'selfie': ('selfie.png', io.BytesIO(png_bytes), 'image/png'),
    }
    data = {'id_type': 'aadhaar', 'id_number': '123456789012'}
    resp = requests.post(f"{BASE_URL}/kyc/submit",
                        headers={"Authorization": f"Bearer {user10_token}"},
                        files=files, data=data)
    
    if resp.status_code == 200:
        time.sleep(0.5)
        
        # Admin approves KYC
        admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
        kyc_list = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
                               headers={"Authorization": f"Bearer {admin_token}"}).json()
        user10_kyc = [k for k in kyc_list if k["user_id"] == user10_id]
        
        if user10_kyc:
            admin_approve_kyc(admin_token, user10_kyc[0]["id"])
            
            time.sleep(0.5)
            
            # Check for kyc_approved notification
            notifs = get_notifications(user10_token)
            approved_notifs = [n for n in notifs if n["type"] == "kyc_approved"]
            
            if len(approved_notifs) == 1:
                notif = approved_notifs[0]
                if notif["title"] == "KYC approved" and "approved" in notif["body"]:
                    log_test("kyc_approved trigger (regression)", True, "Notification created with correct title/body")
                else:
                    log_test("kyc_approved trigger (regression)", False, f"Incorrect title/body: {notif}")
            else:
                log_test("kyc_approved trigger (regression)", False, f"Expected 1 kyc_approved notification, got {len(approved_notifs)}")
        else:
            log_test("kyc_approved trigger (regression)", False, "Could not find user's KYC record")
    else:
        log_test("kyc_approved trigger (regression)", False, f"KYC submission failed: {resp.status_code}")
except Exception as e:
    log_test("kyc_approved trigger (regression)", False, str(e))

# ============================================================================
# PART 7: REWARDS FEED STILL WORKS
# ============================================================================
print("\n[PART 7] Testing GET /api/rewards/feed still works")

# Test 13: GET /api/rewards/feed
print("\n--- Test 13: GET /api/rewards/feed ---")
try:
    # Use existing user
    existing_token = login(EXISTING_USER_EMAIL, EXISTING_USER_PASSWORD)
    
    resp = requests.get(f"{BASE_URL}/rewards/feed", headers={"Authorization": f"Bearer {existing_token}"})
    
    if resp.status_code == 200:
        feed = resp.json()
        if isinstance(feed, list):
            log_test("GET /api/rewards/feed", True, f"Returns list with {len(feed)} items")
        else:
            log_test("GET /api/rewards/feed", False, f"Expected list, got {type(feed)}")
    else:
        log_test("GET /api/rewards/feed", False, f"Request failed: {resp.status_code} {resp.text}")
except Exception as e:
    log_test("GET /api/rewards/feed", False, str(e))

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
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
