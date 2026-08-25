import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/shared/lib/api";

export function useAdminDeposits(status) {
  return useQuery({
    queryKey: ["admin-deposits", status || "all"],
    queryFn: async () =>
      (await api.get("/admin/deposits", { params: status ? { status } : {} })).data,
    refetchInterval: 30000,
  });
}

export function useApproveDeposit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approved_amount, note }) =>
      (await api.post(`/admin/deposits/${id}/approve`, { approved_amount, note })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-deposits"] }),
  });
}

export function useRejectDeposit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }) =>
      (await api.post(`/admin/deposits/${id}/reject`, { note })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-deposits"] }),
  });
}

export function useBatchApproveDeposits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, note }) =>
      (await api.post("/admin/deposits/batch-approve", { ids, note })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-deposits"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });
}

export function useBatchRejectDeposits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, reason }) =>
      (await api.post("/admin/deposits/batch-reject", { ids, reason })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-deposits"] }),
  });
}

export function useBatchSetDepositStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, status, note, reason }) =>
      (await api.post("/admin/deposits/batch-set-status", { ids, status, note: note || reason })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-deposits"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });
}

export function useAdminDepositSettings() {
  return useQuery({
    queryKey: ["admin-deposit-settings"],
    queryFn: async () => (await api.get("/admin/settings/deposit")).data,
  });
}

export function useAdminSettings() {
  return useQuery({
    queryKey: ["admin-settings"],
    queryFn: async () => (await api.get("/admin/settings")).data,
    refetchInterval: 15000,
  });
}

export function useSaveAdminSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch) => (await api.put("/admin/settings", patch)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-settings"] });
      qc.invalidateQueries({ queryKey: ["admin-maintenance"] });
      qc.invalidateQueries({ queryKey: ["public-maintenance"] });
      qc.invalidateQueries({ queryKey: ["admin-deposit-settings"] });
      qc.invalidateQueries({ queryKey: ["deposit-config"] });
      qc.invalidateQueries({ queryKey: ["admin-audit-logs"] });
    },
  });
}

export function useSaveDepositAddresses() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ trc20, bep20 }) =>
      (await api.put("/admin/settings/deposit", { trc20, bep20 })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-deposit-settings"] });
      qc.invalidateQueries({ queryKey: ["admin-settings"] });
      qc.invalidateQueries({ queryKey: ["deposit-config"] });
      qc.invalidateQueries({ queryKey: ["admin-audit-logs"] });
    },
  });
}

export function useAdminKyc(status) {
  return useQuery({
    queryKey: ["admin-kyc", status || "all"],
    queryFn: async () =>
      (await api.get("/admin/kyc", { params: status ? { status } : {} })).data,
    refetchInterval: 30000,
  });
}

export function useApproveKyc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }) => (await api.post(`/admin/kyc/${id}/approve`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-kyc"] }),
  });
}

export function useRejectKyc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }) => (await api.post(`/admin/kyc/${id}/reject`, { reason })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-kyc"] }),
  });
}

export function useBatchApproveKyc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids }) => (await api.post("/admin/kyc/batch-approve", { ids })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-kyc"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function useBatchRejectKyc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, reason }) => (await api.post("/admin/kyc/batch-reject", { ids, reason })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-kyc"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function useBatchSetKycStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, status, reason, note }) =>
      (await api.post("/admin/kyc/batch-set-status", { ids, status, reason: reason || note })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-kyc"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });
}

// Fetch a protected KYC document as an object URL (admin-authenticated).
export async function fetchAdminKycDocUrl(docId) {
  try {
    const res = await api.get(`/admin/kyc/documents/${docId}`, { responseType: "blob" });
    if (!res?.data || (res.data.type && res.data.type.includes("application/json"))) {
      throw new Error("Invalid document response");
    }
    return URL.createObjectURL(res.data);
  } catch (err) {
    throw err;
  }
}

export function useAdminReferrals() {
  return useQuery({
    queryKey: ["admin-referrals"],
    queryFn: async () => (await api.get("/admin/referrals")).data,
    refetchInterval: 30000,
  });
}

/* ------------------------- Users (view / suspend) ------------------------- */
export function useAdminUsers({ status, q } = {}) {
  return useQuery({
    queryKey: ["admin-users", status || "all", q || ""],
    queryFn: async () => {
      const params = {};
      if (status) params.status = status;
      if (q) params.q = q;
      return (await api.get("/admin/users", { params })).data;
    },
    refetchInterval: 30000,
  });
}

export function useSuspendUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }) =>
      (await api.post(`/admin/users/${id}/suspend`, { reason })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useUnsuspendUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }) => (await api.post(`/admin/users/${id}/unsuspend`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useBatchSetUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, status, reason }) =>
      (await api.post("/admin/users/batch-set-status", { ids, status, reason })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-kyc"] });
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });
}

/* ------------------------- Maintenance mode ------------------------- */
export function useAdminMaintenance() {
  return useQuery({
    queryKey: ["admin-maintenance"],
    queryFn: async () => (await api.get("/admin/maintenance")).data,
  });
}

export function useSaveMaintenance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch) => (await api.put("/admin/maintenance", patch)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-maintenance"] });
      qc.invalidateQueries({ queryKey: ["public-maintenance"] });
    },
  });
}

/* ------------------------- Admin Wallet & Adjustments ------------------------- */
export function useAdminWalletTransactions({ user_id, type, direction, q } = {}) {
  return useQuery({
    queryKey: ["admin-wallet-transactions", user_id || "", type || "", direction || "", q || ""],
    queryFn: async () => {
      const params = {};
      if (user_id) params.user_id = user_id;
      if (type) params.type = type;
      if (direction) params.direction = direction;
      if (q) params.q = q;
      return (await api.get("/admin/wallet/transactions", { params })).data;
    },
    refetchInterval: 15000,
  });
}

export function useAdminAdjustWallet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ user_id, amount, direction, reason, note, idempotency_key }) =>
      (
        await api.post("/admin/wallet/adjust", {
          user_id,
          amount,
          direction,
          reason,
          note,
          idempotency_key,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-wallet-transactions"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-audit-logs"] });
    },
  });
}

/* ------------------------- Audit logs ------------------------- */
export function useAdminAuditLogs({ action, entity_type, decision, q, from_date, to_date } = {}) {
  return useQuery({
    queryKey: [
      "admin-audit-logs",
      action || "all",
      entity_type || "all",
      decision || "all",
      q || "",
      from_date || "",
      to_date || "",
    ],
    queryFn: async () => {
      const params = {};
      if (action && action !== "all") params.action = action;
      if (entity_type && entity_type !== "all") params.entity_type = entity_type;
      if (decision && decision !== "all") params.decision = decision;
      if (q) params.q = q;
      if (from_date) params.from_date = from_date;
      if (to_date) params.to_date = to_date;
      return (await api.get("/admin/audit-logs", { params })).data;
    },
    refetchInterval: 15000,
  });
}

// Download Audit Logs (CSV or XLSX)
export async function downloadAuditLogs(format = "csv", filters = {}) {
  const params = { format };
  if (filters.action && filters.action !== "all") params.action = filters.action;
  if (filters.entity_type && filters.entity_type !== "all") params.entity_type = filters.entity_type;
  if (filters.decision && filters.decision !== "all") params.decision = filters.decision;
  if (filters.q) params.q = filters.q;
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;

  const res = await api.get("/admin/audit-logs", {
    params,
    responseType: "blob",
  });
  let filename = `easyx-audit-logs-${new Date().toISOString().slice(0, 10)}.${format}`;
  const cd = res.headers?.["content-disposition"];
  if (cd) {
    const m = /filename="?([^"]+)"?/.exec(cd);
    if (m) filename = m[1];
  }
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return filename;
}

/* ------------------------- Reports / Exports ------------------------- */
export function useAdminReports() {
  return useQuery({
    queryKey: ["admin-reports"],
    queryFn: async () => (await api.get("/admin/reports")).data,
  });
}

export function useAdminReportData({ dataset, q, status, from_date, to_date } = {}) {
  return useQuery({
    queryKey: ["admin-report-data", dataset || "users", q || "", status || "", from_date || "", to_date || ""],
    queryFn: async () => {
      const params = { format: "json" };
      if (q) params.q = q;
      if (status && status !== "all") params.status = status;
      if (from_date) params.from_date = from_date;
      if (to_date) params.to_date = to_date;
      return (await api.get(`/admin/reports/${dataset || "users"}`, { params })).data;
    },
    enabled: Boolean(dataset),
    refetchInterval: 15000,
  });
}

// Trigger a browser download of a dataset export (CSV or XLSX) with filters.
export async function downloadReport(dataset, format = "csv", filters = {}) {
  const params = { format };
  if (filters.q) params.q = filters.q;
  if (filters.status && filters.status !== "all") params.status = filters.status;
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;

  const res = await api.get(`/admin/reports/${dataset}`, {
    params,
    responseType: "blob",
  });
  // Derive filename from Content-Disposition when available.
  let filename = `easyx-${dataset}-${new Date().toISOString().slice(0, 10)}.${format}`;
  const cd = res.headers?.["content-disposition"];
  if (cd) {
    const m = /filename="?([^"]+)"?/.exec(cd);
    if (m) filename = m[1];
  }
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return filename;
}

/* Public maintenance status (no auth) — used by auth screens. */
export function usePublicMaintenance() {
  return useQuery({
    queryKey: ["public-maintenance"],
    queryFn: async () => (await api.get("/maintenance")).data,
    refetchInterval: 60000,
  });
}

/* ------------------------- Overview / KPIs ------------------------- */
export function useAdminOverview() {
  return useQuery({
    queryKey: ["admin-overview"],
    queryFn: async () => (await api.get("/admin/overview")).data,
    refetchInterval: 30000,
  });
}

/* ------------------------- Investment plans ------------------------- */
export function useAdminPlans() {
  return useQuery({
    queryKey: ["admin-plans"],
    queryFn: async () => (await api.get("/admin/plans")).data,
  });
}

export function useSavePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, patch }) => (await api.put(`/admin/plans/${key}`, patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-plans"] }),
  });
}

export function usePlanHistory(key) {
  return useQuery({
    queryKey: ["admin-plan-history", key],
    queryFn: async () => (await api.get(`/admin/plans/${key}/history`)).data,
    enabled: !!key,
  });
}

/* ------------------------- Investments (cancel) ------------------------- */
export function useAdminInvestments({ status, q } = {}) {
  return useQuery({
    queryKey: ["admin-investments", status || "all", q || ""],
    queryFn: async () => {
      const params = {};
      if (status) params.status = status;
      if (q) params.q = q;
      return (await api.get("/admin/investments", { params })).data;
    },
    refetchInterval: 30000,
  });
}

export function useCancelInvestment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, refund_amount, reason }) =>
      (await api.post(`/admin/investments/${id}/cancel`, { refund_amount, reason })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-investments"] }),
  });
}

/* ------------------------- Withdrawals ------------------------- */
export function useAdminWithdrawals({ status } = {}) {
  return useQuery({
    queryKey: ["admin-withdrawals", status || "all"],
    queryFn: async () => {
      const params = {};
      if (status) params.status = status;
      return (await api.get("/admin/withdrawals", { params })).data;
    },
    refetchInterval: 20000,
  });
}

export function useWithdrawalAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, body }) =>
      (await api.post(`/admin/withdrawals/${id}/${action}`, body || {})).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-withdrawals"] }),
  });
}

export function useBatchSetWithdrawalStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, status, note, reason, tx_hash }) =>
      (await api.post("/admin/withdrawals/batch-set-status", { ids, status, note: note || reason, tx_hash })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-withdrawals"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });
}

/* ------------------------- Analytics & Growth Trends (Recharts) ------------------------- */
export function useAdminAnalyticsTrends(period = "30d") {
  return useQuery({
    queryKey: ["admin-analytics-trends", period],
    queryFn: async () => (await api.get("/admin/analytics/trends", { params: { period } })).data,
    refetchInterval: 30000,
  });
}

