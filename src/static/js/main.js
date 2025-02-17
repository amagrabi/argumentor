import { hexToRgb, rgbToHex, interpolateColor } from "./utils.js";
import {
  DEFAULT_CATEGORIES,
  CATEGORY_ICONS,
  ERROR_MESSAGES,
  EVALUATION_CATEGORIES,
  EVALUATION_TRANSLATION_MAPPING,
} from "./constants.js";
import {
  typeWriter,
  updateQuestionDisplay,
  scoreToColor,
  setupCharCounter,
} from "./helpers.js";

// Initialize mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: "base",
  flowchart: {
    curve: "basis",
    padding: 30,
    nodeSpacing: 50,
    rankSpacing: 70,
    htmlLabels: true,
    defaultRenderer: "elk",
  },
  themeVariables: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: "16px",
    primaryColor: "#4F46E5",
    primaryTextColor: "#1F2937",
    lineColor: "#9CA3AF",
    edgeLabelBackground: "#FFFFFF",
    clusterBkg: "#F3F4F6",
    clusterBorder: "#E5E7EB",
    nodeBorder: "#4F46E5",
    mainBkg: "#FFFFFF",
  },
});

// Global variable that stores your selected category values.
let selectedCategories = [];
// Global variable to store the currently displayed question.
let currentQuestion = null;

// Modified getNewQuestion function:
// 1. It appends the selectedCategories as a query parameter to the request URL.
// 2. After fetching a new question, it stores that question in sessionStorage.
async function getNewQuestion(shouldScroll = true) {
  try {
    let query = "";
    if (selectedCategories.length > 0) {
      const encodedCategories = selectedCategories.map(encodeURIComponent);
      query = `?categories=${encodedCategories.join(",")}`;
    }
    const response = await fetch("/get_question" + query);
    const question = await response.json();
    if (question.error) {
      console.error("Error fetching new question:", question.error);
      return;
    }
    currentQuestion = question;
    sessionStorage.setItem("currentQuestion", JSON.stringify(question));

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
      const categoryText = CATEGORY_ICONS[question.category]
        ? `${CATEGORY_ICONS[question.category]} ${question.category}`
        : question.category;
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

// Updated submission handler
document.getElementById("submitAnswer").addEventListener("click", async () => {
  const startTime = Date.now();
  const claim = document.getElementById("claimInput").value.trim();
  const argument = document.getElementById("argumentInput").value.trim();
  const submitBtn = document.getElementById("submitAnswer");
  const counterargument = document
    .getElementById("counterargumentInput")
    .value.trim();

  if (!claim || !argument) {
    document.getElementById("errorMessage").textContent =
      translations.errors.requiredFields;
    return;
  }

  const payload = {
    claim,
    argument,
    counterargument: counterargument || null,
  };

  if (currentQuestion?.id) {
    payload.question_id = currentQuestion.id;
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
  submitBtn.innerHTML = `
    <span class="loading-dots">
      <span class="animate-pulse">${translations.challenge.analyzing}</span>
    </span>
  `;
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
      if (elapsed < 2000) {
        await new Promise((resolve) => setTimeout(resolve, 2000 - elapsed));
      }
    }

    const data = await response.json(); // Single parse here

    if (!response.ok) {
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
        <div id="totalScoreBar" class="rounded-full total-progress-bar" style="width: ${totalScorePercent}%; background-color: ${totalScoreColor};"></div>
      </div>
      <p id="overallFeedback" class="text-md">
        ${data.evaluation.overall_feedback}
      </p>
    `;

    // Now set the score color after the element exists
    document.getElementById("totalScoreValue").style.color = totalScoreColor;

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
        <div class="mt-8 flex justify-center">
          <div class="w-full max-w-full bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 class="text-lg font-bold mb-4 text-center text-gray-800">Estimated Argument Structure</h3>
            <div id="argumentStructureViz" class="overflow-x-auto flex justify-center"></div>
          </div>
        </div>
      `;

      const graph = `graph TD;
        %% Node styling
        classDef premise fill:#F8FAFC,stroke:#1F2937,stroke-width:2px,rx:12,ry:12;
        classDef conclusion fill:#EEF2FF,stroke:#1F2937,stroke-width:2px,rx:12,ry:12;

        %% Edge styling
        linkStyle default stroke:#9CA3AF,stroke-width:2px;

        ${structure.nodes
          .map(
            (node) =>
              `${safeIds[node.id]}["<div class='p-2 rounded-xl no-wrap-text'>${
                node.text
              }</div>"]`
          )
          .join(";\n")}
        ${structure.edges
          .map((edge) => `${safeIds[edge.from]}-->${safeIds[edge.to]}`)
          .join(";\n")}

        %% Apply classes
        ${structure.nodes
          .map(
            (node) =>
              `class ${safeIds[node.id]} ${
                node.type === "premise" ? "premise" : "conclusion"
              }`
          )
          .join(";\n")}
      `;

      mermaid
        .render("argumentGraph", graph)
        .then((result) => {
          document.getElementById("argumentStructureViz").innerHTML =
            result.svg;
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

      // Use the mapping defined in constants.js
      const translationKey = EVALUATION_TRANSLATION_MAPPING[category];
      const translatedCategory =
        (translations.evaluation.scores &&
          translations.evaluation.scores[translationKey]) ||
        category;

      return `
        <div class="mb-2">
          <div class="flex justify-between items-center">
            <span class="font-medium">${translatedCategory}</span>
            <span class="font-medium score-value" data-final="${finalScore}" data-color="${color}" style="color: #e53e3e;">1/10</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
            <div class="rounded-full h-2 progress-fill"
                 data-score="${finalWidthPercent}"
                 data-color="${color}"
                 style="width: 10%; background-color: #e53e3e;"></div>
          </div>
          <p class="text-sm text-gray-500 feedback" data-final="${feedbackText}"></p>
        </div>
      `;
    }).join("");

    scoresDiv.innerHTML = evaluationHTML;

    setTimeout(() => {
      document.querySelectorAll(".progress-fill").forEach((fill, index) => {
        const delay = index * 100;
        setTimeout(() => {
          const targetWidth = fill.getAttribute("data-score");
          const targetColor = fill.getAttribute("data-color");
          fill.style.backgroundColor = "#e53e3e";
          fill.style.width = "10%";
          void fill.offsetWidth; // Trigger reflow
          fill.style.width = targetWidth + "%";
          fill.style.backgroundColor = targetColor;
        }, delay);
      });
      document
        .querySelectorAll(".score-value")
        .forEach((scoreElement, index) => {
          const finalScore = parseFloat(scoreElement.dataset.final);
          const targetColor = scoreElement.dataset.color;
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

    // Update XP and level info as before...
    document.getElementById("xpGained").innerHTML =
      "<strong>" + data.xp_gained + "</strong>";
    document.getElementById("currentLevel").innerHTML =
      "<strong>" + data.current_level + "</strong>";
    document.getElementById("xpProgressText").textContent =
      data.level_info.xp_into_level + " / " + data.level_info.xp_needed;
    document.getElementById("nextLevel").textContent =
      data.level_info.next_level;

    const xpOldBar = document.getElementById("xpOldBar");
    const xpNewBar = document.getElementById("xpNewBar");

    if (data.leveled_up) {
      xpOldBar.style.display = "none";
      xpNewBar.style.left = "0%";
      xpNewBar.style.width = data.level_info.progress_percent + "%";
    } else {
      xpOldBar.style.display = "block";
      const oldXpValue = data.current_xp - data.xp_gained;
      const oldPercent =
        ((oldXpValue - data.level_info.current_threshold) /
          data.level_info.xp_needed) *
        100;
      xpOldBar.style.width = oldPercent + "%";
      xpNewBar.style.left = oldPercent + "%";
      const newPortion = data.level_info.progress_percent - oldPercent;
      xpNewBar.style.width = newPortion + "%";
    }

    if (data.leveled_up) {
      document.getElementById("levelUpMessage").textContent = "Level Up!";
    } else {
      document.getElementById("levelUpMessage").textContent = "";
    }

    const evaluationResults = document.getElementById("evaluationResults");
    evaluationResults.classList.remove("hidden");
    evaluationResults.style.display = "block";
    evaluationResults.classList.add("fade-in");
    evaluationResults.scrollIntoView({ behavior: "smooth" });

    // Update header elements immediately after answer submission
    const userLevelElem = document.getElementById("userLevelElem");
    if (userLevelElem) {
      userLevelElem.textContent = data.current_level;
    }

    const miniXpBarFill = document.getElementById("miniXpBarFill");
    if (miniXpBarFill) {
      miniXpBarFill.style.width = data.level_info.progress_percent + "%";
    }

    // Update the small circle indicator of the level
    const levelNumberElem = document.getElementById("levelNumber");
    if (levelNumberElem && data.level_info) {
      levelNumberElem.textContent = data.level_info.level_number;
    }

    // After a successful answer submission, store the answer ID for later use:
    if (data.answer_id) {
      sessionStorage.setItem("lastAnswerId", data.answer_id);
    }

    // If the evaluation contains a challenge, display the challenge text and reveal the challenge section.
    if (data.evaluation.challenge) {
      const challengeSection = document.getElementById("challengeSection");
      const challengeTextElem = document.getElementById("challengeText");
      if (challengeTextElem && challengeSection) {
        challengeTextElem.textContent = data.evaluation.challenge;
        challengeSection.classList.remove("hidden");
      }
    }

    // Update character count for the challenge response text area.
    document
      .getElementById("challengeResponseInput")
      .addEventListener("input", () => {
        document.getElementById("challengeErrorMessage").textContent = "";
      });

    // Display XP message
    document.getElementById("xpMessage").textContent = data.xp_message || "";
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

// Update the DOMContentLoaded handler
window.addEventListener("DOMContentLoaded", () => {
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
    const storedQuestion = sessionStorage.getItem("currentQuestion");
    if (storedQuestion) {
      currentQuestion = JSON.parse(storedQuestion);
      updateQuestionDisplay(currentQuestion);
    } else {
      getNewQuestion();
    }
  });

  const challengeBtn = document.getElementById("submitChallengeResponse");

  // Bind the challenge submission event listener only once.
  challengeBtn.addEventListener("click", async () => {
    const startTime = Date.now();
    const challengeResponse = document
      .getElementById("challengeResponseInput")
      .value.trim();
    const challengeErrorMessage = document.getElementById(
      "challengeErrorMessage"
    );

    if (!challengeResponse) {
      challengeErrorMessage.textContent =
        "Please provide a response to the challenge.";
      return;
    }
    const answerId = sessionStorage.getItem("lastAnswerId");
    if (!answerId) {
      challengeErrorMessage.textContent = "No associated answer found.";
      return;
    }

    challengeBtn.innerHTML = `
      <span class="loading-dots">
        <span class="animate-pulse">${translations.challenge.analyzing}</span>
      </span>
    `;
    challengeBtn.disabled = true;

    try {
      const response = await fetch("/submit_challenge_response", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          challenge_response: challengeResponse,
          answer_id: answerId,
        }),
      });

      if (response.ok) {
        const elapsed = Date.now() - startTime;
        if (elapsed < 3000) {
          await new Promise((resolve) => setTimeout(resolve, 3000 - elapsed));
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
      updateXpIndicator(data.current_xp, data.level_info);

      // Update challenge evaluation feedback.
      const challengeEvalDiv = document.getElementById(
        "challengeEvaluationResults"
      );
      const totalScore = data.evaluation.total_score;
      const totalScorePercent = totalScore * 10;
      const totalScoreColor = scoreToColor(totalScore);

      let challengeHtml = `
        <p class="text-l font-bold mb-2">
          ${translations.evaluation.overall}:
          <span id="challengeTotalScoreValue" style="color: ${totalScoreColor};">${totalScore.toFixed(
        1
      )}/10</span>
        </p>
        <div class="w-full bg-gray-200 rounded-full h-2.5 mb-2">
          <div id="challengeTotalScoreBar" class="rounded-full total-progress-bar"
               style="width: ${totalScorePercent}%; background-color: ${totalScoreColor};"></div>
        </div>
        <p id="challengeOverallFeedback" class="text-md">${
          data.evaluation.overall_feedback
        }</p>
        <div class="flex flex-wrap gap-2 mt-2">`;

      // Use the centralized evaluation categories from constants.js
      EVALUATION_CATEGORIES.forEach((category) => {
        if (typeof data.evaluation.scores[category] !== "undefined") {
          const score = data.evaluation.scores[category];
          const translationKey = EVALUATION_TRANSLATION_MAPPING[category];
          // Lookup the translated category label; fallback to the original if missing
          const translatedCategory =
            (translations.evaluation.scores &&
              translations.evaluation.scores[translationKey]) ||
            category;
          challengeHtml += `<div class="px-2 py-1 rounded-full text-xs" style="background-color: ${scoreToColor(
            score
          )};">
                                ${translatedCategory}: ${score}/10
                              </div>`;
        }
      });

      challengeHtml += `</div>`;
      challengeEvalDiv.innerHTML = challengeHtml;
      challengeEvalDiv.classList.remove("hidden");

      // Display XP message for challenge within the challenge evaluation section
      const challengeXpMessage = document.createElement("p");
      challengeXpMessage.classList.add("text-sm", "text-red-600", "mt-4");
      challengeXpMessage.textContent = data.xp_message || "";
      challengeEvalDiv.appendChild(challengeXpMessage);

      challengeBtn.innerHTML = "Submit";
      challengeBtn.disabled = false;

      // After the evaluation is displayed, scroll to it
      setTimeout(() => {
        scrollToChallengeEvaluation();
      }, 100); // Small delay to ensure the content is rendered
    } catch (error) {
      console.error("Error submitting challenge response:", error);
      challengeErrorMessage.innerHTML = ERROR_MESSAGES.UNEXPECTED_ERROR;
      challengeBtn.innerHTML = "Submit";
      challengeBtn.disabled = false;
    }
  });
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
            heading.textContent = category;
            questionList.appendChild(heading);

            groups[category].forEach((question) => {
              const item = document.createElement("div");
              item.className =
                "question-item cursor-pointer p-2 border-b hover:bg-gray-100";
              item.textContent = question.description;
              item.dataset.id = question.id;
              item.addEventListener("click", () => {
                // Immediately hide the question selection overlay
                const overlay = document.getElementById(
                  "questionSelectionOverlay"
                );
                overlay.classList.add("hidden");

                // Now fetch and update with the selected question
                fetch("/select_question", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ question_id: question.id }),
                })
                  .then((response) => response.json())
                  .then((selected) => {
                    currentQuestion = selected;
                    updateQuestionDisplay(selected);
                    typeWriter(
                      document.getElementById("questionDescription"),
                      selected.description,
                      15
                    );
                    // Clear the input fields
                    document.getElementById("claimInput").value = "";
                    document.getElementById("argumentInput").value = "";
                    document.getElementById("counterargumentInput").value = "";
                    document.getElementById("charCount").textContent = "200";
                    document.getElementById("errorMessage").textContent = "";
                  })
                  .catch((error) =>
                    console.error("Error selecting question:", error)
                  );
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

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    handleLogin();
  });
}

function updateXpIndicator(totalXp, levelInfo) {
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

  // Update the level number indicator
  const levelNumberElem = document.getElementById("levelNumber");
  if (levelNumberElem) {
    levelNumberElem.textContent = levelInfo.level_number;
  }
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

// Add new function for scrolling to challenge evaluation
function scrollToChallengeEvaluation() {
  const challengeEvalDiv = document.getElementById(
    "challengeEvaluationResults"
  );
  if (challengeEvalDiv) {
    challengeEvalDiv.scrollIntoView({
      behavior: "smooth",
      block: "start",
      inline: "nearest",
    });
  }
}
