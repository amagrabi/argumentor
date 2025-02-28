// Level module - Handles level and XP related functionality

// Shared function for handling XP animations
export function handleXpAnimations(data, options) {
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

    // Update non-image level info
    updateLevelInfo(data.total_xp, data.level_info);

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

                      // Get the level number indicator associated with this level image
                      const levelNumberIndicator = levelImageContainer
                        .closest(".level-indicator, .level-image-wrapper")
                        .querySelector(".level-number-indicator");

                      // Force the level number to show the old level and prepare for animation
                      if (levelNumberIndicator) {
                        // Calculate the old level number
                        const oldLevelNumber =
                          data.previous_level ||
                          parseInt(data.level_info.level_number) - 1;

                        // Store current textContent before we change it
                        levelNumberIndicator.dataset.oldLevel =
                          levelNumberIndicator.textContent;

                        // Force the old level number to be displayed
                        levelNumberIndicator.textContent = oldLevelNumber;

                        // Force a reflow to ensure the old number is rendered
                        void levelNumberIndicator.offsetWidth;

                        // Now add the transition class to start animation
                        levelNumberIndicator.classList.add(
                          "level-number-transition"
                        );
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

                          // Create a specific delayed update function for the level number
                          const updateLevelNumber = () => {
                            if (levelNumberIndicator) {
                              // Set a timer to update the number text at exactly the right moment during animation
                              setTimeout(() => {
                                levelNumberIndicator.textContent =
                                  data.current_level ||
                                  data.level_info.level_number;
                              }, 50); // Small delay to ensure it happens during the opacity:0 part of animation
                            }
                          };

                          // Schedule the level number update
                          updateLevelNumber();

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

                        // Remove the level number transition class
                        if (levelNumberIndicator) {
                          levelNumberIndicator.classList.remove(
                            "level-number-transition"
                          );
                          // Clean up the temporary data attribute
                          delete levelNumberIndicator.dataset.oldLevel;
                        }

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
                      }, 600);
                    }
                  }, 800);
                } else {
                  // Normal progress animation
                  xpProgressBar.style.transition =
                    "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
                  xpProgressBar.style.width = targetWidth;
                }
              } else {
                // No XP gained, just set the width without animation
                xpProgressBar.style.transition = "none";
                xpProgressBar.style.width = targetWidth;
              }

              // Update non-image level info
              updateLevelInfo(data.total_xp, data.level_info);
            }

            // Disconnect observer after triggering animations
            xpAnimationObserver.disconnect();
          }, 100); // 100ms delay
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

// Split updateXpIndicator into two functions
export function updateLevelInfo(totalXp, levelInfo) {
  // Update the mini XP progress bar
  const miniXpBarFill = document.getElementById("miniXpBarFill");
  if (miniXpBarFill) {
    miniXpBarFill.style.width = levelInfo.progress_percent + "%";
  }

  // Update the level display element
  const userLevelElem = document.getElementById("userLevelElem");
  if (userLevelElem) {
    userLevelElem.textContent = levelInfo.display_name;
  }

  // Update all level number indicators, except those that are currently animating
  const levelNumberElems = document.querySelectorAll(
    "#levelNumber, .level-number-indicator:not(.level-number-transition)"
  );
  levelNumberElems.forEach((elem) => {
    if (elem) {
      elem.textContent = levelInfo.level_number;
    }
  });
}

export function updateXpIndicator(totalXp, levelInfo) {
  updateLevelInfo(totalXp, levelInfo);

  // Update all level images on the page
  const levelImages = document.querySelectorAll(".level-image");
  levelImages.forEach((img) => {
    img.src = levelInfo.level_image;
    img.alt = levelInfo.level_label;
  });
}
