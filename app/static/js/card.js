// card.js

document.addEventListener('DOMContentLoaded', () => {
    // 1. SELECT ELEMENTS
    const body = document.body;
    const themeToggle = document.querySelector('.header-btn[title="Toggle Theme"]');
    const cardInner = document.getElementById('card-inner');
    const buttons = document.querySelectorAll('.card-btn');
    const currentStreakText = document.getElementById('current-streak');
    const maxStreakText = document.getElementById('max-streak');

    // 2. STATE
    let currentStreak = 0;
    let maxStreak = 0;
    let barHeights = [0, 0, 0, 0];

    // 3. THEME LOGIC (works with base.html theme button)
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = body.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            body.setAttribute('data-theme', newTheme);
        });
    }

    // 4. FLIP LOGIC
    function flipCard() {
        if (cardInner) cardInner.classList.toggle('is-flipped');
    }

    // Spacebar Trigger
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            flipCard();
        }
    });

    // Side Click Trigger
    if (cardInner) {
        cardInner.addEventListener('click', (e) => {
            // Stop flip if a button was clicked
            if (e.target.closest('.card-btn')) return;

            const rect = cardInner.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const cardWidth = rect.width;

            // Flip if click is near the left or right edges
            if (x < cardWidth * 0.2 || x > cardWidth * 0.8) {
                flipCard();
            }
        });
    }

    // 5. STREAK & BAR LOGIC
    buttons.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            // Increase corresponding bar
            barHeights[index] = Math.min(barHeights[index] + 10, 100);

            updateDisplay();

            // Auto-flip back to front after picking an answer
            setTimeout(flipCard, 200);

            // Send action to backend
            const action = btn.dataset.action;
            if (typeof HANDLE_CARD_URL !== 'undefined') {
                fetch(HANDLE_CARD_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action })
                })
                .then(res => res.json())
                .then(data => console.log(data.message))
                .catch(err => console.error('Card fetch error:', err));
            }
        });
    });

    function updateDisplay() {
        if (currentStreakText) currentStreakText.innerText = currentStreak;
        if (maxStreakText) maxStreakText.innerText = maxStreak;

        barHeights.forEach((height, i) => {
            const bar = document.getElementById(`bar-${i}`);
            if (bar) bar.style.height = height + '%';
        });
    }
});