// card.js

document.addEventListener('DOMContentLoaded', () => {
    const cardInner = document.getElementById('card-inner');
    const frontText = document.getElementById('front-text');
    const backText = document.getElementById('back-text');
    const frontSentence = document.getElementById('front-sentence');
    const backTranslation = document.getElementById('back-translation');
    const buttons = document.querySelectorAll('.card-btn');
    const currentStreakText = document.getElementById('current-streak');
    const maxStreakText = document.getElementById('max-streak');

    const initial = (typeof INITIAL_STATS !== 'undefined') ? INITIAL_STATS : {};
    const initialPreviews = (typeof INITIAL_PREVIEW_INTERVALS !== 'undefined') ? INITIAL_PREVIEW_INTERVALS : {};

    let reviewStateId = typeof CURRENT_REVIEW_STATE_ID !== 'undefined' ? CURRENT_REVIEW_STATE_ID : null;
    let currentStreak = initial.current_streak || 0;
    let maxStreak = initial.max_streak || 0;
    let totalReviewed = initial.total_reviewed || 0;
    let reviewCounts = {
        again: (initial.counts && initial.counts.again) || 0,
        hard:  (initial.counts && initial.counts.hard)  || 0,
        good:  (initial.counts && initial.counts.good)  || 0,
        easy:  (initial.counts && initial.counts.easy)  || 0,
    };
    let isFlipping = false;

    updateProgressBar();
    updatePreviewLabels(initialPreviews);

    if (currentStreakText) currentStreakText.innerText = currentStreak;
    if (maxStreakText) maxStreakText.innerText = maxStreak;

    function flipCard() {
        if (cardInner) cardInner.classList.toggle('is-flipped');
    }

    function flipToFront() {
        if (cardInner) cardInner.classList.remove('is-flipped');
    }

    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            flipCard();
        }
    });

    if (cardInner) {
        cardInner.addEventListener('click', (e) => {
            if (e.target.closest('.card-btn')) return;
            const rect = cardInner.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const cardWidth = rect.width;
            if (x < cardWidth * 0.2 || x > cardWidth * 0.8) {
                flipCard();
            }
        });
    }

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (isFlipping || !reviewStateId) return;
            isFlipping = true;

            const rating = parseInt(btn.dataset.action, 10);

            fetch(RATE_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    review_state_id: reviewStateId,
                    rating: rating
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    console.error('Rating error:', data.error);
                    isFlipping = false;
                    return;
                }

                if (data.stats) {
                    syncStats(data.stats);
                }

                if (data.next_card) {
                    flipToFront();

                    setTimeout(() => {
                        frontText.textContent = data.next_card.term || '';
                        backText.textContent = data.next_card.english_gloss || '';

                        if (frontSentence) {
                            frontSentence.textContent = data.next_card.sentence || '';
                            frontSentence.style.display = data.next_card.sentence ? '' : 'none';
                        }

                        if (backTranslation) {
                            backTranslation.textContent = data.next_card.translation || '';
                            backTranslation.style.display = data.next_card.translation ? '' : 'none';
                        }

                        updatePreviewLabels(data.next_card.preview_intervals || {});
                        enableButtons();

                        reviewStateId = data.next_card.review_state_id;
                        isFlipping = false;
                    }, 400);
                } else {
                    flipToFront();

                    setTimeout(() => {
                        frontText.textContent = '🎉 Done!';
                        backText.textContent = 'No more cards due.';

                        if (frontSentence) {
                            frontSentence.textContent = '';
                            frontSentence.style.display = 'none';
                        }

                        if (backTranslation) {
                            backTranslation.textContent = '';
                            backTranslation.style.display = 'none';
                        }

                        updatePreviewLabels({});
                        reviewStateId = null;
                        disableButtons();
                        isFlipping = false;
                    }, 400);
                }
            })
            .catch(err => {
                console.error('Card fetch error:', err);
                isFlipping = false;
            });
        });
    });

    function updatePreviewLabels(previews) {
        document.querySelectorAll('[data-rating-label]').forEach((el) => {
            const rating = el.dataset.ratingLabel;
            el.textContent = (previews && previews[rating] && previews[rating].label) ? previews[rating].label : '';
        });
    }

    function disableButtons() {
        buttons.forEach((b) => {
            b.disabled = true;
        });
    }

    function enableButtons() {
        buttons.forEach((b) => {
            b.disabled = false;
        });
    }

    function syncStats(stats) {
        totalReviewed = stats.total_reviewed || 0;
        currentStreak = stats.current_streak || 0;
        maxStreak = stats.max_streak || 0;
        reviewCounts = {
            again: (stats.counts && stats.counts.again) || 0,
            hard:  (stats.counts && stats.counts.hard)  || 0,
            good:  (stats.counts && stats.counts.good)  || 0,
            easy:  (stats.counts && stats.counts.easy)  || 0,
        };

        if (currentStreakText) currentStreakText.innerText = currentStreak;
        if (maxStreakText) maxStreakText.innerText = maxStreak;

        updateProgressBar();

        const totalNew = document.getElementById('total-new');
        const totalLearning = document.getElementById('total-learning');
        const totalReview = document.getElementById('total-review');

        if (totalNew) totalNew.innerText = stats.new_cards || 0;
        if (totalLearning) totalLearning.innerText = stats.learning_cards || 0;
        if (totalReview) totalReview.innerText = stats.review_cards || 0;
    }

    function updateProgressBar() {
        const totalCards = totalReviewed;
        const cardsReviewedEl = document.getElementById('cards-reviewed');
        const totalCardsEl = document.getElementById('total-cards');

        if (cardsReviewedEl) cardsReviewedEl.innerText = totalReviewed;
        if (totalCardsEl) totalCardsEl.innerText = totalCards;

        const again = reviewCounts.again || 0;
        const hard = reviewCounts.hard || 0;
        const good = reviewCounts.good || 0;
        const easy = reviewCounts.easy || 0;

        const segments = {
            again: document.getElementById('segment-again'),
            hard: document.getElementById('segment-hard'),
            good: document.getElementById('segment-good'),
            easy: document.getElementById('segment-easy'),
        };

        const safeTotal = Math.max(again + hard + good + easy, 1);

        if (segments.again) segments.again.style.width = `${(again / safeTotal) * 100}%`;
        if (segments.hard) segments.hard.style.width = `${(hard / safeTotal) * 100}%`;
        if (segments.good) segments.good.style.width = `${(good / safeTotal) * 100}%`;
        if (segments.easy) segments.easy.style.width = `${(easy / safeTotal) * 100}%`;
    }
});