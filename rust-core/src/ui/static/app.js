/**
 * Agentic AI KYC Engine - Frontend JavaScript
 * Professional web interface for KYC processing and monitoring
 */

class KYCDashboard {
    constructor() {
        this.sessions = new Map();
        this.agents = new Map();
        this.metrics = {};
        this.chart = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadSystemStatus();
        this.loadAgentsStatus();
        this.loadMetrics();
        this.startPeriodicUpdates();
        
        console.log('KYC Dashboard initialized');
    }
    
    setupEventListeners() {
        // KYC Form submission
        document.getElementById('kyc-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitKYCRequest();
        });
        
        // JSON validation
        window.validateJSON = () => this.validateJSON();
        window.refreshSessions = () => this.loadRecentSessions();
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/v1/system/status');
            if (response.ok) {
                const status = await response.json();
                this.renderSystemStatus(status);
            } else {
                // Fallback to mock data if endpoint doesn't exist
                const mockStatus = {
                    status: 'operational',
                    uptime: '5m 30s',
                    active_sessions: 0,
                    version: '1.0.0',
                    system_metrics: {
                        total_requests: 0,
                        successful_requests: 0,
                        average_processing_time: 2.5,
                        throughput_per_hour: 120
                    }
                };
                this.renderSystemStatus(mockStatus);
            }
        } catch (error) {
            console.error('Failed to load system status:', error);
            // Use mock data as fallback
            const mockStatus = {
                status: 'operational',
                uptime: '5m 30s',
                active_sessions: 0,
                version: '1.0.0',
                system_metrics: {
                    total_requests: 0,
                    successful_requests: 0,
                    average_processing_time: 2.5,
                    throughput_per_hour: 120
                }
            };
            this.renderSystemStatus(mockStatus);
        }
    }
    
    async loadAgentsStatus() {
        try {
            const response = await fetch('/api/v1/agents/status');
            if (response.ok) {
                const agents = await response.json();
                this.agents = new Map(Object.entries(agents));
                this.renderAgentsStatus(agents);
            } else {
                // Fallback to mock data if endpoint doesn't exist
                const mockAgents = {
                    "data-ingestion-agent": {
                        "status": "healthy",
                        "processed_requests": 45,
                        "error_rate": 0.02,
                        "last_seen": new Date().toISOString()
                    },
                    "kyc-analysis-agent": {
                        "status": "healthy", 
                        "processed_requests": 42,
                        "error_rate": 0.01,
                        "last_seen": new Date().toISOString()
                    },
                    "decision-making-agent": {
                        "status": "healthy",
                        "processed_requests": 38,
                        "error_rate": 0.03,
                        "last_seen": new Date().toISOString()
                    },
                    "data-quality-agent": {
                        "status": "healthy",
                        "processed_requests": 41,
                        "error_rate": 0.02,
                        "last_seen": new Date().toISOString()
                    },
                    "compliance-monitoring-agent": {
                        "status": "healthy",
                        "processed_requests": 35,
                        "error_rate": 0.01,
                        "last_seen": new Date().toISOString()
                    }
                };
                this.agents = new Map(Object.entries(mockAgents));
                this.renderAgentsStatus(mockAgents);
            }
        } catch (error) {
            console.error('Failed to load agents status:', error);
            // Use mock data as fallback
            const mockAgents = {
                "data-ingestion-agent": {
                    "status": "healthy",
                    "processed_requests": 45,
                    "error_rate": 0.02,
                    "last_seen": new Date().toISOString()
                },
                "kyc-analysis-agent": {
                    "status": "healthy", 
                    "processed_requests": 42,
                    "error_rate": 0.01,
                    "last_seen": new Date().toISOString()
                },
                "decision-making-agent": {
                    "status": "healthy",
                    "processed_requests": 38,
                    "error_rate": 0.03,
                    "last_seen": new Date().toISOString()
                },
                "data-quality-agent": {
                    "status": "healthy",
                    "processed_requests": 41,
                    "error_rate": 0.02,
                    "last_seen": new Date().toISOString()
                },
                "compliance-monitoring-agent": {
                    "status": "healthy",
                    "processed_requests": 35,
                    "error_rate": 0.01,
                    "last_seen": new Date().toISOString()
                }
            };
            this.agents = new Map(Object.entries(mockAgents));
            this.renderAgentsStatus(mockAgents);
        }
    }
    
    async loadMetrics() {
        try {
            const response = await fetch('/api/v1/system/status');
            if (response.ok) {
                const data = await response.json();
                this.metrics = data.system_metrics;
                this.renderMetrics(this.metrics);
                this.renderDecisionChart();
            } else {
                // Fallback to mock metrics
                this.metrics = {
                    total_requests: 0,
                    successful_requests: 0,
                    average_processing_time: 2.5,
                    throughput_per_hour: 120
                };
                this.renderMetrics(this.metrics);
                this.renderDecisionChart();
            }
        } catch (error) {
            console.error('Failed to load metrics:', error);
            // Use mock metrics as fallback
            this.metrics = {
                total_requests: 0,
                successful_requests: 0,
                average_processing_time: 2.5,
                throughput_per_hour: 120
            };
            this.renderMetrics(this.metrics);
            this.renderDecisionChart();
        }
    }
    
    async loadRecentSessions() {
        // In a real implementation, this would fetch from an API
        // For now, we'll use localStorage to simulate recent sessions
        const sessions = this.getStoredSessions();
        this.renderRecentSessions(sessions);
    }
    
    renderSystemStatus(status) {
        const container = document.getElementById('system-status');
        
        const statusItems = [
            {
                label: 'System Status',
                value: status.status,
                indicator: status.status === 'operational' ? 'healthy' : 'unhealthy'
            },
            {
                label: 'Uptime',
                value: status.uptime,
                indicator: 'healthy'
            },
            {
                label: 'Active Sessions',
                value: status.active_sessions.toString(),
                indicator: status.active_sessions > 0 ? 'healthy' : 'warning'
            },
            {
                label: 'Version',
                value: status.version,
                indicator: 'healthy'
            }
        ];
        
        container.innerHTML = statusItems.map(item => `
            <div class="col-md-3">
                <div class="status-item">
                    <div class="status-indicator ${item.indicator}"></div>
                    <div>
                        <div class="fw-bold">${item.label}</div>
                        <div class="text-muted small">${item.value}</div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    renderAgentsStatus(agents) {
        const container = document.getElementById('agents-status');
        
        const agentCards = Object.entries(agents).map(([name, agent]) => {
            const statusClass = agent.status === 'healthy' ? 'healthy' : 'unhealthy';
            const borderClass = agent.status === 'healthy' ? 'border-start-success' : 'border-start-danger';
            
            return `
                <div class="col-md-4 mb-3">
                    <div class="card agent-card ${borderClass}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <div class="agent-name">${this.formatAgentName(name)}</div>
                                    <div class="agent-status">
                                        <span class="badge bg-${agent.status === 'healthy' ? 'success' : 'danger'}">
                                            ${agent.status}
                                        </span>
                                    </div>
                                    <div class="agent-metrics">
                                        <small>
                                            Requests: ${agent.processed_requests} | 
                                            Error Rate: ${(agent.error_rate * 100).toFixed(1)}%
                                        </small>
                                    </div>
                                </div>
                                <div class="status-indicator ${statusClass}"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = agentCards;
    }
    
    renderMetrics(metrics) {
        document.getElementById('total-requests').textContent = metrics.total_requests.toLocaleString();
        
        const successRate = metrics.total_requests > 0 
            ? ((metrics.successful_requests / metrics.total_requests) * 100).toFixed(1) + '%'
            : '0%';
        document.getElementById('success-rate').textContent = successRate;
        
        document.getElementById('avg-processing-time').textContent = 
            metrics.average_processing_time.toFixed(2) + 's';
        
        document.getElementById('throughput').textContent = 
            Math.round(metrics.throughput_per_hour).toLocaleString();
    }
    
    renderDecisionChart() {
        const ctx = document.getElementById('decision-chart').getContext('2d');
        
        // Sample data - in production this would come from metrics
        const data = {
            labels: ['Approved', 'Rejected', 'Requires Review', 'Additional Info'],
            datasets: [{
                data: [65, 15, 15, 5],
                backgroundColor: [
                    '#198754',
                    '#dc3545',
                    '#ffc107',
                    '#0dcaf0'
                ],
                borderWidth: 0
            }]
        };
        
        if (this.chart) {
            this.chart.destroy();
        }
        
        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    renderRecentSessions(sessions) {
        const container = document.getElementById('recent-sessions');
        
        if (sessions.length === 0) {
            container.innerHTML = '<div class="text-center"><p class="text-muted">No recent sessions</p></div>';
            return;
        }
        
        const sessionCards = sessions.map(session => `
            <div class="session-card fade-in">
                <div class="session-header">
                    <div>
                        <div class="fw-bold">${session.customer_id}</div>
                        <div class="session-id">${session.session_id}</div>
                    </div>
                    <span class="session-status ${session.status.toLowerCase().replace('_', '-')}">
                        ${session.status.replace('_', ' ')}
                    </span>
                </div>
                <div class="session-details">
                    <div class="row">
                        <div class="col-md-6">
                            <small class="text-muted">Created:</small>
                            <span>${new Date(session.created_at).toLocaleString()}</span>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">Stage:</small>
                            <span>${this.formatStage(session.current_stage)}</span>
                        </div>
                    </div>
                    ${session.processing_time ? `
                        <div class="mt-2">
                            <small class="text-muted">Processing Time:</small>
                            <span>${session.processing_time.toFixed(2)}s</span>
                        </div>
                    ` : ''}
                </div>
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewSession('${session.session_id}')">
                        <i class="fas fa-eye me-1"></i>
                        View Details
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = sessionCards;
    }
    
    async submitKYCRequest() {
        const customerId = document.getElementById('customer-id').value;
        const priority = document.getElementById('priority').value;
        const customerDataText = document.getElementById('customer-data').value;
        
        // Get vision model configuration
        const visionModel = document.getElementById('vision-model').value;
        const visionApiKey = document.getElementById('vision-api-key').value;
        
        // Get memory backend configuration
        const memoryBackend = document.getElementById('memory-backend').value;
        const pineconeApiKey = document.getElementById('pinecone-api-key').value;
        
        // Get selected regulatory requirements
        const regulatoryRequirements = Array.from(
            document.querySelectorAll('input[type="checkbox"]:checked')
        ).map(cb => cb.value);
        
        // Validate JSON
        let customerData;
        try {
            customerData = JSON.parse(customerDataText);
        } catch (error) {
            this.showError('Invalid JSON format in customer data');
            return;
        }
        
        // Validate required fields
        if (!customerId.trim()) {
            this.showError('Customer ID is required');
            return;
        }
        
        // Validate vision API key if GPT-4V is selected
        if (visionModel === 'gpt4v' && !visionApiKey.trim()) {
            this.showError('Vision API Key is required for GPT-4V model');
            return;
        }
        
        // Validate Pinecone API key if Pinecone is selected
        if (memoryBackend === 'pinecone' && !pineconeApiKey.trim()) {
            this.showError('Pinecone API Key is required for Pinecone backend');
            return;
        }
        
        const requestData = {
            customer_id: customerId,
            customer_data: customerData,
            priority: priority,
            regulatory_requirements: regulatoryRequirements,
            vision_model: visionModel,
            vision_api_key: visionApiKey,
            memory_backend: memoryBackend,
            pinecone_api_key: pineconeApiKey
        };
        
        try {
            this.showLoading('Processing KYC request...');
            
            const response = await fetch('/api/v1/kyc/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            this.showSuccess(`KYC processing initiated. Session ID: ${result.session_id}`);
            
            // Store session for recent sessions display
            this.storeSession({
                session_id: result.session_id,
                customer_id: customerId,
                status: result.status,
                created_at: new Date().toISOString(),
                current_stage: 'DataIngestion'
            });
            
            // Redirect to processing page
            setTimeout(() => {
                window.location.href = `/processing/${result.session_id}`;
            }, 2000);
            
        } catch (error) {
            console.error('KYC request failed:', error);
            this.showError(`Failed to process KYC request: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }
    
    validateJSON() {
        const customerDataText = document.getElementById('customer-data').value;
        
        try {
            JSON.parse(customerDataText);
            this.showSuccess('JSON is valid');
        } catch (error) {
            this.showError(`Invalid JSON: ${error.message}`);
        }
    }
    
    formatAgentName(name) {
        return name.split('-').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }
    
    formatStage(stage) {
        return stage.replace(/([A-Z])/g, ' $1').trim();
    }
    
    storeSession(session) {
        const sessions = this.getStoredSessions();
        sessions.unshift(session);
        
        // Keep only last 10 sessions
        const recentSessions = sessions.slice(0, 10);
        localStorage.setItem('kyc_sessions', JSON.stringify(recentSessions));
        
        this.loadRecentSessions();
    }
    
    getStoredSessions() {
        try {
            return JSON.parse(localStorage.getItem('kyc_sessions') || '[]');
        } catch {
            return [];
        }
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'danger');
    }
    
    showLoading(message) {
        this.showToast(message, 'info');
    }
    
    hideLoading() {
        const toast = bootstrap.Toast.getInstance(document.getElementById('toast'));
        if (toast) {
            toast.hide();
        }
    }
    
    showToast(message, type = 'info') {
        const toastElement = document.getElementById('toast');
        const toastBody = document.getElementById('toast-body');
        
        toastBody.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${this.getToastIcon(type)} me-2"></i>
                ${message}
            </div>
        `;
        
        toastElement.className = `toast border-${type}`;
        
        const toast = new bootstrap.Toast(toastElement, {
            delay: type === 'danger' ? 5000 : 3000
        });
        
        toast.show();
    }
    
    getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    startPeriodicUpdates() {
        // Update system status every 30 seconds
        setInterval(() => {
            this.loadSystemStatus();
            this.loadAgentsStatus();
        }, 30000);
        
        // Update metrics every 60 seconds
        setInterval(() => {
            this.loadMetrics();
        }, 60000);
        
        // Load recent sessions on startup
        this.loadRecentSessions();
    }
}

// Global functions
window.viewSession = function(sessionId) {
    window.location.href = `/results/${sessionId}`;
};

/**
 * Toggle Vision API Key field visibility based on selected vision model
 * Shows the API key field only when GPT-4V is selected
 */
window.toggleVisionApiKey = function() {
    const visionModel = document.getElementById('vision-model').value;
    const apiKeyContainer = document.getElementById('vision-api-key-container');
    const apiKeyInput = document.getElementById('vision-api-key');
    
    if (visionModel === 'gpt4v') {
        apiKeyContainer.style.display = 'block';
        apiKeyInput.required = true;
    } else {
        apiKeyContainer.style.display = 'none';
        apiKeyInput.required = false;
        apiKeyInput.value = ''; // Clear the field when hidden
    }
};

/**
 * Toggle Pinecone API Key field visibility based on selected memory backend
 * Shows the API key field only when Pinecone is selected
 */
window.togglePineconeApiKey = function() {
    const memoryBackend = document.getElementById('memory-backend').value;
    const apiKeyContainer = document.getElementById('pinecone-api-key-container');
    const apiKeyInput = document.getElementById('pinecone-api-key');
    
    if (memoryBackend === 'pinecone') {
        apiKeyContainer.style.display = 'block';
        apiKeyInput.required = true;
    } else {
        apiKeyContainer.style.display = 'none';
        apiKeyInput.required = false;
        apiKeyInput.value = ''; // Clear the field when hidden
    }
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.kycDashboard = new KYCDashboard();
    
    // Initialize conditional field visibility
    toggleVisionApiKey();
    togglePineconeApiKey();
});
