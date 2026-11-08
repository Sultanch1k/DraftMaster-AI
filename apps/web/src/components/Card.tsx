import { cn } from '@/lib/format';

export function Card({
  children,
  className,
  title,
  icon,
  action,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className={cn('card card-pad animate-fade-up', className)}>
      {title && (
        <header className="mb-3 flex items-center justify-between gap-2">
          <h2 className="section-title">
            {icon}
            {title}
          </h2>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
