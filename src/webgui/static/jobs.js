// src/webgui/static/jobs.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    
    // Main elements
    const jobsListBody = document.getElementById('jobs-list-body');
    const searchInput = document.getElementById('job-search-input');
    
    // Form elements
    const jobForm = document.getElementById('job-form');
    const jobIdInput = document.getElementById('job-id');
    const jobTypeSelect = document.getElementById('job-type');
    const jobFuncInput = document.getElementById('job-func');
    const jobDescriptionInput = document.getElementById('job-description');
    const jobEnabledCheckbox = document.getElementById('job-enabled');
    const triggerTypeSelect = document.getElementById('trigger-type');
    const cronFieldsDiv = document.getElementById('cron-fields');
    const intervalFieldsDiv = document.getElementById('interval-fields');
    const clearFormBtn = document.getElementById('clear-form-btn');
    const jobFormTitle = document.getElementById('job-form-title');
    const jobIdHidden = document.getElementById('job-id-hidden');

    // Command fields
    const shellCommandFields = document.getElementById('shell-command-fields');
    const jobCwdInput = document.getElementById('job-cwd');
    const jobEnvInput = document.getElementById('job-env');

    // Cron fields
    const cronMinuteInput = document.getElementById('cron-minute');
    const cronHourInput = document.getElementById('cron-hour');
    const cronDayOfWeekInput = document.getElementById('cron-day-of-week');

    // Interval fields
    const intervalWeeksInput = document.getElementById('interval-weeks');
    const intervalDaysInput = document.getElementById('interval-days');
    const intervalHoursInput = document.getElementById('interval-hours');
    const intervalMinutesInput = document.getElementById('interval-minutes');

    // Bulk action elements
    const selectAllCheckbox = document.getElementById('select-all-jobs');
    const bulkActionsGroup = document.getElementById('bulk-actions-group');
    const bulkPauseBtn = document.getElementById('bulk-pause-btn');
    const bulkResumeBtn = document.getElementById('bulk-resume-btn');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');

    const COMMAND_JOB_TYPES = ['cmd', 'powershell', 'shell'];

    // --- Utility Functions ---

    function showTriggerFields(type) {
        cronFieldsDiv.classList.toggle('d-none', type !== 'cron');
        intervalFieldsDiv.classList.toggle('d-none', type !== 'interval');
    }

    function showCommandFields(jobType) {
        const isCommandJob = COMMAND_JOB_TYPES.includes(jobType);
        shellCommandFields.classList.toggle('d-none', !isCommandJob);
    }
    
    function parseEnv(envString) {
        const env = {};
        if (envString) {
            envString.split('\n').forEach(line => {
                const parts = line.split('=');
                if (parts.length === 2) {
                    env[parts[0].trim()] = parts[1].trim();
                }
            });
        }
        return env;
    }

    function formatEnv(envObject) {
        if (!envObject) return '';
        return Object.entries(envObject).map(([key, value]) => `${key}=${value}`).join('\n');
    }

    function clearForm() {
        jobForm.reset();
        jobIdInput.value = '';
        jobTypeSelect.value = 'python';
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
        jobCwdInput.value = '';
        jobEnvInput.value = '';
        jobFormTitle.textContent = '新規ジョブ作成';
        jobIdInput.readOnly = false;
        jobIdHidden.value = '';
        showTriggerFields('cron');
        showCommandFields('python');
    }

    function populateFormForEdit(jobId) {
        fetch(`${API_BASE_URL}/api/jobs/${jobId}`)
            .then(response => {
                if (!response.ok) throw new Error('ジョブ定義の取得に失敗しました。');
                return response.json();
            })
            .then(job => {
                jobIdInput.value = job.id;
                jobIdInput.readOnly = true;
                jobIdHidden.value = job.id;
                jobDescriptionInput.value = job.description || '';
                jobEnabledCheckbox.checked = job.is_enabled;
                triggerTypeSelect.value = job.trigger.type;
                jobTypeSelect.value = job.job_type;

                if (COMMAND_JOB_TYPES.includes(job.job_type)) {
                    const command = job.kwargs.command || [];
                    jobFuncInput.value = command.join(' ');
                    jobCwdInput.value = job.kwargs.cwd || '';
                    jobEnvInput.value = formatEnv(job.kwargs.env);
                } else { // python
                    jobFuncInput.value = job.func;
                    jobCwdInput.value = '';
                    jobEnvInput.value = '';
                }
                showCommandFields(job.job_type);

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
                window.scrollTo(0, document.body.scrollHeight);
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
            return isoString;
        }
    }

    function updateBulkActions() {
        const selectedCheckboxes = jobsListBody.querySelectorAll('.job-checkbox:checked');
        const allCheckboxes = jobsListBody.querySelectorAll('.job-checkbox');
        
        if (selectedCheckboxes.length > 0) {
            bulkActionsGroup.style.display = 'inline-flex';
        } else {
            bulkActionsGroup.style.display = 'none';
        }

        if (allCheckboxes.length > 0 && selectedCheckboxes.length === allCheckboxes.length) {
            selectAllCheckbox.checked = true;
        } else {
            selectAllCheckbox.checked = false;
        }
    }

    function fetchAndDisplayJobs() {
        fetch(`${API_BASE_URL}/api/scheduler/jobs`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(jobs => {
                jobsListBody.innerHTML = '';
                if (jobs.length === 0) {
                    jobsListBody.innerHTML = `<tr><td colspan="7" class="text-center">スケジュールされたジョブはありません。</td></tr>`;
                    return;
                }
                jobs.forEach(job => {
                    const isPaused = job.next_run_time === null;
                    const row = document.createElement('tr');
                    
                    let displayFunc = job.func;
                    if (COMMAND_JOB_TYPES.includes(job.job_type) && job.kwargs && job.kwargs.command) {
                        displayFunc = `<span class="badge bg-info text-uppercase">${job.job_type}</span> ${job.kwargs.command.join(' ')}`;
                    }

                    row.innerHTML = `
                        <td><input type="checkbox" class="form-check-input job-checkbox" data-job-id="${job.id}"></td>
                        <td>
                            <div class="form-check form-switch">
                                <input class="form-check-input status-toggle" type="checkbox" role="switch" 
                                       data-job-id="${job.id}" ${isPaused ? '' : 'checked'}>
                                <label class="form-check-label">
                                    ${isPaused ? '<span class="badge bg-secondary">停止中</span>' : '<span class="badge bg-success">実行中</span>'}
                                </label>
                            </div>
                        </td>
                        <td><a href="/jobs/${job.id}">${job.id}</a></td>
                        <td>${formatTrigger(job.trigger)}</td>
                        <td>${formatDateTime(job.next_run_time)}</td>
                        <td class="text-break">${displayFunc}</td>
                        <td>
                            <button class="btn btn-sm btn-primary btn-run" data-job-id="${job.id}" title="今すぐ実行">実行</button>
                            <button class="btn btn-sm btn-info btn-edit" data-job-id="${job.id}" title="編集">編集</button>
                            <button class="btn btn-sm btn-danger btn-delete" data-job-id="${job.id}" title="削除">削除</button>
                        </td>
                    `;
                    jobsListBody.appendChild(row);
                });
                updateBulkActions();
            })
            .catch(error => {
                console.error('Error fetching scheduled jobs:', error);
                jobsListBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">ジョブの読み込みに失敗しました。</td></tr>`;
            });
    }

    function performBulkAction(action, url, confirmationText) {
        const selectedJobIds = Array.from(jobsListBody.querySelectorAll('.job-checkbox:checked'))
                                    .map(cb => cb.dataset.jobId);

        if (selectedJobIds.length === 0) {
            alert('操作対象のジョブを選択してください。');
            return;
        }

        if (confirm(`${selectedJobIds.length}件のジョブを${confirmationText}してもよろしいですか？`)) {
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_ids: selectedJobIds })
            })
            .then(response => {
                if (!response.ok) throw new Error(`${confirmationText}に失敗しました。`);
                return response.json();
            })
            .then(data => {
                alert(data.message || `${confirmationText}が完了しました。`);
                fetchAndDisplayJobs();
            })
            .catch(error => {
                alert(`エラー: ${error.message}`);
                fetchAndDisplayJobs();
            });
        }
    }

    function initializeJobTypes() {
        fetch(`${API_BASE_URL}/api/system/os`)
            .then(response => response.json())
            .then(data => {
                const osType = data.os_type;
                const options = jobTypeSelect.querySelectorAll('option.os-specific');
                options.forEach(option => {
                    const supportedOs = option.dataset.os;
                    if (osType.toLowerCase().includes(supportedOs)) {
                        option.style.display = 'block';
                    }
                });
            })
            .catch(error => console.error('Error fetching OS info:', error));
    }

    // --- Event Listeners ---

    searchInput.addEventListener('keyup', function() {
        const searchTerm = searchInput.value.toLowerCase();
        const rows = jobsListBody.getElementsByTagName('tr');
        for (const row of rows) {
            const jobIdCell = row.cells[2];
            const funcCell = row.cells[5];
            if (jobIdCell && funcCell) {
                const match = jobIdCell.textContent.toLowerCase().includes(searchTerm) || 
                              funcCell.textContent.toLowerCase().includes(searchTerm);
                row.style.display = match ? '' : 'none';
            }
        }
    });

    selectAllCheckbox.addEventListener('change', function() {
        const isChecked = selectAllCheckbox.checked;
        jobsListBody.querySelectorAll('.job-checkbox').forEach(checkbox => {
            checkbox.checked = isChecked;
        });
        updateBulkActions();
    });

    bulkPauseBtn.addEventListener('click', () => performBulkAction('pause', `${API_BASE_URL}/api/scheduler/jobs/bulk/pause`, '一括停止'));
    bulkResumeBtn.addEventListener('click', () => performBulkAction('resume', `${API_BASE_URL}/api/scheduler/jobs/bulk/resume`, '一括再開'));
    bulkDeleteBtn.addEventListener('click', () => performBulkAction('delete', `${API_BASE_URL}/api/jobs/bulk/delete`, '一括削除'));

    triggerTypeSelect.addEventListener('change', (event) => {
        showTriggerFields(event.target.value);
    });

    jobTypeSelect.addEventListener('change', (event) => {
        showCommandFields(event.target.value);
    });

    clearFormBtn.addEventListener('click', clearForm);

    const newJobBtn = document.getElementById('new-job-btn');
    if (newJobBtn) {
        newJobBtn.addEventListener('click', clearForm);
    }

    jobForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const isEdit = !!jobIdHidden.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${API_BASE_URL}/api/jobs/${jobIdHidden.value}` : `${API_BASE_URL}/api/jobs`;
        const jobType = jobTypeSelect.value;

        const jobData = {
            id: jobIdInput.value,
            job_type: jobType,
            func: null,
            description: jobDescriptionInput.value,
            is_enabled: jobEnabledCheckbox.checked,
            trigger: { type: triggerTypeSelect.value },
            args: [],
            kwargs: {},
            max_instances: 3,
            coalesce: true,
            misfire_grace_time: 3600,
            replace_existing: true,
        };

        if (COMMAND_JOB_TYPES.includes(jobType)) {
            jobData.func = 'modules.scheduler.job_executors:execute_command_job';
            const commandParts = jobFuncInput.value.match(/"[^"]+"|"[^"]+"|\S+/g) || [];
            jobData.kwargs.command = commandParts.map(part => part.replace(/^['"]|['"]$/g, ''));
            jobData.kwargs.job_type = jobType; // Pass job_type for the wrapper
            jobData.kwargs.cwd = jobCwdInput.value || null;
            jobData.kwargs.env = parseEnv(jobEnvInput.value) || null;
        } else { // python
            jobData.func = jobFuncInput.value;
        }

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
            setTimeout(fetchAndDisplayJobs, 500);
        })
        .catch(error => {
            console.error('Error saving job definition:', error);
            alert(`ジョブ定義の保存に失敗しました: ${error.message}`);
        });
    });

    jobsListBody.addEventListener('click', function(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;

        if (target.classList.contains('job-checkbox')) {
            updateBulkActions();
            return;
        }

        if (!jobId) return;

        if (target.classList.contains('btn-run')) {
            if (confirm(`ジョブ '${jobId}' を今すぐ実行しますか？`)) {
                fetch(`${API_BASE_URL}/api/scheduler/jobs/${jobId}/run`, { method: 'POST' })
                    .then(response => {
                        if (!response.ok) throw new Error('実行リクエストに失敗しました。');
                        return response.json();
                    })
                    .then(() => {
                        alert(`ジョブ '${jobId}' はすぐに実行されます。`);
                        setTimeout(fetchAndDisplayJobs, 500);
                    })
                    .catch(error => alert(`エラー: ${error.message}`));
            }
        } 
        else if (target.classList.contains('btn-delete')) {
            if (confirm(`ジョブ定義 '${jobId}' を削除してもよろしいですか？\nこの操作は元に戻せません。`)) {
                fetch(`${API_BASE_URL}/api/jobs/${jobId}`, { method: 'DELETE' })
                    .then(response => {
                        if (!response.ok) throw new Error('削除に失敗しました。');
                        alert(`ジョブ定義 '${jobId}' が削除されました。`);
                        setTimeout(fetchAndDisplayJobs, 500);
                    })
                    .catch(error => alert(`エラー: ${error.message}`));
            }
        } 
        else if (target.classList.contains('btn-edit')) {
            populateFormForEdit(jobId);
        }
    });
    
    jobsListBody.addEventListener('change', function(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;

        if (!jobId || !target.classList.contains('status-toggle')) return;

        const action = target.checked ? 'resume' : 'pause';
        
        fetch(`${API_BASE_URL}/api/scheduler/jobs/${jobId}/${action}`, { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('ステータスの変更に失敗しました。');
                return response.json();
            })
            .then(() => {
                fetchAndDisplayJobs();
            })
            .catch(error => {
                alert(`エラー: ${error.message}`);
                target.checked = !target.checked;
            });
    });

    // --- Initial Load ---
    initializeJobTypes();
    showTriggerFields('cron');
    showCommandFields('python');
    fetchAndDisplayJobs();
});
