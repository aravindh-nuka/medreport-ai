export type Mode = "patient" | "student" | "doctor";
export type Lang = "en" | "te";

export interface ReportOut {
  id: string;
  original_filename: string;
  report_type: string;
  patient_name: string | null;
  patient_age: string | null;
  patient_sex: string | null;
  hospital_name: string | null;
  doctor_name: string | null;
  sample_date: string | null;
  uploaded_at: string;
  chat_available: boolean;
}

export interface ParameterExplanation {
  what_it_measures: string;
  why_it_matters: string;
  high_value_reasons: string;
  low_value_reasons: string;
  lifestyle_suggestions: string;
  when_to_consult_doctor: string;
  clinical_significance: string;
  educational_notes: string;
  source_of_truth: string;
}

export interface LabParameter {
  id: string;
  test_name_raw: string;
  test_name_normalized: string | null;
  loinc_code: string | null;
  loinc_verified: boolean;
  loinc_category?: string | null;
  value: string | null;
  unit: string | null;
  reference_range: string | null;
  status: string;
  explanation?: ParameterExplanation | null;
}

export interface ReportSummary {
  short_summary: string;
  detailed_explanation: string;
  final_verdict: string;
  suggestions: string;
  precautions: string;
  lifestyle_advice: string;
  diet_recommendations: string;
  exercise_suggestions: string;
  followup_advice: string;
  doctor_consultation_advice: string;
  monitoring_advice: string;
  source_of_truth: string;
}

export interface KeyFindings {
  verified_abnormal: LabParameter[];
  verified_normal: LabParameter[];
  unverified: LabParameter[];
}

export interface ReportDetail extends ReportOut {
  parameters: LabParameter[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  grounded: boolean;
  created_at: string;
  source_of_truth?: string;
}

export interface Flashcard {
  id: string;
  term: string;
  definition: string;
  category: string;
  reference_range: string | null;
  bookmarked: boolean;
}
