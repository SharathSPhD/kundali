import type { ButtonHTMLAttributes, ElementType } from "react";
import Link from "next/link";

type Variant = "gold" | "ghost" | "danger";

const VARIANT_CLASS: Record<Variant, string> = {
  gold: "btn-gold",
  ghost: "btn-ghost",
  danger: "btn-ghost text-red-400 hover:border-red-800 hover:text-red-300",
};

const SIZE_CLASS = {
  sm: "px-3 py-1.5 text-xs",
  md: "",
} as const;

interface CommonProps {
  variant?: Variant;
  size?: keyof typeof SIZE_CLASS;
  icon?: ElementType;
  className?: string;
  children?: React.ReactNode;
}

interface ButtonProps
  extends CommonProps,
    Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className" | "children"> {
  href?: undefined;
}

interface LinkButtonProps extends CommonProps {
  href: string;
}

/**
 * Shared button primitive over the `.btn-gold` / `.btn-ghost` Tailwind
 * tokens (globals.css). Renders a `<Link>` when `href` is given, otherwise a
 * native `<button>`, so call sites don't have to duplicate the variant
 * class-name lookup themselves.
 */
export default function Button(props: ButtonProps | LinkButtonProps) {
  const { variant = "ghost", size = "md", icon: Icon, className = "", children } = props;
  const classes = `${VARIANT_CLASS[variant]} ${SIZE_CLASS[size]} transition active:scale-95 ${className}`.trim();

  if ("href" in props && props.href) {
    return (
      <Link href={props.href} className={classes}>
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
        {children}
      </Link>
    );
  }

  const { href: _href, ...buttonProps } = props as ButtonProps;
  return (
    <button className={classes} {...buttonProps}>
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
      {children}
    </button>
  );
}
