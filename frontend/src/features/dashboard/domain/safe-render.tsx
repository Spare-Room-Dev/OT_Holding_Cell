import type { JSX } from "react";

export type SafeRenderMode = "text" | "html";

export interface SafeRenderProps {
  value: string | null | undefined;
  renderMode?: SafeRenderMode;
  className?: string;
}

const BLOCKED_TAGS = new Set(["script", "style", "iframe", "object", "embed", "link", "meta", "base"]);
const URL_ATTRIBUTES = new Set(["href", "src", "xlink:href", "action", "formaction"]);

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stripDangerousAttributes(element: Element): void {
  for (const attribute of [...element.attributes]) {
    const name = attribute.name.toLowerCase();
    const value = attribute.value.trim().toLowerCase();

    if (name.startsWith("on")) {
      element.removeAttribute(attribute.name);
      continue;
    }

    if (URL_ATTRIBUTES.has(name) && (value.startsWith("javascript:") || value.startsWith("data:text/html"))) {
      element.removeAttribute(attribute.name);
    }
  }
}

function sanitizeHtmlWithDom(unsafeHtml: string): string {
  const template = document.createElement("template");
  template.innerHTML = unsafeHtml;

  const elements = [...template.content.querySelectorAll("*")];
  for (const element of elements) {
    if (BLOCKED_TAGS.has(element.tagName.toLowerCase())) {
      element.remove();
      continue;
    }
    stripDangerousAttributes(element);
  }

  return template.innerHTML;
}

export function sanitizeAttackerHtml(unsafeHtml: string): string {
  if (typeof document === "undefined") {
    return escapeHtml(unsafeHtml);
  }
  return sanitizeHtmlWithDom(unsafeHtml);
}

export function SafeRender({
  value,
  renderMode = "text",
  className,
}: SafeRenderProps): JSX.Element {
  const normalizedValue = value ?? "";

  if (renderMode === "html") {
    const sanitizedHtml = sanitizeAttackerHtml(normalizedValue);
    return <span className={className} dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />;
  }

  return <span className={className}>{normalizedValue}</span>;
}
