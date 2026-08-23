import React, { useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, Copy, Check, AlertTriangle, ShieldCheck } from "lucide-react";
import { QRCodeCanvas } from "qrcode.react";
import { toast } from "sonner";
import dayjs from "dayjs";

import {
  useDepositConfig,
  useMyDeposits,
  useCreateDeposit,
  money,
} from "@/features/dashboard/api";
import { apiError } from "@/lib/api";
import {
  PageHeading,
  EasyXCard,
  EasyXButton,
  EasyXLoader,
  EasyXStatusBadge,
} from "@/design/EasyX";

const NETWORKS = [
  { key: "TRC20", label: "TRC20", chain: "Tron network" },
  { key: "BEP20", label: "BEP20", chain: "BNB Smart Chain" },
];

export default function DepositPage() {
  const { data: config, isLoading } = useDepositConfig();
  const { data: deposits } = useMyDeposits();
  const createDeposit = useCreateDeposit();

  const [network, setNetwork] = useState("TRC20");
  const [amount, setAmount] = useState("");
  const [txHash, setTxHash] = useState("");
  const [copied, setCopied] = useState(false);

  const min = Number(config?.min_deposit ?? 300);
  const address = config?.addresses?.[network] || "";
  const configured = !!config?.configured;

  const amountNum = parseFloat(amount);
  const amountError =
    amount !== "" && (isNaN(amountNum) || amountNum < min)
      ? `Minimum deposit is ${money(min)} USDT`
      : "";
  const canSubmit =
    configured &&
    !amountError &&
    amount !== "" &&
    txHash.trim().length >= 8 &&
    !createDeposit.isPending;

  useEffect(() => {
    setCopied(false);
  }, [network]);

  const copyAddress = async () => {
    try {
      await navigator.clipboard.writeText(address);
      setCopied(true);
      toast.success("Address copied");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy address");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    try {
      await createDeposit.mutateAsync({ network, amount: String(amount), tx_hash: txHash.trim() });
      toast.success("Deposit submitted — pending admin verification");
      setAmount("");
      setTxHash("");
    } catch (err) {
      toast.error(apiError(err, "Could not submit deposit"));
    }
  };

  const sorted = useMemo(() => deposits || [], [deposits]);

  return (
    <div data-testid="deposit-page">
      <PageHeading
        title="Deposit USDT"
        subtitle={`Fund your wallet. Minimum deposit ${money(min)} USDT.`}
        icon={ArrowDownToLine}
      />

      {isLoading || !config ? (
        <EasyXLoader />
      ) : (
        <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Left: address + QR */}
          <EasyXCard>
            <div className="text-sm font-semibold text-ex-text">1. Send USDT to this address</div>

            <div className="mt-3 inline-flex rounded-ex-ctrl bg-white/5 p-1" data-testid="deposit-network-tabs">
              {NETWORKS.map((n) => (
                <button
                  key={n.key}
                  onClick={() => setNetwork(n.key)}
                  data-testid={`deposit-network-${n.key}`}
                  data-active={network === n.key ? "true" : "false"}
                  className={`px-4 py-2 rounded-ex-ctrl text-sm font-medium transition ${
                    network === n.key
                      ? "bg-ex-accent text-ex-ink shadow-ex-btn"
                      : "text-ex-muted hover:text-ex-text"
                  }`}
                >
                  {n.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-ex-muted">
              {NETWORKS.find((n) => n.key === network)?.chain} · USDT only
            </p>

            {!configured && (
              <div className="mt-4 flex items-start gap-2 rounded-ex-ctrl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200" data-testid="deposit-not-configured">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>Deposit addresses are not configured yet. Please check back shortly — an admin needs to set the official addresses.</span>
              </div>
            )}

            <div className="mt-4 flex justify-center rounded-ex bg-white p-4 w-fit mx-auto">
              <QRCodeCanvas value={address || "not-configured"} size={168} includeMargin={false} />
            </div>

            <div className="mt-4">
              <div className="text-xs text-ex-muted mb-1">{network} deposit address</div>
              <div className="flex items-center gap-2">
                <code
                  className="flex-1 break-all rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2.5 text-xs text-ex-text"
                  data-testid="deposit-address"
                >
                  {address}
                </code>
                <EasyXButton variant="ghost" className="h-11 w-11 p-0 shrink-0" onClick={copyAddress} data-testid="deposit-copy-address">
                  {copied ? <Check className="h-4 w-4 text-emerald-300" /> : <Copy className="h-4 w-4" />}
                </EasyXButton>
              </div>
            </div>

            <div className="mt-4 flex items-start gap-2 rounded-ex-ctrl border border-white/10 bg-white/[0.03] p-3 text-xs text-ex-muted">
              <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5 text-ex-lav-300" />
              <span>Send only USDT on the {network} network to this address. After sending, submit the amount and transaction hash — an admin verifies every deposit before it credits your wallet.</span>
            </div>
          </EasyXCard>

          {/* Right: submit form */}
          <EasyXCard>
            <div className="text-sm font-semibold text-ex-text">2. Confirm your transfer</div>
            <form onSubmit={submit} className="mt-4 space-y-4" data-testid="deposit-form">
              <div>
                <label className="text-xs text-ex-muted">Network</label>
                <input
                  value={network}
                  readOnly
                  className="mt-1 w-full rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-ex-text"
                />
              </div>
              <div>
                <label className="text-xs text-ex-muted">Amount (USDT)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  min={min}
                  step="0.01"
                  placeholder={`Min ${money(min)}`}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="mt-1 w-full rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-ex-text placeholder:text-ex-muted/60 focus:border-ex-accent focus:outline-none"
                  data-testid="deposit-amount-input"
                />
                {amountError && <p className="mt-1 text-xs text-red-300" data-testid="deposit-amount-error">{amountError}</p>}
              </div>
              <div>
                <label className="text-xs text-ex-muted">Transaction hash</label>
                <input
                  type="text"
                  placeholder="Paste the on-chain transaction hash"
                  value={txHash}
                  onChange={(e) => setTxHash(e.target.value)}
                  className="mt-1 w-full rounded-ex-ctrl bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-ex-text placeholder:text-ex-muted/60 focus:border-ex-accent focus:outline-none"
                  data-testid="deposit-txhash-input"
                />
                <p className="mt-1 text-[11px] text-ex-muted">Each transaction hash can only be submitted once.</p>
              </div>
              <EasyXButton type="submit" className="w-full" disabled={!canSubmit} loading={createDeposit.isPending} data-testid="deposit-submit">
                Submit deposit
              </EasyXButton>
            </form>
          </EasyXCard>
        </div>
      )}

      {/* History */}
      <h2 className="mt-9 ex-display text-lg font-bold">Your deposits</h2>
      <EasyXCard className="mt-3 p-0 overflow-hidden">
        {!sorted || sorted.length === 0 ? (
          <div className="p-8 text-center text-ex-muted text-sm">No deposits yet.</div>
        ) : (
          <div className="divide-y divide-white/5" data-testid="deposit-history">
            {sorted.map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-3 px-4 py-3" data-testid={`deposit-row-${d.id}`}>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-ex-text">{money(d.amount)} USDT</span>
                    <span className="text-[11px] text-ex-muted">· {d.network}</span>
                  </div>
                  <div className="mt-0.5 truncate text-[11px] text-ex-muted max-w-[220px] sm:max-w-md">
                    {d.tx_hash}
                  </div>
                  <div className="text-[11px] text-ex-muted">{dayjs(d.created_at).format("DD MMM YYYY, HH:mm")}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <EasyXStatusBadge status={d.status} />
                  {d.status === "approved" && d.approved_amount && Number(d.approved_amount) !== Number(d.amount) && (
                    <span className="text-[11px] text-emerald-300">credited {money(d.approved_amount)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </EasyXCard>
    </div>
  );
}
