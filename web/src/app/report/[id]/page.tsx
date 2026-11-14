import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { PrintReport } from "@/components/PrintReport";
import { SAMPLES } from "@/samples";

// A print-friendly evidence report for one of the bundled sample reports (the web copy
// of fixtures/expected). The ids are known at build time, so every page is prerendered.

export function generateStaticParams() {
  return SAMPLES.map((sample) => ({ id: sample.id }));
}

export const metadata: Metadata = {
  title: "Evidence report · Carnot",
  description: "A battery listing's claims, the checks run on them, the arithmetic and the cited constants, laid out for print.",
};

async function Report({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const sample = SAMPLES.find((s) => s.id === id);
  if (!sample) notFound();
  return <PrintReport sample={sample} />;
}

export default function Page(props: PageProps<"/report/[id]">) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white" />}>
      <Report params={props.params} />
    </Suspense>
  );
}
