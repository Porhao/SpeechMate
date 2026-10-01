"use client";

// Old links (/assessment?live=<id>, e.g. in earlier notifications) now open the results page.

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function Redirect() {
  const router = useRouter();
  const live = useSearchParams().get("live");
  useEffect(() => { router.replace(live ? `/results/${live}` : "/progress"); }, [live, router]);
  return null;
}

export default function AssessmentRedirect() {
  return <Suspense><Redirect /></Suspense>;
}
