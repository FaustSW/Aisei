document.addEventListener('DOMContentLoaded', function () {
    const startBtn = document.getElementById('start-sim-time-btn');
    const controlsDiv = document.getElementById('sim-time-controls');
    const displaySpan = document.getElementById('sim-time-display');
    const plusBtn = document.getElementById('sim-time-plus');
    const minusBtn = document.getElementById('sim-time-minus');
    const customInput = document.getElementById('sim-time-custom');
    const applyBtn = document.getElementById('sim-time-apply');
    const resetBtn = document.getElementById('sim-time-reset');

    if (!startBtn || !controlsDiv || !displaySpan || !plusBtn || !minusBtn || !customInput || !applyBtn || !resetBtn) {
        return;
    }

    let realTimeInterval = null;

    startBtn.addEventListener('click', function () {
        fetch('/settings/start_sim_time', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                stopRealTimeClock();
                setSimModeUI(true);
                displaySpan.textContent = formatDateTime(data.sim_time);
                reloadReviewPage();
            });
    });

    plusBtn.addEventListener('click', function () {
        adjustSimTime(1);
    });

    minusBtn.addEventListener('click', function () {
        adjustSimTime(-1);
    });

    applyBtn.addEventListener('click', function () {
    const days = parseInt(customInput.value, 10);
    if (!isNaN(days)) adjustSimTime(days);
    });

    customInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            const days = parseInt(customInput.value, 10);
            if (!isNaN(days)) adjustSimTime(days);
        }
    });

    resetBtn.addEventListener('click', function () {
        fetch('/settings/reset_sim_time', { method: 'POST' })
            .then(res => res.json())
            .then(() => {
                setSimModeUI(false);
                startRealTimeClock();
                reloadReviewPage();
            });
    });

    fetch('/settings/check_sim_time', { method: 'GET' })
        .then(res => res.json())
        .then(data => {
            if (data.active) {
                setSimModeUI(true);
                displaySpan.textContent = formatDateTime(data.sim_time);
            } else {
                setSimModeUI(false);
                startRealTimeClock();
            }
        });

    function adjustSimTime(days) {
        fetch('/settings/adjust_sim_time', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days_delta: days })
        })
            .then(res => res.json())
            .then(data => {
                stopRealTimeClock();
                setSimModeUI(true);
                displaySpan.textContent = formatDateTime(data.sim_time);
                reloadReviewPage();
            });
    }

    function setSimModeUI(active) {
        if (active) {
            controlsDiv.classList.remove('is-hidden');
            startBtn.classList.add('is-hidden');
        } else {
            controlsDiv.classList.add('is-hidden');
            startBtn.classList.remove('is-hidden');
        }
    }

    function startRealTimeClock() {
        stopRealTimeClock();
        updateRealTimeDisplay();
        realTimeInterval = setInterval(updateRealTimeDisplay, 1000);
    }

    function stopRealTimeClock() {
        if (realTimeInterval) {
            clearInterval(realTimeInterval);
            realTimeInterval = null;
        }
    }

    function updateRealTimeDisplay() {
        displaySpan.textContent = formatDateTime(new Date());
    }

    function formatDateTime(value) {
        const dt = value instanceof Date ? value : new Date(value);
        return dt.toLocaleString();
    }

    function reloadReviewPage() {
        location.reload();
    }
});