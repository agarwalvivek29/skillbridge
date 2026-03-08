import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    const errorId = error ? `${inputId}-error` : undefined;
    const helperId = helperText ? `${inputId}-helper` : undefined;

    return (
      <div className="flex flex-col">
        {label && (
          <label
            htmlFor={inputId}
            className="mb-1.5 text-sm font-medium text-neutral-700"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-describedby={errorId ?? helperId}
          aria-invalid={!!error}
          className={cn(
            "h-10 rounded-md border px-3 py-2 text-base text-neutral-900 placeholder:text-neutral-400 transition-colors focus:outline-none focus:ring-1",
            error
              ? "border-error-500 focus:border-error-500 focus:ring-error-500"
              : "border-neutral-300 focus:border-primary-500 focus:ring-primary-500",
            props.disabled &&
              "cursor-not-allowed bg-neutral-100 text-neutral-400",
            className,
          )}
          {...props}
        />
        {error && (
          <p id={errorId} className="mt-1.5 text-sm text-error-500">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="mt-1.5 text-sm text-neutral-500">
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
