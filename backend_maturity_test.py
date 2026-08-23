#!/usr/bin/env python3
"""
EasyX Automatic Maturity Engine - Backend Testing Suite

Tests all 7 critical scenarios:
1. PAYOUT CORRECTNESS
2. IDEMPOTENCY - NEVER PAY TWICE
3. CONCURRENCY - NO DOUBLE PAYOUT
4. AUTOMATIC SWEEP + DUE FILTERING
5. NOTIFICATIONS API
6. AUTH
7. DECIMALS

Base URL from frontend/.env REACT_APP_BACKEND_URL
Admin: admin@easyx.com / Admin@Easyx2026
"""
import asyncio
import os
import sys
import time
import uuid
from decimal import Decimal

import httpx

# Base URL from environment or default
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://easyx-loader.preview.emergentagent.com")
API_BASE = f"{BASE_URL}/api"

# Admin credentials
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test results
results = {
    "passed": 0,
    "failed": 0,
    "errors": [],
}


def log(msg):
    print(f"[TEST] {msg}")


def assert_eq(actual, expected, msg):
    if actual != expected:
        err = f"❌ FAIL: {msg}\n   Expected: {expected}\n   Actual: {actual}"
        results["errors"].append(err)
        results["failed"] += 1
        print(err)
        return False
    results["passed"] += 1
    print(f"✅ PASS: {msg}")
    return True


def assert_true(condition, msg):
    if not condition:
        err = f"❌ FAIL: {msg}"
        results["errors"].append(err)
        results["failed"] += 1
        print(err)
        return False
    results["passed"] += 1
    print(f"✅ PASS: {msg}")
    return True


def assert_in(item, container, msg):
    if item not in container:
        err = f"❌ FAIL: {msg}\n   '{item}' not in {container}"
        results["errors"].append(err)
        results["failed"] += 1
        print(err)
        return False
    results["passed"] += 1
    print(f"✅ PASS: {msg}")
    return True


def is_decimal_string(value):
    """Check if value is a plain 2dp decimal string like '480.00'"""
    if not isinstance(value, str):
        return False
    try:
        d = Decimal(value)
        # Check it has exactly 2 decimal places
        return '.' in value and len(value.split('.')[1]) == 2
    except (ValueError, IndexError):
        return False


async def register_user(client, email, phone=None, password="TestPass123!"):
    """Register a new user and return access token"""
    if phone is None:
        # Generate valid phone number with only digits
        phone = f"+1555{uuid.uuid4().int % 10000000:07d}"
    resp = await client.post(f"{API_BASE}/auth/register", json={
        "name": f"Test User {uuid.uuid4().hex[:6]}",
        "email": email,
        "phone": phone,
        "password": password,
    })
    if resp.status_code != 201:
        log(f"Register failed: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("access_token")


async def admin_login(client):
    """Login as admin and return access token"""
    resp = await client.post(f"{API_BASE}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    if resp.status_code != 200:
        log(f"Admin login failed: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("access_token")


async def admin_credit_wallet(client, admin_token, user_id, amount):
    """Admin credits user wallet"""
    resp = await client.post(
        f"{API_BASE}/admin/wallet/adjust",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": user_id,
            "amount": str(amount),
            "direction": "credit",
            "idempotency_key": f"credit-{uuid.uuid4()}",
        }
    )
    return resp


async def buy_investment(client, user_token, plan_key, idempotency_key=None):
    """Buy an investment plan"""
    payload = {"plan_key": plan_key}
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    resp = await client.post(
        f"{API_BASE}/investments",
        headers={"Authorization": f"Bearer {user_token}"},
        json=payload
    )
    return resp


async def get_wallet(client, user_token):
    """Get wallet summary"""
    resp = await client.get(
        f"{API_BASE}/wallet",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


async def get_transactions(client, user_token):
    """Get wallet transactions"""
    resp = await client.get(
        f"{API_BASE}/transactions",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


async def get_wallet_consistency(client, user_token):
    """Check wallet consistency"""
    resp = await client.get(
        f"{API_BASE}/wallet/consistency",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


async def force_mature_investment(client, admin_token, inv_id):
    """Force-mature a specific investment"""
    resp = await client.post(
        f"{API_BASE}/admin/investments/{inv_id}/mature",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return resp


async def backdate_investment(client, admin_token, inv_id, seconds_ago):
    """Backdate an investment's maturity_at"""
    resp = await client.post(
        f"{API_BASE}/admin/investments/{inv_id}/backdate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"seconds_ago": seconds_ago}
    )
    return resp


async def run_maturity_sweep(client, admin_token):
    """Run the automatic maturity sweep"""
    resp = await client.post(
        f"{API_BASE}/admin/maturity/run",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return resp


async def get_notifications(client, user_token, unread_only=False):
    """Get user notifications"""
    url = f"{API_BASE}/notifications"
    if unread_only:
        url += "?unread_only=true"
    resp = await client.get(url, headers={"Authorization": f"Bearer {user_token}"})
    return resp


async def get_unread_count(client, user_token):
    """Get unread notification count"""
    resp = await client.get(
        f"{API_BASE}/notifications/unread-count",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


async def mark_notification_read(client, user_token, notif_id):
    """Mark a notification as read"""
    resp = await client.post(
        f"{API_BASE}/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


async def mark_all_notifications_read(client, user_token):
    """Mark all notifications as read"""
    resp = await client.post(
        f"{API_BASE}/notifications/read-all",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    return resp


async def get_user_id(client, user_token):
    """Get current user ID"""
    resp = await client.get(
        f"{API_BASE}/auth/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    if resp.status_code == 200:
        return resp.json().get("id")
    return None


# ============================================================================
# TEST SCENARIO 1: PAYOUT CORRECTNESS
# ============================================================================
async def test_payout_correctness():
    log("\n" + "="*80)
    log("TEST SCENARIO 1: PAYOUT CORRECTNESS")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register fresh user
        email = f"payout-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        user_id = await get_user_id(client, user_token)
        assert_true(user_id is not None, "Got user ID")
        
        # Admin login
        admin_token = await admin_login(client)
        assert_true(admin_token is not None, "Admin logged in")
        
        # Admin credit 2000
        resp = await admin_credit_wallet(client, admin_token, user_id, 2000)
        assert_eq(resp.status_code, 200, "Admin credited 2000 to user wallet")
        
        # Buy SILVER (300)
        resp = await buy_investment(client, user_token, "silver", f"payout-test-{uuid.uuid4()}")
        assert_eq(resp.status_code, 201, "Bought SILVER investment")
        inv_data = resp.json()
        inv_id = inv_data.get("id")
        assert_true(inv_id is not None, "Got investment ID")
        
        # Record wallet BEFORE maturity
        resp = await get_wallet(client, user_token)
        assert_eq(resp.status_code, 200, "Got wallet before maturity")
        wallet_before = resp.json()
        log(f"Wallet BEFORE maturity: {wallet_before}")
        
        assert_eq(wallet_before["available_balance"], "1700.00", "Available balance = 1700.00 (2000 - 300)")
        assert_eq(wallet_before["locked_investment"], "300.00", "Locked investment = 300.00")
        assert_eq(wallet_before["total_earned"], "0.00", "Total earned = 0.00 before maturity")
        
        # Force-mature the investment
        resp = await force_mature_investment(client, admin_token, inv_id)
        assert_eq(resp.status_code, 200, "Force-mature investment succeeded")
        mature_data = resp.json()
        log(f"Force-mature response: {mature_data}")
        
        assert_eq(mature_data["performed_payout"], True, "performed_payout = true")
        assert_eq(mature_data["investment"]["status"], "matured", "Investment status = matured")
        assert_true(mature_data["investment"]["matured_at"] is not None, "matured_at is set")
        
        # Get wallet AFTER maturity
        resp = await get_wallet(client, user_token)
        assert_eq(resp.status_code, 200, "Got wallet after maturity")
        wallet_after = resp.json()
        log(f"Wallet AFTER maturity: {wallet_after}")
        
        # Expected: available = 1700 + 480 = 2180, locked = 0, total_earned = 180
        assert_eq(wallet_after["available_balance"], "2180.00", "Available balance = 2180.00 (1700 + 480)")
        assert_eq(wallet_after["locked_investment"], "0.00", "Locked investment = 0.00 (investment no longer active)")
        assert_eq(wallet_after["total_earned"], "180.00", "Total earned = 180.00 (profit)")
        
        # Get transactions - should have TWO new credit entries
        resp = await get_transactions(client, user_token)
        assert_eq(resp.status_code, 200, "Got transactions")
        txs = resp.json()
        
        # Find INVESTMENT_MATURITY and PROFIT transactions
        maturity_txs = [t for t in txs if t["type"] == "INVESTMENT_MATURITY"]
        profit_txs = [t for t in txs if t["type"] == "PROFIT"]
        
        assert_eq(len(maturity_txs), 1, "Exactly ONE INVESTMENT_MATURITY transaction")
        assert_eq(len(profit_txs), 1, "Exactly ONE PROFIT transaction")
        
        if maturity_txs:
            assert_eq(maturity_txs[0]["amount"], "300.00", "INVESTMENT_MATURITY amount = 300.00")
            assert_eq(maturity_txs[0]["direction"], "credit", "INVESTMENT_MATURITY is credit")
        
        if profit_txs:
            assert_eq(profit_txs[0]["amount"], "180.00", "PROFIT amount = 180.00")
            assert_eq(profit_txs[0]["direction"], "credit", "PROFIT is credit")
        
        # Check wallet consistency
        resp = await get_wallet_consistency(client, user_token)
        assert_eq(resp.status_code, 200, "Got wallet consistency")
        consistency = resp.json()
        assert_eq(consistency["consistent"], True, "Wallet is consistent")
        
        log("✅ SCENARIO 1 COMPLETE: Payout correctness verified")
        return inv_id, user_token, admin_token


# ============================================================================
# TEST SCENARIO 2: IDEMPOTENCY - NEVER PAY TWICE
# ============================================================================
async def test_idempotency():
    log("\n" + "="*80)
    log("TEST SCENARIO 2: IDEMPOTENCY - NEVER PAY TWICE (CRITICAL)")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register fresh user
        email = f"idempotency-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        user_id = await get_user_id(client, user_token)
        admin_token = await admin_login(client)
        
        # Admin credit 2000
        await admin_credit_wallet(client, admin_token, user_id, 2000)
        
        # Buy SILVER
        resp = await buy_investment(client, user_token, "silver", f"idempotency-test-{uuid.uuid4()}")
        assert_eq(resp.status_code, 201, "Bought SILVER investment")
        inv_id = resp.json().get("id")
        
        # Force-mature FIRST time
        resp = await force_mature_investment(client, admin_token, inv_id)
        assert_eq(resp.status_code, 200, "First force-mature succeeded")
        first_mature = resp.json()
        assert_eq(first_mature["performed_payout"], True, "First call performed_payout = true")
        
        # Get wallet after first maturity
        resp = await get_wallet(client, user_token)
        wallet_after_first = resp.json()
        log(f"Wallet after FIRST maturity: {wallet_after_first}")
        
        # Get transactions after first maturity
        resp = await get_transactions(client, user_token)
        txs_after_first = resp.json()
        maturity_count_first = len([t for t in txs_after_first if t["type"] == "INVESTMENT_MATURITY"])
        profit_count_first = len([t for t in txs_after_first if t["type"] == "PROFIT"])
        
        log(f"After FIRST maturity: {maturity_count_first} INVESTMENT_MATURITY, {profit_count_first} PROFIT")
        
        # Force-mature SECOND time (SAME investment)
        resp = await force_mature_investment(client, admin_token, inv_id)
        assert_eq(resp.status_code, 200, "Second force-mature succeeded")
        second_mature = resp.json()
        assert_eq(second_mature["performed_payout"], False, "Second call performed_payout = false (CRITICAL)")
        
        # Get wallet after second maturity - should be UNCHANGED
        resp = await get_wallet(client, user_token)
        wallet_after_second = resp.json()
        log(f"Wallet after SECOND maturity: {wallet_after_second}")
        
        assert_eq(wallet_after_second["available_balance"], wallet_after_first["available_balance"], 
                  "Available balance UNCHANGED after second mature call")
        assert_eq(wallet_after_second["total_earned"], wallet_after_first["total_earned"],
                  "Total earned UNCHANGED after second mature call")
        
        # Get transactions after second maturity - should have SAME count
        resp = await get_transactions(client, user_token)
        txs_after_second = resp.json()
        maturity_count_second = len([t for t in txs_after_second if t["type"] == "INVESTMENT_MATURITY"])
        profit_count_second = len([t for t in txs_after_second if t["type"] == "PROFIT"])
        
        log(f"After SECOND maturity: {maturity_count_second} INVESTMENT_MATURITY, {profit_count_second} PROFIT")
        
        assert_eq(maturity_count_second, maturity_count_first, 
                  "INVESTMENT_MATURITY count unchanged (NO new entry created)")
        assert_eq(profit_count_second, profit_count_first,
                  "PROFIT count unchanged (NO new entry created)")
        
        # Check notifications - should have exactly ONE investment_matured notification
        resp = await get_notifications(client, user_token)
        assert_eq(resp.status_code, 200, "Got notifications")
        notifs = resp.json()
        matured_notifs = [n for n in notifs if n["type"] == "investment_matured" and n["investment_id"] == inv_id]
        assert_eq(len(matured_notifs), 1, "Exactly ONE investment_matured notification (deduped)")
        
        # Check consistency
        resp = await get_wallet_consistency(client, user_token)
        consistency = resp.json()
        assert_eq(consistency["consistent"], True, "Wallet still consistent after idempotency test")
        
        log("✅ SCENARIO 2 COMPLETE: Idempotency verified - NO double payout")


# ============================================================================
# TEST SCENARIO 3: CONCURRENCY - NO DOUBLE PAYOUT
# ============================================================================
async def test_concurrency():
    log("\n" + "="*80)
    log("TEST SCENARIO 3: CONCURRENCY - NO DOUBLE PAYOUT (CRITICAL)")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register fresh user
        email = f"concurrency-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        user_id = await get_user_id(client, user_token)
        admin_token = await admin_login(client)
        
        # Admin credit 3000
        await admin_credit_wallet(client, admin_token, user_id, 3000)
        
        # Buy GOLD (1000)
        resp = await buy_investment(client, user_token, "gold", f"concurrency-test-{uuid.uuid4()}")
        assert_eq(resp.status_code, 201, "Bought GOLD investment")
        inv_id = resp.json().get("id")
        
        # Backdate it (120 seconds ago)
        resp = await backdate_investment(client, admin_token, inv_id, 120)
        assert_eq(resp.status_code, 200, "Backdated investment")
        
        # Get wallet BEFORE concurrent maturity
        resp = await get_wallet(client, user_token)
        wallet_before = resp.json()
        log(f"Wallet BEFORE concurrent maturity: {wallet_before}")
        
        # Fire ~10 CONCURRENT requests: mix of maturity/run and force-mature
        log("Firing 10 concurrent maturity requests...")
        tasks = []
        for i in range(5):
            tasks.append(run_maturity_sweep(client, admin_token))
        for i in range(5):
            tasks.append(force_mature_investment(client, admin_token, inv_id))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check responses - should have no 500 errors
        status_codes = []
        for r in responses:
            if isinstance(r, Exception):
                log(f"Exception during concurrent request: {r}")
                results["failed"] += 1
            else:
                status_codes.append(r.status_code)
        
        error_count = sum(1 for code in status_codes if code >= 500)
        assert_eq(error_count, 0, "NO 500 errors during concurrent maturity requests")
        
        # Get wallet AFTER concurrent maturity
        resp = await get_wallet(client, user_token)
        wallet_after = resp.json()
        log(f"Wallet AFTER concurrent maturity: {wallet_after}")
        
        # Expected: starting balance was 2000 (after buying gold), should increase by 1600 (1000 principal + 600 profit)
        # Final available = 2000 + 1600 = 3600
        assert_eq(wallet_after["available_balance"], "3600.00", 
                  "Available balance = 3600.00 (2000 + 1600, paid EXACTLY ONCE)")
        assert_eq(wallet_after["locked_investment"], "0.00", "Locked investment = 0.00")
        assert_eq(wallet_after["total_earned"], "600.00", "Total earned = 600.00 (profit paid ONCE)")
        
        # Get transactions - should have EXACTLY ONE INVESTMENT_MATURITY and ONE PROFIT
        resp = await get_transactions(client, user_token)
        txs = resp.json()
        
        maturity_txs = [t for t in txs if t["type"] == "INVESTMENT_MATURITY" and t["ref_id"] == inv_id]
        profit_txs = [t for t in txs if t["type"] == "PROFIT" and t["ref_id"] == inv_id]
        
        assert_eq(len(maturity_txs), 1, "Exactly ONE INVESTMENT_MATURITY credit (NO double payout)")
        assert_eq(len(profit_txs), 1, "Exactly ONE PROFIT credit (NO double payout)")
        
        if maturity_txs:
            assert_eq(maturity_txs[0]["amount"], "1000.00", "INVESTMENT_MATURITY amount = 1000.00")
        if profit_txs:
            assert_eq(profit_txs[0]["amount"], "600.00", "PROFIT amount = 600.00")
        
        # Check notifications - exactly ONE investment_matured notification
        resp = await get_notifications(client, user_token)
        notifs = resp.json()
        matured_notifs = [n for n in notifs if n["type"] == "investment_matured" and n["investment_id"] == inv_id]
        assert_eq(len(matured_notifs), 1, "Exactly ONE investment_matured notification (deduped under concurrency)")
        
        # Check consistency
        resp = await get_wallet_consistency(client, user_token)
        consistency = resp.json()
        assert_eq(consistency["consistent"], True, "Wallet consistent after concurrent maturity")
        
        log("✅ SCENARIO 3 COMPLETE: Concurrency verified - NO double payout under race conditions")


# ============================================================================
# TEST SCENARIO 4: AUTOMATIC SWEEP + DUE FILTERING
# ============================================================================
async def test_automatic_sweep():
    log("\n" + "="*80)
    log("TEST SCENARIO 4: AUTOMATIC SWEEP + DUE FILTERING")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register fresh user
        email = f"sweep-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        user_id = await get_user_id(client, user_token)
        admin_token = await admin_login(client)
        
        # Admin credit 6000
        await admin_credit_wallet(client, admin_token, user_id, 6000)
        
        # Buy PLATINUM (5000) - maturity_at ~60 days in FUTURE
        resp = await buy_investment(client, user_token, "platinum", f"sweep-test-{uuid.uuid4()}")
        assert_eq(resp.status_code, 201, "Bought PLATINUM investment")
        inv_data = resp.json()
        inv_id = inv_data.get("id")
        
        log(f"PLATINUM investment created with maturity_at in FUTURE: {inv_data.get('maturity_at')}")
        
        # Get wallet before sweep
        resp = await get_wallet(client, user_token)
        wallet_before_sweep = resp.json()
        log(f"Wallet BEFORE sweep: {wallet_before_sweep}")
        
        # Run maturity sweep - should NOT mature the platinum (not yet due)
        resp = await run_maturity_sweep(client, admin_token)
        assert_eq(resp.status_code, 200, "Maturity sweep ran")
        sweep_result = resp.json()
        log(f"Sweep result (before backdate): {sweep_result}")
        
        # Get wallet after sweep - should be UNCHANGED
        resp = await get_wallet(client, user_token)
        wallet_after_sweep = resp.json()
        log(f"Wallet AFTER sweep (before backdate): {wallet_after_sweep}")
        
        assert_eq(wallet_after_sweep["available_balance"], wallet_before_sweep["available_balance"],
                  "Available balance UNCHANGED (future investment not matured)")
        assert_eq(wallet_after_sweep["locked_investment"], "5000.00",
                  "Locked investment still 5000.00 (investment still active)")
        
        # Now backdate the platinum (5 seconds ago)
        resp = await backdate_investment(client, admin_token, inv_id, 5)
        assert_eq(resp.status_code, 200, "Backdated platinum investment")
        backdate_result = resp.json()
        log(f"Backdated maturity_at: {backdate_result.get('maturity_at')}")
        
        # Run maturity sweep again - NOW it should mature
        resp = await run_maturity_sweep(client, admin_token)
        assert_eq(resp.status_code, 200, "Maturity sweep ran after backdate")
        sweep_result2 = resp.json()
        log(f"Sweep result (after backdate): {sweep_result2}")
        
        # The sweep should have matured at least 1 investment (could be more if other tests left investments)
        # We'll verify by checking the specific investment status
        
        # Get wallet after second sweep - should now show maturity payout
        resp = await get_wallet(client, user_token)
        wallet_after_backdate = resp.json()
        log(f"Wallet AFTER sweep (after backdate): {wallet_after_backdate}")
        
        # Expected: available = 1000 (before) + 10000 (5000 principal + 5000 profit) = 11000
        # Platinum has 100% profit (5000 -> 10000)
        assert_eq(wallet_after_backdate["available_balance"], "11000.00",
                  "Available balance = 11000.00 (1000 + 10000 payout)")
        assert_eq(wallet_after_backdate["locked_investment"], "0.00",
                  "Locked investment = 0.00 (platinum matured)")
        assert_eq(wallet_after_backdate["total_earned"], "5000.00",
                  "Total earned = 5000.00 (platinum profit)")
        
        # Check consistency
        resp = await get_wallet_consistency(client, user_token)
        consistency = resp.json()
        assert_eq(consistency["consistent"], True, "Wallet consistent after automatic sweep")
        
        log("✅ SCENARIO 4 COMPLETE: Automatic sweep + due filtering verified")


# ============================================================================
# TEST SCENARIO 5: NOTIFICATIONS API
# ============================================================================
async def test_notifications_api():
    log("\n" + "="*80)
    log("TEST SCENARIO 5: NOTIFICATIONS API")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register fresh user
        email = f"notif-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        user_id = await get_user_id(client, user_token)
        admin_token = await admin_login(client)
        
        # Admin credit 2000
        await admin_credit_wallet(client, admin_token, user_id, 2000)
        
        # Buy SILVER and force-mature to generate notification
        resp = await buy_investment(client, user_token, "silver", f"notif-test-{uuid.uuid4()}")
        inv_id = resp.json().get("id")
        
        resp = await force_mature_investment(client, admin_token, inv_id)
        assert_eq(resp.status_code, 200, "Investment matured")
        
        # Test GET /api/notifications
        resp = await get_notifications(client, user_token)
        assert_eq(resp.status_code, 200, "GET /api/notifications succeeded")
        notifs = resp.json()
        assert_true(len(notifs) >= 1, "At least 1 notification returned")
        
        # Find the investment_matured notification
        matured_notif = None
        for n in notifs:
            if n["type"] == "investment_matured" and n["investment_id"] == inv_id:
                matured_notif = n
                break
        
        assert_true(matured_notif is not None, "Found investment_matured notification")
        assert_true("Investment matured" in matured_notif["title"], 
                    "Notification title contains 'Investment matured'")
        assert_true("USDT" in matured_notif["body"],
                    "Notification body mentions USDT amount")
        
        log(f"Notification: {matured_notif}")
        
        # Test GET /api/notifications/unread-count
        resp = await get_unread_count(client, user_token)
        assert_eq(resp.status_code, 200, "GET /api/notifications/unread-count succeeded")
        unread_data = resp.json()
        unread_count_before = unread_data.get("count", 0)
        assert_true(unread_count_before >= 1, f"Unread count >= 1 (got {unread_count_before})")
        
        # Test POST /api/notifications/{id}/read
        notif_id = matured_notif["id"]
        resp = await mark_notification_read(client, user_token, notif_id)
        assert_eq(resp.status_code, 200, "POST /api/notifications/{id}/read succeeded")
        read_result = resp.json()
        assert_eq(read_result.get("ok"), True, "Notification marked as read")
        
        # Check unread count decreased
        resp = await get_unread_count(client, user_token)
        unread_data = resp.json()
        unread_count_after = unread_data.get("count", 0)
        assert_true(unread_count_after < unread_count_before,
                    f"Unread count decreased ({unread_count_before} -> {unread_count_after})")
        
        # Test GET /api/notifications?unread_only=true
        resp = await get_notifications(client, user_token, unread_only=True)
        assert_eq(resp.status_code, 200, "GET /api/notifications?unread_only=true succeeded")
        unread_notifs = resp.json()
        
        # The notification we just marked as read should NOT be in unread list
        unread_ids = [n["id"] for n in unread_notifs]
        assert_true(notif_id not in unread_ids, "Read notification excluded from unread_only list")
        
        # Test POST /api/notifications/read-all
        resp = await mark_all_notifications_read(client, user_token)
        assert_eq(resp.status_code, 200, "POST /api/notifications/read-all succeeded")
        read_all_result = resp.json()
        log(f"Read-all result: {read_all_result}")
        
        # Check unread count is now 0
        resp = await get_unread_count(client, user_token)
        unread_data = resp.json()
        unread_count_final = unread_data.get("count", 0)
        assert_eq(unread_count_final, 0, "Unread count = 0 after read-all")
        
        log("✅ SCENARIO 5 COMPLETE: Notifications API verified")


# ============================================================================
# TEST SCENARIO 6: AUTH
# ============================================================================
async def test_auth():
    log("\n" + "="*80)
    log("TEST SCENARIO 6: AUTH")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register normal user
        email = f"auth-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        admin_token = await admin_login(client)
        
        # Test 1: Admin endpoints require admin role
        # Normal user calling admin endpoint should get 403
        resp = await client.post(
            f"{API_BASE}/admin/maturity/run",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert_eq(resp.status_code, 403, "Normal user calling admin endpoint -> 403")
        
        # Test 2: Admin endpoints require authentication
        # No token should get 401
        resp = await client.post(f"{API_BASE}/admin/maturity/run")
        assert_eq(resp.status_code, 401, "Admin endpoint without token -> 401")
        
        # Test 3: User notifications endpoint requires authentication
        resp = await client.get(f"{API_BASE}/notifications")
        assert_eq(resp.status_code, 401, "GET /api/notifications without token -> 401")
        
        # Test 4: Admin can access admin endpoints
        resp = await client.post(
            f"{API_BASE}/admin/maturity/run",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert_true(resp.status_code in [200, 201], "Admin can access admin endpoints")
        
        log("✅ SCENARIO 6 COMPLETE: Auth verified")


# ============================================================================
# TEST SCENARIO 7: DECIMALS
# ============================================================================
async def test_decimals():
    log("\n" + "="*80)
    log("TEST SCENARIO 7: DECIMALS")
    log("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Setup: Register fresh user
        email = f"decimal-test-{uuid.uuid4().hex[:8]}@test.com"
        user_token = await register_user(client, email)
        assert_true(user_token is not None, "User registered successfully")
        
        user_id = await get_user_id(client, user_token)
        admin_token = await admin_login(client)
        
        # Admin credit 2000
        await admin_credit_wallet(client, admin_token, user_id, 2000)
        
        # Buy SILVER and force-mature
        resp = await buy_investment(client, user_token, "silver", f"decimal-test-{uuid.uuid4()}")
        inv_id = resp.json().get("id")
        
        resp = await force_mature_investment(client, admin_token, inv_id)
        assert_eq(resp.status_code, 200, "Investment matured")
        
        # Check wallet response for decimal format
        resp = await get_wallet(client, user_token)
        wallet = resp.json()
        
        assert_true(is_decimal_string(wallet["available_balance"]),
                    f"available_balance is plain 2dp string: {wallet['available_balance']}")
        assert_true(is_decimal_string(wallet["locked_investment"]),
                    f"locked_investment is plain 2dp string: {wallet['locked_investment']}")
        assert_true(is_decimal_string(wallet["total_portfolio"]),
                    f"total_portfolio is plain 2dp string: {wallet['total_portfolio']}")
        assert_true(is_decimal_string(wallet["total_invested"]),
                    f"total_invested is plain 2dp string: {wallet['total_invested']}")
        assert_true(is_decimal_string(wallet["total_earned"]),
                    f"total_earned is plain 2dp string: {wallet['total_earned']}")
        
        # Check transactions for decimal format
        resp = await get_transactions(client, user_token)
        txs = resp.json()
        
        for tx in txs[:3]:  # Check first 3 transactions
            assert_true(is_decimal_string(tx["amount"]),
                        f"Transaction amount is plain 2dp string: {tx['amount']}")
            assert_true(is_decimal_string(tx["balance_after"]),
                        f"Transaction balance_after is plain 2dp string: {tx['balance_after']}")
        
        # Check notifications for decimal format (body should mention amounts)
        resp = await get_notifications(client, user_token)
        notifs = resp.json()
        
        # Just verify no Decimal128 leakage in notification body
        for notif in notifs:
            body = notif.get("body", "")
            assert_true("$numberDecimal" not in body,
                        f"Notification body has no Decimal128 leakage: {body[:50]}...")
        
        log("✅ SCENARIO 7 COMPLETE: All money values are plain 2dp strings, no Decimal128 leakage")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
async def run_all_tests():
    log("="*80)
    log("EasyX AUTOMATIC MATURITY ENGINE - BACKEND TESTING")
    log("="*80)
    log(f"Base URL: {BASE_URL}")
    log(f"API Base: {API_BASE}")
    log("")
    
    try:
        await test_payout_correctness()
        await test_idempotency()
        await test_concurrency()
        await test_automatic_sweep()
        await test_notifications_api()
        await test_auth()
        await test_decimals()
    except Exception as e:
        log(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["failed"] += 1
    
    # Print summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    log(f"✅ PASSED: {results['passed']}")
    log(f"❌ FAILED: {results['failed']}")
    
    if results["errors"]:
        log("\nFAILED TESTS:")
        for err in results["errors"]:
            log(err)
    
    if results["failed"] == 0:
        log("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        log(f"\n⚠️  {results['failed']} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
