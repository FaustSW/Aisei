// 1. SELECT ELEMENTS
const body = document.body;
const themeToggle = document.getElementById('theme-toggle');
const cardInner = document.getElementById('card-inner');
const buttons = document.querySelectorAll('.card-btn');
const currentStreakText = document.getElementById('current-streak');
const maxStreakText = document.getElementById('max-streak');

// 2. STATE
let currentStreak = 0;
let maxStreak = 0;
let barHeights = [0, 0, 0, 0];

// 3. THEME LOGIC
themeToggle.addEventListener('click', () => {
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    body.setAttribute('data-theme', newTheme);
});

// 4. FLIP LOGIC
function flipCard() {
    if (cardInner) {
        cardInner.classList.toggle('is-flipped');
    }
}

// Spacebar Trigger
window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
        e.preventDefault(); 
        flipCard();
    }
});

// Side Click Trigger
cardInner.addEventListener('click', (e) => {
    // Stop flip if a button was clicked
    if (e.target.closest('.card-btn')) return;

    const rect = cardInner.getBoundingClientRect();
    const x = e.clientX - rect.left; 
    const cardWidth = rect.width;

    if (x < cardWidth * 0.2 || x > cardWidth * 0.8) {
        flipCard();
    }
});

// 5. STREAK & BAR LOGIC
buttons.forEach((btn, index) => {
    btn.addEventListener('click', () => {
        /*
        // Increment streak 
        currentStreak++;
        if (currentStreak > maxStreak) {
            maxStreak = currentStreak;
        }
        */

        // Increase corresponding bar
        barHeights[index] = Math.min(barHeights[index] + 10, 100);

        updateDisplay();
        
        // Auto-flip back to front after picking an answer
        setTimeout(flipCard, 200); 
    });
});

function updateDisplay() {
    currentStreakText.innerText = currentStreak;
    maxStreakText.innerText = maxStreak;

    barHeights.forEach((height, i) => {
        const bar = document.getElementById(`bar-${i}`);
        if (bar) {
            bar.style.height = height + '%';
        }
    });
}

// Returns button response to Flask backend
document.querySelectorAll('.card-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const action = btn.dataset.action;

        fetch('/handle_card_response', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
        });
    });
});
