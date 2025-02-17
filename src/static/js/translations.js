import { updateQuestionDisplay } from "./helpers.js";

let currentLanguage = localStorage.getItem("language") || "en";
export let translations = {};

async function loadTranslations() {
  try {
    console.log("Loading translations for language:", currentLanguage);
    const response = await fetch(
      `/static/translations/${currentLanguage}.json`
    );
    translations = await response.json();
    console.log("Translations loaded:", translations);
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
  } catch (error) {
    console.error("Error loading translations:", error);
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

async function changeLanguage(lang) {
  // Close the dropdown menu
  const dropdown = document.getElementById("languageDropdown");
  if (dropdown) {
    dropdown.classList.add("hidden");
  }

  // Update language selector aria-expanded state
  const languageSelector = document.getElementById("languageSelector");
  if (languageSelector) {
    languageSelector.setAttribute("aria-expanded", "false");
  }

  currentLanguage = lang;
  localStorage.setItem("language", lang);

  // Update server-side session language
  await fetch("/set_language", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ language: lang }),
  });

  // Force page reload to ensure all translations are applied
  window.location.reload();
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
  if (!container.contains(event.target)) {
    document.getElementById("languageDropdown").classList.add("hidden");
    document
      .getElementById("languageSelector")
      .setAttribute("aria-expanded", "false");
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

export { changeLanguage };

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
