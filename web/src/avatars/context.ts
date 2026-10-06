import { createContext, useContext } from "react";

/**
 * Per-android state that faces and bodies read without prop-threading.
 * `still`: freeze every ambient loop (lists, thumbnails).
 * `lookAt`: -1..1, where the android's attention is (left/centre/right).
 */
export interface AvatarContextValue {
  still: boolean;
  lookAt: number;
}

export const AvatarContext = createContext<AvatarContextValue>({ still: false, lookAt: 0 });

export function useAvatar(): AvatarContextValue {
  return useContext(AvatarContext);
}
