import { fetchConfig, getApiBaseUrl } from './api_config.js';

document.addEventListener('DOMContentLoaded', async function() {
    await fetchConfig();

    const workflowsListBody = document.getElementById('workflows-list-body');
    const workflowForm = document.getElementById('workflow-form');
    const workflowFormTitle = document.getElementById('workflow-form-title');
    const workflowIdInput = document.getElementById('workflow-id-hidden');
    const stepsContainer = document.getElementById('steps-container');
    const addStepBtn = document.getElementById('add-step-btn');
    const stepTemplate = document.getElementById('step-template');
    const paramsContainer = document.getElementById('params-container');
    const addParamBtn = document.getElementById('add-param-btn');
    const paramTemplate = document.getElementById('param-template');

    const runWorkflowModal = new bootstrap.Modal(document.getElementById('runWorkflowModal'));
    const runWorkflowModalLabel = document.getElementById('runWorkflowModalLabel');
    const modalRunWorkflowIdInput = document.getElementById('modal-run-workflow-id');
    const modalParamInputsContainer = document.getElementById('modal-param-inputs');
    const confirmRunWorkflowBtn = document.getElementById('confirm-run-workflow-btn');

    let serverOsType = '';
    let availablePythonTasks = []; // Now stores objects with module and function

    // --- Utility Functions ---

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
                            <a href="/workflows/${wf.id}" class="btn btn-sm btn-primary">詳細</a>
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

    function toggleTaskParameterInputs(stepCard, taskType) {
        const pythonParamsContainer = stepCard.querySelector('.python-params-container');
        const shellParamsContainer = stepCard.querySelector('.shell-params-container');
        const genericTargetContainer = stepCard.querySelector('.step-target-generic');
        const genericTargetInput = stepCard.querySelector('.step-target-text');
        const shellCommandInput = stepCard.querySelector('.shell-command');

        // Hide all first
        pythonParamsContainer.style.display = 'none';
        shellParamsContainer.style.display = 'none';
        genericTargetContainer.style.display = 'none';

        // Disable required for all specific inputs
        genericTargetInput.required = false;
        if (shellCommandInput) shellCommandInput.required = false; // Check if element exists

        if (taskType === 'python') {
            pythonParamsContainer.style.display = 'block';
        } else if (['cmd', 'powershell', 'shell'].includes(taskType)) {
            shellParamsContainer.style.display = 'block';
            if (shellCommandInput) shellCommandInput.required = true; // Ensure shell command is required when visible
        } else {
            genericTargetContainer.style.display = 'block';
            genericTargetInput.required = true;
        }
    }

    function addStep(stepData = null) {
        const newStep = stepTemplate.content.cloneNode(true);
        const stepCard = newStep.querySelector('.step-card');
        const jobTypeSelect = stepCard.querySelector('.step-job-type');

        stepsContainer.appendChild(stepCard);
        updateStepTitles();

        // Initialize visibility based on default or loaded job type
        const initialJobType = stepData ? stepData.task_parameters.task_type : jobTypeSelect.value;
        toggleTaskParameterInputs(stepCard, initialJobType);

        jobTypeSelect.addEventListener('change', () => {
            toggleTaskParameterInputs(stepCard, jobTypeSelect.value);
        });

        if (stepData) {
            stepCard.querySelector('.step-name').value = stepData.name;
            jobTypeSelect.value = stepData.task_parameters.task_type;
            stepCard.querySelector('.step-on-failure').value = stepData.on_failure;
            stepCard.querySelector('.step-run-in-background').checked = stepData.run_in_background;

            const taskParams = stepData.task_parameters;

            if (taskParams.task_type === 'python') {
                stepCard.querySelector('.python-module').value = taskParams.module || '';
                stepCard.querySelector('.python-function').value = taskParams.function || '';
                stepCard.querySelector('.python-args').value = JSON.stringify(taskParams.args || []);
                stepCard.querySelector('.python-kwargs').value = JSON.stringify(taskParams.kwargs || {});
            } else if (['cmd', 'powershell', 'shell'].includes(taskParams.task_type)) {
                stepCard.querySelector('.shell-command').value = taskParams.command || '';
                stepCard.querySelector('.shell-cwd').value = taskParams.cwd || '';
                stepCard.querySelector('.shell-env').value = JSON.stringify(taskParams.env || {});
            } else {
                // For other generic types, if any, use the generic target text field
                stepCard.querySelector('.step-target-text').value = taskParams.target || ''; // Assuming a 'target' field for generic types
            }
        }
    }

    function updateStepTitles() {
        const steps = stepsContainer.querySelectorAll('.step-card');
        steps.forEach((step, index) => {
            step.querySelector('.card-title').textContent = `ステップ ${index + 1}`;
        });
    }

    function fetchOsInfo() {
        return fetch(`${getApiBaseUrl()}/api/system/os`)
            .then(response => response.json())
            .then(data => {
                serverOsType = data.os_type;
                // After fetching OS info, initialize job type options for all existing steps
                stepsContainer.querySelectorAll('.step-card').forEach(stepCard => {
                    initializeJobTypeOptions(stepCard);
                });
            })
            .catch(error => console.error('Error fetching OS info:', error));
    }

    function initializeJobTypeOptions(container) {
        const options = container.querySelectorAll('option.os-specific');
        options.forEach(option => {
            const supportedOs = option.dataset.os;
            if (serverOsType.toLowerCase().includes(supportedOs)) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none'; // Hide options not supported by OS
            }
        });
    }

    function fetchPythonTasks() {
        return fetch(`${getApiBaseUrl()}/api/available-tasks`)
            .then(response => response.json())
            .then(data => {
                availablePythonTasks = data; // Store full objects
            })
            .catch(error => console.error('Error fetching Python tasks:', error));
    }

    // --- Event Listeners ---

    addStepBtn.addEventListener('click', () => addStep());

    stepsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-step-btn')) {
            event.target.closest('.step-card').remove();
            updateStepTitles();
        }
    });

    // --- Parameter Functions and Listeners ---

    function addParam(paramData = null) {
        const newParam = paramTemplate.content.cloneNode(true);
        const paramCard = newParam.querySelector('.param-card');
        paramsContainer.appendChild(paramCard);
        updateParamTitles();

        if (paramData) {
            paramCard.querySelector('.param-name').value = paramData.name;
            paramCard.querySelector('.param-label').value = paramData.label || ''; // Use label from paramData
            // Add other fields if WorkflowParameter schema expands (type, default, required)
        }
    }

    function updateParamTitles() {
        const params = paramsContainer.querySelectorAll('.param-card');
        params.forEach((param, index) => {
            param.querySelector('.card-title').textContent = `パラメータ ${index + 1}`;
        });
    }

    addParamBtn.addEventListener('click', () => addParam());

    paramsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-param-btn')) {
            event.target.closest('.param-card').remove();
            updateParamTitles();
        }
    });

    // --- Run Workflow Button Listener ---
    confirmRunWorkflowBtn.addEventListener('click', function() {
        const workflowId = modalRunWorkflowIdInput.value;
        const paramInputs = modalParamInputsContainer.querySelectorAll('.modal-param-input');
        const paramsVal = {};
        let allParamsValid = true;

        paramInputs.forEach(input => {
            if (!input.value) {
                allParamsValid = false;
                input.classList.add('is-invalid');
            } else {
                input.classList.remove('is-invalid');
                paramsVal[input.dataset.paramName] = input.value;
            }
        });

        if (!allParamsValid) {
            alert('すべてのパラメータを入力してください。');
            return;
        }

        fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ params_val: paramsVal })
        })
        .then(response => {
            if (!response.ok) return response.json().then(err => { throw new Error(err.detail || 'Unknown error'); });
            return response.json();
        })
        .then(data => {
            alert(`ワークフローが実行キューに追加されました: ${data.message}`);
            runWorkflowModal.hide();
            fetchAndDisplayWorkflows();
        })
        .catch(error => {
            console.error('Error running workflow:', error);
            alert(`ワークフローの実行に失敗しました: ${error.message}`);
        });
    });

    // --- Workflow Form Submission ---
    workflowForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const isEdit = !!workflowIdInput.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${getApiBaseUrl()}/api/workflows/${workflowIdInput.value}` : `${getApiBaseUrl()}/api/workflows`;

        const steps = [];
        stepsContainer.querySelectorAll('.step-card').forEach((stepCard, index) => {
            const jobType = stepCard.querySelector('.step-job-type').value;
            let taskParameters = {};

            if (jobType === 'python') {
                taskParameters = {
                    task_type: 'python',
                    module: stepCard.querySelector('.python-module').value,
                    function: stepCard.querySelector('.python-function').value,
                    args: JSON.parse(stepCard.querySelector('.python-args').value || '[]'),
                    kwargs: JSON.parse(stepCard.querySelector('.python-kwargs').value || '{}')
                };
            } else if (['cmd', 'powershell', 'shell'].includes(jobType)) {
                taskParameters = {
                    task_type: jobType,
                    command: stepCard.querySelector('.shell-command').value,
                    cwd: stepCard.querySelector('.shell-cwd').value || null,
                    env: JSON.parse(stepCard.querySelector('.shell-env').value || '{}')
                };
            } else {
                // Generic type, assuming it still uses a 'target' field
                taskParameters = {
                    task_type: jobType,
                    target: stepCard.querySelector('.step-target-text').value
                };
            }

            steps.push({
                step_order: index + 1,
                name: stepCard.querySelector('.step-name').value,
                task_parameters: taskParameters, // Use the new unified field
                on_failure: stepCard.querySelector('.step-on-failure').value,
                run_in_background: stepCard.querySelector('.step-run-in-background').checked,
            });
        });

        const params = [];
        paramsContainer.querySelectorAll('.param-card').forEach((paramCard) => {
            params.push({
                name: paramCard.querySelector('.param-name').value,
                label: paramCard.querySelector('.param-label').value,
                // Add other fields from WorkflowParameter schema if they exist in the form
            });
        });

        const workflowData = {
            name: document.getElementById('workflow-name').value,
            description: document.getElementById('workflow-description').value,
            schedule: document.getElementById('workflow-schedule').value,
            is_enabled: document.getElementById('workflow-enabled').checked,
            steps: steps,
            params_def: params
        };

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(workflowData)
        })
        .then(response => {
            if (!response.ok) return response.json().then(err => { throw new Error(err.detail || 'Unknown error'); });
            return response.json();
        })
        .then(data => {
            alert(`ワークフロー '${data.name}' が${isEdit ? '更新' : '作成'}されました。`);
            workflowForm.reset();
            stepsContainer.innerHTML = '';
            fetchAndDisplayWorkflows();
        })
        .catch(error => {
            console.error('Error saving workflow:', error);
            alert(`ワークフローの保存に失敗しました: ${error.message}`);
        });
    });

    workflowsListBody.addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('btn-edit-workflow')) {
            const workflowId = target.dataset.workflowId;
            fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}`)
                .then(response => response.json())
                .then(workflow => {
                    workflowFormTitle.textContent = `ワークフロー編集: ${workflow.name}`;
                    workflowIdInput.value = workflow.id;
                    document.getElementById('workflow-name').value = workflow.name;
                    document.getElementById('workflow-description').value = workflow.description;
                    document.getElementById('workflow-schedule').value = workflow.schedule;
                    document.getElementById('workflow-enabled').checked = workflow.is_enabled;

                    stepsContainer.innerHTML = '';
                    workflow.steps.sort((a, b) => a.step_order - b.step_order).forEach(addStep);

                    paramsContainer.innerHTML = '';
                    if (workflow.params_def) {
                        workflow.params_def.forEach(addParam);
                    }

                    window.scrollTo(0, document.body.scrollHeight);
                });
        }

        if (target.classList.contains('btn-run-workflow')) {
            const workflowId = target.dataset.workflowId;
            const workflowName = target.dataset.workflowName;
            openRunWorkflowModal(workflowId, workflowName);
        }

        if (target.classList.contains('btn-delete-workflow')) {
            const workflowId = target.dataset.workflowId;
            if (confirm('本当にこのワークフローを削除しますか？')) {
                fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}`, { method: 'DELETE' })
                    .then(response => {
                        if (response.ok) {
                            alert('ワークフローが削除されました。');
                            fetchAndDisplayWorkflows();
                        }
                        else {
                            throw new Error('削除に失敗しました。');
                        }
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
            .then(() => {
                fetchAndDisplayWorkflows();
            })
            .catch(error => {
                alert(`エラー: ${error.message}`);
                target.checked = !target.checked;
            });
    });

    // --- Initial Load ---
    Promise.all([
        fetchOsInfo(),
        fetchPythonTasks()
    ]).then(() => {
        fetchAndDisplayWorkflows();
    }).catch(error => {
        console.error("Error during initial data load:", error);
        fetchAndDisplayWorkflows();
        alert("初期データの読み込み中にエラーが発生しました。一部の機能が利用できない可能性があります。");
    });

    // --- Run Workflow Modal Logic ---
    function openRunWorkflowModal(workflowId, workflowName) {
        runWorkflowModalLabel.textContent = `ワークフロー実行: ${workflowName}`;
        modalRunWorkflowIdInput.value = workflowId;
        modalParamInputsContainer.innerHTML = '';

        fetch(`${getApiBaseUrl()}/api/workflows/${workflowId}`)
            .then(response => response.json())
            .then(workflow => {
                if (workflow.params_def && workflow.params_def.length > 0) {
                    workflow.params_def.forEach(paramDef => {
                        const paramInputDiv = document.createElement('div');
                        paramInputDiv.classList.add('mb-3');
                        paramInputDiv.innerHTML = `
                            <label for="param-${paramDef.name}" class="form-label">${paramDef.label || paramDef.name}</label>
                            <input type="text" class="form-control modal-param-input" id="param-${paramDef.name}" data-param-name="${paramDef.name}" placeholder="${paramDef.label || paramDef.name}" required>
                        `;
                        modalParamInputsContainer.appendChild(paramInputDiv);
                    });
                }
                else {
                    modalParamInputsContainer.innerHTML = '<p>このワークフローにはパラメータが定義されていません。すぐに実行します。</p>';
                }
                runWorkflowModal.show();
            })
            .catch(error => {
                console.error('Error fetching workflow for modal:', error);
                alert('ワークフロー情報の取得に失敗しました。');
            });
    }
});