function showLoginModal() {
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Login</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove(); event.stopPropagation()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="loginForm" class="space-y-4">
          <div id="loginErrorMessage" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">Username or Email</label>
            <input type="text" id="loginIdentity" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Password</label>
            <input type="password" id="loginPassword" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div class="flex gap-4">
            <button type="submit" class="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
              Login
            </button>
            <button type="button" onclick="switchToSignup()" class="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">
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

  // Attach submit event listener after the modal is added to the DOM
  const loginForm = modal.querySelector("#loginForm");
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const identity = document.getElementById("loginIdentity").value;
    const password = document.getElementById("loginPassword").value;
    const errorMessage = document.getElementById("loginErrorMessage");
    try {
      errorMessage.textContent = "";
      errorMessage.classList.add("hidden");
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login: identity, password }),
      });

      // First check if response is json
      const contentType = response.headers.get("content-type");
      let data;
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        data = { error: await response.text() };
      }

      if (!response.ok) throw new Error(data.error || "Login failed");
      modal.remove();
      window.location.reload();
    } catch (error) {
      console.error("Login error:", error);
      errorMessage.textContent = error.message;
      errorMessage.classList.remove("hidden");
    }
  });

  // Remove any existing modal and append this one
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  document.body.appendChild(modal);
}

function showSignupModal() {
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Signup</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove(); event.stopPropagation()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="signupForm" class="space-y-4">
          <div id="signupErrorMessage" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">Username</label>
            <input type="text" id="signupUsername" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Email</label>
            <input type="email" id="signupEmail" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Password</label>
            <input type="password" id="signupPassword" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div class="flex gap-4">
            <button type="button" onclick="switchToLogin()" class="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">
              Login
            </button>
            <button type="submit" class="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
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

  const signupForm = modal.querySelector("#signupForm");
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("signupUsername").value;
    const email = document.getElementById("signupEmail").value;
    const password = document.getElementById("signupPassword").value;
    const errorMessage = document.getElementById("signupErrorMessage");
    try {
      errorMessage.textContent = "";
      errorMessage.classList.add("hidden");
      const response = await fetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Signup failed");
      modal.remove();
      window.location.reload();
    } catch (error) {
      console.error("Signup error:", error);
      errorMessage.textContent = error.message;
      errorMessage.classList.remove("hidden");
    }
  });

  // Remove any existing modal and add this one
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  document.body.appendChild(modal);
}

function switchToSignup() {
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  showSignupModal();
}

function switchToLogin() {
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  showLoginModal();
}

// When someone wants to authenticate, call this to show the login modal by default.
function showAuthModal() {
  showLoginModal();
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

  // First try authenticating without username
  fetch("/google-auth", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: response.credential }),
  })
    .then((res) => {
      if (res.status === 400) {
        // If server requires username, show username prompt modal
        return res.json().then((data) => {
          if (data.error === "Username is required for Google signups.") {
            showGoogleUsernameModal(response.credential);
            throw new Error("username_required");
          }
          throw new Error(data.error || "Google authentication failed");
        });
      }
      if (!res.ok) {
        throw new Error("Google authentication failed");
      }
      return res.json();
    })
    .then((data) => {
      const authForm = document.querySelector("#authForm");
      if (authForm) {
        const modal = authForm.closest('div[class*="fixed inset-0"]');
        if (modal) modal.remove();
      }
      window.location.reload();
    })
    .catch((error) => {
      if (error.message !== "username_required") {
        console.error("Google auth error:", error);
        alert("Failed to authenticate with Google");
      }
    });
}

function showGoogleUsernameModal(credential) {
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Choose Username</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="googleUsernameForm" class="space-y-4">
          <div id="googleUsernameError" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">Username</label>
            <input type="text" id="googleUsername" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <button type="submit" class="w-full bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
            Continue
          </button>
        </form>
      </div>
    </div>
  `;

  const form = modal.querySelector("#googleUsernameForm");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const username = document.getElementById("googleUsername").value;
    const errorDiv = document.getElementById("googleUsernameError");

    fetch("/google-auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: credential, username }),
    })
      .then((res) => {
        if (!res.ok)
          return res.json().then((data) => Promise.reject(data.error));
        return res.json();
      })
      .then(() => {
        modal.remove();
        window.location.reload();
      })
      .catch((error) => {
        errorDiv.textContent = error;
        errorDiv.classList.remove("hidden");
      });
  });

  document.body.appendChild(modal);
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
