import { motion } from "motion/react";
import { useMemo } from "react";
import type { Avatar, Mood } from "../types";
import { BODIES } from "./bodies";
import { FACES } from "./faces";
import { accentFor, alpha } from "./palettes";
import { AvatarContext } from "./context";

interface Props {
  avatar: Avatar;
  mood?: Mood;
  seed?: number;
  size?: number;
  className?: string;
  /** Static mode freezes every ambient loop (for lists and thumbnails). */
  still?: boolean;
  /** -1..1: turn the head and eyes toward the left/right while idle. */
  lookAt?: number;
}

/**
 * A full android: body + face, with ambient bob, head tilt and a floor glow.
 * All micro-animations are driven by `mood`.
 */
export default function Android({ avatar, mood = "idle", seed = 0, size = 180, className, still, lookAt = 0 }: Props) {
  const accent = accentFor(avatar.palette);
  const Face = FACES[avatar.face] ?? FACES.duo;
  const Body = BODIES[avatar.body] ?? BODIES.capsule;
  const bobDuration = useMemo(() => 3.2 + (seed % 5) * 0.35, [seed]);
  const hovering = avatar.body === "hover";
  // Only idle androids follow the conversation; talking/thinking own the head.
  const look = still || mood !== "idle" ? 0 : Math.max(-1, Math.min(1, lookAt));
  const ctx = useMemo(() => ({ still: !!still, lookAt: look }), [still, look]);

  const bodyAnim = still
    ? { y: 0, rotate: 0 }
    : mood === "talking"
      ? { y: [0, -6, 0, -3, 0], rotate: [0, -1.2, 0.8, -0.6, 0] }
      : mood === "thinking"
        ? { y: [0, -2, 0], rotate: [0, 2.5, 2.5, 0] }
        : { y: hovering ? [0, -8, 0] : [0, -3, 0], rotate: 0 };

  const headAnim = still
    ? { rotate: 0, y: 0 }
    : mood === "talking"
      ? { rotate: [0, 3, -2, 2, 0], y: [0, -1, 0] }
      : mood === "thinking"
        ? { rotate: [0, -7, -7, 0], y: [0, 1, 0] }
        : { rotate: [0, 1.5, 0, -1.5, 0], y: 0 };

  return (
    <svg
      viewBox="0 0 200 250"
      width={size}
      height={size * 1.25}
      className={className}
      style={{ overflow: "visible" }}
      role="img"
      aria-label={`${avatar.face} ${avatar.body} android`}
    >
      {/* floor glow */}
      <motion.ellipse
        cx={100}
        cy={240}
        rx={58}
        ry={9}
        fill={accent}
        style={{ filter: "blur(10px)" }}
        animate={{ opacity: mood === "talking" ? [0.45, 0.8, 0.45] : mood === "thinking" ? [0.2, 0.45, 0.2] : 0.18 }}
        transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut" }}
      />
      <ellipse cx={100} cy={240} rx={46} ry={5} fill={alpha(accent, 0.35)} />

      <AvatarContext.Provider value={ctx}>
        <motion.g animate={bodyAnim} transition={{ duration: mood === "idle" ? bobDuration : 1.4, repeat: Infinity, ease: "easeInOut" }}>
          <Body accent={accent} mood={mood} />
          <motion.g
            style={{ transformBox: "fill-box", transformOrigin: "50% 95%" }}
            animate={headAnim}
            transition={{ duration: mood === "idle" ? bobDuration * 1.3 : 1.6, repeat: Infinity, ease: "easeInOut" }}
          >
            {/* head turn toward whoever has the floor */}
            <motion.g
              style={{ transformBox: "fill-box", transformOrigin: "50% 95%" }}
              initial={{ rotate: 0 }}
              animate={{ rotate: look * 7 }}
              transition={{ type: "spring", stiffness: 120, damping: 14 }}
            >
              <Face accent={accent} mood={mood} seed={seed} />
            </motion.g>
          </motion.g>
        </motion.g>
      </AvatarContext.Provider>
    </svg>
  );
}
