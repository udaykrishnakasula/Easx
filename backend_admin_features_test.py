"""
Comprehensive backend tests for 3 new admin features:
1. Account Suspension (suspend/unsuspend + enforcement)
2. Maintenance Mode + feature switches
3. Audit logs (read) + logging on mutations

Admin credentials: admin@easyx.com / Admin@Easyx2026
Base URL from frontend/.env REACT_APP_BACKEND_URL (all routes prefixed with /api)
"""
import requests
import uuid
import time
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://easyx-loader.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test results tracking
test_results = []


def log_test(feature, scenario, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({
        "feature": feature,
        "scenario": scenario,
        "passed": passed,
        "details": details
    })
    print(f"{status} - {feature} - {scenario}")
    if details:
        print(f"  Details: {details}")


def admin_login():
    """Login as admin and return token"""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def register_test_user():
    """Register a fresh test user and return (user_id, email, password, token)"""
    email = f"testuser_{uuid.uuid4().hex[:8]}@easyx.com"
    # Generate numeric phone number only
    import random
    phone = f"+91{random.randint(1000000000, 9999999999)}"
    password = "TestPass123!"
    
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Test User",
        "email": email,
        "phone": phone,
        "password": password
    })
    
    if resp.status_code not in [200, 201]:
        raise Exception(f"User registration failed: {resp.status_code} {resp.text}")
    
    data = resp.json()
    return data["user"]["id"], email, password, data["access_token"]


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(test_results)
    passed = sum(1 for t in test_results if t["passed"])
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    if total > 0:
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
    else:
        print("Success Rate: N/A\n")
    
    if failed > 0:
        print("FAILED TESTS:")
        for t in test_results:
            if not t["passed"]:
                print(f"  ❌ {t['feature']} - {t['scenario']}")
                if t["details"]:
                    print(f"     {t['details']}")


# =============================================================================
# FEATURE 1: ACCOUNT SUSPENSION
# =============================================================================

def test_account_suspension():
    """Test complete account suspension feature"""
    print("\n" + "="*80)
    print("FEATURE 1: ACCOUNT SUSPENSION")
    print("="*80 + "\n")
    
    admin_token = admin_login()
    
    # Register a fresh test user
    user_id, user_email, user_password, user_token = register_test_user()
    log_test("Account Suspension", "Register fresh test user", True, 
             f"user_id={user_id}, email={user_email}")
    
    # Verify user appears in admin users list with wallet field
    resp = requests.get(
        f"{BASE_URL}/admin/users?limit=100",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        users = resp.json().get("users", [])
        user_found = any(u["id"] == user_id for u in users)
        has_wallet = any(u["id"] == user_id and "wallet" in u for u in users)
        log_test("Account Suspension", "User appears in admin list with wallet", 
                 user_found and has_wallet,
                 f"user_found={user_found}, has_wallet={has_wallet}")
    else:
        log_test("Account Suspension", "User appears in admin list with wallet", False,
                 f"Status {resp.status_code}: {resp.text}")
    
    # Suspend the user
    resp = requests.post(
        f"{BASE_URL}/admin/users/{user_id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "testing suspension"}
    )
    if resp.status_code == 200:
        data = resp.json()
        is_suspended = data.get("status") == "suspended"
        log_test("Account Suspension", "Suspend user returns status='suspended'", 
                 is_suspended,
                 f"status={data.get('status')}")
    else:
        log_test("Account Suspension", "Suspend user returns status='suspended'", False,
                 f"Status {resp.status_code}: {resp.text}")
    
    # Verify suspended user CANNOT login
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": user_email,
        "password": user_password
    })
    login_blocked = resp.status_code == 403
    log_test("Account Suspension", "Suspended user cannot login (403)", 
             login_blocked,
             f"Status {resp.status_code}")
    
    # Verify suspended user's existing Bearer token is rejected on protected route
    resp = requests.get(
        f"{BASE_URL}/wallet",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    token_blocked = resp.status_code == 403
    log_test("Account Suspension", "Suspended user's old token rejected on protected route (403)", 
             token_blocked,
             f"Status {resp.status_code}")
    
    # Try to suspend again (should fail with 400 - already suspended)
    resp = requests.post(
        f"{BASE_URL}/admin/users/{user_id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "testing double suspension"}
    )
    double_suspend_blocked = resp.status_code == 400
    log_test("Account Suspension", "Double suspend returns 400 (already suspended)", 
             double_suspend_blocked,
             f"Status {resp.status_code}")
    
    # Try to suspend admin user (should fail with 400)
    # First get admin user ID
    resp = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        admin_id = resp.json()["id"]
        resp = requests.post(
            f"{BASE_URL}/admin/users/{admin_id}/suspend",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "testing admin suspension"}
        )
        admin_suspend_blocked = resp.status_code == 400
        log_test("Account Suspension", "Cannot suspend admin user (400)", 
                 admin_suspend_blocked,
                 f"Status {resp.status_code}")
    else:
        log_test("Account Suspension", "Cannot suspend admin user (400)", False,
                 "Could not get admin user ID")
    
    # Get user's investment count before unsuspend
    resp = requests.get(
        f"{BASE_URL}/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    investment_count_before = 0
    if resp.status_code == 200:
        investment_count_before = resp.json().get("investment_count", 0)
    
    # Unsuspend the user
    resp = requests.post(
        f"{BASE_URL}/admin/users/{user_id}/unsuspend",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        data = resp.json()
        is_active = data.get("status") == "active"
        log_test("Account Suspension", "Unsuspend user returns status='active'", 
                 is_active,
                 f"status={data.get('status')}")
    else:
        log_test("Account Suspension", "Unsuspend user returns status='active'", False,
                 f"Status {resp.status_code}: {resp.text}")
    
    # Verify user can login again after unsuspend
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": user_email,
        "password": user_password
    })
    login_works = resp.status_code == 200
    new_token = resp.json().get("access_token") if login_works else None
    log_test("Account Suspension", "Unsuspended user can login (200)", 
             login_works,
             f"Status {resp.status_code}")
    
    # Verify user can access protected route after unsuspend
    if new_token:
        resp = requests.get(
            f"{BASE_URL}/wallet",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        access_works = resp.status_code == 200
        log_test("Account Suspension", "Unsuspended user can access protected route (200)", 
                 access_works,
                 f"Status {resp.status_code}")
    else:
        log_test("Account Suspension", "Unsuspended user can access protected route (200)", 
                 False, "No token obtained")
    
    # Verify investment count unchanged
    resp = requests.get(
        f"{BASE_URL}/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        investment_count_after = resp.json().get("investment_count", 0)
        investments_unchanged = investment_count_before == investment_count_after
        log_test("Account Suspension", "Suspension did not alter user's investments", 
                 investments_unchanged,
                 f"before={investment_count_before}, after={investment_count_after}")
    else:
        log_test("Account Suspension", "Suspension did not alter user's investments", False,
                 f"Could not verify: Status {resp.status_code}")


# =============================================================================
# FEATURE 2: MAINTENANCE MODE + FEATURE SWITCHES
# =============================================================================

def test_maintenance_mode():
    """Test maintenance mode and feature switches"""
    print("\n" + "="*80)
    print("FEATURE 2: MAINTENANCE MODE + FEATURE SWITCHES")
    print("="*80 + "\n")
    
    admin_token = admin_login()
    
    # Test public GET /api/maintenance (NO auth)
    resp = requests.get(f"{BASE_URL}/maintenance")
    if resp.status_code == 200:
        data = resp.json()
        has_required_fields = all(k in data for k in ["is_enabled", "message", "features"])
        has_feature_switches = all(k in data.get("features", {}) 
                                   for k in ["registration", "deposits", "investments", "withdrawals"])
        log_test("Maintenance Mode", "Public GET /api/maintenance returns required fields", 
                 has_required_fields and has_feature_switches,
                 f"is_enabled={data.get('is_enabled')}, features={list(data.get('features', {}).keys())}")
    else:
        log_test("Maintenance Mode", "Public GET /api/maintenance returns required fields", False,
                 f"Status {resp.status_code}: {resp.text}")
    
    # Test admin GET /api/admin/maintenance
    resp = requests.get(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    admin_get_works = resp.status_code == 200
    log_test("Maintenance Mode", "Admin GET /api/admin/maintenance returns full doc", 
             admin_get_works,
             f"Status {resp.status_code}")
    
    # Enable full maintenance mode
    resp = requests.put(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_enabled": True, "message": "Down for maintenance"}
    )
    if resp.status_code == 200:
        data = resp.json()
        maintenance_enabled = data.get("is_enabled") == True
        log_test("Maintenance Mode", "Enable maintenance mode (is_enabled=true)", 
                 maintenance_enabled,
                 f"is_enabled={data.get('is_enabled')}")
    else:
        log_test("Maintenance Mode", "Enable maintenance mode (is_enabled=true)", False,
                 f"Status {resp.status_code}: {resp.text}")
    
    # Verify public endpoint shows maintenance enabled
    resp = requests.get(f"{BASE_URL}/maintenance")
    if resp.status_code == 200:
        is_enabled = resp.json().get("is_enabled") == True
        log_test("Maintenance Mode", "Public endpoint shows is_enabled=true", 
                 is_enabled,
                 f"is_enabled={resp.json().get('is_enabled')}")
    else:
        log_test("Maintenance Mode", "Public endpoint shows is_enabled=true", False,
                 f"Status {resp.status_code}")
    
    # Try to register (should fail with 503)
    import random
    test_email = f"maintenancetest_{uuid.uuid4().hex[:8]}@easyx.com"
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Maintenance Test",
        "email": test_email,
        "phone": f"+91{random.randint(1000000000, 9999999999)}",
        "password": "TestPass123!"
    })
    register_blocked = resp.status_code == 503
    log_test("Maintenance Mode", "Register blocked during maintenance (503)", 
             register_blocked,
             f"Status {resp.status_code}")
    
    # Create a test user with funds to test invest/deposit blocking
    # First disable maintenance temporarily
    requests.put(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_enabled": False}
    )
    
    user_id, user_email, user_password, user_token = register_test_user()
    
    # Fund the user
    requests.post(
        f"{BASE_URL}/admin/wallet/adjust",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": user_id,
            "amount": "2000",
            "direction": "credit",
            "note": "Test funding"
        }
    )
    
    # Re-enable maintenance
    requests.put(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_enabled": True, "message": "Down for maintenance"}
    )
    
    # Try to create investment (should fail with 503)
    resp = requests.post(
        f"{BASE_URL}/investments",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "plan_key": "silver",
            "idempotency_key": f"maint_test_{uuid.uuid4().hex[:8]}"
        }
    )
    invest_blocked = resp.status_code == 503
    log_test("Maintenance Mode", "Investment blocked during maintenance (503)", 
             invest_blocked,
             f"Status {resp.status_code}")
    
    # Try to create deposit (should fail with 503)
    resp = requests.post(
        f"{BASE_URL}/deposits",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "network": "TRC20",
            "amount": "500",
            "tx_hash": f"MAINT{uuid.uuid4().hex[:16].upper()}"
        }
    )
    deposit_blocked = resp.status_code == 503
    log_test("Maintenance Mode", "Deposit blocked during maintenance (503)", 
             deposit_blocked,
             f"Status {resp.status_code}")
    
    # Disable maintenance but disable investments_enabled only
    resp = requests.put(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "is_enabled": False,
            "investments_enabled": False
        }
    )
    if resp.status_code == 200:
        data = resp.json()
        settings_updated = (data.get("is_enabled") == False and 
                          data.get("investments_enabled") == False)
        log_test("Maintenance Mode", "Disable maintenance but disable investments_enabled", 
                 settings_updated,
                 f"is_enabled={data.get('is_enabled')}, investments_enabled={data.get('investments_enabled')}")
    else:
        log_test("Maintenance Mode", "Disable maintenance but disable investments_enabled", False,
                 f"Status {resp.status_code}")
    
    # Register should work now
    test_email2 = f"maintenancetest2_{uuid.uuid4().hex[:8]}@easyx.com"
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Maintenance Test 2",
        "email": test_email2,
        "phone": f"+91{random.randint(1000000000, 9999999999)}",
        "password": "TestPass123!"
    })
    register_works = resp.status_code in [200, 201]
    log_test("Maintenance Mode", "Register works when maintenance disabled (200/201)", 
             register_works,
             f"Status {resp.status_code}")
    
    # Deposit should work
    resp = requests.post(
        f"{BASE_URL}/deposits",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "network": "TRC20",
            "amount": "500",
            "tx_hash": f"WORK{uuid.uuid4().hex[:16].upper()}"
        }
    )
    deposit_works = resp.status_code in [200, 201]
    log_test("Maintenance Mode", "Deposit works when deposits_enabled=true (200/201)", 
             deposit_works,
             f"Status {resp.status_code}")
    
    # Investment should still be blocked (investments_enabled=false)
    resp = requests.post(
        f"{BASE_URL}/investments",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "plan_key": "silver",
            "idempotency_key": f"maint_test2_{uuid.uuid4().hex[:8]}"
        }
    )
    invest_still_blocked = resp.status_code == 503
    log_test("Maintenance Mode", "Investment blocked when investments_enabled=false (503)", 
             invest_still_blocked,
             f"Status {resp.status_code}")
    
    # Cleanup: restore all features to enabled
    resp = requests.put(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "is_enabled": False,
            "registration_enabled": True,
            "deposits_enabled": True,
            "investments_enabled": True,
            "withdrawals_enabled": True
        }
    )
    if resp.status_code == 200:
        data = resp.json()
        all_enabled = (data.get("is_enabled") == False and
                      data.get("registration_enabled") == True and
                      data.get("deposits_enabled") == True and
                      data.get("investments_enabled") == True and
                      data.get("withdrawals_enabled") == True)
        log_test("Maintenance Mode", "Cleanup: restore all features to enabled", 
                 all_enabled,
                 f"All features enabled: {all_enabled}")
    else:
        log_test("Maintenance Mode", "Cleanup: restore all features to enabled", False,
                 f"Status {resp.status_code}")


# =============================================================================
# FEATURE 3: AUDIT LOGS
# =============================================================================

def test_audit_logs():
    """Test audit logs feature"""
    print("\n" + "="*80)
    print("FEATURE 3: AUDIT LOGS")
    print("="*80 + "\n")
    
    admin_token = admin_login()
    
    # Perform a suspend action to generate audit log
    user_id, user_email, user_password, user_token = register_test_user()
    
    resp = requests.post(
        f"{BASE_URL}/admin/users/{user_id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "audit log test suspension"}
    )
    suspend_success = resp.status_code == 200
    log_test("Audit Logs", "Perform suspend action for audit log", 
             suspend_success,
             f"Status {resp.status_code}")
    
    # Perform an unsuspend action
    resp = requests.post(
        f"{BASE_URL}/admin/users/{user_id}/unsuspend",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    unsuspend_success = resp.status_code == 200
    log_test("Audit Logs", "Perform unsuspend action for audit log", 
             unsuspend_success,
             f"Status {resp.status_code}")
    
    # Perform a maintenance update
    resp = requests.put(
        f"{BASE_URL}/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"message": "Audit log test maintenance message"}
    )
    maintenance_update_success = resp.status_code == 200
    log_test("Audit Logs", "Perform maintenance update for audit log", 
             maintenance_update_success,
             f"Status {resp.status_code}")
    
    # Wait a moment for logs to be written
    time.sleep(0.5)
    
    # Get audit logs
    resp = requests.get(
        f"{BASE_URL}/admin/audit-logs?limit=50",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if resp.status_code == 200:
        logs = resp.json()
        
        # Check if it's a list
        is_list = isinstance(logs, list)
        log_test("Audit Logs", "GET /api/admin/audit-logs returns array", 
                 is_list,
                 f"Type: {type(logs)}")
        
        if is_list:
            # Check for required actions
            actions = [log.get("action") for log in logs]
            has_suspend = "user.suspend" in actions
            has_unsuspend = "user.unsuspend" in actions
            has_maintenance = "maintenance.update" in actions
            
            log_test("Audit Logs", "Audit logs contain 'user.suspend' action", 
                     has_suspend,
                     f"Found actions: {set(actions)}")
            
            log_test("Audit Logs", "Audit logs contain 'user.unsuspend' action", 
                     has_unsuspend,
                     f"Found actions: {set(actions)}")
            
            log_test("Audit Logs", "Audit logs contain 'maintenance.update' action", 
                     has_maintenance,
                     f"Found actions: {set(actions)}")
            
            # Check structure of first log entry
            if logs:
                first_log = logs[0]
                has_required_fields = all(k in first_log for k in 
                                         ["action", "actor_id", "entity_type", "entity_id", "created_at"])
                log_test("Audit Logs", "Audit log entries have required fields", 
                         has_required_fields,
                         f"Fields: {list(first_log.keys())}")
            else:
                log_test("Audit Logs", "Audit log entries have required fields", False,
                         "No logs returned")
    else:
        log_test("Audit Logs", "GET /api/admin/audit-logs returns array", False,
                 f"Status {resp.status_code}: {resp.text}")
    
    # Test auth: normal user should get 403
    resp = requests.get(
        f"{BASE_URL}/admin/audit-logs",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    user_blocked = resp.status_code == 403
    log_test("Audit Logs", "Normal user gets 403 on audit logs endpoint", 
             user_blocked,
             f"Status {resp.status_code}")
    
    # Test auth: no token should get 401
    resp = requests.get(f"{BASE_URL}/admin/audit-logs")
    no_auth_blocked = resp.status_code == 401
    log_test("Audit Logs", "No token gets 401 on audit logs endpoint", 
             no_auth_blocked,
             f"Status {resp.status_code}")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("EASYX BACKEND - ADMIN FEATURES TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print(f"Started: {datetime.now().isoformat()}")
    
    try:
        # Run all feature tests
        test_account_suspension()
        test_maintenance_mode()
        test_audit_logs()
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Print summary
        print_summary()
        
        print(f"\nCompleted: {datetime.now().isoformat()}")
        print("="*80)
