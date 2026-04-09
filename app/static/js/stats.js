/**
 * stats.js
 *
 * Handles the interactive period-selector bar chart on the stats page.
 * Fetches data from /stats/history?period=<1m|3m|all> and renders a
 * stacked bar chart using only HTML/CSS.
 */

document.addEventListener('DOMContentLoaded', () => {
    const periodBtns = document.querySelectorAll('.period-btn');
    const chartEl    = document.getElementById('period-chart');
    const avgEl      = document.getElementById('period-avg-per-day');
    const sessionsEl = document.getElementById('period-sessions');

    if (!chartEl) return;

    let currentPeriod = '1m';

    //  Load data ──────────────────────────────────────────────────────────

    function loadPeriod(period) {
        currentPeriod = period;

        chartEl.innerHTML = '<div class="period-chart-loading">Loading\u2026</div>';
        if (avgEl) avgEl.textContent = '\u2014';
        if (sessionsEl) sessionsEl.textContent = '\u2014';

        fetch(`${HISTORY_URL}?period=${encodeURIComponent(period)}`)
            .then(r => r.json())
            .then(data => renderChart(data))
            .catch(() => {
                chartEl.innerHTML = '<div class="period-chart-loading">Failed to load data.</div>';
            });
    }

    // ── Render ─────────────────────────────────────────────────────────────

    function renderChart(data) {
        const weeks = data.weeks || [];

        if (avgEl)      avgEl.textContent      = data.avg_per_day !== undefined ? data.avg_per_day : '\u2014';
        if (sessionsEl) sessionsEl.textContent = data.sessions    !== undefined ? data.sessions    : '\u2014';

        if (weeks.length === 0) {
            chartEl.innerHTML = '<div class="period-chart-empty">No review data for this period.</div>';
            return;
        }

        
        const totals = weeks.map(w => w.again + w.hard + w.good + w.easy);
        const maxTotal = Math.max(...totals, 1);

        
        const bars = weeks.map(week => {
            const total = week.again + week.hard + week.good + week.easy;
            const heightPct = Math.max((total / maxTotal) * 100, total > 0 ? 2 : 0);

            const segments = [
                { key: 'again', color: 'segment-again', count: week.again },
                { key: 'hard',  color: 'segment-hard',  count: week.hard  },
                { key: 'good',  color: 'segment-good',  count: week.good  },
                { key: 'easy',  color: 'segment-easy',  count: week.easy  },
            ];

            const segHtml = segments
                .filter(s => s.count > 0)
                .map(s => {
                    const segPct = (s.count / Math.max(total, 1)) * 100;
                    return `<div class="period-bar-segment ${s.color}"
                                 style="height:${segPct.toFixed(1)}%"
                                 title="${s.key.charAt(0).toUpperCase() + s.key.slice(1)}: ${s.count}"></div>`;
                })
                .join('');

            const labelParts = week.label.split(' \u2013 ');
            const labelHtml = labelParts.length === 2
                ? `${labelParts[0]}<br>${labelParts[1]}`
                : week.label;

            const tooltip = `Again: ${week.again}  Hard: ${week.hard}  Good: ${week.good}  Easy: ${week.easy}`;

            return `<div class="period-bar-group">
                        <div class="period-bar-stack" style="height:${heightPct.toFixed(1)}%" title="${tooltip}">
                            ${segHtml}
                        </div>
                        <span class="period-bar-total">${total > 0 ? total : ''}</span>
                        <span class="period-bar-label">${labelHtml}</span>
                    </div>`;
        });

        chartEl.innerHTML = bars.join('');
    }

    // ── Button handlers ────────────────────────────────────────────────────

    periodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            periodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadPeriod(btn.dataset.period);
        });
    });

    
    loadPeriod(currentPeriod);
});
