import { NewsletterPanel } from "@/components/newsletter-panel";

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col bg-zinc-950 text-zinc-100">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_85%_55%_at_50%_-25%,rgba(20,184,166,0.14),transparent),radial-gradient(ellipse_50%_45%_at_100%_0%,rgba(16,185,129,0.07),transparent)]"
        aria-hidden
      />
      <header className="relative z-10 border-b border-zinc-800/60 px-6 py-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-teal-400/85">
              AI Product Demo
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white lg:text-3xl">
              Source-Constrained Newsletter Generation Agent
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-zinc-500">
              Generates fully cited insights strictly from verified sources.
            </p>
          </div>
        </div>
      </header>
      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-8">
        <NewsletterPanel />
        <div className="mt-6 rounded-xl border border-zinc-800/70 bg-zinc-900/30 px-4 py-3 text-xs text-zinc-500">
          Retrieval: FAISS · Generation: source-constrained only · Runtime:
          Next.js + FastAPI
        </div>
      </main>
    </div>
  );
}
