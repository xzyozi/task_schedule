// src/webgui/static/jobs.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = ''; // Use relative paths

    // --- Global State ---
    let availableTasks = [];
    let jobsData = []; // Cache for jobs data

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

    // Task parameter elements (dynamic)
    const taskSelect = document.getElementById('task-select');
    const dynamicParamsContainer = document.getElementById('dynamic-params-container');

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
        const toast = document.createElement('div');
        toast.className = `toast show position-fixed top-0 end-0 p-3 ${type === 'success' ? 'bg-success' : 'bg-danger'} text-white`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }

    function parseJsonInput(value, paramName, defaultValue) {
        if (!value.trim()) return defaultValue;
        try {
            return JSON.parse(value);
        } catch (e) {
            alert(`Parameter "${paramName}" has invalid JSON: ${e.message}`);
            throw e; // Stop form submission
        }
    }

    // --- Dynamic Form Generation ---

    function generateFormField(param) {
        const formGroup = document.createElement('div');
        formGroup.className = 'mb-3';

        const label = document.createElement('label');
        label.htmlFor = `param-${param.name}`;
        label.className = 'form-label';
        label.textContent = param.label;
        if (param.required) {
            const requiredSpan = document.createElement('span');
            requiredSpan.className = 'text-danger';
            requiredSpan.textContent = ' *';
            label.appendChild(requiredSpan);
        }
        formGroup.appendChild(label);

        let input;
        const inputId = `param-${param.name}`;
        const isJson = param.type.includes('Dict') || param.type.includes('List');
        const isBool = param.type.toLowerCase().includes('bool');

        if (isBool) {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.className = 'form-check-input';
        } else if (isJson) {
            input = document.createElement('textarea');
            input.rows = 3;
            input.placeholder = `Enter JSON for ${param.name}`;
            input.className = 'form-control';
        } else {
            input = document.createElement('input');
            input.type = param.type.toLowerCase().includes('int') ? 'number' : 'text';
            input.className = 'form-control';
        }

        input.id = inputId;
        input.name = param.name;
        if (param.required) {
            input.required = true;
        }

        formGroup.appendChild(input);

        if (param.description) {
            const helpText = document.createElement('div');
            helpText.className = 'form-text';
            helpText.textContent = param.description;
            formGroup.appendChild(helpText);
        }
        return formGroup;
    }

    function generateParamsForm(taskId) {
        dynamicParamsContainer.innerHTML = '';
        const selectedTask = availableTasks.find(t => t.id === taskId);

        if (!selectedTask || !selectedTask.parameters || selectedTask.parameters.length === 0) {
            dynamicParamsContainer.classList.add('d-none');
            return;
        }

        selectedTask.parameters.forEach(param => {
            const field = generateFormField(param);
            dynamicParamsContainer.appendChild(field);
        });
        dynamicParamsContainer.classList.remove('d-none');
    }

    // --- Form Logic ---

    function showTriggerFields(type) {
        cronFieldsDiv.classList.toggle('d-none', type !== 'cron');
        intervalFieldsDiv.classList.toggle('d-none', type !== 'interval');
    }

    function clearForm() {
        jobForm.reset();
        jobIdHidden.value = '';
        jobFormTitle.textContent = '新規ジョブ作成';
        
        taskSelect.value = '';
        taskSelect.disabled = false;
        dynamicParamsContainer.innerHTML = '';
        dynamicParamsContainer.classList.add('d-none');

        triggerTypeSelect.value = 'cron';
        showTriggerFields('cron');
    }

    async function populateFormForEdit(jobId) {
        // Ensure tasks are loaded before populating
        if (availableTasks.length === 0) {
            await fetchAvailableTasks();
        }

        const job = jobsData.find(j => j.id === jobId);
        if (!job) {
            alert('ジョブが見つかりません。');
            return;
        }

        clearForm();
        jobIdHidden.value = job.id;
        jobNameInput.value = job.name;
        jobDescriptionInput.value = job.description || '';
        jobEnabledCheckbox.checked = job.is_enabled;

        const params = job.task_parameters;
        let taskId;
        if (params.task_type === 'python') {
            taskId = `python:${params.module}:${params.function}`;
        } else {
            taskId = params.task_type;
        }

        taskSelect.value = taskId;
        generateParamsForm(taskId);
        taskSelect.disabled = true; // Don't allow changing task type on edit

        // Populate dynamic fields
        if (params) {
            for (const [key, value] of Object.entries(params)) {
                const input = document.getElementById(`param-${key}`);
                if (!input) continue;

                if (input.type === 'checkbox') {
                    input.checked = !!value;
                } else if (input.tagName === 'TEXTAREA') {
                    input.value = JSON.stringify(value, null, 2);
                } else {
                    input.value = value;
                }
            }
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
        window.scrollTo(0, document.body.scrollHeight); // Scroll to form
    }

    // --- API and Display Logic ---

    async function fetchAvailableTasks() {
        taskSelect.disabled = true;
        try {
            const response = await fetch(`${API_BASE_URL}/api/available-tasks`);
            if (!response.ok) throw new Error('Failed to fetch tasks');
            availableTasks = await response.json();
            
            taskSelect.innerHTML = '<option value="" selected disabled>タスクを選択...</option>';
            availableTasks.forEach(task => {
                const option = document.createElement('option');
                option.value = task.id;
                option.textContent = task.name;
                taskSelect.appendChild(option);
            });
            taskSelect.disabled = false;

        } catch (error) {
            console.error('Error fetching available tasks:', error);
            taskSelect.innerHTML = '<option value="" selected disabled>タスクの読み込みに失敗しました。</option>';
        }
    }

    function formatTask(taskParams) {
        if (!taskParams) return 'N/A';
        switch (taskParams.task_type) {
            case 'python':
                return `<span class="badge bg-primary">Py</span> ${taskParams.module}:${taskParams.function}`;
            case 'shell':
                return `<span class="badge bg-secondary">Sh</span> ${taskParams.command.substring(0, 50)}...`;
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
        if (!isoString) return '--';
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
                jobsData = jobs; // Cache the data
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

    taskSelect.addEventListener('change', (e) => generateParamsForm(e.target.value));
    triggerTypeSelect.addEventListener('change', (e) => showTriggerFields(e.target.value));
    newJobBtn.addEventListener('click', clearForm);
    clearFormBtn.addEventListener('click', clearForm);

    jobForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const selectedTaskId = taskSelect.value;
        if (!selectedTaskId) {
            alert('タスクを選択してください。');
            return;
        }

        const selectedTask = availableTasks.find(t => t.id === selectedTaskId);
        const isEdit = !!jobIdHidden.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${API_BASE_URL}/api/jobs/${jobIdHidden.value}` : `${API_BASE_URL}/api/jobs`;

        let task_parameters = {
            task_type: selectedTask.task_type
        };

        // For python tasks, add module and function
        if (selectedTask.task_type === 'python') {
            task_parameters.module = selectedTask.module;
            task_parameters.function = selectedTask.function;
        }

        try {
            // Dynamically gather parameters from the generated form
            selectedTask.parameters.forEach(param => {
                const input = document.getElementById(`param-${param.name}`);
                if (!input) return;

                let value;
                if (input.type === 'checkbox') {
                    value = input.checked;
                } else if (input.tagName === 'TEXTAREA') {
                    const isJson = param.type.includes('Dict') || param.type.includes('List');
                    if (isJson) {
                        value = parseJsonInput(input.value, param.name, isJson && param.type.includes('List') ? [] : {});
                    } else {
                        value = input.value;
                    }
                } else {
                    value = input.value;
                }
                
                if (input.required && !value && input.type !== 'checkbox') {
                    throw new Error(`必須パラメータ "${param.label}" が空です。`);
                }

                // Only include the parameter if it has a value or is required
                if (value !== null && value !== '' || param.required) {
                    task_parameters[param.name] = value;
                }
            });
        } catch (e) {
            alert(e.message);
            return; // Stop submission
        }

        const jobData = {
            name: jobNameInput.value,
            description: jobDescriptionInput.value,
            is_enabled: jobEnabledCheckbox.checked,
            trigger: { type: triggerTypeSelect.value },
            task_parameters: task_parameters,
        };
        
        if (!isEdit) {
            jobData.id = jobNameInput.value.trim().replace(/\s+/g, '_');
             if (!jobData.id) {
                alert('ジョブ名は必須です。');
                return;
            }
        }

        if (jobData.trigger.type === 'cron') {
            jobData.trigger.minute = cronMinuteInput.value;
            jobData.trigger.hour = cronHourInput.value;
            jobData.trigger.day_of_week = cronDayOfWeekInput.value;
        } else {
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
        .then(response => response.ok ? response.json() : response.json().then(err => Promise.reject(err)))
        .then(data => {
            showToast(`ジョブ '${data.name}' が${isEdit ? '更新' : '作成'}されました。`);
            clearForm();
            fetchAndDisplayJobs();
        })
        .catch(error => {
            const errorMessage = error.detail ? JSON.stringify(error.detail) : error.message;
            alert(`ジョブの保存に失敗しました:\n${errorMessage}`);
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
    showTriggerFields('cron');
    fetchAndDisplayJobs();
    fetchAvailableTasks();
});