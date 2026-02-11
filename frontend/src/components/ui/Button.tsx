/**
 * Button component
 */

import React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

const variantStyles = {
  default: 'bg-slate-600 text-white border-none shadow-md hover:bg-slate-700 hover:shadow-lg',
  primary: 'bg-slate-600 text-white border-none shadow-md hover:bg-slate-700 hover:shadow-lg',
  secondary: 'bg-slate-100 text-slate-700 border-none hover:bg-slate-200',
  ghost: 'hover:bg-slate-100 hover:text-slate-900',
  destructive: 'bg-slate-500 text-white border-none hover:bg-slate-600',
};

const sizeStyles = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 py-2',
  lg: 'h-12 px-6 text-lg',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', children, style, ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-all',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'disabled:pointer-events-none disabled:opacity-50',
          'hover:translate-y-[-2px]',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        style={style}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
