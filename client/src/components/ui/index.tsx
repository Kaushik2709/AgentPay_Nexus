"use client";
import { useEffect, useRef, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Loader2, X, type LucideIcon } from "lucide-react";

export function Button({ variant = "primary", loading = false, children, className = "", disabled, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost"; loading?: boolean }) {
  return <button type="button" {...props} disabled={disabled || loading} className={`ui-button ui-button-${variant} ${className}`} aria-busy={loading || undefined}>
    {loading && <Loader2 aria-hidden className="size-4 animate-spin" />}{children}
  </button>;
}
export function IconButton({ label, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return <Button variant="ghost" {...props} aria-label={label} className={`size-11 shrink-0 p-0 ${props.className || ""}`}>{children}</Button>;
}
export function Panel({ title, description, actions, children, className = "", ...props }: Omit<HTMLAttributes<HTMLElement>, "title"> & { title?: ReactNode; description?: string; actions?: ReactNode }) {
  return <section {...props} className={`nexus-card p-5 sm:p-6 ${className}`}>
    {(title || actions) && <div className="panel-heading"><div>{title && <h2 className="text-lg font-semibold tracking-tight">{title}</h2>}{description && <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>}</div>{actions}</div>}{children}
  </section>;
}
export function StatusBadge({ tone = "neutral", children }: { tone?: "neutral" | "success" | "warning" | "danger" | "info"; children: ReactNode }) {
  return <span className={`ui-status ui-status-${tone}`}>{children}</span>;
}
export function PageHeader({ title, description, eyebrow }: { title: string; description: string; eyebrow: string }) {
  return <div className="page-heading"><p className="mb-3 text-xs font-semibold uppercase tracking-[.16em] text-blue-700">{eyebrow}</p><h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-[32px]">{title}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{description}</p></div>;
}
export function Field({ label, htmlFor, hint, children }: { label: string; htmlFor: string; hint?: string; children: ReactNode }) {
  return <div className="space-y-2"><label htmlFor={htmlFor} className="block text-sm font-medium text-slate-800">{label}</label>{children}{hint && <p className="text-xs leading-5 text-slate-500">{hint}</p>}</div>;
}
export function Toggle({ checked, onChange, label, description, disabled }: { checked: boolean; onChange: () => void; label: string; description?: string; disabled?: boolean }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={onChange} className={`ui-toggle ${checked ? "ui-toggle-checked" : ""}`}>
    <span className="min-w-0"><span className="block text-sm font-medium">{label}</span>{description && <span className="mt-1 block text-xs leading-5 text-slate-500">{description}</span>}</span><span aria-hidden className={`toggle-track ${checked ? "bg-blue-600" : "bg-slate-300"}`}><span className={`toggle-thumb ${checked ? "translate-x-4" : ""}`} /></span>
  </button>;
}
export function Skeleton({ className = "" }: { className?: string }) { return <span aria-hidden className={`block rounded-md bg-slate-100 ${className}`} />; }
export function MetricCard({ label, value, caption, icon: Icon, loading }: { label: string; value: ReactNode | null; caption: string; icon: LucideIcon; loading?: boolean }) {
  return <div className="nexus-card p-4 sm:p-5" aria-busy={loading || undefined}><div className="flex items-center justify-between gap-2"><p className="text-xs font-medium text-slate-600">{label}</p><Icon aria-hidden className="size-4 text-slate-400" /></div>{loading ? <Skeleton className="my-3 h-8 w-24" /> : <p className="my-3 text-2xl font-semibold tracking-tight tabular-nums">{value ?? "—"}</p>}<p className="text-xs leading-5 text-slate-500">{caption}</p></div>;
}
export function StatePanel({ title, description, icon: Icon, action, compact = false }: { title: string; description: string; icon: LucideIcon; action?: ReactNode; compact?: boolean }) {
  return <div className={`flex flex-col items-center rounded-xl border border-dashed border-slate-200 bg-slate-50/60 text-center ${compact ? "p-6" : "px-6 py-12"}`}><div className="mb-4 flex size-12 items-center justify-center rounded-xl border border-slate-200 bg-white"><Icon aria-hidden className="size-5 text-blue-600" /></div><h3 className="text-base font-semibold">{title}</h3><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">{description}</p>{action && <div className="mt-5">{action}</div>}</div>;
}
export function Pagination({ page, pageSize, total, onPageChange, label = "records" }: { page: number; pageSize: number; total: number; onPageChange: (page: number) => void; label?: string }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(page, pages - 1);
  return <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4"><p role="status" className="text-xs text-slate-500">{total ? current * pageSize + 1 : 0}–{Math.min((current + 1) * pageSize, total)} of {total} {label}</p><div className="flex items-center gap-2"><IconButton label={`Previous ${label} page`} disabled={current === 0} onClick={() => onPageChange(current - 1)}><ChevronLeft className="size-4" /></IconButton><span className="text-xs text-slate-600">{current + 1} / {pages}</span><IconButton label={`Next ${label} page`} disabled={current >= pages - 1} onClick={() => onPageChange(current + 1)}><ChevronRight className="size-4" /></IconButton></div></div>;
}
export function Dialog({ title, id, onClose, children }: { title: string; id: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    const element = ref.current;
    element?.showModal();
    return () => { element?.close(); if (opener instanceof HTMLElement) requestAnimationFrame(() => { if (opener.isConnected) opener.focus({ preventScroll: true }); }); };
  }, []);
  return <dialog ref={ref} aria-labelledby={id} onCancel={event => { event.preventDefault(); onClose(); }} className="ui-dialog"><div className="flex items-center justify-between gap-4 border-b border-slate-100 p-5"><h2 id={id} className="text-lg font-semibold">{title}</h2><IconButton label={`Close ${title.toLowerCase()}`} onClick={onClose}><X className="size-5" /></IconButton></div><div className="p-5 sm:p-6">{children}</div></dialog>;
}
