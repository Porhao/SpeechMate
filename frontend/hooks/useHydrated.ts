"use client";

import { useSyncExternalStore } from "react";

/** False during the server render and hydration, true after: for UI that depends on localStorage
 *  (the saved user), which the server can't see. */
export const useHydrated = () => useSyncExternalStore(() => () => {}, () => true, () => false);
