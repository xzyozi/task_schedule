// src/webgui/static/jobs.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const jobDefinitionsListBody = document.getElementById('job-definitions-list-body');
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
        if (type === 'cron') {
            cronFieldsDiv.classList.remove('d-none');
            intervalFieldsDiv.classList.add('d-none');
        } else if (type === 'interval') {
            cronFieldsDiv.classList.add('d-none');
            intervalFieldsDiv.classList.remove('d-none');
        }
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
        jobIdInput.readOnly = false; // Make ID editable for new jobs
        jobIdHidden.value = '';
        showTriggerFields('cron');
    }

    function populateFormForEdit(job) {
        jobIdInput.value = job.id;
        jobIdInput.readOnly = true; // Make ID read-only for edits
        jobIdHidden.value = job.id; // Store original ID for PUT request
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
    }

    // --- Fetch and Display Jobs ---

    function fetchAndDisplayJobs() {
        fetch(`${API_BASE_URL}/jobs`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(jobs => {
                jobDefinitionsListBody.innerHTML = '';
                jobs.forEach(job => {
                    const row = document.createElement('tr');
                    const triggerDisplay = job.trigger.type === 'cron' 
                        ? `Cron: ${job.trigger.minute} ${job.trigger.hour} ${job.trigger.day_of_week}`
                        : `Interval: ${job.trigger.weeks}w ${job.trigger.days}d ${job.trigger.hours}h ${job.trigger.minutes}m`;
                    
                    const statusBadge = job.is_enabled 
                        ? '<span class="badge bg-success">有効</span>' 
                        : '<span class="badge bg-secondary">無効</span>';

                    row.innerHTML = `
                        <td>${job.id}</td>
                        <td>${job.func}</td>
                        <td>${triggerDisplay}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn btn-sm btn-info btn-edit" data-job-id="${job.id}">編集</button>
                            <button class="btn btn-sm btn-danger btn-delete" data-job-id="${job.id}">削除</button>
                        </td>
                    `;
                    jobDefinitionsListBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching job definitions:', error);
                jobDefinitionsListBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">ジョブ定義の読み込みに失敗しました。</td></tr>`;
            });
    }

    // --- Event Listeners ---

    triggerTypeSelect.addEventListener('change', (event) => {
        showTriggerFields(event.target.value);
    });

    clearFormBtn.addEventListener('click', clearForm);

    jobForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const jobId = jobIdInput.value;
        const isEdit = !!jobIdHidden.value; // Check if we are editing an existing job
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${API_BASE_URL}/jobs/${jobIdHidden.value}` : `${API_BASE_URL}/jobs`;

        const jobData = {
            id: jobId,
            func: jobFuncInput.value,
            description: jobDescriptionInput.value,
            is_enabled: jobEnabledCheckbox.checked,
            args: [], // Simplified for now
            kwargs: {},
            max_instances: 1,
            coalesce: false,
            misfire_grace_time: 3600,
            replace_existing: true,
        };

        // Trigger specific data
        const triggerType = triggerTypeSelect.value;
        jobData.trigger = { type: triggerType };

        if (triggerType === 'cron') {
            jobData.trigger.minute = cronMinuteInput.value;
            jobData.trigger.hour = cronHourInput.value;
            jobData.trigger.day_of_week = cronDayOfWeekInput.value;
        } else if (triggerType === 'interval') {
            jobData.trigger.weeks = parseInt(intervalWeeksInput.value);
            jobData.trigger.days = parseInt(intervalDaysInput.value);
            jobData.trigger.hours = parseInt(intervalHoursInput.value);
            jobData.trigger.minutes = parseInt(intervalMinutesInput.value);
        }

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(jobData),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || 'Unknown error'); });
            }
            return response.json();
        })
        .then(data => {
            alert(`ジョブ '${data.id}' が${isEdit ? '更新' : '作成'}されました。`);
            clearForm();
            fetchAndDisplayJobs();
        })
        .catch(error => {
            console.error('Error saving job:', error);
            alert(`ジョブの保存に失敗しました: ${error.message}`);
        });
    });

    jobDefinitionsListBody.addEventListener('click', function(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;

        if (target.classList.contains('btn-delete')) {
            if (confirm(`ジョブ '${jobId}' を削除してもよろしいですか？`)) {
                fetch(`${API_BASE_URL}/jobs/${jobId}`, {
                    method: 'DELETE'
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.detail || 'Unknown error'); });
                    }
                    // For 204 No Content, response.json() will throw an error
                    if (response.status === 204) return {}; 
                    return response.json();
                })
                .then(() => {
                    alert(`ジョブ '${jobId}' が削除されました。`);
                    fetchAndDisplayJobs();
                })
                .catch(error => {
                    console.error('Error deleting job:', error);
                    alert(`ジョブの削除に失敗しました: ${error.message}`);
                });
            }
        } else if (target.classList.contains('btn-edit')) {
            // Fetch job data and populate the form
            fetch(`${API_BASE_URL}/jobs/${jobId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(job => {
                    populateFormForEdit(job);
                })
                .catch(error => {
                    console.error('Error fetching job for edit:', error);
                    alert(`ジョブの編集データを取得できませんでした: ${error.message}`);
                });
        }
    });

    // Initial load
    fetchAndDisplayJobs();
});