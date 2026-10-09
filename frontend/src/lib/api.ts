import axios from "axios";
import type {
  ReportOut, ReportDetail, ReportSummary, KeyFindings, LabParameter,
  ChatMessage, Flashcard, Mode, Lang,
} from "./types";

// Same-origin by default (local dev via Vite's proxy, or any deployment
// serving frontend + backend from one domain, e.g. Hugging Face Spaces).
// If deploying frontend and backend to SEPARATE domains (e.g. Vercel +
// Render), set VITE_API_BASE_URL to the backend's full URL — e.g.
// https://your-backend.onrender.com/api — or every request below would
// silently hit the frontend's own domain instead of the real backend.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

const client = axios.create({ baseURL: API_BASE_URL });

export const api = {
  async uploadReport(file: File): Promise<ReportOut> {
    const form = new FormData();
    form.append("file", file);
    const { data } = await client.post<ReportOut>("/reports/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  async listReports(): Promise<ReportOut[]> {
    const { data } = await client.get<ReportOut[]>("/reports");
    return data;
  },

  async getReport(reportId: string): Promise<ReportDetail> {
    const { data } = await client.get<ReportDetail>(`/reports/${reportId}`);
    return data;
  },

  async deleteReport(reportId: string): Promise<void> {
    await client.delete(`/reports/${reportId}`);
  },

  async getKeyFindings(reportId: string): Promise<KeyFindings> {
    const { data } = await client.get<KeyFindings>(`/reports/${reportId}/key-findings`);
    return data;
  },

  async getOverview(reportId: string, mode: Mode, language: Lang): Promise<ReportSummary> {
    const { data } = await client.post<ReportSummary>("/reports/overview", {
      report_id: reportId, mode, language,
    });
    return data;
  },

  async explainParameter(parameterId: string, mode: Mode, language: Lang): Promise<LabParameter> {
    const { data } = await client.post<LabParameter>("/reports/parameter/explain", {
      parameter_id: parameterId, mode, language,
    });
    return data;
  },

  async sendChatMessage(reportId: string, question: string, mode: Mode, language: Lang) {
    const { data } = await client.post<{ answer: string; grounded: boolean; retrieved_chunk_count: number; source_of_truth: string }>(
      "/chat", { report_id: reportId, question, mode, language }
    );
    return data;
  },

  async getChatHistory(reportId: string): Promise<ChatMessage[]> {
    const { data } = await client.get<ChatMessage[]>(`/chat/${reportId}/history`);
    return data;
  },

  async getFlashcards(reportId: string, mode: Mode, language: Lang): Promise<Flashcard[]> {
    const { data } = await client.get<Flashcard[]>(`/flashcards/${reportId}`, {
      params: { mode, language },
    });
    return data;
  },

  async toggleBookmark(flashcardId: string): Promise<Flashcard> {
    const { data } = await client.post<Flashcard>(`/flashcards/${flashcardId}/toggle-bookmark`);
    return data;
  },
};

export function friendlyErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail ?? "Something went wrong. Please try again.";
  }
  return "Something went wrong. Please try again.";
}
