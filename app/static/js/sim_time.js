document.addEventListener('DOMContentLoaded', function () {
    const startBtn = document.getElementById('start-sim-time-btn');
    const controlsDiv = document.getElementById('sim-time-controls');
    const displaySpan = document.getElementById('sim-time-display');
    const plusBtn = document.getElementById('sim-time-plus');
    const minusBtn = document.getElementById('sim-time-minus');
    const customInput = document.getElementById('sim-time-custom');
    const setBtn = document.getElementById('sim-time-set');
    const resetBtn = document.getElementById('sim-time-reset');

    if (!startBtn || !controlsDiv || !displaySpan || !plusBtn || !minusBtn || !customInput || !setBtn || !resetBtn) {
        return;
    }

    startBtn.addEventListener('click', function () {
        controlsDiv.style.display = 'block';

        fetch('/review/start_sim_time', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                displaySpan.textContent = formatSimTime(data.sim_time, data.active);
                reloadReviewPage();
            });
    });

    plusBtn.addEventListener('click', function () {
        adjustSimTime(1);
    });

    minusBtn.addEventListener('click', function () {
        adjustSimTime(-1);
    });

    setBtn.addEventListener('click', function () {
        const days = parseInt(customInput.value, 10);
        if (!isNaN(days)) {
            adjustSimTime(days);
        }
    });

    resetBtn.addEventListener('click', function () {
        fetch('/review/reset_sim_time', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                displaySpan.textContent = formatSimTime(data.sim_time, data.active);
                reloadReviewPage();
            });
    });

    fetch('/review/check_sim_time', { method: 'GET' })
        .then(res => res.json())
        .then(data => {
            if (data.active) {
                controlsDiv.style.display = 'block';
            }
            displaySpan.textContent = formatSimTime(data.sim_time, data.active);
        });

    function adjustSimTime(days) {
        fetch('/review/adjust_sim_time', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days_delta: days })
        })
            .then(res => res.json())
            .then(data => {
                controlsDiv.style.display = 'block';
                displaySpan.textContent = formatSimTime(data.sim_time, data.active);
                reloadReviewPage();
            });
    }

    function formatSimTime(isoString, active) {
        if (!active || !isoString) {
            return 'Real time';
        }

        const dt = new Date(isoString);
        return dt.toLocaleString();
    }

    function reloadReviewPage() {
        location.reload();
    }
});