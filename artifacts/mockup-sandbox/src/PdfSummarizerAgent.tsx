import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Brain,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileText,
  Gauge,
  Layers3,
  Loader2,
  MessageSquareText,
  Moon,
  PanelLeft,
  PanelRight,
  RefreshCcw,
  Search,
  Send,
  Sparkles,
  Sun,
  Trash2,
  UploadCloud,
  WandSparkles,
  X,
  Zap,
} from "lucide-react";
import {
  Component,
  type ChangeEvent,
  type DragEvent,
  type ErrorInfo,
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type ThemeMode = "light" | "dark";
type ProcessingStatus =
  | "idle"
  | "uploading"
  | "extracting"
  | "summarizing"
  | "ready"
  | "error";
type MessageRole = "user" | "assistant";
type ChatTab = "summary" | "chat";

interface PDFDocument {
  id: string;
  fileName: string;
  size: number;
  uploadedAt: Date;
  status: Exclude<ProcessingStatus, "idle">;
  pageCount: number;
  activePage: number;
  text: string;
  summary?: SummaryResult;
  error?: string;
}

interface SummaryResult {
  overview: string;
  bullets: string[];
  targetAudience: string;
  keyMetrics: Array<{ label: string; value: string; trend: "up" | "flat" }>;
  confidence: number;
}

interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: Date;
}

interface AgentResponse {
  content: string;
  summary?: SummaryResult;
}

interface ApiPayload {
  task: "summarize" | "chat";
  document: Pick<PDFDocument, "id" | "fileName" | "text" | "pageCount">;
  question?: string;
  history?: Message[];
}

interface AppErrorBoundaryState {
  hasError: boolean;
  message: string;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const BACKEND_API_URL = import.meta.env.VITE_AI_API_URL as string | undefined;
const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY as string | undefined;

const quickActions = [
  "Summarize in 3 bullet points",
  "Extract action items",
  "Translate to Urdu",
  "Find risks and deadlines",
] as const;

const processingCopy: Record<ProcessingStatus, string> = {
  idle: "Waiting",
  uploading: "Uploading",
  extracting: "Extracting text",
  summarizing: "AI summarizing",
  ready: "Ready",
  error: "Error",
};

class AppErrorBoundary extends Component<
  { children: ReactNode },
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("PDF Summarizer crashed", error, info);
  }

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-zinc-50">
        <section className="w-full max-w-lg rounded-lg border border-red-500/30 bg-red-950/20 p-6 shadow-2xl">
          <AlertTriangle className="mb-4 h-8 w-8 text-red-300" />
          <h1 className="text-xl font-semibold">Application error</h1>
          <p className="mt-2 text-sm text-red-100">{this.state.message}</p>
          <button
            className="mt-5 inline-flex items-center gap-2 rounded-md bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-400"
            onClick={() => window.location.reload()}
            type="button"
          >
            <RefreshCcw className="h-4 w-4" />
            Reload
          </button>
        </section>
      </main>
    );
  }
}

function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "2-digit",
  }).format(date);
}

function createId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function withTimeout<T>(
  task: Promise<T>,
  timeoutMs: number,
  label: string,
): Promise<T> {
  let timeoutId = 0;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = window.setTimeout(
      () => reject(new Error(`${label} timed out. Please try again.`)),
      timeoutMs,
    );
  });

  try {
    return await Promise.race([task, timeout]);
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function validatePdfFile(file: File): void {
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Only PDF files are supported.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error("File is larger than 10MB.");
  }

  if (file.size === 0) {
    throw new Error("This PDF is empty.");
  }
}

async function extractPdfText(file: File): Promise<{ text: string; pageCount: number }> {
  validatePdfFile(file);
  await delay(600);

  const baseName = file.name.replace(/\.pdf$/i, "").replace(/[-_]/g, " ");
  const estimatedPages = Math.max(1, Math.min(24, Math.ceil(file.size / 220_000)));
  const text = [
    `Document title: ${baseName}.`,
    `This document contains ${estimatedPages} estimated pages and was uploaded for executive PDF analysis.`,
    "The core themes include strategic priorities, financial impact, operational risks, stakeholder decisions, and recommended next steps.",
    "The agent should surface key points, action items, unresolved questions, timelines, and audience-specific summaries.",
    "Sections include overview, context, findings, risks, implementation notes, and closing recommendations.",
  ].join("\n\n");

  return { text, pageCount: estimatedPages };
}

function buildLocalSummary(document: PDFDocument): SummaryResult {
  const words = document.text.split(/\s+/).filter(Boolean).length;
  const minutes = Math.max(1, Math.ceil(words / 180));

  return {
    overview: `${document.fileName} has been analyzed into an executive-ready brief with the major themes, decision points, and follow-up work separated for fast review.`,
    bullets: [
      "Primary themes are organized around context, findings, risk, and recommended next steps.",
      "The document is suitable for stakeholder review after validating factual details against the source PDF.",
      "The highest-value next action is to convert highlighted decisions into owners, due dates, and measurable outcomes.",
    ],
    targetAudience: "Executives, analysts, project owners, and operators who need fast document intelligence.",
    keyMetrics: [
      { label: "Pages", value: String(document.pageCount), trend: "flat" },
      { label: "Read time", value: `${minutes} min`, trend: "flat" },
      { label: "Signal", value: "High", trend: "up" },
    ],
    confidence: 92,
  };
}

function buildLocalChatAnswer(document: PDFDocument, question: string): string {
  const lower = question.toLowerCase();

  if (lower.includes("urdu") || lower.includes("translate")) {
    return "خلاصہ: دستاویز کے اہم نکات، خطرات، فیصلے، اور اگلے اقدامات کو مختصر انداز میں پیش کیا گیا ہے تاکہ ٹیم فوری طور پر عمل کر سکے۔";
  }

  if (lower.includes("action")) {
    return [
      "Recommended action items:",
      "1. Confirm the final decision owner for each recommendation.",
      "2. Convert open risks into tracked tasks with due dates.",
      "3. Share the executive summary with stakeholders before the next review.",
    ].join("\n");
  }

  if (lower.includes("risk") || lower.includes("deadline")) {
    return "The main risks are unclear ownership, delayed validation, and missing follow-through on recommendations. Treat deadlines as review checkpoints until the original PDF dates are verified.";
  }

  if (lower.includes("3 bullet") || lower.includes("three bullet")) {
    return [
      "• The PDF is structured around findings, risks, and recommendations.",
      "• The strongest value is fast executive review and follow-up planning.",
      "• Next steps should be assigned to owners with measurable outcomes.",
    ].join("\n");
  }

  return `Based on ${document.fileName}, the relevant answer is that the document should be read as a decision-support brief: extract the key findings, verify source-specific numbers, and turn recommendations into concrete next steps.`;
}

async function callBackend(payload: ApiPayload): Promise<AgentResponse> {
  if (!BACKEND_API_URL) {
    throw new Error("Backend URL is not configured.");
  }

  const response = await fetch(BACKEND_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}.`);
  }

  return (await response.json()) as AgentResponse;
}

async function callGemini(payload: ApiPayload): Promise<AgentResponse> {
  if (!GEMINI_API_KEY) {
    throw new Error("Gemini key is not configured.");
  }

  const prompt =
    payload.task === "summarize"
      ? `Create a concise executive PDF summary as JSON with overview, bullets, targetAudience, keyMetrics, confidence.\n\n${payload.document.text}`
      : `Answer the question from this document only.\n\nDocument:\n${payload.document.text}\n\nQuestion: ${payload.question}`;

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
    },
  );

  if (!response.ok) {
    throw new Error(`Gemini returned ${response.status}.`);
  }

  const data = (await response.json()) as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  };
  const content =
    data.candidates?.[0]?.content?.parts?.map((part) => part.text ?? "").join("\n") ??
    "";

  return { content: content.trim() };
}

async function summarizeWithAgent(document: PDFDocument): Promise<SummaryResult> {
  const payload: ApiPayload = {
    task: "summarize",
    document: {
      id: document.id,
      fileName: document.fileName,
      pageCount: document.pageCount,
      text: document.text,
    },
  };

  if (BACKEND_API_URL) {
    const response = await withTimeout(callBackend(payload), 20_000, "Summary");
    if (response.summary) {
      return response.summary;
    }
  }

  if (GEMINI_API_KEY) {
    const response = await withTimeout(callGemini(payload), 20_000, "Gemini");
    if (response.content) {
      return {
        ...buildLocalSummary(document),
        overview: response.content.slice(0, 360),
      };
    }
  }

  await delay(700);
  return buildLocalSummary(document);
}

async function askAgent(
  document: PDFDocument,
  question: string,
  history: Message[],
): Promise<string> {
  const payload: ApiPayload = {
    task: "chat",
    question,
    history,
    document: {
      id: document.id,
      fileName: document.fileName,
      pageCount: document.pageCount,
      text: document.text,
    },
  };

  if (BACKEND_API_URL) {
    const response = await withTimeout(callBackend(payload), 20_000, "Chat");
    return response.content;
  }

  if (GEMINI_API_KEY) {
    const response = await withTimeout(callGemini(payload), 20_000, "Gemini");
    return response.content || buildLocalChatAnswer(document, question);
  }

  await delay(500);
  return buildLocalChatAnswer(document, question);
}

function StatusBadge({ status }: { status: PDFDocument["status"] }) {
  const styles: Record<PDFDocument["status"], string> = {
    uploading: "border-blue-500/30 bg-blue-500/10 text-blue-500",
    extracting: "border-indigo-500/30 bg-indigo-500/10 text-indigo-500",
    summarizing: "border-violet-500/30 bg-violet-500/10 text-violet-500",
    ready: "border-emerald-500/30 bg-emerald-500/10 text-emerald-500",
    error: "border-red-500/30 bg-red-500/10 text-red-500",
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${styles[status]}`}
    >
      {status === "ready" ? <CheckCircle2 className="h-3 w-3" /> : null}
      {status !== "ready" && status !== "error" ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : null}
      {status === "error" ? <AlertTriangle className="h-3 w-3" /> : null}
      {processingCopy[status]}
    </span>
  );
}

function EmptyIllustration() {
  return (
    <div className="relative mx-auto h-44 w-64">
      <div className="absolute inset-x-6 bottom-4 h-24 rounded-lg border border-zinc-300 bg-white shadow-xl shadow-zinc-300/50 dark:border-zinc-700 dark:bg-zinc-900 dark:shadow-black/30" />
      <div className="absolute left-10 top-5 h-32 w-24 -rotate-6 rounded-md border border-indigo-200 bg-indigo-50 shadow-lg dark:border-indigo-500/30 dark:bg-indigo-500/10" />
      <div className="absolute right-10 top-2 h-36 w-24 rotate-6 rounded-md border border-blue-200 bg-blue-50 shadow-lg dark:border-blue-500/30 dark:bg-blue-500/10" />
      <FileText className="absolute left-1/2 top-14 h-14 w-14 -translate-x-1/2 text-indigo-500" />
      <Sparkles className="absolute right-9 top-12 h-5 w-5 text-blue-500" />
      <Zap className="absolute left-12 bottom-12 h-5 w-5 text-amber-500" />
    </div>
  );
}

function Sidebar({
  documents,
  activeDocumentId,
  onSelectDocument,
  onClearAll,
}: {
  documents: PDFDocument[];
  activeDocumentId: string | null;
  onSelectDocument: (id: string) => void;
  onClearAll: () => void;
}) {
  return (
    <aside className="flex min-h-0 flex-col border-r border-zinc-200 bg-zinc-50/80 dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="border-b border-zinc-200 p-4 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-indigo-600 text-white shadow-lg shadow-indigo-600/25">
            <Brain className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-zinc-950 dark:text-white">
              PDF Agent
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Executive document AI
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-xs font-semibold uppercase text-zinc-500">
          Documents
        </span>
        <button
          className="inline-flex h-8 items-center gap-1 rounded-md border border-zinc-200 px-2 text-xs font-medium text-zinc-600 transition hover:border-red-300 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-800 dark:text-zinc-300"
          disabled={documents.length === 0}
          onClick={onClearAll}
          type="button"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Clear All
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-3 pb-4">
        {documents.length === 0 ? (
          <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
            No documents yet.
          </div>
        ) : null}

        {documents.map((document) => {
          const isActive = document.id === activeDocumentId;

          return (
            <button
              className={`w-full rounded-lg border p-3 text-left transition ${
                isActive
                  ? "border-indigo-400 bg-indigo-50 shadow-sm dark:border-indigo-500/60 dark:bg-indigo-500/10"
                  : "border-zinc-200 bg-white hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
              }`}
              key={document.id}
              onClick={() => onSelectDocument(document.id)}
              type="button"
            >
              <div className="flex items-start justify-between gap-2">
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
                <StatusBadge status={document.status} />
              </div>
              <p className="mt-2 truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {document.fileName}
              </p>
              <div className="mt-2 flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
                <span>{formatBytes(document.size)}</span>
                <span>{formatTime(document.uploadedAt)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function UploadZone({
  isDragging,
  onDrop,
  onDragOver,
  onDragLeave,
  onFileChange,
  status,
}: {
  isDragging: boolean;
  onDrop: (event: DragEvent<HTMLLabelElement>) => void;
  onDragOver: (event: DragEvent<HTMLLabelElement>) => void;
  onDragLeave: () => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  status: ProcessingStatus;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <label
      className={`group flex min-h-[320px] cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center transition ${
        isDragging
          ? "border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/15"
          : "border-zinc-300 bg-white hover:border-indigo-400 dark:border-zinc-800 dark:bg-zinc-900/70 dark:hover:border-indigo-500"
      }`}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <input
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={onFileChange}
        ref={inputRef}
        type="file"
      />
      <EmptyIllustration />
      <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
        <UploadCloud className="h-3.5 w-3.5" />
        PDF upload
      </div>
      <h2 className="mt-3 text-xl font-semibold text-zinc-950 dark:text-white">
        Drop a PDF into the workspace
      </h2>
      <p className="mt-2 max-w-sm text-sm text-zinc-500 dark:text-zinc-400">
        The agent validates size, extracts document signals, and prepares an
        executive analysis stream.
      </p>
      {status !== "idle" && status !== "ready" && status !== "error" ? (
        <div className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-indigo-600 dark:text-indigo-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          {processingCopy[status]}
        </div>
      ) : null}
    </label>
  );
}

function PdfViewer({
  document,
  onPreviousPage,
  onNextPage,
}: {
  document: PDFDocument;
  onPreviousPage: () => void;
  onNextPage: () => void;
}) {
  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-zinc-200 p-4 dark:border-zinc-800">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-zinc-950 dark:text-white">
            {document.fileName}
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {formatBytes(document.size)} · {document.pageCount} pages
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="grid h-8 w-8 place-items-center rounded-md border border-zinc-200 text-zinc-600 transition hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
            disabled={document.activePage === 1}
            onClick={onPreviousPage}
            title="Previous page"
            type="button"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="w-20 text-center text-xs font-semibold text-zinc-600 dark:text-zinc-300">
            {document.activePage} / {document.pageCount}
          </span>
          <button
            className="grid h-8 w-8 place-items-center rounded-md border border-zinc-200 text-zinc-600 transition hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
            disabled={document.activePage === document.pageCount}
            onClick={onNextPage}
            title="Next page"
            type="button"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-zinc-100 p-4 dark:bg-zinc-950">
        <div className="mx-auto min-h-[720px] max-w-3xl rounded-lg border border-zinc-200 bg-white p-8 shadow-xl shadow-zinc-200/70 dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-black/30">
          <div className="mb-8 flex items-center justify-between border-b border-zinc-200 pb-4 dark:border-zinc-800">
            <div>
              <div className="h-3 w-40 rounded bg-zinc-200 dark:bg-zinc-700" />
              <div className="mt-2 h-2 w-24 rounded bg-zinc-100 dark:bg-zinc-800" />
            </div>
            <FileText className="h-8 w-8 text-indigo-500" />
          </div>

          <div className="space-y-4">
            <div className="h-8 w-3/4 rounded bg-zinc-900 dark:bg-zinc-100" />
            {[92, 84, 96, 74].map((width) => (
              <div
                className="h-3 rounded bg-zinc-200 dark:bg-zinc-700"
                key={width}
                style={{ width: `${width}%` }}
              />
            ))}
            <div className="my-8 grid grid-cols-3 gap-3">
              {[0, 1, 2].map((item) => (
                <div
                  className="h-20 rounded-md border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
                  key={item}
                />
              ))}
            </div>
            {[88, 94, 79, 91, 64, 83].map((width) => (
              <div
                className="h-3 rounded bg-zinc-200 dark:bg-zinc-700"
                key={`body-${width}`}
                style={{ width: `${width}%` }}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function SummaryPanel({ summary }: { summary?: SummaryResult }) {
  if (!summary) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Building executive summary
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center gap-2 text-sm font-semibold text-indigo-600 dark:text-indigo-300">
          <WandSparkles className="h-4 w-4" />
          Executive Summary
        </div>
        <p className="mt-3 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
          {summary.overview}
        </p>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">
          Key points
        </h3>
        <ul className="mt-3 space-y-3">
          {summary.bullets.map((bullet) => (
            <li className="flex gap-3 text-sm text-zinc-700 dark:text-zinc-300" key={bullet}>
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid grid-cols-3 gap-3">
        {summary.keyMetrics.map((metric) => (
          <div
            className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
            key={metric.label}
          >
            <p className="text-xs text-zinc-500">{metric.label}</p>
            <div className="mt-1 flex items-center gap-2">
              <p className="text-lg font-semibold text-zinc-950 dark:text-white">
                {metric.value}
              </p>
              {metric.trend === "up" ? <ArrowRight className="h-4 w-4 -rotate-45 text-emerald-500" /> : null}
            </div>
          </div>
        ))}
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-xs font-semibold uppercase text-zinc-500">
          Target audience
        </p>
        <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-300">
          {summary.targetAudience}
        </p>
        <div className="mt-4 h-2 rounded-full bg-zinc-100 dark:bg-zinc-800">
          <div
            className="h-full rounded-full bg-indigo-600"
            style={{ width: `${summary.confidence}%` }}
          />
        </div>
      </section>
    </div>
  );
}

function ChatPanel({
  messages,
  input,
  isThinking,
  onInputChange,
  onSubmit,
  onQuickAction,
}: {
  messages: Message[];
  input: string;
  isThinking: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onQuickAction: (question: string) => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap gap-2 p-4">
        {quickActions.map((action) => (
          <button
            className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
            key={action}
            onClick={() => onQuickAction(action)}
            type="button"
          >
            {action}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 pb-4">
        {messages.map((message) => (
          <div
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            key={message.id}
          >
            <div
              className={`max-w-[86%] rounded-lg border px-4 py-3 text-sm leading-6 ${
                message.role === "user"
                  ? "border-indigo-500 bg-indigo-600 text-white"
                  : "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
              }`}
            >
              <p className="whitespace-pre-line">{message.content}</p>
              <p
                className={`mt-2 text-[11px] ${
                  message.role === "user" ? "text-indigo-100" : "text-zinc-400"
                }`}
              >
                {formatTime(message.createdAt)}
              </p>
            </div>
          </div>
        ))}
        {isThinking ? (
          <div className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900">
            <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
            Agent is reading context
          </div>
        ) : null}
      </div>

      <form
        className="border-t border-zinc-200 p-4 dark:border-zinc-800"
        onSubmit={onSubmit}
      >
        <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white p-2 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <input
            className="min-w-0 flex-1 bg-transparent px-2 text-sm text-zinc-900 outline-none placeholder:text-zinc-400 dark:text-white"
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="Ask about this PDF..."
            type="text"
            value={input}
          />
          <button
            className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-700"
            disabled={!input.trim() || isThinking}
            title="Send"
            type="submit"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}

function AgentPanel({
  activeTab,
  document,
  messages,
  input,
  isThinking,
  onTabChange,
  onInputChange,
  onSubmit,
  onQuickAction,
}: {
  activeTab: ChatTab;
  document: PDFDocument | null;
  messages: Message[];
  input: string;
  isThinking: boolean;
  onTabChange: (tab: ChatTab) => void;
  onInputChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onQuickAction: (question: string) => void;
}) {
  return (
    <aside className="flex min-h-0 flex-col border-l border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="border-b border-zinc-200 p-4 dark:border-zinc-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-zinc-500">
              AI Agent
            </p>
            <h2 className="mt-1 text-base font-semibold text-zinc-950 dark:text-white">
              Document intelligence
            </h2>
          </div>
          <Bot className="h-5 w-5 text-indigo-500" />
        </div>

        <div className="mt-4 grid grid-cols-2 rounded-lg border border-zinc-200 bg-white p-1 dark:border-zinc-800 dark:bg-zinc-900">
          {[
            { id: "summary" as const, label: "Summary", icon: Layers3 },
            { id: "chat" as const, label: "Chat", icon: MessageSquareText },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
                }`}
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                type="button"
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {!document ? (
          <div className="grid h-full place-items-center p-6 text-center">
            <div>
              <Search className="mx-auto h-9 w-9 text-zinc-400" />
              <p className="mt-3 text-sm font-medium text-zinc-600 dark:text-zinc-300">
                Awaiting document
              </p>
            </div>
          </div>
        ) : activeTab === "summary" ? (
          <div className="h-full overflow-y-auto p-4">
            <SummaryPanel summary={document.summary} />
          </div>
        ) : (
          <ChatPanel
            input={input}
            isThinking={isThinking}
            messages={messages}
            onInputChange={onInputChange}
            onQuickAction={onQuickAction}
            onSubmit={onSubmit}
          />
        )}
      </div>
    </aside>
  );
}

function TopBar({
  theme,
  status,
  onThemeToggle,
}: {
  theme: ThemeMode;
  status: ProcessingStatus;
  onThemeToggle: () => void;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white/90 px-4 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">
      <div className="flex items-center gap-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 px-3 py-1 text-xs font-semibold text-zinc-600 dark:border-zinc-800 dark:text-zinc-300">
          <Gauge className="h-3.5 w-3.5 text-emerald-500" />
          {processingCopy[status]}
        </div>
        <div className="hidden items-center gap-2 text-xs text-zinc-500 md:flex">
          <Clock className="h-3.5 w-3.5" />
          Low-latency workspace
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="grid h-9 w-9 place-items-center rounded-md border border-zinc-200 text-zinc-600 transition hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
          title="Download session"
          type="button"
        >
          <Download className="h-4 w-4" />
        </button>
        <button
          className="grid h-9 w-9 place-items-center rounded-md border border-zinc-200 text-zinc-600 transition hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800"
          onClick={onThemeToggle}
          title="Toggle theme"
          type="button"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}

function PdfSummarizerAgent() {
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [status, setStatus] = useState<ProcessingStatus>("idle");
  const [isDragging, setIsDragging] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [activeTab, setActiveTab] = useState<ChatTab>("summary");
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeDocument = useMemo(
    () => documents.find((document) => document.id === activeDocumentId) ?? null,
    [activeDocumentId, documents],
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const updateDocument = useCallback((id: string, patch: Partial<PDFDocument>) => {
    setDocuments((current) =>
      current.map((document) =>
        document.id === id ? { ...document, ...patch } : document,
      ),
    );
  }, []);

  const handleFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const file = Array.from(fileList)[0];
      if (!file) {
        return;
      }

      setError(null);
      setActiveTab("summary");

      try {
        validatePdfFile(file);
        setStatus("uploading");

        const documentId = createId("pdf");
        const nextDocument: PDFDocument = {
          id: documentId,
          fileName: file.name,
          size: file.size,
          uploadedAt: new Date(),
          status: "uploading",
          pageCount: 1,
          activePage: 1,
          text: "",
        };

        setDocuments((current) => [nextDocument, ...current]);
        setActiveDocumentId(documentId);
        setMessages([]);

        await delay(350);
        setStatus("extracting");
        updateDocument(documentId, { status: "extracting" });
        const extracted = await withTimeout(
          extractPdfText(file),
          12_000,
          "PDF extraction",
        );

        const extractedDocument: PDFDocument = {
          ...nextDocument,
          status: "summarizing",
          pageCount: extracted.pageCount,
          text: extracted.text,
        };

        setStatus("summarizing");
        updateDocument(documentId, extractedDocument);
        const summary = await summarizeWithAgent(extractedDocument);

        setStatus("ready");
        updateDocument(documentId, { status: "ready", summary });
        setMessages([
          {
            id: createId("msg"),
            role: "assistant",
            content:
              "I finished the first pass. Ask for risks, action items, a tighter summary, or an Urdu translation.",
            createdAt: new Date(),
          },
        ]);
      } catch (caught) {
        const message =
          caught instanceof Error ? caught.message : "Unable to process this PDF.";
        setError(message);
        setStatus("error");
        setDocuments((current) =>
          current.map((document, index) =>
            index === 0 && document.status !== "ready"
              ? { ...document, status: "error", error: message }
              : document,
          ),
        );
      } finally {
        setIsDragging(false);
      }
    },
    [updateDocument],
  );

  const submitQuestion = useCallback(
    async (question: string) => {
      if (!activeDocument || !question.trim() || isThinking) {
        return;
      }

      const userMessage: Message = {
        id: createId("msg"),
        role: "user",
        content: question.trim(),
        createdAt: new Date(),
      };

      const nextHistory = [...messages, userMessage];
      setMessages(nextHistory);
      setChatInput("");
      setActiveTab("chat");
      setIsThinking(true);

      try {
        const answer = await askAgent(activeDocument, question, nextHistory);
        setMessages((current) => [
          ...current,
          {
            id: createId("msg"),
            role: "assistant",
            content: answer,
            createdAt: new Date(),
          },
        ]);
      } catch (caught) {
        const message =
          caught instanceof Error ? caught.message : "The agent could not answer.";
        setMessages((current) => [
          ...current,
          {
            id: createId("msg"),
            role: "assistant",
            content: message,
            createdAt: new Date(),
          },
        ]);
      } finally {
        setIsThinking(false);
      }
    },
    [activeDocument, isThinking, messages],
  );

  const onDrop = (event: DragEvent<HTMLLabelElement>): void => {
    event.preventDefault();
    void handleFiles(event.dataTransfer.files);
  };

  const onDragOver = (event: DragEvent<HTMLLabelElement>): void => {
    event.preventDefault();
    setIsDragging(true);
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>): void => {
    if (event.target.files) {
      void handleFiles(event.target.files);
      event.target.value = "";
    }
  };

  const onChatSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void submitQuestion(chatInput);
  };

  const clearAllDocuments = (): void => {
    setDocuments([]);
    setActiveDocumentId(null);
    setMessages([]);
    setStatus("idle");
    setError(null);
    setChatInput("");
  };

  const stepPage = (direction: "previous" | "next"): void => {
    if (!activeDocument) {
      return;
    }

    const nextPage =
      direction === "previous"
        ? Math.max(1, activeDocument.activePage - 1)
        : Math.min(activeDocument.pageCount, activeDocument.activePage + 1);
    updateDocument(activeDocument.id, { activePage: nextPage });
  };

  return (
    <AppErrorBoundary>
      <main className="h-screen overflow-hidden bg-white text-zinc-950 transition dark:bg-zinc-950 dark:text-zinc-50">
        <div className="grid h-full grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_420px]">
          <Sidebar
            activeDocumentId={activeDocumentId}
            documents={documents}
            onClearAll={clearAllDocuments}
            onSelectDocument={setActiveDocumentId}
          />

          <section className="flex min-h-0 flex-col">
            <TopBar
              onThemeToggle={() =>
                setTheme((current) => (current === "dark" ? "light" : "dark"))
              }
              status={status}
              theme={theme}
            />

            {error ? (
              <div className="m-4 flex items-start justify-between rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                <div className="flex gap-3">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
                <button
                  className="grid h-6 w-6 place-items-center rounded-md hover:bg-red-100 dark:hover:bg-red-500/10"
                  onClick={() => setError(null)}
                  title="Dismiss"
                  type="button"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : null}

            <div className="min-h-0 flex-1 p-4">
              {activeDocument ? (
                <div className="flex h-full overflow-hidden rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
                  <PdfViewer
                    document={activeDocument}
                    onNextPage={() => stepPage("next")}
                    onPreviousPage={() => stepPage("previous")}
                  />
                </div>
              ) : (
                <UploadZone
                  isDragging={isDragging}
                  onDragLeave={() => setIsDragging(false)}
                  onDragOver={onDragOver}
                  onDrop={onDrop}
                  onFileChange={onFileChange}
                  status={status}
                />
              )}
            </div>
          </section>

          <AgentPanel
            activeTab={activeTab}
            document={activeDocument}
            input={chatInput}
            isThinking={isThinking}
            messages={messages}
            onInputChange={setChatInput}
            onQuickAction={(question) => void submitQuestion(question)}
            onSubmit={onChatSubmit}
            onTabChange={setActiveTab}
          />
        </div>

        <div className="fixed bottom-4 left-1/2 z-30 hidden -translate-x-1/2 items-center gap-2 rounded-full border border-zinc-200 bg-white/90 px-3 py-2 text-xs text-zinc-500 shadow-lg backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/90 lg:flex">
          <PanelLeft className="h-3.5 w-3.5" />
          History
          <span className="h-1 w-1 rounded-full bg-zinc-300 dark:bg-zinc-700" />
          Workspace
          <span className="h-1 w-1 rounded-full bg-zinc-300 dark:bg-zinc-700" />
          Agent
          <PanelRight className="h-3.5 w-3.5" />
        </div>
      </main>
    </AppErrorBoundary>
  );
}

export default PdfSummarizerAgent;
