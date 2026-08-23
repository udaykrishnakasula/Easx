"""
EasyX Investment Engine - Concurrency & Idempotency Re-test
After fix in invest_service.py (DuplicateKeyError handling with retry).

Focus: Test extreme race conditions with same idempotency_key to verify NO 500 errors.
"""
import time
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

# Read base URL from frontend/.env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip() + '/api'
            break

print(f"🔗 Testing against: {BASE_URL}")
print("=" * 80)

# Admin credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test results tracking
passed = 0
failed = 0
test_results = []

def log_test(name, success, detail=None):
    global passed, failed
    if success:
        passed += 1
        result = f"✅ PASS"
    else:
        failed += 1
        result = f"❌ FAIL"
    
    msg = f"{result} - {name}"
    if detail:
        msg += f"\n    {detail}"
    
    print(msg)
    test_results.append({"test": name, "passed": success, "detail": detail})

def get_admin_token():
    """Login as admin and return token."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    raise Exception(f"Admin login failed: {response.status_code} {response.text}")

def register_user(email, phone, password="TestPass123!", name="Test User"):
    """Register a new user and return token."""
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "name": name,
            "email": email,
            "phone": phone,
            "password": password
        },
        timeout=10
    )
    if response.status_code == 201:
        return response.json()["access_token"]
    raise Exception(f"Registration failed: {response.status_code} {response.text}")

def fund_user(admin_token, user_id, amount):
    """Fund user wallet via admin adjust."""
    response = requests.post(
        f"{BASE_URL}/admin/wallet/adjust",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": user_id,
            "amount": str(amount),
            "direction": "credit",
            "note": "Test funding"
        },
        timeout=10
    )
    if response.status_code != 200:
        raise Exception(f"Funding failed: {response.status_code} {response.text}")

def get_user_id(token):
    """Get user ID from /api/auth/me."""
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if response.status_code == 200:
        return response.json()["id"]
    raise Exception(f"Get user failed: {response.status_code} {response.text}")

def get_wallet(token):
    """Get wallet summary."""
    response = requests.get(
        f"{BASE_URL}/wallet",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Get wallet failed: {response.status_code} {response.text}")

def get_transactions(token):
    """Get wallet transactions."""
    response = requests.get(
        f"{BASE_URL}/transactions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Get transactions failed: {response.status_code} {response.text}")

def get_consistency(token):
    """Check wallet consistency."""
    response = requests.get(
        f"{BASE_URL}/wallet/consistency",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Get consistency failed: {response.status_code} {response.text}")

def buy_investment(token, plan_key, idempotency_key):
    """Buy investment plan. Returns (status_code, response_json)."""
    try:
        response = requests.post(
            f"{BASE_URL}/investments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "plan_key": plan_key,
                "idempotency_key": idempotency_key
            },
            timeout=10
        )
        return response.status_code, response.json() if response.text else {}
    except Exception as e:
        return None, {"error": str(e)}

# Get admin token
print("\n🔐 Logging in as admin...")
admin_token = get_admin_token()
print("✅ Admin token obtained")

print("\n" + "=" * 80)
print("TEST 1: IDEMPOTENCY + EXTREME RACE (SAME KEY)")
print("=" * 80)
print("Register fresh user, fund with EXACTLY 1000, fire 10+ concurrent gold requests")
print("with SAME idempotency_key. Expect: NO 500s, exactly ONE investment created.")
print("-" * 80)

timestamp = int(time.time() * 1000)
user1_email = f"race_same_{timestamp}@test.com"
user1_phone = f"+91{timestamp % 10000000000}"

print(f"\n1️⃣  Registering user: {user1_email}")
user1_token = register_user(user1_email, user1_phone)
user1_id = get_user_id(user1_token)
print(f"✅ User registered: {user1_id}")

print(f"\n2️⃣  Funding user with EXACTLY 1000.00")
fund_user(admin_token, user1_id, 1000)
wallet_before = get_wallet(user1_token)
print(f"✅ Wallet funded: available_balance = {wallet_before['available_balance']}")

print(f"\n3️⃣  Firing 12 CONCURRENT gold purchase requests with SAME idempotency_key='RACE_SAME'")
SAME_KEY = "RACE_SAME"
NUM_REQUESTS = 12

def make_request(idx):
    """Make a single investment request."""
    status, resp = buy_investment(user1_token, "gold", SAME_KEY)
    return idx, status, resp

# Fire concurrent requests
start_time = time.time()
results = []
with ThreadPoolExecutor(max_workers=NUM_REQUESTS) as executor:
    futures = [executor.submit(make_request, i) for i in range(NUM_REQUESTS)]
    for future in as_completed(futures):
        results.append(future.result())
elapsed = time.time() - start_time

print(f"✅ All {NUM_REQUESTS} requests completed in {elapsed:.2f}s")

# Analyze results
status_codes = {}
investment_ids = set()
error_500_count = 0

for idx, status, resp in results:
    status_codes[status] = status_codes.get(status, 0) + 1
    if status == 500:
        error_500_count += 1
        print(f"   ⚠️  Request {idx}: 500 ERROR - {resp.get('detail', 'Unknown error')}")
    elif status in [200, 201]:
        inv_id = resp.get("id")
        if inv_id:
            investment_ids.add(inv_id)
    print(f"   Request {idx}: status={status}, id={resp.get('id', 'N/A')[:8] if resp.get('id') else 'N/A'}")

print(f"\n📊 Status code distribution:")
for status, count in sorted(status_codes.items()):
    print(f"   {status}: {count} requests")

print(f"\n📊 Unique investment IDs created: {len(investment_ids)}")
if investment_ids:
    for inv_id in investment_ids:
        print(f"   - {inv_id}")

# Check wallet state
wallet_after = get_wallet(user1_token)
transactions = get_transactions(user1_token)
consistency = get_consistency(user1_token)

investment_debits = [t for t in transactions if t.get("type") == "INVESTMENT" and t.get("direction") == "debit"]

print(f"\n💰 Wallet state after:")
print(f"   Available balance: {wallet_after['available_balance']}")
print(f"   Locked investment: {wallet_after['locked_investment']}")
print(f"   Total portfolio: {wallet_after['total_portfolio']}")
print(f"   INVESTMENT debit count: {len(investment_debits)}")
if investment_debits:
    for debit in investment_debits:
        print(f"      - Amount: {debit['amount']}, Balance after: {debit['balance_after']}")

print(f"\n🔍 Consistency check:")
print(f"   Consistent: {consistency['consistent']}")
print(f"   Available balance: {consistency['available_balance']}")
print(f"   Ledger balance: {consistency['ledger_balance']}")

# Validate TEST 1
test1_pass = True
test1_details = []

if error_500_count > 0:
    test1_pass = False
    test1_details.append(f"❌ Found {error_500_count} 500 errors (expected 0)")
else:
    test1_details.append(f"✅ No 500 errors (0/{NUM_REQUESTS})")

if len(investment_ids) != 1:
    test1_pass = False
    test1_details.append(f"❌ Created {len(investment_ids)} investments (expected exactly 1)")
else:
    test1_details.append(f"✅ Exactly 1 investment created")

if len(investment_debits) != 1:
    test1_pass = False
    test1_details.append(f"❌ Found {len(investment_debits)} INVESTMENT debits (expected exactly 1)")
else:
    test1_details.append(f"✅ Exactly 1 INVESTMENT debit")

if wallet_after['available_balance'] != "0.00":
    test1_pass = False
    test1_details.append(f"❌ Final balance {wallet_after['available_balance']} (expected 0.00)")
else:
    test1_details.append(f"✅ Final balance 0.00")

if not consistency['consistent']:
    test1_pass = False
    test1_details.append(f"❌ Wallet consistency check failed")
else:
    test1_details.append(f"✅ Wallet consistency maintained")

log_test("TEST 1: IDEMPOTENCY + EXTREME RACE (SAME KEY)", test1_pass, "\n    ".join(test1_details))

print("\n" + "=" * 80)
print("TEST 2: CONCURRENCY DIFFERENT KEYS / NO DOUBLE-SPEND")
print("=" * 80)
print("Register fresh user, fund with EXACTLY 1000, fire 10 concurrent gold requests")
print("with DIFFERENT idempotency_keys. Expect: at most ONE succeeds (201), rest 402.")
print("-" * 80)

timestamp = int(time.time() * 1000)
user2_email = f"race_diff_{timestamp}@test.com"
user2_phone = f"+91{(timestamp + 1) % 10000000000}"

print(f"\n1️⃣  Registering user: {user2_email}")
user2_token = register_user(user2_email, user2_phone)
user2_id = get_user_id(user2_token)
print(f"✅ User registered: {user2_id}")

print(f"\n2️⃣  Funding user with EXACTLY 1000.00")
fund_user(admin_token, user2_id, 1000)
wallet_before = get_wallet(user2_token)
print(f"✅ Wallet funded: available_balance = {wallet_before['available_balance']}")

print(f"\n3️⃣  Firing 10 CONCURRENT gold purchase requests with DIFFERENT idempotency_keys")
NUM_REQUESTS_2 = 10

def make_request_diff(idx):
    """Make a single investment request with unique key."""
    key = f"RACE_DIFF_{idx}"
    status, resp = buy_investment(user2_token, "gold", key)
    return idx, key, status, resp

# Fire concurrent requests
start_time = time.time()
results2 = []
with ThreadPoolExecutor(max_workers=NUM_REQUESTS_2) as executor:
    futures = [executor.submit(make_request_diff, i) for i in range(NUM_REQUESTS_2)]
    for future in as_completed(futures):
        results2.append(future.result())
elapsed = time.time() - start_time

print(f"✅ All {NUM_REQUESTS_2} requests completed in {elapsed:.2f}s")

# Analyze results
status_codes_2 = {}
investment_ids_2 = set()
success_count = 0
insufficient_count = 0
error_500_count_2 = 0

for idx, key, status, resp in results2:
    status_codes_2[status] = status_codes_2.get(status, 0) + 1
    if status == 201:
        success_count += 1
        inv_id = resp.get("id")
        if inv_id:
            investment_ids_2.add(inv_id)
    elif status == 402:
        insufficient_count += 1
    elif status == 500:
        error_500_count_2 += 1
        print(f"   ⚠️  Request {idx} (key={key}): 500 ERROR - {resp.get('detail', 'Unknown error')}")
    
    print(f"   Request {idx} (key={key}): status={status}, id={resp.get('id', 'N/A')[:8] if resp.get('id') else 'N/A'}")

print(f"\n📊 Status code distribution:")
for status, count in sorted(status_codes_2.items()):
    print(f"   {status}: {count} requests")

print(f"\n📊 Success (201): {success_count}, Insufficient (402): {insufficient_count}, 500 errors: {error_500_count_2}")
print(f"📊 Unique investment IDs created: {len(investment_ids_2)}")

# Check wallet state
wallet_after_2 = get_wallet(user2_token)
transactions_2 = get_transactions(user2_token)
consistency_2 = get_consistency(user2_token)

investment_debits_2 = [t for t in transactions_2 if t.get("type") == "INVESTMENT" and t.get("direction") == "debit"]

print(f"\n💰 Wallet state after:")
print(f"   Available balance: {wallet_after_2['available_balance']}")
print(f"   Locked investment: {wallet_after_2['locked_investment']}")
print(f"   Total portfolio: {wallet_after_2['total_portfolio']}")
print(f"   INVESTMENT debit count: {len(investment_debits_2)}")

print(f"\n🔍 Consistency check:")
print(f"   Consistent: {consistency_2['consistent']}")
print(f"   Available balance: {consistency_2['available_balance']}")
print(f"   Ledger balance: {consistency_2['ledger_balance']}")

# Check for negative balance
balance_negative = False
try:
    balance_val = Decimal(wallet_after_2['available_balance'])
    if balance_val < 0:
        balance_negative = True
except (ValueError, KeyError, TypeError):
    pass

# Validate TEST 2
test2_pass = True
test2_details = []

if error_500_count_2 > 0:
    test2_pass = False
    test2_details.append(f"❌ Found {error_500_count_2} 500 errors (expected 0)")
else:
    test2_details.append(f"✅ No 500 errors")

if success_count > 1:
    test2_pass = False
    test2_details.append(f"❌ {success_count} requests succeeded (expected at most 1)")
else:
    test2_details.append(f"✅ At most 1 request succeeded ({success_count})")

if len(investment_debits_2) != success_count:
    test2_pass = False
    test2_details.append(f"❌ {len(investment_debits_2)} debits but {success_count} successes (should match)")
else:
    test2_details.append(f"✅ Debit count matches success count ({len(investment_debits_2)})")

if balance_negative:
    test2_pass = False
    test2_details.append(f"❌ Balance went negative: {wallet_after_2['available_balance']}")
else:
    test2_details.append(f"✅ Balance never negative: {wallet_after_2['available_balance']}")

if wallet_after_2['available_balance'] != "0.00":
    test2_pass = False
    test2_details.append(f"❌ Final balance {wallet_after_2['available_balance']} (expected 0.00)")
else:
    test2_details.append(f"✅ Final balance 0.00")

if not consistency_2['consistent']:
    test2_pass = False
    test2_details.append(f"❌ Wallet consistency check failed")
else:
    test2_details.append(f"✅ Wallet consistency maintained")

log_test("TEST 2: CONCURRENCY DIFFERENT KEYS / NO DOUBLE-SPEND", test2_pass, "\n    ".join(test2_details))

print("\n" + "=" * 80)
print("TEST 3: SEQUENTIAL IDEMPOTENCY REGRESSION")
print("=" * 80)
print("Register fresh user, fund with 1000, POST gold with idempotency_key='SEQ1' TWICE")
print("sequentially. Expect: same investment ID both times, only ONE debit.")
print("-" * 80)

timestamp = int(time.time() * 1000)
user3_email = f"seq_{timestamp}@test.com"
user3_phone = f"+91{(timestamp + 2) % 10000000000}"

print(f"\n1️⃣  Registering user: {user3_email}")
user3_token = register_user(user3_email, user3_phone)
user3_id = get_user_id(user3_token)
print(f"✅ User registered: {user3_id}")

print(f"\n2️⃣  Funding user with 1000.00")
fund_user(admin_token, user3_id, 1000)
wallet_before_3 = get_wallet(user3_token)
print(f"✅ Wallet funded: available_balance = {wallet_before_3['available_balance']}")

print(f"\n3️⃣  First POST gold with idempotency_key='SEQ1'")
status1, resp1 = buy_investment(user3_token, "gold", "SEQ1")
print(f"   Status: {status1}, Investment ID: {resp1.get('id', 'N/A')}")

print(f"\n4️⃣  Second POST gold with SAME idempotency_key='SEQ1'")
status2, resp2 = buy_investment(user3_token, "gold", "SEQ1")
print(f"   Status: {status2}, Investment ID: {resp2.get('id', 'N/A')}")

# Check wallet state
wallet_after_3 = get_wallet(user3_token)
transactions_3 = get_transactions(user3_token)
investment_debits_3 = [t for t in transactions_3 if t.get("type") == "INVESTMENT" and t.get("direction") == "debit"]

print(f"\n💰 Wallet state after:")
print(f"   Available balance: {wallet_after_3['available_balance']}")
print(f"   INVESTMENT debit count: {len(investment_debits_3)}")

# Validate TEST 3
test3_pass = True
test3_details = []

if status1 not in [200, 201] or status2 not in [200, 201]:
    test3_pass = False
    test3_details.append(f"❌ Unexpected status codes: {status1}, {status2}")
else:
    test3_details.append(f"✅ Both requests returned success ({status1}, {status2})")

inv_id_1 = resp1.get("id")
inv_id_2 = resp2.get("id")
if inv_id_1 != inv_id_2:
    test3_pass = False
    test3_details.append(f"❌ Different investment IDs: {inv_id_1} vs {inv_id_2}")
else:
    test3_details.append(f"✅ Same investment ID returned: {inv_id_1}")

if len(investment_debits_3) != 1:
    test3_pass = False
    test3_details.append(f"❌ {len(investment_debits_3)} debits (expected exactly 1)")
else:
    test3_details.append(f"✅ Exactly 1 INVESTMENT debit")

if wallet_after_3['available_balance'] != "0.00":
    test3_pass = False
    test3_details.append(f"❌ Final balance {wallet_after_3['available_balance']} (expected 0.00)")
else:
    test3_details.append(f"✅ Final balance 0.00 (debited once)")

log_test("TEST 3: SEQUENTIAL IDEMPOTENCY REGRESSION", test3_pass, "\n    ".join(test3_details))

print("\n" + "=" * 80)
print("TEST 4: QUICK REGRESSION - SILVER PURCHASE & INSUFFICIENT BALANCE")
print("=" * 80)
print("Register fresh user, fund with 500, buy silver (300) -> 201, check amounts.")
print("Then try to buy gold (1000) with insufficient balance -> 402 with full rollback.")
print("-" * 80)

timestamp = int(time.time() * 1000)
user4_email = f"quick_{timestamp}@test.com"
user4_phone = f"+91{(timestamp + 3) % 10000000000}"

print(f"\n1️⃣  Registering user: {user4_email}")
user4_token = register_user(user4_email, user4_phone)
user4_id = get_user_id(user4_token)
print(f"✅ User registered: {user4_id}")

print(f"\n2️⃣  Funding user with 500.00")
fund_user(admin_token, user4_id, 500)
wallet_before_4 = get_wallet(user4_token)
print(f"✅ Wallet funded: available_balance = {wallet_before_4['available_balance']}")

print(f"\n3️⃣  Buying silver (fixed price 300)")
status_silver, resp_silver = buy_investment(user4_token, "silver", "SILVER_TEST")
print(f"   Status: {status_silver}")
if status_silver == 201:
    print(f"   Investment ID: {resp_silver.get('id')}")
    print(f"   Principal: {resp_silver.get('principal')}")
    print(f"   Profit amount: {resp_silver.get('profit_amount')}")
    print(f"   Maturity amount: {resp_silver.get('maturity_amount')}")
    print(f"   Status: {resp_silver.get('status')}")
    print(f"   Lock days: {resp_silver.get('lock_days')}")
    print(f"   Start at: {resp_silver.get('start_at')}")
    print(f"   Maturity at: {resp_silver.get('maturity_at')}")
    
    # Check maturity date is start + 60 days
    from datetime import datetime, timedelta
    start_at = resp_silver.get('start_at')
    maturity_at = resp_silver.get('maturity_at')
    if start_at and maturity_at:
        start_dt = datetime.fromisoformat(start_at.replace('Z', '+00:00'))
        maturity_dt = datetime.fromisoformat(maturity_at.replace('Z', '+00:00'))
        expected_maturity = start_dt + timedelta(days=60)
        diff_seconds = abs((maturity_dt - expected_maturity).total_seconds())
        print(f"   Maturity date check: {diff_seconds:.1f}s difference (expected ~0)")

wallet_after_silver = get_wallet(user4_token)
print(f"\n💰 Wallet after silver purchase:")
print(f"   Available balance: {wallet_after_silver['available_balance']}")
print(f"   Locked investment: {wallet_after_silver['locked_investment']}")

print(f"\n4️⃣  Attempting to buy gold (1000) with insufficient balance (200)")
status_gold, resp_gold = buy_investment(user4_token, "gold", "GOLD_TEST")
print(f"   Status: {status_gold}")
if status_gold == 402:
    print(f"   Detail: {resp_gold.get('detail')}")

# Check wallet state after failed purchase
wallet_after_fail = get_wallet(user4_token)
transactions_4 = get_transactions(user4_token)
investment_debits_4 = [t for t in transactions_4 if t.get("type") == "INVESTMENT" and t.get("direction") == "debit"]

print(f"\n💰 Wallet after failed gold purchase:")
print(f"   Available balance: {wallet_after_fail['available_balance']}")
print(f"   INVESTMENT debit count: {len(investment_debits_4)}")

consistency_4 = get_consistency(user4_token)
print(f"\n🔍 Consistency check:")
print(f"   Consistent: {consistency_4['consistent']}")

# Validate TEST 4
test4_pass = True
test4_details = []

# Silver purchase checks
if status_silver != 201:
    test4_pass = False
    test4_details.append(f"❌ Silver purchase failed: status {status_silver}")
else:
    test4_details.append(f"✅ Silver purchase succeeded (201)")

if resp_silver.get('principal') != "300.00":
    test4_pass = False
    test4_details.append(f"❌ Principal {resp_silver.get('principal')} (expected 300.00)")
else:
    test4_details.append(f"✅ Principal 300.00")

if resp_silver.get('profit_amount') != "180.00":
    test4_pass = False
    test4_details.append(f"❌ Profit {resp_silver.get('profit_amount')} (expected 180.00)")
else:
    test4_details.append(f"✅ Profit 180.00")

if resp_silver.get('maturity_amount') != "480.00":
    test4_pass = False
    test4_details.append(f"❌ Maturity {resp_silver.get('maturity_amount')} (expected 480.00)")
else:
    test4_details.append(f"✅ Maturity 480.00")

if resp_silver.get('status') != "active":
    test4_pass = False
    test4_details.append(f"❌ Status {resp_silver.get('status')} (expected active)")
else:
    test4_details.append(f"✅ Status active")

# Check maturity date
if start_at and maturity_at:
    if diff_seconds > 10:  # Allow 10s tolerance
        test4_pass = False
        test4_details.append(f"❌ Maturity date off by {diff_seconds:.1f}s (expected start + 60 days)")
    else:
        test4_details.append(f"✅ Maturity date = start + 60 days")

# Insufficient balance checks
if status_gold != 402:
    test4_pass = False
    test4_details.append(f"❌ Gold purchase status {status_gold} (expected 402)")
else:
    test4_details.append(f"✅ Gold purchase rejected with 402")

# Check rollback
if wallet_after_fail['available_balance'] != wallet_after_silver['available_balance']:
    test4_pass = False
    test4_details.append(f"❌ Balance changed after failed purchase (no rollback)")
else:
    test4_details.append(f"✅ Balance unchanged after failed purchase (rollback OK)")

if len(investment_debits_4) != 1:
    test4_pass = False
    test4_details.append(f"❌ {len(investment_debits_4)} debits (expected 1, no debit for failed purchase)")
else:
    test4_details.append(f"✅ Only 1 debit (no debit for failed purchase)")

if not consistency_4['consistent']:
    test4_pass = False
    test4_details.append(f"❌ Wallet consistency check failed")
else:
    test4_details.append(f"✅ Wallet consistency maintained")

log_test("TEST 4: QUICK REGRESSION - SILVER PURCHASE & INSUFFICIENT BALANCE", test4_pass, "\n    ".join(test4_details))

# Final summary
print("\n" + "=" * 80)
print("CONCURRENCY & IDEMPOTENCY TEST SUMMARY")
print("=" * 80)
print(f"✅ PASSED: {passed}/{passed + failed}")
print(f"❌ FAILED: {failed}/{passed + failed}")
print(f"📊 Success rate: {(passed / (passed + failed) * 100):.1f}%")
print("=" * 80)

if failed == 0:
    print("\n🎉 ALL TESTS PASSED! Concurrency/idempotency fix verified.")
else:
    print(f"\n⚠️  {failed} test(s) failed. Review details above.")

print("\n📋 Test Results:")
for result in test_results:
    status = "✅" if result["passed"] else "❌"
    print(f"{status} {result['test']}")
