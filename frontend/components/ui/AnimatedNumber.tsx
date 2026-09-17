"use client";

import { useEffect, useRef } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

// Counts up from 0 on first mount, and eases to the new value on every
// change after that (a live metric ticking up mid-session feels very
// different from one that just snaps to the new number).
export function AnimatedNumber({
  value,
  duration = 1,
  decimals = 0,
  suffix = "",
  prefix = "",
}: {
  value: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
}) {
  const mv = useMotionValue(0);
  const display = useTransform(mv, (v) => `${prefix}${v.toFixed(decimals)}${suffix}`);
  const mounted = useRef(false);

  useEffect(() => {
    const controls = animate(mv, value, {
      duration: mounted.current ? 0.7 : duration,
      ease: "easeOut",
    });
    mounted.current = true;
    return controls.stop;
  }, [value, mv, duration]);

  return <motion.span>{display}</motion.span>;
}
