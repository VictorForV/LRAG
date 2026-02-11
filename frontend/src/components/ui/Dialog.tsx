/**
 * Dialog component
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { cn } from '../../lib/utils';
import { X } from 'lucide-react';

interface DialogContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DialogContext = createContext<DialogContextValue | undefined>(undefined);

export interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

export function Dialog({ open = false, onOpenChange, children }: DialogProps) {
  const [internalOpen, setInternalOpen] = useState(open);

  const isControlled = onOpenChange !== undefined;
  const isOpen = isControlled ? open : internalOpen;

  const setOpen = (value: boolean) => {
    if (isControlled) {
      onOpenChange(value);
    } else {
      setInternalOpen(value);
    }
  };

  return (
    <DialogContext.Provider value={{ open: isOpen, setOpen }}>
      {children}
    </DialogContext.Provider>
  );
}

export function DialogTrigger({ children, asChild = false }: { children: React.ReactNode; asChild?: boolean }) {
  const { setOpen } = useContext(DialogContext)!;

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      onClick: () => setOpen(true),
    } as React.HTMLAttributes<HTMLElement>);
  }

  return <div onClick={() => setOpen(true)}>{children}</div>;
}

export function DialogContent({ children, className }: { children: React.ReactNode; className?: string }) {
  const { open, setOpen } = useContext(DialogContext)!;

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-400/30 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
        onClick={() => setOpen(false)}
      />

      {/* Dialog */}
      <div
        className={cn(
          'relative z-50 bg-white rounded-xl shadow-lg w-full mx-4',
          'transition-all duration-300 animate-in fade-in zoom-in-95 slide-in-from-bottom-4',
          className
        )}
        style={{ maxWidth: '900px' }}
      >
        <button
          onClick={() => setOpen(false)}
          className="absolute right-4 top-4 rounded-md p-1 opacity-60 transition-all hover:bg-slate-100 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Закрыть</span>
        </button>
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col space-y-1.5 text-center sm:text-left px-6 pt-6', className)}>
      {children}
    </div>
  );
}

export function DialogTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={cn('text-lg font-semibold leading-none tracking-tight', className)}>
      {children}
    </h2>
  );
}

export function DialogDescription({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={cn('text-sm text-muted-foreground', className)}>
      {children}
    </p>
  );
}

export function DialogFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 px-6 pb-6', className)}>
      {children}
    </div>
  );
}
