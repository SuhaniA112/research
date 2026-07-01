import { type InputHTMLAttributes } from "react";

interface InputFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  required?: boolean;
}

export function InputField({ label, required, className = "", ...props }: InputFieldProps) {
  return (
    <div className="w-full">
      {label && (
        <label className="mb-1.5 block text-sm font-medium text-gray-900">
          {label}
          {required && <span className="text-red-500"> *</span>}
        </label>
      )}
      <input
        className={`w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-brand-700 focus:outline-none focus:ring-1 focus:ring-brand-700 ${className}`}
        {...props}
      />
    </div>
  );
}
