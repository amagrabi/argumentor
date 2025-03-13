/**
 * Achievement Tooltip Positioning
 *
 * This script handles the positioning of achievement tooltips to ensure they're
 * always visible on the screen, regardless of the achievement's position in the grid.
 *
 * It uses a combination of JavaScript and CSS to:
 * 1. Detect the position of each achievement in the grid
 * 2. Position tooltips to expand to the right for icons on the left side of the screen
 * 3. Position tooltips to expand to the left for icons on the right side of the screen
 * 4. Adapt to different grid layouts (2, 3, 4 rows, etc.)
 */

document.addEventListener("DOMContentLoaded", function () {
  // Initialize tooltip positioning
  setupAchievementTooltips();

  // Also set up when window is resized
  window.addEventListener("resize", setupAchievementTooltips);

  // Listen for the achievementsLoaded event
  document.addEventListener("achievementsLoaded", setupAchievementTooltips);

  // Set up a MutationObserver to detect when achievements are added to the DOM
  const achievementObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "childList" &&
        (mutation.target.classList.contains("inline-grid") ||
          mutation.target.closest(".inline-grid"))
      ) {
        setupAchievementTooltips();
      }
    });
  });

  // Start observing the document with the configured parameters
  const achievementContainers = document.querySelectorAll(".inline-grid");
  achievementContainers.forEach((container) => {
    achievementObserver.observe(container, { childList: true, subtree: true });
  });

  // Also observe the body for any new achievement containers that might be added
  achievementObserver.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: false,
    characterData: false,
  });
});

/**
 * Sets up achievement tooltips by calculating their position in the grid
 * and adjusting their position to ensure they're always visible.
 */
function setupAchievementTooltips() {
  const achievementGroups = document.querySelectorAll(".inline-grid > .group");
  if (!achievementGroups.length) return;

  // Get the grid container
  const gridContainer = achievementGroups[0].parentElement;

  // Get the number of columns in the grid
  const computedStyle = window.getComputedStyle(gridContainer);
  const gridTemplateColumns = computedStyle.getPropertyValue(
    "grid-template-columns"
  );
  const columnCount = gridTemplateColumns.split(" ").length;

  achievementGroups.forEach((group, index) => {
    const tooltip = group.querySelector(".opacity-0.group-hover\\:opacity-100");
    if (!tooltip) return;

    // Add mouseenter event to dynamically position tooltip
    group.addEventListener("mouseenter", () => {
      // Reset any previous positioning
      tooltip.style.left = "";
      tooltip.style.right = "";
      tooltip.style.transform = "";

      // Calculate row and column position
      const row = Math.floor(index / columnCount);
      const column = index % columnCount;

      // Calculate the center position of the icon relative to the viewport
      const rect = group.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const iconCenter = rect.left + rect.width / 2;

      // Determine if we're in the left or right half of the screen
      const isLeftHalf = iconCenter < viewportWidth / 2;

      // For left half of the screen, position tooltip to the right
      // For right half of the screen, position tooltip to the left
      if (isLeftHalf) {
        tooltip.style.left = "0";
        tooltip.style.right = "auto";
        tooltip.style.transform = "translateY(0.5rem)";
      } else {
        tooltip.style.left = "auto";
        tooltip.style.right = "0";
        tooltip.style.transform = "translateY(0.5rem)";
      }
    });
  });
}
