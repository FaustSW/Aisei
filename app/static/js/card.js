document.addEventListener('DOMContentLoaded', () => {
    const cardInner = document.getElementById('card-inner');
    const frontText = document.getElementById('front-text');
    const backText = document.getElementById('back-text');
    const frontSentence = document.getElementById('front-sentence');
    const backTranslation = document.getElementById('back-translation');
    const buttons = document.querySelectorAll('.card-btn');

    const initial = (typeof INITIAL_STATS !== 'undefined') ? INITIAL_STATS : {};
    const initialPreviews = (typeof INITIAL_PREVIEW_INTERVALS !== 'undefined') ? INITIAL_PREVIEW_INTERVALS : {};

    let reviewStateId = typeof CURRENT_REVIEW_STATE_ID !== 'undefined' ? CURRENT_REVIEW_STATE_ID : null;
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

    function flipCard() {
        if (cardInner) cardInner.classList.toggle('is-flipped');
    }

    function flipToFront() {
        if (cardInner) cardInner.classList.remove('is-flipped');
    }

    function setCardContent(nextCard) {
        if (frontText) {
            frontText.textContent = nextCard.term || '';
        }

        if (backText) {
            backText.textContent = nextCard.english_gloss || '';
        }

        if (frontSentence) {
            frontSentence.textContent = nextCard.sentence || '';
            frontSentence.style.display = nextCard.sentence ? '' : 'none';
        }

        if (backTranslation) {
            backTranslation.textContent = nextCard.translation || '';
            backTranslation.style.display = nextCard.translation ? '' : 'none';
        }
    }

    function setDoneState() {
        if (frontText) {
            frontText.textContent = '🎉 Done!';
        }

        if (backText) {
            backText.textContent = 'No more cards due.';
        }

        if (frontSentence) {
            frontSentence.textContent = '';
            frontSentence.style.display = 'none';
        }

        if (backTranslation) {
            backTranslation.textContent = '';
            backTranslation.style.display = 'none';
        }
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

                flipToFront();

                setTimeout(() => {
                    if (data.next_card) {
                        setCardContent(data.next_card);
                        updatePreviewLabels(data.next_card.preview_intervals || {});
                        enableButtons();
                        reviewStateId = data.next_card.review_state_id;
                    } else {
                        setDoneState();
                        updatePreviewLabels({});
                        disableButtons();
                        reviewStateId = null;
                    }

                    isFlipping = false;
                }, 400);
            })
            .catch(err => {
                console.error('Request failed:', err);
                isFlipping = false;
            });
        });
    });

    function disableButtons() {
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('disabled');
        });
    }

    function enableButtons() {
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('disabled');
        });
    }

    function updatePreviewLabels(previews) {
        document.querySelectorAll('[data-rating-label]').forEach((el) => {
            const rating = el.dataset.ratingLabel;
            el.textContent = (previews[rating] && previews[rating].label) || '';
        });
    }

    function syncStats(stats) {
        totalReviewed = stats.total_reviewed || 0;
        reviewCounts = {
            again: (stats.counts && stats.counts.again) || 0,
            hard:  (stats.counts && stats.counts.hard)  || 0,
            good:  (stats.counts && stats.counts.good)  || 0,
            easy:  (stats.counts && stats.counts.easy)  || 0,
        };

        updateProgressBar();

        const totalNew = document.getElementById('total-new');
        const totalLearning = document.getElementById('total-learning');
        const totalReview = document.getElementById('total-review');

        if (totalNew) totalNew.innerText = stats.new_cards || 0;
        if (totalLearning) totalLearning.innerText = stats.learning_cards || 0;
        if (totalReview) totalReview.innerText = stats.review_cards || 0;
    }

    function updateProgressBar() {
        const cardsReviewedEl = document.getElementById('cards-reviewed');
        if (cardsReviewedEl) cardsReviewedEl.innerText = totalReviewed;

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