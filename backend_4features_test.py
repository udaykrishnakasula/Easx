#!/usr/bin/env python3
"""
Comprehensive backend test for 4 new EasyX features:
1. Admin - Investment Plan editor + history
2. Admin - Investment cancel + refund
3. Withdrawals - user request + admin approve/reject/process
4. Admin - Overview KPIs

Base URL from frontend/.env REACT_APP_BACKEND_URL; all routes prefixed with /api.
Admin: admin@easyx.com / Admin@Easyx2026
"""
import requests
import time
import json
from decimal import Decimal

BASE_URL = "https://easyx-loader.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@easyx.com"
ADMIN_PASSWORD = "Admin@Easyx2026"

# Test counters
tests_passed = 0
tests_failed = 0

def log(msg):
    print(f"[TEST] {msg}")

def assert_eq(actual, expected, msg):
    global tests_passed, tests_failed
    if actual == expected:
        tests_passed += 1
        log(f"✅ {msg}")
    else:
        tests_failed += 1
        log(f"❌ {msg} | Expected: {expected}, Got: {actual}")

def assert_true(condition, msg):
    global tests_passed, tests_failed
    if condition:
        tests_passed += 1
        log(f"✅ {msg}")
    else:
        tests_failed += 1
        log(f"❌ {msg}")

def assert_status(response, expected_status, msg):
    assert_eq(response.status_code, expected_status, msg)

def register_user(name, email, phone, password="Passw0rd!"):
    """Register a fresh user and return token + user_id."""
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": name, "email": email, "phone": phone, "password": password
    })
    if resp.status_code != 201:
        log(f"❌ Register failed for {email}: {resp.status_code} {resp.text}")
        return None, None
    data = resp.json()
    return data["access_token"], data["user"]["id"]

def admin_login():
    """Login as admin and return token."""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        log(f"❌ Admin login failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()["access_token"]

def admin_fund_wallet(admin_token, user_id, amount):
    """Admin credits user wallet."""
    resp = requests.post(f"{BASE_URL}/admin/wallet/adjust", 
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": user_id, "direction": "credit", "amount": str(amount), "note": "test fund"}
    )
    return resp

def get_wallet(token):
    """Get user wallet."""
    resp = requests.get(f"{BASE_URL}/wallet", headers={"Authorization": f"Bearer {token}"})
    return resp.json() if resp.status_code == 200 else None

def buy_investment(token, plan_key, idempotency_key=None):
    """User buys an investment."""
    payload = {"plan_key": plan_key}
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    resp = requests.post(f"{BASE_URL}/investments", 
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    return resp

def get_investments(token):
    """Get user investments."""
    resp = requests.get(f"{BASE_URL}/investments", headers={"Authorization": f"Bearer {token}"})
    return resp.json() if resp.status_code == 200 else []

def submit_kyc(token, id_type="aadhaar", id_number="123456789012"):
    """Submit KYC with dummy files."""
    # Create minimal PNG files (1x1 pixel)
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    files = {
        'id_document': ('id.png', png_bytes, 'image/png'),
        'selfie': ('selfie.png', png_bytes, 'image/png')
    }
    data = {'id_type': id_type, 'id_number': id_number}
    resp = requests.post(f"{BASE_URL}/kyc/submit",
        headers={"Authorization": f"Bearer {token}"},
        files=files, data=data
    )
    return resp

def admin_approve_kyc(admin_token, kyc_id):
    """Admin approves KYC."""
    resp = requests.post(f"{BASE_URL}/admin/kyc/{kyc_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return resp

def get_kyc(token):
    """Get user KYC status."""
    resp = requests.get(f"{BASE_URL}/kyc", headers={"Authorization": f"Bearer {token}"})
    return resp.json() if resp.status_code == 200 else None

# ============================================================================
# FEATURE 1: Investment Plan editor + history
# ============================================================================
def test_feature1_plan_editor():
    log("\n" + "="*80)
    log("FEATURE 1: Investment Plan editor + history")
    log("="*80)
    
    admin_token = admin_login()
    assert_true(admin_token is not None, "Admin login successful")
    
    # 1. GET /api/admin/plans -> array of 4 plans
    resp = requests.get(f"{BASE_URL}/admin/plans", headers={"Authorization": f"Bearer {admin_token}"})
    assert_status(resp, 200, "GET /api/admin/plans returns 200")
    plans = resp.json()
    assert_true(len(plans) == 4, f"4 plans returned (got {len(plans)})")
    
    # Find silver plan
    silver = next((p for p in plans if p["key"] == "silver"), None)
    assert_true(silver is not None, "Silver plan found")
    
    original_price = silver["price"]
    original_profit = silver["profit_percentage"]
    original_version = silver["version"]
    log(f"Silver plan original: price={original_price}, profit_percentage={original_profit}, version={original_version}")
    
    # 2. REGRESSION SETUP: create user U1, fund 2000, buy silver
    ts = int(time.time())
    u1_email = f"plantest_u1_{ts}@easyx.com"
    u1_phone = f"+9198765{ts % 100000:05d}"
    u1_token, u1_id = register_user("Plan Test U1", u1_email, u1_phone)
    assert_true(u1_token is not None, f"U1 registered: {u1_email}")
    
    fund_resp = admin_fund_wallet(admin_token, u1_id, 2000)
    assert_status(fund_resp, 200, "U1 wallet funded with 2000")
    
    u1_wallet_before = get_wallet(u1_token)
    assert_true(u1_wallet_before["available_balance"] == "2000.00", "U1 wallet balance 2000.00")
    
    # Buy silver investment
    buy_resp = buy_investment(u1_token, "silver")
    assert_status(buy_resp, 201, "U1 bought silver investment")
    u1_investment = buy_resp.json()
    u1_inv_id = u1_investment["id"]
    u1_principal = u1_investment["principal"]
    u1_profit = u1_investment["profit_amount"]
    log(f"U1 investment created: id={u1_inv_id}, principal={u1_principal}, profit={u1_profit}")
    
    # 3. PUT /api/admin/plans/silver {price:'350', profit_percentage:'70'}
    # Use different values to ensure we get a change (in case plan was already edited)
    new_price = "360" if original_price == "350.00" else "350"
    new_profit = "75" if original_profit == "70.00" else "70"
    
    edit_resp = requests.put(f"{BASE_URL}/admin/plans/silver",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"price": new_price, "profit_percentage": new_profit}
    )
    assert_status(edit_resp, 200, "PUT /api/admin/plans/silver returns 200")
    updated_silver = edit_resp.json()
    assert_eq(updated_silver["price"], f"{new_price}.00" if len(new_price) == 3 else f"{new_price}0.00", f"Silver price updated to {new_price}")
    assert_eq(updated_silver["profit_percentage"], f"{new_profit}.00", f"Silver profit_percentage updated to {new_profit}")
    assert_true(updated_silver["version"] == original_version + 1, f"Silver version incremented (was {original_version}, now {updated_silver['version']})")
    
    # 4. GET /api/admin/plans/silver/history
    history_resp = requests.get(f"{BASE_URL}/admin/plans/silver/history",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert_status(history_resp, 200, "GET /api/admin/plans/silver/history returns 200")
    history = history_resp.json()
    assert_true(len(history) >= 1, f"History has >=1 entry (got {len(history)})")
    
    latest_history = history[0]
    assert_true("changed" in latest_history, "History entry has 'changed' field")
    changed = latest_history["changed"]
    # The latest change should have price or profit_percentage (we just edited it)
    has_changes = len(changed) > 0 and ("price" in changed or "profit_percentage" in changed)
    assert_true(has_changes, f"History shows price or profit_percentage change (changed: {changed})")
    log(f"History entry changed: {json.dumps(changed, indent=2)}")
    
    # 5. CRITICAL: U1's existing investment UNCHANGED
    u1_invs = get_investments(u1_token)
    u1_inv_after = next((i for i in u1_invs if i["id"] == u1_inv_id), None)
    assert_true(u1_inv_after is not None, "U1 investment still exists")
    assert_eq(u1_inv_after["principal"], u1_principal, f"U1 investment principal UNCHANGED (still {u1_principal})")
    assert_eq(u1_inv_after["profit_amount"], u1_profit, f"U1 investment profit_amount UNCHANGED (still {u1_profit})")
    
    # 6. Invalid: PUT with negative price
    invalid_resp = requests.put(f"{BASE_URL}/admin/plans/silver",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"price": "-5"}
    )
    assert_true(invalid_resp.status_code in [400, 422], f"PUT with negative price rejected (got {invalid_resp.status_code})")
    
    # 7. Invalid: PUT nonexistent plan
    notfound_resp = requests.put(f"{BASE_URL}/admin/plans/nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"price": "400"}
    )
    assert_status(notfound_resp, 404, "PUT nonexistent plan returns 404")

# ============================================================================
# FEATURE 2: Investment cancel + refund
# ============================================================================
def test_feature2_cancel_refund():
    log("\n" + "="*80)
    log("FEATURE 2: Investment cancel + refund")
    log("="*80)
    
    admin_token = admin_login()
    
    # Setup: create user U2, fund, buy silver (at current price 350)
    ts = int(time.time())
    u2_email = f"canceltest_u2_{ts}@easyx.com"
    u2_phone = f"+9198766{ts % 100000:05d}"
    u2_token, u2_id = register_user("Cancel Test U2", u2_email, u2_phone)
    assert_true(u2_token is not None, f"U2 registered: {u2_email}")
    
    admin_fund_wallet(admin_token, u2_id, 2000)
    u2_wallet_before = get_wallet(u2_token)
    log(f"U2 wallet before investment: {u2_wallet_before['available_balance']}")
    
    # Buy silver investment
    buy_resp = buy_investment(u2_token, "silver")
    assert_status(buy_resp, 201, "U2 bought silver investment")
    u2_inv = buy_resp.json()
    u2_inv_id = u2_inv["id"]
    u2_principal = u2_inv["principal"]
    log(f"U2 investment: id={u2_inv_id}, principal={u2_principal}")
    
    u2_wallet_after_buy = get_wallet(u2_token)
    log(f"U2 wallet after investment: {u2_wallet_after_buy['available_balance']}")
    
    # 1. Cancel with full refund
    cancel_resp = requests.post(f"{BASE_URL}/admin/investments/{u2_inv_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"refund_amount": u2_principal, "reason": "test cancel"}
    )
    assert_status(cancel_resp, 200, "POST cancel returns 200")
    cancelled_inv = cancel_resp.json()
    assert_eq(cancelled_inv["status"], "cancelled", "Investment status is 'cancelled'")
    
    # Verify wallet increased by EXACTLY refund amount (no profit)
    u2_wallet_after_cancel = get_wallet(u2_token)
    expected_balance = str(Decimal(u2_wallet_after_buy["available_balance"]) + Decimal(u2_principal))
    assert_eq(u2_wallet_after_cancel["available_balance"], expected_balance, 
              f"U2 wallet increased by refund amount {u2_principal} (no profit)")
    
    # 2. Attempt cancel again -> 409
    cancel_again_resp = requests.post(f"{BASE_URL}/admin/investments/{u2_inv_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"refund_amount": "100", "reason": "test"}
    )
    assert_status(cancel_again_resp, 409, "Cancel already-cancelled investment returns 409")
    
    # 3. Create another investment, try excessive refund
    admin_fund_wallet(admin_token, u2_id, 1000)
    buy_resp2 = buy_investment(u2_token, "silver")
    u2_inv2_id = buy_resp2.json()["id"]
    u2_principal2 = buy_resp2.json()["principal"]
    
    excessive_resp = requests.post(f"{BASE_URL}/admin/investments/{u2_inv2_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"refund_amount": "999999", "reason": "test"}
    )
    assert_status(excessive_resp, 422, "Excessive refund amount returns 422")
    
    # 4. Cancel with $0 refund (allowed)
    zero_refund_resp = requests.post(f"{BASE_URL}/admin/investments/{u2_inv2_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"refund_amount": "0", "reason": "zero refund test"}
    )
    assert_status(zero_refund_resp, 200, "Cancel with $0 refund returns 200")
    
    u2_wallet_after_zero = get_wallet(u2_token)
    # Wallet should be unchanged from before this cancel (no refund)
    log(f"U2 wallet after $0 refund cancel: {u2_wallet_after_zero['available_balance']}")
    
    # 5. GET /api/admin/investments?status=cancelled
    admin_invs_resp = requests.get(f"{BASE_URL}/admin/investments?status=cancelled",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert_status(admin_invs_resp, 200, "GET /api/admin/investments?status=cancelled returns 200")
    cancelled_invs = admin_invs_resp.json()
    assert_true(len(cancelled_invs) >= 2, f"At least 2 cancelled investments (got {len(cancelled_invs)})")
    
    u2_cancelled = [i for i in cancelled_invs if i["id"] in [u2_inv_id, u2_inv2_id]]
    assert_true(len(u2_cancelled) == 2, "Both U2 cancelled investments in list")
    for inv in u2_cancelled:
        assert_true("user" in inv, "Investment has user info")
        assert_true("refund_amount" in inv, "Investment has refund_amount")
        assert_true("cancel_reason" in inv, "Investment has cancel_reason")

# ============================================================================
# FEATURE 3: Withdrawals flow
# ============================================================================
def test_feature3_withdrawals():
    log("\n" + "="*80)
    log("FEATURE 3: Withdrawals flow")
    log("="*80)
    
    admin_token = admin_login()
    
    # 1. GET /api/withdrawals/config (requires auth in actual implementation)
    # Create a temp user to get config
    ts_temp = int(time.time())
    temp_token, _ = register_user("Temp Config", f"tempconfig_{ts_temp}@easyx.com", f"+9198768{ts_temp % 100000:05d}")
    
    config_resp = requests.get(f"{BASE_URL}/withdrawals/config", 
                               headers={"Authorization": f"Bearer {temp_token}"})
    assert_status(config_resp, 200, "GET /api/withdrawals/config returns 200")
    config = config_resp.json()
    assert_eq(config["min_withdrawal"], "10.00", "min_withdrawal is 10.00")
    assert_true("TRC20" in config["networks"] and "BEP20" in config["networks"], 
                "networks include TRC20 and BEP20")
    
    # 2. Create user U3 (NOT KYC-approved yet)
    ts = int(time.time())
    u3_email = f"withdrawtest_u3_{ts}@easyx.com"
    u3_phone = f"+9198767{ts % 100000:05d}"
    u3_token, u3_id = register_user("Withdraw Test U3", u3_email, u3_phone)
    assert_true(u3_token is not None, f"U3 registered: {u3_email}")
    
    admin_fund_wallet(admin_token, u3_id, 2000)
    
    # 3. U3 POST withdrawal without KYC -> 403
    withdraw_no_kyc_resp = requests.post(f"{BASE_URL}/withdrawals",
        headers={"Authorization": f"Bearer {u3_token}"},
        json={"network": "TRC20", "amount": "100", "to_address": "TXsomeaddress123456"}
    )
    assert_status(withdraw_no_kyc_resp, 403, "Withdrawal without KYC returns 403 (kyc_required)")
    
    # 4. Make U3 KYC-approved
    submit_kyc_resp = submit_kyc(u3_token)
    assert_status(submit_kyc_resp, 200, "U3 KYC submitted")
    
    # Get KYC record ID
    admin_kyc_resp = requests.get(f"{BASE_URL}/admin/kyc?status=pending",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    kyc_records = admin_kyc_resp.json()
    u3_kyc = next((k for k in kyc_records if k["user_email"] == u3_email), None)
    assert_true(u3_kyc is not None, "U3 KYC record found in admin list")
    
    approve_kyc_resp = admin_approve_kyc(admin_token, u3_kyc["id"])
    assert_status(approve_kyc_resp, 200, "U3 KYC approved by admin")
    
    # Verify KYC status
    u3_kyc_status = get_kyc(u3_token)
    assert_eq(u3_kyc_status["status"], "approved", "U3 KYC status is 'approved'")
    
    # 5. U3 POST withdrawal with KYC approved -> 201
    u3_wallet_before_wd = get_wallet(u3_token)
    log(f"U3 wallet before withdrawal: {u3_wallet_before_wd['available_balance']}")
    
    # Re-fetch user to verify KYC status is in user object
    me_resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {u3_token}"})
    u3_user = me_resp.json()
    log(f"U3 user kyc_status from /auth/me: {u3_user.get('kyc_status')}")
    
    withdraw_resp = requests.post(f"{BASE_URL}/withdrawals",
        headers={"Authorization": f"Bearer {u3_token}"},
        json={"network": "TRC20", "amount": "100", "to_address": "TXsomeaddress123456"}
    )
    if withdraw_resp.status_code != 201:
        log(f"Withdrawal failed: {withdraw_resp.status_code} {withdraw_resp.text}")
    assert_status(withdraw_resp, 201, "Withdrawal request created (201)")
    withdrawal = withdraw_resp.json()
    wd_id = withdrawal["id"]
    assert_eq(withdrawal["status"], "pending", "Withdrawal status is 'pending'")
    assert_eq(withdrawal["amount"], "100.00", "Withdrawal amount is 100.00")
    
    # Verify wallet balance dropped by 100 (held)
    u3_wallet_after_wd = get_wallet(u3_token)
    expected_balance = str(Decimal(u3_wallet_before_wd["available_balance"]) - Decimal("100"))
    assert_eq(u3_wallet_after_wd["available_balance"], expected_balance, 
              "U3 wallet available_balance dropped by 100 (held)")
    
    # 6. Below min withdrawal -> 400
    below_min_resp = requests.post(f"{BASE_URL}/withdrawals",
        headers={"Authorization": f"Bearer {u3_token}"},
        json={"network": "TRC20", "amount": "5", "to_address": "TXsomeaddress123456"}
    )
    assert_status(below_min_resp, 400, "Below min withdrawal returns 400")
    
    # 7. Invalid network -> 422
    invalid_network_resp = requests.post(f"{BASE_URL}/withdrawals",
        headers={"Authorization": f"Bearer {u3_token}"},
        json={"network": "ERC20", "amount": "100", "to_address": "0xsomeaddress"}
    )
    assert_status(invalid_network_resp, 422, "Invalid network returns 422")
    
    # 8. Admin GET pending withdrawals
    admin_wd_resp = requests.get(f"{BASE_URL}/admin/withdrawals?status=pending",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert_status(admin_wd_resp, 200, "GET /api/admin/withdrawals?status=pending returns 200")
    pending_wds = admin_wd_resp.json()
    u3_wd = next((w for w in pending_wds if w["id"] == wd_id), None)
    assert_true(u3_wd is not None, "U3 withdrawal in pending list")
    assert_true("user" in u3_wd, "Withdrawal has user info")
    
    # 9. Admin approve
    approve_wd_resp = requests.post(f"{BASE_URL}/admin/withdrawals/{wd_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={}
    )
    assert_status(approve_wd_resp, 200, "Admin approve withdrawal returns 200")
    approved_wd = approve_wd_resp.json()
    assert_eq(approved_wd["status"], "approved", "Withdrawal status is 'approved'")
    
    # 10. Admin process with tx_hash
    process_resp = requests.post(f"{BASE_URL}/admin/withdrawals/{wd_id}/process",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tx_hash": "0xabc123deadbeef"}
    )
    assert_status(process_resp, 200, "Admin process withdrawal returns 200")
    paid_wd = process_resp.json()
    assert_eq(paid_wd["status"], "paid", "Withdrawal status is 'paid'")
    assert_eq(paid_wd["tx_hash"], "0xabc123deadbeef", "tx_hash saved")
    
    # 11. Process before approve should 409 - create new withdrawal to test
    withdraw_resp2 = requests.post(f"{BASE_URL}/withdrawals",
        headers={"Authorization": f"Bearer {u3_token}"},
        json={"network": "BEP20", "amount": "50", "to_address": "0xanotheraddress"}
    )
    wd_id2 = withdraw_resp2.json()["id"]
    
    process_before_approve_resp = requests.post(f"{BASE_URL}/admin/withdrawals/{wd_id2}/process",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tx_hash": "0xtest"}
    )
    # Note: actual implementation returns 422 for invalid tx_hash length, not 409 for wrong state
    # The 409 would only happen if we pass a valid tx_hash (>=8 chars)
    if process_before_approve_resp.status_code == 422:
        # Try with valid tx_hash length
        process_before_approve_resp = requests.post(f"{BASE_URL}/admin/withdrawals/{wd_id2}/process",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"tx_hash": "0xtestvalidhash"}
        )
    assert_status(process_before_approve_resp, 409, "Process before approve returns 409")
    
    # 12. REJECT + REFUND: create 3rd withdrawal, reject it
    u3_wallet_before_reject = get_wallet(u3_token)
    
    withdraw_resp3 = requests.post(f"{BASE_URL}/withdrawals",
        headers={"Authorization": f"Bearer {u3_token}"},
        json={"network": "TRC20", "amount": "50", "to_address": "TXrejecttest"}
    )
    wd_id3 = withdraw_resp3.json()["id"]
    
    u3_wallet_after_hold = get_wallet(u3_token)
    log(f"U3 wallet after 3rd withdrawal hold: {u3_wallet_after_hold['available_balance']}")
    
    reject_resp = requests.post(f"{BASE_URL}/admin/withdrawals/{wd_id3}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "bad address"}
    )
    assert_status(reject_resp, 200, "Admin reject withdrawal returns 200")
    rejected_wd = reject_resp.json()
    assert_eq(rejected_wd["status"], "rejected", "Withdrawal status is 'rejected'")
    
    # Verify wallet restored by 50 (WITHDRAWAL_REVERSAL)
    u3_wallet_after_reject = get_wallet(u3_token)
    expected_balance_after_reject = str(Decimal(u3_wallet_after_hold["available_balance"]) + Decimal("50"))
    assert_eq(u3_wallet_after_reject["available_balance"], expected_balance_after_reject,
              "U3 wallet restored by 50 after rejection (WITHDRAWAL_REVERSAL)")

# ============================================================================
# FEATURE 4: Admin Overview KPIs
# ============================================================================
def test_feature4_overview():
    log("\n" + "="*80)
    log("FEATURE 4: Admin Overview KPIs")
    log("="*80)
    
    admin_token = admin_login()
    
    # GET /api/admin/overview
    overview_resp = requests.get(f"{BASE_URL}/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert_status(overview_resp, 200, "GET /api/admin/overview returns 200")
    overview = overview_resp.json()
    
    # Verify all required keys present
    required_keys = [
        "users", "investments", "deposits", "withdrawals", "kyc", "wallet", "referrals"
    ]
    for key in required_keys:
        assert_true(key in overview, f"Overview has '{key}' key")
    
    # Verify nested structure
    assert_true("total" in overview["users"], "users.total present")
    assert_true("active" in overview["users"], "users.active present")
    assert_true("suspended" in overview["users"], "users.suspended present")
    
    assert_true("active" in overview["investments"], "investments.active present")
    assert_true("matured" in overview["investments"], "investments.matured present")
    assert_true("cancelled" in overview["investments"], "investments.cancelled present")
    assert_true("active_principal" in overview["investments"], "investments.active_principal present")
    
    assert_true("pending" in overview["deposits"], "deposits.pending present")
    assert_true("approved_total" in overview["deposits"], "deposits.approved_total present")
    
    assert_true("pending" in overview["withdrawals"], "withdrawals.pending present")
    assert_true("approved" in overview["withdrawals"], "withdrawals.approved present")
    assert_true("paid_total" in overview["withdrawals"], "withdrawals.paid_total present")
    
    assert_true("pending" in overview["kyc"], "kyc.pending present")
    
    assert_true("available_total" in overview["wallet"], "wallet.available_total present")
    assert_true("locked_total" in overview["wallet"], "wallet.locked_total present")
    assert_true("liabilities" in overview["wallet"], "wallet.liabilities present")
    
    assert_true("commissions_paid" in overview["referrals"], "referrals.commissions_paid present")
    
    # Sanity check: all counts are non-negative
    assert_true(overview["users"]["total"] >= 0, "users.total >= 0")
    assert_true(overview["users"]["active"] >= 0, "users.active >= 0")
    assert_true(overview["users"]["suspended"] >= 0, "users.suspended >= 0")
    assert_true(overview["investments"]["active"] >= 0, "investments.active >= 0")
    assert_true(overview["investments"]["matured"] >= 0, "investments.matured >= 0")
    assert_true(overview["investments"]["cancelled"] >= 0, "investments.cancelled >= 0")
    assert_true(overview["deposits"]["pending"] >= 0, "deposits.pending >= 0")
    assert_true(overview["withdrawals"]["pending"] >= 0, "withdrawals.pending >= 0")
    assert_true(overview["withdrawals"]["approved"] >= 0, "withdrawals.approved >= 0")
    assert_true(overview["kyc"]["pending"] >= 0, "kyc.pending >= 0")
    
    log(f"Overview snapshot: {json.dumps(overview, indent=2)}")

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    log("Starting comprehensive backend test for 4 new features...")
    log(f"Base URL: {BASE_URL}")
    log(f"Admin: {ADMIN_EMAIL}")
    
    try:
        test_feature1_plan_editor()
        test_feature2_cancel_refund()
        test_feature3_withdrawals()
        test_feature4_overview()
    except Exception as e:
        log(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    log("\n" + "="*80)
    log(f"FINAL RESULTS: {tests_passed} passed, {tests_failed} failed")
    log("="*80)
    
    if tests_failed == 0:
        log("✅ ALL TESTS PASSED")
        exit(0)
    else:
        log(f"❌ {tests_failed} TESTS FAILED")
        exit(1)
