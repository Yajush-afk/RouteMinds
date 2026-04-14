export const landingEase = [0.22, 1, 0.36, 1] as const;

export const landingViewport = {
  once: true,
  amount: 0.22,
} as const;

export function fadeUp(distance = 24, duration = 0.65) {
  return {
    hidden: { opacity: 0, y: distance },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration, ease: landingEase },
    },
  };
}

export function fadeIn(duration = 0.6, delay = 0) {
  return {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration, delay, ease: landingEase },
    },
  };
}

export function staggerContainer(delayChildren = 0.1, staggerChildren = 0.12) {
  return {
    hidden: {},
    visible: {
      transition: {
        delayChildren,
        staggerChildren,
      },
    },
  };
}
