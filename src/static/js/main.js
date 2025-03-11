import { hexToRgb, rgbToHex, interpolateColor } from "./utils.js";
import {
  DEFAULT_CATEGORIES,
  CATEGORY_ICONS,
  ERROR_MESSAGES,
  EVALUATION_CATEGORIES,
  EVALUATION_TRANSLATION_MAPPING,
  SUPPORTED_LANGUAGES,
  DEFAULT_LANGUAGE,
  CHAR_LIMITS,
  VOICE_LIMITS,
  TIMING,
} from "./constants.js";
import {
  typeWriter,
  updateQuestionDisplay,
  scoreToColor,
  setupCharCounter,
} from "./helpers.js";
import { translations } from "./translations.js";
import {
  initializeAchievements,
  showEvaluationSection,
  showAchievementNotification,
  preserveEvaluationContent,
  restoreEvaluationContent,
  refreshAchievementDisplay,
  updateAchievementsDisplay,
  resetShownAchievementNotifications,
} from "./evaluation.js";
import { initMainVoiceInput, initChallengeVoiceInput } from "./voice.js";

// Initialize mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: "default",
  flowchart: {
    curve: "linear",
    htmlLabels: true,
    wrap: true,
  },
});

// Global variable that stores your selected category values.
let selectedCategories = [];
// Global variable to store the currently displayed question.
let currentQuestion = null;

// Initialize voice input maxlength and counter
const voiceTranscript = document.getElementById("voiceTranscript");
const voiceCount = document.getElementById("voiceCount");
if (voiceTranscript && voiceCount) {
  voiceTranscript.setAttribute("maxlength", CHAR_LIMITS.VOICE.toString());
  voiceCount.textContent = CHAR_LIMITS.VOICE.toString();
}

// Initialize challenge voice input maxlength and counter
let challengeVoiceTranscript = document.getElementById(
  "challengeVoiceTranscript"
);
let challengeVoiceCount = document.getElementById("challengeVoiceCount");
if (challengeVoiceTranscript && challengeVoiceCount) {
  challengeVoiceTranscript.setAttribute(
    "maxlength",
    CHAR_LIMITS.VOICE.toString()
  );
  challengeVoiceCount.textContent = CHAR_LIMITS.VOICE.toString();
}

// Get all achievements data from the script tag
const all_achievements = JSON.parse(
  document.getElementById("all-achievements-data").textContent
);

// Get authentication state
const current_user_authenticated =
  document.querySelector('meta[name="user-authenticated"]')?.content === "true";
const current_user_username =
  document.querySelector('meta[name="user-username"]')?.content || "Anonymous";

// Get initial earned achievements from sessionStorage or DOM
let earned_achievements = [];

// This function is now imported from evaluation.js
async function initLocalAchievements() {
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
        return;
      }
    } catch (error) {
      console.error("Error fetching user achievements:", error);
      // Continue to fallback methods
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
}

// Call the local initialization function
initLocalAchievements();

// This function has been moved to evaluation.js
// Using local function name to avoid conflicts
async function updateLocalAchievementsDisplay(newAchievements = []) {
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
  } else {
    // For authenticated users, always get the freshest data
    if (isAuthenticated) {
      try {
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
        console.error("Error fetching achievements:", error);
        // Fall back to sessionStorage
        const storedAchievements = sessionStorage.getItem(
          "earned_achievements"
        );
        if (storedAchievements) {
          earned_achievements = JSON.parse(storedAchievements);
        }
      }
    } else {
      // For non-authenticated users, rely on sessionStorage
      const storedAchievements = sessionStorage.getItem("earned_achievements");
      if (storedAchievements) {
        earned_achievements = JSON.parse(storedAchievements);
      }
    }
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

// Modified getNewQuestion function:
// 1. It appends the selectedCategories as a query parameter to the request URL.
// 2. After fetching a new question, it stores that question in sessionStorage.
async function getNewQuestion(shouldScroll = true) {
  try {
    // Reset shown achievement notifications when getting a new question
    resetShownAchievementNotifications();

    let query = "";
    if (selectedCategories.length > 0) {
      const encodedCategories = selectedCategories.map(encodeURIComponent);
      query = `?categories=${encodedCategories.join(",")}`;
    }
    const response = await fetch("/get_question" + query);

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Error fetching new question:", errorData.error);

      // Show a message to the user if no questions are available
      const questionElem = document.getElementById("questionDescription");
      if (questionElem) {
        questionElem.textContent =
          translations.errors?.noQuestionsAvailable ||
          "No questions available for the selected categories. Try selecting different categories.";
      }
      return;
    }

    const question = await response.json();
    if (question.error) {
      console.error("Error fetching new question:", question.error);
      return;
    }

    currentQuestion = {
      ...question,
      id: question.id, // Ensure ID is included
      category: question.category,
      description: question.description,
    };
    sessionStorage.setItem("currentQuestion", JSON.stringify(currentQuestion));

    document.getElementById("claimInput").value = "";
    document.getElementById("argumentInput").value = "";
    document.getElementById("counterargumentInput").value = "";

    // Animate the new question description
    const questionElem = document.getElementById("questionDescription");
    if (questionElem) {
      typeWriter(questionElem, question.description, 15);
    }

    // Update only the category badge, and not the question text again
    const categoryBadge = document.getElementById("categoryBadge");
    if (categoryBadge) {
      const translatedCategory =
        translations.categories[question.category] || question.category;
      const categoryText = CATEGORY_ICONS[question.category]
        ? `${CATEGORY_ICONS[question.category]} ${translatedCategory}`
        : translatedCategory;
      categoryBadge.textContent = categoryText;
    }

    if (questionElem && shouldScroll) {
      questionElem.scrollIntoView({
        behavior: "smooth",
        block: "start",
        inline: "nearest",
      });

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }
  } catch (error) {
    console.error("Error fetching new question:", error);
  }
}

// Expose it globally
window.getNewQuestion = getNewQuestion;

// Add new function to handle session update and UI refresh
async function updateAuthUI(userData, redirect = false) {
  try {
    const response = await fetch("/update_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userData || {}),
    });
    if (!response.ok) throw new Error("Failed to update session");

    const result = await response.json();
    const info = result.user || result;

    // Update username
    const usernameElem = document.getElementById("usernameElem");
    if (usernameElem) {
      usernameElem.textContent = info.username || "Anonymous";
    }

    // Update level info
    const userLevelElem = document.getElementById("userLevelElem");
    if (userLevelElem && info.level_info) {
      userLevelElem.textContent = info.level_info.display_name;
    }

    // Update level number
    const levelNumber = document.getElementById("levelNumber");
    if (levelNumber && info.level_info) {
      levelNumber.textContent = info.level_info.level_number;
    }

    // Update XP bar
    const miniXpBarFill = document.getElementById("miniXpBarFill");
    if (miniXpBarFill && info.level_info) {
      miniXpBarFill.style.width = `${info.level_info.progress_percent}%`;
    }

    // Update login/logout button
    const loginButton = document.querySelector("#loginButton");
    if (loginButton) {
      const logoutButton = document.createElement("button");
      logoutButton.className =
        "bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-full text-sm";
      logoutButton.onclick = handleLogout;
      logoutButton.textContent = "Logout";
      loginButton.replaceWith(logoutButton);
    }

    if (redirect) {
      window.location.href = "/profile";
    }
  } catch (error) {
    console.error("Failed to update UI:", error);
  }
}

// Make handleLogout available globally
window.handleLogout = handleLogout;

// Add event listener for logout button
document.addEventListener("DOMContentLoaded", () => {
  const logoutButton = document.querySelector("#logoutButton");
  if (logoutButton) {
    logoutButton.addEventListener("click", handleLogout);
  }
});

async function handleLogout() {
  try {
    // Save current question and form data to localStorage before logout
    if (currentQuestion) {
      localStorage.setItem(
        "preservedQuestion",
        JSON.stringify(currentQuestion)
      );
    }

    // Save form data
    const claimInput = document.getElementById("claimInput");
    const argumentInput = document.getElementById("argumentInput");
    const counterargumentInput = document.getElementById(
      "counterargumentInput"
    );
    const voiceTranscript = document.getElementById("voiceTranscript");
    const challengeResponseInput = document.getElementById(
      "challengeResponseInput"
    );

    if (claimInput)
      localStorage.setItem("preservedClaimInput", claimInput.value);
    if (argumentInput)
      localStorage.setItem("preservedArgumentInput", argumentInput.value);
    if (counterargumentInput)
      localStorage.setItem(
        "preservedCounterargumentInput",
        counterargumentInput.value
      );
    if (voiceTranscript)
      localStorage.setItem("preservedVoiceTranscript", voiceTranscript.value);
    if (challengeResponseInput)
      localStorage.setItem(
        "preservedChallengeResponseInput",
        challengeResponseInput.value
      );

    // Save evaluation content
    const evaluationContent = preserveEvaluationContent();
    localStorage.setItem(
      "preservedEvaluationContent",
      JSON.stringify(evaluationContent)
    );

    const response = await fetch("/logout", { method: "POST" });
    if (response.ok) {
      window.location.reload();
    }
  } catch (error) {
    console.error("Logout failed:", error);
  }
}

// Initialize all counters
setupCharCounter("claimInput", "claimCount", "claim");
setupCharCounter("argumentInput", "argumentCount", "argument");
setupCharCounter(
  "counterargumentInput",
  "counterargumentCount",
  "counterargument"
);
setupCharCounter("challengeResponseInput", "challengeCount", "challenge");

// This function has been moved to level.js
// Using local function name to avoid conflicts
function handleLocalXpAnimations(data, options) {
  const {
    xpInfoElement,
    xpGainedElement,
    xpMessageElement,
    levelUpMessageElement,
    currentLevelElement,
    xpProgressTextElement,
    xpProgressBarElement,
    nextLevelElement,
    oldLevelText,
    isChallenge = false,
  } = options;

  // Check if we should skip animations (no XP gained)
  const xpValue = data.relevance_too_low
    ? 0
    : (isChallenge ? data.challenge_xp_earned : data.xp_gained) || 0;
  const shouldSkipAnimation = xpValue <= 0;

  // Clear any existing content if needed
  if (data.clear_content && xpInfoElement) {
    xpInfoElement.innerHTML = "";
  }

  // Update XP message for relevance warning
  if (xpMessageElement) {
    if (data.relevance_too_low) {
      xpMessageElement.textContent = translations.evaluation.relevanceWarning;
      xpMessageElement.classList.remove("hidden");
    } else {
      xpMessageElement.textContent = "";
      xpMessageElement.classList.add("hidden");
    }
  }

  // Update level up message
  if (levelUpMessageElement) {
    levelUpMessageElement.textContent = data.leveled_up
      ? translations.evaluation.levelUp
      : "";
  }

  // Update XP gained display
  if (xpGainedElement) {
    xpGainedElement.innerHTML = `<strong class="${
      shouldSkipAnimation ? "" : "xp-gained-pop"
    }">${xpValue}</strong>`;
  }

  // If we're skipping animations, update all values immediately
  if (shouldSkipAnimation) {
    if (currentLevelElement) {
      currentLevelElement.innerHTML = `<strong>${data.current_level}</strong>`;
    }

    if (xpProgressTextElement && data.level_info) {
      xpProgressTextElement.textContent = `${data.level_info.xp_into_level} / ${data.level_info.xp_needed}`;
    }

    if (nextLevelElement && data.level_info) {
      nextLevelElement.textContent = data.level_info.next_level;
    }

    if (xpProgressBarElement && data.level_info) {
      xpProgressBarElement.style.transition = "none";
      xpProgressBarElement.style.width = data.level_info.progress_percent + "%";
    }

    // Use local renamed function to avoid identifier conflict
    updateLocalLevelInfo(data.total_xp, data.level_info);

    return null; // No need for observer
  }

  // Only update the level text immediately if not leveling up
  if (currentLevelElement && !data.leveled_up) {
    currentLevelElement.innerHTML = `<strong>${data.current_level}</strong>`;
  }

  // Update XP progress text
  if (xpProgressTextElement && data.level_info) {
    xpProgressTextElement.textContent = `${data.level_info.xp_into_level} / ${data.level_info.xp_needed}`;
  }

  // Update next level text
  if (nextLevelElement && data.level_info) {
    nextLevelElement.textContent = data.level_info.next_level;
  }

  // Create intersection observer for XP animations
  const xpAnimationObserver = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          // Add a small delay to ensure the element is fully visible
          setTimeout(function () {
            const xpInfo = entry.target;

            // Animate XP bar with smooth progress
            const xpProgressBar =
              xpProgressBarElement || xpInfo.querySelector(".xp-progress-bar");
            if (xpProgressBar) {
              // Parse current width as number for comparison
              const currentWidthStr = xpProgressBar.style.width || "0%";
              const currentWidthNum = parseFloat(currentWidthStr);
              const targetWidthNum = data.level_info.progress_percent;
              const targetWidth = targetWidthNum + "%";

              // Only animate if there's xp gained or it's initial load
              // AND if the target width is greater than current width (prevent backward animation)
              // Level-up is an exception which should animate regardless
              if (
                (data.xp_gained === undefined ||
                  data.xp_gained > 0 ||
                  (isChallenge && data.challenge_xp_earned > 0)) &&
                (data.leveled_up || targetWidthNum >= currentWidthNum)
              ) {
                if (data.leveled_up) {
                  // For level up, first animate to 100%, then show level transition, then animate to new progress
                  xpProgressBar.style.transition =
                    "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
                  xpProgressBar.style.width = "100%";

                  // Animate the XP progress text during the first part of the level up animation
                  if (xpProgressTextElement) {
                    // Add animation class
                    xpProgressTextElement.classList.add("count-up-animation");

                    // Animate the numbers counting up to max XP
                    const startXp =
                      parseInt(
                        xpProgressTextElement.textContent.split(" / ")[0]
                      ) || 0;
                    const endXp = parseInt(data.level_info.xp_needed);
                    const xpNeeded = data.level_info.xp_needed;
                    const duration = 800; // match the progress bar animation duration
                    const startTime = performance.now();

                    const animateXpNumbers = function (timestamp) {
                      const elapsed = timestamp - startTime;
                      const progress = Math.min(elapsed / duration, 1);
                      const currentXp = Math.floor(
                        startXp + (endXp - startXp) * progress
                      );

                      xpProgressTextElement.textContent = `${currentXp} / ${xpNeeded}`;

                      if (progress < 1) {
                        requestAnimationFrame(animateXpNumbers);
                      } else {
                        // Animation complete, but don't remove the animation class yet
                        // as we'll continue with the second part of the animation
                      }
                    };

                    requestAnimationFrame(animateXpNumbers);
                  }

                  // After reaching 100%, trigger level transition
                  setTimeout(function () {
                    const levelImageContainer = xpInfo.querySelector(
                      ".level-image-container"
                    );

                    // Get the level text element
                    const levelTextElement = currentLevelElement;
                    // Use the previously stored old level text
                    const originalLevelText = oldLevelText || "";

                    if (levelImageContainer) {
                      // Get the level image element
                      const levelImage =
                        levelImageContainer.querySelector("img");

                      // Store both old and new image sources
                      const oldImageSrc = data.level_info.previous_level_image;
                      const newImageSrc = data.level_info.level_image;

                      if (!oldImageSrc || !newImageSrc) {
                        console.error(
                          "Missing level image sources for animation",
                          {
                            oldImageSrc,
                            newImageSrc,
                            data,
                          }
                        );
                      }

                      // Create a clone of the image for the animation
                      if (levelImage && oldImageSrc && newImageSrc) {
                        // Force the old image to be displayed first
                        levelImage.src = oldImageSrc;
                        levelImage.alt = `Level ${data.previous_level}`;

                        // Force a reflow to ensure the old image is rendered
                        void levelImageContainer.offsetWidth;
                      }

                      // Start glow effect
                      levelImageContainer.classList.add("level-up-glow");

                      // For challenge section, add a special class to control the glow intensity
                      if (isChallenge) {
                        levelImageContainer.classList.add("challenge-glow");
                      }

                      // Start rotation with old image
                      levelImageContainer.classList.add(
                        "level-image-transition"
                      );

                      // Start level text transition if it exists
                      if (levelTextElement) {
                        // Set the text content to the original level text before starting the animation
                        levelTextElement.innerHTML = originalLevelText;

                        // Start the animation
                        levelTextElement.classList.add("level-text-transition");

                        // Update the level text halfway through the animation
                        setTimeout(() => {
                          levelTextElement.innerHTML = `<strong>${data.level_info.display_name}</strong>`;
                        }, 600);

                        // Remove animation class after completion
                        setTimeout(function () {
                          levelTextElement.classList.remove(
                            "level-text-transition"
                          );
                        }, 1200);
                      }

                      // Update the image halfway through the animation
                      setTimeout(function () {
                        const levelImage =
                          levelImageContainer.querySelector("img");
                        if (levelImage && newImageSrc) {
                          // Set the image source to the new level image
                          levelImage.src = newImageSrc;
                          levelImage.alt = `Level ${data.current_level}`;

                          // Force a reflow to ensure the new image is rendered
                          void levelImageContainer.offsetWidth;

                          // Also update all other level images on the page
                          if (!isChallenge) {
                            const otherLevelImages = document.querySelectorAll(
                              ".level-image:not(.level-indicator.challenge-xp .level-image)"
                            );
                            otherLevelImages.forEach((img) => {
                              if (img !== levelImage) {
                                img.src = newImageSrc;
                                img.alt = `Level ${data.current_level}`;
                              }
                            });
                          } else {
                            // For challenge, only update challenge-related images
                            const challengeLevelImages =
                              document.querySelectorAll(
                                ".level-indicator.challenge-xp .level-image"
                              );
                            challengeLevelImages.forEach((img) => {
                              if (img !== levelImage) {
                                img.src = newImageSrc;
                                img.alt = `Level ${data.current_level}`;
                              }
                            });
                          }
                        }
                      }, 600);

                      // Remove glow and rotation classes after animation completes
                      setTimeout(function () {
                        levelImageContainer.classList.remove("level-up-glow");
                        levelImageContainer.classList.remove(
                          "level-image-transition"
                        );

                        // Also remove the challenge-glow class
                        levelImageContainer.classList.remove("challenge-glow");

                        // Reset progress bar to 0 and then animate to new progress
                        xpProgressBar.style.transition = "none";
                        xpProgressBar.style.width = "0%";

                        // Force a reflow
                        void xpProgressBar.offsetWidth;

                        // Animate to the new progress
                        xpProgressBar.style.transition =
                          "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
                        xpProgressBar.style.width = targetWidth;

                        // Animate the XP progress text
                        if (xpProgressTextElement) {
                          // Add animation class
                          xpProgressTextElement.classList.add(
                            "count-up-animation"
                          );

                          // Animate the numbers counting up
                          const startXp = 0;
                          const endXp = parseInt(data.level_info.xp_into_level);
                          const xpNeeded = data.level_info.xp_needed;
                          const duration = 800; // match the progress bar animation duration
                          const startTime = performance.now();
                          const isChallenge = true; // This is in the challenge context

                          const animateXpNumbers = function (timestamp) {
                            const elapsed = timestamp - startTime;
                            const progress = Math.min(elapsed / duration, 1);
                            const currentXp = Math.floor(
                              startXp + (endXp - startXp) * progress
                            );

                            xpProgressTextElement.textContent = `${currentXp} / ${xpNeeded}`;

                            if (progress < 1) {
                              requestAnimationFrame(animateXpNumbers);
                            } else {
                              // Animation complete, remove animation class
                              setTimeout(function () {
                                xpProgressTextElement.classList.remove(
                                  "count-up-animation"
                                );
                              }, 200);
                            }
                          };

                          requestAnimationFrame(animateXpNumbers);
                        }
                      }, 600); // Reduced from 800ms to 600ms to better align with the faster rotation
                    }
                  }, 800);
                } else {
                  // Normal progress animation
                  xpProgressBar.style.transition =
                    "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
                  xpProgressBar.style.width = targetWidth;

                  // Add XP number animation for regular XP gains
                  if (xpProgressTextElement && data.level_info) {
                    // Add animation class
                    xpProgressTextElement.classList.add("count-up-animation");

                    // Animate the numbers counting up
                    const startXp =
                      parseInt(
                        xpProgressTextElement.textContent.split(" / ")[0]
                      ) || 0;
                    const endXp = parseInt(data.level_info.xp_into_level);
                    const xpNeeded = data.level_info.xp_needed;
                    const duration = 800; // match the progress bar animation duration
                    const startTime = performance.now();

                    const animateXpNumbers = function (timestamp) {
                      const elapsed = timestamp - startTime;
                      const progress = Math.min(elapsed / duration, 1);
                      const currentXp = Math.floor(
                        startXp + (endXp - startXp) * progress
                      );

                      xpProgressTextElement.textContent = `${currentXp} / ${xpNeeded}`;

                      if (progress < 1) {
                        requestAnimationFrame(animateXpNumbers);
                      } else {
                        // Animation complete, remove animation class
                        setTimeout(function () {
                          xpProgressTextElement.classList.remove(
                            "count-up-animation"
                          );
                        }, 200);
                      }
                    };

                    requestAnimationFrame(animateXpNumbers);
                  }
                }
              } else {
                // No XP gained, just set the width without animation
                xpProgressBar.style.transition = "none";
                xpProgressBar.style.width = targetWidth;
              }

              // Use local renamed function to avoid identifier conflict
              updateLocalLevelInfo(data.total_xp, data.level_info);
            }

            // Disconnect observer after triggering animations
            xpAnimationObserver.disconnect();
          }, 100); // 100ms delay between each animation
        }
      });
    },
    { threshold: 0.5 } // Increased threshold to ensure more visibility
  );

  // Observe the XP info element
  if (xpInfoElement) {
    xpAnimationObserver.observe(xpInfoElement);
  }

  return xpAnimationObserver;
}

// Updated submission handler for handling both text and voice input
document.getElementById("submitAnswer").addEventListener("click", async () => {
  const startTime = Date.now();
  const errorMessage = document.getElementById("errorMessage");
  const submitBtn = document.getElementById("submitAnswer");
  let claim, argument, counterargument, voice_answer;

  // Determine the current input mode (voice or text)
  const inputMode = window.currentInputMode;
  if (inputMode === "voice") {
    const voiceResponse = document
      .getElementById("voiceTranscript")
      .value.trim();
    if (!voiceResponse) {
      const defaultError = "Please provide your response before submitting.";
      errorMessage.textContent =
        translations?.errors?.voiceRequiredField || defaultError;
      errorMessage.classList.remove("hidden");
      return;
    }

    if (voiceResponse.length > CHAR_LIMITS.VOICE) {
      const defaultError = `Please reduce your response to ${CHAR_LIMITS.VOICE} characters or less.`;
      errorMessage.textContent = translations?.errors?.tooLong || defaultError;
      errorMessage.classList.remove("hidden");
      return;
    }

    // For voice mode, split the response into claim and argument portions
    const maxLength = CHAR_LIMITS.CHALLENGE;

    // For voice input, we need to handle the claim differently
    // Set claim and argument to placeholders and keep the full response in voice_answer
    claim = voiceResponse.substring(0, 100) + "..."; // Just a placeholder
    argument = "See voice answer"; // Just a placeholder
    voice_answer = voiceResponse; // Send the full voice response separately
    counterargument =
      document.getElementById("counterargumentInput").value.trim() || "";
  } else {
    claim = document.getElementById("claimInput").value.trim();
    argument = document.getElementById("argumentInput").value.trim();
    counterargument = document
      .getElementById("counterargumentInput")
      .value.trim();

    if (!claim || !argument) {
      const defaultError =
        "Please fill in both required fields (Claim and Argument) before submitting.";
      errorMessage.textContent =
        translations?.errors?.requiredFields || defaultError;
      errorMessage.classList.remove("hidden");
      return;
    }

    // Check character limits for text mode
    if (
      claim.length > CHAR_LIMITS.CHALLENGE ||
      argument.length > CHAR_LIMITS.CHALLENGE
    ) {
      const defaultError = `Please ensure each field is ${CHAR_LIMITS.CHALLENGE} characters or less.`;
      errorMessage.textContent = translations?.errors?.tooLong || defaultError;
      errorMessage.classList.remove("hidden");
      return;
    }
  }

  const payload = {
    claim,
    argument,
    counterargument: counterargument || null,
    input_mode: inputMode,
    question_id: currentQuestion?.id,
  };

  // Include voice_answer in the payload when using voice input
  if (inputMode === "voice" && voice_answer) {
    payload.voice_answer = voice_answer;
  }

  if (currentQuestion?.id) {
    payload.question_id = currentQuestion.id;

    // For custom questions, include the question text in the payload
    if (currentQuestion.isCustom) {
      payload.question_text = currentQuestion.description;
    }
  }

  // Before processing the new response, clear any previous challenge content:
  const challengeSection = document.getElementById("challengeSection");
  if (challengeSection) {
    challengeSection.classList.add("hidden");
  }
  const challengeResponseInput = document.getElementById(
    "challengeResponseInput"
  );
  if (challengeResponseInput) {
    challengeResponseInput.value = "";
  }
  const challengeEvalDiv = document.getElementById(
    "challengeEvaluationResults"
  );
  if (challengeEvalDiv) {
    challengeEvalDiv.innerHTML = "";
    challengeEvalDiv.classList.add("hidden");
  }
  document.getElementById("challengeErrorMessage").textContent = "";

  // Disable button and show loading state
  submitBtn.innerHTML = `${translations.challenge.analyzing} <span class="spinner"></span>`;
  submitBtn.disabled = true;

  try {
    const response = await fetch("/submit_answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    // Calculate remaining time only for successful responses
    if (response.ok) {
      const elapsed = Date.now() - startTime;
      if (elapsed < TIMING.EVALUATION_DELAY) {
        await new Promise((resolve) =>
          setTimeout(resolve, TIMING.EVALUATION_DELAY - elapsed)
        );
      }
    }

    const data = await response.json(); // Single parse here

    if (!response.ok) {
      if (response.status === 409) {
        document.getElementById("errorMessage").textContent =
          translations.errors.similarAnswer;
        submitBtn.innerHTML = "Submit";
        submitBtn.disabled = false;
        return;
      }
      if (data.error === "tooManySubmissions") {
        document.getElementById("errorMessage").textContent =
          translations.errors.tooManySubmissions;
        submitBtn.innerHTML = "Submit";
        submitBtn.disabled = false;
        return;
      }
      document.getElementById("errorMessage").innerHTML =
        data.error || ERROR_MESSAGES.UNEXPECTED_ERROR;
      submitBtn.innerHTML = "Submit";
      submitBtn.disabled = false;
      return;
    }

    if (!data || !data.evaluation) {
      document.getElementById("errorMessage").textContent =
        "Invalid response from server";
      submitBtn.innerHTML = "Submit";
      submitBtn.disabled = false;
      return;
    }

    submitBtn.innerHTML = "Submit";
    submitBtn.disabled = false;

    // First display overall evaluation with a prominent total score bar
    const overallEvalDiv = document.getElementById("overallEvaluation");
    const totalScore = data.evaluation.total_score;
    const totalScorePercent = totalScore * 10;
    const totalScoreColor = scoreToColor(totalScore);

    overallEvalDiv.innerHTML = `
      <p class="text-l font-bold mb-2">
        ${
          translations.evaluation.overall
        }: <span id="totalScoreValue">${totalScore.toFixed(1)}/10</span>
      </p>
      <div class="w-full bg-gray-200 rounded-full h-2.5 mb-2">
        <div id="totalScoreBar" class="rounded-full total-progress-bar"
             style="width: 0%; background-color: ${totalScoreColor}; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
      </div>
      <p id="overallFeedback" class="text-md">
        ${data.evaluation.overall_feedback}
</p>
    `;

    // Now set the score color after the element exists
    document.getElementById("totalScoreValue").style.color = totalScoreColor;

    // Animate the overall score bar after a short delay
    setTimeout(() => {
      const totalScoreBar = document.getElementById("totalScoreBar");
      if (totalScoreBar) {
        totalScoreBar.style.width = `${totalScorePercent}%`;
      }
    }, 100);

    // Add argument structure visualization if available
    if (
      data.evaluation.argument_structure &&
      Array.isArray(data.evaluation.argument_structure.nodes) &&
      data.evaluation.argument_structure.nodes.some(
        (node) => node.text && node.text.trim().length > 0
      )
    ) {
      const structure = data.evaluation.argument_structure;

      // Create a mapping for safe node IDs to avoid spaces or special characters issues.
      const safeIds = {};
      structure.nodes.forEach((node, index) => {
        safeIds[node.id] = "node" + index;
      });

      overallEvalDiv.innerHTML += `
        <div class="mt-6 flex justify-center">
          <div class="w-full max-w-full bg-white rounded-xl shadow-sm border border-gray-100 argument-structure-box">
            <h3 class="text-base sm:text-lg mb-3 text-center text-gray-800">
              <span class="font-bold">${
                translations.evaluation.argumentstructure.split("(")[0]
              }</span><span class="font-normal text-gray-500">(${
        translations.evaluation.argumentstructure.split("(")[1]
      }</span>
            </h3>
            <div id="argumentStructureViz" class="overflow-x-auto flex justify-center"></div>
          </div>
        </div>
      `;

      // Check if screen is mobile
      const isMobile = window.innerWidth < 768;
      // Use shorter line length on mobile
      const maxLineLength = isMobile ? 20 : 40;
      // Adjust words per line based on screen size
      const wordsPerLine = isMobile ? 3 : 4;

      const graph = `graph TD;
        %% Node styling
        classDef default fill:#f1f1f9,stroke:#666666,stroke-width:1px,rx:8,ry:8;
        classDef premise fill:#f1f1f9,stroke:#666666,stroke-width:1px,rx:8,ry:8;
        classDef conclusion fill:#f1f1f9,stroke:#666666,stroke-width:1.5px,rx:8,ry:8;

        %% Define nodes
        ${structure.nodes
          .map((node) => {
            let displayText = node.text;
            // Split into words and add line breaks every few words
            const words = displayText.split(" ");
            let formattedText = "";

            for (let i = 0; i < words.length; i++) {
              formattedText += words[i];
              if (i < words.length - 1) {
                if ((i + 1) % wordsPerLine === 0) {
                  formattedText += "<br/>";
                } else {
                  formattedText += " ";
                }
              }
            }
            return `${safeIds[node.id]}["${formattedText}"]:::${node.type}`;
          })
          .join("\n          ")}

        %% Define edges
        ${structure.edges
          .map((edge) => `${safeIds[edge.from]} --> ${safeIds[edge.to]}`)
          .join("\n          ")}`;

      // Initialize mermaid with updated config
      mermaid.initialize({
        startOnLoad: true,
        theme: "default",
        flowchart: {
          curve: "basis",
          htmlLabels: true,
          wrap: true,
          nodeSpacing: isMobile ? 20 : 40,
          rankSpacing: isMobile ? 40 : 50,
          defaultRenderer: "dagre",
        },
        themeVariables: {
          nodeBorder: "#666666",
          mainBkg: "#f5f5f5",
          nodeTextColor: "#333333",
          lineColor: "#666666",
          fontSize: isMobile ? "14px" : "13px",
          fontFamily:
            "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          edgeLabelBackground: "#f5f5f5",
          arrowheadColor: "#666666",
        },
      });

      // Render graph
      mermaid
        .render("argumentGraph", graph)
        .then((result) => {
          const vizContainer = document.getElementById("argumentStructureViz");
          vizContainer.innerHTML = result.svg;

          // Add resize handler to re-render diagram when screen size changes
          // (like when rotating a mobile device)
          let resizeTimeout;
          const originalWidth = window.innerWidth;

          const handleResize = () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
              // Only re-render if width changed significantly (orientation change)
              const widthDiff = Math.abs(originalWidth - window.innerWidth);
              if (widthDiff > 100) {
                // Remove old event listener to avoid memory leaks
                window.removeEventListener("resize", handleResize);

                // Force re-render by refreshing the section
                if (
                  vizContainer &&
                  vizContainer.closest(".argument-structure-box")
                ) {
                  const parent = vizContainer.closest(
                    ".argument-structure-box"
                  );
                  if (parent && parent.parentElement) {
                    parent.style.opacity = "0.5";
                    setTimeout(() => {
                      parent.style.opacity = "1";
                      // This will trigger the browser to re-render the SVG
                      vizContainer.innerHTML = vizContainer.innerHTML;
                    }, 200);
                  }
                }
              }
            }, 500);
          };

          window.addEventListener("resize", handleResize);
        })
        .catch((error) => {
          console.error("Failed to render argument structure:", error);
        });
    }

    // Now populate the detailed individual factor scores (the look and animation remain unchanged)
    const scoresDiv = document.getElementById("scores");
    scoresDiv.innerHTML = "";

    const evaluationHTML = EVALUATION_CATEGORIES.map((category) => {
      const finalScore = data.evaluation.scores[category] || 0;
      const finalWidthPercent = finalScore * 10;
      const color = scoreToColor(finalScore);
      const feedbackText = data.evaluation.feedback[category] || "";

      // Get translation key from mapping
      const translationKey = EVALUATION_TRANSLATION_MAPPING[category];

      return `
        <div class="mb-2 score-item">
          <div class="flex justify-between items-center">
            <span data-i18n="evaluation.scores.${translationKey}">${
        translations.evaluation.scores[translationKey] || category
      }</span>
            <span class="font-medium score-value" style="color: ${color};">${finalScore}/10</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
            <div class="rounded-full h-2 score-bar"
                 style="width: 0%; background-color: ${color}; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
          </div>
          <p class="text-sm text-gray-500">${feedbackText}</p>
        </div>
      `;
    }).join("");

    scoresDiv.innerHTML = evaluationHTML;

    setTimeout(() => {
      document.querySelectorAll(".score-bar").forEach((bar, index) => {
        const delay = index * 100;
        setTimeout(() => {
          const scoreItem = bar.closest(".score-item");
          const scoreValue = scoreItem.querySelector(".score-value");
          const finalScore = parseFloat(scoreValue.textContent);
          const scorePercent = finalScore * 10;
          bar.style.width = `${scorePercent}%`;
        }, delay);
      });
      document
        .querySelectorAll(".score-value")
        .forEach((scoreElement, index) => {
          const finalScore = parseFloat(scoreElement.dataset.final);
          const targetColor = scoreElement.dataset.color || "#16a34a";
          const startColor = hexToRgb("#e53e3e");
          const endColor = hexToRgb(targetColor);
          let current = 1;
          const updateScore = () => {
            if (current <= finalScore) {
              const factor = (current - 1) / 9;
              const interpolated = interpolateColor(
                startColor,
                endColor,
                factor
              );
              scoreElement.style.color = rgbToHex(
                interpolated.r,
                interpolated.g,
                interpolated.b
              );
              scoreElement.textContent = `${current}/10`;
              current++;
              requestAnimationFrame(updateScore);
            }
          };
          requestAnimationFrame(updateScore);
        });
      document.querySelectorAll(".feedback").forEach((paragraph, index) => {
        const delay = index * 100;
        setTimeout(() => {
          typeWriter(paragraph, paragraph.getAttribute("data-final"), 15);
        }, delay);
      });
    }, 100);

    // Insert the following snippet before the '// Update XP and level info with animations' comment
    if (data.leveled_up) {
      var oldLevelText = document.getElementById("currentLevel")
        ? document.getElementById("currentLevel").innerHTML
        : "";
    } else {
      var oldLevelText = "";
    }

    // Get the current XP progress state before evaluation
    const currentXpProgressBar = document.querySelector(".xp-progress-bar");
    let currentProgressWidth = 0;
    if (currentXpProgressBar) {
      currentProgressWidth = parseFloat(currentXpProgressBar.style.width) || 0;
    }

    // Use the shared function for XP animations
    const xpInfo = document.getElementById("xpInfo");
    const mainXpGainedElement = document.getElementById("xpGained");
    const mainXpMessageElement = document.getElementById("xpMessage");
    const mainLevelUpMessageElement = document.getElementById("levelUpMessage");
    const mainCurrentLevelElement = document.getElementById("currentLevel");
    const mainXpProgressTextElement = document.getElementById("xpProgressText");
    const mainXpProgressBarElement = xpInfo.querySelector(".xp-progress-bar");
    const mainNextLevelElement = document.getElementById("nextLevel");

    // Before running handleXpAnimations, set the progress bar to the current value
    // to ensure we start the animation from the current state
    if (mainXpProgressBarElement) {
      mainXpProgressBarElement.style.width = `${currentProgressWidth}%`;
    }

    handleLocalXpAnimations(data, {
      xpInfoElement: xpInfo,
      xpGainedElement: mainXpGainedElement,
      xpMessageElement: mainXpMessageElement,
      levelUpMessageElement: mainLevelUpMessageElement,
      currentLevelElement: mainCurrentLevelElement,
      xpProgressTextElement: mainXpProgressTextElement,
      xpProgressBarElement: mainXpProgressBarElement,
      nextLevelElement: mainNextLevelElement,
      oldLevelText,
      isChallenge: false,
    });

    // Show the evaluation section
    showEvaluationSection(document.getElementById("evaluationResults"), false);

    // Remove any previous scroll behavior
    window.removeEventListener("scroll", localScrollToChallengeEvaluation);

    // Ensure we scroll to the start of the main evaluation section
    requestAnimationFrame(() => {
      localScrollToMainEvaluation();
    });

    // Make sure the XP info section is visible
    if (xpInfo) {
      xpInfo.classList.remove("hidden");
      xpInfo.style.display = "block";
    }

    // After a successful answer submission, store the answer ID for later use:
    if (data.answer_id) {
      sessionStorage.setItem("lastAnswerId", data.answer_id);
    }

    // If the evaluation contains a challenge, display the challenge text and reveal the challenge section.
    if (data.evaluation && data.evaluation.challenge) {
      const challengeSection = document.getElementById("challengeSection");
      const challengeTextElem = document.getElementById("challengeText");
      if (challengeTextElem && challengeSection) {
        challengeTextElem.textContent = data.evaluation.challenge;
        challengeSection.classList.remove("hidden");
        challengeSection.style.display = "block"; // Explicitly set display to block
      } else {
        console.error("Challenge section or text element not found:", {
          challengeSection,
          challengeTextElem,
        });
      }
    }

    // Make sure the XP info is properly initialized and displayed
    if (mainXpGainedElement && data.xp_gained !== undefined) {
      mainXpGainedElement.innerHTML = `<strong>${data.xp_gained}</strong>`;
    }

    // Make sure the level info is properly displayed
    const currentLevelElement = document.getElementById("currentLevel");
    if (currentLevelElement && !data.leveled_up) {
      currentLevelElement.innerHTML = `<strong>${data.level_info.display_name}</strong>`;
    }
    // Otherwise, if leveling up, we rely on the delayed update in the animation block

    // Only set initial progress bar state if we're not going to animate it
    const xpProgressBar = document.querySelector("#xpInfo .xp-progress-bar");
    if (xpProgressBar && data.xp_gained === 0) {
      xpProgressBar.style.width = `${data.level_info.progress_percent}%`;
    }

    // Make sure the XP progress text is properly displayed
    const xpProgressText = document.getElementById("xpProgressText");
    if (xpProgressText) {
      xpProgressText.textContent = `${data.level_info.xp_into_level} / ${data.level_info.xp_needed}`;
    }

    // Make sure the next level text is properly displayed
    const nextLevelElement = document.getElementById("nextLevel");
    if (nextLevelElement) {
      nextLevelElement.textContent = data.level_info.next_level;
    }

    // Update character count for the challenge response text area.
    const challengeResponseInput = document.getElementById(
      "challengeResponseInput"
    );
    if (challengeResponseInput) {
      challengeResponseInput.addEventListener("input", () => {
        document.getElementById("challengeErrorMessage").textContent = "";
      });
    }

    // Display XP message
    const challengeXpMessage = document.createElement("p");
    challengeXpMessage.classList.add("text-sm", "text-red-600", "mt-4");
    challengeXpMessage.textContent = data.relevance_too_low
      ? translations.evaluation.relevanceWarning
      : "";

    // Make sure we have a place to put the XP message
    let challengeXpInfo = document.getElementById("challengeXpInfo");
    if (challengeXpInfo) {
      // Clear any existing content
      challengeXpInfo.innerHTML = "";

      // Add the XP message
      challengeXpInfo.appendChild(challengeXpMessage);

      // Make sure the challenge XP info section is visible
      challengeXpInfo.classList.remove("hidden");
      challengeXpInfo.style.display = "block";
    }

    // Show achievement notifications if any were awarded
    if (data.achievements) {
      // Update our local achievement list and fetch from server
      await updateAchievementsDisplay(data.achievements);

      // Update the achievement counter in the UI
      const achievementCounterElement = document.querySelector(
        ".text-lg.font-bold.mb-4 .text-gray-600.font-normal"
      );
      if (achievementCounterElement) {
        try {
          // Get the current text content
          const counterText = achievementCounterElement.textContent.trim();
          // Parse the current count and total count
          const matches = counterText.match(/\((\d+)\/(\d+)\)/);
          if (matches && matches.length >= 3) {
            const currentEarnedCount =
              parseInt(matches[1]) + data.achievements.length;
            const totalCount = parseInt(matches[2]);
            // Update the counter text
            achievementCounterElement.textContent = `(${currentEarnedCount}/${totalCount})`;
          }
        } catch (parseError) {
          console.error("Error updating achievement counter:", parseError);
        }
      }
    }

    // After the evaluation is displayed, scroll to it
    setTimeout(() => {
      localScrollToMainEvaluation();
    }, 100); // Small delay to ensure the content is rendered

    // Update main evaluation XP and warning
    const xpMessage = document.getElementById("xpMessage");
    const xpGained = document.getElementById("xpGained");

    if (data.relevance_too_low) {
      if (xpMessage) {
        xpMessage.textContent = translations.evaluation.relevanceWarning;
        xpMessage.classList.remove("hidden");
      }
      if (xpGained) {
        xpGained.innerHTML = "<strong>0</strong>";
      }
    } else {
      if (xpMessage) {
        xpMessage.textContent = "";
        xpMessage.classList.add("hidden");
      }
      if (xpGained) {
        xpGained.innerHTML = `<strong>${data.xp_gained}</strong>`;
      }
    }

    // Update achievements display
    if (data.achievements) {
      await updateAchievementsDisplay(data.achievements);
    } else {
      // Even if no new achievements, refresh the display to ensure consistency
      await refreshAchievementDisplay();
    }
  } catch (error) {
    console.error("Error submitting answer:", error);
    document.getElementById("errorMessage").textContent =
      ERROR_MESSAGES.UNEXPECTED_ERROR;
    submitBtn.textContent = "Submit";
    submitBtn.disabled = false;
  }
});

document
  .getElementById("rerollButton")
  .addEventListener("click", () => getNewQuestion(false));

// Function to restore saved text field values after login/signup
function restoreSavedTextFieldValues() {
  try {
    // Get the saved text field values
    const savedClaimInput = localStorage.getItem("savedClaimInput");
    const savedArgumentInput = localStorage.getItem("savedArgumentInput");
    const savedCounterargumentInput = localStorage.getItem(
      "savedCounterargumentInput"
    );
    const savedVoiceTranscript = localStorage.getItem("savedVoiceTranscript");
    const savedChallengeResponseInput = localStorage.getItem(
      "savedChallengeResponseInput"
    );
    const savedInputMode = localStorage.getItem("savedInputMode");

    // Restore text field values if they exist
    const claimInput = document.getElementById("claimInput");
    const argumentInput = document.getElementById("argumentInput");
    const counterargumentInput = document.getElementById(
      "counterargumentInput"
    );
    const voiceTranscript = document.getElementById("voiceTranscript");
    const challengeResponseInput = document.getElementById(
      "challengeResponseInput"
    );

    if (claimInput && savedClaimInput) claimInput.value = savedClaimInput;
    if (argumentInput && savedArgumentInput)
      argumentInput.value = savedArgumentInput;
    if (counterargumentInput && savedCounterargumentInput)
      counterargumentInput.value = savedCounterargumentInput;
    if (voiceTranscript && savedVoiceTranscript)
      voiceTranscript.value = savedVoiceTranscript;
    if (challengeResponseInput && savedChallengeResponseInput)
      challengeResponseInput.value = savedChallengeResponseInput;

    // Restore input mode if it exists
    if (savedInputMode) {
      window.currentInputMode = savedInputMode;

      // Switch to the correct input mode tab
      if (savedInputMode === "voice") {
        const voiceModeTab = document.getElementById("voiceModeTab");
        const textModeTab = document.getElementById("textModeTab");
        const voiceInputSection = document.getElementById("voiceInputSection");
        const textInputSection = document.getElementById("textInputSection");

        if (
          voiceModeTab &&
          textModeTab &&
          voiceInputSection &&
          textInputSection
        ) {
          voiceModeTab.classList.add("active");
          textModeTab.classList.remove("active");
          voiceInputSection.style.display = "block";
          textInputSection.style.display = "none";
        }
      }
    }

    // Restore evaluation section state if it was visible
    if (localStorage.getItem("evaluationVisible") === "true") {
      const evaluationResults = document.getElementById("evaluationResults");
      if (evaluationResults) {
        // Restore the overall evaluation content
        const overallEvaluation = document.getElementById("overallEvaluation");
        const savedOverallEvaluation = localStorage.getItem(
          "savedOverallEvaluation"
        );
        if (overallEvaluation && savedOverallEvaluation) {
          overallEvaluation.innerHTML = savedOverallEvaluation;
        }

        // Restore the scores content
        const scores = document.getElementById("scores");
        const savedScores = localStorage.getItem("savedScores");
        if (scores && savedScores) {
          scores.innerHTML = savedScores;
        }

        // Make the evaluation section visible
        evaluationResults.classList.remove("hidden");
        evaluationResults.style.display = "block";

        // Restore challenge section state
        const challengeSection = document.getElementById("challengeSection");
        if (
          challengeSection &&
          localStorage.getItem("challengeSectionVisible") === "true"
        ) {
          // Restore challenge text
          const challengeText = document.getElementById("challengeText");
          const savedChallengeText = localStorage.getItem("savedChallengeText");
          if (challengeText && savedChallengeText) {
            challengeText.textContent = savedChallengeText;
          }

          // Make the challenge section visible
          challengeSection.classList.remove("hidden");

          // Restore challenge evaluation results if they were visible
          const challengeEvaluationResults = document.getElementById(
            "challengeEvaluationResults"
          );
          if (
            challengeEvaluationResults &&
            localStorage.getItem("challengeEvaluationVisible") === "true"
          ) {
            const savedChallengeEvaluation = localStorage.getItem(
              "savedChallengeEvaluation"
            );
            if (savedChallengeEvaluation) {
              challengeEvaluationResults.innerHTML = savedChallengeEvaluation;
              challengeEvaluationResults.classList.remove("hidden");
            }
          }
        }

        // Restore the last answer ID for challenge submission
        const savedLastAnswerId = localStorage.getItem("savedLastAnswerId");
        if (savedLastAnswerId) {
          sessionStorage.setItem("lastAnswerId", savedLastAnswerId);
        }
      }
    }

    // Clear the saved values from localStorage
    localStorage.removeItem("savedClaimInput");
    localStorage.removeItem("savedArgumentInput");
    localStorage.removeItem("savedCounterargumentInput");
    localStorage.removeItem("savedVoiceTranscript");
    localStorage.removeItem("savedChallengeResponseInput");
    localStorage.removeItem("savedInputMode");
    localStorage.removeItem("evaluationVisible");
    localStorage.removeItem("savedOverallEvaluation");
    localStorage.removeItem("savedScores");
    localStorage.removeItem("challengeSectionVisible");
    localStorage.removeItem("savedChallengeText");
    localStorage.removeItem("challengeEvaluationVisible");
    localStorage.removeItem("savedChallengeEvaluation");
    localStorage.removeItem("savedLastAnswerId");
  } catch (error) {
    console.error("Error restoring form data from localStorage:", error);
    // Continue even if restoration fails
  }
}

// Update the DOMContentLoaded handler
window.addEventListener("DOMContentLoaded", async () => {
  // Initialize the voice input modules
  initMainVoiceInput();
  initChallengeVoiceInput();

  // Reset shown achievement notifications
  resetShownAchievementNotifications();

  // Make sure we initialize with fresh achievements data
  await initializeAchievements(all_achievements);

  // Initialize achievements from evaluation.js
  initializeAchievements(all_achievements);
  // Restore saved text field values if they exist
  restoreSavedTextFieldValues();

  const language = localStorage.getItem("language") || "en";

  // Update the server-side session language to match localStorage
  try {
    await fetch("/set_language", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ language }),
    });
  } catch (error) {
    console.error("Error setting language on server:", error);
  }

  try {
    // Check for language in URL path
    const pathSegments = window.location.pathname.split("/").filter(Boolean);
    const pathLang = pathSegments[0];

    if (["en", "de"].includes(pathLang)) {
      if (pathLang !== localStorage.getItem("language")) {
        // Update localStorage and server-side language
        await fetch("/set_language", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ language: pathLang }),
        });

        localStorage.setItem("language", pathLang);
        window.location.reload();
        return;
      }
    }

    // Only load categories if we're not changing language
    await loadSavedCategories();
  } catch (error) {
    console.error("Error in DOMContentLoaded:", error);
    // Ensure we have a valid language set
    localStorage.setItem("language", DEFAULT_LANGUAGE);
  }

  // Add event delegation for settings button
  document.addEventListener("click", (e) => {
    const settingsButton = e.target.closest("#settingsButton");
    if (settingsButton) {
      e.stopPropagation();
      const modalOverlay = document.getElementById("modalOverlay");
      if (modalOverlay) {
        modalOverlay.classList.remove("hidden");
        const categoriesError = document.getElementById("categoriesError");
        if (categoriesError) {
          categoriesError.classList.add("hidden");
        }
      }
    }

    // Handle modal overlay click to close
    const modalOverlay = e.target.closest("#modalOverlay");
    if (modalOverlay && e.target === modalOverlay) {
      if (document.querySelectorAll(".category-item.selected").length === 0) {
        document.getElementById("categoriesError").classList.remove("hidden");
      } else {
        modalOverlay.classList.add("hidden");
        updateSelectedCategories();
      }
    }

    // Handle close button click
    const closeButton = e.target.closest("#closeCategories");
    if (closeButton) {
      e.stopPropagation();
      if (document.querySelectorAll(".category-item.selected").length === 0) {
        document.getElementById("categoriesError").classList.remove("hidden");
        return;
      }
      document.getElementById("modalOverlay").classList.add("hidden");
      updateSelectedCategories();
    }
  });

  // Add event delegation for category items
  document.addEventListener("click", (e) => {
    const categoryItem = e.target.closest(".category-item");
    if (categoryItem) {
      categoryItem.classList.toggle("selected");
      if (categoryItem.classList.contains("selected")) {
        categoryItem.classList.add("bg-gray-800", "text-white");
        categoryItem.classList.remove("bg-white", "text-black");
      } else {
        categoryItem.classList.remove("bg-gray-800", "text-white");
        categoryItem.classList.add("bg-white", "text-black");
      }
    }
  });

  // Load saved categories and handle stored question
  loadSavedCategories().then(() => {
    // First check if we have preserved data from a login/logout
    const preservedQuestion = localStorage.getItem("preservedQuestion");

    if (preservedQuestion) {
      // We have preserved data from login/logout
      currentQuestion = JSON.parse(preservedQuestion);
      updateQuestionDisplay(currentQuestion);

      // Remove from localStorage so it's not used again
      localStorage.removeItem("preservedQuestion");

      // Restore form data
      const claimInput = document.getElementById("claimInput");
      const argumentInput = document.getElementById("argumentInput");
      const counterargumentInput = document.getElementById(
        "counterargumentInput"
      );
      const voiceTranscript = document.getElementById("voiceTranscript");
      const challengeResponseInput = document.getElementById(
        "challengeResponseInput"
      );

      if (claimInput && localStorage.getItem("preservedClaimInput")) {
        claimInput.value = localStorage.getItem("preservedClaimInput");
        localStorage.removeItem("preservedClaimInput");
      }

      if (argumentInput && localStorage.getItem("preservedArgumentInput")) {
        argumentInput.value = localStorage.getItem("preservedArgumentInput");
        localStorage.removeItem("preservedArgumentInput");
      }

      if (
        counterargumentInput &&
        localStorage.getItem("preservedCounterargumentInput")
      ) {
        counterargumentInput.value = localStorage.getItem(
          "preservedCounterargumentInput"
        );
        localStorage.removeItem("preservedCounterargumentInput");
      }

      if (voiceTranscript && localStorage.getItem("preservedVoiceTranscript")) {
        voiceTranscript.value = localStorage.getItem(
          "preservedVoiceTranscript"
        );
        localStorage.removeItem("preservedVoiceTranscript");
      }

      if (
        challengeResponseInput &&
        localStorage.getItem("preservedChallengeResponseInput")
      ) {
        challengeResponseInput.value = localStorage.getItem(
          "preservedChallengeResponseInput"
        );
        localStorage.removeItem("preservedChallengeResponseInput");
      }

      // Restore evaluation content if it exists
      const preservedEvaluationContent = localStorage.getItem(
        "preservedEvaluationContent"
      );
      if (preservedEvaluationContent) {
        const evaluationContent = JSON.parse(preservedEvaluationContent);
        restoreEvaluationContent(evaluationContent);
        localStorage.removeItem("preservedEvaluationContent");
      }
    } else {
      // Normal flow - check sessionStorage, then get a new question if needed
      const storedQuestion = sessionStorage.getItem("currentQuestion");
      if (storedQuestion) {
        currentQuestion = JSON.parse(storedQuestion);
        updateQuestionDisplay(currentQuestion);
      } else {
        getNewQuestion();
      }
    }
  });

  const challengeBtn = document.getElementById("submitChallengeResponse");

  // Bind the challenge submission event listener only once.
  challengeBtn.addEventListener("click", async () => {
    const startTime = Date.now();
    const challengeResponseInput = document.getElementById(
      "challengeResponseInput"
    );
    const challengeErrorMessage = document.getElementById(
      "challengeErrorMessage"
    );

    // Get the challenge XP info element early to avoid reference errors
    let challengeXpInfo = document.getElementById("challengeXpInfo");

    // Determine the current input mode (voice or text)
    const inputMode = window.challengeInputMode || "text";
    let challengeResponse;
    let voice_answer;

    if (inputMode === "voice") {
      voice_answer = document
        .getElementById("challengeVoiceTranscript")
        .value.trim();
      // For voice input, use a placeholder for challenge_response
      // The actual voice content will be sent in voice_answer
      challengeResponse = voice_answer.substring(0, 100) + "..."; // Just a placeholder
    } else {
      challengeResponse = document
        .getElementById("challengeResponseInput")
        .value.trim();
    }

    if (
      (!challengeResponse && inputMode === "text") ||
      (!voice_answer && inputMode === "voice")
    ) {
      challengeErrorMessage.textContent =
        "Please provide a response to the challenge.";
      return;
    }

    // Add character limit validation
    if (
      (inputMode === "text" &&
        challengeResponse.length > CHAR_LIMITS.CHALLENGE) ||
      (inputMode === "voice" &&
        voice_answer &&
        voice_answer.length > CHAR_LIMITS.VOICE)
    ) {
      challengeErrorMessage.textContent = `Please ensure your response is ${
        inputMode === "voice" ? CHAR_LIMITS.VOICE : CHAR_LIMITS.CHALLENGE
      } characters or less.`;
      return;
    }

    const answerId = sessionStorage.getItem("lastAnswerId");
    if (!answerId) {
      challengeErrorMessage.textContent = "No associated answer found.";
      return;
    }

    challengeBtn.innerHTML = `${
      translations.challenge.analyzing || "Analyzing..."
    } <span class="spinner"></span>`;
    challengeBtn.disabled = true;
    challengeErrorMessage.textContent = "";

    try {
      const payload = {
        answer_id: answerId,
        challenge_response: challengeResponse,
        input_mode: inputMode,
      };

      // Include voice_answer in the payload when using voice input
      if (inputMode === "voice" && voice_answer) {
        payload.voice_answer = voice_answer;
      }

      const response = await fetch("/submit_challenge_response", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const elapsed = Date.now() - startTime;
        if (elapsed < TIMING.EVALUATION_DELAY) {
          await new Promise((resolve) =>
            setTimeout(resolve, TIMING.EVALUATION_DELAY - elapsed)
          );
        }
      }

      const data = await response.json();

      if (!response.ok) {
        challengeErrorMessage.innerHTML =
          data.error || ERROR_MESSAGES.UNEXPECTED_ERROR;
        challengeBtn.innerHTML = "Submit";
        challengeBtn.disabled = false;
        return;
      }

      // Update only the global (header) XP/level indicator
      updateLocalXpIndicator(data.current_xp, data.level_info);

      // Update challenge evaluation feedback.
      const challengeEvalDiv = document.getElementById(
        "challengeEvaluationResults"
      );

      if (!challengeEvalDiv) {
        // Create the div if it doesn't exist
        const newChallengeEvalDiv = document.createElement("div");
        newChallengeEvalDiv.id = "challengeEvaluationResults";
        newChallengeEvalDiv.className = "mt-8 bg-white p-8 fade-in";
        newChallengeEvalDiv.style.display = "block";

        // Create the structure
        newChallengeEvalDiv.innerHTML = `
          <h2 class="text-2xl font-bold mb-6" data-i18n="evaluation.title">
            Evaluation
          </h2>
          <div id="challengeOverallEvaluation" class="mb-6"></div>
          <div id="challengeScores" class="grid gap-4 mb-8">
            <div class="score-item">
              <span data-i18n="evaluation.scores.relevance">Relevance</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.logic">Logical Structure</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.clarity">Clarity</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.depth">Depth</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.objectivity">Objectivity</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.creativity">Creativity</span>
            </div>
          </div>
          <div id="challengeXpInfo" class="mt-4 text-center profile-xp"></div>
        `;

        // Append to the challenge section
        const challengeSection = document.getElementById("challengeSection");
        if (challengeSection) {
          challengeSection.appendChild(newChallengeEvalDiv);
          // Update our reference to the newly created div
          challengeEvalDiv = newChallengeEvalDiv;
        } else {
          console.error(
            "Challenge section not found, cannot append evaluation div"
          );
          return; // Exit early if we can't create the evaluation div
        }
      } else if (!document.getElementById("challengeOverallEvaluation")) {
        // If the div exists but doesn't have the required structure, recreate it
        // Clear the existing content of challengeEvalDiv
        challengeEvalDiv.innerHTML = `
          <h2 class="text-2xl font-bold mb-6" data-i18n="evaluation.title">
            Evaluation
          </h2>
          <div id="challengeOverallEvaluation" class="mb-6"></div>
          <div id="challengeScores" class="grid gap-4 mb-8">
            <div class="score-item">
              <span data-i18n="evaluation.scores.relevance">Relevance</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.logic">Logical Structure</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.clarity">Clarity</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.depth">Depth</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.objectivity">Objectivity</span>
            </div>
            <div class="score-item">
              <span data-i18n="evaluation.scores.creativity">Creativity</span>
            </div>
          </div>
          <div id="challengeXpInfo" class="mt-4 text-center profile-xp"></div>
        `;
      }

      // Safely get values with fallbacks
      const totalScore =
        data.evaluation && data.evaluation.total_score !== undefined
          ? data.evaluation.total_score
          : data.evaluation && data.evaluation.scores
          ? Object.values(data.evaluation.scores).reduce(
              (sum, val) => sum + val,
              0
            ) / Object.values(data.evaluation.scores).length
          : 0;

      const totalScorePercent = totalScore * 10;
      const totalScoreColor = scoreToColor(totalScore);
      const overallFeedback =
        data.evaluation && data.evaluation.overall_feedback
          ? data.evaluation.overall_feedback
          : "Evaluation complete.";

      // Update the overall evaluation section
      const challengeOverallEvaluation = document.getElementById(
        "challengeOverallEvaluation"
      );

      if (challengeOverallEvaluation) {
        challengeOverallEvaluation.innerHTML = `
          <p class="text-l font-bold mb-2">
            ${translations.evaluation.overall}:
            <span id="challengeTotalScoreValue" style="color: ${totalScoreColor};">${totalScore.toFixed(
          1
        )}/10</span>
          </p>
          <div class="w-full bg-gray-200 rounded-full h-2.5 mb-2">
            <div id="challengeTotalScoreBar" class="rounded-full total-progress-bar"
                 style="width: 0%; background-color: ${totalScoreColor}; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
          </div>
          <p id="challengeOverallFeedback" class="text-md">${overallFeedback}</p>
        `;

        // Animate the challenge overall score bar after a short delay
        setTimeout(() => {
          const challengeTotalScoreBar = document.getElementById(
            "challengeTotalScoreBar"
          );
          if (challengeTotalScoreBar) {
            challengeTotalScoreBar.style.width = `${totalScorePercent}%`;
          }
        }, 100);
      }

      // Update the scores section
      const challengeScores = document.getElementById("challengeScores");

      if (challengeScores && data.evaluation && data.evaluation.scores) {
        // Clear existing content first
        challengeScores.innerHTML = "";

        // Create score items for each evaluation category
        EVALUATION_CATEGORIES.forEach((category) => {
          const score = data.evaluation.scores[category] || 0;
          const scorePercent = score * 10;
          const scoreColor = scoreToColor(score);
          const feedback = data.evaluation.feedback[category] || "";

          // Get translation key from mapping
          const translationKey = EVALUATION_TRANSLATION_MAPPING[category];

          // Create the score item element
          const scoreItem = document.createElement("div");
          scoreItem.className = "mb-4 score-item";
          scoreItem.innerHTML = `
            <div class="flex justify-between items-center">
              <span data-i18n="evaluation.scores.${translationKey}">${
            translations.evaluation.scores[translationKey] || category
          }</span>
              <span class="font-medium score-value" style="color: ${scoreColor};">1/10</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
              <div class="rounded-full h-2 score-bar"
                   style="width: 0%; background-color: ${scoreColor}; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
            </div>
            <p class="text-sm text-gray-500 mt-1">${feedback}</p>
          `;

          // Add to the scores container
          challengeScores.appendChild(scoreItem);
        });

        // Create an observer for score animations
        const challengeScoreAnimationObserver = new IntersectionObserver(
          (entries) => {
            if (entries[0].isIntersecting) {
              const scoreItems =
                challengeScores.querySelectorAll(".score-item");

              // Animate score bars with delay between each
              scoreItems.forEach((item, index) => {
                setTimeout(() => {
                  const categoryText = item.querySelector("span").textContent;
                  const category = Object.keys(
                    EVALUATION_TRANSLATION_MAPPING
                  ).find(
                    (key) =>
                      translations.evaluation.scores[
                        EVALUATION_TRANSLATION_MAPPING[key]
                      ] === categoryText
                  );

                  if (!category) return;

                  const score = data.evaluation.scores[category] || 0;
                  const scorePercent = score * 10;
                  const scoreBar = item.querySelector(".score-bar");
                  const scoreValue = item.querySelector(".score-value");

                  // Animate the score bar width
                  if (scoreBar) {
                    scoreBar.style.width = `${scorePercent}%`;
                  }

                  // Animate the score value with counting effect
                  if (scoreValue) {
                    let current = 1;
                    const targetScore = Math.round(score);
                    const duration = 800; // ms
                    const startTime = performance.now();

                    const animateScore = (timestamp) => {
                      const elapsed = timestamp - startTime;
                      const progress = Math.min(elapsed / duration, 1);

                      // Calculate current value (1 to target)
                      current = 1 + Math.floor(progress * (targetScore - 1));

                      // Update the score text
                      scoreValue.textContent = `${current}/10`;

                      // Continue animation until complete
                      if (progress < 1) {
                        requestAnimationFrame(animateScore);
                      } else {
                        // Ensure final value is exact
                        scoreValue.textContent = `${targetScore}/10`;
                      }
                    };

                    requestAnimationFrame(animateScore);
                  }
                }, index * 100); // 100ms delay between each animation
              });

              // Disconnect observer after triggering animations
              challengeScoreAnimationObserver.disconnect();
            }
          },
          { threshold: 0.2 }
        );

        // Start observing the scores section
        challengeScoreAnimationObserver.observe(challengeScores);
      }

      // Update XP and level info
      // Get the challengeXpInfo element - if it doesn't exist, we need to create it
      let challengeXpInfo = document.getElementById("challengeXpInfo");

      if (!challengeXpInfo && challengeEvalDiv) {
        challengeXpInfo = document.createElement("div");
        challengeXpInfo.id = "challengeXpInfo";
        challengeXpInfo.className = "mt-4 text-center profile-xp";
        challengeEvalDiv.appendChild(challengeXpInfo);
      }

      if (challengeXpInfo) {
        challengeXpInfo.classList.remove("hidden");
        challengeXpInfo.style.display = "block";
        challengeXpInfo.className = "mt-4 text-center profile-xp"; // Ensure it has the same classes as the main XP info
      } else {
        console.error(
          "Challenge XP Info element not found after creation attempt"
        );
      }

      // Check for challenge XP using the correct property name
      if (
        challengeXpInfo &&
        (data.challenge_xp_earned !== undefined || data.xp_gained !== undefined)
      ) {
        const xpGained =
          data.challenge_xp_earned !== undefined
            ? data.challenge_xp_earned
            : data.xp_gained;
        // Debug logs removed
        const current_user_username =
          document.getElementById("usernameElem")?.textContent.trim() ||
          "Anonymous";

        // Clear any existing content
        challengeXpInfo.innerHTML = "";

        // Create the XP info structure
        challengeXpInfo.innerHTML = `
          ${
            data.relevance_too_low
              ? `
            <p id="challengeXpMessage" class="text-sm text-red-600 text-center mb-4" style="text-align: center; padding-left: 0">
              ${translations.evaluation.relevanceWarning}
            </p>
          `
              : ""
          }
          ${
            data.leveled_up
              ? `
            <p id="challengeLevelUpMessage" class="text-green-600 font-bold text-center" data-i18n="evaluation.levelUp" style="text-align: center; padding-left: 0">
              ${translations.evaluation.levelUp || "Level Up!"}
            </p>
          `
              : ""
          }
          <p>
            <span data-i18n="evaluation.experiencePoints">
              Experience Points Gained:
            </span>
            <span id="challengeXpGained"><strong class="xp-gained-pop">${
              data.relevance_too_low ? "0" : data.challenge_xp_earned || "0"
            }</strong></span>
          </p>

          <!-- Two-column layout for level info -->
          <div class="flex items-center justify-center">
            <!-- Left column: level image with number indicator -->
            <div class="level-image-wrapper">
              <div class="level-indicator challenge-xp">
                <div class="level-image-container">
                  <img src="${
                    data.leveled_up
                      ? data.level_info.previous_level_image // Always use previous level image when leveling up
                      : data.level_info.level_image
                  }" class="level-image" alt="Level ${
          data.leveled_up ? data.previous_level : data.level_info.level_number
        }" />
                </div>
              </div>
              <div class="level-number-indicator">${
                data.leveled_up
                  ? data.previous_level
                  : data.level_info.level_number
              }</div>
            </div>
            <!-- Right column: username, level name, XP bar and progress info -->
            <div class="flex flex-col text-left">
              <p class="text-sm text-gray-600 mb-0 move-down">
                ${current_user_username}
              </p>
              <p class="text-base mb-0 move-down" id="challengeCurrentLevel">
                <strong>${
                  data.leveled_up
                    ? `Level ${data.previous_level}`
                    : data.level_info.display_name
                }</strong>
              </p>
              <div class="xp-bar-wrapper mt-2">
                <div class="xp-bar-container">
                  <div class="xp-progress-bar bg-green-500 h-full transition-all duration-500" style="width: ${
                    data.level_info.progress_percent
                  }%;"></div>
                </div>
                <p class="text-sm mt-1">
                  <span data-i18n="evaluation.progress">Progress:</span>
                  <span id="challengeXpProgressText">${
                    data.level_info.xp_into_level
                  } / ${data.level_info.xp_needed}</span> XP
                </p>
                <p class="text-sm mt-1">
                  <span data-i18n="evaluation.nextLevel">Next Level:</span>
                  <span id="challengeNextLevel">${
                    data.level_info.next_level
                  }</span>
                </p>
              </div>
            </div>
          </div>

          <!-- Achievements Section -->
          <div class="mt-8 text-center">
            <h5 class="text-lg font-bold mb-4">
              <span data-i18n="profile.achievements">Achievements</span>
              <span class="text-gray-600 font-normal achievements-count">
                (${data.achievements ? data.achievements.length : 0}/${
          all_achievements.length
        })
              </span>
            </h5>
            <div class="flex justify-center w-full">
              <div class="inline-grid grid-cols-10 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-[repeat(15,minmax(0,40px))] justify-center justify-items-center gap-x-3 gap-y-3 mb-8 max-w-4xl mx-auto px-4">
                ${all_achievements
                  .map((achievement) => {
                    const isEarned =
                      data.achievements &&
                      data.achievements.some(
                        (earned) => earned.id === achievement.id
                      );
                    return `
                    <div class="group relative">
                      <div data-achievement-id="${achievement.id}"
                           class="achievement-icon w-10 h-10 flex items-center justify-center rounded-lg border-2 ${
                             isEarned ? "border-gray-600" : "border-gray-200"
                           } bg-white ${
                      isEarned ? "" : "opacity-40"
                    } transition-all duration-300 hover:border-gray-400">
                        <img src="/static/img/trophy.webp" class="w-6 h-6 ${
                          isEarned ? "" : "opacity-30"
                        }" alt="Trophy" />
                      </div>
                      <!-- Tooltip -->
                      <div class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 absolute z-10 w-48 -translate-x-1/4 translate-y-2 pointer-events-none bg-gray-800 text-white text-sm rounded-lg p-2 shadow-lg">
                        <p class="font-bold mb-1">${
                          translations.profile.achievementData[achievement.id]
                            .name
                        }</p>
                        <p class="text-gray-200 text-xs">${
                          translations.profile.achievementData[achievement.id]
                            .description
                        }</p>
                      </div>
                    </div>
                  `;
                  })
                  .join("")}
              </div>
            </div>
          </div>

          <!-- Profile and Login Messages -->
          <div class="mt-2 text-center">
            <p class="text-sm text-center">
              <span data-i18n="evaluation.checkProfile">Check your</span>
              <a href="/profile" class="inline-flex items-baseline text-gray-800 underline hover:text-gray-600">
                <img src="https://img.icons8.com/windows/32/gender-neutral-user.png" alt="Profile" class="w-4 h-4 mr-1 relative top-0.5" />
                <span data-i18n="evaluation.profilePage">Profile Page</span>
              </a>
              <span data-i18n="evaluation.reviewProgress">to review answered questions and track your progress.</span>
            </p>
          </div>

          <!-- Authentication Warning -->
          ${
            !current_user_authenticated
              ? `
          <div class="mt-4 mb-4 max-w-full md:w-max mx-auto bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded text-sm">
            <span>${translations.evaluation.notLoggedIn}</span>
            <a href="#" onclick="showAuthModal()" class="text-gray-800 underline hover:text-gray-600">
              <span>${translations.evaluation.here}</span></a><span>${translations.evaluation.loginSuffix}</span>
          </div>
          `
              : ""
          }
        `;
      }

      // Update the challenge XP info section
      // Use the existing challengeXpInfo variable instead of redeclaring it
      if (challengeXpInfo) {
        // Update XP gained
        const challengeXpGained = document.getElementById("challengeXpGained");
        if (challengeXpGained) {
          const xpValue =
            data.challenge_xp_earned !== undefined
              ? data.challenge_xp_earned
              : data.xp_gained !== undefined
              ? data.xp_gained
              : 0;
          challengeXpGained.innerHTML = `<strong>${xpValue}</strong>`;
        }

        // Update level info
        const challengeCurrentLevel = document.getElementById(
          "challengeCurrentLevel"
        );
        if (
          challengeCurrentLevel &&
          data.level_info &&
          data.level_info.display_name
        ) {
          challengeCurrentLevel.innerHTML = `<strong>${data.level_info.display_name}</strong>`;
        }

        // Update XP progress text
        const challengeXpProgressText = document.getElementById(
          "challengeXpProgressText"
        );
        if (challengeXpProgressText && data.level_info) {
          const xpIntoLevel =
            data.level_info.xp_into_level !== undefined
              ? data.level_info.xp_into_level
              : 0;
          const xpNeeded =
            data.level_info.xp_needed !== undefined
              ? data.level_info.xp_needed
              : 100;
          challengeXpProgressText.textContent = `${xpIntoLevel} / ${xpNeeded}`;
        }

        // Update next level text
        const challengeNextLevel =
          document.getElementById("challengeNextLevel");
        if (
          challengeNextLevel &&
          data.level_info &&
          data.level_info.next_level
        ) {
          challengeNextLevel.textContent = data.level_info.next_level;
        }

        // Immediately set the progress bar width to ensure it's visible
        const xpProgressBar = challengeXpInfo.querySelector(".xp-progress-bar");
        if (xpProgressBar) {
          // Start with 0% width for animation
          xpProgressBar.style.width = "0%";
        }

        // Create intersection observer for challenge XP animations
        const challengeXpAnimationObserver = new IntersectionObserver(
          (entries) => {
            if (entries[0].isIntersecting) {
              const isChallenge = true; // This is always true in the challenge XP context

              // Add a small delay to ensure the element is fully visible
              setTimeout(() => {
                const challengeXpInfo = entries[0].target;

                // Get the progress bar element
                const xpProgressBar =
                  challengeXpInfo.querySelector(".xp-progress-bar");

                if (xpProgressBar) {
                  // Force reflow to ensure animation works
                  void xpProgressBar.offsetWidth;

                  // Add transition
                  xpProgressBar.style.transition =
                    "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";

                  // Animate if there's xp gained
                  if (data.challenge_xp_earned > 0) {
                    // Calculate target width before animations
                    const targetWidth = `${data.level_info.progress_percent}%`;

                    // If leveled up, handle level image transition
                    if (data.leveled_up) {
                      // Get the level indicator container and image immediately
                      const levelImageContainer = challengeXpInfo.querySelector(
                        ".level-image-container"
                      );
                      const levelImage = levelImageContainer
                        ? levelImageContainer.querySelector("img")
                        : null;
                      const oldImageSrc = data.level_info.previous_level_image;
                      const newImageSrc = data.level_info.level_image;

                      // Set the old image immediately before any animations start
                      if (levelImage && oldImageSrc && newImageSrc) {
                        // Ensure we're starting with the old image
                        levelImage.src = oldImageSrc;
                        levelImage.alt = `Level ${data.previous_level}`;
                        // Force a reflow to ensure the old image is rendered
                        void levelImageContainer.offsetWidth;
                      }

                      // First animate to 100%
                      xpProgressBar.style.transition =
                        "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
                      xpProgressBar.style.width = "100%";

                      // After reaching 100%, trigger level transition with a small delay
                      // to ensure the old image is fully loaded
                      setTimeout(function () {
                        if (levelImageContainer && levelImage) {
                          // Get the level text element for challenge
                          const challengeLevelTextElement =
                            document.getElementById("challengeCurrentLevel");

                          // Store the original level text
                          const originalChallengeLevelText =
                            challengeLevelTextElement
                              ? challengeLevelTextElement.innerHTML
                              : "";

                          if (!oldImageSrc || !newImageSrc) {
                            console.error(
                              "Missing level image sources for animation",
                              {
                                oldImageSrc,
                                newImageSrc,
                                data,
                              }
                            );
                            return;
                          }

                          // Create a function to start the animation only after ensuring the old image is loaded
                          const startLevelAnimation = () => {
                            // Double check we're still showing the old image
                            // This is critical to ensure we start with the old image
                            if (levelImage.src !== oldImageSrc) {
                              levelImage.src = oldImageSrc;
                              levelImage.alt = `Level ${data.previous_level}`;
                              // Force a reflow to ensure the old image is rendered
                              void levelImageContainer.offsetWidth;
                            }

                            // Start glow effect and rotation AFTER ensuring old image is shown
                            levelImageContainer.classList.add(
                              "level-up-glow",
                              "challenge-glow",
                              "level-image-transition"
                            );

                            // Start level text transition if it exists
                            if (challengeLevelTextElement) {
                              challengeLevelTextElement.innerHTML =
                                originalChallengeLevelText;
                              challengeLevelTextElement.classList.add(
                                "level-text-transition"
                              );

                              // Update the level text halfway through the animation
                              setTimeout(() => {
                                challengeLevelTextElement.innerHTML = `<strong>${data.level_info.display_name}</strong>`;
                              }, 600);

                              // Remove text animation class after completion
                              setTimeout(() => {
                                challengeLevelTextElement.classList.remove(
                                  "level-text-transition"
                                );
                              }, 1200);
                            }

                            // Update the image halfway through the animation
                            setTimeout(() => {
                              levelImage.src = newImageSrc;
                              levelImage.alt = `Level ${data.current_level}`;
                              void levelImageContainer.offsetWidth;
                            }, 600);

                            // Clean up animations and handle progress bar
                            setTimeout(() => {
                              // Remove all animation classes
                              levelImageContainer.classList.remove(
                                "level-up-glow",
                                "challenge-glow",
                                "level-image-transition"
                              );

                              // Reset and animate progress bar to new position
                              xpProgressBar.style.transition = "none";
                              xpProgressBar.style.width = "0%";
                              void xpProgressBar.offsetWidth;
                              xpProgressBar.style.transition =
                                "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
                              xpProgressBar.style.width = targetWidth;

                              // Animate the XP progress text
                              const challengeXpProgressTextElement =
                                document.getElementById(
                                  "challengeXpProgressText"
                                );
                              if (challengeXpProgressTextElement) {
                                challengeXpProgressTextElement.classList.add(
                                  "count-up-animation"
                                );
                                const startXp = 0;
                                const endXp = parseInt(
                                  data.level_info.xp_into_level
                                );
                                const xpNeeded = data.level_info.xp_needed;
                                const duration = 800;
                                const startTime = performance.now();

                                const animateChallengeXpNumbers = (
                                  timestamp
                                ) => {
                                  const elapsed = timestamp - startTime;
                                  const progress = Math.min(
                                    elapsed / duration,
                                    1
                                  );
                                  const currentXp = Math.floor(
                                    startXp + (endXp - startXp) * progress
                                  );
                                  challengeXpProgressTextElement.textContent = `${currentXp} / ${xpNeeded}`;

                                  if (progress < 1) {
                                    requestAnimationFrame(
                                      animateChallengeXpNumbers
                                    );
                                  } else {
                                    setTimeout(() => {
                                      challengeXpProgressTextElement.classList.remove(
                                        "count-up-animation"
                                      );
                                    }, 200);
                                  }
                                };

                                requestAnimationFrame(
                                  animateChallengeXpNumbers
                                );
                              }
                            }, 1200);
                          };

                          // Ensure the old image is loaded before starting the animation
                          if (levelImage.complete) {
                            startLevelAnimation();
                          } else {
                            // If the image is not yet loaded, wait for it
                            levelImage.onload = startLevelAnimation;
                            // Set a fallback in case the image fails to load
                            setTimeout(startLevelAnimation, 100);
                          }
                        }
                      }, 200); // Increased delay to ensure everything is ready
                    } else {
                      // No level up, just animate progress bar
                      xpProgressBar.style.width = targetWidth;
                    }
                  }
                }
              }, 100);
              // Disconnect the observer after triggering the animation
              challengeXpAnimationObserver.disconnect();
            }
          },
          { threshold: 0.5 }
        );

        // Observe the challenge XP info element
        if (challengeXpInfo) {
          challengeXpAnimationObserver.observe(challengeXpInfo);
        }
      }

      // Show the challenge evaluation results
      if (challengeEvalDiv) {
        challengeEvalDiv.classList.remove("hidden");
        challengeEvalDiv.style.display = "block";
        challengeEvalDiv.classList.add("fade-in");

        // Ensure it has the same styling as the main evaluation section
        challengeEvalDiv.className = "mt-8 bg-white p-8 fade-in";

        localScrollToChallengeEvaluation();
      } else {
        console.error("Challenge evaluation div not found");
      }

      challengeBtn.innerHTML = "Submit";
      challengeBtn.disabled = false;

      // Show achievement notifications if any were awarded
      if (data.achievements) {
        // Update achievements display
        await updateAchievementsDisplay(data.achievements);
      } else {
        // Even if no new achievements, refresh the display to ensure consistency
        await refreshAchievementDisplay();
      }

      // Only proceed if we have the challenge XP info element
      if (challengeXpInfo) {
        const challengeXpGainedElement =
          document.getElementById("challengeXpGained");
        const challengeXpMessageElement =
          document.getElementById("challengeXpMessage");
        const challengeLevelUpMessageElement = document.getElementById(
          "challengeLevelUpMessage"
        );
        const challengeCurrentLevelElement = document.getElementById(
          "challengeCurrentLevel"
        );
        const challengeXpProgressTextElement = document.getElementById(
          "challengeXpProgressText"
        );
        const challengeXpProgressBarElement =
          challengeXpInfo.querySelector(".xp-progress-bar");
        const challengeNextLevelElement =
          document.getElementById("challengeNextLevel");

        // Store old level text for level up animation
        let oldChallengeLevelText = "";
        if (data.leveled_up && challengeCurrentLevelElement) {
          // Get the current level number from level_info
          const previousLevelNumber = data.level_info.level_number - 1;
          // Use the level number to construct the display name
          oldChallengeLevelText = `<strong>Level ${previousLevelNumber} (${
            data.level_info.previous_level_label || "Curious Mind"
          })</strong>`;
          // Set the initial text to show the old level
          challengeCurrentLevelElement.innerHTML = oldChallengeLevelText;
        }

        // Use the shared function for XP animations
        handleLocalXpAnimations(data, {
          xpInfoElement: challengeXpInfo,
          xpGainedElement: challengeXpGainedElement,
          xpMessageElement: challengeXpMessageElement,
          levelUpMessageElement: challengeLevelUpMessageElement,
          currentLevelElement: challengeCurrentLevelElement,
          xpProgressTextElement: challengeXpProgressTextElement,
          xpProgressBarElement: challengeXpProgressBarElement,
          nextLevelElement: challengeNextLevelElement,
          oldLevelText: oldChallengeLevelText,
          isChallenge: true,
          clear_content: true,
        });

        // Show the challenge evaluation results
        showEvaluationSection(challengeEvalDiv, true);

        // Code moved to our previous edit where we show the challenge evaluation results
      }
    } catch (error) {
      console.error("Error submitting challenge response:", error);
      if (challengeErrorMessage) {
        challengeErrorMessage.textContent =
          (translations &&
            translations.challenge &&
            translations.challenge.errors &&
            translations.challenge.errors.submissionError) ||
          "Error submitting your response. Please try again.";
      }
      if (challengeBtn) {
        challengeBtn.innerHTML = "Submit";
        challengeBtn.disabled = false;
      }
    }
  });

  // Challenge voice mode tab handling
  const challengeTextModeTab = document.getElementById("challengeTextModeTab");
  const challengeVoiceModeTab = document.getElementById(
    "challengeVoiceModeTab"
  );
  const challengeTextInputSection = document.getElementById(
    "challengeTextInputSection"
  );
  const challengeVoiceInputSection = document.getElementById(
    "challengeVoiceInputSection"
  );

  // Initialize challenge input mode
  window.challengeInputMode = "text";

  if (challengeTextModeTab && challengeVoiceModeTab) {
    challengeTextModeTab.addEventListener("click", () => {
      challengeTextModeTab.classList.add("active", "text-gray-800");
      challengeTextModeTab.classList.remove("text-gray-500");
      challengeVoiceModeTab.classList.remove("active", "text-gray-800");
      challengeVoiceModeTab.classList.add("text-gray-500");
      challengeTextInputSection.style.display = "block";
      challengeVoiceInputSection.style.display = "none";
      window.challengeInputMode = "text";
    });

    challengeVoiceModeTab.addEventListener("click", () => {
      challengeVoiceModeTab.classList.add("active", "text-gray-800");
      challengeVoiceModeTab.classList.remove("text-gray-500");
      challengeTextModeTab.classList.remove("active", "text-gray-800");
      challengeTextModeTab.classList.add("text-gray-500");
      challengeVoiceInputSection.style.display = "block";
      challengeTextInputSection.style.display = "none";
      window.challengeInputMode = "voice";
    });
  }

  // Challenge voice recording functionality
  const challengeRecordButton = document.getElementById(
    "challengeRecordButton"
  );
  const challengeRecordingTimer = document.getElementById(
    "challengeRecordingTimer"
  );
  const challengeTimerDisplay = document.getElementById(
    "challengeTimerDisplay"
  );
  const challengeRecordingStatus = document.getElementById(
    "challengeRecordingStatus"
  );
  // Get the current XP progress state for challenge section
  const challengeXpProgressBar = document.querySelector(
    ".challenge-xp .xp-progress-bar"
  );
  window.currentChallengeProgressWidth = 0;
  if (challengeXpProgressBar) {
    window.currentChallengeProgressWidth =
      parseFloat(challengeXpProgressBar.style.width) || 0;
  }
  // Reuse existing variables instead of redeclaring
  challengeVoiceTranscript = document.getElementById(
    "challengeVoiceTranscript"
  );
  challengeVoiceCount = document.getElementById("challengeVoiceCount");

  let challengeMediaRecorder;
  let challengeAudioChunks = [];
  let challengeRecordingTimeout;
  let isChallengeRecording = false;
  let challengeTimerInterval;
  let challengeStartTime;

  // Function to format max recording time as MM:SS for challenge recording
  function formatMaxRecordingTime() {
    const ms = VOICE_LIMITS.MAX_RECORDING_TIME;
    return formatChallengeTime(ms);
  }

  // Function to format time as MM:SS for challenge recording
  function formatChallengeTime(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  }

  // Function to update challenge timer display
  function updateChallengeTimer() {
    const elapsed = Date.now() - challengeStartTime;
    challengeTimerDisplay.textContent = formatChallengeTime(elapsed);
  }

  // Function to toggle challenge recording state
  async function toggleChallengeRecording() {
    if (!isChallengeRecording) {
      // Check voice limits before starting recording
      try {
        const response = await fetch("/check_voice_limits");
        const data = await response.json();

        if (data.limit_reached) {
          // Display error message if limit is reached
          const errorElement = document.getElementById("challengeErrorMessage");
          if (errorElement) {
            errorElement.innerHTML = data.error;
          }
          challengeRecordingStatus.textContent =
            translations?.main?.voiceInput?.status?.limitReached ||
            "Recording limit reached.";
          return;
        }

        // If no limits reached, start recording
        startChallengeRecording();
      } catch (error) {
        console.error("Error checking voice limits:", error);
        // If there's an error checking limits, allow recording anyway
        startChallengeRecording();
      }
    } else {
      stopChallengeRecording();
    }
  }

  // Challenge recording functions
  async function startChallengeRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      challengeMediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
        bitsPerSecond: 128000,
      });

      isChallengeRecording = true;
      challengeRecordButton.classList.add(
        "bg-red-50",
        "border-red-500",
        "text-red-500"
      );
      challengeRecordButton.innerHTML = `
        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      `;

      challengeRecordingStatus.textContent =
        translations?.main?.voiceInput?.status?.recording || "Recording...";
      challengeRecordingTimer.classList.remove("hidden");
      challengeStartTime = Date.now();
      challengeTimerInterval = setInterval(updateChallengeTimer, 1000);

      challengeAudioChunks = [];
      challengeMediaRecorder.addEventListener("dataavailable", (event) => {
        challengeAudioChunks.push(event.data);
      });

      challengeMediaRecorder.addEventListener("stop", async () => {
        // Immediately update the UI to reflect that recording has stopped.
        stopChallengeRecording();

        // Now update the status to indicate that transcription is starting.
        challengeRecordingStatus.innerHTML =
          (translations?.main?.voiceInput?.status?.transcribing ||
            "Transcribing...") + '<span class="spinner"></span>';

        const audioBlob = new Blob(challengeAudioChunks, {
          type: "audio/webm",
        });
        const formData = new FormData();
        formData.append("file", audioBlob, "recording");

        // Get the current language from local storage (or fallback to "en")
        const language = localStorage.getItem("language") || "en";

        // Get the current question from session storage
        const currentQuestion = JSON.parse(
          sessionStorage.getItem("currentQuestion")
        );
        const questionText = currentQuestion ? currentQuestion.description : "";

        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes

          const response = await fetch(
            `/transcribe_voice?lang=${language}&question=${encodeURIComponent(
              questionText
            )}`,
            {
              method: "POST",
              body: formData,
              signal: controller.signal,
            }
          );

          clearTimeout(timeoutId);

          // Handle different response status codes
          if (response.status === 204) {
            // No text detected (204 No Content)
            challengeRecordingStatus.innerHTML =
              translations?.main?.voiceInput?.status?.noTextDetected ||
              "Could not identify any text from the recording. Please try again.";
            challengeRecordButton.disabled = false;
            return;
          } else if (response.status === 500) {
            // Server error (500 Internal Server Error)
            challengeRecordingStatus.innerHTML =
              translations?.main?.voiceInput?.status?.transcriptionError ||
              "Error during transcription. Please try again later.";
            challengeRecordButton.disabled = false;
            return;
          }

          const data = await response.json();

          if (!response.ok) {
            challengeRecordingStatus.innerHTML =
              data.error ||
              translations?.main?.voiceInput?.status?.transcriptionError ||
              "Error during transcription.";
            challengeRecordButton.disabled = false;
            return;
          }

          // Show post-processing status
          challengeRecordingStatus.innerHTML =
            (translations?.main?.voiceInput?.status?.postProcessing ||
              "Post-processing...") + '<span class="spinner"></span>';

          let transcript = data.transcript || "";

          // Check if the transcript is empty or only contains whitespace
          if (!transcript.trim()) {
            challengeRecordingStatus.innerHTML =
              translations?.main?.voiceInput?.status?.noTextDetected ||
              "Could not identify any text from the recording. Please try again.";
            challengeRecordButton.disabled = false;
            return;
          }

          // Update status based on whether the transcription was improved
          challengeRecordingStatus.innerHTML = data.was_improved
            ? translations?.main?.voiceInput?.status?.transcriptionImproved ||
              "Transcription complete and enhanced. You may edit the text."
            : translations?.main?.voiceInput?.status?.transcriptionComplete ||
              "Transcription complete. You may edit the text.";

          challengeVoiceTranscript.value = transcript;
          challengeVoiceCount.textContent = (
            CHAR_LIMITS.VOICE - transcript.length
          ).toString();

          // If the transcript exceeds the character limit, highlight it.
          if (transcript.length > CHAR_LIMITS.VOICE) {
            challengeVoiceTranscript.classList.add("border-red-500");
            challengeRecordingStatus.innerHTML =
              translations?.main?.voiceInput?.status?.tooLong ||
              "Transcription exceeds character limit. Please edit before submitting.";
          } else {
            challengeVoiceTranscript.classList.remove("border-red-500");
          }
        } catch (error) {
          if (error.name === "AbortError") {
            challengeRecordingStatus.innerHTML =
              translations?.main?.voiceInput?.status?.transcriptionTimeout ||
              "Transcription timed out. Please try a shorter recording.";
          } else {
            challengeRecordingStatus.innerHTML =
              translations?.main?.voiceInput?.status?.transcriptionError ||
              "Error during transcription.";
          }
          console.error(error);
          challengeRecordButton.disabled = false;
        }
        // Re-enable the record button once transcription is complete.
        challengeRecordButton.disabled = false;
      });

      challengeMediaRecorder.start();
      // Automatically stop recording after MAX_RECORDING_TIME
      challengeRecordingTimeout = setTimeout(() => {
        if (
          challengeMediaRecorder &&
          challengeMediaRecorder.state !== "inactive"
        ) {
          challengeMediaRecorder.stop();
        }
      }, VOICE_LIMITS.MAX_RECORDING_TIME);

      // Update max recording time display
      document.getElementById("challengeMaxRecordingTime").textContent =
        formatMaxRecordingTime();
    } catch (error) {
      console.error("Error accessing microphone:", error);
      challengeRecordingStatus.innerHTML =
        translations?.main?.voiceInput?.status?.microphoneError ||
        "Error accessing microphone.";
    }
  }

  function stopChallengeRecording() {
    // If the recorder is still active, stop it.
    if (challengeMediaRecorder && challengeMediaRecorder.state !== "inactive") {
      challengeMediaRecorder.stop();
    }
    // Always perform the UI reset.
    isChallengeRecording = false;
    clearInterval(challengeTimerInterval);
    challengeRecordingTimer.classList.add("hidden");
    challengeRecordButton.classList.remove(
      "bg-red-50",
      "border-red-500",
      "text-red-500"
    );
    challengeRecordButton.innerHTML = `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
    </svg>`;
  }

  // Update remaining character count as user edits challenge voice transcript
  if (challengeVoiceTranscript) {
    challengeVoiceTranscript.addEventListener("input", () => {
      const remaining =
        CHAR_LIMITS.VOICE - challengeVoiceTranscript.value.length;
      challengeVoiceCount.textContent = remaining.toString();
      // Clear error message on input
      document.getElementById("challengeErrorMessage").textContent = "";
    });
  }

  // Add event listener to challenge record button
  if (challengeRecordButton) {
    challengeRecordButton.addEventListener("click", toggleChallengeRecording);
  }
});

// Update selectedCategories based on selected items and possibly re-roll the question
function updateSelectedCategories() {
  const categoryItems = document.querySelectorAll(".category-item");
  selectedCategories = Array.from(categoryItems)
    .filter((item) => item.classList.contains("selected"))
    .map((item) => item.dataset.value);

  // Persist the selection
  fetch("/update_categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ categories: selectedCategories }),
  }).catch((error) => console.error("Error saving categories:", error));

  if (
    currentQuestion &&
    !selectedCategories.includes(currentQuestion.category)
  ) {
    getNewQuestion(false).then(() => {
      document.getElementById("claimInput").value = "";
      document.getElementById("argumentInput").value = "";
      document.getElementById("counterargumentInput").value = "";
    });
  }
}

// Add new function to update UI based on saved preferences
function updateCategoryUI() {
  const categoryItems = document.querySelectorAll(".category-item");
  categoryItems.forEach((item) => {
    if (selectedCategories.includes(item.dataset.value)) {
      item.classList.add("selected");
      item.classList.add("bg-gray-800");
      item.classList.add("text-white");
      item.classList.remove("bg-white");
      item.classList.remove("text-black");
    } else {
      item.classList.remove("selected");
      item.classList.remove("bg-gray-800");
      item.classList.remove("text-white");
      item.classList.add("bg-white");
      item.classList.add("text-black");
    }
  });
}

// Question selection overlay handler
document
  .getElementById("selectQuestionButton")
  .addEventListener("click", () => {
    fetch("/get_all_questions")
      .then((response) => response.json())
      .then((questions) => {
        const questionList = document.getElementById("questionList");
        questionList.innerHTML = "";

        const filteredQuestions = questions.filter((q) =>
          selectedCategories.includes(q.category)
        );
        const groups = {};
        const categoryOrder = [];
        filteredQuestions.forEach((question) => {
          if (!groups[question.category]) {
            groups[question.category] = [];
            categoryOrder.push(question.category);
          }
          groups[question.category].push(question);
        });

        if (filteredQuestions.length === 0) {
          const noQuestionsItem = document.createElement("div");
          noQuestionsItem.className = "text-gray-600 py-2";
          noQuestionsItem.textContent =
            "No questions available for the selected categories.";
          questionList.appendChild(noQuestionsItem);
        } else {
          categoryOrder.forEach((category) => {
            const heading = document.createElement("h4");
            heading.className = "mt-4 mb-2 font-bold text-lg";
            // Translate the category name using the translations object.
            heading.textContent = translations.categories[category] || category;
            questionList.appendChild(heading);

            groups[category].forEach((question) => {
              const item = document.createElement("div");
              item.className =
                "question-item cursor-pointer p-2 border-b hover:bg-gray-100";
              item.textContent = question.description;
              item.dataset.id = question.id;
              item.addEventListener("click", () => {
                // Store the selected question
                currentQuestion = question;
                sessionStorage.setItem(
                  "currentQuestion",
                  JSON.stringify(question)
                );

                // Update the display
                updateQuestionDisplay(question);

                // Try to hide the overlay if it exists
                const overlay = document.getElementById(
                  "questionSelectionOverlay"
                );
                if (overlay) {
                  overlay.classList.add("hidden");
                }
              });
              questionList.appendChild(item);
            });
          });
        }
        document
          .getElementById("questionSelectionOverlay")
          .classList.remove("hidden");
      })
      .catch((error) => console.error("Error fetching questions:", error));
  });

document
  .getElementById("closeQuestionSelection")
  .addEventListener("click", () => {
    document.getElementById("questionSelectionOverlay").classList.add("hidden");
  });

document
  .getElementById("questionSelectionOverlay")
  .addEventListener("click", (e) => {
    if (e.target === document.getElementById("questionSelectionOverlay")) {
      document
        .getElementById("questionSelectionOverlay")
        .classList.add("hidden");
    }
  });

document.getElementById("nextQuestion").addEventListener("click", async () => {
  try {
    // Completely clear the evaluation section
    const evaluationResults = document.getElementById("evaluationResults");
    // Hide the entire evaluation container
    evaluationResults.classList.add("hidden");
    evaluationResults.style.display = "none";
    // Clear all inner content so nothing remains visible:
    const scoresDiv = document.getElementById("scores");
    scoresDiv.innerHTML = "";

    // Now get a new question and scroll to it
    await getNewQuestion(true);

    // Reset input fields
    document.getElementById("claimInput").value = "";
    document.getElementById("argumentInput").value = "";
    document.getElementById("counterargumentInput").value = "";

    // Scroll to the question section
    document.getElementById("questionDescription").scrollIntoView({
      behavior: "smooth",
      block: "start",
      inline: "nearest",
    });
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  } catch (error) {
    console.error("Error loading new question:", error);
    document.getElementById("errorMessage").textContent =
      "Failed to load new question";
  }
});

function updateLocalLevelInfo(totalXp, levelInfo) {
  // Use dynamic import to access the module function
  import("./level.js").then((levelModule) => {
    levelModule.updateLevelInfo(totalXp, levelInfo);
  });
}

function updateLocalXpIndicator(totalXp, levelInfo) {
  // Update the local level info
  updateLocalLevelInfo(totalXp, levelInfo);

  // Then update level images using dynamic import
  import("./level.js").then((levelModule) => {
    // Just update the images since we already updated the level info
    const levelImages = document.querySelectorAll(".level-image");
    levelImages.forEach((img) => {
      img.src = levelInfo.level_image;
      img.alt = levelInfo.level_label;
    });
  });
}

// Function to load saved categories
async function loadSavedCategories() {
  try {
    const response = await fetch("/get_categories");
    const data = await response.json();
    // If no categories are returned, use the defaults
    selectedCategories =
      data.categories && data.categories.length > 0
        ? data.categories
        : DEFAULT_CATEGORIES;

    // Wait for next tick to ensure DOM is ready
    setTimeout(() => {
      updateCategoryUI();
    }, 0);
  } catch (error) {
    console.error("Error loading categories:", error);
    selectedCategories = DEFAULT_CATEGORIES;
    setTimeout(() => {
      updateCategoryUI();
    }, 0);
  }
}

// Local wrappers to use imported functions
function localScrollToChallengeEvaluation() {
  import("./evaluation.js").then((evalModule) => {
    evalModule.scrollToChallengeEvaluation();
  });
}

function localScrollToMainEvaluation() {
  import("./evaluation.js").then((evalModule) => {
    evalModule.scrollToMainEvaluation();
  });
}

// Event listener for achievement updates
document.addEventListener("refreshAchievements", () => {
  updateLocalAchievementsDisplay(all_achievements);
});

// Write Question button handler (for pro users)
const writeQuestionButton = document.getElementById("writeQuestionButton");
if (writeQuestionButton) {
  writeQuestionButton.addEventListener("click", () => {
    document.getElementById("writeQuestionOverlay").classList.remove("hidden");
    document.getElementById("customQuestion").focus();
  });

  // Close button for write question overlay
  document
    .getElementById("closeWriteQuestion")
    .addEventListener("click", () => {
      document.getElementById("writeQuestionOverlay").classList.add("hidden");
    });

  // Click outside to close
  document
    .getElementById("writeQuestionOverlay")
    .addEventListener("click", (e) => {
      if (e.target === document.getElementById("writeQuestionOverlay")) {
        document.getElementById("writeQuestionOverlay").classList.add("hidden");
      }
    });

  // Submit custom question
  document
    .getElementById("submitCustomQuestion")
    .addEventListener("click", () => {
      const customQuestionText = document
        .getElementById("customQuestion")
        .value.trim();

      if (!customQuestionText) {
        showToast("Please enter a question", "error");
        return;
      }

      // Create a custom question object with a unique ID
      const customQuestion = {
        id: "custom_" + Date.now(),
        description: customQuestionText,
        category: "Custom", // Keep this as "Custom" for internal use
        isCustom: true,
      };

      // Store the selected question
      currentQuestion = customQuestion;
      sessionStorage.setItem("currentQuestion", JSON.stringify(customQuestion));

      // Also store in the server session
      fetch("/store_custom_question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: customQuestion }),
      }).catch((error) => {
        console.error("Error storing custom question:", error);
      });

      // Update the display
      updateQuestionDisplay(customQuestion);

      // Hide the overlay
      document.getElementById("writeQuestionOverlay").classList.add("hidden");

      // Clear the textarea for next time
      document.getElementById("customQuestion").value = "";
    });
}
