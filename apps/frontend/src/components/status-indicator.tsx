import { Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type StatusType = 'pending' | 'processing' | 'success' | 'failed';

interface StatusIndicatorProps {
  status: StatusType;
  label: string;
  className?: string;
  timer?: ReactNode;
}

const statusConfig = {
  pending: {
    circle: 'bg-gray-400',
    text: 'text-gray-700',
    icon: null,
    animate: false,
  },
  processing: {
    circle: 'bg-blue-500',
    text: 'text-blue-700',
    icon: null,
    animate: true,
  },
  success: {
    circle: 'bg-emerald-500',
    text: 'text-emerald-700',
    icon: 'check',
    animate: false,
  },
  failed: {
    circle: 'bg-red-500',
    text: 'text-red-700',
    icon: 'x',
    animate: false,
  },
};

export function StatusIndicator({ status, label, className, timer }: StatusIndicatorProps) {
  const config = statusConfig[status];

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span className="relative flex h-3 w-3">
        {config.animate && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
        )}
        <span className={cn('relative inline-flex rounded-full h-3 w-3', config.circle)}>
          {config.icon === 'check' && (
            <Check className="h-2 w-2 text-white absolute top-0.5 left-0.5" />
          )}
          {config.icon === 'x' && <X className="h-2 w-2 text-white absolute top-0.5 left-0.5" />}
        </span>
      </span>
      <span className={cn('text-sm font-medium', config.text)}>{label}</span>
      {timer}
    </span>
  );
}
