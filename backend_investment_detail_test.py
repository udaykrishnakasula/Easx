"""
Comprehensive test suite for GET /api/investments/{investment_id} endpoint.
Tests individual investment detail retrieval with all required fields including
profit_percentage and maturity_percentage.
"""
import time
import requests
import json

# Read base URL from frontend/.env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip() + '/api'
            break

print(f"🔗 Testing against: {BASE_URL}")
print("=" * 80)

# Test results tracking
passed = 0
failed = 0

def log_test(name, success, status_code=None, expected=None, detail=None):
    global passed, failed
    if success:
        passed += 1
        result = f"✅ PASS"
    else:
        failed += 1
        result = f"❌ FAIL"
    
    msg = f"{result} - {name}"
    if status_code is not None:
        msg += f" (status: {status_code}"
        if expected:
            msg += f", expected: {expected}"
        msg += ")"
    if detail:
        msg += f" - {detail}"
    
    print(msg)

# Test credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"
TEST_USER_EMAIL = "belltester@easyx.com"
TEST_USER_PASSWORD = "Test@1234"

admin_token = None
test_user_token = None
test_user_id = None
test_user2_token = None
test_user2_id = None

print("\n" + "=" * 80)
print("📋 SETUP: Login admin and test users")
print("=" * 80)

# Login admin
print("\n1️⃣  Logging in as admin...")
try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        admin_token = response.json()["access_token"]
        log_test("Admin login", True, 200)
    else:
        log_test("Admin login", False, response.status_code, 200, detail=response.text[:200])
        exit(1)
except Exception as e:
    log_test("Admin login", False, detail=f"Exception: {str(e)}")
    exit(1)

# Check if test user exists, if not register
print("\n2️⃣  Setting up test user...")
try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        test_user_token = data["access_token"]
        test_user_id = data["user"]["id"]
        log_test("Test user login", True, 200)
    elif response.status_code == 401:
        # Register test user
        timestamp = int(time.time() * 1000)
        reg_response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "name": "Bell Tester",
                "email": TEST_USER_EMAIL,
                "phone": f"+91{timestamp % 10000000000}",
                "password": TEST_USER_PASSWORD
            },
            timeout=10
        )
        if reg_response.status_code == 201:
            data = reg_response.json()
            test_user_token = data["access_token"]
            test_user_id = data["user"]["id"]
            log_test("Test user registration", True, 201)
        else:
            log_test("Test user registration", False, reg_response.status_code, 201, detail=reg_response.text[:200])
            exit(1)
    else:
        log_test("Test user setup", False, response.status_code, detail=response.text[:200])
        exit(1)
except Exception as e:
    log_test("Test user setup", False, detail=f"Exception: {str(e)}")
    exit(1)

print("\n" + "=" * 80)
print("📋 TEST 1: GET /api/investments/{id} returns 401 without auth")
print("=" * 80)

try:
    response = requests.get(
        f"{BASE_URL}/investments/some-id-123",
        timeout=10
    )
    if response.status_code == 401:
        log_test("GET /api/investments/{id} without auth returns 401", True, 401)
    else:
        log_test("GET /api/investments/{id} without auth returns 401", False, response.status_code, 401, detail=response.text[:200])
except Exception as e:
    log_test("GET /api/investments/{id} without auth", False, detail=f"Exception: {str(e)}")

print("\n" + "=" * 80)
print("📋 TEST 2: Fund user and buy investment, then GET detail with all fields")
print("=" * 80)

# Fund test user with 500 USDT
print("\n1️⃣  Funding test user with 500 USDT...")
try:
    response = requests.post(
        f"{BASE_URL}/admin/wallet/adjust",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": test_user_id,
            "amount": "500",
            "direction": "credit",
            "note": "Test funding for investment detail test"
        },
        timeout=10
    )
    if response.status_code == 200:
        log_test("Admin credit 500 to test user", True, 200)
    else:
        log_test("Admin credit 500 to test user", False, response.status_code, 200, detail=response.text[:200])
except Exception as e:
    log_test("Admin credit", False, detail=f"Exception: {str(e)}")

# Buy silver investment
print("\n2️⃣  Buying silver investment...")
investment_id = None
idempotency_key = f"test-detail-{int(time.time() * 1000)}"
try:
    response = requests.post(
        f"{BASE_URL}/investments",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"plan_key": "silver", "idempotency_key": idempotency_key},
        timeout=10
    )
    if response.status_code == 201:
        data = response.json()
        investment_id = data.get("id")
        log_test("Buy silver investment", True, 201, detail=f"Investment ID: {investment_id}")
    else:
        log_test("Buy silver investment", False, response.status_code, 201, detail=response.text[:200])
except Exception as e:
    log_test("Buy silver investment", False, detail=f"Exception: {str(e)}")

# GET investment detail
print("\n3️⃣  Getting investment detail...")
if investment_id:
    try:
        response = requests.get(
            f"{BASE_URL}/investments/{investment_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            log_test("GET /api/investments/{id} returns 200", True, 200)
            
            # Check all required fields
            required_fields = [
                "id", "plan_key", "plan_name", "principal", "profit_amount", 
                "maturity_amount", "profit_percentage", "maturity_percentage",
                "lock_days", "status", "start_at", "maturity_at", "matured_at",
                "remaining_days", "created_at"
            ]
            
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                log_test("All required fields present", False, 200, detail=f"Missing: {missing_fields}")
            else:
                log_test("All required fields present", True, 200)
            
            # Verify field values
            id_correct = data.get("id") == investment_id
            log_test("Field 'id' matches investment ID", id_correct, 200, detail=f"Got: {data.get('id')}")
            
            plan_key_correct = data.get("plan_key") == "silver"
            log_test("Field 'plan_key' is 'silver'", plan_key_correct, 200, detail=f"Got: {data.get('plan_key')}")
            
            plan_name_present = data.get("plan_name") is not None
            log_test("Field 'plan_name' is present", plan_name_present, 200, detail=f"Got: {data.get('plan_name')}")
            
            principal_correct = data.get("principal") == "300.00"
            log_test("Field 'principal' is '300.00'", principal_correct, 200, detail=f"Got: {data.get('principal')}")
            
            # Check profit_percentage and maturity_percentage are non-null decimal strings
            profit_pct = data.get("profit_percentage")
            profit_pct_valid = (
                profit_pct is not None and 
                isinstance(profit_pct, str) and 
                "." in profit_pct and
                len(profit_pct.split(".")[-1]) == 2
            )
            log_test("Field 'profit_percentage' is non-null decimal string", profit_pct_valid, 200, 
                    detail=f"Got: {profit_pct} (expected format: '60.00')")
            
            maturity_pct = data.get("maturity_percentage")
            maturity_pct_valid = (
                maturity_pct is not None and 
                isinstance(maturity_pct, str) and 
                "." in maturity_pct and
                len(maturity_pct.split(".")[-1]) == 2
            )
            log_test("Field 'maturity_percentage' is non-null decimal string", maturity_pct_valid, 200,
                    detail=f"Got: {maturity_pct} (expected format: '160.00')")
            
            # Verify profit_amount and maturity_amount
            profit_amount_present = data.get("profit_amount") is not None
            log_test("Field 'profit_amount' is present", profit_amount_present, 200, detail=f"Got: {data.get('profit_amount')}")
            
            maturity_amount_present = data.get("maturity_amount") is not None
            log_test("Field 'maturity_amount' is present", maturity_amount_present, 200, detail=f"Got: {data.get('maturity_amount')}")
            
            lock_days_present = data.get("lock_days") is not None
            log_test("Field 'lock_days' is present", lock_days_present, 200, detail=f"Got: {data.get('lock_days')}")
            
            status_correct = data.get("status") == "active"
            log_test("Field 'status' is 'active'", status_correct, 200, detail=f"Got: {data.get('status')}")
            
            start_at_present = data.get("start_at") is not None
            log_test("Field 'start_at' is present", start_at_present, 200, detail=f"Got: {data.get('start_at')}")
            
            maturity_at_present = data.get("maturity_at") is not None
            log_test("Field 'maturity_at' is present", maturity_at_present, 200, detail=f"Got: {data.get('maturity_at')}")
            
            # matured_at should be None for active investment
            matured_at_null = data.get("matured_at") is None
            log_test("Field 'matured_at' is null for active investment", matured_at_null, 200, detail=f"Got: {data.get('matured_at')}")
            
            remaining_days_valid = isinstance(data.get("remaining_days"), int) and data.get("remaining_days") > 0
            log_test("Field 'remaining_days' is positive integer", remaining_days_valid, 200, detail=f"Got: {data.get('remaining_days')}")
            
            created_at_present = data.get("created_at") is not None
            log_test("Field 'created_at' is present", created_at_present, 200, detail=f"Got: {data.get('created_at')}")
            
        else:
            log_test("GET /api/investments/{id}", False, response.status_code, 200, detail=response.text[:200])
    except Exception as e:
        log_test("GET /api/investments/{id}", False, detail=f"Exception: {str(e)}")
else:
    log_test("GET /api/investments/{id} - skipped", False, detail="No investment ID available")

print("\n" + "=" * 80)
print("📋 TEST 3: GET /api/investments/{non-existent-id} returns 404")
print("=" * 80)

try:
    response = requests.get(
        f"{BASE_URL}/investments/non-existent-id-12345",
        headers={"Authorization": f"Bearer {test_user_token}"},
        timeout=10
    )
    if response.status_code == 404:
        log_test("GET /api/investments/{non-existent-id} returns 404", True, 404)
    else:
        log_test("GET /api/investments/{non-existent-id} returns 404", False, response.status_code, 404, detail=response.text[:200])
except Exception as e:
    log_test("GET /api/investments/{non-existent-id}", False, detail=f"Exception: {str(e)}")

print("\n" + "=" * 80)
print("📋 TEST 4: SECURITY/ISOLATION - User B cannot access User A's investment")
print("=" * 80)

# Register second user (User B)
print("\n1️⃣  Registering User B...")
timestamp = int(time.time() * 1000)
userB_email = f"userB{timestamp}@easyx.com"
userB_phone = f"+91{timestamp % 10000000000}"
try:
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "name": "User B",
            "email": userB_email,
            "phone": userB_phone,
            "password": "UserB@1234"
        },
        timeout=10
    )
    if response.status_code == 201:
        data = response.json()
        test_user2_token = data["access_token"]
        test_user2_id = data["user"]["id"]
        log_test("User B registration", True, 201)
    else:
        log_test("User B registration", False, response.status_code, 201, detail=response.text[:200])
except Exception as e:
    log_test("User B registration", False, detail=f"Exception: {str(e)}")

# User B tries to access User A's investment
print("\n2️⃣  User B attempting to access User A's investment...")
if test_user2_token and investment_id:
    try:
        response = requests.get(
            f"{BASE_URL}/investments/{investment_id}",
            headers={"Authorization": f"Bearer {test_user2_token}"},
            timeout=10
        )
        if response.status_code == 404:
            log_test("User B accessing User A's investment returns 404 (security OK)", True, 404)
        else:
            log_test("User B accessing User A's investment returns 404", False, response.status_code, 404, 
                    detail=f"SECURITY ISSUE: User B can access User A's data! Response: {response.text[:200]}")
    except Exception as e:
        log_test("User B accessing User A's investment", False, detail=f"Exception: {str(e)}")
else:
    log_test("User B security test - skipped", False, detail="User B token or investment ID not available")

print("\n" + "=" * 80)
print("📋 TEST 5: INDEPENDENCE - Same user buys same plan 3 times, gets 3 distinct investments")
print("=" * 80)

# Fund User A with more money
print("\n1️⃣  Funding User A with additional 1000 USDT...")
try:
    response = requests.post(
        f"{BASE_URL}/admin/wallet/adjust",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": test_user_id,
            "amount": "1000",
            "direction": "credit",
            "note": "Additional funding for independence test"
        },
        timeout=10
    )
    if response.status_code == 200:
        log_test("Admin credit 1000 to User A", True, 200)
    else:
        log_test("Admin credit 1000 to User A", False, response.status_code, 200, detail=response.text[:200])
except Exception as e:
    log_test("Admin credit additional funds", False, detail=f"Exception: {str(e)}")

# Buy silver 3 times with different idempotency keys
investment_ids = []
print("\n2️⃣  Buying silver plan 3 times with different idempotency keys...")
for i in range(3):
    idempotency_key = f"test-independence-{int(time.time() * 1000)}-{i}"
    try:
        response = requests.post(
            f"{BASE_URL}/investments",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"plan_key": "silver", "idempotency_key": idempotency_key},
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            inv_id = data.get("id")
            investment_ids.append(inv_id)
            log_test(f"Buy silver investment #{i+1}", True, 201, detail=f"ID: {inv_id}")
        else:
            log_test(f"Buy silver investment #{i+1}", False, response.status_code, 201, detail=response.text[:200])
    except Exception as e:
        log_test(f"Buy silver investment #{i+1}", False, detail=f"Exception: {str(e)}")
    time.sleep(0.1)  # Small delay to ensure different timestamps

# Verify we have 3 distinct investment IDs
print("\n3️⃣  Verifying 3 distinct investment IDs...")
if len(investment_ids) == 3:
    unique_ids = len(set(investment_ids)) == 3
    log_test("3 distinct investment IDs created", unique_ids, detail=f"IDs: {investment_ids}")
else:
    log_test("3 distinct investment IDs created", False, detail=f"Only {len(investment_ids)} investments created")

# GET each investment individually and verify they are distinct
print("\n4️⃣  Getting each investment detail and verifying independence...")
investment_details = []
for i, inv_id in enumerate(investment_ids):
    try:
        response = requests.get(
            f"{BASE_URL}/investments/{inv_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            investment_details.append(data)
            log_test(f"GET investment #{i+1} detail", True, 200, detail=f"ID: {data.get('id')}")
        else:
            log_test(f"GET investment #{i+1} detail", False, response.status_code, 200, detail=response.text[:200])
    except Exception as e:
        log_test(f"GET investment #{i+1} detail", False, detail=f"Exception: {str(e)}")

# Verify each has unique ID and maturity_at
print("\n5️⃣  Verifying each investment has unique ID and maturity_at...")
if len(investment_details) == 3:
    ids = [inv.get("id") for inv in investment_details]
    maturity_dates = [inv.get("maturity_at") for inv in investment_details]
    
    unique_ids = len(set(ids)) == 3
    log_test("All 3 investments have unique IDs", unique_ids, detail=f"IDs: {ids}")
    
    # Maturity dates should be distinct (different timestamps)
    unique_maturity = len(set(maturity_dates)) == 3
    log_test("All 3 investments have unique maturity_at dates", unique_maturity, 
            detail=f"Maturity dates: {maturity_dates}")
    
    # Verify each has its own principal
    principals = [inv.get("principal") for inv in investment_details]
    all_300 = all(p == "300.00" for p in principals)
    log_test("All 3 investments have principal '300.00'", all_300, detail=f"Principals: {principals}")
    
else:
    log_test("Verify 3 distinct investments - skipped", False, detail=f"Only {len(investment_details)} details retrieved")

# Verify GET /api/investments (list) contains all 3
print("\n6️⃣  Verifying GET /api/investments (list) contains all 3...")
try:
    response = requests.get(
        f"{BASE_URL}/investments",
        headers={"Authorization": f"Bearer {test_user_token}"},
        timeout=10
    )
    if response.status_code == 200:
        investments_list = response.json()
        list_ids = [inv.get("id") for inv in investments_list]
        
        # Check if all 3 new investment IDs are in the list
        all_present = all(inv_id in list_ids for inv_id in investment_ids)
        log_test("GET /api/investments (list) contains all 3 new investments", all_present, 200,
                detail=f"List has {len(investments_list)} investments, looking for IDs: {investment_ids}")
    else:
        log_test("GET /api/investments (list)", False, response.status_code, 200, detail=response.text[:200])
except Exception as e:
    log_test("GET /api/investments (list)", False, detail=f"Exception: {str(e)}")

print("\n" + "=" * 80)
print("📋 TEST 6: REGRESSION - Verify existing endpoints still work")
print("=" * 80)

# Test GET /api/investments (list)
print("\n1️⃣  Testing GET /api/investments (list)...")
try:
    response = requests.get(
        f"{BASE_URL}/investments",
        headers={"Authorization": f"Bearer {test_user_token}"},
        timeout=10
    )
    if response.status_code == 200:
        log_test("GET /api/investments (list) still works", True, 200)
    else:
        log_test("GET /api/investments (list) still works", False, response.status_code, 200, detail=response.text[:200])
except Exception as e:
    log_test("GET /api/investments (list)", False, detail=f"Exception: {str(e)}")

# Test POST /api/investments
print("\n2️⃣  Testing POST /api/investments...")
try:
    response = requests.post(
        f"{BASE_URL}/investments",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"plan_key": "silver", "idempotency_key": f"regression-{int(time.time() * 1000)}"},
        timeout=10
    )
    if response.status_code in [201, 402]:  # 201 if funded, 402 if insufficient balance
        log_test("POST /api/investments still works", True, response.status_code)
    else:
        log_test("POST /api/investments still works", False, response.status_code, detail=response.text[:200])
except Exception as e:
    log_test("POST /api/investments", False, detail=f"Exception: {str(e)}")

# Test GET /api/rewards/feed
print("\n3️⃣  Testing GET /api/rewards/feed...")
try:
    response = requests.get(
        f"{BASE_URL}/rewards/feed",
        headers={"Authorization": f"Bearer {test_user_token}"},
        timeout=10
    )
    if response.status_code == 200:
        log_test("GET /api/rewards/feed still works", True, 200)
    else:
        log_test("GET /api/rewards/feed still works", False, response.status_code, 200, detail=response.text[:200])
except Exception as e:
    log_test("GET /api/rewards/feed", False, detail=f"Exception: {str(e)}")

# Test notification triggers - check if investment_purchased notification was created
print("\n4️⃣  Testing notification trigger (investment_purchased)...")
try:
    response = requests.get(
        f"{BASE_URL}/notifications",
        headers={"Authorization": f"Bearer {test_user_token}"},
        timeout=10
    )
    if response.status_code == 200:
        notifications = response.json()
        investment_notifs = [n for n in notifications if n.get("type") == "investment_purchased"]
        if len(investment_notifs) > 0:
            log_test("Notification trigger 'investment_purchased' still works", True, 200,
                    detail=f"Found {len(investment_notifs)} investment_purchased notifications")
        else:
            log_test("Notification trigger 'investment_purchased' still works", False, 200,
                    detail="No investment_purchased notifications found")
    else:
        log_test("GET /api/notifications", False, response.status_code, 200, detail=response.text[:200])
except Exception as e:
    log_test("Notification trigger check", False, detail=f"Exception: {str(e)}")

print("\n" + "=" * 80)
print("📊 TEST SUMMARY")
print("=" * 80)
print(f"✅ PASSED: {passed}")
print(f"❌ FAILED: {failed}")
print(f"📈 SUCCESS RATE: {(passed / (passed + failed) * 100):.1f}%")
print("=" * 80)

if failed == 0:
    print("\n🎉 ALL TESTS PASSED!")
else:
    print(f"\n⚠️  {failed} TEST(S) FAILED - Review details above")
