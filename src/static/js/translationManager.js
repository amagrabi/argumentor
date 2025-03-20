// Translation Manager - Handles centralized translation loading and caching
const TRANSLATION_VERSION = "1.0"; // Increment this when translations structure changes

class TranslationManager {
  constructor() {
    this.translations = null;
    this.currentLanguage = null;
  }

  async initialize() {
    this.currentLanguage = localStorage.getItem("language") || "en";
    await this.loadTranslations();
    this.attachLanguageChangeListener();
  }

  async loadTranslations() {
    try {
      // Check if we have cached translations
      const cached = this.getCachedTranslations();
      if (cached) {
        this.translations = cached.translations;
        window.translations = this.translations;
        return;
      }

      // If no cache or version mismatch, fetch from server
      const response = await fetch(
        `/static/translations/${this.currentLanguage}.json`
      );
      if (!response.ok) throw new Error("Failed to load translations");

      this.translations = await response.json();
      window.translations = this.translations;

      // Cache the new translations
      this.cacheTranslations();
    } catch (error) {
      console.error("Error loading translations:", error);
      // Fallback to empty translations object
      this.translations = {};
      window.translations = {};
    }
  }

  getCachedTranslations() {
    try {
      const cached = JSON.parse(
        localStorage.getItem(`translations_${this.currentLanguage}`)
      );
      if (cached && cached.version === TRANSLATION_VERSION) {
        return cached;
      }
      return null;
    } catch {
      return null;
    }
  }

  cacheTranslations() {
    try {
      localStorage.setItem(
        `translations_${this.currentLanguage}`,
        JSON.stringify({
          version: TRANSLATION_VERSION,
          translations: this.translations,
          timestamp: Date.now(),
        })
      );
    } catch (error) {
      console.error("Error caching translations:", error);
    }
  }

  attachLanguageChangeListener() {
    window.addEventListener("languageChanged", async (event) => {
      this.currentLanguage = event.detail.language;
      await this.loadTranslations();
      this.applyTranslations();
    });
  }

  applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.getAttribute("data-i18n");
      const translation = key
        .split(".")
        .reduce((obj, k) => obj && obj[k], this.translations);
      if (translation) {
        if (
          element.tagName === "INPUT" &&
          element.getAttribute("type") === "placeholder"
        ) {
          element.placeholder = translation;
        } else {
          element.innerHTML = translation;
        }
      }
    });
    document.documentElement.lang = this.currentLanguage;
  }

  getTranslation(key) {
    return (
      key.split(".").reduce((obj, k) => obj && obj[k], this.translations) || key
    );
  }
}

// Create and export singleton instance
export const translationManager = new TranslationManager();

// Initialize immediately
translationManager.initialize().catch(console.error);
