// src/webgui/static/workflows.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';

    // Main elements
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

    // Modal elements
    const runWorkflowModal = new bootstrap.Modal(document.getElementById('runWorkflowModal'));
    const runWorkflowModalLabel = document.getElementById('runWorkflowModalLabel');
    const modalRunWorkflowIdInput = document.getElementById('modal-run-workflow-id');
    const modalParamInputsContainer = document.getElementById('modal-param-inputs');
    const confirmRunWorkflowBtn = document.getElementById('confirm-run-workflow-btn');

    let serverOsType = '';
    let availablePythonTasks = [];

    // --- Utility Functions ---

    function fetchAndDisplayWorkflows() {
        fetch(`${API_BASE_URL}/api/workflows`)
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

    function toggleTargetInput(stepCard, jobType) {
        const textTarget = stepCard.querySelector('.step-target-text');
        const pythonTarget = stepCard.querySelector('.step-target-python');

        if (jobType === 'python') {
            textTarget.style.display = 'none';
            textTarget.required = false;
            pythonTarget.style.display = 'block';
            pythonTarget.required = true;
        } else {
            textTarget.style.display = 'block';
            textTarget.required = true;
            pythonTarget.style.display = 'none';
            pythonTarget.required = false;
        }
    }

    function addStep(stepData = null) {
        const newStep = stepTemplate.content.cloneNode(true);
        const stepCard = newStep.querySelector('.step-card');
        const jobTypeSelect = stepCard.querySelector('.step-job-type');
        const pythonTargetSelect = stepCard.querySelector('.step-target-python');

        // Populate python tasks dropdown
        availablePythonTasks.forEach(task => {
            const option = document.createElement('option');
            option.value = task;
            option.textContent = task;
            pythonTargetSelect.appendChild(option);
        });

        stepsContainer.appendChild(stepCard);
        updateStepTitles();
        initializeJobTypeOptions(stepCard);

        jobTypeSelect.addEventListener('change', () => {
            toggleTargetInput(stepCard, jobTypeSelect.value);
        });

        if (stepData) {
            stepCard.querySelector('.step-name').value = stepData.name;
            jobTypeSelect.value = stepData.job_type;
            stepCard.querySelector('.step-on-failure').value = stepData.on_failure;
            stepCard.querySelector('.step-run-in-background').checked = stepData.run_in_background;
            
            // Set target value after toggling visibility
            toggleTargetInput(stepCard, stepData.job_type);
            if (stepData.job_type === 'python') {
                pythonTargetSelect.value = stepData.target;
            } else {
                stepCard.querySelector('.step-target-text').value = stepData.target;
            }
        } else {
            // Default view
            toggleTargetInput(stepCard, jobTypeSelect.value);
        }
    }

    function updateStepTitles() {
        const steps = stepsContainer.querySelectorAll('.step-card');
        steps.forEach((step, index) => {
            step.querySelector('.card-title').textContent = `ステップ ${index + 1}`;
        });
    }

    function initializeJobTypeOptions(container) {
        const options = container.querySelectorAll('option.os-specific');
        options.forEach(option => {
            const supportedOs = option.dataset.os;
            if (serverOsType.toLowerCase().includes(supportedOs)) {
                option.style.display = 'block';
            }
        });
    }

    function fetchOsInfo() {
        return fetch(`${API_BASE_URL}/api/system/os`)
            .then(response => response.json())
            .then(data => {
                serverOsType = data.os_type;
            })
            .catch(error => console.error('Error fetching OS info:', error));
    }

    function fetchPythonTasks() {
        return fetch(`${API_BASE_URL}/api/python-tasks`)
            .then(response => response.json())
            .then(data => {
                availablePythonTasks = data;
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
            paramCard.querySelector('.param-label').value = paramData.label;
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
                input.classList.add('is-invalid'); // Bootstrap validation class
            } else {
                input.classList.remove('is-invalid');
                paramsVal[input.dataset.paramName] = input.value;
            }
        });

        if (!allParamsValid) {
            alert('すべてのパラメータを入力してください。');
            return;
        }

        fetch(`${API_BASE_URL}/api/workflows/${workflowId}/run`, {
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
            fetchAndDisplayWorkflows(); // Refresh list to show potential status changes
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
        const url = isEdit ? `${API_BASE_URL}/api/workflows/${workflowIdInput.value}` : `${API_BASE_URL}/api/workflows`;

        const steps = [];
        stepsContainer.querySelectorAll('.step-card').forEach((stepCard, index) => {
            const jobType = stepCard.querySelector('.step-job-type').value;
            let targetValue;
            if (jobType === 'python') {
                targetValue = stepCard.querySelector('.step-target-python').value;
            } else {
                targetValue = stepCard.querySelector('.step-target-text').value;
            }

            steps.push({
                step_order: index + 1,
                name: stepCard.querySelector('.step-name').value,
                job_type: jobType,
                target: targetValue,
                on_failure: stepCard.querySelector('.step-on-failure').value,
                run_in_background: stepCard.querySelector('.step-run-in-background').checked,
            });
        });

        const params = [];
        paramsContainer.querySelectorAll('.param-card').forEach((paramCard) => {
            params.push({
                name: paramCard.querySelector('.param-name').value,
                label: paramCard.querySelector('.param-label').value,
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
            fetch(`${API_BASE_URL}/api/workflows/${workflowId}`)
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
                fetch(`${API_BASE_URL}/api/workflows/${workflowId}`, { method: 'DELETE' })
                    .then(response => {
                        if (response.ok) {
                            alert('ワークフローが削除されました。');
                            fetchAndDisplayWorkflows();
                        } else {
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
        
        fetch(`${API_BASE_URL}/api/workflows/${workflowId}/${action}`, { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('ステータスの変更に失敗しました。');
                return response.json();
            })
            .then(() => {
                fetchAndDisplayWorkflows();
            })
            .catch(error => {
                alert(`エラー: ${error.message}`);
                target.checked = !target.checked; // Revert on failure
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
        // Still try to display workflows, as OS info might not be critical
        fetchAndDisplayWorkflows();
        alert("初期データの読み込み中にエラーが発生しました。一部の機能が利用できない可能性があります。");
    });

    // --- Run Workflow Modal Logic ---
    function openRunWorkflowModal(workflowId, workflowName) {
    runWorkflowModalLabel.textContent = `ワークフロー実行: ${workflowName}`;
    modalRunWorkflowIdInput.value = workflowId;
    modalParamInputsContainer.innerHTML = ''; // Clear previous inputs

    fetch(`${API_BASE_URL}/api/workflows/${workflowId}`)
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
            } else {
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
