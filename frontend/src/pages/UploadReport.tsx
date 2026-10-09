import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { UploadCloud, FileWarning, Loader2, FileText } from "lucide-react";
import { api, friendlyErrorMessage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useT } from "@/i18n";

export function UploadReportPage() {
  const navigate = useNavigate();
  const t = useT();
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState<"idle" | "uploading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (file.type !== "application/pdf") {
        setStatus("error");
        setError("Only PDF files are supported.");
        return;
      }
      setFileName(file.name);
      setStatus("uploading");
      setError(null);
      try {
        const report = await api.uploadReport(file);
        navigate(`/reports/${report.id}`);
      } catch (e) {
        setStatus("error");
        setError(friendlyErrorMessage(e));
      }
    },
    [navigate]
  );

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="font-display text-2xl font-semibold text-brand-900 dark:text-paper md:text-3xl">{t("upload.title")}</h1>
      <p className="mt-2 text-sm text-unknown-600">{t("upload.subtitle")}</p>

      <motion.label
        htmlFor="pdf-upload"
        animate={{ borderColor: dragActive ? "#1E5C5F" : "#E2E8E4", scale: dragActive ? 1.01 : 1 }}
        className="mt-6 flex cursor-pointer flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed bg-white px-6 py-16 text-center dark:bg-surface-dark"
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
      >
        <input
          id="pdf-upload"
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {status === "uploading" ? (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-brand-700" />
            <p className="text-sm font-medium text-brand-900 dark:text-paper">{t("upload.reading", { filename: fileName ?? "" })}</p>
            <p className="text-xs text-unknown-600">{t("upload.processingHint")}</p>
          </>
        ) : (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 dark:bg-white/5">
              <UploadCloud className="h-6 w-6 text-brand-700 dark:text-brand-300" />
            </div>
            <p className="text-sm font-medium text-brand-900 dark:text-paper">
              {t("upload.dropHint")}<span className="text-brand-700 underline dark:text-brand-300">{t("upload.browse")}</span>
            </p>
            <p className="text-xs text-unknown-600">{t("upload.maxSize")}</p>
          </>
        )}
      </motion.label>

      {status === "error" && error && (
        <Card className="mt-4 flex items-start gap-3 border-attention-400/40 bg-attention-50 p-4 dark:bg-attention-600/10">
          <FileWarning className="mt-0.5 h-5 w-5 shrink-0 text-attention-600" />
          <div>
            <p className="text-sm font-medium text-attention-700">{t("upload.uploadFailed")}</p>
            <p className="mt-0.5 text-sm text-attention-700/90">{error}</p>
          </div>
        </Card>
      )}

      <Card className="mt-6 flex items-start gap-3 p-4">
        <FileText className="mt-0.5 h-5 w-5 shrink-0 text-brand-700 dark:text-brand-300" />
        <div className="text-sm text-unknown-600">
          <p className="font-medium text-brand-900 dark:text-paper">{t("upload.whatHappensTitle")}</p>
          <p className="mt-1 leading-relaxed">{t("upload.whatHappensBody")}</p>
        </div>
      </Card>

      <Button variant="ghost" className="mt-2 w-full" onClick={() => document.getElementById("pdf-upload")?.click()}>
        {t("upload.chooseFile")}
      </Button>
    </div>
  );
}
