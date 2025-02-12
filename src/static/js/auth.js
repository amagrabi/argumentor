function showAuthModal() {
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Login/Signup</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove(); event.stopPropagation()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">
            &times;
          </button>
        </div>
        <form id="authForm" class="space-y-4">
          <div id="authErrorMessage" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">Username</label>
            <input type="text" id="authUsername" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Password</label>
            <input type="password" id="authPassword" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div class="flex gap-4">
            <button type="submit" class="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
              Login
            </button>
            <button type="button" onclick="handleAuth('signup')"
                    class="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">
              Signup
            </button>
          </div>
        </form>
        <div id="googleButtonContainer" class="mt-4"></div>
        <div class="mt-6">
          <button onclick="handleGoogleAuth()"
                  class="w-full flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
            <svg class="w-5 h-5" viewBox="0 0 24 24">
              <path fill="currentColor" d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a5.94 5.94 0 1 1 0-11.88c1.094 0 2.354.371 3.227 1.067l2.355-2.362A9.914 9.914 0 0 0 12.545 2C7.021 2 2.545 6.477 2.545 12s4.476 10 10 10c5.523 0 10-4.477 10-10a9.9 9.9 0 0 0-1.091-4.571l-8.909 3.81z"/>
            </svg>
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  `;

  // Remove any existing modal first
  document
    .querySelectorAll('div[class*="fixed inset-0"]')
    .forEach((existingModal) => existingModal.remove());

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      modal.remove();
      document.removeEventListener("keydown", handleKeyDown);
    }
  };
  document.addEventListener("keydown", handleKeyDown);
  document.body.appendChild(modal);

  // Attach submit event listener after the modal is in the DOM
  const authForm = modal.querySelector("#authForm");
  authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    handleAuth("login");
  });

  modal.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", () => {
      document.getElementById("authErrorMessage").classList.add("hidden");
    });
  });
}

async function handleAuth(action) {
  const username = document.getElementById("authUsername").value;
  const password = document.getElementById("authPassword").value;
  const errorMessage = document.getElementById("authErrorMessage");

  try {
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");

    const response = await fetch(`/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const contentType = response.headers.get("content-type");
    const data = contentType?.includes("json")
      ? await response.json()
      : { error: await response.text() };

    if (!response.ok) throw new Error(data.error || "Authentication failed");

    // Close the auth modal if present
    const authModal = document
      .querySelector("#authForm")
      .closest('div[class*="fixed inset-0"]');
    if (authModal) authModal.remove();

    // For the profile page, we reload immediately
    if (window.location.pathname === "/profile") {
      window.location.reload();
      return;
    }

    // For non-profile pages, force a full reload so that
    // header elements (username, XP, settings button click) get reinitialized.
    window.location.reload();

    // Alternatively, if you don't want to reload, you would need to:
    // 1. Call updateAuthUI(userData, false) to update text.
    // 2. Manually re-bind any event listeners (such as for the settings button)
    // which can be more complex.
  } catch (error) {
    console.error("Auth error:", error);
    errorMessage.textContent = error.message;
    errorMessage.classList.remove("hidden");
  }
}

// Initialize Google client
function initGoogleAuth() {
  const meta = document.querySelector('meta[name="google-signin-client_id"]');
  const clientId = meta ? meta.getAttribute("content") : "";
  google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleAuthResponse,
  });
}

// Handle Google auth button click
function handleGoogleAuth() {
  console.log("Google auth button clicked");
  if (google && google.accounts && google.accounts.id) {
    google.accounts.id.prompt((notification) => {
      console.log("Google prompt response:", notification);
    });
  } else {
    console.error(
      "Google API not available. Check if the script loaded properly."
    );
  }
}

// Handle Google auth response
function handleGoogleAuthResponse(response) {
  if (!response.credential) {
    console.log("No token received");
    return;
  }
  fetch("/google-auth", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: response.credential }),
  })
    .then((res) => {
      if (!res.ok) {
        throw new Error("Google authentication failed");
      }
      return res.json();
    })
    .then((data) => {
      // Remove the auth modal by referencing the auth form's container
      const authForm = document.querySelector("#authForm");
      if (authForm) {
        const modal = authForm.closest('div[class*="fixed inset-0"]');
        if (modal) {
          modal.remove();
        }
      }
      // Force a full page reload so the header (with the new username) is updated.
      window.location.reload();
    })
    .catch((error) => {
      console.error("Google auth error:", error);
      alert("Failed to authenticate with Google");
    });
}

// Load Google library and initialize
(function loadGoogleAuth() {
  const script = document.createElement("script");
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.defer = true;
  document.head.appendChild(script);
  script.onload = initGoogleAuth;
})();
