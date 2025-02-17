let currentLanguage = localStorage.getItem("language") || "en";
let translations = {};

async function loadTranslations() {
  try {
    const response = await fetch(
      `/static/translations/${currentLanguage}.json`
    );
    translations = await response.json();
    applyTranslations();
    updateLanguageIndicator();
  } catch (error) {
    console.error("Error loading translations:", error);
  }
}

function applyTranslations() {
  // Update meta tags
  document.title = translations.meta.title;
  document.querySelector('meta[name="description"]').content =
    translations.meta.description;

  // Update text content for elements with data-i18n attribute
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const translation = getNestedTranslation(key);
    if (translation) {
      element.textContent = translation;
    }
  });
}

function getNestedTranslation(key) {
  return key.split(".").reduce((obj, k) => obj && obj[k], translations);
}

function updateLanguageIndicator() {
  document.getElementById("checkEn").style.opacity =
    currentLanguage === "en" ? "1" : "0";
  document.getElementById("checkDe").style.opacity =
    currentLanguage === "de" ? "1" : "0";
}

function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem("language", currentLanguage);
  loadTranslations();
  toggleDropdown();
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
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });

  loadTranslations();
});
