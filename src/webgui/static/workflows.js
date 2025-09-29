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

    let serverOsType = '';

    // --- Utility Functions ---

    function fetchAndDisplayWorkflows() {
        fetch(`${API_BASE_URL}/api/workflows`)
            .then(response => response.json())
            .then(workflows => {
                workflowsListBody.innerHTML = '';
                workflows.forEach(wf => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td><span class="badge bg-${wf.is_enabled ? 'success' : 'secondary'}">${wf.is_enabled ? '有効' : '無効'}</span></td>
                        <td><a href="/workflows/${wf.id}">${wf.name}</a></td>
                        <td>${wf.description || ''}</td>
                        <td>${wf.schedule || 'N/A'}</td>
                        <td>
                            <a href="/workflows/${wf.id}" class="btn btn-sm btn-primary">詳細</a>
                            <button class="btn btn-sm btn-info btn-edit-workflow" data-workflow-id="${wf.id}">編集</button>
                            <button class="btn btn-sm btn-danger btn-delete-workflow" data-workflow-id="${wf.id}">削除</button>
                        </td>
                    `;
                    workflowsListBody.appendChild(row);
                });
            })
            .catch(error => console.error('Error fetching workflows:', error));
    }

    function addStep(stepData = null) {
        const newStep = stepTemplate.content.cloneNode(true);
        const stepCard = newStep.querySelector('.step-card');
        stepsContainer.appendChild(stepCard);
        updateStepTitles();
        initializeJobTypeOptions(stepCard);

        if (stepData) {
            stepCard.querySelector('.step-name').value = stepData.name;
            stepCard.querySelector('.step-job-type').value = stepData.job_type;
            stepCard.querySelector('.step-target').value = stepData.target;
            stepCard.querySelector('.step-on-failure').value = stepData.on_failure;
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

    // --- Event Listeners ---

    addStepBtn.addEventListener('click', () => addStep());

    stepsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-step-btn')) {
            event.target.closest('.step-card').remove();
            updateStepTitles();
        }
    });

    workflowForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const isEdit = !!workflowIdInput.value;
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `${API_BASE_URL}/api/workflows/${workflowIdInput.value}` : `${API_BASE_URL}/api/workflows`;

        const steps = [];
        stepsContainer.querySelectorAll('.step-card').forEach((stepCard, index) => {
            steps.push({
                step_order: index + 1,
                name: stepCard.querySelector('.step-name').value,
                job_type: stepCard.querySelector('.step-job-type').value,
                target: stepCard.querySelector('.step-target').value,
                on_failure: stepCard.querySelector('.step-on-failure').value,
            });
        });

        const workflowData = {
            name: document.getElementById('workflow-name').value,
            description: document.getElementById('workflow-description').value,
            schedule: document.getElementById('workflow-schedule').value,
            is_enabled: document.getElementById('workflow-enabled').checked,
            steps: steps
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

                    window.scrollTo(0, document.body.scrollHeight);
                });
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

    // --- Initial Load ---
    fetchOsInfo().then(() => {
        fetchAndDisplayWorkflows();
    });
});
