import { cn } from '@/lib/utils'

// Printed on every page that shows Simulated Readings.
export function Stamp({ className }: { className?: string }) {
  return (
    <p
      role="note"
      className={cn(
        'w-fit -rotate-6 border-2 border-destructive px-2.5 py-1 text-[13px] font-semibold tracking-[.12em] text-destructive uppercase',
        className,
      )}
    >
      Simulated<span className="sr-only"> Readings</span>
    </p>
  )
}

// Small uppercase label used above figures and as table headers.
export function Label({ className, ...props }: React.ComponentProps<'p'>) {
  return <p className={cn('text-xs tracking-[.06em] text-muted-foreground uppercase', className)} {...props} />
}
