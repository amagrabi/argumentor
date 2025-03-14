import { updateQuestionDisplay } from "./helpers.js";
import { SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE } from "./constants.js";
import { translationManager } from "./translationManager.js";

let currentLanguage = localStorage.getItem("language") || DEFAULT_LANGUAGE;
localStorage.setItem("language", currentLanguage);
export let translations = {};

async function loadTranslations() {
  try {
    // Validate language and default to English if invalid
    if (!SUPPORTED_LANGUAGES.includes(currentLanguage)) {
      currentLanguage = DEFAULT_LANGUAGE;
      localStorage.setItem("language", DEFAULT_LANGUAGE);
    }

    const response = await fetch(
      `/static/translations/${currentLanguage}.json`
    );
    if (!response.ok) {
      throw new Error(`Failed to load translations for ${currentLanguage}`);
    }

    translations = await response.json();
    applyTranslations();
    updateLanguageIndicator();
    updateEvaluationTranslations();

    // Make translations globally available
    window.translations = translations;

    // Update current question if it exists
    let currentQuestion = JSON.parse(sessionStorage.getItem("currentQuestion"));
    if (currentQuestion) {
      const translatedQuestion = getNestedTranslation(
        `questions.${currentQuestion.category}.${currentQuestion.id}`
      );
      if (translatedQuestion) {
        currentQuestion.description = translatedQuestion;
        updateQuestionDisplay(currentQuestion);
      }
    }

    // Mark translations as loaded
    document.documentElement.classList.add("translations-loaded");
  } catch (error) {
    console.error("Error loading translations:", error);
    // Fallback to English if translation loading fails
    if (currentLanguage !== DEFAULT_LANGUAGE) {
      localStorage.setItem("language", DEFAULT_LANGUAGE);
      window.location.reload();
    }
  }
}

function applyTranslations() {
  // Update meta tags
  document.title = translations.meta.title;
  const descriptionMeta = document.querySelector('meta[name="description"]');
  if (descriptionMeta) {
    descriptionMeta.content = translations.meta.description;
  }

  // Update text content for elements with data-i18n attribute
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const translation = getNestedTranslation(key);
    if (translation) {
      if (translation.includes("<a")) {
        element.innerHTML = translation;
      } else {
        element.textContent = translation;
      }
    }
  });

  // Add support for placeholder translations
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.getAttribute("data-i18n-placeholder");
    const translation = getNestedTranslation(key);
    if (translation) {
      element.placeholder = translation;
    }
  });
}

function getNestedTranslation(key) {
  return key.split(".").reduce((obj, k) => obj && obj[k], translations);
}

function updateLanguageIndicator() {
  console.log("Updating language indicator to:", currentLanguage);
  const checkEn = document.getElementById("checkEn");
  const checkDe = document.getElementById("checkDe");

  if (checkEn) checkEn.style.opacity = currentLanguage === "en" ? "1" : "0";
  if (checkDe) checkDe.style.opacity = currentLanguage === "de" ? "1" : "0";
}

export async function changeLanguage(lang) {
  // Store original hasVisitedBefore value to preserve first-time visitor status
  const hasVisitedBefore = localStorage.getItem("hasVisitedBefore");

  // Update localStorage
  localStorage.setItem("language", lang);

  // For first-time visitors, we'll delay setting hasVisitedBefore until they
  // interact with the page/video
  if (!hasVisitedBefore) {
    // Remove any existing hasVisitedBefore to ensure they get the first-time experience
    localStorage.removeItem("hasVisitedBefore");

    // Add a flag to indicate this is a language redirect for a first-time visitor
    sessionStorage.setItem("isLanguageRedirect", "true");
  }

  // Dispatch language change event
  window.dispatchEvent(
    new CustomEvent("languageChanged", {
      detail: { language: lang },
    })
  );

  // Get the current path without language prefix
  const path = window.location.pathname;
  const pathSegments = path.split("/").filter(Boolean);
  const isLanguagePath = ["en", "de"].includes(pathSegments[0]);
  const basePath = isLanguagePath
    ? "/" + pathSegments.slice(1).join("/")
    : path;

  // Construct the new URL with language prefix
  const newPath = lang === "en" ? basePath : `/${lang}${basePath}`;
  window.location.href = newPath;
}

function toggleDropdown() {
  const dropdown = document.getElementById("languageDropdown");
  const isHidden = dropdown.classList.contains("hidden");
  dropdown.classList.toggle("hidden");
  document
    .getElementById("languageSelector")
    .setAttribute("aria-expanded", !isHidden);
}

// Close dropdown when clicking outside
document.addEventListener("click", (event) => {
  const container = document.getElementById("languageContainer");
  if (container && !container.contains(event.target)) {
    const dropdown = document.getElementById("languageDropdown");
    const selector = document.getElementById("languageSelector");
    if (dropdown) dropdown.classList.add("hidden");
    if (selector) selector.setAttribute("aria-expanded", "false");
  }
});

// Update the event listener initialization
document.addEventListener("DOMContentLoaded", () => {
  const languageSelector = document.getElementById("languageSelector");
  const languageButtons = document.querySelectorAll("[data-lang]");

  if (languageSelector) {
    languageSelector.addEventListener("click", toggleDropdown);
  }

  languageButtons.forEach((button) => {
    button.addEventListener("click", () => changeLanguage(button.dataset.lang));
  });

  if (document.readyState !== "loading") {
    loadTranslations();
  } else {
    document.addEventListener("DOMContentLoaded", loadTranslations);
  }
});

// Define the function for switching translations
function setLanguage(lang) {
  // This is just one example.
  // You might load a JSON file dynamically
  // or update UI elements based on the provided translation data.
  if (lang === "de") {
    // Load or apply German translations
    console.log("Switching to German");
    // For example, you might change the document language
    document.documentElement.lang = "de";
  } else {
    // Default to English translations
    console.log("Switching to English");
    document.documentElement.lang = "en";
  }
  // Additional code to update the UI accordingly
}

// Make sure it's globally accessible
window.setLanguage = setLanguage;

function updateEvaluationTranslations() {
  // Update overall evaluation title
  const overallEvalDiv = document.getElementById("overallEvaluation");
  if (overallEvalDiv) {
    const totalScoreLabel = overallEvalDiv.querySelector(".text-l.font-bold");
    if (totalScoreLabel) {
      totalScoreLabel.firstChild.textContent = `${translations.evaluation.overall}: `;
    }
  }

  // Update individual score categories
  const scoresDiv = document.getElementById("scores");
  if (scoresDiv) {
    const scoreItems = scoresDiv.querySelectorAll(
      ".score-item span:first-child"
    );
    scoreItems.forEach((span) => {
      const key = span.getAttribute("data-i18n");
      if (key) {
        const translation = getNestedTranslation(key);
        if (translation) {
          span.textContent = translation;
        }
      }
    });
  }

  // Update challenge evaluation if it exists
  const challengeEvalDiv = document.getElementById(
    "challengeEvaluationResults"
  );
  if (challengeEvalDiv) {
    // Update overall rating text
    const challengeTotalLabel =
      challengeEvalDiv.querySelector(".text-l.font-bold");
    if (challengeTotalLabel) {
      challengeTotalLabel.firstChild.textContent = `${translations.evaluation.overall}: `;
    }

    // Update individual category scores in the challenge section
    const categoryDivs = challengeEvalDiv.querySelectorAll(
      "[data-translation-key]"
    );
    categoryDivs.forEach((div) => {
      const translationKey = div.getAttribute("data-translation-key");
      if (translationKey) {
        const translation = getNestedTranslation(translationKey);
        if (translation) {
          // Preserve the score value (everything after the colon)
          const score = div.textContent.split(":")[1];
          div.textContent = `${translation}:${score}`;
        }
      }
    });
  }
}

// Export translations for backward compatibility
export { translationManager };

// Get the current language
function getCurrentLanguage() {
  return currentLanguage;
}

// Handle Stripe checkout response for plan changes
async function handlePlanChangeResponse(response) {
  try {
    const data = await response.json();

    if (data.success && data.redirect) {
      // Redirect to the plan change scheduled page
      window.location.href = data.redirect;
    } else if (data.id) {
      // Regular checkout session, redirect to Stripe
      const stripe = Stripe(stripePublicKey);
      stripe.redirectToCheckout({
        sessionId: data.id,
      });
    } else {
      console.error("Unexpected response format:", data);
    }
  } catch (error) {
    console.error("Error handling plan change response:", error);
  }
}

// Export the functions
export {
  loadTranslations,
  getCurrentLanguage,
  setLanguage,
  applyTranslations,
  handlePlanChangeResponse,
};
