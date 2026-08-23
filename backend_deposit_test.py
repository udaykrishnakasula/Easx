#!/usr/bin/env python3
"""
USDT Deposit Flow Backend Test Suite
Tests all 12 scenarios specified in the review request.
"""
import requests
import uuid
import time
from decimal import Decimal

# Base URL from frontend/.env
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
    status = "✅ PASS" if passed else "❌ FAIL"
    if passed:
        tests_passed += 1
    else:
        tests_failed += 1
    msg = f"{status} - Scenario {scenario}: {test_name}"
    if details:
        msg += f" | {details}"
    print(msg)
    test_results.append({"scenario": scenario, "test": test_name, "passed": passed, "details": details})


def register_user(email, password="TestPass123!", name="Test User", phone=None):
    """Register a new user and return access token."""
    if phone is None:
        phone = f"+1555{str(uuid.uuid4().int)[:7]}"
    
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": name,
        "email": email,
        "phone": phone,
        "password": password,
        "password_confirm": password,
    })
    if resp.status_code == 201:
        return resp.json()["access_token"]
    else:
        print(f"Failed to register user {email}: {resp.status_code} {resp.text}")
        return None


def login(email, password):
    """Login and return access token."""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password,
    })
    if resp.status_code == 200:
        return resp.json()["access_token"]
    else:
        print(f"Failed to login {email}: {resp.status_code} {resp.text}")
        return None


def get_wallet(token):
    """Get wallet summary."""
    resp = requests.get(f"{BASE_URL}/wallet", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    return None


def get_transactions(token):
    """Get wallet transactions."""
    resp = requests.get(f"{BASE_URL}/transactions", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    return None


def get_wallet_consistency(token):
    """Check wallet consistency."""
    resp = requests.get(f"{BASE_URL}/wallet/consistency", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    return None


def get_notifications(token):
    """Get user notifications."""
    resp = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    return None


def admin_credit_wallet(admin_token, user_id, amount):
    """Admin credits user wallet."""
    resp = requests.post(f"{BASE_URL}/admin/wallet/adjust", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={
                            "user_id": user_id,
                            "amount": str(amount),
                            "direction": "credit",
                            "note": "Test credit",
                            "idempotency_key": f"test-credit-{uuid.uuid4()}"
                        })
    return resp.status_code == 200


print("=" * 80)
print("USDT DEPOSIT FLOW BACKEND TEST SUITE")
print("=" * 80)
print()

# Login as admin
print("Logging in as admin...")
admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
if not admin_token:
    print("❌ CRITICAL: Failed to login as admin. Cannot proceed.")
    exit(1)
print("✅ Admin login successful")
print()

# ============================================================================
# SCENARIO 1: CONFIG - GET /api/deposits/config
# ============================================================================
print("SCENARIO 1: CONFIG - GET /api/deposits/config")
print("-" * 80)

# Register a test user for config check
u1_email = f"config_user_{uuid.uuid4().hex[:8]}@test.com"
u1_token = register_user(u1_email, name="Config User")

if u1_token:
    resp = requests.get(f"{BASE_URL}/deposits/config", headers={"Authorization": f"Bearer {u1_token}"})
    
    if resp.status_code == 200:
        config = resp.json()
        
        # Check min_deposit exactly "300.00"
        min_deposit_ok = config.get("min_deposit") == "300.00"
        log_test(1, "min_deposit exactly '300.00'", min_deposit_ok, 
                f"Expected '300.00', got '{config.get('min_deposit')}'")
        
        # Check networks ["TRC20", "BEP20"]
        networks = config.get("networks", [])
        networks_ok = set(networks) == {"TRC20", "BEP20"}
        log_test(1, "networks ['TRC20', 'BEP20']", networks_ok,
                f"Expected ['TRC20', 'BEP20'], got {networks}")
        
        # Check addresses present for both
        addresses = config.get("addresses", {})
        trc20_addr = addresses.get("TRC20")
        bep20_addr = addresses.get("BEP20")
        addresses_ok = trc20_addr is not None and bep20_addr is not None
        log_test(1, "addresses present for TRC20 and BEP20", addresses_ok,
                f"TRC20: {trc20_addr}, BEP20: {bep20_addr}")
        
        # Check configured is boolean
        configured = config.get("configured")
        configured_ok = isinstance(configured, bool)
        log_test(1, "configured is boolean", configured_ok,
                f"Expected bool, got {type(configured).__name__}: {configured}")
    else:
        log_test(1, "GET /api/deposits/config", False, f"Status {resp.status_code}")
else:
    log_test(1, "Register user for config test", False, "Failed to register user")

print()

# ============================================================================
# SCENARIO 2: CREATE PENDING (no auto-credit)
# ============================================================================
print("SCENARIO 2: CREATE PENDING (no auto-credit)")
print("-" * 80)

u1_email = f"deposit_user_{uuid.uuid4().hex[:8]}@test.com"
u1_token = register_user(u1_email, name="Deposit User 1")

if u1_token:
    # Get initial wallet balance (should be 0.00)
    wallet_before = get_wallet(u1_token)
    initial_balance = wallet_before.get("available_balance", "0.00") if wallet_before else "0.00"
    
    log_test(2, "Initial wallet balance is 0.00", initial_balance == "0.00",
            f"Expected '0.00', got '{initial_balance}'")
    
    # Create deposit
    unique_hash_a = f"TESTHASH{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u1_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "500",
                            "tx_hash": unique_hash_a
                        })
    
    if resp.status_code == 201:
        deposit = resp.json()
        
        # Check status is "pending"
        status_ok = deposit.get("status") == "pending"
        log_test(2, "Deposit status is 'pending'", status_ok,
                f"Expected 'pending', got '{deposit.get('status')}'")
        
        # Check amount is "500.00"
        amount_ok = deposit.get("amount") == "500.00"
        log_test(2, "Deposit amount is '500.00'", amount_ok,
                f"Expected '500.00', got '{deposit.get('amount')}'")
        
        # Check network is "TRC20"
        network_ok = deposit.get("network") == "TRC20"
        log_test(2, "Deposit network is 'TRC20'", network_ok,
                f"Expected 'TRC20', got '{deposit.get('network')}'")
        
        # CRITICAL: Check wallet balance is STILL 0.00 (no auto-credit)
        wallet_after = get_wallet(u1_token)
        balance_after = wallet_after.get("available_balance", "0.00") if wallet_after else "0.00"
        no_auto_credit = balance_after == "0.00"
        log_test(2, "CRITICAL: Wallet STILL 0.00 (no auto-credit)", no_auto_credit,
                f"Expected '0.00', got '{balance_after}'")
        
        # Check deposit appears in user's deposit list as pending
        resp_list = requests.get(f"{BASE_URL}/deposits", headers={"Authorization": f"Bearer {u1_token}"})
        if resp_list.status_code == 200:
            deposits = resp_list.json()
            found = any(d.get("id") == deposit.get("id") and d.get("status") == "pending" for d in deposits)
            log_test(2, "Deposit appears in user's list as pending", found,
                    f"Found deposit in list: {found}")
        else:
            log_test(2, "GET /api/deposits", False, f"Status {resp_list.status_code}")
        
        # Store deposit ID and user token for later scenarios
        u1_deposit_id = deposit.get("id")
        u1_user_id = None
        # Get user ID from /api/auth/me
        me_resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {u1_token}"})
        if me_resp.status_code == 200:
            u1_user_id = me_resp.json().get("id")
    else:
        log_test(2, "POST /api/deposits (500 TRC20)", False, 
                f"Status {resp.status_code}: {resp.text}")
else:
    log_test(2, "Register user for deposit test", False, "Failed to register user")

print()

# ============================================================================
# SCENARIO 3: MINIMUM $300 ENFORCED
# ============================================================================
print("SCENARIO 3: MINIMUM $300 ENFORCED")
print("-" * 80)

if u1_token:
    # Try to deposit 299.99 (below minimum)
    unique_hash_b = f"TESTHASH{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u1_token}"},
                        json={
                            "network": "BEP20",
                            "amount": "299.99",
                            "tx_hash": unique_hash_b
                        })
    
    below_min_ok = resp.status_code == 400
    detail = resp.json().get("detail", {}) if resp.status_code == 400 else {}
    code_ok = detail.get("code") == "below_minimum" if isinstance(detail, dict) else False
    
    log_test(3, "Amount 299.99 rejected with 400", below_min_ok,
            f"Expected 400, got {resp.status_code}")
    log_test(3, "Error code is 'below_minimum'", code_ok,
            f"Expected 'below_minimum', got '{detail.get('code') if isinstance(detail, dict) else detail}'")
    
    # Try to deposit exactly 300 (boundary inclusive)
    unique_hash_c = f"TESTHASH{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u1_token}"},
                        json={
                            "network": "BEP20",
                            "amount": "300",
                            "tx_hash": unique_hash_c
                        })
    
    boundary_ok = resp.status_code == 201
    log_test(3, "Amount 300 accepted (boundary inclusive)", boundary_ok,
            f"Expected 201, got {resp.status_code}")
    
    if boundary_ok:
        deposit = resp.json()
        status_ok = deposit.get("status") == "pending"
        log_test(3, "300 deposit status is 'pending'", status_ok,
                f"Expected 'pending', got '{deposit.get('status')}'")

print()

# ============================================================================
# SCENARIO 4: DUPLICATE TX HASH BLOCKED
# ============================================================================
print("SCENARIO 4: DUPLICATE TX HASH BLOCKED")
print("-" * 80)

if u1_token:
    # Submit a deposit with a unique hash
    dup_hash = "DUPHASH123456"
    resp1 = requests.post(f"{BASE_URL}/deposits",
                         headers={"Authorization": f"Bearer {u1_token}"},
                         json={
                             "network": "TRC20",
                             "amount": "400",
                             "tx_hash": dup_hash
                         })
    
    first_ok = resp1.status_code == 201
    log_test(4, "First deposit with DUPHASH123456 succeeds", first_ok,
            f"Expected 201, got {resp1.status_code}")
    
    # Try to submit again with the SAME hash
    resp2 = requests.post(f"{BASE_URL}/deposits",
                         headers={"Authorization": f"Bearer {u1_token}"},
                         json={
                             "network": "BEP20",  # Different network
                             "amount": "500",
                             "tx_hash": dup_hash
                         })
    
    dup_blocked = resp2.status_code == 409
    detail = resp2.json().get("detail", {}) if resp2.status_code == 409 else {}
    code_ok = detail.get("code") == "duplicate_tx_hash" if isinstance(detail, dict) else False
    
    log_test(4, "Duplicate hash rejected with 409", dup_blocked,
            f"Expected 409, got {resp2.status_code}")
    log_test(4, "Error code is 'duplicate_tx_hash'", code_ok,
            f"Expected 'duplicate_tx_hash', got '{detail.get('code') if isinstance(detail, dict) else detail}'")
    
    # Register a second user and try with same hash (different user)
    u2_email = f"deposit_user2_{uuid.uuid4().hex[:8]}@test.com"
    u2_token = register_user(u2_email, name="Deposit User 2")
    
    if u2_token:
        resp3 = requests.post(f"{BASE_URL}/deposits",
                             headers={"Authorization": f"Bearer {u2_token}"},
                             json={
                                 "network": "TRC20",
                                 "amount": "600",
                                 "tx_hash": dup_hash
                             })
        
        dup_blocked_u2 = resp3.status_code == 409
        log_test(4, "Duplicate hash blocked for different user", dup_blocked_u2,
                f"Expected 409, got {resp3.status_code}")
    
    # Test case-insensitivity: submit with lowercase version
    resp4 = requests.post(f"{BASE_URL}/deposits",
                         headers={"Authorization": f"Bearer {u1_token}"},
                         json={
                             "network": "TRC20",
                             "amount": "700",
                             "tx_hash": "duphash123456"  # lowercase
                         })
    
    case_insensitive = resp4.status_code == 409
    log_test(4, "Case-insensitive duplicate detection", case_insensitive,
            f"Expected 409 for lowercase 'duphash123456', got {resp4.status_code}")

print()

# ============================================================================
# SCENARIO 5: INVALID INPUT
# ============================================================================
print("SCENARIO 5: INVALID INPUT")
print("-" * 80)

if u1_token:
    # Invalid network
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u1_token}"},
                        json={
                            "network": "ETH",
                            "amount": "500",
                            "tx_hash": f"TESTHASH{uuid.uuid4().hex[:16].upper()}"
                        })
    
    invalid_network = resp.status_code == 422
    log_test(5, "Invalid network rejected with 422", invalid_network,
            f"Expected 422, got {resp.status_code}")
    
    # tx_hash too short
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u1_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "500",
                            "tx_hash": "abc"
                        })
    
    short_hash = resp.status_code == 422
    log_test(5, "Short tx_hash (<8 chars) rejected with 422", short_hash,
            f"Expected 422, got {resp.status_code}")
    
    # Non-numeric amount
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u1_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "abc",
                            "tx_hash": f"TESTHASH{uuid.uuid4().hex[:16].upper()}"
                        })
    
    invalid_amount = resp.status_code == 422
    detail = resp.json().get("detail", {}) if resp.status_code == 422 else {}
    code_ok = (detail.get("code") == "invalid_amount" if isinstance(detail, dict) else False) or resp.status_code == 422
    
    log_test(5, "Non-numeric amount rejected with 422", invalid_amount,
            f"Expected 422, got {resp.status_code}")

print()

# ============================================================================
# SCENARIO 6: ADMIN APPROVE credits EXACT amount
# ============================================================================
print("SCENARIO 6: ADMIN APPROVE credits EXACT amount")
print("-" * 80)

# Create a fresh user with a pending deposit
u3_email = f"approve_user_{uuid.uuid4().hex[:8]}@test.com"
u3_token = register_user(u3_email, name="Approve User")

if u3_token and admin_token:
    # Get user ID
    me_resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {u3_token}"})
    u3_user_id = me_resp.json().get("id") if me_resp.status_code == 200 else None
    
    # Create a pending deposit
    unique_hash = f"APPROVE{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u3_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "500",
                            "tx_hash": unique_hash
                        })
    
    if resp.status_code == 201:
        deposit = resp.json()
        deposit_id = deposit.get("id")
        
        # Admin: GET /api/admin/deposits?status=pending
        resp_admin = requests.get(f"{BASE_URL}/admin/deposits?status=pending",
                                 headers={"Authorization": f"Bearer {admin_token}"})
        
        if resp_admin.status_code == 200:
            admin_deposits = resp_admin.json()
            found_deposit = next((d for d in admin_deposits if d.get("id") == deposit_id), None)
            
            if found_deposit:
                # Check embedded user email
                user_email = found_deposit.get("user", {}).get("email")
                email_ok = user_email == u3_email
                log_test(6, "Admin list includes deposit with embedded user email", email_ok,
                        f"Expected '{u3_email}', got '{user_email}'")
                
                # Approve with NO body (default to submitted amount)
                resp_approve = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                                            headers={"Authorization": f"Bearer {admin_token}"},
                                            json={})
                
                if resp_approve.status_code == 200:
                    approved_deposit = resp_approve.json()
                    
                    # Check status is "approved"
                    status_ok = approved_deposit.get("status") == "approved"
                    log_test(6, "Deposit status is 'approved'", status_ok,
                            f"Expected 'approved', got '{approved_deposit.get('status')}'")
                    
                    # Check approved_amount is "500.00"
                    approved_amt = approved_deposit.get("approved_amount")
                    amount_ok = approved_amt == "500.00"
                    log_test(6, "Approved amount is '500.00'", amount_ok,
                            f"Expected '500.00', got '{approved_amt}'")
                    
                    # Check wallet credited EXACTLY 500.00
                    wallet = get_wallet(u3_token)
                    if wallet:
                        available = wallet.get("available_balance", "0.00")
                        wallet_ok = available == "500.00"
                        log_test(6, "Wallet credited EXACTLY 500.00", wallet_ok,
                                f"Expected '500.00', got '{available}'")
                    
                    # Check transaction ledger has DEPOSIT credit of 500.00
                    transactions = get_transactions(u3_token)
                    if transactions:
                        deposit_tx = next((t for t in transactions if t.get("type") == "DEPOSIT" 
                                         and t.get("ref_type") == "deposit" 
                                         and t.get("ref_id") == deposit_id), None)
                        
                        if deposit_tx:
                            tx_amount = deposit_tx.get("amount")
                            tx_status = deposit_tx.get("status")
                            tx_ok = tx_amount == "500.00" and tx_status == "completed"
                            log_test(6, "Ledger has DEPOSIT credit 500.00 completed", tx_ok,
                                    f"Amount: {tx_amount}, Status: {tx_status}")
                        else:
                            log_test(6, "Ledger has DEPOSIT entry", False, "DEPOSIT transaction not found")
                    
                    # Check wallet consistency
                    consistency = get_wallet_consistency(u3_token)
                    if consistency:
                        consistent = consistency.get("consistent")
                        log_test(6, "Wallet consistency maintained", consistent == True,
                                f"consistent={consistent}")
                    
                    # Check user notification
                    notifications = get_notifications(u3_token)
                    if notifications:
                        notif = next((n for n in notifications if n.get("type") == "deposit_approved"), None)
                        if notif:
                            title_ok = notif.get("title") == "Deposit approved"
                            log_test(6, "User receives 'Deposit approved' notification", title_ok,
                                    f"Title: {notif.get('title')}")
                        else:
                            log_test(6, "User receives notification", False, "No deposit_approved notification found")
                else:
                    log_test(6, "POST /api/admin/deposits/{id}/approve", False,
                            f"Status {resp_approve.status_code}")
            else:
                log_test(6, "Find deposit in admin list", False, "Deposit not found in admin list")
        else:
            log_test(6, "GET /api/admin/deposits?status=pending", False,
                    f"Status {resp_admin.status_code}")
    else:
        log_test(6, "Create pending deposit for approval", False,
                f"Status {resp.status_code}")

print()

# ============================================================================
# SCENARIO 7: ADMIN APPROVE WITH AMOUNT OVERRIDE
# ============================================================================
print("SCENARIO 7: ADMIN APPROVE WITH AMOUNT OVERRIDE")
print("-" * 80)

# Create another pending deposit for the same user
if u3_token and admin_token:
    unique_hash = f"OVERRIDE{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u3_token}"},
                        json={
                            "network": "BEP20",
                            "amount": "1000",
                            "tx_hash": unique_hash
                        })
    
    if resp.status_code == 201:
        deposit = resp.json()
        deposit_id = deposit.get("id")
        
        # Get wallet balance before approval
        wallet_before = get_wallet(u3_token)
        balance_before = wallet_before.get("available_balance", "0.00") if wallet_before else "0.00"
        
        # Approve with amount override
        resp_approve = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                                    headers={"Authorization": f"Bearer {admin_token}"},
                                    json={
                                        "approved_amount": "950",
                                        "note": "Received 950 on-chain"
                                    })
        
        if resp_approve.status_code == 200:
            approved_deposit = resp_approve.json()
            
            # Check approved_amount is "950.00"
            approved_amt = approved_deposit.get("approved_amount")
            amount_ok = approved_amt == "950.00"
            log_test(7, "Approved amount is '950.00' (overridden)", amount_ok,
                    f"Expected '950.00', got '{approved_amt}'")
            
            # Check wallet credited EXACTLY 950.00 (not 1000)
            wallet_after = get_wallet(u3_token)
            if wallet_after:
                balance_after = wallet_after.get("available_balance", "0.00")
                expected_balance = str(Decimal(balance_before) + Decimal("950.00"))
                wallet_ok = balance_after == expected_balance
                log_test(7, f"Wallet credited EXACTLY 950.00 (not 1000)", wallet_ok,
                        f"Before: {balance_before}, After: {balance_after}, Expected: {expected_balance}")
            
            # Check consistency
            consistency = get_wallet_consistency(u3_token)
            if consistency:
                consistent = consistency.get("consistent")
                log_test(7, "Wallet consistency maintained", consistent == True,
                        f"consistent={consistent}")
        else:
            log_test(7, "POST /api/admin/deposits/{id}/approve with override", False,
                    f"Status {resp_approve.status_code}")
    else:
        log_test(7, "Create pending deposit for override test", False,
                f"Status {resp.status_code}")

print()

# ============================================================================
# SCENARIO 8: IDEMPOTENT APPROVE (never double-credit)
# ============================================================================
print("SCENARIO 8: IDEMPOTENT APPROVE (never double-credit)")
print("-" * 80)

# Create a fresh user with a pending deposit
u4_email = f"idempotent_user_{uuid.uuid4().hex[:8]}@test.com"
u4_token = register_user(u4_email, name="Idempotent User")

if u4_token and admin_token:
    # Create a pending deposit
    unique_hash = f"IDEMP{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u4_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "600",
                            "tx_hash": unique_hash
                        })
    
    if resp.status_code == 201:
        deposit = resp.json()
        deposit_id = deposit.get("id")
        
        # Approve once
        resp_approve1 = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                                     headers={"Authorization": f"Bearer {admin_token}"},
                                     json={})
        
        if resp_approve1.status_code == 200:
            # Get wallet balance after first approval
            wallet_after_first = get_wallet(u4_token)
            balance_after_first = wallet_after_first.get("available_balance", "0.00") if wallet_after_first else "0.00"
            
            # Get transaction count
            transactions_after_first = get_transactions(u4_token)
            deposit_txs_first = [t for t in transactions_after_first if t.get("type") == "DEPOSIT" 
                                and t.get("ref_id") == deposit_id] if transactions_after_first else []
            count_first = len(deposit_txs_first)
            
            # Approve AGAIN (idempotent)
            resp_approve2 = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                                         headers={"Authorization": f"Bearer {admin_token}"},
                                         json={})
            
            # Should not return 500 error
            no_error = resp_approve2.status_code != 500
            log_test(8, "Second approve does not return 500 error", no_error,
                    f"Status: {resp_approve2.status_code}")
            
            # Get wallet balance after second approval
            wallet_after_second = get_wallet(u4_token)
            balance_after_second = wallet_after_second.get("available_balance", "0.00") if wallet_after_second else "0.00"
            
            # Wallet should be UNCHANGED
            wallet_unchanged = balance_after_first == balance_after_second
            log_test(8, "CRITICAL: Wallet unchanged after second approve", wallet_unchanged,
                    f"After 1st: {balance_after_first}, After 2nd: {balance_after_second}")
            
            # Get transaction count after second approval
            transactions_after_second = get_transactions(u4_token)
            deposit_txs_second = [t for t in transactions_after_second if t.get("type") == "DEPOSIT" 
                                 and t.get("ref_id") == deposit_id] if transactions_after_second else []
            count_second = len(deposit_txs_second)
            
            # Should still be exactly ONE DEPOSIT ledger entry
            one_entry = count_second == 1
            log_test(8, "CRITICAL: Exactly ONE DEPOSIT ledger entry (not two)", one_entry,
                    f"After 1st: {count_first} entries, After 2nd: {count_second} entries")
        else:
            log_test(8, "First approve", False, f"Status {resp_approve1.status_code}")
    else:
        log_test(8, "Create pending deposit for idempotency test", False,
                f"Status {resp.status_code}")

print()

# ============================================================================
# SCENARIO 9: REJECT (no credit)
# ============================================================================
print("SCENARIO 9: REJECT (no credit)")
print("-" * 80)

# Create a fresh user with a pending deposit
u5_email = f"reject_user_{uuid.uuid4().hex[:8]}@test.com"
u5_token = register_user(u5_email, name="Reject User")

if u5_token and admin_token:
    # Create a pending deposit
    unique_hash = f"REJECT{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u5_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "400",
                            "tx_hash": unique_hash
                        })
    
    if resp.status_code == 201:
        deposit = resp.json()
        deposit_id = deposit.get("id")
        
        # Get wallet balance before rejection
        wallet_before = get_wallet(u5_token)
        balance_before = wallet_before.get("available_balance", "0.00") if wallet_before else "0.00"
        
        # Reject the deposit
        resp_reject = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/reject",
                                   headers={"Authorization": f"Bearer {admin_token}"},
                                   json={"note": "hash not found"})
        
        if resp_reject.status_code == 200:
            rejected_deposit = resp_reject.json()
            
            # Check status is "rejected"
            status_ok = rejected_deposit.get("status") == "rejected"
            log_test(9, "Deposit status is 'rejected'", status_ok,
                    f"Expected 'rejected', got '{rejected_deposit.get('status')}'")
            
            # CRITICAL: Check wallet balance UNCHANGED (no credit)
            wallet_after = get_wallet(u5_token)
            balance_after = wallet_after.get("available_balance", "0.00") if wallet_after else "0.00"
            wallet_unchanged = balance_before == balance_after
            log_test(9, "CRITICAL: Wallet UNCHANGED (no credit)", wallet_unchanged,
                    f"Before: {balance_before}, After: {balance_after}")
            
            # Check NO DEPOSIT ledger entry created
            transactions = get_transactions(u5_token)
            deposit_txs = [t for t in transactions if t.get("type") == "DEPOSIT" 
                          and t.get("ref_id") == deposit_id] if transactions else []
            no_deposit_entry = len(deposit_txs) == 0
            log_test(9, "CRITICAL: NO DEPOSIT ledger entry created", no_deposit_entry,
                    f"Found {len(deposit_txs)} DEPOSIT entries (expected 0)")
            
            # Check user notification
            notifications = get_notifications(u5_token)
            if notifications:
                notif = next((n for n in notifications if n.get("type") == "deposit_rejected"), None)
                if notif:
                    title_ok = notif.get("title") == "Deposit rejected"
                    log_test(9, "User receives 'Deposit rejected' notification", title_ok,
                            f"Title: {notif.get('title')}")
                else:
                    log_test(9, "User receives notification", False, "No deposit_rejected notification found")
            
            # Try to approve a rejected deposit (should fail with 409)
            resp_approve = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                                        headers={"Authorization": f"Bearer {admin_token}"},
                                        json={})
            
            approve_rejected_blocked = resp_approve.status_code == 409
            detail = resp_approve.json().get("detail", {}) if resp_approve.status_code == 409 else {}
            code_ok = detail.get("code") == "already_rejected" if isinstance(detail, dict) else False
            
            log_test(9, "Approving rejected deposit returns 409", approve_rejected_blocked,
                    f"Expected 409, got {resp_approve.status_code}")
            log_test(9, "Error code is 'already_rejected'", code_ok,
                    f"Expected 'already_rejected', got '{detail.get('code') if isinstance(detail, dict) else detail}'")
        else:
            log_test(9, "POST /api/admin/deposits/{id}/reject", False,
                    f"Status {resp_reject.status_code}")
    else:
        log_test(9, "Create pending deposit for rejection test", False,
                f"Status {resp.status_code}")

# Test rejecting an approved deposit
if u3_token and admin_token:
    # u3 has an approved deposit from scenario 6
    # Create a new pending deposit and approve it
    unique_hash = f"APPREJ{uuid.uuid4().hex[:16].upper()}"
    resp = requests.post(f"{BASE_URL}/deposits",
                        headers={"Authorization": f"Bearer {u3_token}"},
                        json={
                            "network": "TRC20",
                            "amount": "350",
                            "tx_hash": unique_hash
                        })
    
    if resp.status_code == 201:
        deposit = resp.json()
        deposit_id = deposit.get("id")
        
        # Approve it
        resp_approve = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/approve",
                                    headers={"Authorization": f"Bearer {admin_token}"},
                                    json={})
        
        if resp_approve.status_code == 200:
            # Try to reject the approved deposit
            resp_reject = requests.post(f"{BASE_URL}/admin/deposits/{deposit_id}/reject",
                                       headers={"Authorization": f"Bearer {admin_token}"},
                                       json={"note": "test"})
            
            reject_approved_blocked = resp_reject.status_code == 409
            detail = resp_reject.json().get("detail", {}) if resp_reject.status_code == 409 else {}
            code_ok = detail.get("code") == "already_approved" if isinstance(detail, dict) else False
            
            log_test(9, "Rejecting approved deposit returns 409", reject_approved_blocked,
                    f"Expected 409, got {resp_reject.status_code}")
            log_test(9, "Error code is 'already_approved'", code_ok,
                    f"Expected 'already_approved', got '{detail.get('code') if isinstance(detail, dict) else detail}'")

print()

# ============================================================================
# SCENARIO 10: ADMIN ADDRESS SETTINGS
# ============================================================================
print("SCENARIO 10: ADMIN ADDRESS SETTINGS")
print("-" * 80)

if admin_token:
    # Set deposit addresses
    test_trc20 = "TTestTRCaddr1111111111111111111111"
    test_bep20 = "0xTestBEPaddr00000000000000000000000000000000"
    
    resp = requests.put(f"{BASE_URL}/admin/settings/deposit",
                       headers={"Authorization": f"Bearer {admin_token}"},
                       json={
                           "trc20": test_trc20,
                           "bep20": test_bep20
                       })
    
    if resp.status_code == 200:
        config = resp.json()
        
        # Check addresses updated
        addresses = config.get("addresses", {})
        trc20_ok = addresses.get("TRC20") == test_trc20
        bep20_ok = addresses.get("BEP20") == test_bep20
        
        log_test(10, "TRC20 address updated", trc20_ok,
                f"Expected '{test_trc20}', got '{addresses.get('TRC20')}'")
        log_test(10, "BEP20 address updated", bep20_ok,
                f"Expected '{test_bep20}', got '{addresses.get('BEP20')}'")
        
        # Check configured is true
        configured = config.get("configured")
        configured_ok = configured == True
        log_test(10, "configured is true", configured_ok,
                f"Expected True, got {configured}")
        
        # Verify from user endpoint
        if u1_token:
            resp_user = requests.get(f"{BASE_URL}/deposits/config",
                                    headers={"Authorization": f"Bearer {u1_token}"})
            if resp_user.status_code == 200:
                user_config = resp_user.json()
                user_addresses = user_config.get("addresses", {})
                user_trc20_ok = user_addresses.get("TRC20") == test_trc20
                user_bep20_ok = user_addresses.get("BEP20") == test_bep20
                user_configured = user_config.get("configured") == True
                
                log_test(10, "User sees updated TRC20 address", user_trc20_ok,
                        f"Expected '{test_trc20}', got '{user_addresses.get('TRC20')}'")
                log_test(10, "User sees updated BEP20 address", user_bep20_ok,
                        f"Expected '{test_bep20}', got '{user_addresses.get('BEP20')}'")
                log_test(10, "User sees configured=true", user_configured,
                        f"Expected True, got {user_config.get('configured')}")
    else:
        log_test(10, "PUT /api/admin/settings/deposit", False,
                f"Status {resp.status_code}")
    
    # Try to set with empty address (should fail with 422)
    resp_empty = requests.put(f"{BASE_URL}/admin/settings/deposit",
                             headers={"Authorization": f"Bearer {admin_token}"},
                             json={
                                 "trc20": "",
                                 "bep20": test_bep20
                             })
    
    empty_rejected = resp_empty.status_code == 422
    log_test(10, "Empty address rejected with 422", empty_rejected,
            f"Expected 422, got {resp_empty.status_code}")

print()

# ============================================================================
# SCENARIO 11: AUTH
# ============================================================================
print("SCENARIO 11: AUTH")
print("-" * 80)

if u1_token and admin_token:
    # User token on admin endpoint -> 403
    resp = requests.get(f"{BASE_URL}/admin/deposits",
                       headers={"Authorization": f"Bearer {u1_token}"})
    
    user_on_admin_blocked = resp.status_code == 403
    log_test(11, "User token on /api/admin/deposits returns 403", user_on_admin_blocked,
            f"Expected 403, got {resp.status_code}")
    
    # No token on admin endpoint -> 401
    resp = requests.get(f"{BASE_URL}/admin/deposits")
    
    no_token_admin = resp.status_code == 401
    log_test(11, "No token on /api/admin/deposits returns 401", no_token_admin,
            f"Expected 401, got {resp.status_code}")
    
    # No token on user deposit endpoint -> 401
    resp = requests.post(f"{BASE_URL}/deposits",
                        json={
                            "network": "TRC20",
                            "amount": "500",
                            "tx_hash": "TESTHASH12345678"
                        })
    
    no_token_user = resp.status_code == 401
    log_test(11, "No token on POST /api/deposits returns 401", no_token_user,
            f"Expected 401, got {resp.status_code}")

print()

# ============================================================================
# SCENARIO 12: DECIMALS
# ============================================================================
print("SCENARIO 12: DECIMALS - all money is plain 2dp strings")
print("-" * 80)

# Check various endpoints for decimal format
if u3_token:  # u3 has approved deposits and wallet balance
    # Check deposit response
    resp = requests.get(f"{BASE_URL}/deposits", headers={"Authorization": f"Bearer {u3_token}"})
    if resp.status_code == 200:
        deposits = resp.json()
        if deposits:
            deposit = deposits[0]
            amount = deposit.get("amount")
            approved_amount = deposit.get("approved_amount")
            
            # Check no Decimal128 leakage
            amount_ok = isinstance(amount, str) and not isinstance(amount, dict)
            log_test(12, "Deposit amount is plain string (no Decimal128)", amount_ok,
                    f"Type: {type(amount).__name__}, Value: {amount}")
            
            if approved_amount:
                approved_ok = isinstance(approved_amount, str) and not isinstance(approved_amount, dict)
                log_test(12, "Approved amount is plain string (no Decimal128)", approved_ok,
                        f"Type: {type(approved_amount).__name__}, Value: {approved_amount}")
    
    # Check wallet response
    wallet = get_wallet(u3_token)
    if wallet:
        available = wallet.get("available_balance")
        locked = wallet.get("locked_investment")
        total = wallet.get("total_portfolio")
        
        available_ok = isinstance(available, str) and not isinstance(available, dict)
        log_test(12, "Wallet available_balance is plain string", available_ok,
                f"Type: {type(available).__name__}, Value: {available}")
        
        locked_ok = isinstance(locked, str) and not isinstance(locked, dict)
        log_test(12, "Wallet locked_investment is plain string", locked_ok,
                f"Type: {type(locked).__name__}, Value: {locked}")
        
        total_ok = isinstance(total, str) and not isinstance(total, dict)
        log_test(12, "Wallet total_portfolio is plain string", total_ok,
                f"Type: {type(total).__name__}, Value: {total}")
    
    # Check transaction response
    transactions = get_transactions(u3_token)
    if transactions:
        tx = transactions[0]
        amount = tx.get("amount")
        balance_after = tx.get("balance_after")
        
        amount_ok = isinstance(amount, str) and not isinstance(amount, dict)
        log_test(12, "Transaction amount is plain string", amount_ok,
                f"Type: {type(amount).__name__}, Value: {amount}")
        
        balance_ok = isinstance(balance_after, str) and not isinstance(balance_after, dict)
        log_test(12, "Transaction balance_after is plain string", balance_ok,
                f"Type: {type(balance_after).__name__}, Value: {balance_after}")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total tests: {tests_passed + tests_failed}")
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"Success rate: {(tests_passed / (tests_passed + tests_failed) * 100):.1f}%")
print()

# Group results by scenario
scenarios = {}
for result in test_results:
    scenario = result["scenario"]
    if scenario not in scenarios:
        scenarios[scenario] = {"passed": 0, "failed": 0, "tests": []}
    if result["passed"]:
        scenarios[scenario]["passed"] += 1
    else:
        scenarios[scenario]["failed"] += 1
    scenarios[scenario]["tests"].append(result)

print("RESULTS BY SCENARIO:")
print("-" * 80)
for scenario in sorted(scenarios.keys()):
    data = scenarios[scenario]
    status = "✅ PASS" if data["failed"] == 0 else "❌ FAIL"
    print(f"{status} Scenario {scenario}: {data['passed']}/{data['passed'] + data['failed']} tests passed")
    if data["failed"] > 0:
        print("  Failed tests:")
        for test in data["tests"]:
            if not test["passed"]:
                print(f"    - {test['test']}: {test['details']}")

print()
print("=" * 80)
