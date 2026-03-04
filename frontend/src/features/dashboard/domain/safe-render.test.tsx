import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SafeRender } from "./safe-render";

describe("SafeRender", () => {
  it("escapes attacker-controlled text by default", () => {
    const markup = renderToStaticMarkup(<SafeRender value={'<script>alert("xss")</script>'} />);
    expect(markup).toContain("&lt;script&gt;");
  });

  it("sanitizes explicit html mode", () => {
    const markup = renderToStaticMarkup(
      <SafeRender
        value={'<img src="x" onerror="alert(1)" /><script>alert("xss")</script><b>safe</b>'}
        renderMode="html"
      />,
    );

    expect(markup).not.toContain("onerror");
    expect(markup).not.toContain("<script>");
    expect(markup).toContain("<b>safe</b>");
  });

  it("strips dangerous url attributes in html mode", () => {
    const markup = renderToStaticMarkup(
      <SafeRender value={'<a href="javascript:alert(1)">click</a>'} renderMode="html" />,
    );

    expect(markup).toContain("<a>click</a>");
    expect(markup).not.toContain("javascript:");
  });

  it("removes blocked container tags in html mode", () => {
    const markup = renderToStaticMarkup(
      <SafeRender value={"<style>body{display:none}</style><em>visible</em>"} renderMode="html" />,
    );

    expect(markup).not.toContain("<style>");
    expect(markup).toContain("<em>visible</em>");
  });
});
