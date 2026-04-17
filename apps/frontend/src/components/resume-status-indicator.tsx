import type {
  PdfToMarkdownConversionResult,
  ResumeParseArtifacts,
  ResumeRecord,
} from '@/lib/api/modules/resume';
import { StatusIndicator } from './status-indicator';
import { ProcessingTimer } from './ui/processing-timer';

interface ResumeStatusIndicatorProps {
  resume: ResumeRecord;
  parseDebug?: PdfToMarkdownConversionResult | ResumeParseArtifacts | null;
  processingStartTime?: number | null;
  isProcessingOverride?: boolean;
}

type ResumeStatus = 'pending' | 'processing' | 'success' | 'failed';

function resolveResumeStatus(
  resume: ResumeRecord,
  parseDebug?: PdfToMarkdownConversionResult | ResumeParseArtifacts | null
) {
  if (parseDebug?.ai_path === 'rules' && (parseDebug.fallback_used || !parseDebug.ai_used)) {
    return { status: 'success' as const, label: 'Markdown 已就绪（规则解析）' };
  }
  if (resume.parse_status === 'failed') {
    return { status: 'failed' as const, label: '解析失败' };
  }
  if (resume.parse_status === 'success') {
    return { status: 'success' as const, label: 'Markdown 已就绪' };
  }
  if (resume.parse_status === 'processing') {
    return { status: 'processing' as const, label: '解析中' };
  }
  return { status: 'pending' as const, label: '待解析' };
}

export function ResumeStatusIndicator({
  resume,
  parseDebug,
  processingStartTime,
  isProcessingOverride,
}: ResumeStatusIndicatorProps) {
  const isProcessing = isProcessingOverride ?? resume.parse_status === 'processing';
  const { status, label } = resolveResumeStatus(resume, parseDebug);

  return (
    <StatusIndicator
      status={status as ResumeStatus}
      label={label}
      timer={
        isProcessing && processingStartTime !== null ? (
          <ProcessingTimer startTime={processingStartTime ?? null} isActive={isProcessing} />
        ) : null
      }
    />
  );
}
