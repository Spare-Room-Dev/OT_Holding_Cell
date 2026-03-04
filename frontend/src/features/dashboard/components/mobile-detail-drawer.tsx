import type { ReactNode } from "react";
import "./dashboard-layout.css";

export interface MobileDetailDrawerProps {
  isOpen: boolean;
  title?: string;
  onClose?: () => void;
  children: ReactNode;
}

export function MobileDetailDrawer({
  isOpen,
  title = "Prisoner Detail",
  onClose,
  children,
}: MobileDetailDrawerProps) {
  return (
    <div className={`mobile-detail-drawer${isOpen ? " mobile-detail-drawer--open" : ""}`} aria-hidden={!isOpen}>
      <button
        type="button"
        className="mobile-detail-drawer__backdrop"
        onClick={onClose}
        aria-label="Close detail drawer"
      />
      <aside className="mobile-detail-drawer__panel" role="dialog" aria-modal="true" aria-label={title}>
        <header className="mobile-detail-drawer__header">
          <h2 className="mobile-detail-drawer__title">{title}</h2>
          <button type="button" className="mobile-detail-drawer__close" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="mobile-detail-drawer__body">{children}</div>
      </aside>
    </div>
  );
}
