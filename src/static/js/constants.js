import { hexToRgb } from "./utils.js";

export const SUPPORTED_LANGUAGES = ["en", "de"];
export const DEFAULT_LANGUAGE = "en";

// Categories
export const DEFAULT_CATEGORIES = [
  "Philosophy",
  "AI & Future",
  "Personal Growth & Relationships",
  "Politics",
  "Ethics",
  "Thought Experiments",
  "Business & Risk",
  "Biases & Fallacies",
  "Fun & Casual",
];

// Category icons mapping
export const CATEGORY_ICONS = {
  Philosophy: "📚",
  "AI & Future": "🤖",
  "Personal Growth & Relationships": "🌱",
  Politics: "🏛️",
  Ethics: "⚖️",
  "Thought Experiments": "💡",
  "Business & Risk": "💼",
  "Biases & Fallacies": "🔍",
  "Fun & Casual": "🎉",
};

// Character limits for different fields
export const CHAR_LIMITS = {
  CLAIM: 200,
  ARGUMENT: 2000,
  COUNTERARGUMENT: 800,
  CHALLENGE: 3000,
  VOICE: 3000,
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

// Add this with the other constants
export const ERROR_MESSAGES = {
  UNEXPECTED_ERROR:
    "An unexpected error occurred while processing your submission. Please try again and send feedback if the issue persists.",
  REQUIRED_FIELDS:
    "Please fill in both required fields (Claim and Argument) before submitting.",
};

// Relevance is deliberately absent. Measured across 162 evaluations its
// standard deviation was 3.80, nearly double every other dimension: off-topic
// scores 1, on-topic scores 8-10, with almost nothing in between. It is a
// binary gate, not a graded dimension, and showing it alongside the others made
// the overall score lurch. It is surfaced as its own notice instead -- see
// #relevanceNotice.
export const EVALUATION_CATEGORIES = [
  "Logical Structure",
  "Clarity",
  "Depth",
  "Objectivity",
  "Creativity",
];

// Mapping of evaluation category labels to translation keys
export const EVALUATION_TRANSLATION_MAPPING = {
  Relevance: "relevance",
  "Logical Structure": "logic",
  Clarity: "clarity",
  Depth: "depth",
  Objectivity: "objectivity",
  Creativity: "creativity",
};

// Voice recording settings
export const VOICE_LIMITS = {
  MAX_RECORDING_TIME: 120000, // 60000=1 minute
};

// Timing constants
export const TIMING = {
  EVALUATION_DELAY: 2000, // 2 seconds minimum delay before showing evaluation results
};
