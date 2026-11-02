"use client";
// Small shadcn-style primitives (hand-written; no external registry needed).
import { useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "teal";
export function Button({ variant = "primary", className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant }) {
  const v = {
    primary: "bg-terminal text-white hover:bg-slate-800",
    secondary: "bg-white border border-slate-300 text-slate-800 hover:bg-slate-50",
    ghost: "text-slate-700 hover:bg-slate-100",
    danger: "bg-red-700 text-white hover:bg-red-800",
    teal: "bg-teal-ml text-white hover:bg-teal-800",
  }[variant];
  return (
    <button
      {...p}
      className={cx("font-sans text-sm px-3 py-1.5 rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors", v, className)}
    />
  );
}

export function Card({ children, className, accent }: { children: ReactNode; className?: string; accent?: string }) {
  return (
    <section className={cx("bg-white border border-rule rounded-lg shadow-sm", className)} style={accent ? { borderTop: `4px solid ${accent}` } : undefined}>
      {children}
    </section>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "red" | "amber" | "teal" | "indigo" | "blue" }) {
  const t = {
    slate: "bg-slate-100 text-slate-700", green: "bg-green-100 text-green-800", red: "bg-red-100 text-red-800",
    amber: "bg-amber-100 text-amber-900", teal: "bg-teal-soft text-teal-ml", indigo: "bg-indigo-soft text-indigo-accent",
    blue: "bg-blue-100 text-blue-800",
  }[tone];
  return <span className={cx("inline-block font-sans text-[11px] font-medium px-2 py-0.5 rounded", t)}>{children}</span>;
}

export function Label({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <span className="block mb-1">
      <span className="label">{children}</span>
      {hint ? <span className="block font-sans text-[11px] text-slate-500 normal-case tracking-normal">{hint}</span> : null}
    </span>
  );
}

export function Input({ className, ...p }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...p}
      className={cx(/\bw-/.test(className ?? "") ? "" : "w-full", "border border-slate-300 rounded-md px-2.5 py-1.5 text-sm bg-white disabled:bg-slate-100 disabled:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-400", className)}
    />
  );
}

export function Select({ className, children, ...p }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...p} className={cx(/\bw-/.test(className ?? "") ? "" : "w-full", "border border-slate-300 rounded-md px-2 py-1.5 text-sm bg-white", className)}>
      {children}
    </select>
  );
}

export function Field({ label, hint, children, className }: { label: ReactNode; hint?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <label className={cx("block", className)}>
      <Label hint={hint}>{label}</Label>
      {children}
    </label>
  );
}

export function Section({ title, children, defaultOpen = true, right, tone }: { title: ReactNode; children: ReactNode; defaultOpen?: boolean; right?: ReactNode; tone?: string }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card className="mb-4" accent={tone}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-rule">
        <button type="button" onClick={() => setOpen(!open)} className="font-sans font-semibold text-sm flex items-center gap-2">
          <span className="text-slate-400 w-3">{open ? "▾" : "▸"}</span>
          {title}
        </button>
        {right}
      </div>
      {open ? <div className="p-4">{children}</div> : null}
    </Card>
  );
}

export function Alert({ tone = "amber", children }: { tone?: "amber" | "red" | "teal" | "slate" | "green"; children: ReactNode }) {
  const t = {
    amber: "bg-amber-50 border-amber-300 text-amber-950", red: "bg-red-50 border-red-300 text-red-900",
    teal: "bg-teal-soft border-teal-300 text-teal-900", slate: "bg-slate-50 border-slate-300 text-slate-800",
    green: "bg-green-50 border-green-300 text-green-900",
  }[tone];
  return <div className={cx("border rounded-md px-3 py-2 text-sm font-sans", t)}>{children}</div>;
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="px-4 py-3 border-b border-rule flex justify-between items-center">
          <h3 className="font-sans font-semibold">{title}</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-900" aria-label="Close">✕</button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 font-sans text-sm text-slate-600">
      <span className="h-3.5 w-3.5 rounded-full border-2 border-slate-300 border-t-slate-700 animate-spin" />
      {label}
    </span>
  );
}

export const pct = (x: number | null | undefined, d = 0) => (x == null || Number.isNaN(x) ? "—" : `${(x * 100).toFixed(d)}%`);
export { cx };
