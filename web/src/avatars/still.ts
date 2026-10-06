import { createContext, useContext } from "react";

/**
 * True inside an <Android still />: every ambient loop (blink, thrusters)
 * must hold a fixed frame so lists and thumbnails stay static.
 */
export const StillContext = createContext(false);

export function useStill(): boolean {
  return useContext(StillContext);
}
