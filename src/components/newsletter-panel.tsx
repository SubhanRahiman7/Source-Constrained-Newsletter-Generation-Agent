"use client";

import { Loader2, Newspaper } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type RetrievedBlock = {
  chunk_id: string;
  score: number;
  text: string;
  citation: string;
  source_id: string;
};

type NewsletterSection = {
  title: string;
  body: string;
  confidence: number;
  cited_chunks: string[];
};

type DivergingView = {
  claim_a: string;
  claim_b: string;
  notes?: string | null;
};

type NewsletterPayload = {
  title: string;
  summary: string;
  sections: NewsletterSection[];
  diverging_views: DivergingView[];
};

type GenerateResponse = {
  status: "ok" | "not_found_in_sources";
  topic: string;
  retrieval_date: string;
  newsletter: NewsletterPayload | null;
  context_blocks: RetrievedBlock[];
  source_coverage_percent: number;
  most_cited_source: string | null;
};

type SourceInfo = {
  id: string;
  source_name: string;
  publication_date: string;
  description?: string | null;
  url?: string | null;
};

function compactCitation(raw: string) {
  // Convert "(Source: Name, YYYY-MM-DD | Retrieved: ... | Location: Page 12)"
  // to "(Name, YYYY, p.12)" for UI readability.
  const m = raw.match(
    /^\(Source:\s*(.+?),\s*(\d{4})(?:-\d{2}-\d{2})?\s*\|\s*Retrieved:.*\|\s*Location:\s*(.+)\)$/,
  );
  if (!m) return raw;
  const source = m[1].trim();
  const year = m[2];
  const location = m[3].trim().replace(/^Page\s+/i, "p.");
  return `(${source}, ${year}, ${location})`;
}

function shortSource(label: string) {
  if (label.includes("NITI")) return "NITI Aayog (2021)";
  if (label.includes("IndiaAI")) return "IndiaAI / MeitY (2024)";
  if (label.includes("Cyber Laws")) return "MeitY Advisory (2024)";
  return label;
}

function sourceYear(publicationDate: string) {
  return publicationDate.slice(0, 4) || publicationDate;
}

export function NewsletterPanel() {
  const apiBase = useMemo(
    () =>
      process.env.NEXT_PUBLIC_NEWSLETTER_API_URL ?? "http://127.0.0.1:8001",
    [],
  );

  const [topic, setTopic] = useState(
    "AI regulation in India: transparency, risk assessments, and enforcement",
  );
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [sources, setSources] = useState<SourceInfo[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function loadSources() {
      try {
        const res = await fetch(`${apiBase.replace(/\/$/, "")}/sources`);
        if (!res.ok) return;
        const data = (await res.json()) as SourceInfo[];
        if (!cancelled) setSources(data);
      } catch {
        // Keep generation usable even if source metadata fetch fails.
      }
    }
    void loadSources();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${apiBase.replace(/\/$/, "")}/generate-newsletter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          excluded_sources: Array.from(excluded),
        }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = (await res.json()) as GenerateResponse;
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleSource(id: string) {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <section className="rounded-2xl border border-zinc-800/80 bg-zinc-900/35 p-6 shadow-sm shadow-black/20">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-xl border border-teal-500/25 bg-teal-500/10 p-2 text-teal-200">
            <Newspaper className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-white">
              Source-Constrained Newsletter
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-zinc-500">
              Uses only your ingested corpus in{" "}
              <span className="font-mono text-zinc-400">backend/data</span>. Toggle
              sources to test removal impact and traceability.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void run()}
          disabled={busy || topic.trim().length < 3}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-500 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-teal-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : null}
          Generate Newsletter
        </button>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <label className="lg:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Enter Topic
          </span>
          <textarea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            rows={4}
            className="mt-2 w-full resize-y rounded-xl border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-sm text-zinc-100 outline-none ring-teal-500/0 transition focus:border-teal-500/40 focus:ring-4 focus:ring-teal-500/15"
          />
        </label>
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Active Sources
          </span>
          <div className="mt-2 space-y-2 rounded-xl border border-zinc-800 bg-zinc-950/40 p-3">
            {sources.map((s) => (
              <label
                key={s.id}
                className="flex cursor-pointer items-start gap-2 text-sm text-zinc-300"
              >
                <input
                  type="checkbox"
                  checked={excluded.has(s.id)}
                  onChange={() => toggleSource(s.id)}
                  className="mt-1"
                />
                <span>
                  <span className="font-medium text-zinc-200">
                    {shortSource(s.source_name)} ({sourceYear(s.publication_date)})
                  </span>
                  {s.description ? (
                    <span className="mt-0.5 block text-[11px] leading-relaxed text-zinc-400">
                      {s.description}
                    </span>
                  ) : null}
                  <span className="mt-0.5 block font-mono text-[11px] text-zinc-500">
                    {s.id}
                  </span>
                  {s.url ? (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-0.5 block text-[11px] text-teal-300/90 hover:underline"
                    >
                      View source PDF
                    </a>
                  ) : null}
                </span>
              </label>
            ))}
            <p className="pt-1 text-[11px] text-zinc-500">
              Toggle to test source removal.
            </p>
          </div>
        </div>
      </div>

      {error ? (
        <p className="mt-4 rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="mt-6 space-y-5">
          <div className="flex flex-wrap gap-2 text-xs text-zinc-400">
            <span className="rounded-lg border border-zinc-800 bg-zinc-950/40 px-2 py-1 font-mono">
              Source coverage: {result.source_coverage_percent}%
            </span>
            <span className="rounded-lg border border-zinc-800 bg-zinc-950/40 px-2 py-1 font-mono">
              Retrieval date: {result.retrieval_date}
            </span>
            {result.most_cited_source ? (
              <span className="rounded-lg border border-zinc-800 bg-zinc-950/40 px-2 py-1 font-mono">
                Most cited: {result.most_cited_source}
              </span>
            ) : null}
          </div>
          {excluded.size > 0 ? (
            <div className="rounded-xl border border-teal-500/25 bg-teal-500/10 px-4 py-3 text-sm text-teal-100">
              <p className="font-semibold">Source Impact</p>
              <p className="mt-1 text-teal-100/90">
                Removing {excluded.size} source(s) changes the output coverage to{" "}
                {result.source_coverage_percent}% and may remove arguments tied to
                those sources.
              </p>
            </div>
          ) : null}

          {result.status === "not_found_in_sources" || !result.newsletter ? (
            <p className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-3 text-sm text-amber-100">
              Not found in sources (retrieval threshold not met). Try a broader
              topic, ingest more data, or lower the backend similarity threshold.
            </p>
          ) : (
            <article className="space-y-5">
              <header>
                <h3 className="text-xl font-semibold text-white">
                  {result.newsletter.title}
                </h3>
              </header>
              <section>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Summary
                </h4>
                <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-zinc-200">
                  {result.newsletter.summary
                    .split("\n")
                    .filter((line) => line.trim().length > 0)
                    .slice(0, 4)
                    .map((line, idx) => (
                      <p key={idx} className="mb-2">
                        {line.replaceAll("(Source:", "(")}
                      </p>
                    ))}
                </div>
              </section>
              <section>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Key Themes
                </h4>
                <div className="mt-2 space-y-2 text-sm leading-relaxed text-zinc-200">
                  {result.newsletter.sections.slice(0, 2).map((s) => (
                    <p key={`theme-${s.title}`}>{s.body.split("\n")[0]}</p>
                  ))}
                </div>
              </section>
              <section>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Regulatory Gaps
                </h4>
                <div className="mt-2 text-sm leading-relaxed text-zinc-200">
                  {result.newsletter.sections[2]?.body ??
                    "No explicit regulatory gap detail available in the currently retrieved context."}
                </div>
              </section>
              {result.newsletter.sections.map((s) => (
                <section key={s.title}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h4 className="text-sm font-semibold text-white">
                      Source-wise Contributions
                    </h4>
                    <span className="font-mono text-[11px] text-zinc-500">
                      confidence: {s.confidence.toFixed(2)}
                    </span>
                  </div>
                  <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-zinc-200">
                    {s.body
                      .split("\n")
                      .filter((line) => line.trim().length > 0)
                      .slice(0, 3)
                      .map((line, idx) => (
                        <p key={idx} className="mb-1">
                          {compactCitation(line)}
                        </p>
                      ))}
                  </div>
                </section>
              ))}
              {result.newsletter.diverging_views.length ? (
                <section>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    Diverging views
                  </h4>
                  <div className="mt-3 space-y-3">
                    {result.newsletter.diverging_views.map((d, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-zinc-800 bg-zinc-950/35 p-4"
                      >
                        <p className="text-sm text-zinc-200">
                          {compactCitation(d.claim_a)}
                        </p>
                        <p className="mt-3 text-sm text-zinc-200">
                          {compactCitation(d.claim_b)}
                        </p>
                        {d.notes ? (
                          <p className="mt-3 text-xs text-zinc-500">{d.notes}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}
              <section>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Conclusion
                </h4>
                <p className="mt-2 text-sm leading-relaxed text-zinc-200">
                  The newsletter is generated strictly from active sources; changing
                  active sources changes both coverage and argument composition.
                </p>
              </section>
            </article>
          )}

          {result.context_blocks.length ? (
            <details className="rounded-xl border border-zinc-800 bg-zinc-950/35 p-4">
              <summary className="cursor-pointer text-sm font-medium text-zinc-200">
                Show Retrieval Debug ({result.context_blocks.length} chunks)
              </summary>
              <ol className="mt-3 space-y-3 text-sm text-zinc-300">
                {result.context_blocks.map((b, idx) => (
                  <li key={b.chunk_id} className="rounded-lg border border-zinc-800/80 p-3">
                    <div className="font-mono text-[11px] text-zinc-500">
                      #{idx + 1} · score {b.score.toFixed(3)} · {b.citation}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-zinc-200">{b.text}</p>
                  </li>
                ))}
              </ol>
            </details>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
