let profiles = [];
let selectedProfile = null;

/* ============================================================================================================== */
/* LOAD PROFILES FROM BACKEND */
/* ============================================================================================================== */

function loadProfiles() {
  if (typeof PROFILES_FROM_DB !== "undefined") {
    profiles = PROFILES_FROM_DB;
  }
  renderProfiles();
}

/* ============================================================================================================== */
/* DISPLAY ALL PROFILE CARDS */
/* ============================================================================================================== */

function renderProfiles() {
  const grid = document.getElementById("profilesGrid");
  grid.innerHTML = "";

  profiles.forEach((profile) => {
    const profileCard = document.createElement("div");
    profileCard.className = "profile-card";
    profileCard.onclick = (event) => selectProfile(profile, event);

    profileCard.innerHTML = `
      <button class="remove-btn" onclick="removeProfile(event, ${profile.id})">×</button>
      <div class="profile-avatar ${profile.avatar}">${profile.initials}</div>
      <div class="profile-name">${profile.name}</div>
      <div class="profile-username">@${profile.username}</div>
    `;

    grid.appendChild(profileCard);
  });
}

/* ============================================================================================================== */
/* PROFILE CLICK */
/* ============================================================================================================== */

function selectProfile(profile, event) {
  selectedProfile = profile;

  document.querySelectorAll(".profile-card").forEach((card) => {
    card.classList.remove("selected");
  });

  event.currentTarget.classList.add("selected");
  document.getElementById("selectedProfileName").textContent =
    `Enter password for ${profile.name}`;
  document.getElementById("passwordSection").style.display = "block";
  document.getElementById("passwordInput").value = "";
  document.getElementById("passwordInput").focus();
  document.getElementById("message").style.display = "none";
  document.getElementById("passwordError").classList.remove("show");
}

/* ============================================================================================================== */
/* REMOVE PROFILE */
/* ============================================================================================================== */

function removeProfile(event, profileId) {
  event.stopPropagation();

  const profile = profiles.find((p) => p.id === profileId);
  if (!profile) return;

  if (confirm(`Are you sure you want to delete ${profile.name}?`)) {
    fetch("/delete_user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: profileId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok) {
          profiles = profiles.filter((p) => p.id !== profileId);
          renderProfiles();
          selectedProfile = null;
          document.getElementById("passwordSection").style.display = "none";
          document.getElementById("selectedProfileName").textContent =
            "Select a profile to continue";
          document.getElementById("message").style.display = "none";
          showMessage(`✅ ${profile.name} has been deleted!`, "success");
        } else {
          showMessage(
            "Error deleting profile: " + (data.error || "unknown"),
            "error",
          );
        }
      })
      .catch((err) => {
        console.error("Error:", err);
        showMessage("Error deleting profile", "error");
      });
  }
}

/* ============================================================================================================== */
/* LOGIN */
/* ============================================================================================================== */

function handleLogin() {
  if (!selectedProfile) {
    showMessage("Please select a profile", "error");
    return;
  }

  const passwordInput = document.getElementById("passwordInput");
  const password = passwordInput.value;
  const passwordError = document.getElementById("passwordError");
  const apiModal = document.getElementById("API-data-modal");

  fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: selectedProfile.username,
      password: password,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.ok) {
        // 1. Clear any previous errors
        passwordError.classList.remove("show");
        showMessage(`✅ Welcome, ${selectedProfile.name}!`, "success");

        // 2. Decide: Go straight to review OR show the optional setup
        if (data.has_keys) {
          // Everything is ready, proceed immediately
          window.location.href = "/go_to_review";
        } else {
          // Keys are missing. Show the modal so they CAN add them,
          // but allow them to skip it.
          apiModal.classList.remove("is-hidden");

          // We update the 'Cancel' button to act as a 'Skip' button 
          // to make it clear they aren't stuck here.
          const skipBtn = apiModal.querySelector(".btn-cancel");
          if (skipBtn) {
            skipBtn.textContent = "Skip for Now";
            skipBtn.onclick = () => {
              window.location.href = "/go_to_review";
            };
          }
        }
      } else {
        // 3. Handle Authentication Failure
        passwordError.classList.add("show");
        passwordInput.value = "";
        passwordInput.focus();
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showMessage("Error connecting to server", "error");
    });
}

function showMessage(text, type) {
  const messageDiv = document.getElementById("message");
  messageDiv.textContent = text;
  messageDiv.className = `message ${type}`;
}

function saveAPIKeys() {
    const openaiKey = document.getElementById("newOpenAIKey").value.trim();
    const elevenlabsKey = document.getElementById("ElevenLabsKey").value.trim();

    // If both are empty, we just treat it as a "Skip"
    if (!openaiKey && !elevenlabsKey) {
        window.location.href = "/go_to_review";
        return;
    }

    const saveBtn = document.querySelector("#API-data-modal .btn-create");
    saveBtn.textContent = "Saving...";
    saveBtn.disabled = true;

    fetch("/save_api_keys", { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            openai_key: openaiKey,    // Could be an empty string ""
            elevenlabs_key: elevenlabsKey // Could be an empty string ""
        }),
    })
    .then((res) => res.json())
    .then((data) => {
        if (data.ok) {
            // Once saved, proceed to the app
            window.location.href = "/go_to_review";
        } else {
            alert("Error saving keys: " + (data.error || "Unknown error"));
            saveBtn.textContent = "Save & Continue";
            saveBtn.disabled = false;
        }
    })
    .catch((err) => {
        console.error("Error:", err);
        alert("Failed to reach server.");
        saveBtn.disabled = false;
    });
}

/* ============================================================================================================== */
/* OPEN/CLOSE POP UP (add profile pop up) */
/* ============================================================================================================== */

function openAddProfileModal() {
  document.getElementById("addProfileModal").classList.add("show");
}

function closeAddProfileModal() {
  document.getElementById("addProfileModal").classList.remove("show");
  document.getElementById("createProfileForm").reset();
}

/* ============================================================================================================== */
/* CREATE NEW PROFILE */
/* ============================================================================================================== */

document
  .getElementById("createProfileForm")
  .addEventListener("submit", function (e) {
    e.preventDefault();

    const name = document.getElementById("newUsername").value.trim();
    const username = document.getElementById("newLoginUsername").value.trim();
    const password = document.getElementById("newPassword").value;

    if (profiles.find((p) => p.username === username)) {
      alert("Username already exists!");
      return;
    }

    const avatarClass = `avatar-${(profiles.length % 5) + 1}`;

    fetch("/create_user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        username: username,
        password: password,
        avatar: avatarClass,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok) {
          profiles.push(data.profile);
          renderProfiles();
          closeAddProfileModal();
          showMessage("✅ Profile created successfully!", "success");
        } else {
          alert("Error: " + (data.error || "unknown"));
        }
      })
      .catch((err) => {
        console.error("Error:", err);
        alert("Error creating profile");
      });
  });

/* ============================================================================================================== */
/* EXTRA */
/* ============================================================================================================== */
// Add this to your login page JS

window.addEventListener('click', (e) => {
    const apiModal = document.getElementById('API-data-modal');
    if (e.target === apiModal) {
        apiModal.classList.add('is-hidden');
    }
});

window.onclick = function (event) {
  const modal = document.getElementById("addProfileModal");
  if (event.target === modal) {
    closeAddProfileModal();
  }
};

document
  .getElementById("passwordInput")
  .addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      handleLogin();
    }
  });

loadProfiles();