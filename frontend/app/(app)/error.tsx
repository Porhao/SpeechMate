"use client";

// A page crashed: keep the nav, say so plainly, and offer a retry instead of a blank screen.

import { useEffect } from "react";
import { Button, LinkButton, PageHeader } from "@/components/ui/kit";

export default function AppError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => { console.error(error); }, [error]);

  return (
    <div className="px-4 sm:px-6 py-16 max-w-[640px] mx-auto">
      <PageHeader eyebrow="Something went wrong" title="This page couldn't load.">
        It may be a brief connection problem with the server. Your saved sessions are not affected.
      </PageHeader>
      <div className="flex gap-3">
        <Button onClick={retry}>Try again</Button>
        <LinkButton href="/home" variant="secondary">Back to home</LinkButton>
      </div>
    </div>
  );
}
