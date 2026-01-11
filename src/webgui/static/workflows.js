import { fetchConfig, getApiBaseUrl } from './api_config.js';

document.addEventListener('DOMContentLoaded', async function() {
    await fetchConfig();

    // --- Global State ---
    let availableTasks = [];

    // --- Element Selectors ---
    const workflowsListBody = document.getElementById('workflows-list-body');
    const workflowForm = document.getElementById('workflow-form');
    const workflowFormTitle = document.getElementById('workflow-form-title');
    const workflowIdInput = document.getElementById('workflow-id-hidden');
    
    const paramsContainer = document.getElementById('params-container');
    const addParamBtn = document.getElementById('add-param-btn');
    const paramTemplate = document.getElementById('param-template');

    const stepsContainer = document.getElementById('steps-container');
    const addStepBtn = document.getElementById('add-step-btn');
    const stepTemplate = document.getElementById('step-template');
    const clearFormBtn = document.getElementById('clear-workflow-form-btn');

    const runWorkflowModal = new bootstrap.Modal(document.getElementById('runWorkflowModal'));
    const runWorkflowModalLabel = document.getElementById('runWorkflowModalLabel');
    const modalRunWorkflowIdInput = document.getElementById('modal-run-workflow-id');
    const modalParamInputsContainer = document.getElementById('modal-param-inputs');
    const confirmRunWorkflowBtn = document.getElementById('confirm-run-workflow-btn');

    // --- Utility Functions ---

    function showToast(message, type = 'success') {
        // Implementation from jobs.js or a shared utility file
    }

    function parseJsonInput(value, paramName, defaultValue) {
        if (!value.trim()) return defaultValue;
        try {
            return JSON.parse(value);
        } catch (e) {
            alert(`Parameter "${paramName}" has invalid JSON: ${e.message}`);
            throw e;
        }
    }

    // --- Dynamic Form Generation (for parameters) ---
    function addParam(paramData = null) {
        const newParam = paramTemplate.content.cloneNode(true);
        const paramCard = newParam.querySelector('.param-card');
        if (paramData) {
            paramCard.querySelector('.param-name').value = paramData.name || '';
            paramCard.querySelector('.param-label').value = paramData.label || '';
        }
        paramsContainer.appendChild(paramCard);
    }

    // --- Dynamic Form Generation (for steps) ---

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

    function generateStepParamsForm(stepCard, taskId) {
        const paramsContainer = stepCard.querySelector('.dynamic-step-params-container');
        paramsContainer.innerHTML = '';
        const selectedTask = availableTasks.find(t => t.id === taskId);

        if (!selectedTask || !selectedTask.parameters || selectedTask.parameters.length === 0) {
            paramsContainer.style.display = 'none';
            return;
        }

        selectedTask.parameters.forEach(param => {
            const field = generateFormField(param);
            // Prefix IDs and names to make them unique per step
            const input = field.querySelector('input, textarea');
            const label = field.querySelector('label');
            const stepId = `step-${Date.now()}`;
            if(input) {
                input.id = `${stepId}-${input.id}`;
                label.htmlFor = input.id;
            }
            paramsContainer.appendChild(field);
        });
        paramsContainer.style.display = 'block';
    }

    // --- Main Workflow and Step Functions ---

    function addStep(stepData = null) {
        const newStep = stepTemplate.content.cloneNode(true);
        const stepCard = newStep.querySelector('.step-card');
        const jobTypeSelect = stepCard.querySelector('.step-job-type');

        // Populate job type dropdown
        availableTasks.forEach(task => {
            const option = document.createElement('option');
            option.value = task.id;
            option.textContent = task.name;
            jobTypeSelect.appendChild(option);
        });

        stepsContainer.appendChild(stepCard);
        updateStepTitles();

        jobTypeSelect.addEventListener('change', () => {
            generateStepParamsForm(stepCard, jobTypeSelect.value);
        });

        if (stepData) {
            stepCard.querySelector('.step-name').value = stepData.name;
            stepCard.querySelector('.step-on-failure').value = stepData.on_failure;
            stepCard.querySelector('.step-run-in-background').checked = stepData.run_in_background;
            stepCard.querySelector('.step-output-variable-name').value = stepData.output_variable_name || '';
            stepCard.querySelector('.step-output-capture-source').value = stepData.output_capture_source || 'return_value';

            let taskParams = stepData.task_parameters;
            if (typeof taskParams === 'string') {
                try {
                    taskParams = JSON.parse(taskParams);
                } catch (e) {
                    console.error('Failed to parse task_parameters for step:', stepData, e);
                    const title = stepCard.querySelector('.card-title');
                    title.textContent += ' - ERROR: Could not load step data';
                    stepCard.style.borderColor = 'red';
                    return;
                }
            }
            console.log('taskParams:', taskParams);

            let taskId;
            if (taskParams.task_type === 'python') {
                taskId = `python:${taskParams.module}:${taskParams.function}`;
            } else {
                taskId = taskParams.task_type;
            }

            jobTypeSelect.value = taskId;
            generateStepParamsForm(stepCard, taskId);

            // Populate dynamic fields
            const selectedTask = availableTasks.find(t => t.id === taskId);
            if (selectedTask) {
                selectedTask.parameters.forEach(param => {
                    const input = stepCard.querySelector(`[name="${param.name}"]`);
                    if (!input) return;
                    
                    // Find the value from taskParams, attempting a case-insensitive match for the key
                    let value;
                    const paramName = param.name;
                    
                    // For python jobs, parameters are nested in kwargs
                    let sourceParams = taskParams;
                    if (taskParams.task_type === 'python' && taskParams.kwargs) {
                        sourceParams = taskParams.kwargs;
                    }

                    if (sourceParams.hasOwnProperty(paramName)) {
                        value = sourceParams[paramName];
                    } else {
                        const lowerParamName = paramName.toLowerCase();
                        const matchingKey = Object.keys(sourceParams).find(k => k.toLowerCase() === lowerParamName);
                        if (matchingKey) {
                            value = sourceParams[matchingKey];
                        }
                    }

                    if (input.type === 'checkbox') {
                        input.checked = !!value;
                    } else if (input.tagName === 'TEXTAREA') {
                        input.value = value != null ? JSON.stringify(value, null, 2) : '';
                    } else {
                        if (typeof value === 'object' && value !== null) {
                            input.value = JSON.stringify(value);
                        } else {
                            input.value = value ?? '';
                        }
                    }
                });
            }
        }
    }

    function updateStepTitles() {
        const steps = stepsContainer.querySelectorAll('.step-card');
        steps.forEach((step, index) => {
            step.querySelector('.card-title').textContent = `ステップ ${index + 1}`;
        });
    }
    
    function clearWorkflowForm() {
        workflowForm.reset();
        workflowIdInput.value = '';
        stepsContainer.innerHTML = '';
        paramsContainer.innerHTML = '';
        workflowFormTitle.textContent = '新規ワークフロー作成';
    }

    // --- API Fetching ---

    async function fetchAvailableTasks() {
        try {
            const response = await fetch(`${getApiBaseUrl()}/api/available-tasks`);
            if (!response.ok) throw new Error('Failed to fetch tasks');
            availableTasks = await response.json();
        } catch (error) {
            console.error('Error fetching available tasks:', error);
            alert('タスクの読み込みに失敗しました。');
        }
    }

    function fetchAndDisplayWorkflows() {
        fetch(`${getApiBaseUrl()}/api/workflows`)
            .then(response => response.json())
            .then(workflows => {
                workflowsListBody.innerHTML = '';
                workflows.forEach(wf => {
                    const row = document.createElement('tr');
                    const isEnabled = wf.is_enabled;
                    row.innerHTML = `
                        <td>
                            <div class="form-check form-switch">
                                <input class="form-check-input workflow-status-toggle" type="checkbox" role="switch"
                                       data-workflow-id="${wf.id}" ${isEnabled ? 'checked' : ''}>
                                <label class="form-check-label">
                                    ${isEnabled ? '<span class="badge bg-success">有効</span>' : '<span class="badge bg-secondary">無効</span>'}
                                </label>
                            </div>
                        </td>
                        <td><a href="/workflows/${wf.id}">${wf.name}</a></td>
                        <td>${wf.description || ''}</td>
                        <td>${wf.schedule || 'N/A'}</td>
                        <td>
                            <button class="btn btn-sm btn-info btn-edit-workflow" data-workflow-id="${wf.id}">編集</button>
                            <button class="btn btn-sm btn-success btn-run-workflow" data-workflow-id="${wf.id}" data-workflow-name="${wf.name}">実行</button>
                            <button class="btn btn-sm btn-danger btn-delete-workflow" data-workflow-id="${wf.id}">削除</button>
                        </td>
                    `;
                    workflowsListBody.appendChild(row);
                });
            })
            .catch(error => console.error('Error fetching workflows:', error));
    }

    // --- Event Listeners ---

    addParamBtn.addEventListener('click', () => addParam());

    paramsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-param-btn')) {
            event.target.closest('.param-card').remove();
        }
    });

    addStepBtn.addEventListener('click', () => addStep());
    clearFormBtn.addEventListener('click', clearWorkflowForm);

    stepsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-step-btn')) {
            event.target.closest('.step-card').remove();
            updateStepTitles();
        }
    });

    confirmRunWorkflowBtn.addEventListener('click', function() {
        const workflowId = modalRunWorkflowIdInput.value;
        fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}/run`, { method: 'POST' })
            .then(response => response.ok ? response.json() : Promise.reject('Failed to run workflow'))
            .then(data => {
                alert(`ワークフローが実行キューに追加されました: ${data.message}`);
                runWorkflowModal.hide();
            })
            .catch(error => alert(error));
    });

    workflowForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const isEdit = !!workflowIdInput.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${getApiBaseUrl()}/api/workflows/${workflowIdInput.value}` : `${getApiBaseUrl()}/api/workflows`;

        const params_def = [];
        paramsContainer.querySelectorAll('.param-card').forEach(paramCard => {
            const name = paramCard.querySelector('.param-name').value.trim();
            const label = paramCard.querySelector('.param-label').value.trim();
            if (name && label) {
                params_def.push({ name, label });
            }
        });

        const steps = [];
        try {
            stepsContainer.querySelectorAll('.step-card').forEach((stepCard, index) => {
                const selectedTaskId = stepCard.querySelector('.step-job-type').value;
                if (!selectedTaskId) throw new Error(`ステップ ${index + 1} のジョブタイプを選択してください。`);
                
                const selectedTask = availableTasks.find(t => t.id === selectedTaskId);
                let task_parameters = { task_type: selectedTask.task_type };

                if (selectedTask.task_type === 'python') {
                    task_parameters.module = selectedTask.module;
                    task_parameters.function = selectedTask.function;
                }

                selectedTask.parameters.forEach(param => {
                    const input = stepCard.querySelector(`[name="${param.name}"]`);
                    if (!input) return;
                    let value;
                    if (input.type === 'checkbox') {
                        value = input.checked;
                    } else if (input.tagName === 'TEXTAREA') {
                        value = parseJsonInput(input.value, param.name, param.type.includes('List') ? [] : {});
                    } else {
                        value = input.value;
                    }
                    if (input.required && !value && input.type !== 'checkbox') {
                        throw new Error(`ステップ ${index + 1} の必須パラメータ "${param.label}" が空です。`);
                    }
                    if (value !== null && value !== '') {
                        task_parameters[param.name] = value;
                    }
                });

                steps.push({
                    step_order: index + 1,
                    name: stepCard.querySelector('.step-name').value,
                    task_parameters: task_parameters,
                    on_failure: stepCard.querySelector('.step-on-failure').value,
                    run_in_background: stepCard.querySelector('.step-run-in-background').checked,
                    output_variable_name: stepCard.querySelector('.step-output-variable-name').value.trim() || null,
                    output_capture_source: stepCard.querySelector('.step-output-capture-source').value,
                });
            });
        } catch (e) {
            alert(e.message);
            return;
        }

        const workflowData = {
            name: document.getElementById('workflow-name').value,
            description: document.getElementById('workflow-description').value,
            schedule: document.getElementById('workflow-schedule').value,
            is_enabled: document.getElementById('workflow-enabled').checked,
            params_def: params_def,
            steps: steps,
        };

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(workflowData)
        })
        .then(response => response.ok ? response.json() : response.json().then(err => Promise.reject(err)))
        .then(data => {
            alert(`ワークフロー '${data.name}' が${isEdit ? '更新' : '作成'}されました。`);
            clearWorkflowForm();
            fetchAndDisplayWorkflows();
        })
        .catch(error => {
            const errorMessage = error.detail ? JSON.stringify(error.detail) : (error.message || 'Unknown error');
            alert(`ワークフローの保存に失敗しました:\n${errorMessage}`);
        });
    });

    workflowsListBody.addEventListener('click', async function(event) {
        const target = event.target;
        const workflowId = target.dataset.workflowId;
        if (!workflowId) return;

        if (target.classList.contains('btn-edit-workflow')) {
            const response = await fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}`);
            const workflow = await response.json();
            
            clearWorkflowForm();
            workflowFormTitle.textContent = `ワークフロー編集: ${workflow.name}`;
            workflowIdInput.value = workflow.id;
            document.getElementById('workflow-name').value = workflow.name;
            document.getElementById('workflow-description').value = workflow.description;
            document.getElementById('workflow-schedule').value = workflow.schedule;
            document.getElementById('workflow-enabled').checked = workflow.is_enabled;

            paramsContainer.innerHTML = '';
            if (workflow.params_def && Array.isArray(workflow.params_def)) {
                workflow.params_def.forEach(addParam);
            }

            stepsContainer.innerHTML = '';
            workflow.steps.sort((a, b) => a.step_order - b.step_order).forEach(addStep);

            window.scrollTo(0, document.body.scrollHeight);

        } else if (target.classList.contains('btn-run-workflow')) {
            runWorkflowModalLabel.textContent = `ワークフロー実行: ${target.dataset.workflowName}`;
            modalRunWorkflowIdInput.value = workflowId;
            modalParamInputsContainer.innerHTML = '<p>このワークフローをすぐに実行しますか？</p>';
            runWorkflowModal.show();

        } else if (target.classList.contains('btn-delete-workflow')) {
            if (confirm('本当にこのワークフローを削除しますか？')) {
                fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}`, { method: 'DELETE' })
                    .then(response => {
                        if (!response.ok) throw new Error('削除に失敗しました。');
                        alert('ワークフローが削除されました。');
                        fetchAndDisplayWorkflows();
                    })
                    .catch(error => alert(error.message));
            }
        }
    });
    
    workflowsListBody.addEventListener('change', function(event) {
        const target = event.target;
        const workflowId = target.dataset.workflowId;
        if (!workflowId || !target.classList.contains('workflow-status-toggle')) return;

        const action = target.checked ? 'resume' : 'pause';
        fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}/${action}`, { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('ステータスの変更に失敗しました。');
                return response.json();
            })
            .then(() => fetchAndDisplayWorkflows())
            .catch(error => {
                alert(`エラー: ${error.message}`);
                target.checked = !target.checked;
            });
    });

    // --- Initial Load ---
    (async () => {
        await fetchAvailableTasks();
        fetchAndDisplayWorkflows();
    })();
});
