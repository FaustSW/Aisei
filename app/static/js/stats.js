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
    const distributionTooltip = createDistributionTooltip();

    function parseCountsFromDataset(dataset) {
        return {
            again: Number(dataset.again || 0),
            hard: Number(dataset.hard || 0),
            good: Number(dataset.good || 0),
            easy: Number(dataset.easy || 0),
        };
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

    function createDistributionTooltip() {
        const el = document.createElement('div');
        el.className = 'distribution-hover-tooltip';
        document.body.appendChild(el);
        return el;
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
            distributionTooltip.innerHTML = tooltipMarkup(parseCountsFromDataset(target.dataset));
            distributionTooltip.classList.add('is-visible');
            positionTooltip(e.clientX, e.clientY);
        };
        const move = (e) => positionTooltip(e.clientX, e.clientY);
        const hide = () => distributionTooltip.classList.remove('is-visible');

        target.addEventListener('mouseenter', show);
        target.addEventListener('mousemove', move);
        target.addEventListener('mouseleave', hide);
    }

    document.querySelectorAll('.js-distribution-tooltip-target').forEach(bindDistributionTooltip);

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

            return `<div class="period-bar-group">
                        <div class="period-bar-stack js-distribution-tooltip-target"
                             style="height:${heightPct.toFixed(1)}%"
                             data-again="${week.again}"
                             data-hard="${week.hard}"
                             data-good="${week.good}"
                             data-easy="${week.easy}">
                            ${segHtml}
                        </div>
                        <span class="period-bar-total">${total > 0 ? total : ''}</span>
                        <span class="period-bar-label">${labelHtml}</span>
                    </div>`;
        });

        chartEl.innerHTML = bars.join('');
        chartEl.querySelectorAll('.js-distribution-tooltip-target').forEach(bindDistributionTooltip);
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
