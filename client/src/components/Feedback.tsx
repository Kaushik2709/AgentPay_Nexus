import { AlertCircle } from "lucide-react";
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
export function ErrorNotice({ message }: { message: string | null }) {
  if (!message) return null;
  return <div role="alert" className="mb-4 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"><AlertCircle className="mt-0.5 size-4" /><span>{message}</span></div>;
}
