// ==============================================================================================================
// INITIALIZATION - Runs on page load
// ==============================================================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadThemes();
    loadSavedTheme();

    if (document.getElementById('voice-dropdown')) {
        loadVoices();
    }

    if (document.getElementById('newOpenAIKey')) {
        loadSavedAPIKeys(); 
    }

    if (document.getElementById('voice-speed-slider')) {
        initVoiceSpeedSlider();
    }

    setupModalLogic();
});

// ==============================================================================================================
// THEME LOGIC
// ==============================================================================================================

async function loadThemes() {
    const dropdown = document.getElementById('theme-dropdown');
    if (!dropdown) return;

    try {
        const response = await fetch('/settings/themes'); 
        const themesList = await response.json();

        dropdown.innerHTML = '';
        themesList.forEach(theme => {
            const option = document.createElement('option');
            option.value = theme.id;
            option.textContent = theme.name;
            dropdown.appendChild(option);
        });

        const savedTheme = localStorage.getItem('selectedTheme');
        if (savedTheme) dropdown.value = savedTheme;

    } catch (error) {
        console.error('Error loading themes:', error);
        dropdown.innerHTML = '<option value="">Error loading themes</option>';
    }
}

function changeTheme() {
    const dropdown = document.getElementById('theme-dropdown');
    const themeId = dropdown?.value;
    if (!themeId) return;

    fetch(`/settings/theme/${themeId}`)
        .then(response => response.json())
        .then(theme => {
            applyTheme(theme);
            localStorage.setItem('selectedTheme', themeId);
            fetch('/settings/save-theme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme_id: themeId })
            });
        });
}

function applyTheme(theme) {
    if (!theme.class) return;
    document.body.className = document.body.className.replace(/\btheme-\S+/g, '').trim();
    document.body.classList.add(theme.class);
}

function loadSavedTheme() {
    const savedTheme = localStorage.getItem('selectedTheme');
    if (!savedTheme) {
        document.body.style.visibility = 'visible';
        return;
    }

    fetch(`/settings/theme/${savedTheme}`)
        .then(response => response.json())
        .then(theme => applyTheme(theme))
        .finally(() => document.body.style.visibility = 'visible');
}

// ==============================================================================================================
// VOICE LOGIC (Gated)
// ==============================================================================================================

async function loadVoices() {
    const dropdown = document.getElementById('voice-dropdown');
    if (!dropdown) return;

    try {
        const response = await fetch('/settings/voices');
        const data = await response.json();

        const voicesList = data.voices || [];
        const selectedVoiceId = data.selected_voice_id || null;

        dropdown.innerHTML = '';

        voicesList.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            dropdown.appendChild(option);
        });

        const localVoice = localStorage.getItem('selectedVoice');
        const effectiveVoice = localVoice || selectedVoiceId;

        if (effectiveVoice) {
            dropdown.value = effectiveVoice;
            localStorage.setItem('selectedVoice', effectiveVoice);
        }
    } catch (error) {
        console.error('Error loading voices:', error);
    }
}

function changeVoice() {
    const dropdown = document.getElementById('voice-dropdown');
    const voiceId = dropdown?.value;
    if (!voiceId) return;

    fetch('/settings/save-voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_id: voiceId })
    })
        .then(res => res.json())
        .then(data => {
            if (data.ok && data.voice_id) {
                localStorage.setItem('selectedVoice', data.voice_id);
            } else {
                console.error('Error saving voice:', data.error);
            }
        })
        .catch(error => {
            console.error('Error saving voice:', error);
        });
}

function loadSavedVoice() {
    const dropdown = document.getElementById('voice-dropdown');
    if (!dropdown) return;

    const savedVoice = localStorage.getItem('selectedVoice');
    if (savedVoice) dropdown.value = savedVoice;
}

// ==============================================================================================================
// MODAL LOGIC
// ==============================================================================================================

function setupModalLogic() {
    console.log('setupModalLogic running, wrapper:', document.querySelector('.settings'), 'modal:', document.getElementById('settings-modal'));
    // ... rest of function
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const cancelBtn = document.querySelector('#settings-modal .btn-cancel');

    // Attach listener to the wrapper div since it sits on top of the button
    const settingsWrapper = settingsBtn?.closest('.settings');
    if (settingsWrapper && settingsModal) {
        settingsWrapper.addEventListener('click', () => settingsModal.classList.remove('is-hidden'));
    }

    if (settingsBtn && settingsModal) {
        settingsBtn.addEventListener('click', () => settingsModal.classList.remove('is-hidden'));
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent the wrapper click from re-opening it
            settingsModal.classList.add('is-hidden');
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.classList.add('is-hidden');
    });
}

function loadSavedVoice() {
    const dropdown = document.getElementById('voice-dropdown');
    if (!dropdown) return;

    const savedVoice = localStorage.getItem('selectedVoice');
    if (savedVoice) dropdown.value = savedVoice;
}

// ==============================================================================================================
// API LOGIC (Gated)
// ==============================================================================================================
function saveAPIKeys() {
    const openaiKey = document.getElementById("newOpenAIKey").value.trim();
    const elevenlabsKey = document.getElementById("ElevenLabsKey").value.trim();

    const saveBtn = document.querySelector("#settings-modal .btn-create");
    saveBtn.textContent = "Saving...";
    saveBtn.disabled = true;

    const body = {};
    if (openaiKey) body.openai_key = openaiKey;       
    if (elevenlabsKey) body.elevenlabs_key = elevenlabsKey;

    if (Object.keys(body).length === 0) {
        alert("No changes to save.");
        return;
    }

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
            alert("API keys saved successfully!");
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
    saveBtn.textContent = "Save & Continue";
    saveBtn.disabled = false;
}

function loadSavedAPIKeys() {
    fetch('/api-keys-status')
        .then(res => res.json())
        .then(data => {
            const MASK = '••••••••••••••••';
            const openaiInput = document.getElementById('newOpenAIKey');
            const elevenlabsInput = document.getElementById('ElevenLabsKey');

            if (data.has_openai_key) openaiInput.placeholder = MASK;
            if (data.has_elevenlabs_key) elevenlabsInput.placeholder = MASK;
        })
        .catch(err => console.error('Error loading API key status:', err));
}

// ==============================================================================================================
// VOICE SPEED LOGIC
// ==============================================================================================================

function initVoiceSpeedSlider() {
    const slider = document.getElementById('voice-speed-slider');
    const label  = document.getElementById('voice-speed-label');
    if (!slider) return;

    // Restore from localStorage, fall back to server-supplied initial value
    const saved = localStorage.getItem('voiceSpeed');
    const initial = (saved !== null) ? parseFloat(saved) : (window.INITIAL_VOICE_SPEED ?? 1.0);
    slider.value = initial;
    if (label) label.textContent = parseFloat(initial).toFixed(2) + '×';

    slider.addEventListener('input', () => {
        if (label) label.textContent = parseFloat(slider.value).toFixed(2) + '×';
    });

    slider.addEventListener('change', saveVoiceSpeed);
}

function saveVoiceSpeed() {
    const slider = document.getElementById('voice-speed-slider');
    if (!slider) return;

    const speed = parseFloat(slider.value);

    fetch('/settings/change_voice_speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_speed: speed })
    })
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                localStorage.setItem('voiceSpeed', data.voice_speed);
            } else {
                console.error('Error saving voice speed:', data.error);
            }
        })
        .catch(err => console.error('Error saving voice speed:', err));
}

