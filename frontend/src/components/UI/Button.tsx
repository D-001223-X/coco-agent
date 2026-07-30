import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  children: ReactNode;
}

export function Button({
  variant = "primary",
  children,
  className = "",
  ...rest
}: ButtonProps) {
  const base =
    "px-5 py-2.5 rounded-button font-semibold text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-coral hover:bg-coral-hover shadow-md hover:shadow-lg",
    secondary: "bg-warmorange hover:bg-warmorange-hover shadow-md hover:shadow-lg",
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}
