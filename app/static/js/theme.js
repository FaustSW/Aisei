// ==============================================================================================================
// THEME SWITCHER - Load and apply themes
// ==============================================================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, starting theme setup...');
    loadThemes();
    loadSavedTheme();
});

// ==============================================================================================================
// LOAD THEMES - Fetch all themes from backend
// ==============================================================================================================

function loadThemes() {
    console.log('Fetching themes...');
    fetch('/api/themes')
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(themesList => {
            console.log('Themes loaded:', themesList);
            const dropdown = document.getElementById('theme-dropdown');
            if (!dropdown) {
                console.error('Dropdown element not found!');
                return;
            }

            dropdown.innerHTML = '';

            themesList.forEach(theme => {
                const option = document.createElement('option');
                option.value = theme.id;
                option.textContent = theme.name;
                dropdown.appendChild(option);
            });

            console.log('Dropdown populated with', themesList.length, 'themes');

            const savedTheme = localStorage.getItem('selectedTheme');
            if (savedTheme) {
                dropdown.value = savedTheme;
            }
        })
        .catch(error => {
            console.error('Error loading themes:', error);
            const dropdown = document.getElementById('theme-dropdown');
            if (dropdown) {
                dropdown.innerHTML = '<option value="">Error loading themes</option>';
            }
        });
}

// ==============================================================================================================
// CHANGE THEME - When user selects from dropdown
// ==============================================================================================================

function changeTheme() {
    const dropdown = document.getElementById('theme-dropdown');
    if (!dropdown) {
        console.error('Dropdown element not found!');
        return;
    }

    const themeId = dropdown.value;

    if (!themeId) {
        console.log('No theme selected');
        return;
    }

    console.log('Changing to theme:', themeId);

    fetch(`/api/theme/${themeId}`)
        .then(response => response.json())
        .then(theme => {
            console.log('Theme data received:', theme);
            applyTheme(theme);
            saveThemePreference(themeId);
        })
        .catch(error => console.error('Error loading theme:', error));
}

// ==============================================================================================================
// APPLY THEME - Change the body class to apply theme
// ==============================================================================================================

function applyTheme(theme) {
    console.log('Applying theme with class:', theme.class);
    document.body.className = document.body.className.replace(/\btheme-\S+/g, '').trim();

    if (theme.class) {
        document.body.classList.add(theme.class);
    }
}

// ==============================================================================================================
// SAVE THEME PREFERENCE - Store user's choice
// ==============================================================================================================

function saveThemePreference(themeId) {
    localStorage.setItem('selectedTheme', themeId);

    fetch('/api/save-theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ theme_id: themeId })
    })
    .catch(error => console.error('Error saving theme:', error));
}

// ==============================================================================================================
// LOAD SAVED THEME - Restore user's previously selected theme
// ==============================================================================================================

function loadSavedTheme() {
    const savedTheme = localStorage.getItem('selectedTheme');
    console.log('Saved theme from localStorage:', savedTheme);

    if (!savedTheme) {
        document.body.style.visibility = 'visible';
        return;
    }

    fetch(`/api/theme/${savedTheme}`)
        .then(response => response.json())
        .then(theme => {
            applyTheme(theme);

            const dropdown = document.getElementById('theme-dropdown');
            if (dropdown) {
                dropdown.value = savedTheme;
            }
        })
        .catch(error => console.error('Error loading saved theme:', error))
        .finally(() => {
            document.body.style.visibility = 'visible';
        });
}