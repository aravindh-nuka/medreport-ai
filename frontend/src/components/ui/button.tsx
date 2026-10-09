import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-pill font-sans font-medium transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap",
  {
    variants: {
      variant: {
        primary: "bg-brand-700 text-white hover:bg-brand-900 shadow-card hover:shadow-cardHover",
        secondary: "bg-white text-brand-700 border border-border hover:border-brand-300 dark:bg-surface-dark dark:text-paper dark:border-borderDark",
        ghost: "bg-transparent text-brand-700 hover:bg-brand-50 dark:text-paper dark:hover:bg-white/5",
        danger: "bg-attention-600 text-white hover:bg-attention-700",
      },
      size: {
        sm: "h-9 px-4 text-sm",
        md: "h-11 px-6 text-sm",
        lg: "h-13 px-8 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
);
Button.displayName = "Button";
