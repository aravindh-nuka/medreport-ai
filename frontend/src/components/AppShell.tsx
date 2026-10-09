import { NavLink, Outlet, useParams } from "react-router-dom";
import { Home, Upload, FileText, ListChecks, MessageSquare, Layers, Settings, Stethoscope } from "lucide-react";
import { cn } from "@/lib/utils";
import { TopControls } from "./TopControls";
import { useT } from "@/i18n";

function useNavItems(reportId: string | undefined) {
  const t = useT();
  return [
    { to: "/", label: t("nav.home"), icon: Home, end: true },
    { to: "/upload", label: t("nav.upload"), icon: Upload },
    { to: reportId ? `/reports/${reportId}` : "/reports", label: t("nav.overview"), icon: FileText },
    { to: reportId ? `/reports/${reportId}/tests` : "/upload", label: t("nav.tests"), icon: ListChecks },
    { to: reportId ? `/reports/${reportId}/chat` : "/upload", label: t("nav.chat"), icon: MessageSquare },
    { to: reportId ? `/reports/${reportId}/flashcards` : "/upload", label: t("nav.flashcards"), icon: Layers },
    { to: "/settings", label: t("nav.settings"), icon: Settings },
  ];
}

export function AppShell() {
  const { reportId } = useParams();
  const items = useNavItems(reportId);
  const t = useT();

  return (
    <div className="min-h-screen bg-paper dark:bg-surface-dark">
      <div className="mx-auto flex max-w-7xl">
        {/* Desktop sidebar */}
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border px-4 py-6 dark:border-borderDark md:flex">
          <div className="mb-8 flex items-center gap-2 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-700 text-white">
              <Stethoscope className="h-5 w-5" />
            </div>
            <span className="font-display text-lg font-semibold text-brand-900 dark:text-paper">{t("nav.appName")}</span>
          </div>
          <nav className="flex flex-1 flex-col gap-1">
            {items.map((item) => (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-brand-50 text-brand-900 dark:bg-white/10 dark:text-paper"
                      : "text-brand-700/70 hover:bg-brand-50 hover:text-brand-900 dark:text-paper/60 dark:hover:bg-white/5"
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <p className="px-2 text-xs leading-relaxed text-unknown-600">{t("nav.disclaimer")}</p>
        </aside>

        {/* Main column */}
        <div className="flex min-h-screen flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-paper/90 px-4 py-3 backdrop-blur dark:border-borderDark dark:bg-surface-dark/90 md:px-8">
            <div className="flex items-center gap-2 md:hidden">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">
                <Stethoscope className="h-4 w-4" />
              </div>
              <span className="font-display text-base font-semibold text-brand-900 dark:text-paper">{t("nav.appName")}</span>
            </div>
            <div className="hidden md:block" />
            <TopControls />
          </header>

          <main className="flex-1 px-4 pb-24 pt-6 md:px-8 md:pb-10">
            <Outlet />
          </main>

          {/* Mobile bottom nav */}
          <nav
            className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around overflow-x-auto border-t border-border bg-white/95 py-2 backdrop-blur dark:border-borderDark dark:bg-surface-dark/95 md:hidden"
            style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}
          >
            {items.map((item) => (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex shrink-0 flex-col items-center gap-1 rounded-lg px-2.5 py-1.5 text-[10px] font-medium",
                    isActive ? "text-brand-700 dark:text-paper" : "text-unknown-600"
                  )
                }
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
}
