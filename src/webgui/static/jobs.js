// src/webgui/static/jobs.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const jobsListBody = document.getElementById('jobs-list-body');
    const jobForm = document.getElementById('job-form');
    const jobIdInput = document.getElementById('job-id');
    const jobFuncInput = document.getElementById('job-func');
    const jobDescriptionInput = document.getElementById('job-description');
    const jobEnabledCheckbox = document.getElementById('job-enabled');
    const triggerTypeSelect = document.getElementById('trigger-type');
    const cronFieldsDiv = document.getElementById('cron-fields');
    const intervalFieldsDiv = document.getElementById('interval-fields');
    const clearFormBtn = document.getElementById('clear-form-btn');
    const jobFormTitle = document.getElementById('job-form-title');
    const jobIdHidden = document.getElementById('job-id-hidden');

    // Cron fields
    const cronMinuteInput = document.getElementById('cron-minute');
    const cronHourInput = document.getElementById('cron-hour');
    const cronDayOfWeekInput = document.getElementById('cron-day-of-week');

    // Interval fields
    const intervalWeeksInput = document.getElementById('interval-weeks');
    const intervalDaysInput = document.getElementById('interval-days');
    const intervalHoursInput = document.getElementById('interval-hours');
    const intervalMinutesInput = document.getElementById('interval-minutes');

    // --- Utility Functions ---

    function showTriggerFields(type) {
        cronFieldsDiv.classList.toggle('d-none', type !== 'cron');
        intervalFieldsDiv.classList.toggle('d-none', type !== 'interval');
    }

    function clearForm() {
        jobForm.reset();
        jobIdInput.value = '';
        jobFuncInput.value = '';
        jobDescriptionInput.value = '';
        jobEnabledCheckbox.checked = true;
        triggerTypeSelect.value = 'cron';
        cronMinuteInput.value = '*'
        cronHourInput.value = '*'
        cronDayOfWeekInput.value = '*'
        intervalWeeksInput.value = 0;
        intervalDaysInput.value = 0;
        intervalHoursInput.value = 0;
        intervalMinutesInput.value = 5;
        jobFormTitle.textContent = '新規ジョブ作成';
        jobIdInput.readOnly = false;
        jobIdHidden.value = '';
        showTriggerFields('cron');
    }

    function populateFormForEdit(jobId) {
        // Fetch the job *definition* from the DB to edit it
        fetch(`${API_BASE_URL}/jobs/${jobId}`)
            .then(response => {
                if (!response.ok) throw new Error('ジョブ定義の取得に失敗しました。');
                return response.json();
            })
            .then(job => {
                jobIdInput.value = job.id;
                jobIdInput.readOnly = true;
                jobIdHidden.value = job.id;
                jobFuncInput.value = job.func;
                jobDescriptionInput.value = job.description || '';
                jobEnabledCheckbox.checked = job.is_enabled;
                triggerTypeSelect.value = job.trigger.type;

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
                jobFormTitle.textContent = `ジョブ編集: ${job.id}`;
                window.scrollTo(0, document.body.scrollHeight); // Scroll to form
            })
            .catch(error => {
                console.error('Error fetching job for edit:', error);
                alert(`ジョブの編集データを取得できませんでした: ${error.message}`);
            });
    }

    function formatTrigger(trigger) {
        if (!trigger) return 'N/A';
        if (trigger.type === 'cron') {
            return `Cron: ${trigger.minute || '*'} ${trigger.hour || '*'} * * ${trigger.day_of_week || '*'}`;
        } else if (trigger.type === 'interval') {
            let parts = [];
            if (trigger.weeks) parts.push(`${trigger.weeks}w`);
            if (trigger.days) parts.push(`${trigger.days}d`);
            if (trigger.hours) parts.push(`${trigger.hours}h`);
            if (trigger.minutes) parts.push(`${trigger.minutes}m`);
            if (trigger.seconds) parts.push(`${trigger.seconds}s`);
            return `Interval: ${parts.join(' ')}`;
        }
        return 'Unknown';
    }
    
    function formatDateTime(isoString) {
        if (!isoString) return '---';
        try {
            const date = new Date(isoString);
            return date.toLocaleString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch (e) {
            return isoString; // Return original string if parsing fails
        }
    }


    // --- Main Fetch and Display Function ---

    function fetchAndDisplayJobs() {
        // Fetch the live job status from the scheduler
        fetch(`${API_BASE_URL}/scheduler/jobs`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(jobs => {
                jobsListBody.innerHTML = '';
                if (jobs.length === 0) {
                    jobsListBody.innerHTML = `<tr><td colspan="6" class="text-center">スケジュールされたジョブはありません。</td></tr>`;
                    return;
                }
                jobs.forEach(job => {
                    const isPaused = job.next_run_time === null;
                    const row = document.createElement('tr');

                    row.innerHTML = `
                        <td>
                            <div class="form-check form-switch">
                                <input class="form-check-input status-toggle" type="checkbox" role="switch" 
                                       data-job-id="${job.id}" ${isPaused ? '' : 'checked'}>
                                <label class="form-check-label">
                                    ${isPaused ? '<span class="badge bg-secondary">停止中</span>' : '<span class="badge bg-success">実行中</span>'}
                                </label>
                            </div>
                        </td>
                        <td>${job.id}</td>
                        <td>${formatTrigger(job.trigger)}</td>
                        <td>${formatDateTime(job.next_run_time)}</td>
                        <td class="text-break">${job.func}</td>
                        <td>
                            <button class="btn btn-sm btn-primary btn-run" data-job-id="${job.id}" title="今すぐ実行">実行</button>
                            <button class="btn btn-sm btn-info btn-edit" data-job-id="${job.id}" title="編集">編集</button>
                            <button class="btn btn-sm btn-danger btn-delete" data-job-id="${job.id}" title="削除">削除</button>
                        </td>
                    `;
                    jobsListBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching scheduled jobs:', error);
                jobsListBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">ジョブの読み込みに失敗しました。</td></tr>`;
            });
    }

    // --- Event Listeners ---

    triggerTypeSelect.addEventListener('change', (event) => {
        showTriggerFields(event.target.value);
    });

    clearFormBtn.addEventListener('click', clearForm);

    // Form submission for creating/updating job *definitions*
    jobForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const jobId = jobIdInput.value;
        const isEdit = !!jobIdHidden.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${API_BASE_URL}/jobs/${jobIdHidden.value}` : `${API_BASE_URL}/jobs`;

        const jobData = {
            id: jobId,
            func: jobFuncInput.value,
            description: jobDescriptionInput.value,
            is_enabled: jobEnabledCheckbox.checked,
            trigger: { type: triggerTypeSelect.value },
            // Default values, can be expanded later
            args: [],
            kwargs: {},
            max_instances: 3,
            coalesce: true,
            misfire_grace_time: 3600,
            replace_existing: true,
        };

        if (jobData.trigger.type === 'cron') {
            jobData.trigger.minute = cronMinuteInput.value;
            jobData.trigger.hour = cronHourInput.value;
            jobData.trigger.day_of_week = cronDayOfWeekInput.value;
        } else if (jobData.trigger.type === 'interval') {
            jobData.trigger.weeks = parseInt(intervalWeeksInput.value) || 0;
            jobData.trigger.days = parseInt(intervalDaysInput.value) || 0;
            jobData.trigger.hours = parseInt(intervalHoursInput.value) || 0;
            jobData.trigger.minutes = parseInt(intervalMinutesInput.value) || 0;
        }

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jobData),
        })
        .then(response => {
            if (!response.ok) return response.json().then(err => { throw new Error(err.detail || 'Unknown error'); });
            return response.json();
        })
        .then(data => {
            alert(`ジョブ定義 '${data.id}' が${isEdit ? '更新' : '作成'}されました。`);
            clearForm();
            // The scheduler will sync automatically, so we just refresh the view
            setTimeout(fetchAndDisplayJobs, 500); // Give a moment for sync
        })
        .catch(error => {
            console.error('Error saving job definition:', error);
            alert(`ジョブ定義の保存に失敗しました: ${error.message}`);
        });
    });

    // Event delegation for job action buttons
    jobsListBody.addEventListener('click', function(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;

        if (!jobId) return;

        // --- Scheduler Control Actions ---
        if (target.classList.contains('btn-run')) {
            if (confirm(`ジョブ '${jobId}' を今すぐ実行しますか？`)) {
                fetch(`${API_BASE_URL}/scheduler/jobs/${jobId}/run`, { method: 'POST' })
                    .then(response => {
                        if (!response.ok) throw new Error('実行リクエストに失敗しました。');
                        return response.json();
                    })
                    .then(() => {
                        alert(`ジョブ '${jobId}' はすぐに実行されます。`);
                        setTimeout(fetchAndDisplayJobs, 500); // Refresh view
                    })
                    .catch(error => alert(`エラー: ${error.message}`));
            }
        }

        // --- DB Definition Actions ---
        else if (target.classList.contains('btn-delete')) {
            if (confirm(`ジョブ定義 '${jobId}' を削除してもよろしいですか？
この操作は元に戻せません。`)) {
                fetch(`${API_BASE_URL}/jobs/${jobId}`, { method: 'DELETE' })
                    .then(response => {
                        if (!response.ok) throw new Error('削除に失敗しました。');
                        alert(`ジョブ定義 '${jobId}' が削除されました。`);
                        setTimeout(fetchAndDisplayJobs, 500); // Refresh view after sync
                    })
                    .catch(error => alert(`エラー: ${error.message}`));
            }
        } 
        else if (target.classList.contains('btn-edit')) {
            populateFormForEdit(jobId);
        }
    });
    
    // Event delegation for status toggle
    jobsListBody.addEventListener('change', function(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;

        if (!jobId || !target.classList.contains('status-toggle')) return;

        const action = target.checked ? 'resume' : 'pause';
        
        fetch(`${API_BASE_URL}/scheduler/jobs/${jobId}/${action}`, { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('ステータスの変更に失敗しました。');
                return response.json();
            })
            .then(() => {
                // No alert needed for this, just refresh the view
                fetchAndDisplayJobs();
            })
            .catch(error => {
                alert(`エラー: ${error.message}`);
                // Revert toggle on failure
                target.checked = !target.checked;
            });
    });


    // --- Initial Load ---
    showTriggerFields('cron');
    fetchAndDisplayJobs();
});
