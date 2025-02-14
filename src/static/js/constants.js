import { hexToRgb } from "./utils.js";

// Categories
export const DEFAULT_CATEGORIES = [
  "Philosophy",
  "Ethics",
  "Business & Risk",
  "Thought Experiments",
  "Politics",
  "Biases & Fallacies",
  "AI & Future",
  "Fun & Casual",
];

// Category icons mapping
export const CATEGORY_ICONS = {
  Philosophy: "📚",
  Ethics: "⚖️",
  "Business & Risk": "💼",
  "Thought Experiments": "💡",
  Politics: "🏛️",
  "Biases & Fallacies": "🔍",
  "AI & Future": "🤖",
  "Fun & Casual": "🎉",
};

// Character limits for different fields
export const CHAR_LIMITS = {
  CLAIM: 200,
  ARGUMENT: 1000,
  COUNTERARGUMENT: 500,
  CHALLENGE: 1000,
};

// Color gradient configuration for scores
export const SCORE_COLORS = {
  LOW: "#ef4444", // red-500 (1-3)
  MEDIUM_LOW: "#f59e0b", // amber-500 (4-5)
  MEDIUM: "#eab308", // yellow-500 (6)
  MEDIUM_HIGH: "#84cc16", // lime-500 (7)
  HIGH: "#16a34a", // green-600 (8-9)
  VERY_HIGH: "#059669", // emerald-600 (10)
};

// Score thresholds for color transitions
export const SCORE_THRESHOLDS = {
  LOW: 0.3,
  MEDIUM_LOW: 0.5,
  MEDIUM: 0.7,
  MEDIUM_HIGH: 0.9,
};

// Five-color gradient: red -> orange -> yellow -> lime -> emerald
export const COLORS = [
  hexToRgb("#ef4444"), // red-500 (1-3)
  hexToRgb("#f59e0b"), // amber-500 (4-5)
  hexToRgb("#eab308"), // yellow-500 (6)
  hexToRgb("#84cc16"), // lime-500 (7)
  hexToRgb("#16a34a"), // green-600 (8-9)
  hexToRgb("#059669"), // emerald-600 (10)
];
