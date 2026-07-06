import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";

interface CardProps extends Omit<ComponentPropsWithoutRef<"div">, "title"> {
  /** Optional heading rendered in the card's display font + gold accent. */
  title?: ReactNode;
  subtitle?: ReactNode;
  /** Small icon rendered to the left of the title (e.g. a lucide-react icon). */
  icon?: ElementType;
  /** Extra controls rendered to the right of the title (buttons, tabs, etc). */
  actions?: ReactNode;
}

/**
 * Shared card primitive wrapping the `.card` Tailwind token (globals.css) so
 * padding, headings and the fade-in entrance are consistent across pages
 * instead of each page hand-rolling its own div/h2 pairing.
 */
export default function Card({
  title,
  subtitle,
  icon: Icon,
  actions,
  className = "",
  children,
  ...rest
}: CardProps) {
  return (
    <div className={`card animate-fade-up p-5 ${className}`} {...rest}>
      {(title || actions) && (
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && (
              <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-gold-300">
                {Icon && <Icon className="h-4 w-4 shrink-0" aria-hidden />}
                {title}
              </h2>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}
