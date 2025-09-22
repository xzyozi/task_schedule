document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const jobId = document.getElementById('job-id-hidden').value; // Get job_id from hidden input

    // Job Definition Elements
    const jobIdInput = document.getElementById('job-id');
    const jobFuncInput = document.getElementById('job-func');
    const jobDescriptionInput = document.getElementById('job-description');
    const jobEnabledCheckbox = document.getElementById('job-enabled');
    const triggerTypeInput = document.getElementById('trigger-type');
    const cronFieldsDiv = document.getElementById('cron-fields-detail');
    const intervalFieldsDiv = document.getElementById('interval-fields-detail');
    const cronMinuteInput = document.getElementById('cron-minute');
    const cronHourInput = document.getElementById('cron-hour');
    const cronDayOfWeekInput = document.getElementById('cron-day-of-week');
    const intervalWeeksInput = document.getElementById('interval-weeks');
    const intervalDaysInput = document.getElementById('interval-days');
    const intervalHoursInput = document.getElementById('interval-hours');
    const intervalMinutesInput = document.getElementById('interval-minutes');

    // Execution History Elements
    const executionHistoryBody = document.getElementById('execution-history-body');

    // Log Display Elements
    const logDisplaySection = document.getElementById('log-display-section');
    const logDetailIdSpan = document.getElementById('log-detail-id');
    const logStdoutCode = document.getElementById('log-stdout');
    const logStderrCode = document.getElementById('log-stderr');
    const copyLogBtn = document.getElementById('copy-log-btn');

    // --- Utility Functions ---

    function showTriggerFields(type) {
        cronFieldsDiv.classList.toggle('d-none', type !== 'cron');
        intervalFieldsDiv.classList.toggle('d-none', type !== 'interval');
    }

    function formatDateTime(isoString) {
        if (!isoString) return '---';
        try {
            const date = new Date(isoString);
            return date.toLocaleString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch (e) {
            return isoString;
        }
    }

    function formatDuration(start, end) {
        if (!start || !end) return '---';
        const startDate = new Date(start);
        const endDate = new Date(end);
        const durationMs = endDate - startDate;
        return (durationMs / 1000).toFixed(2);
    }

    // --- Fetch and Display Functions ---

    function fetchJobDetails() {
        fetch(`${API_BASE_URL}/jobs/${jobId}`)
            .then(response => {
                if (!response.ok) throw new Error('ジョブ定義の取得に失敗しました。');
                return response.json();
            })
            .then(job => {
                jobIdInput.value = job.id;
                jobFuncInput.value = job.func;
                jobDescriptionInput.value = job.description || '';
                jobEnabledCheckbox.checked = job.is_enabled;
                triggerTypeInput.value = job.trigger.type;

                showTriggerFields(job.trigger.type);

                if (job.trigger.type === 'cron') {
                    cronMinuteInput.value = job.trigger.minute || '*'
                    cronHourInput.value = job.trigger.hour || '*'
                    cronDayOfWeekInput.value = job.trigger.day_of_week || '*'
                } else if (job.trigger.type === 'interval') {
                    intervalWeeksInput.value = job.trigger.weeks || 0;
                    intervalDaysInput.value = job.trigger.days || 0;
                    intervalHoursInput.value = job.trigger.hours || 0;
                    intervalMinutesInput.value = job.trigger.minutes || 0;
                }
            })
            .catch(error => {
                console.error('Error fetching job details:', error);
                alert(`ジョブ詳細の取得に失敗しました: ${error.message}`);
            });
    }

    function fetchExecutionHistory() {
        fetch(`${API_BASE_URL}/api/jobs/${jobId}/history`)
            .then(response => {
                if (!response.ok) throw new Error('実行履歴の取得に失敗しました。');
                return response.json();
            })
            .then(history => {
                executionHistoryBody.innerHTML = '';
                if (history.length === 0) {
                    executionHistoryBody.innerHTML = `<tr><td colspan="6" class="text-center">このジョブの実行履歴はありません。</td></tr>`;
                    return;
                }
                history.forEach(log => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${log.id}</td>
                        <td><span class="badge bg-${log.status === 'COMPLETED' ? 'success' : log.status === 'FAILED' ? 'danger' : 'info'}">${log.status}</span></td>
                        <td>${formatDateTime(log.start_time)}</td>
                        <td>${formatDateTime(log.end_time)}</td>
                        <td>${formatDuration(log.start_time, log.end_time)}</td>
                        <td>
                            <button class="btn btn-sm btn-secondary btn-view-log" data-log-id="${log.id}" 
                                data-stdout="${log.stdout || ''}" data-stderr="${log.stderr || ''}">
                                ログ表示
                            </button>
                        </td>
                    `;
                    executionHistoryBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching execution history:', error);
                executionHistoryBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">実行履歴の読み込みに失敗しました。</td></tr>`;
            });
    }

    // --- Event Listeners ---

    executionHistoryBody.addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('btn-view-log')) {
            const logId = target.dataset.logId;
            const stdout = target.dataset.stdout;
            const stderr = target.dataset.stderr;

            logDetailIdSpan.textContent = logId;
            logStdoutCode.textContent = stdout;
            logStderrCode.textContent = stderr;
            logDisplaySection.style.display = 'block';

            // Scroll to log section
            logDisplaySection.scrollIntoView({ behavior: 'smooth' });
        }
    });

    copyLogBtn.addEventListener('click', function() {
        const activeTabContent = document.querySelector('#logTabs .nav-link.active').getAttribute('aria-controls');
        let textToCopy = '';
        if (activeTabContent === 'stdout-content') {
            textToCopy = logStdoutCode.textContent;
        } else if (activeTabContent === 'stderr-content') {
            textToCopy = logStderrCode.textContent;
        }

        if (navigator.clipboard) {
            navigator.clipboard.writeText(textToCopy).then(function() {
                alert('ログがクリップボードにコピーされました。');
            }, function(err) {
                console.error('ログのコピーに失敗しました: ', err);
                alert('ログのコピーに失敗しました。');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement("textarea");
            textArea.value = textToCopy;
            textArea.style.position = "fixed"; // Avoid scrolling to bottom
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                alert('ログがクリップボードにコピーされました。');
            } catch (err) {
                console.error('ログのコピーに失敗しました: ', err);
                alert('ログのコピーに失敗しました。');
            }
            document.body.removeChild(textArea);
        }
    });

    // --- Initial Load ---
    fetchJobDetails();
    fetchExecutionHistory();
});