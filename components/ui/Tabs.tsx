interface TabsProps<T extends string> {
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
  /** Optional display label override, defaults to the option value itself. */
  labelFor?: (option: T) => string;
  className?: string;
}

/**
 * Shared pill-tab primitive (extracted from the chart page's varga
 * selector) so gold/ghost active-state styling stays consistent anywhere a
 * short, fixed set of options needs switching between.
 */
export default function Tabs<T extends string>({
  options,
  value,
  onChange,
  labelFor,
  className = "",
}: TabsProps<T>) {
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={
            value === opt
              ? "btn-gold px-3 py-1.5 text-xs transition"
              : "btn-ghost px-3 py-1.5 text-xs transition"
          }
        >
          {labelFor ? labelFor(opt) : opt}
        </button>
      ))}
    </div>
  );
}
