document.addEventListener('DOMContentLoaded', () => {
    const cardInner = document.getElementById('card-inner');
    const frontText = document.getElementById('front-text');
    const backText = document.getElementById('back-text');
    const frontSentence = document.getElementById('front-sentence');
    const backTranslation = document.getElementById('back-translation');
    const buttons = document.querySelectorAll('.card-btn');
    const frontAudioBtn = document.getElementById('front-audio-btn');
    const backAudioBtn = document.getElementById('back-audio-btn');
    const ratingButtonRow = document.getElementById('rating-button-row');

    const dailyNewLimitInput = document.getElementById('daily-new-limit-input');
    const dailyNewLimitApplyBtn = document.getElementById('daily-new-limit-apply');

    const initial = (typeof INITIAL_STATS !== 'undefined') ? INITIAL_STATS : {};
    const initialPreviews = (typeof INITIAL_PREVIEW_INTERVALS !== 'undefined') ? INITIAL_PREVIEW_INTERVALS : {};
    const initialDailyNewLimit = (typeof INITIAL_DAILY_NEW_LIMIT !== 'undefined') ? INITIAL_DAILY_NEW_LIMIT : 10;

    const logoutModal = document.getElementById('logout-modal');
    const signOutBtn = document.getElementById('sign-out-btn'); 
    const modalConfirm = document.getElementById('modal-confirm');
    const modalCancel = document.getElementById('modal-cancel');
    const modalMessage = document.getElementById('modal-message');
    const ratingDistributionBar = document.querySelector('.rating-distribution-bar.js-distribution-tooltip-target');

    let reviewStateId = typeof CURRENT_REVIEW_STATE_ID !== 'undefined' ? CURRENT_REVIEW_STATE_ID : null;
    let reviewCounts = {
        again: (initial.counts && initial.counts.again) || 0,
        hard:  (initial.counts && initial.counts.hard)  || 0,
        good:  (initial.counts && initial.counts.good)  || 0,
        easy:  (initial.counts && initial.counts.easy)  || 0,
    };
    let isFlipping = false;
    const distributionTooltip = createDistributionTooltip();

    function createDistributionTooltip() {
        const el = document.createElement('div');
        el.className = 'distribution-hover-tooltip';
        document.body.appendChild(el);
        return el;
    }

    function tooltipMarkup(counts) {
        return `
            <div class="distribution-tooltip-title">Rating Distribution</div>
            <div class="distribution-tooltip-row"><span class="distribution-tooltip-dot dot-again"></span>Again: <strong>${counts.again}</strong></div>
            <div class="distribution-tooltip-row"><span class="distribution-tooltip-dot dot-hard"></span>Hard: <strong>${counts.hard}</strong></div>
            <div class="distribution-tooltip-row"><span class="distribution-tooltip-dot dot-good"></span>Good: <strong>${counts.good}</strong></div>
            <div class="distribution-tooltip-row"><span class="distribution-tooltip-dot dot-easy"></span>Easy: <strong>${counts.easy}</strong></div>
        `;
    }

    function positionTooltip(mouseX, mouseY) {
        const pad = 12;
        const rect = distributionTooltip.getBoundingClientRect();
        let left = mouseX + pad;
        let top = mouseY + pad;

        if (left + rect.width > window.innerWidth - 8) {
            left = mouseX - rect.width - pad;
        }
        if (top + rect.height > window.innerHeight - 8) {
            top = mouseY - rect.height - pad;
        }

        distributionTooltip.style.left = `${Math.max(8, left)}px`;
        distributionTooltip.style.top = `${Math.max(8, top)}px`;
    }

    function bindDistributionTooltip(target) {
        if (!target || target.dataset.tooltipBound === '1') return;
        target.dataset.tooltipBound = '1';

        const show = (e) => {
            const counts = {
                again: Number(target.dataset.again || 0),
                hard: Number(target.dataset.hard || 0),
                good: Number(target.dataset.good || 0),
                easy: Number(target.dataset.easy || 0),
            };
            distributionTooltip.innerHTML = tooltipMarkup(counts);
            distributionTooltip.classList.add('is-visible');
            positionTooltip(e.clientX, e.clientY);
        };

        const move = (e) => positionTooltip(e.clientX, e.clientY);
        const hide = () => distributionTooltip.classList.remove('is-visible');

        target.addEventListener('mouseenter', show);
        target.addEventListener('mousemove', move);
        target.addEventListener('mouseleave', hide);
    }

    if (dailyNewLimitInput) {
        dailyNewLimitInput.value = initialDailyNewLimit;
    }

    bindDistributionTooltip(ratingDistributionBar);

    updateRatingDistribution();
    updatePreviewLabels(initialPreviews);

    if (!reviewStateId) {
        setDoneState();
        disableButtons();
    }

// 1. Replace the old speakText with this API-driven version
async function speakWithElevenLabs(text, voiceId) {
    if (!text || !text.trim()) return;

    try {
        // We call our Flask route instead of the browser's TTS engine
        const response = await fetch('/review/generate_audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text.trim(),
                voice_id: voiceId
            })
        });

        const data = await response.json();

        if (data.success && data.audio_url) {
            // Play the file returned by the server
            const audio = new Audio(data.audio_url);
            audio.play();
        } else {
            console.error('ElevenLabs Error:', data.error);
        }
    } catch (err) {
        console.error('Failed to communicate with audio service:', err);
    }
}

// 2. Update the event listeners to use the new function
if (frontAudioBtn) {
    frontAudioBtn.addEventListener('click', () => {
        const parts = [frontText?.textContent, frontSentence?.textContent]
            .filter(t => t && t.trim());
        
        // Using ID: U9jmr7kY6mMqS39kfA01 for the front
        speakWithElevenLabs(parts.join('. '), "U9jmr7kY6mMqS39kfA01");
    });
}

if (backAudioBtn) {
    backAudioBtn.addEventListener('click', () => {
        const parts = [backText?.textContent, backTranslation?.textContent]
            .filter(t => t && t.trim());
        
        // Using ID: rixsIpPlTphvsJd2mI03 for the back
        speakWithElevenLabs(parts.join('. '), "rixsIpPlTphvsJd2mI03");
    });
}

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

        if (frontAudioBtn) {
            frontAudioBtn.classList.remove('is-hidden');
        }

        if (backAudioBtn) {
            backAudioBtn.classList.remove('is-hidden');
        }

        if (ratingButtonRow) {
            ratingButtonRow.classList.remove('is-hidden');
        }
    }

    function setDoneState() {
        flipToFront();

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

        if (frontAudioBtn) {
            frontAudioBtn.classList.add('is-hidden');
        }

        if (backAudioBtn) {
            backAudioBtn.classList.add('is-hidden');
        }

        if (ratingButtonRow) {
            ratingButtonRow.classList.add('is-hidden');
        }

        // Show a link to the stats page in the front card's label area
        const frontLabel = document.querySelector('.card-front .btn-label');
        if (frontLabel) {
            frontLabel.innerHTML = '<a href="/stats/" class="done-stats-link">View your stats &#8594;</a>';
        }
    }

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
        reviewCounts = {
            again: (stats.counts && stats.counts.again) || 0,
            hard: (stats.counts && stats.counts.hard) || 0,
            good: (stats.counts && stats.counts.good) || 0,
            easy: (stats.counts && stats.counts.easy) || 0,
        };

        updateRatingDistribution();

        const totalNew = document.getElementById('total-new');
        const totalLearning = document.getElementById('total-learning');
        const totalReview = document.getElementById('total-review');

        if (totalNew) totalNew.innerText = stats.new_cards || 0;
        if (totalLearning) totalLearning.innerText = stats.learning_cards || 0;
        if (totalReview) totalReview.innerText = stats.review_cards || 0;

        if (dailyNewLimitInput && typeof stats.daily_new_limit !== 'undefined') {
            dailyNewLimitInput.value = stats.daily_new_limit;
        }
    }

    function applyNextCardResponse(nextCard) {
        function applyContent() {
            if (nextCard) {
                setCardContent(nextCard);
                updatePreviewLabels(nextCard.preview_intervals || {});
                enableButtons();
                reviewStateId = nextCard.review_state_id;
            } else {
                setDoneState();
                updatePreviewLabels({});
                disableButtons();
                reviewStateId = null;
            }
            isFlipping = false;
        }

        if (cardInner && cardInner.classList.contains('is-flipped')) {
            cardInner.addEventListener('transitionend', function handler(e) {
                if (e.propertyName !== 'transform' || e.target !== cardInner) return;
                cardInner.removeEventListener('transitionend', handler);
                applyContent();
            });
            flipToFront();
        } else {
            flipToFront();
            applyContent();
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
            if (e.target.closest('.card-btn') || e.target.closest('.audio-btn')) return;
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

                    applyNextCardResponse(data.next_card);
                })
                .catch(err => {
                    console.error('Request failed:', err);
                    isFlipping = false;
                });
        });
    });

    if (dailyNewLimitApplyBtn && dailyNewLimitInput) {
        const submitDailyNewLimit = () => {
            const rawValue = dailyNewLimitInput.value.trim();
            const parsed = parseInt(rawValue, 10);

            if (Number.isNaN(parsed)) {
                dailyNewLimitInput.value = initialDailyNewLimit;
                return;
            }

            fetch(SET_DAILY_NEW_LIMIT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    daily_new_limit: parsed,
                })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        console.error('Daily new limit error:', data.error);
                        return;
                    }

                    if (typeof data.daily_new_limit !== 'undefined') {
                        dailyNewLimitInput.value = data.daily_new_limit;
                    }

                    window.location.reload();
                })
                .catch(err => {
                    console.error('Request failed:', err);
                });
        };

        dailyNewLimitApplyBtn.addEventListener('click', submitDailyNewLimit);

        dailyNewLimitInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                submitDailyNewLimit();
            }
        });
    }

    if (signOutBtn) {
        signOutBtn.addEventListener('click', () => {
            // Pulling live numbers from the spans that syncStats updates
            const newCards = parseInt(document.getElementById('total-new')?.textContent) || 0;
            const learningCards = parseInt(document.getElementById('total-learning')?.textContent) || 0;
            const reviewCards = parseInt(document.getElementById('total-review')?.textContent) || 0;
            const totalRemaining = newCards + learningCards + reviewCards;

            if (totalRemaining > 0) {
                modalMessage.innerHTML = `You still have <strong>${totalRemaining}</strong> cards left today.<br>Are you sure you want to leave?`;
            } else {
                modalMessage.textContent = "You've finished your cards! See you next time?";
            }

            logoutModal.classList.remove('is-hidden');
        });
    }

    if (modalCancel) {
        modalCancel.addEventListener('click', () => {
            logoutModal.classList.add('is-hidden');
        });
    }

    if (modalConfirm) {
        modalConfirm.addEventListener('click', () => {
            window.location.href = "/logout";
        });
    }

    // Close modal if clicking the background overlay
    window.addEventListener('click', (e) => {
        if (e.target === logoutModal) {
            logoutModal.classList.add('is-hidden');
        }
    });

    function updateRatingDistribution() {
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

        if (ratingDistributionBar) {
            ratingDistributionBar.dataset.again = String(again);
            ratingDistributionBar.dataset.hard = String(hard);
            ratingDistributionBar.dataset.good = String(good);
            ratingDistributionBar.dataset.easy = String(easy);
        }

        if (segments.again) segments.again.style.width = `${(again / safeTotal) * 100}%`;
        if (segments.hard) segments.hard.style.width = `${(hard / safeTotal) * 100}%`;
        if (segments.good) segments.good.style.width = `${(good / safeTotal) * 100}%`;
        if (segments.easy) segments.easy.style.width = `${(easy / safeTotal) * 100}%`;
    }
});
