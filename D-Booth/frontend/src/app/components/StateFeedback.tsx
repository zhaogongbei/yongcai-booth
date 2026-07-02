import { Loader2, Inbox, AlertTriangle, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

interface LoadingSpinnerProps { message?: string }
export function LoadingSpinner({ message = "加载中..." }: LoadingSpinnerProps) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={32} className="text-violet-400 animate-spin" />
        <span className="text-sm text-white/40">{message}</span>
      </div>
    </div>
  );
}

interface EmptyStateProps { icon?: ReactNode; title?: string; description?: string; action?: ReactNode }
export function EmptyState({ icon, title = "暂无数据", description, action }: EmptyStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-sm">
        <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-4">
          {icon || <Inbox size={28} className="text-white/20" />}
        </div>
        <h3 className="text-base font-semibold text-white/60 mb-1">{title}</h3>
        {description && <p className="text-sm text-white/30 mb-4">{description}</p>}
        {action}
      </div>
    </div>
  );
}

interface ErrorStateProps { message?: string; onRetry?: () => void }
export function ErrorState({ message = "加载失败，请重试", onRetry }: ErrorStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-sm">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle size={28} className="text-red-400" />
        </div>
        <h3 className="text-base font-semibold text-white/60 mb-1">出错了</h3>
        <p className="text-sm text-white/30 mb-4">{message}</p>
        {onRetry && (
          <button onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white/60 text-sm hover:bg-white/10 transition-colors">
            <RefreshCw size={14} />重试
          </button>
        )}
      </div>
    </div>
  );
}
