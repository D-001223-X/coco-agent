import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className = "", ...rest }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label className="text-sm font-semibold text-gray-700">{label}</label>
      )}
      <input
        className={`w-full px-4 py-3 rounded-input border border-gray-200 bg-white text-gray-800 placeholder-gray-400 outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral transition-all ${className}`}
        {...rest}
      />
    </div>
  );
}
