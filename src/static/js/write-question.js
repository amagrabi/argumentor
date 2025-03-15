/**
 * Write Question Functionality - Simplified Implementation
 */

// Single event listener for initialization
document.addEventListener("DOMContentLoaded", function () {
  setupWriteQuestionButton();
});

// Function to set up the Write Question button and overlay
function setupWriteQuestionButton() {
  const writeButton = document.getElementById("writeQuestionButton");
  if (!writeButton) return;

  // Clean up any existing static overlay
  const staticOverlay = document.getElementById("writeQuestionOverlay");
  if (staticOverlay) {
    // Instead of removing it, just make sure it stays hidden
    staticOverlay.classList.add("hidden");
    staticOverlay.style.display = "none";
  }

  // Override any existing event listeners by cloning the button
  const newButton = writeButton.cloneNode(true);
  if (writeButton.parentNode) {
    writeButton.parentNode.replaceChild(newButton, writeButton);
  }

  // Single click handler for the button
  newButton.addEventListener("click", function (event) {
    event.preventDefault();
    createDynamicOverlay();
    return false;
  });

  // Override the global showWriteQuestionOverlay function
  window.showWriteQuestionOverlay = createDynamicOverlay;
}

// Function to create a dynamic overlay
function createDynamicOverlay() {
  // Remove any existing dynamic overlay
  removeDynamicOverlay();

  // Hide the static overlay if it exists
  const staticOverlay = document.getElementById("writeQuestionOverlay");
  if (staticOverlay) {
    staticOverlay.classList.add("hidden");
    staticOverlay.style.display = "none";
  }

  // Create overlay container
  const overlay = document.createElement("div");
  overlay.id = "dynamicWriteQuestionOverlay";
  overlay.style.position = "fixed";
  overlay.style.top = "0";
  overlay.style.left = "0";
  overlay.style.right = "0";
  overlay.style.bottom = "0";
  overlay.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
  overlay.style.display = "flex";
  overlay.style.justifyContent = "center";
  overlay.style.alignItems = "center";
  overlay.style.zIndex = "999999";

  // Create the content container
  const container = document.createElement("div");
  container.style.backgroundColor = "white";
  container.style.borderRadius = "12px";
  container.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.2)";
  container.style.padding = "20px";
  container.style.width = "90%";
  container.style.maxWidth = "600px";

  // Create header
  const header = document.createElement("div");
  header.style.display = "flex";
  header.style.justifyContent = "space-between";
  header.style.alignItems = "center";
  header.style.marginBottom = "16px";

  // Get translations from the global translations object
  const translations = window.translations || {};
  const writeQuestionTranslations = translations.writeQuestion || {};

  // Title
  const title = document.createElement("h3");
  title.textContent =
    writeQuestionTranslations.title || "Write Your Own Question";
  title.style.fontSize = "18px";
  title.style.fontWeight = "bold";
  title.style.margin = "0";

  // Close button
  const closeButton = document.createElement("button");
  closeButton.textContent = writeQuestionTranslations.close || "✕";
  closeButton.style.backgroundColor = "#333";
  closeButton.style.color = "white";
  closeButton.style.border = "none";
  closeButton.style.borderRadius = "20px";
  closeButton.style.padding = "5px 12px";
  closeButton.style.cursor = "pointer";
  closeButton.addEventListener("click", removeDynamicOverlay);

  header.appendChild(title);
  header.appendChild(closeButton);

  // Text area container
  const textAreaContainer = document.createElement("div");
  textAreaContainer.style.marginBottom = "16px";

  // Text area
  const textArea = document.createElement("textarea");
  textArea.style.width = "100%";
  textArea.style.padding = "8px";
  textArea.style.border = "1px solid #ccc";
  textArea.style.borderRadius = "4px";
  textArea.style.fontSize = "14px";
  textArea.style.marginBottom = "8px";
  textArea.style.resize = "vertical";
  textArea.rows = 3;
  textArea.placeholder =
    writeQuestionTranslations.label || "Enter your question here...";
  textArea.maxLength = 200;

  // Hint text
  const hint = document.createElement("div");
  hint.textContent =
    writeQuestionTranslations.hint ||
    "Write a clear question that can be argued from multiple perspectives.";
  hint.style.fontSize = "12px";
  hint.style.color = "#666";

  textAreaContainer.appendChild(textArea);
  textAreaContainer.appendChild(hint);

  // Button container
  const buttonContainer = document.createElement("div");
  buttonContainer.style.display = "flex";
  buttonContainer.style.justifyContent = "flex-end";

  // Submit button
  const submitButton = document.createElement("button");
  submitButton.textContent =
    writeQuestionTranslations.submit || "Use This Question";
  submitButton.style.backgroundColor = "#444";
  submitButton.style.color = "white";
  submitButton.style.border = "none";
  submitButton.style.borderRadius = "6px";
  submitButton.style.padding = "8px 16px";
  submitButton.style.fontSize = "14px";
  submitButton.style.fontWeight = "500";
  submitButton.style.cursor = "pointer";

  submitButton.addEventListener("click", function () {
    const questionText = textArea.value.trim();

    if (!questionText) {
      // Get error message from translations if available
      const errorMessage =
        translations.errors && translations.errors.emptyQuestion
          ? translations.errors.emptyQuestion
          : "Please enter a question";

      if (typeof showToast === "function") {
        showToast(errorMessage, "error");
      } else {
        alert(errorMessage);
      }
      return;
    }

    // Create custom question object
    const customQuestion = {
      id: "custom_" + Date.now(),
      description: questionText,
      category: "Custom",
      isCustom: true,
    };

    // Store the question in global context and session storage
    window.currentQuestion = customQuestion; // Always set it globally
    sessionStorage.setItem("currentQuestion", JSON.stringify(customQuestion));

    // Send to server
    fetch("/store_custom_question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: customQuestion }),
    }).catch(function (error) {
      console.error("Error storing custom question:", error);
    });

    // Update display
    if (typeof updateQuestionDisplay === "function") {
      updateQuestionDisplay(customQuestion);
    } else {
      // Fallback if updateQuestionDisplay is not available
      const questionDisplay = document.getElementById("questionDescription");
      if (questionDisplay) {
        questionDisplay.textContent = customQuestion.description;
      }
    }

    // Remove the overlay
    removeDynamicOverlay();
  });

  buttonContainer.appendChild(submitButton);

  // Add all elements to the container
  container.appendChild(header);
  container.appendChild(textAreaContainer);
  container.appendChild(buttonContainer);

  // Add click outside to close
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) {
      removeDynamicOverlay();
    }
  });

  // Add container to overlay
  overlay.appendChild(container);

  // Add overlay to document body
  document.body.appendChild(overlay);

  // Focus on textarea
  setTimeout(function () {
    textArea.focus();
  }, 100);
}

// Function to remove dynamic overlay
function removeDynamicOverlay() {
  const overlay = document.getElementById("dynamicWriteQuestionOverlay");
  if (overlay && overlay.parentNode) {
    overlay.parentNode.removeChild(overlay);
  }

  // Ensure the static overlay remains hidden
  const staticOverlay = document.getElementById("writeQuestionOverlay");
  if (staticOverlay) {
    staticOverlay.classList.add("hidden");
    staticOverlay.style.display = "none";
  }
}
