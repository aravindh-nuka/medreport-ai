import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2, Layers, Bookmark, BookmarkCheck } from "lucide-react";
import { api, friendlyErrorMessage } from "@/lib/api";
import type { Flashcard } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { useAppSettings } from "@/hooks/useAppSettings";
import { useT } from "@/i18n";
import { cn } from "@/lib/utils";

const CATEGORY_COLOR: Record<string, string> = {
  Test: "bg-brand-50 text-brand-700 dark:bg-white/5 dark:text-brand-300",
  Disease: "bg-attention-50 text-attention-700",
  "Abnormal Finding": "bg-attention-50 text-attention-700",
  Concept: "bg-ai-50 text-ai-700 dark:bg-ai-600/20 dark:text-ai-400",
  Vocabulary: "bg-verified-50 text-verified-700",
  "Reference Range": "bg-unknown-50 text-unknown-600",
};

function FlipCard({ card, onToggleBookmark }: { card: Flashcard; onToggleBookmark: (id: string) => void }) {
  const t = useT();
  const [flipped, setFlipped] = useState(false);
  return (
    <div className="[perspective:1000px]">
      <motion.div
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ duration: 0.5 }}
        className="relative h-44 [transform-style:preserve-3d]"
      >
        <Card
          onClick={() => setFlipped((f) => !f)}
          className="absolute inset-0 flex cursor-pointer flex-col items-start justify-center gap-2 p-5 [backface-visibility:hidden]"
        >
          <div className="flex w-full items-center justify-between">
            <span className={`rounded-pill px-2 py-0.5 font-mono text-[10px] uppercase ${CATEGORY_COLOR[card.category] ?? CATEGORY_COLOR.Concept}`}>
              {card.category}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onToggleBookmark(card.id); }}
              aria-label={t("flashcards.bookmark")}
              className="text-unknown-400 hover:text-brand-700 dark:hover:text-brand-300"
            >
              {card.bookmarked ? <BookmarkCheck className="h-4 w-4 text-brand-700 dark:text-brand-300" /> : <Bookmark className="h-4 w-4" />}
            </button>
          </div>
          <p className="font-display text-lg font-semibold text-brand-900 dark:text-paper">{card.term}</p>
          <p className="text-xs text-unknown-600">{t("flashcards.tapToReveal")}</p>
        </Card>
        <Card
          onClick={() => setFlipped((f) => !f)}
          className="absolute inset-0 flex cursor-pointer flex-col justify-center gap-2 p-5 [backface-visibility:hidden] [transform:rotateY(180deg)]"
        >
          <p className="text-sm leading-relaxed text-brand-900 dark:text-paper/90">{card.definition}</p>
          {card.reference_range && (
            <p className="font-mono text-xs text-unknown-600">ref: {card.reference_range}</p>
          )}
        </Card>
      </motion.div>
    </div>
  );
}

export function FlashcardsPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { mode, explanationLanguage } = useAppSettings();
  const t = useT();
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "bookmarked">("all");

  useEffect(() => {
    if (!reportId) return;
    setLoading(true);
    api.getFlashcards(reportId, mode, explanationLanguage)
      .then(setCards)
      .catch((e) => setError(friendlyErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [reportId, mode, explanationLanguage]);

  const toggleBookmark = async (id: string) => {
    setCards((prev) => prev.map((c) => (c.id === id ? { ...c, bookmarked: !c.bookmarked } : c)));
    try {
      await api.toggleBookmark(id);
    } catch {
      setCards((prev) => prev.map((c) => (c.id === id ? { ...c, bookmarked: !c.bookmarked } : c)));
    }
  };

  const visible = filter === "bookmarked" ? cards.filter((c) => c.bookmarked) : cards;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-brand-900 dark:text-paper">{t("flashcards.title")}</h1>
          <p className="mt-1 text-sm text-unknown-600">{t("flashcards.subtitle")}</p>
        </div>
        <div className="inline-flex items-center rounded-pill border border-border bg-white p-1 dark:bg-surface-dark dark:border-borderDark">
          {(["all", "bookmarked"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "rounded-pill px-3 py-1.5 text-xs font-medium",
                filter === f ? "bg-brand-700 text-white" : "text-brand-700 dark:text-paper/80"
              )}
            >
              {f === "all" ? t("flashcards.all") : t("flashcards.bookmarkedOnly")}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-16 text-sm text-unknown-600"><Loader2 className="h-4 w-4 animate-spin" /> {t("flashcards.generating")}</div>
      ) : error ? (
        <p className="mt-6 text-sm text-attention-600">{error}</p>
      ) : visible.length === 0 ? (
        <Card className="mt-6 flex flex-col items-center gap-2 py-16 text-center">
          <Layers className="h-8 w-8 text-unknown-400" />
          <p className="text-sm text-unknown-600">{t("flashcards.noCards")}</p>
        </Card>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          {visible.map((c) => <FlipCard key={c.id} card={c} onToggleBookmark={toggleBookmark} />)}
        </div>
      )}
    </div>
  );
}
