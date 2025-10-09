// src/webgui/static/jobs.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = ''; // Use relative paths

    // --- Element Selectors ---
    const jobsListBody = document.getElementById('jobs-list-body');
    const searchInput = document.getElementById('job-search-input');
    const newJobBtn = document.getElementById('new-job-btn');

    // Form elements
    const jobForm = document.getElementById('job-form');
    const jobFormTitle = document.getElementById('job-form-title');
    const jobIdHidden = document.getElementById('job-id-hidden');
    const jobNameInput = document.getElementById('job-name');
    const jobDescriptionInput = document.getElementById('job-description');
    const jobEnabledCheckbox = document.getElementById('job-enabled');
    const clearFormBtn = document.getElementById('clear-form-btn');

    // Task parameter elements
    const taskTypeSelect = document.getElementById('task-type');
    const pythonParamsDiv = document.getElementById('python-params');
    const shellParamsDiv = document.getElementById('shell-params');
    const emailParamsDiv = document.getElementById('email-params');
    const taskParamsGroups = document.querySelectorAll('.task-params-group');

    // Python fields
    const pythonModuleInput = document.getElementById('python-module');
    const pythonFunctionInput = document.getElementById('python-function');
    const pythonArgsTextarea = document.getElementById('python-args');
    const pythonKwargsTextarea = document.getElementById('python-kwargs');

    // Shell fields
    const shellCommandTextarea = document.getElementById('shell-command');
    const shellCwdInput = document.getElementById('shell-cwd');
    const shellEnvTextarea = document.getElementById('shell-env');

    // Email fields
    const emailToInput = document.getElementById('email-to');
    const emailSubjectInput = document.getElementById('email-subject');
    const emailBodyTextarea = document.getElementById('email-body');

    // Trigger elements
    const triggerTypeSelect = document.getElementById('trigger-type');
    const cronFieldsDiv = document.getElementById('cron-fields');
    const intervalFieldsDiv = document.getElementById('interval-fields');
    const cronMinuteInput = document.getElementById('cron-minute');
    const cronHourInput = document.getElementById('cron-hour');
    const cronDayOfWeekInput = document.getElementById('cron-day-of-week');
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

    // --- Utility Functions ---

    function showToast(message, type = 'success') {
        // A simple toast notification function. Implement a proper library if needed.
        const toast = document.createElement('div');
        toast.className = `toast position-fixed top-0 end-0 p-3 ${type === 'success' ? 'bg-success' : 'bg-danger'} text-white`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    function parseJsonInput(value, defaultValue) {
        if (!value.trim()) return defaultValue;
        try {
            return JSON.parse(value);
        } catch (e) {
            alert(`JSON形式が無効です: ${e.message}`);
            throw e; // Stop form submission
        }
    }

    function parseEnv(envString) {
        const env = {};
        if (envString) {
            envString.split(/\r?\n/).forEach(line => {
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

    // --- Form Logic ---

    function updateFormForJobType(jobType) {
        taskParamsGroups.forEach(div => div.classList.add('d-none'));
        const activeDiv = document.getElementById(`${jobType}-params`);
        if (activeDiv) {
            activeDiv.classList.remove('d-none');
        }
    }

    function showTriggerFields(type) {
        cronFieldsDiv.classList.toggle('d-none', type !== 'cron');
        intervalFieldsDiv.classList.toggle('d-none', type !== 'interval');
    }

    function clearForm() {
        jobForm.reset();
        jobIdHidden.value = '';
        jobFormTitle.textContent = '新規ジョブ作成';
        taskTypeSelect.value = 'python';
        updateFormForJobType('python');
        triggerTypeSelect.value = 'cron';
        showTriggerFields('cron');
    }

    function populateFormForEdit(jobId) {
        fetch(`${API_BASE_URL}/api/jobs/${jobId}`)
            .then(response => {
                if (!response.ok) throw new Error('ジョブ定義の取得に失敗しました。');
                return response.json();
            })
            .then(job => {
                clearForm();
                jobIdHidden.value = job.id;
                jobNameInput.value = job.name;
                jobDescriptionInput.value = job.description || '';
                jobEnabledCheckbox.checked = job.is_enabled;
                
                taskTypeSelect.value = job.task_parameters.task_type;
                updateFormForJobType(job.task_parameters.task_type);

                const params = job.task_parameters;
                switch (params.task_type) {
                    case 'python':
                        pythonModuleInput.value = params.module;
                        pythonFunctionInput.value = params.function;
                        pythonArgsTextarea.value = JSON.stringify(params.args || [], null, 2);
                        pythonKwargsTextarea.value = JSON.stringify(params.kwargs || {}, null, 2);
                        break;
                    case 'shell':
                        shellCommandTextarea.value = params.command;
                        shellCwdInput.value = params.cwd || '';
                        shellEnvTextarea.value = formatEnv(params.env);
                        break;
                    case 'email':
                        emailToInput.value = params.to_email;
                        emailSubjectInput.value = params.subject;
                        emailBodyTextarea.value = params.body || '';
                        break;
                }

                triggerTypeSelect.value = job.trigger.type;
                showTriggerFields(job.trigger.type);
                const trigger = job.trigger;
                if (trigger.type === 'cron') {
                    cronMinuteInput.value = trigger.minute || '*';
                    cronHourInput.value = trigger.hour || '*';
                    cronDayOfWeekInput.value = trigger.day_of_week || '*';
                } else if (trigger.type === 'interval') {
                    intervalWeeksInput.value = trigger.weeks || 0;
                    intervalDaysInput.value = trigger.days || 0;
                    intervalHoursInput.value = trigger.hours || 0;
                    intervalMinutesInput.value = trigger.minutes || 0;
                }

                jobFormTitle.textContent = `ジョブ編集: ${job.name}`;
                window.scrollTo(0, 0); // Scroll to top to see the form
            })
            .catch(error => alert(`ジョブの編集データを取得できませんでした: ${error.message}`));
    }

    // --- API and Display Logic ---

    function formatTask(taskParams) {
        if (!taskParams) return 'N/A';
        switch (taskParams.task_type) {
            case 'python':
                return `<span class="badge bg-primary">Py</span> ${taskParams.module}:${taskParams.function}`;
            case 'shell':
                return `<span class="badge bg-secondary">Sh</span> ${taskParams.command}`;
            case 'email':
                return `<span class="badge bg-info">Mail</span> To: ${taskParams.to_email}`;
            default:
                return 'Unknown Task';
        }
    }

    function formatTrigger(trigger) {
        if (!trigger) return 'N/A';
        if (trigger.type === 'cron') {
            return `Cron: ${trigger.minute || '*'} ${trigger.hour || '*'} * * ${trigger.day_of_week || '*'}`;
        }
        if (trigger.type === 'interval') {
            let parts = [];
            if (trigger.weeks) parts.push(`${trigger.weeks}w`);
            if (trigger.days) parts.push(`${trigger.days}d`);
            if (trigger.hours) parts.push(`${trigger.hours}h`);
            if (trigger.minutes) parts.push(`${trigger.minutes}m`);
            if (trigger.seconds) parts.push(`${trigger.seconds}s`);
            return `Interval: ${parts.join(' ') || 'N/A'}`;
        }
        return 'Unknown';
    }

    function formatDateTime(isoString) {
        if (!isoString) return '---';
        try {
            return new Date(isoString).toLocaleString('ja-JP');
        } catch (e) {
            return isoString;
        }
    }

    function fetchAndDisplayJobs() {
        fetch(`${API_BASE_URL}/api/jobs`)
            .then(response => response.json())
            .then(jobs => {
                jobsListBody.innerHTML = '';
                if (jobs.length === 0) {
                    jobsListBody.innerHTML = `<tr><td colspan="7" class="text-center">登録済みのジョブはありません。</td></tr>`;
                    return;
                }
                jobs.forEach(job => {
                    const row = document.createElement('tr');
                    const status = job.is_enabled ? '<span class="badge bg-success">有効</span>' : '<span class="badge bg-secondary">無効</span>';
                    row.innerHTML = `
                        <td><input type="checkbox" class="form-check-input job-checkbox" data-job-id="${job.id}"></td>
                        <td>${status}</td>
                        <td><a href="#" class="job-name-link" data-job-id="${job.id}">${job.name}</a><br><small class="text-muted">${job.id}</small></td>
                        <td>${formatTrigger(job.trigger)}</td>
                        <td>${formatDateTime(job.next_run_time)}</td>
                        <td class="text-break">${formatTask(job.task_parameters)}</td>
                        <td>
                            <button class="btn btn-sm btn-info btn-edit" data-job-id="${job.id}" title="編集">編集</button>
                            <button class="btn btn-sm btn-danger btn-delete" data-job-id="${job.id}" title="削除">削除</button>
                        </td>
                    `;
                    jobsListBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching jobs:', error);
                jobsListBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">ジョブの読み込みに失敗しました。</td></tr>`;
            });
    }

    // --- Event Listeners ---

    taskTypeSelect.addEventListener('change', (e) => updateFormForJobType(e.target.value));
    triggerTypeSelect.addEventListener('change', (e) => showTriggerFields(e.target.value));
    newJobBtn.addEventListener('click', clearForm);
    clearFormBtn.addEventListener('click', clearForm);

    jobForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const isEdit = !!jobIdHidden.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${API_BASE_URL}/api/jobs/${jobIdHidden.value}` : `${API_BASE_URL}/api/jobs`;

        let task_parameters = {};
        const taskType = taskTypeSelect.value;

        try {
            switch (taskType) {
                case 'python':
                    task_parameters = {
                        task_type: 'python',
                        module: pythonModuleInput.value,
                        function: pythonFunctionInput.value,
                        args: parseJsonInput(pythonArgsTextarea.value, []),
                        kwargs: parseJsonInput(pythonKwargsTextarea.value, {}),
                    };
                    break;
                case 'shell':
                    task_parameters = {
                        task_type: 'shell',
                        command: shellCommandTextarea.value,
                        cwd: shellCwdInput.value || null,
                        env: parseEnv(shellEnvTextarea.value) || null,
                    };
                    break;
                case 'email':
                    task_parameters = {
                        task_type: 'email',
                        to_email: emailToInput.value,
                        subject: emailSubjectInput.value,
                        body: emailBodyTextarea.value || null,
                    };
                    break;
            }
        } catch (e) {
            return; // Stop submission if JSON parsing fails
        }

        const jobData = {
            name: jobNameInput.value,
            description: jobDescriptionInput.value,
            is_enabled: jobEnabledCheckbox.checked,
            trigger: { type: triggerTypeSelect.value },
            task_parameters: task_parameters,
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
            showToast(`ジョブ '${data.name}' が${isEdit ? '更新' : '作成'}されました。`);
            clearForm();
            fetchAndDisplayJobs();
        })
        .catch(error => {
            console.error('Error saving job:', error);
            alert(`ジョブの保存に失敗しました: ${error.message}`);
        });
    });

    jobsListBody.addEventListener('click', function(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;
        if (!jobId) return;

        if (target.classList.contains('btn-edit') || target.classList.contains('job-name-link')) {
            event.preventDefault();
            populateFormForEdit(jobId);
        } else if (target.classList.contains('btn-delete')) {
            if (confirm(`ジョブ定義 '${jobId}' を削除してもよろしいですか？\nこの操作は元に戻せません。`)) {
                fetch(`${API_BASE_URL}/api/jobs/${jobId}`, { method: 'DELETE' })
                    .then(response => {
                        if (!response.ok) throw new Error('削除に失敗しました。');
                        showToast(`ジョブ定義 '${jobId}' が削除されました。`);
                        fetchAndDisplayJobs();
                    })
                    .catch(error => alert(`エラー: ${error.message}`));
            }
        }
    });

    // --- Initial Load ---
    updateFormForJobType('python');
    showTriggerFields('cron');
    fetchAndDisplayJobs();
});
