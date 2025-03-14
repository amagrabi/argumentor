// Evaluation module - Handles all evaluation rendering and interactions
import { scoreToColor } from "./helpers.js";
import { translations } from "./translations.js";
import {
  EVALUATION_CATEGORIES,
  EVALUATION_TRANSLATION_MAPPING,
} from "./constants.js";

// Global variable to store earned achievements and all achievements
let earned_achievements = [];
let all_achievements = [];

// Track active notifications
let activeNotifications = [];
const NOTIFICATION_HEIGHT = 84; // Reduced from 100 to make it more compact
const NOTIFICATION_GAP = 4; // Reduced from 8 to make it more compact

// Track which achievements have already been shown as notifications
let shownAchievementNotifications = new Set();

// Initialize achievements from server or session storage
export async function initializeAchievements(achievements) {
  all_achievements = achievements;

  // Reset shown achievement notifications
  resetShownAchievementNotifications();

  // Check if user is authenticated
  const isAuthenticated =
    document.querySelector('meta[name="user-authenticated"]')?.content ===
    "true";

  if (isAuthenticated) {
    try {
      // Fetch achievements from server for authenticated users
      const response = await fetch("/get_user_achievements");
      const data = await response.json();

      if (response.ok && data.earned_achievements) {
        earned_achievements = data.earned_achievements;
        // Update sessionStorage with server data
        sessionStorage.setItem(
          "earned_achievements",
          JSON.stringify(earned_achievements)
        );
        return earned_achievements;
      }
    } catch (error) {
      console.error("Error fetching user achievements:", error);
      // Fall back to sessionStorage
    }
  }

  // If server fetch failed or user is not authenticated, try sessionStorage
  const storedAchievements = sessionStorage.getItem("earned_achievements");
  if (storedAchievements) {
    earned_achievements = JSON.parse(storedAchievements);
  } else {
    // Last resort - fall back to DOM elements if no sessionStorage data
    earned_achievements = Array.from(
      document.querySelectorAll("[data-achievement-id]")
    )
      .filter((el) => !el.classList.contains("opacity-40"))
      .map((el) => el.getAttribute("data-achievement-id"));

    // Store in sessionStorage for future use
    if (earned_achievements.length > 0) {
      sessionStorage.setItem(
        "earned_achievements",
        JSON.stringify(earned_achievements)
      );
    }
  }
  return earned_achievements;
}

// Function to update achievements display in both main and challenge sections
export async function updateAchievementsDisplay(newAchievements = []) {
  const isAuthenticated =
    document.querySelector('meta[name="user-authenticated"]')?.content ===
    "true";

  // Add any new achievements to our earned list
  if (newAchievements.length > 0) {
    earned_achievements = [
      ...new Set([...earned_achievements, ...newAchievements.map((a) => a.id)]),
    ];

    // Store earned achievements in sessionStorage for persistence
    sessionStorage.setItem(
      "earned_achievements",
      JSON.stringify(earned_achievements)
    );

    // For authenticated users, get the server's list after a brief delay
    // to allow the server to process any new achievements
    if (isAuthenticated) {
      try {
        // Short delay to ensure server processes any new achievements first
        await new Promise((resolve) => setTimeout(resolve, 300));

        const response = await fetch("/get_user_achievements");
        const data = await response.json();

        if (response.ok && data.earned_achievements) {
          earned_achievements = data.earned_achievements;
          // Update sessionStorage with server data
          sessionStorage.setItem(
            "earned_achievements",
            JSON.stringify(earned_achievements)
          );
        }
      } catch (error) {
        console.error("Error fetching updated achievements:", error);
      }
    }

    // Show notifications for new achievements that haven't been shown yet
    newAchievements.forEach((achievement) => {
      if (!shownAchievementNotifications.has(achievement.id)) {
        showAchievementNotification(achievement);
        shownAchievementNotifications.add(achievement.id);
      }
    });
  }

  // Update all achievement containers on the page
  const containers = [
    document.querySelector("#evaluationResults"),
    document.querySelector("#challengeEvaluationResults"),
  ];

  containers.forEach((container) => {
    if (!container) return;

    // Update the count in the header
    const countSpan = container.querySelector(".achievements-count");
    if (countSpan) {
      countSpan.textContent = `(${earned_achievements.length}/${all_achievements.length})`;
    }

    // Update each achievement icon
    all_achievements.forEach((achievement) => {
      const isEarned = earned_achievements.includes(achievement.id);
      const icon = container.querySelector(
        `[data-achievement-id="${achievement.id}"]`
      );

      if (icon) {
        // Update container classes
        icon.classList.toggle("opacity-40", !isEarned);
        icon.classList.toggle("border-gray-200", !isEarned);
        icon.classList.toggle("border-gray-600", isEarned);

        // Update trophy image opacity
        const trophyImage = icon.querySelector("img");
        if (trophyImage) {
          trophyImage.classList.toggle("opacity-30", !isEarned);
        }
      }
    });
  });
}

// Create evaluation HTML for scores with animation
export function createEvaluationScores(data, isChallenge = false) {
  const prefix = isChallenge ? "challenge" : "";
  const scoresHtml = EVALUATION_CATEGORIES.map((category) => {
    const finalScore = data.evaluation.scores[category] || 0;
    const finalWidthPercent = finalScore * 10;
    const color = scoreToColor(finalScore);
    const feedbackText = data.evaluation.feedback[category] || "";

    // Get translation key from mapping
    const translationKey = EVALUATION_TRANSLATION_MAPPING[category];

    return `
      <div class="mb-2 score-item text-left">
        <div class="flex justify-between items-center text-left">
          <span data-i18n="evaluation.scores.${translationKey}" class="text-left">${
      translations.evaluation.scores[translationKey] || category
    }</span>
          <span class="font-medium score-value" style="color: ${color};">${finalScore}/10</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
          <div class="rounded-full h-2 score-bar"
               style="width: 0%; background-color: ${color}; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
        </div>
        <p class="text-sm text-gray-500 text-left">${feedbackText}</p>
      </div>
    `;
  }).join("");

  return scoresHtml;
}

// Create overall evaluation HTML
export function createOverallEvaluation(data, isChallenge = false) {
  const prefix = isChallenge ? "challenge" : "";
  const totalScore = data.evaluation.total_score;
  const totalScorePercent = totalScore * 10;
  const totalScoreColor = scoreToColor(totalScore);

  return `
    <p class="text-l font-bold mb-2 text-left">
      ${
        translations.evaluation.overall
      }: <span id="${prefix}TotalScoreValue" style="color: ${totalScoreColor};">${totalScore.toFixed(
    1
  )}/10</span>
    </p>
    <div class="w-full bg-gray-200 rounded-full h-2.5 mb-2">
      <div id="${prefix}TotalScoreBar" class="rounded-full total-progress-bar"
           style="width: 0%; background-color: ${totalScoreColor}; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
    </div>
    <p id="${prefix}OverallFeedback" class="text-md text-left">
      ${data.evaluation.overall_feedback}
    </p>
  `;
}

// Animate score bars
export function animateScoreBars(scoresContainer, delay = 100) {
  setTimeout(() => {
    const scoreBars = scoresContainer.querySelectorAll(".score-bar");
    scoreBars.forEach((bar, index) => {
      const delay = index * 100;
      setTimeout(() => {
        const scoreItem = bar.closest(".score-item");
        const scoreValue = scoreItem.querySelector(".score-value");
        const finalScore = parseFloat(scoreValue.textContent);
        const scorePercent = finalScore * 10;
        bar.style.width = `${scorePercent}%`;
      }, delay);
    });
  }, delay);
}

// Function to show evaluation section
export function showEvaluationSection(evalDiv, isChallenge = false) {
  if (!evalDiv) {
    console.error(
      isChallenge
        ? "Challenge evaluation div not found"
        : "Evaluation div not found"
    );
    return;
  }

  // Make sure the evaluation section is visible
  evalDiv.classList.remove("hidden");
  evalDiv.style.display = "block";
  evalDiv.classList.add("fade-in");

  // Ensure it has the same styling
  evalDiv.className = "mt-8 bg-white p-8 fade-in";

  // Scroll to the appropriate section
  requestAnimationFrame(() => {
    if (isChallenge) {
      scrollToChallengeEvaluation();
    } else {
      scrollToMainEvaluation();
    }
  });
}

// Show achievement notification
export function showAchievementNotification(achievement) {
  // Create notification element
  const notification = document.createElement("div");
  notification.className =
    "fixed bg-gray-800 text-white p-4 rounded-lg shadow-lg transform translate-y-full opacity-0 transition-all duration-500";
  notification.style.zIndex = "9999";

  // Add responsive positioning
  const isMobile = window.innerWidth < 640; // Check if screen is small (mobile)
  if (isMobile) {
    notification.style.left = "16px";
    notification.style.right = "16px";
    notification.style.maxWidth = "calc(100vw - 32px)"; // Account for left/right margins
  } else {
    notification.style.right = "16px";
    notification.style.maxWidth = "320px"; // Limit width on larger screens
  }

  // Calculate position based on active notifications
  const notificationIndex = activeNotifications.length;
  const bottomOffset =
    16 + (NOTIFICATION_HEIGHT + NOTIFICATION_GAP) * notificationIndex;
  notification.style.bottom = `${bottomOffset}px`;

  // Add achievement content
  notification.innerHTML = `
    <div class="flex items-center gap-3">
      <div class="achievement-icon ${
        isMobile ? "w-10 h-10" : "w-12 h-12"
      } flex items-center justify-center rounded-lg bg-gray-400">
        <img src="/static/img/trophy.webp" class="${
          isMobile ? "w-6 h-6" : "w-8 h-8"
        }" alt="Trophy" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-bold ${
          isMobile ? "text-sm" : ""
        } truncate" data-i18n="${achievement.name_key}"></h3>
        <p class="${
          isMobile ? "text-xs" : "text-sm"
        } text-gray-300 truncate" data-i18n="${
    achievement.description_key
  }"></p>
      </div>
    </div>
  `;

  // Add to document and track
  document.body.appendChild(notification);
  activeNotifications.push(notification);

  // Initialize translations for the new elements
  const i18nElements = notification.querySelectorAll("[data-i18n]");
  i18nElements.forEach((element) => {
    const key = element.getAttribute("data-i18n");
    // Split the key by dots and traverse the translations object
    const value = key
      .split(".")
      .reduce((obj, k) => obj && obj[k], translations);
    element.textContent = value || key;
  });

  // Trigger animation
  setTimeout(() => {
    notification.classList.remove("translate-y-full", "opacity-0");
  }, 100);

  // Remove after delay
  setTimeout(() => {
    notification.classList.add("translate-y-full", "opacity-0");
    setTimeout(() => {
      // Remove from tracking and document
      const index = activeNotifications.indexOf(notification);
      if (index > -1) {
        activeNotifications.splice(index, 1);
        // Adjust positions of remaining notifications
        activeNotifications.forEach((n, i) => {
          const newBottom = 16 + (NOTIFICATION_HEIGHT + NOTIFICATION_GAP) * i;
          n.style.bottom = `${newBottom}px`;
        });
      }
      notification.remove();
    }, 500);
  }, 5000);
}

// Function to preserve evaluation content for restoration
export function preserveEvaluationContent() {
  const evaluationResults = document.getElementById("evaluationResults");
  const overallEvaluation = document.getElementById("overallEvaluation");
  const scores = document.getElementById("scores");

  return {
    isHidden: evaluationResults.classList.contains("hidden"),
    overallHtml: overallEvaluation?.innerHTML || "",
    scoresHtml: scores?.innerHTML || "",
  };
}

// Function to restore evaluation content
export function restoreEvaluationContent(content) {
  const evaluationResults = document.getElementById("evaluationResults");
  const overallEvaluation = document.getElementById("overallEvaluation");
  const scores = document.getElementById("scores");

  if (evaluationResults && overallEvaluation && scores && content) {
    // If the evaluation was not hidden, show it
    if (!content.isHidden) {
      evaluationResults.classList.remove("hidden");
    }

    // Restore the HTML content
    overallEvaluation.innerHTML = content.overallHtml;
    scores.innerHTML = content.scoresHtml;
  }
}

// Function to scroll to main evaluation
export function scrollToMainEvaluation() {
  const evaluationResults = document.getElementById("evaluationResults");
  if (evaluationResults) {
    // Get the header height to offset the scroll position
    const header = document.querySelector("header");
    const headerHeight = header ? header.offsetHeight : 0;

    const yOffset = -headerHeight - 20; // Additional 20px buffer
    const y =
      evaluationResults.getBoundingClientRect().top +
      window.pageYOffset +
      yOffset;

    window.scrollTo({
      top: y,
      behavior: "smooth",
    });

    // Refresh achievement display after scrolling
    refreshAchievementDisplay();
  }
}

// Function to scroll to challenge evaluation
export function scrollToChallengeEvaluation() {
  const challengeEval = document.getElementById("challengeEvaluationResults");
  if (challengeEval) {
    challengeEval.scrollIntoView({ behavior: "smooth" });
    refreshAchievementDisplay();
  }
}

// Function to refresh achievement display from server
export async function refreshAchievementDisplay() {
  const isAuthenticated =
    document.querySelector('meta[name="user-authenticated"]')?.content ===
    "true";

  if (isAuthenticated) {
    try {
      const response = await fetch("/get_user_achievements");
      const data = await response.json();

      if (response.ok && data.earned_achievements) {
        earned_achievements = data.earned_achievements;
        sessionStorage.setItem(
          "earned_achievements",
          JSON.stringify(earned_achievements)
        );
      }
    } catch (error) {
      console.error("Error fetching achievements:", error);
    }
  }

  // Update display regardless of authentication status
  await updateAchievementsDisplay();
}

// Function to reset the shown achievement notifications
export function resetShownAchievementNotifications() {
  shownAchievementNotifications.clear();
}
