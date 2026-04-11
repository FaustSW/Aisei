// ==============================================================================================================
// INITIALIZATION - Runs on page load
// ==============================================================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Seisei Settings...');
    
    // 1. Always load themes (Public)
    loadThemes();
    loadSavedTheme();

    // 2. Only load voices/settings if the elements exist (Gated)
    if (document.getElementById('voice-dropdown')) {
        loadVoices();
        loadSavedVoice();
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
        const voicesList = await response.json();

        dropdown.innerHTML = '';
        voicesList.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            dropdown.appendChild(option);
        });

        const savedVoice = localStorage.getItem('selectedVoice');
        if (savedVoice) dropdown.value = savedVoice;
    } catch (error) {
        console.error('Error loading voices:', error);
    }
}

function changeVoice() {
    const dropdown = document.getElementById('voice-dropdown');
    const voiceId = dropdown?.value;
    if (!voiceId) return;

    localStorage.setItem('selectedVoice', voiceId);
    fetch('/settings/save-voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_id: voiceId })
    });
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