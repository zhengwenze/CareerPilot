'use client';

import Link from 'next/link';
import { useEffect, useRef, useState, type ChangeEvent, type ReactNode } from 'react';
import { ArrowUpRight, Download, FileUp, Sparkles } from 'lucide-react';

import { useAuth } from '@/components/auth-provider';
import { PaperInput, PaperTextarea } from '@/components/brutalist/form-controls';
import { MetaChip, PageHeader, PageShell, PaperSection } from '@/components/brutalist/page-shell';
import { PageEmptyState } from '@/components/page-state';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Timer } from '@/components/ui/timer';
import { ApiError } from '@/lib/api/client';
import {
  createJob,
  createEmptyJobDraft,
  fetchJobDetail,
  fetchJobList,
  type JobDraft,
  type JobRecord,
  toJobDraft,
  updateJob,
} from '@/lib/api/modules/jobs';
import {
  fetchTailoredResumeWorkflowDetail,
  convertResumePdfToMarkdown,
  recordTailoredResumeEvent,
  retryResumeParse,
  downloadTailoredResumeMarkdown,
  fetchResumeDetail,
  fetchResumeList,
  fetchTailoredResumeWorkflows,
  optimizeTailoredResume,
  retryTailoredResumeGeneration,
  updateResumeStructuredData,
  uploadPrimaryResume,
  type ContentSegmentRecord,
  type PdfToMarkdownConversionResult,
  type ResumeRecord,
  type ResumeStructuredData,
  type TailoredResumeArtifactRecord,
  type TailoredResumeWorkflowRecord,
} from '@/lib/api/modules/resume';
import { cn } from '@/lib/utils';
import { ResumeStatusIndicator } from '@/components/resume-status-indicator';
import { JobStatusIndicator } from '@/components/job-status-indicator';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '操作失败，请稍后重试。';
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

type WorkflowDisplayStatus = TailoredResumeArtifactRecord['display_status'];

const TERMINAL_WORKFLOW_STATUSES = new Set<WorkflowDisplayStatus>([
  'success',
  'failed',
  'cancelled',
  'returned',
  'aborted',
  'empty_result',
]);

function getFitBandLabel(value: string) {
  const labels: Record<string, string> = {
    excellent: '强适配',
    strong: '较强适配',
    partial: '部分适配',
    weak: '低适配',
    unknown: '待评估',
  };
  return labels[value] ?? value;
}

function getCanonicalResumeMarkdown(resume: ResumeRecord | null) {
  if (!resume) {
    return '';
  }
  return resume.parse_artifacts_json?.canonical_resume_md?.trim() || resume.raw_text?.trim() || '';
}

function getResumeAiDebug(
  source: PdfToMarkdownConversionResult | ResumeRecord['parse_artifacts_json'] | null | undefined
) {
  if (!source) {
    return null;
  }
  return {
    aiUsed: source.ai_used,
    provider: source.ai_provider,
    model: source.ai_model,
    error: source.ai_error,
    fallbackUsed: source.fallback_used,
    promptVersion: source.prompt_version,
    latencyMs: source.ai_latency_ms,
    aiPath: source.ai_path,
    attempts: source.ai_attempts ?? [],
    chainLatencyMs: source.ai_chain_latency_ms,
    degradedUsed: source.degraded_used,
  };
}

function hasResumeAiDebug(
  source: PdfToMarkdownConversionResult | ResumeRecord['parse_artifacts_json'] | null | undefined
) {
  if (!source) {
    return false;
  }
  return Boolean(
    source.ai_used ||
    source.fallback_used ||
    source.ai_error ||
    source.ai_provider ||
    source.ai_model ||
    source.prompt_version ||
    source.ai_latency_ms !== null ||
    source.ai_chain_latency_ms !== null ||
    source.degraded_used ||
    Boolean(source.ai_path) ||
    (source.ai_attempts?.length ?? 0) > 0
  );
}

function formatAttemptLine(
  stage: string,
  provider: string,
  model: string,
  status: string,
  latencyMs: number | null,
  error: string | null
) {
  const providerModel = [provider, model].filter(Boolean).join('/') || 'n/a';
  const latency = latencyMs === null ? 'n/a' : `${latencyMs} ms`;
  const suffix = error ? ` | error: ${error}` : '';
  return `${stage}: ${providerModel} | status: ${status} | latency: ${latency}${suffix}`;
}

function normalizeMarkdown(md: string) {
  return md.replace(/\r\n/g, '\n').trim();
}

const AUTO_SAVE_SECTION_TITLES = new Set([
  '个人简介',
  'summary',
  '专业技能',
  '技能',
  'skills',
  '工作经历',
  'work experience',
  'experience',
  '项目经历',
  'projects',
  '教育经历',
  '教育背景',
  'education',
]);

function looksLikeNameHeading(line: string) {
  const candidate = line.replace(/^#\s+/, '').trim();
  if (!candidate) {
    return false;
  }
  if (candidate.length > 40) {
    return false;
  }
  if (candidate.includes('@')) {
    return false;
  }
  if (candidate.startsWith('http://') || candidate.startsWith('https://')) {
    return false;
  }
  return true;
}

function isLikelyAutoSaveSafe(markdown: string) {
  const lines = normalizeMarkdown(markdown)
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return false;
  }

  const firstContentLine = lines[0] ?? '';
  const hasNameSignal = looksLikeNameHeading(firstContentLine);
  const hasSectionSignal = lines.some(line => {
    const normalized = line
      .replace(/^##\s+/, '')
      .trim()
      .toLowerCase();
    return AUTO_SAVE_SECTION_TITLES.has(normalized);
  });

  return hasNameSignal && hasSectionSignal;
}

function pickSection(markdown: string, names: string[]) {
  const lines = normalizeMarkdown(markdown).split('\n');
  const sections = new Map<string, string[]>();
  let current = '__root__';
  sections.set(current, []);

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const headingMatch = line.match(/^##\s+(.+)$/);
    if (headingMatch) {
      current = headingMatch[1].trim().toLowerCase();
      sections.set(current, []);
      continue;
    }
    sections.get(current)?.push(line);
  }

  for (const name of names) {
    const value = sections.get(name.toLowerCase());
    if (value) {
      return value;
    }
  }
  return [];
}

function cleanList(lines: string[]) {
  return lines
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => line.replace(/^[-*]\s*/, '').trim())
    .filter(Boolean);
}

function markdownToStructuredResume(markdown: string): ResumeStructuredData {
  const normalized = normalizeMarkdown(markdown);
  const lines = normalized.split('\n');
  const name =
    lines
      .find(line => line.trim().startsWith('# '))
      ?.replace(/^#\s+/, '')
      .trim() ?? '';
  const introLines: string[] = [];
  for (const line of lines.slice(1)) {
    if (line.trim().startsWith('## ')) {
      break;
    }
    introLines.push(line.trim());
  }

  const infoMap = new Map<string, string>();
  for (const line of introLines) {
    const bullet = line.replace(/^[-*]\s*/, '').trim();
    const [label, ...rest] = bullet.split('：');
    if (rest.length > 0) {
      infoMap.set(label.trim(), rest.join('：').trim());
    }
  }

  const skills = cleanList(
    pickSection(normalized, ['专业技能', '技能', 'skills']).flatMap(line => line.split(/[,，]/))
  );
  const education = cleanList(pickSection(normalized, ['教育经历', 'education']));
  const workExperience = cleanList(pickSection(normalized, ['工作经验', 'work experience']));
  const projects = cleanList(pickSection(normalized, ['项目经历', 'projects']));
  const certifications = cleanList(pickSection(normalized, ['证书', 'certificates']));

  return {
    basic_info: {
      name,
      email: infoMap.get('邮箱') ?? '',
      phone: infoMap.get('电话') ?? '',
      location: infoMap.get('所在地') ?? '',
      summary: infoMap.get('求职方向') ?? '',
    },
    education,
    work_experience: workExperience,
    projects,
    skills: {
      technical: skills,
      tools: [],
      languages: [],
    },
    certifications,
  };
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern =
    /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*]+)\*\*|__([^_]+)__|`([^`]+)`|\*([^*]+)\*|_([^_]+)_)/g;
  let lastIndex = 0;
  let key = 0;

  for (const match of text.matchAll(pattern)) {
    const matched = match[0];
    const start = match.index ?? 0;
    if (start > lastIndex) {
      nodes.push(text.slice(lastIndex, start));
    }

    if (match[2] && match[3]) {
      nodes.push(
        <a
          key={`inline-${key}`}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
          className="text-[#111111] underline underline-offset-2"
        >
          {match[2]}
        </a>
      );
    } else if (match[4] || match[5]) {
      nodes.push(
        <strong key={`inline-${key}`} className="font-semibold text-[#1C1C1C]">
          {match[4] ?? match[5]}
        </strong>
      );
    } else if (match[6]) {
      nodes.push(
        <code
          key={`inline-${key}`}
          className="rounded bg-[#1C1C1C]/6 px-1 py-0.5 text-[0.95em] text-[#1C1C1C]"
        >
          {match[6]}
        </code>
      );
    } else if (match[7] || match[8]) {
      nodes.push(
        <em key={`inline-${key}`} className="italic">
          {match[7] ?? match[8]}
        </em>
      );
    } else {
      nodes.push(matched);
    }

    lastIndex = start + matched.length;
    key += 1;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length ? nodes : [text];
}

function ResumeMarkdownPreview({ markdown }: { markdown: string }) {
  const lines = markdown.split('\n');
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = (key: string) => {
    if (!listItems.length) {
      return;
    }
    nodes.push(
      <ul key={key} className="my-3 list-disc space-y-2 pl-5 text-sm leading-7 text-[#1C1C1C]">
        {listItems.map((item, index) => (
          <li key={`${key}-${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim();
    if (!line) {
      flushList(`list-${index}`);
      return;
    }

    if (line.startsWith('- ')) {
      listItems.push(line.slice(2).trim());
      return;
    }

    flushList(`list-${index}`);

    if (line.startsWith('### ')) {
      nodes.push(
        <h3 key={`h3-${index}`} className="mt-5 text-base font-semibold text-[#1C1C1C]">
          {renderInlineMarkdown(line.slice(4))}
        </h3>
      );
      return;
    }

    if (line.startsWith('## ')) {
      nodes.push(
        <h2
          key={`h2-${index}`}
          className="mt-6 border-t border-[#1C1C1C]/10 pt-6 text-lg font-semibold text-[#1C1C1C]"
        >
          {renderInlineMarkdown(line.slice(3))}
        </h2>
      );
      return;
    }

    if (line.startsWith('# ')) {
      nodes.push(
        <h1 key={`h1-${index}`} className="text-2xl font-semibold text-[#1C1C1C]">
          {renderInlineMarkdown(line.slice(2))}
        </h1>
      );
      return;
    }

    nodes.push(
      <p
        key={`p-${index}`}
        className={cn(
          'text-sm leading-7 text-[#1C1C1C]/80',
          /^\d{4}[./-]\d{1,2}\s*-\s*/.test(line) || /^\d{4}\s*-\s*\d{4}/.test(line)
            ? 'font-medium text-[#1C1C1C]'
            : ''
        )}
      >
        {renderInlineMarkdown(line)}
      </p>
    );
  });

  flushList('list-final');
  return <div className="space-y-1">{nodes}</div>;
}

function isTerminalWorkflowStatus(status: WorkflowDisplayStatus | null | undefined) {
  return status ? TERMINAL_WORKFLOW_STATUSES.has(status) : false;
}

function isInterviewReadyWorkflow(workflow: TailoredResumeWorkflowRecord | null) {
  return Boolean(
    workflow &&
    workflow.target_job.id &&
    workflow.tailored_resume.session_id &&
    workflow.tailored_resume.display_status === 'success' &&
    workflow.tailored_resume.downloadable
  );
}

function getWorkflowStatusLabel(status: WorkflowDisplayStatus | null | undefined) {
  switch (status) {
    case 'success':
      return '生成成功';
    case 'failed':
      return '生成失败';
    case 'processing':
      return '后台处理中';
    case 'segment_progress':
      return '分段生成中';
    case 'cancelled':
      return '任务已取消';
    case 'returned':
      return '任务已退回';
    case 'aborted':
      return '任务已中断';
    case 'empty_result':
      return '生成结束但无结果';
    default:
      return '未开始';
  }
}

function getWorkflowStatusTone(status: WorkflowDisplayStatus | null | undefined) {
  switch (status) {
    case 'success':
      return 'border-[#111111] bg-[#111111] text-[#fafafa]';
    case 'failed':
    case 'cancelled':
    case 'returned':
    case 'aborted':
    case 'empty_result':
      return 'border-[#111111] bg-[#f5f5f5] text-[#111111]';
    case 'processing':
    case 'segment_progress':
      return 'border-[#111111] bg-[#fafafa] text-[#111111]';
    default:
      return 'border-[#e5e5e5] bg-[#fafafa] text-[#111111]';
  }
}

function getWorkflowPrimaryMessage(workflow: TailoredResumeWorkflowRecord | null) {
  if (!workflow) {
    return '还没有开始生成优化简历。';
  }
  return (
    workflow.tailored_resume.error_message ||
    workflow.tailored_resume.task_state?.message ||
    '等待任务状态。'
  );
}

function getWorkflowSecondaryMessage(workflow: TailoredResumeWorkflowRecord | null) {
  if (!workflow) {
    return '先完成简历和岗位 JD 保存，再发起生成。';
  }

  const displayStatus = workflow.tailored_resume.display_status;
  const totalSteps =
    workflow.tailored_resume.task_state?.total_steps ||
    workflow.tailored_resume.segments?.length ||
    0;
  const currentStep = workflow.tailored_resume.task_state?.current_step || 0;

  switch (displayStatus) {
    case 'processing':
    case 'segment_progress':
      return `阶段：${workflow.tailored_resume.task_state?.phase || 'queued'} · 进度 ${currentStep}/${totalSteps || 1}`;
    case 'success':
      return workflow.tailored_resume.downloadable
        ? '当前最新结果已可下载。'
        : '当前任务已结束，但下载结果不可用。';
    case 'empty_result':
      return '流程已结束，但没有产出可下载的优化简历内容，可直接重试。';
    case 'failed':
      return workflow.tailored_resume.retryable ? '本次生成失败，可直接重试。' : '本次生成失败。';
    case 'cancelled':
    case 'returned':
    case 'aborted':
      return '本次任务未正常完成，可重新发起生成。';
    default:
      return '任务尚未开始。';
  }
}

function getSegmentStatusLabel(status: ContentSegmentRecord['status']) {
  switch (status) {
    case 'success':
      return '已完成';
    case 'failed':
      return '失败';
    case 'processing':
      return '进行中';
    default:
      return '待处理';
  }
}

function SegmentCard({ segment }: { segment: ContentSegmentRecord }) {
  return (
    <div className="border border-[#e5e5e5] bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <MetaChip>{segment.label}</MetaChip>
        <MetaChip>{getSegmentStatusLabel(segment.status)}</MetaChip>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/45">
            原内容
          </p>
          <div className="border border-[#e5e5e5] bg-[#fafafa] p-4 text-sm leading-7 text-[#1C1C1C]/68 whitespace-pre-wrap">
            {segment.original_text || '暂无'}
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/45">
            优化后
          </p>
          <div className="border border-[#e5e5e5] bg-[#fafafa] p-4 text-sm leading-7 text-[#1C1C1C] whitespace-pre-wrap">
            {segment.suggested_text || '处理中'}
          </div>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="border border-[#e5e5e5] bg-[#fafafa] p-4">
          <p className="text-xs font-semibold text-[#1C1C1C]/50">改了什么</p>
          <p className="mt-2 text-sm leading-6 text-[#1C1C1C]/72">
            {segment.explanation.what || '保持原有结构，仅做保守优化。'}
          </p>
        </div>
        <div className="border border-[#e5e5e5] bg-[#fafafa] p-4">
          <p className="text-xs font-semibold text-[#1C1C1C]/50">为什么这样改</p>
          <p className="mt-2 text-sm leading-6 text-[#1C1C1C]/72">
            {segment.explanation.why || '优先贴合岗位重点，但不新增事实。'}
          </p>
        </div>
        <div className="border border-[#e5e5e5] bg-[#fafafa] p-4">
          <p className="text-xs font-semibold text-[#1C1C1C]/50">这样改的价值</p>
          <p className="mt-2 text-sm leading-6 text-[#1C1C1C]/72">
            {segment.explanation.value || '让招聘方更快看到相关证据。'}
          </p>
        </div>
      </div>
      {segment.error_message ? (
        <p className="mt-3 text-sm text-[#111111]">{segment.error_message}</p>
      ) : null}
    </div>
  );
}

function upsertWorkflowRecord(
  current: TailoredResumeWorkflowRecord[],
  nextWorkflow: TailoredResumeWorkflowRecord
) {
  const filtered = current.filter(
    item => item.tailored_resume.session_id !== nextWorkflow.tailored_resume.session_id
  );
  return [nextWorkflow, ...filtered].sort(
    (left, right) =>
      Date.parse(right.tailored_resume.updated_at) - Date.parse(left.tailored_resume.updated_at)
  );
}

export default function DashboardResumePage() {
  const { token } = useAuth();
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const [resume, setResume] = useState<ResumeRecord | null>(null);
  const [resumeMarkdown, setResumeMarkdown] = useState('');
  const [latestPdfConversion, setLatestPdfConversion] =
    useState<PdfToMarkdownConversionResult | null>(null);
  const [jobDraft, setJobDraft] = useState<JobDraft>(createEmptyJobDraft());
  const [savedJob, setSavedJob] = useState<JobRecord | null>(null);
  const [workflowList, setWorkflowList] = useState<TailoredResumeWorkflowRecord[]>([]);
  const [workflow, setWorkflow] = useState<TailoredResumeWorkflowRecord | null>(null);
  const [pageError, setPageError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isSavingResume, setIsSavingResume] = useState(false);
  const [isRetryingResumeParse, setIsRetryingResumeParse] = useState(false);
  const [isSavingJob, setIsSavingJob] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isRetryingWorkflow, setIsRetryingWorkflow] = useState(false);
  const [generateStartTime, setGenerateStartTime] = useState<number | null>(null);

  const workflowDisplayStatus = workflow?.tailored_resume.display_status ?? 'idle';
  const isWorkflowProcessing =
    workflowDisplayStatus === 'processing' || workflowDisplayStatus === 'segment_progress';
  const latestSuccessfulWorkflow =
    workflowList.find(item => {
      if (!resume?.id || !savedJob?.id || !workflow?.tailored_resume.session_id) {
        return false;
      }
      return (
        item.resume.id === resume.id &&
        item.target_job.id === savedJob.id &&
        item.tailored_resume.display_status === 'success' &&
        item.tailored_resume.session_id !== workflow.tailored_resume.session_id
      );
    }) ?? null;
  const canDownloadCurrentWorkflow = Boolean(
    workflow &&
    workflow.tailored_resume.display_status === 'success' &&
    workflow.tailored_resume.downloadable
  );
  const canRetryWorkflow = Boolean(workflow && workflow.tailored_resume.retryable);
  const interviewEntryWorkflow = isInterviewReadyWorkflow(workflow)
    ? workflow
    : isInterviewReadyWorkflow(latestSuccessfulWorkflow)
      ? latestSuccessfulWorkflow
      : null;
  const canStartInterview = Boolean(interviewEntryWorkflow);
  const isDevelopment = process.env.NODE_ENV === 'development';
  const immediateAiDebug = getResumeAiDebug(latestPdfConversion);
  const persistedAiDebug = getResumeAiDebug(resume?.parse_artifacts_json);
  const hasImmediateAiDebug = hasResumeAiDebug(latestPdfConversion);
  const hasPersistedAiDebug = hasResumeAiDebug(resume?.parse_artifacts_json);

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    async function bootstrap() {
      setPageError('');

      try {
        const [resumes, jobs, workflows] = await Promise.all([
          fetchResumeList(token!),
          fetchJobList(token!),
          fetchTailoredResumeWorkflows(token!).catch(() => []),
        ]);
        if (cancelled) {
          return;
        }

        const nextResume = resumes[0] ?? null;
        const nextSavedJob = jobs[0] ?? null;
        const nextWorkflow =
          workflows.find(
            item => item.resume.id === nextResume?.id && item.target_job.id === nextSavedJob?.id
          ) ?? null;

        setResume(nextResume);
        setLatestPdfConversion(null);
        setResumeMarkdown(current => current || getCanonicalResumeMarkdown(nextResume));
        setSavedJob(nextSavedJob);
        setJobDraft(nextSavedJob ? toJobDraft(nextSavedJob) : createEmptyJobDraft());
        setWorkflowList(workflows);
        setWorkflow(nextWorkflow);
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token || !resume?.id) {
      return;
    }
    if (!['pending', 'processing'].includes(resume.parse_status)) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextResume = await fetchResumeDetail(token, resume.id);
        setResume(nextResume);
        const nextMarkdown = getCanonicalResumeMarkdown(nextResume);
        if (nextMarkdown) {
          setResumeMarkdown(nextMarkdown);
        }
      } catch {
        // keep the last visible state until the next retry
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [resume?.id, resume?.parse_status, token]);

  useEffect(() => {
    if (!token || !savedJob?.id) {
      return;
    }
    if (!['pending', 'processing'].includes(savedJob.parse_status)) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextJob = await fetchJobDetail(token, savedJob.id);
        setSavedJob(nextJob);
        setJobDraft(current => (current.jd_text.trim() ? current : toJobDraft(nextJob)));
      } catch {
        // keep the last visible state until the next retry
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [savedJob?.id, savedJob?.parse_status, token]);

  useEffect(() => {
    if (!token || !workflow?.tailored_resume.session_id || !isWorkflowProcessing) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextWorkflow = await fetchTailoredResumeWorkflowDetail(
          token,
          workflow.tailored_resume.session_id
        );
        setWorkflow(nextWorkflow);
        setWorkflowList(current => upsertWorkflowRecord(current, nextWorkflow));
        if (isTerminalWorkflowStatus(nextWorkflow.tailored_resume.display_status)) {
          setIsGenerating(false);
          setGenerateStartTime(null);
        }
      } catch {
        // keep current state visible until next poll
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [isWorkflowProcessing, token, workflow?.tailored_resume.session_id]);

  useEffect(() => {
    if (!token || !workflow?.tailored_resume.session_id || !isWorkflowProcessing) {
      return;
    }

    const sendExitEvent = () => {
      void recordTailoredResumeEvent(token, workflow.tailored_resume.session_id, {
        event_type: 'workflow_page_exit',
        payload: {
          status: workflow.tailored_resume.task_state.status,
          phase: workflow.tailored_resume.task_state.phase,
        },
      }).catch(() => undefined);
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        sendExitEvent();
      }
    };

    window.addEventListener('beforeunload', sendExitEvent);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      window.removeEventListener('beforeunload', sendExitEvent);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [
    isWorkflowProcessing,
    token,
    workflow?.tailored_resume?.session_id,
    workflow?.tailored_resume?.task_state?.phase,
    workflow?.tailored_resume?.task_state?.status,
  ]);

  const canSaveResume = Boolean(token && resume?.id && normalizeMarkdown(resumeMarkdown));
  const canRetryResume = Boolean(
    token &&
    resume?.id &&
    !isUploading &&
    !isConverting &&
    !isRetryingResumeParse &&
    !['pending', 'processing'].includes(resume?.parse_status ?? '')
  );
  const canSaveJob = Boolean(token && jobDraft.title.trim() && jobDraft.jd_text.trim());
  const canGenerate = Boolean(
    token &&
    resume?.id &&
    resume.parse_status === 'success' &&
    savedJob?.id &&
    savedJob.parse_status === 'success'
  );

  if (!token) {
    return null;
  }

  async function handleUploadResume(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!token || !file) {
      return;
    }

    setIsUploading(true);
    setPageError('');

    try {
      const uploaded = await uploadPrimaryResume(token, file);
      setResume(uploaded);
      setIsConverting(true);

      const converted = await convertResumePdfToMarkdown(token, file);
      setLatestPdfConversion(converted);
      const nextMarkdown = normalizeMarkdown(converted.markdown);
      setResumeMarkdown(nextMarkdown);

      if (converted.fallback_used && !isLikelyAutoSaveSafe(nextMarkdown)) {
        setWorkflowList([]);
        setWorkflow(null);
        return;
      }

      setIsSavingResume(true);

      const autoSaved = await updateResumeStructuredData(token, uploaded.id, nextMarkdown);
      setResume(autoSaved);
      setResumeMarkdown(getCanonicalResumeMarkdown(autoSaved) || nextMarkdown);
      setWorkflowList([]);
      setWorkflow(null);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsUploading(false);
      setIsConverting(false);
      setIsSavingResume(false);
    }
  }

  async function handleSaveResume() {
    if (!token || !resume?.id || !normalizeMarkdown(resumeMarkdown)) {
      return;
    }

    setIsSavingResume(true);
    setPageError('');

    try {
      const saved = await updateResumeStructuredData(
        token,
        resume.id,
        normalizeMarkdown(resumeMarkdown)
      );
      const nextMarkdown = getCanonicalResumeMarkdown(saved) || normalizeMarkdown(resumeMarkdown);
      setResume(saved);
      setResumeMarkdown(nextMarkdown);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSavingResume(false);
    }
  }

  async function handleRetryResume() {
    if (!token || !resume?.id) {
      return;
    }

    setIsRetryingResumeParse(true);
    setPageError('');

    try {
      const nextResume = await retryResumeParse(token, resume.id);
      setResume(nextResume);
      setLatestPdfConversion(null);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsRetryingResumeParse(false);
    }
  }

  async function handleSaveJob() {
    if (!token || !canSaveJob) {
      return;
    }

    setIsSavingJob(true);
    setPageError('');

    try {
      const nextJob = savedJob
        ? await updateJob(token, savedJob.id, jobDraft)
        : await createJob(token, jobDraft);
      setSavedJob(nextJob);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSavingJob(false);
    }
  }

  async function handleGenerateTailoredResume() {
    if (!token || !resume?.id || !savedJob?.id) {
      setPageError('请先完成简历保存和岗位 JD 保存。');
      return;
    }

    setIsGenerating(true);
    setGenerateStartTime(Date.now());
    setPageError('');

    try {
      const generated = await optimizeTailoredResume(token, {
        resume_id: resume.id,
        job_id: savedJob.id,
        force_refresh: true,
      });
      setWorkflow(generated);
      setWorkflowList(current => upsertWorkflowRecord(current, generated));
      if (generated.tailored_resume.task_state.started_at) {
        setGenerateStartTime(Date.parse(generated.tailored_resume.task_state.started_at));
      }
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleRetryWorkflow() {
    if (!token || !workflow) {
      return;
    }

    setIsRetryingWorkflow(true);
    setPageError('');

    try {
      const nextWorkflow = await retryTailoredResumeGeneration(
        token,
        workflow.tailored_resume.session_id
      );
      setWorkflow(nextWorkflow);
      setWorkflowList(current => upsertWorkflowRecord(current, nextWorkflow));
      setGenerateStartTime(
        nextWorkflow.tailored_resume.task_state.started_at
          ? Date.parse(nextWorkflow.tailored_resume.task_state.started_at)
          : Date.now()
      );
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsRetryingWorkflow(false);
    }
  }

  async function handleDownload(targetWorkflow: TailoredResumeWorkflowRecord) {
    if (!token) {
      return;
    }

    setIsDownloading(true);
    setPageError('');

    try {
      const result = await downloadTailoredResumeMarkdown(
        token,
        targetWorkflow.tailored_resume.session_id
      );
      const objectUrl = window.URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download =
        result.fileName ||
        targetWorkflow.tailored_resume.downloadable_file_name ||
        'optimized_resume.md';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <PageShell className="gap-8 py-4 md:py-6">
      <PageHeader
        eyebrow="Tailored Resume"
        title="专属简历"
        description="上传主简历，保存岗位，生成结果。"
        meta={
          <>
            <MetaChip>{resume ? 'Resume Ready' : 'Resume Missing'}</MetaChip>
            <MetaChip>{savedJob ? 'JD Ready' : 'JD Missing'}</MetaChip>
            <MetaChip>{workflow ? 'Result Ready' : 'Result Pending'}</MetaChip>
          </>
        }
      >
        <div className="bw-workbench-hero">
          <div className="bw-flow-strip">
            {[
              { label: 'Step 1', value: '上传主简历' },
              { label: 'Step 2', value: '保存岗位 JD' },
              { label: 'Step 3', value: '生成定制简历' },
              { label: 'Step 4', value: '进入模拟面试' },
            ].map(step => (
              <div key={step.label} className="bw-flow-step">
                <strong>{step.label}</strong>
                <span>{step.value}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <input
              ref={uploadInputRef}
              className="hidden"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleUploadResume}
            />
            <Button
              disabled={isUploading || isConverting}
              size="sm"
              type="button"
              onClick={() => uploadInputRef.current?.click()}
            >
              <FileUp className="size-4" />
              {isUploading || isConverting ? '上传中' : '上传 PDF'}
            </Button>
            <Button
              disabled={!canSaveResume || isSavingResume}
              size="sm"
              type="button"
              variant="outline"
              onClick={() => void handleSaveResume()}
            >
              {isSavingResume ? '保存简历中' : '保存简历'}
            </Button>
            <Button
              disabled={!canRetryResume}
              size="sm"
              type="button"
              variant="outline"
              onClick={() => void handleRetryResume()}
            >
              {isRetryingResumeParse ? '重新解析中' : '重试解析'}
            </Button>
            <Button
              disabled={!canSaveJob || isSavingJob}
              size="sm"
              type="button"
              variant="outline"
              onClick={() => void handleSaveJob()}
            >
              {isSavingJob ? '保存 JD 中' : '保存 JD'}
            </Button>
            <Button
              disabled={!canGenerate || isGenerating || isWorkflowProcessing}
              size="sm"
              type="button"
              onClick={() => void handleGenerateTailoredResume()}
            >
              <Sparkles className="size-4" />
              {(isGenerating || isWorkflowProcessing) && generateStartTime !== null ? (
                <>
                  生成中
                  <Timer startTime={generateStartTime} isActive={true} />
                </>
              ) : (
                '生成简历'
              )}
            </Button>
          </div>
        </div>
      </PageHeader>

      {pageError ? (
        <Alert className="border border-[#e5e5e5] bg-[#fafafa] text-[#111111]">
          <AlertTitle>错误</AlertTitle>
          <AlertDescription>{pageError}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="space-y-6">
          <PaperSection
            eyebrow="Resume"
            title="主简历"
            rightSlot={
              resume ? (
                <div className="bw-meta-row">
                  <MetaChip>
                    <ResumeStatusIndicator resume={resume} />
                  </MetaChip>
                  <MetaChip>{resume.file_name}</MetaChip>
                  <MetaChip>{formatDate(resume.updated_at)}</MetaChip>
                </div>
              ) : null
            }
          >
            {resume ? (
              <div className="space-y-4">
                {isDevelopment && (hasImmediateAiDebug || hasPersistedAiDebug) ? (
                  <div className="border border-[#e5e5e5] bg-[#fafafa] p-4 text-sm text-[#1C1C1C]/72">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#1C1C1C]/50">
                      AI Debug
                    </p>
                    {hasImmediateAiDebug && immediateAiDebug ? (
                      <div className="mt-3 border border-[#e5e5e5] bg-white p-3">
                        <p className="text-xs font-semibold text-[#1C1C1C]/50">
                          本次上传即时转换结果 (/tailored-resumes/pdf-to-md)
                        </p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <p>AI cleaned: {immediateAiDebug.aiUsed ? 'yes' : 'no'}</p>
                          <p>
                            provider/model:{' '}
                            {[immediateAiDebug.provider, immediateAiDebug.model]
                              .filter(Boolean)
                              .join('/') || 'n/a'}
                          </p>
                          <p>fallback used: {immediateAiDebug.fallbackUsed ? 'yes' : 'no'}</p>
                          <p>AI path: {immediateAiDebug.aiPath || 'n/a'}</p>
                          <p>degraded used: {immediateAiDebug.degradedUsed ? 'yes' : 'no'}</p>
                          <p>
                            AI latency:{' '}
                            {immediateAiDebug.latencyMs === null
                              ? 'n/a'
                              : `${immediateAiDebug.latencyMs} ms`}
                          </p>
                          <p>
                            AI chain latency:{' '}
                            {immediateAiDebug.chainLatencyMs === null
                              ? 'n/a'
                              : `${immediateAiDebug.chainLatencyMs} ms`}
                          </p>
                          <p>prompt version: {immediateAiDebug.promptVersion || 'n/a'}</p>
                          <p>error message: {immediateAiDebug.error || 'none'}</p>
                        </div>
                        {immediateAiDebug.attempts.length > 0 ? (
                          <div className="mt-3 space-y-1 border-t border-[#e5e5e5] pt-3 text-xs text-[#1C1C1C]/70">
                            <p className="font-semibold uppercase tracking-[0.16em] text-[#1C1C1C]/50">
                              Attempts
                            </p>
                            {immediateAiDebug.attempts.map(attempt => (
                              <p key={`${attempt.stage}-${attempt.provider}-${attempt.model}`}>
                                {formatAttemptLine(
                                  attempt.stage,
                                  attempt.provider,
                                  attempt.model,
                                  attempt.status,
                                  attempt.latency_ms,
                                  attempt.error
                                )}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                    {hasPersistedAiDebug && persistedAiDebug ? (
                      <div className="mt-3 border border-[#e5e5e5] bg-white p-3">
                        <p className="text-xs font-semibold text-[#1C1C1C]/50">
                          已持久化解析结果 (parse_artifacts_json)
                        </p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <p>AI cleaned: {persistedAiDebug.aiUsed ? 'yes' : 'no'}</p>
                          <p>
                            provider/model:{' '}
                            {[persistedAiDebug.provider, persistedAiDebug.model]
                              .filter(Boolean)
                              .join('/') || 'n/a'}
                          </p>
                          <p>fallback used: {persistedAiDebug.fallbackUsed ? 'yes' : 'no'}</p>
                          <p>AI path: {persistedAiDebug.aiPath || 'n/a'}</p>
                          <p>degraded used: {persistedAiDebug.degradedUsed ? 'yes' : 'no'}</p>
                          <p>
                            AI latency:{' '}
                            {persistedAiDebug.latencyMs === null
                              ? 'n/a'
                              : `${persistedAiDebug.latencyMs} ms`}
                          </p>
                          <p>
                            AI chain latency:{' '}
                            {persistedAiDebug.chainLatencyMs === null
                              ? 'n/a'
                              : `${persistedAiDebug.chainLatencyMs} ms`}
                          </p>
                          <p>prompt version: {persistedAiDebug.promptVersion || 'n/a'}</p>
                          <p>error message: {persistedAiDebug.error || 'none'}</p>
                        </div>
                        {persistedAiDebug.attempts.length > 0 ? (
                          <div className="mt-3 space-y-1 border-t border-[#e5e5e5] pt-3 text-xs text-[#1C1C1C]/70">
                            <p className="font-semibold uppercase tracking-[0.16em] text-[#1C1C1C]/50">
                              Attempts
                            </p>
                            {persistedAiDebug.attempts.map(attempt => (
                              <p key={`${attempt.stage}-${attempt.provider}-${attempt.model}`}>
                                {formatAttemptLine(
                                  attempt.stage,
                                  attempt.provider,
                                  attempt.model,
                                  attempt.status,
                                  attempt.latency_ms,
                                  attempt.error
                                )}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <PaperTextarea
                  value={resumeMarkdown}
                  onChange={event => setResumeMarkdown(event.target.value)}
                  placeholder="上传 PDF 后在这里编辑 Markdown。"
                  className="min-h-[320px]"
                />
                {normalizeMarkdown(resumeMarkdown) ? (
                  <div className="border border-[#e5e5e5] bg-[#fafafa] p-5">
                    <ResumeMarkdownPreview markdown={normalizeMarkdown(resumeMarkdown)} />
                  </div>
                ) : null}
              </div>
            ) : (
              <PageEmptyState title="还没有主简历" description="上传 PDF 后开始编辑。" />
            )}
          </PaperSection>

          <PaperSection
            eyebrow="Job"
            title="岗位 JD"
            rightSlot={
              savedJob ? (
                <MetaChip>
                  <JobStatusIndicator job={savedJob} />
                </MetaChip>
              ) : null
            }
          >
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="mb-2 text-sm font-medium text-[#1C1C1C]">岗位标题</p>
                  <PaperInput
                    value={jobDraft.title}
                    onChange={event =>
                      setJobDraft(current => ({
                        ...current,
                        title: event.target.value,
                      }))
                    }
                    placeholder="高级前端工程师"
                  />
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium text-[#1C1C1C]">公司名称</p>
                  <PaperInput
                    value={jobDraft.company}
                    onChange={event =>
                      setJobDraft(current => ({
                        ...current,
                        company: event.target.value,
                      }))
                    }
                    placeholder="CareerPilot"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="mb-2 text-sm font-medium text-[#1C1C1C]">岗位地点</p>
                  <PaperInput
                    value={jobDraft.job_city}
                    onChange={event =>
                      setJobDraft(current => ({
                        ...current,
                        job_city: event.target.value,
                      }))
                    }
                    placeholder="上海"
                  />
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium text-[#1C1C1C]">来源链接</p>
                  <PaperInput
                    value={jobDraft.source_url}
                    onChange={event =>
                      setJobDraft(current => ({
                        ...current,
                        source_url: event.target.value,
                      }))
                    }
                    placeholder="可选"
                  />
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium text-[#1C1C1C]">目标岗位 JD</p>
                <PaperTextarea
                  value={jobDraft.jd_text}
                  onChange={event =>
                    setJobDraft(current => ({
                      ...current,
                      jd_text: event.target.value,
                    }))
                  }
                  placeholder="粘贴岗位描述。"
                  className="min-h-[240px]"
                />
              </div>
            </div>
          </PaperSection>
        </div>

        <div className="space-y-6">
          <PaperSection
            eyebrow="Tailored"
            title="定制结果"
            rightSlot={
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={!canDownloadCurrentWorkflow || isDownloading}
                  size="sm"
                  type="button"
                  variant="outline"
                  onClick={() => workflow && void handleDownload(workflow)}
                >
                  <Download className="size-4" />
                  {isDownloading ? '下载中' : '下载结果'}
                </Button>
                {canRetryWorkflow ? (
                  <Button
                    disabled={isRetryingWorkflow}
                    size="sm"
                    type="button"
                    variant="outline"
                    onClick={() => void handleRetryWorkflow()}
                  >
                    {isRetryingWorkflow ? '重试中' : '重试生成'}
                  </Button>
                ) : null}
                {canStartInterview ? (
                  <Button asChild size="sm" type="button" variant="outline">
                    <Link
                      href={`/dashboard/interviews?jobId=${interviewEntryWorkflow?.target_job.id}&optimizationSessionId=${interviewEntryWorkflow?.tailored_resume.session_id}`}
                    >
                      进入面试
                      <ArrowUpRight className="size-4" />
                    </Link>
                  </Button>
                ) : null}
              </div>
            }
          >
            {!canGenerate ? (
              <div className="border border-[#e5e5e5] bg-[#fafafa] px-4 py-3 text-sm text-[#1C1C1C]/70">
                先保存主简历和岗位 JD。
              </div>
            ) : null}

            {workflow ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <MetaChip>{workflow.target_job.title}</MetaChip>
                  <MetaChip>{getFitBandLabel(workflow.tailored_resume.fit_band)}</MetaChip>
                  <MetaChip>Score {workflow.tailored_resume.overall_score}</MetaChip>
                  <MetaChip>{getWorkflowStatusLabel(workflowDisplayStatus)}</MetaChip>
                </div>
                <div className={cn('border p-4', getWorkflowStatusTone(workflowDisplayStatus))}>
                  <p className="text-sm font-medium">{getWorkflowPrimaryMessage(workflow)}</p>
                  <p className="mt-2 text-sm opacity-80">{getWorkflowSecondaryMessage(workflow)}</p>
                  {workflow.tailored_resume.display_status !== 'success' &&
                  latestSuccessfulWorkflow ? (
                    <p className="mt-2 text-sm opacity-80">
                      上一份结果仍可下载：
                      {latestSuccessfulWorkflow.tailored_resume.downloadable_file_name ||
                        'optimized_resume.md'}{' '}
                      · {formatDate(latestSuccessfulWorkflow.tailored_resume.updated_at)}
                    </p>
                  ) : null}
                </div>
                {latestSuccessfulWorkflow ? (
                  <Button
                    disabled={isDownloading}
                    size="sm"
                    type="button"
                    variant="ghost"
                    onClick={() => void handleDownload(latestSuccessfulWorkflow)}
                  >
                    <Download className="size-4" />
                    {isDownloading ? '下载中' : '下载上一份结果'}
                  </Button>
                ) : null}
                {workflow.tailored_resume?.segments?.length ? (
                  <div className="space-y-4">
                    {workflow.tailored_resume.segments
                      .slice()
                      .sort((a, b) => a.sequence - b.sequence)
                      .map(segment => (
                        <SegmentCard key={segment.key} segment={segment} />
                      ))}
                  </div>
                ) : (
                  <div className="border border-[#e5e5e5] bg-[#fafafa] px-4 py-3 text-sm text-[#1C1C1C]/70">
                    等待分段结果。
                  </div>
                )}
                {workflow.tailored_resume.document.markdown.trim() ? (
                  <PaperTextarea
                    value={workflow.tailored_resume.document.markdown}
                    readOnly
                    className="min-h-[320px]"
                  />
                ) : (
                  <div className="border border-[#e5e5e5] bg-[#fafafa] px-4 py-3 text-sm text-[#1C1C1C]/70">
                    {workflow.tailored_resume.result_is_empty
                      ? '本次没有可下载内容。'
                      : '等待可展示结果。'}
                  </div>
                )}
              </div>
            ) : (
              <PageEmptyState title="还没有定制结果" description="保存简历和 JD 后开始生成。" />
            )}
          </PaperSection>
        </div>
      </div>
    </PageShell>
  );
}
