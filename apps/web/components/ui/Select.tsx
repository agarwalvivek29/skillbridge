import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { label, error, helperText, options, placeholder, className, id, ...props },
    ref,
  ) => {
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
        <div className="relative">
          <select
            ref={ref}
            id={inputId}
            aria-describedby={errorId ?? helperId}
            aria-invalid={!!error}
            className={cn(
              "h-10 w-full appearance-none rounded-md border bg-white px-3 py-2 pr-10 text-base text-neutral-900 transition-colors focus:outline-none focus:ring-1",
              error
                ? "border-error-500 focus:border-error-500 focus:ring-error-500"
                : "border-neutral-300 focus:border-primary-500 focus:ring-primary-500",
              props.disabled &&
                "cursor-not-allowed bg-neutral-100 text-neutral-400",
              className,
            )}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
        </div>
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

Select.displayName = "Select";
