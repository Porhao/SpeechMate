"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { presentationService } from "@/services/presentation";

// Slide images need the Bearer token (decks are private), which an <img src> can't send,
// so each slide is fetched once with it and shown from an object URL.
// ponytail: URLs live for the page's lifetime (a deck is a few MB); revoke them if decks get huge.
const cache = new Map<string, Promise<string>>();

function slideUrl(deckId: string, n: number): Promise<string> {
  const key = `${deckId}/${n}`;
  let url = cache.get(key);
  if (!url) {
    url = presentationService.slideImage(deckId, n).then((b) => URL.createObjectURL(b));
    url.catch(() => cache.delete(key));  // a failed fetch is tried again next time
    cache.set(key, url);
  }
  return url;
}

export default function SlideImage({ deckId, n, alt, className, style }: {
  deckId: string; n: number; alt: string; className?: string; style?: CSSProperties;
}) {
  const [loaded, setLoaded] = useState<{ key: string; src: string } | null>(null);
  const key = `${deckId}/${n}`;
  useEffect(() => {
    let live = true;
    slideUrl(deckId, n).then((src) => { if (live) setLoaded({ key: `${deckId}/${n}`, src }); }).catch(() => {});
    return () => { live = false; };
  }, [deckId, n]);
  const src = loaded?.key === key ? loaded.src : undefined;
  // eslint-disable-next-line @next/next/no-img-element
  return src ? <img src={src} alt={alt} className={className} style={style} />
    : <div role="img" aria-label={alt} className={className} style={{ background: "var(--surface-2)", ...style }} />;
}
