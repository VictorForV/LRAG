/**
 * Input component
 */

import React from 'react';
import { cn } from '../../lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm',
          'transition-all duration-200 placeholder:text-slate-400',
          'focus-visible:outline-none focus-visible:border-slate-400 focus-visible:ring-2',
          'focus-visible:ring-slate-400/20 disabled:cursor-not-allowed disabled:opacity-50',
          'hover:bg-slate-100',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
