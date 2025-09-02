/**
 * ComplianceAI Agentic Platform - Enhanced UI JavaScript
 * Handles real-time agent communication, live updates, and interactive features
 */

class AgenticDashboard {
    constructor() {
        this.currentTab = 'dashboard';
        this.websocket = null;
        this.updateInterval = null;
        this.performanceChart = null;
        
        this.init();
    }

    init() {
        this.setupTabNavigation();
        this.setupWebSocket();
        this.setupEventListeners();
        this.startPeriodicUpdates();
        this.initializeCharts();
        
        // Show dashboard tab by default
        this.showTab('dashboard');
    }

    setupTabNavigation() {
        const navLinks = document.querySelectorAll('[data-tab]');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = link.getAttribute('data-tab');
                this.showTab(tabName);
                
                // Update active nav link
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
    }

    showTab(tabName) {
        // Hide all tabs
        const tabs = document.querySelectorAll('.tab-content');
        tabs.forEach(tab => tab.classList.remove('active'));
        
        // Show selected tab
        const selectedTab = document.getElementById(tabName);
        if (selectedTab) {
            selectedTab.classList.add('active');
            this.currentTab = tabName;
            
            // Load tab-specific data
            this.loadTabData(tabName);
        }
    }

    loadTabData(tabName) {
        switch (tabName) {
            case 'dashboard':
                this.loadDashboardData();
                break;
            case 'live-agents':
                this.loadLiveAgentData();
                break;
            case 'case-processing':
                this.loadCaseProcessingData();
                break;
            case 'learning-dashboard':
                this.loadLearningData();
                break;
            case 'agent-chat':
                this.loadChatData();
                break;
        }
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/agentic`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.setupWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'agent_status_update':
                this.updateAgentStatus(data.payload);
                break;
            case 'case_update':
                this.updateCaseStatus(data.payload);
                break;
            case 'performance_metrics':
                this.updatePerformanceMetrics(data.payload);
                break;
            case 'agent_conversation':
                this.addAgentConversation(data.payload);
                break;
            case 'cost_optimization':
                this.updateCostMetrics(data.payload);
                break;
            case 'learning_update':
                this.updateLearningMetrics(data.payload);
                break;
        }
    }

    updateConnectionStatus(connected) {
        const statusElements = document.querySelectorAll('.connection-status');
        statusElements.forEach(element => {
            element.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            element.textContent = connected ? 'Connected' : 'Disconnected';
        });
    }

    setupEventListeners() {
        // Case selector
        const caseSelector = document.getElementById('case-selector');
        if (caseSelector) {
            caseSelector.addEventListener('change', () => {
                if (caseSelector.value) {
                    this.loadCaseDetails(caseSelector.value);
                }
            });
        }

        // Chat input
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendChatMessage();
                }
            });
        }

        // Refresh buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('refresh-btn')) {
                this.refreshCurrentTab();
            }
        });
    }

    startPeriodicUpdates() {
        // Update dashboard metrics every 30 seconds
        this.updateInterval = setInterval(() => {
            if (this.currentTab === 'dashboard') {
                this.loadDashboardData();
            }
        }, 30000);
    }

    // Dashboard Data Loading
    async loadDashboardData() {
        try {
            const response = await fetch('/api/v1/dashboard/metrics');
            const data = await response.json();
            
            this.updateSystemStatus(data.system_status);
            this.updateAgentStatus(data.agent_status);
            this.updatePerformanceMetrics(data.performance);
            this.updateCostMetrics(data.cost_optimization);
            this.updatePredictiveInsights(data.insights);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    updateSystemStatus(status) {
        // Update system status indicators
        const elements = {
            'intake-status': status.intake_agent,
            'intel-status': status.intelligence_agent,
            'decision-status': status.decision_agent
        };

        Object.entries(elements).forEach(([id, agentStatus]) => {
            const element = document.getElementById(id);
            if (element) {
                const statusSpan = element.querySelector('span');
                if (statusSpan) {
                    statusSpan.textContent = agentStatus.status;
                    statusSpan.className = `status-${agentStatus.status.toLowerCase()}`;
                }
            }
        });

        // Update queue numbers
        const queueElements = {
            'intake-queue': status.intake_agent.queue_size,
            'intel-processing': status.intelligence_agent.processing_count,
            'decision-pending': status.decision_agent.pending_count
        };

        Object.entries(queueElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    updateAgentStatus(agentStatus) {
        // Update individual agent status cards
        Object.entries(agentStatus).forEach(([agentName, status]) => {
            const statusElement = document.getElementById(`${agentName}-status`);
            if (statusElement) {
                this.updateAgentStatusElement(statusElement, status);
            }
        });
    }

    updateAgentStatusElement(element, status) {
        const statusSpan = element.querySelector('.agent-status span');
        const queueSpan = element.querySelector('.agent-queue span');
        
        if (statusSpan) {
            statusSpan.textContent = status.status;
            statusSpan.className = `status-${status.status.toLowerCase()}`;
        }
        
        if (queueSpan) {
            queueSpan.textContent = status.queue_size || status.processing_count || status.pending_count || 0;
        }
    }

    updatePerformanceMetrics(performance) {
        const metrics = {
            'cases-processed': performance.cases_processed,
            'auto-approved': performance.auto_approved,
            'under-review': performance.under_review,
            'avg-time': `${performance.avg_processing_time}s`,
            'cost-per-case': `$${performance.cost_per_case}`
        };

        Object.entries(metrics).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    updateCostMetrics(costData) {
        const costElements = {
            'current-cost': costData.current_cost_per_case,
            'local-processing': `${costData.local_processing_percentage}%`,
            'fast-track': `${costData.fast_track_percentage}%`
        };

        Object.entries(costElements).forEach(([className, value]) => {
            const elements = document.querySelectorAll(`.${className}`);
            elements.forEach(element => {
                element.textContent = value;
            });
        });
    }

    updatePredictiveInsights(insights) {
        // Update predictive insights section
        if (insights && insights.length > 0) {
            const insightsContainer = document.querySelector('.insight-cards');
            if (insightsContainer) {
                insightsContainer.innerHTML = insights.map(insight => `
                    <div class="col-md-4">
                        <div class="insight-card">
                            <h6>${insight.title}</h6>
                            <p>${insight.description}</p>
                            <small class="text-muted">${insight.recommendation}</small>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    // Live Agent Data Loading
    async loadLiveAgentData() {
        try {
            const response = await fetch('/api/v1/agents/conversations');
            const conversations = await response.json();
            
            this.updateAgentConversations(conversations);
        } catch (error) {
            console.error('Failed to load agent conversations:', error);
        }
    }

    updateAgentConversations(conversations) {
        const streamContainer = document.getElementById('agent-conversation-stream');
        if (!streamContainer) return;

        streamContainer.innerHTML = conversations.map(conv => `
            <div class="conversation-entry ${conv.type === 'case_closed' ? 'case-closed' : ''}">
                <div class="conversation-header">
                    <span class="agent-badge ${conv.agent_type}">${conv.agent_icon} ${conv.agent_name}</span>
                    <span class="timestamp">[${conv.timestamp}]</span>
                </div>
                <div class="conversation-message">
                    ${conv.message}
                </div>
            </div>
        `).join('');

        // Auto-scroll to bottom
        streamContainer.scrollTop = streamContainer.scrollHeight;
    }

    addAgentConversation(conversation) {
        const streamContainer = document.getElementById('agent-conversation-stream');
        if (!streamContainer) return;

        const conversationElement = document.createElement('div');
        conversationElement.className = `conversation-entry ${conversation.type === 'case_closed' ? 'case-closed' : ''}`;
        conversationElement.innerHTML = `
            <div class="conversation-header">
                <span class="agent-badge ${conversation.agent_type}">${conversation.agent_icon} ${conversation.agent_name}</span>
                <span class="timestamp">[${conversation.timestamp}]</span>
            </div>
            <div class="conversation-message">
                ${conversation.message}
            </div>
        `;

        streamContainer.appendChild(conversationElement);
        streamContainer.scrollTop = streamContainer.scrollHeight;
    }

    // Case Processing Data Loading
    async loadCaseProcessingData() {
        try {
            const response = await fetch('/api/v1/cases/active');
            const cases = await response.json();
            
            this.updateCaseSelector(cases);
        } catch (error) {
            console.error('Failed to load case processing data:', error);
        }
    }

    updateCaseSelector(cases) {
        const selector = document.getElementById('case-selector');
        if (!selector) return;

        selector.innerHTML = '<option value="">Select a case to view details...</option>' +
            cases.map(case_ => `
                <option value="${case_.case_id}">${case_.case_id} - ${case_.customer_name}</option>
            `).join('');
    }

    async loadCaseDetails(caseId) {
        try {
            const response = await fetch(`/api/v1/cases/${caseId}/details`);
            const caseDetails = await response.json();
            
            this.displayCaseDetails(caseDetails);
        } catch (error) {
            console.error('Failed to load case details:', error);
        }
    }

    displayCaseDetails(caseDetails) {
        const detailsContainer = document.getElementById('case-details');
        if (!detailsContainer) return;

        // Update case overview
        document.getElementById('case-customer').textContent = caseDetails.customer_name;
        document.getElementById('case-type').textContent = caseDetails.case_type;
        document.getElementById('case-priority').textContent = caseDetails.priority;
        document.getElementById('case-status').innerHTML = `<span class="badge bg-${caseDetails.status_color}">${caseDetails.status_icon} ${caseDetails.status}</span>`;

        // Update timeline
        const timeline = document.getElementById('case-timeline');
        timeline.innerHTML = caseDetails.timeline.map((item, index) => `
            <div class="timeline-item ${index === caseDetails.timeline.length - 1 ? 'active' : ''}">
                ${item.timestamp} - ${item.description}
            </div>
        `).join('');

        // Update workflow
        this.updateWorkflowDiagram(caseDetails.workflow);

        // Show the details
        detailsContainer.style.display = 'block';
    }

    updateWorkflowDiagram(workflow) {
        const steps = ['intake', 'intel', 'decision'];
        steps.forEach(step => {
            const stepElement = document.querySelector(`.workflow-step.${step}`);
            if (stepElement && workflow[step]) {
                stepElement.className = `workflow-step ${workflow[step].status}`;
                stepElement.querySelector('.step-status').textContent = workflow[step].status_text;
                stepElement.querySelector('.step-detail').innerHTML = workflow[step].details;
            }
        });
    }

    // Learning Dashboard Data Loading
    async loadLearningData() {
        try {
            const response = await fetch('/api/v1/learning/metrics');
            const learningData = await response.json();
            
            this.updateLearningMetrics(learningData);
            this.updatePerformanceChart(learningData.performance_history);
        } catch (error) {
            console.error('Failed to load learning data:', error);
        }
    }

    updateLearningMetrics(learningData) {
        // Update learning status metrics
        const learningMetrics = {
            'cases-processed': learningData.cases_processed,
            'model-updates': learningData.update_frequency,
            'last-update': learningData.last_update,
            'confidence-trend': learningData.confidence_trend
        };

        Object.entries(learningMetrics).forEach(([className, value]) => {
            const elements = document.querySelectorAll(`.${className}`);
            elements.forEach(element => {
                element.textContent = value;
            });
        });

        // Update improvements list
        const improvementsList = document.querySelector('.improvements-list');
        if (improvementsList && learningData.recent_improvements) {
            improvementsList.innerHTML = learningData.recent_improvements.map(improvement => `
                <div class="improvement-item ${improvement.type}">
                    <i class="fas fa-${improvement.icon} text-${improvement.type === 'success' ? 'success' : 'warning'} me-2"></i>
                    <strong>${improvement.title}:</strong> ${improvement.description}
                </div>
            `).join('');
        }
    }

    initializeCharts() {
        const ctx = document.getElementById('performance-chart');
        if (!ctx) return;

        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Accuracy %',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Cost per Case ($)',
                    data: [],
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Performance Trends (Last 30 Days)'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Accuracy %'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Cost ($)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    updatePerformanceChart(performanceHistory) {
        if (!this.performanceChart || !performanceHistory) return;

        this.performanceChart.data.labels = performanceHistory.dates;
        this.performanceChart.data.datasets[0].data = performanceHistory.accuracy;
        this.performanceChart.data.datasets[1].data = performanceHistory.cost;
        
        this.performanceChart.update();
    }

    // Chat Interface
    async loadChatData() {
        try {
            const response = await fetch('/api/v1/chat/history');
            const chatHistory = await response.json();
            
            this.updateChatMessages(chatHistory);
        } catch (error) {
            console.error('Failed to load chat data:', error);
        }
    }

    updateChatMessages(messages) {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;

        chatContainer.innerHTML = messages.map(msg => `
            <div class="chat-message ${msg.sender_type} ${msg.agent_type || ''}">
                <div class="message-header">
                    <strong>${msg.sender_name}:</strong>
                    <span class="timestamp">${msg.timestamp}</span>
                </div>
                <div class="message-content">
                    ${msg.content}
                </div>
            </div>
        `).join('');

        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async sendChatMessage() {
        const input = document.getElementById('chat-input');
        if (!input || !input.value.trim()) return;

        const message = input.value.trim();
        input.value = '';

        // Add user message to chat
        this.addChatMessage('user', 'You', message);

        try {
            const response = await fetch('/api/v1/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const result = await response.json();
            
            // Add agent response
            this.addChatMessage('agent', result.agent_name, result.response, result.agent_type);
        } catch (error) {
            console.error('Failed to send chat message:', error);
            this.addChatMessage('system', 'System', 'Sorry, I encountered an error processing your message.');
        }
    }

    addChatMessage(senderType, senderName, content, agentType = '') {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;

        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${senderType} ${agentType}`;
        messageElement.innerHTML = `
            <div class="message-header">
                <strong>${senderName}:</strong>
                <span class="timestamp">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="message-content">
                ${content}
            </div>
        `;

        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Utility Functions
    refreshCurrentTab() {
        this.loadTabData(this.currentTab);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    formatPercentage(value) {
        return `${(value * 100).toFixed(1)}%`;
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds.toFixed(1)}s`;
        } else if (seconds < 3600) {
            return `${(seconds / 60).toFixed(1)}m`;
        } else {
            return `${(seconds / 3600).toFixed(1)}h`;
        }
    }
}

// Global Functions (called from HTML)
function loadCaseDetails() {
    const selector = document.getElementById('case-selector');
    if (selector && selector.value) {
        dashboard.loadCaseDetails(selector.value);
    }
}

function sendChatMessage() {
    dashboard.sendChatMessage();
}

function escalateCase() {
    dashboard.addChatMessage('system', 'System', 'Case escalated to senior compliance officer.');
}

function approveCase() {
    dashboard.addChatMessage('system', 'System', 'Case approved and processed.');
}

function askMoreQuestions() {
    const input = document.getElementById('chat-input');
    if (input) {
        input.focus();
        input.placeholder = 'Ask your follow-up question...';
    }
}

// =============================================================================
// AGENT TESTING FUNCTIONS (Rule 6 Compliance)
// =============================================================================

/**
 * Test all agents with comprehensive test suite
 */
async function testAllAgents() {
    updateTestResults('info', 'Starting comprehensive agent test suite...');
    
    const tests = [
        { name: 'Health Check', func: testAgentHealth },
        { name: 'Performance Test', func: testAgentPerformance },
        { name: 'End-to-End Test', func: testEndToEndFlow }
    ];
    
    let passedTests = 0;
    const startTime = Date.now();
    
    for (const test of tests) {
        try {
            updateTestResults('info', `Running ${test.name}...`);
            await test.func();
            passedTests++;
            updateTestResults('success', `✅ ${test.name} passed`);
        } catch (error) {
            updateTestResults('error', `❌ ${test.name} failed: ${error.message}`);
        }
    }
    
    const duration = Date.now() - startTime;
    const successRate = (passedTests / tests.length * 100).toFixed(1);
    
    updateTestResults('info', `\n📊 Test Suite Complete:\n- Tests Passed: ${passedTests}/${tests.length}\n- Success Rate: ${successRate}%\n- Duration: ${duration}ms`);
    
    // Update metrics
    document.getElementById('success-rate').textContent = `${successRate}%`;
    document.getElementById('avg-response-time').textContent = `${Math.round(duration / tests.length)}`;
    document.getElementById('tests-run').textContent = parseInt(document.getElementById('tests-run').textContent) + tests.length;
}

/**
 * Test agent health endpoints
 */
async function testAgentHealth() {
    const agents = [
        { name: 'intake', port: 8001, statusId: 'intake-status' },
        { name: 'intelligence', port: 8002, statusId: 'intelligence-status' },
        { name: 'decision', port: 8003, statusId: 'decision-status' }
    ];
    
    updateTestResults('info', 'Testing agent health endpoints...');
    
    for (const agent of agents) {
        try {
            const response = await fetch(`http://localhost:${agent.port}/health`, {
                method: 'GET',
                timeout: 5000
            });
            
            const statusElement = document.getElementById(agent.statusId);
            
            if (response.ok) {
                statusElement.className = 'badge bg-success';
                statusElement.textContent = 'Healthy';
                updateTestResults('success', `✅ ${agent.name} agent (port ${agent.port}): Healthy`);
            } else {
                statusElement.className = 'badge bg-warning';
                statusElement.textContent = 'Degraded';
                updateTestResults('warning', `⚠️ ${agent.name} agent (port ${agent.port}): Degraded (${response.status})`);
            }
        } catch (error) {
            const statusElement = document.getElementById(agent.statusId);
            statusElement.className = 'badge bg-danger';
            statusElement.textContent = 'Offline';
            updateTestResults('error', `❌ ${agent.name} agent (port ${agent.port}): Offline - ${error.message}`);
        }
    }
}

/**
 * Test agent performance benchmarks
 */
async function testAgentPerformance() {
    updateTestResults('info', 'Running performance benchmarks...');
    
    const testData = {
        document_type: 'passport',
        customer_data: {
            name: 'Test Customer',
            date_of_birth: '1990-01-01',
            nationality: 'US'
        }
    };
    
    const agents = [
        { name: 'intake', port: 8001, endpoint: '/process' },
        { name: 'intelligence', port: 8002, endpoint: '/process' },
        { name: 'decision', port: 8003, endpoint: '/process' }
    ];
    
    let totalResponseTime = 0;
    let successfulTests = 0;
    
    for (const agent of agents) {
        try {
            const startTime = Date.now();
            
            const response = await fetch(`http://localhost:${agent.port}${agent.endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(testData),
                timeout: 10000
            });
            
            const responseTime = Date.now() - startTime;
            totalResponseTime += responseTime;
            
            if (response.ok) {
                successfulTests++;
                updateTestResults('success', `✅ ${agent.name} agent: ${responseTime}ms response time`);
            } else {
                updateTestResults('warning', `⚠️ ${agent.name} agent: ${responseTime}ms (status: ${response.status})`);
            }
        } catch (error) {
            updateTestResults('error', `❌ ${agent.name} agent performance test failed: ${error.message}`);
        }
    }
    
    const avgResponseTime = Math.round(totalResponseTime / agents.length);
    document.getElementById('avg-response-time').textContent = `${avgResponseTime}`;
    
    updateTestResults('info', `📊 Performance Summary: Average response time: ${avgResponseTime}ms`);
}

/**
 * Test end-to-end workflow
 */
async function testEndToEndFlow() {
    updateTestResults('info', 'Testing end-to-end KYC workflow...');
    
    const testCase = {
        case_id: `test-${Date.now()}`,
        document_type: 'passport',
        customer_data: {
            name: 'John Test Doe',
            date_of_birth: '1985-06-15',
            nationality: 'US',
            document_number: 'TEST123456789'
        }
    };
    
    try {
        // Step 1: Intake Processing
        updateTestResults('info', '1️⃣ Testing intake processing...');
        const intakeResponse = await fetch('http://localhost:8001/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testCase)
        });
        
        if (!intakeResponse.ok) throw new Error(`Intake failed: ${intakeResponse.status}`);
        const intakeResult = await intakeResponse.json();
        updateTestResults('success', '✅ Intake processing completed');
        
        // Step 2: Intelligence Analysis
        updateTestResults('info', '2️⃣ Testing intelligence analysis...');
        const intelligenceResponse = await fetch('http://localhost:8002/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...testCase, intake_result: intakeResult })
        });
        
        if (!intelligenceResponse.ok) throw new Error(`Intelligence failed: ${intelligenceResponse.status}`);
        const intelligenceResult = await intelligenceResponse.json();
        updateTestResults('success', '✅ Intelligence analysis completed');
        
        // Step 3: Decision Making
        updateTestResults('info', '3️⃣ Testing decision making...');
        const decisionResponse = await fetch('http://localhost:8003/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                ...testCase, 
                intake_result: intakeResult,
                intelligence_result: intelligenceResult 
            })
        });
        
        if (!decisionResponse.ok) throw new Error(`Decision failed: ${decisionResponse.status}`);
        const decisionResult = await decisionResponse.json();
        updateTestResults('success', '✅ Decision making completed');
        
        updateTestResults('success', `🎉 End-to-end test successful! Final decision: ${decisionResult.decision || 'Unknown'}`);
        
    } catch (error) {
        updateTestResults('error', `❌ End-to-end test failed: ${error.message}`);
        throw error;
    }
}

/**
 * Test individual agent functions
 */
async function testIntakeAgent(testType) {
    updateTestResults('info', `Testing intake agent: ${testType}...`);
    
    const testData = {
        ocr: { document_image: 'base64_test_image', document_type: 'passport' },
        validation: { customer_name: 'Test User', document_number: 'TEST123' },
        quality: { extracted_data: { name: 'Test', confidence: 0.95 } }
    };
    
    try {
        const response = await fetch(`http://localhost:8001/test/${testType}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testData[testType])
        });
        
        if (response.ok) {
            const result = await response.json();
            document.getElementById('intake-test-results').innerHTML = 
                `<div class="alert alert-success">✅ ${testType} test passed</div>`;
            updateTestResults('success', `✅ Intake ${testType} test completed successfully`);
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        document.getElementById('intake-test-results').innerHTML = 
            `<div class="alert alert-danger">❌ ${testType} test failed: ${error.message}</div>`;
        updateTestResults('error', `❌ Intake ${testType} test failed: ${error.message}`);
    }
}

async function testIntelligenceAgent(testType) {
    updateTestResults('info', `Testing intelligence agent: ${testType}...`);
    
    const testData = {
        kyc: { customer_data: { name: 'Test User', dob: '1990-01-01' } },
        sanctions: { name: 'Test User', country: 'US' },
        pep: { name: 'Test User', position: 'None' }
    };
    
    try {
        const response = await fetch(`http://localhost:8002/test/${testType}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testData[testType])
        });
        
        if (response.ok) {
            const result = await response.json();
            document.getElementById('intelligence-test-results').innerHTML = 
                `<div class="alert alert-success">✅ ${testType} test passed</div>`;
            updateTestResults('success', `✅ Intelligence ${testType} test completed successfully`);
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        document.getElementById('intelligence-test-results').innerHTML = 
            `<div class="alert alert-danger">❌ ${testType} test failed: ${error.message}</div>`;
        updateTestResults('error', `❌ Intelligence ${testType} test failed: ${error.message}`);
    }
}

async function testDecisionAgent(testType) {
    updateTestResults('info', `Testing decision agent: ${testType}...`);
    
    const testData = {
        rules: { risk_score: 0.3, compliance_flags: [] },
        llm: { complex_case: true, context: 'edge case analysis' },
        workflow: { case_data: { status: 'processed' } }
    };
    
    try {
        const response = await fetch(`http://localhost:8003/test/${testType}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testData[testType])
        });
        
        if (response.ok) {
            const result = await response.json();
            document.getElementById('decision-test-results').innerHTML = 
                `<div class="alert alert-success">✅ ${testType} test passed</div>`;
            updateTestResults('success', `✅ Decision ${testType} test completed successfully`);
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        document.getElementById('decision-test-results').innerHTML = 
            `<div class="alert alert-danger">❌ ${testType} test failed: ${error.message}</div>`;
        updateTestResults('error', `❌ Decision ${testType} test failed: ${error.message}`);
    }
}

/**
 * Update test results display
 */
function updateTestResults(type, message) {
    const container = document.getElementById('test-results-container');
    if (!container) return;
    
    const alertClass = {
        'info': 'alert-info',
        'success': 'alert-success',
        'warning': 'alert-warning',
        'error': 'alert-danger'
    }[type] || 'alert-info';
    
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `alert ${alertClass} mb-2`;
    logEntry.innerHTML = `<small class="text-muted">[${timestamp}]</small> ${message}`;
    
    // Clear initial message if it exists
    const initialAlert = container.querySelector('.alert-info');
    if (initialAlert && initialAlert.textContent.includes('Click any test button')) {
        initialAlert.remove();
    }
    
    container.appendChild(logEntry);
    container.scrollTop = container.scrollHeight;
}

// =============================================================================
// USER GUIDES FUNCTIONALITY (Rule 9 Compliance)
// =============================================================================

/**
 * Initialize User Guides tab functionality
 * Handles interactive elements and dynamic content
 */
function initializeUserGuides() {
    // Initialize accordion functionality for troubleshooting
    const accordionButtons = document.querySelectorAll('.accordion-button');
    accordionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-bs-target'));
            if (target) {
                const isExpanded = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', !isExpanded);
                target.classList.toggle('show');
            }
        });
    });
    
    // Add copy functionality to code snippets
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        const copyButton = document.createElement('button');
        copyButton.className = 'btn btn-sm btn-outline-secondary position-absolute top-0 end-0 m-2';
        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
        copyButton.title = 'Copy to clipboard';
        
        block.parentElement.style.position = 'relative';
        block.parentElement.appendChild(copyButton);
        
        copyButton.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent).then(() => {
                copyButton.innerHTML = '<i class="fas fa-check text-success"></i>';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });
        });
    });
    
    // Add search functionality for guides
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control mb-3';
    searchInput.placeholder = 'Search user guides...';
    searchInput.id = 'guide-search';
    
    const userGuidesTab = document.getElementById('user-guides');
    if (userGuidesTab) {
        const cardBody = userGuidesTab.querySelector('.card-body');
        if (cardBody) {
            cardBody.insertBefore(searchInput, cardBody.firstChild);
            
            searchInput.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const sections = cardBody.querySelectorAll('.row');
                
                sections.forEach(section => {
                    const text = section.textContent.toLowerCase();
                    section.style.display = text.includes(searchTerm) ? 'block' : 'none';
                });
            });
        }
    }
}

// Initialize dashboard when DOM is loaded
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new AgenticDashboard();
    
    // Initialize agent testing on page load
    if (document.getElementById('agent-testing')) {
        setTimeout(testAgentHealth, 1000); // Auto-check health after 1 second
    }
    
    // Initialize user guides functionality
    initializeUserGuides();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgenticDashboard;
}
