import { toast } from "sonner";

/**
 * Triggers a browser download of the complete EasyX Production Audit Report.
 * @param {'md' | 'txt'} format 
 */
export async function downloadProductionAuditReport(format = "md") {
  try {
    const response = await fetch("/EASYX_COMPLETE_PRODUCTION_AUDIT_REPORT.md");
    if (!response.ok) {
      throw new Error(`Failed to load audit report (${response.status})`);
    }
    const content = await response.text();
    const mimeType = format === "txt" ? "text/plain;charset=utf-8" : "text/markdown;charset=utf-8";
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `EASYX_COMPLETE_PRODUCTION_AUDIT_REPORT_${new Date().toISOString().slice(0, 10)}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success(`Downloaded Complete Audit Report (${format.toUpperCase()})`);
    return true;
  } catch (err) {
    console.error("Audit report download failed:", err);
    toast.error("Failed to download audit report. Please try again.");
    return false;
  }
}
