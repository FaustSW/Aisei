// static/js/header.js

document.addEventListener("DOMContentLoaded", function() {
    const themeBtn = document.querySelector('.header-btn[title="Toggle Theme"]');
    const settingsBtn = document.querySelector('.header-btn[title="Settings"]');

    themeBtn.addEventListener('click', () => {
        const body = document.body;

        // Remove all theme classes first
        body.classList.remove('theme-light','theme-dark','theme-green','theme-red','theme-blue');

        // Cycle themes (simple example)
        if (!body.classList.contains('theme-dark')) {
            body.classList.add('theme-dark');
        } else if (!body.classList.contains('theme-green')) {
            body.classList.add('theme-green');
        } else {
            body.classList.add('theme-light');
        }
        // TODO: Implement a more robust theme cycling or selection mechanism

    localStorage.setItem('theme', body.className); // optional
    });

    // SETTINGS BUTTON
    settingsBtn.addEventListener('click', () => {
        // Open a settings modal or navigate
        alert("Settings modal would open here!");
    });

    // Optional: load saved theme on page load
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.body.dataset.theme = savedTheme;
    }
});