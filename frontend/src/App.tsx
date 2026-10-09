import { Routes, Route } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { HomePage } from "@/pages/Home";
import { UploadReportPage } from "@/pages/UploadReport";
import { ReportOverviewPage } from "@/pages/ReportOverview";
import { IndividualTestAnalysisPage } from "@/pages/IndividualTestAnalysis";
import { ChatPage } from "@/pages/Chat";
import { FlashcardsPage } from "@/pages/Flashcards";
import { SettingsPage } from "@/pages/Settings";
import { ReportsListPage } from "@/pages/ReportsList";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadReportPage />} />
        <Route path="/reports" element={<ReportsListPage />} />
        <Route path="/reports/:reportId" element={<ReportOverviewPage />} />
        <Route path="/reports/:reportId/tests" element={<IndividualTestAnalysisPage />} />
        <Route path="/reports/:reportId/chat" element={<ChatPage />} />
        <Route path="/reports/:reportId/flashcards" element={<FlashcardsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
