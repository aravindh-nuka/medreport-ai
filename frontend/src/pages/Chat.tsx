import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Send, Loader2, Sparkles, User, AlertTriangle } from "lucide-react";
import { api, friendlyErrorMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { useAppSettings } from "@/hooks/useAppSettings";
import { ModeSwitcher } from "@/components/ModeSwitcher";
import { ExplanationLanguageSwitcher } from "@/components/ExplanationLanguageSwitcher";
import { cn } from "@/lib/utils";
import { useT } from "@/i18n";

export function ChatPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { mode, explanationLanguage } = useAppSettings();
  const t = useT();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatAvailable, setChatAvailable] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const SUGGESTIONS = [t("chat.suggestion1"), t("chat.suggestion2"), t("chat.suggestion3")];

  useEffect(() => {
    if (!reportId) return;
    api.getChatHistory(reportId).then(setMessages);
    api.getReport(reportId).then((r) => setChatAvailable(r.chat_available));
  }, [reportId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const send = async (text: string) => {
    if (!reportId || !text.trim() || sending) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text, grounded: true, created_at: new Date().toISOString() }]);
    setSending(true);
    try {
      const res = await api.sendChatMessage(reportId, text, mode, explanationLanguage);
      setMessages((m) => [...m, { role: "assistant", content: res.answer, grounded: res.grounded, created_at: new Date().toISOString(), source_of_truth: res.source_of_truth }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: friendlyErrorMessage(e), grounded: false, created_at: new Date().toISOString() }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-140px)] max-w-2xl flex-col">
      <div className="flex items-center justify-between gap-2 pb-4">
        <div>
          <h1 className="font-display text-xl font-semibold text-brand-900 dark:text-paper">{t("chat.title")}</h1>
          <p className="text-xs text-unknown-600">{t("chat.subtitle")}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ModeSwitcher />
          <ExplanationLanguageSwitcher />
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {!chatAvailable && (
          <div className="flex items-start gap-3 rounded-card border border-attention-400/40 bg-attention-50 p-4 dark:bg-attention-600/10">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-attention-600" />
            <p className="text-sm text-attention-700">
              This report's search index couldn't be built when it was uploaded, so chat can't
              search its content. Try re-uploading the report — Report Overview, Individual Test
              Analysis, and Flashcards are unaffected and work normally.
            </p>
          </div>
        )}
        {messages.length === 0 && (
          <div className="mt-6 flex flex-col gap-2">
            <p className="text-sm text-unknown-600">{t("chat.tryAsking")}</p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="rounded-card border border-border bg-white px-4 py-2.5 text-left text-sm text-brand-900 hover:border-brand-300 dark:bg-surface-dark dark:text-paper dark:border-borderDark"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn("flex gap-2.5", m.role === "user" ? "justify-end" : "justify-start")}
          >
            {m.role === "assistant" && (
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai-50 dark:bg-ai-600/20">
                <Sparkles className="h-3.5 w-3.5 text-ai-600 dark:text-ai-400" />
              </div>
            )}
            <div className={cn("flex max-w-[80%] flex-col gap-1", m.role === "user" ? "items-end" : "items-start")}>
              <div
                className={cn(
                  "rounded-card px-4 py-2.5 text-sm leading-relaxed",
                  m.role === "user"
                    ? "bg-brand-700 text-white"
                    : m.grounded
                    ? "bg-white text-brand-900 border border-border dark:bg-surface-dark dark:text-paper dark:border-borderDark"
                    : "bg-unknown-50 text-unknown-600 border border-unknown-400/30 dark:bg-white/5"
                )}
              >
                {m.content}
              </div>
              {m.role === "assistant" && m.source_of_truth === "template_fallback" && (
                <span className="rounded-pill bg-attention-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-attention-700 dark:bg-attention-600/15">
                  Basic mode · AI unavailable
                </span>
              )}
            </div>
            {m.role === "user" && (
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-50 dark:bg-white/10">
                <User className="h-3.5 w-3.5 text-brand-700 dark:text-brand-300" />
              </div>
            )}
          </motion.div>
        ))}
        {sending && (
          <div className="flex items-center gap-2 text-sm text-unknown-600">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("chat.reading")}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(input); }}
        className="flex items-center gap-2 border-t border-border pt-3 dark:border-borderDark"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("chat.placeholder")}
          className="flex-1 rounded-pill border border-border bg-white px-4 py-2.5 text-sm text-brand-900 outline-none focus:border-brand-500 dark:bg-surface-dark dark:text-paper dark:border-borderDark"
        />
        <button
          type="submit"
          disabled={sending || !input.trim() || !chatAvailable}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-700 text-white disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
