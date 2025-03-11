import { rgbToHex } from "./utils.js";
import { CATEGORY_ICONS, CHAR_LIMITS, COLORS } from "./constants.js";
import { translations } from "./translations.js";

// Helper function for typewriter effect
export function typeWriter(element, text, speed) {
  if (element._typewriterTimer) {
    clearInterval(element._typewriterTimer);
  }
  element.textContent = "";
  let i = 0;
  element._typewriterTimer = setInterval(() => {
    element.textContent += text.charAt(i);
    i++;
    if (i >= text.length) {
      clearInterval(element._typewriterTimer);
      element._typewriterTimer = null;
    }
  }, speed);
}

// Helper function to update the question display
export function updateQuestionDisplay(question) {
  const questionElem = document.getElementById("questionDescription");
  if (questionElem && question) {
    // For custom questions, use the description directly
    if (question.isCustom) {
      questionElem.textContent = question.description;
    } else {
      // Try to get the translated question text if available
      const translatedQuestion =
        window.translations?.questions?.[question.category]?.[question.id];
      questionElem.textContent = translatedQuestion || question.description;
    }
  }

  const categoryBadge = document.getElementById("categoryBadge");
  if (categoryBadge) {
    // For custom questions, show "Custom" category
    if (question.isCustom) {
      const translatedCustom =
        window.translations?.categories?.Custom || "Custom";
      categoryBadge.textContent = `✏️ ${translatedCustom}`;
    } else {
      const translatedCategory =
        window.translations?.categories?.[question.category] ||
        question.category;
      const categoryText = CATEGORY_ICONS[question.category]
        ? `${CATEGORY_ICONS[question.category]} ${translatedCategory}`
        : translatedCategory;
      categoryBadge.textContent = categoryText;
    }
  }
}

// Function to determine color based on score using linear interpolation
export function scoreToColor(score) {
  const minScore = 1,
    maxScore = 10;
  const clampedScore = Math.min(maxScore, Math.max(minScore, score));
  const factor = (clampedScore - minScore) / (maxScore - minScore);

  if (factor < 0.3) {
    return interpolate(COLORS[0], COLORS[1], factor / 0.3);
  } else if (factor < 0.5) {
    return interpolate(COLORS[1], COLORS[2], (factor - 0.3) / 0.2);
  } else if (factor < 0.7) {
    return interpolate(COLORS[2], COLORS[3], (factor - 0.5) / 0.2);
  } else if (factor < 0.9) {
    return interpolate(COLORS[3], COLORS[4], (factor - 0.7) / 0.2);
  } else {
    return interpolate(COLORS[4], COLORS[5], (factor - 0.9) / 0.1);
  }

  function interpolate(start, end, ratio) {
    const result = {
      r: Math.round(start.r + (end.r - start.r) * ratio),
      g: Math.round(start.g + (end.g - start.g) * ratio),
      b: Math.round(start.b + (end.b - start.b) * ratio),
    };
    return rgbToHex(result.r, result.g, result.b);
  }
}

// Update character counters
export function setupCharCounter(inputId, countId, fieldName) {
  const input = document.getElementById(inputId);
  const count = document.getElementById(countId);
  if (input && count) {
    const maxLength = CHAR_LIMITS[fieldName.toUpperCase()];
    input.setAttribute("maxlength", maxLength);
    count.textContent = maxLength;

    input.addEventListener("input", () => {
      const remaining = maxLength - input.value.length;
      count.textContent = remaining;
      // Clear error message on any input
      document.getElementById("errorMessage").textContent = "";
      // Additional check to clear message when requirements are met
      if (
        input.value.length > 0 &&
        document.getElementById("errorMessage").textContent
      ) {
        document.getElementById("errorMessage").textContent = "";
      }
    });
  }
}
