/**
 * Phase 3 Dashboard JavaScript
 * Handles all UI interactions for Intelligence & Compliance Agent features
 * 
 * Features:
 * - Rule Compiler testing and validation
 * - Kafka Consumer monitoring and control
 * - Jurisdiction Handler testing
 * - Overlap Resolver analysis
 * - Audit Logger management
 */

class Phase3Dashboard {
    constructor() {
        this.apiBase = '/api/phase3';
        this.wsConnection = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.setupWebSocket();
        this.startMetricsUpdate();
    }

    setupEventListeners() {
        // Rule Compiler
        document.getElementById('ruleCompilerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.compileRule();
        });

        document.getElementById('validateRule').addEventListener('click', () => {
            this.validateRule();
        });

        document.getElementById('testRule').addEventListener('click', () => {
            this.testRule();
        });

        // Kafka Consumer
        document.getElementById('startConsumer').addEventListener('click', () => {
            this.startKafkaConsumer();
        });

        document.getElementById('stopConsumer').addEventListener('click', () => {
            this.stopKafkaConsumer();
        });

        document.getElementById('kafkaTestForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendTestMessage();
        });

        // Jurisdiction Handler
        document.getElementById('jurisdictionTestForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.testJurisdictionFiltering();
        });

        // Overlap Resolver
        document.getElementById('overlapTestForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.detectOverlaps();
        });

        document.getElementById('resolveOverlaps').addEventListener('click', () => {
            this.resolveOverlaps();
        });

        document.getElementById('viewMerged').addEventListener('click', () => {
            this.viewMergedRule();
        });

        // Similarity threshold slider
        document.getElementById('similarityThreshold').addEventListener('input', (e) => {
            document.getElementById('thresholdValue').textContent = e.target.value + '%';
        });

        // Audit Logger
        document.getElementById('auditTestForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createAuditEntry();
        });

        document.getElementById('auditQueryForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.queryAuditTrail();
        });

        document.getElementById('exportAudit').addEventListener('click', () => {
            this.exportAuditTrail();
        });

        document.getElementById('verifyIntegrity').addEventListener('click', () => {
            this.verifyAuditIntegrity();
        });

        // Set default dates
        const today = new Date().toISOString().split('T')[0];
        const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        document.getElementById('queryDateFrom').value = weekAgo;
        document.getElementById('queryDateTo').value = today;
    }

    async loadInitialData() {
        try {
            // Load jurisdiction configuration
            await this.loadJurisdictionConfig();
            
            // Load recent audit entries
            await this.loadRecentAuditEntries();
            
            // Load performance metrics
            await this.updateMetrics();
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showAlert('error', 'Failed to load initial dashboard data');
        }
    }

    setupWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/phase3`;
        
        this.wsConnection = new WebSocket(wsUrl);
        
        this.wsConnection.onopen = () => {
            console.log('WebSocket connected');
        };
        
        this.wsConnection.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.wsConnection.onclose = () => {
            console.log('WebSocket disconnected, attempting to reconnect...');
            setTimeout(() => this.setupWebSocket(), 5000);
        };
        
        this.wsConnection.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'kafka_message':
                this.appendKafkaMessage(data.message);
                break;
            case 'metrics_update':
                this.updateMetricsDisplay(data.metrics);
                break;
            case 'audit_entry':
                this.addAuditEntry(data.entry);
                break;
            case 'consumer_status':
                this.updateConsumerStatus(data.status);
                break;
        }
    }

    // Rule Compiler Methods
    async compileRule() {
        const obligationText = document.getElementById('obligationText').value;
        const regulationType = document.getElementById('regulationType').value;
        const jurisdiction = document.getElementById('jurisdiction').value;

        if (!obligationText.trim()) {
            this.showAlert('warning', 'Please enter obligation text');
            return;
        }

        this.showCompilationProgress(true);

        try {
            const response = await fetch(`${this.apiBase}/rule-compiler/compile`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    obligation_text: obligationText,
                    regulation_type: regulationType,
                    jurisdiction: jurisdiction
                })
            });

            const result = await response.json();

            if (response.ok) {
                document.getElementById('jsonLogicOutput').textContent = 
                    JSON.stringify(result.json_logic, null, 2);
                
                this.showCompilationResult('success', 
                    `Rule compiled successfully in ${result.compilation_time}ms`);
                
                // Update metrics
                this.updateMetric('rulesCompiled', result.total_rules || 1);
                this.updateMetric('avgCompileTime', result.compilation_time + 'ms');
                
            } else {
                throw new Error(result.error || 'Compilation failed');
            }

        } catch (error) {
            console.error('Rule compilation error:', error);
            this.showCompilationResult('error', `Compilation failed: ${error.message}`);
        } finally {
            this.showCompilationProgress(false);
        }
    }

    async validateRule() {
        const jsonLogicText = document.getElementById('jsonLogicOutput').textContent;
        
        if (!jsonLogicText || jsonLogicText === 'Click "Compile Rule" to generate JSON-Logic...') {
            this.showAlert('warning', 'Please compile a rule first');
            return;
        }

        try {
            const jsonLogic = JSON.parse(jsonLogicText);
            
            const response = await fetch(`${this.apiBase}/rule-compiler/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ json_logic: jsonLogic })
            });

            const result = await response.json();

            if (response.ok && result.valid) {
                this.showAlert('success', 'Rule validation passed');
            } else {
                this.showAlert('error', `Validation failed: ${result.error || 'Invalid rule structure'}`);
            }

        } catch (error) {
            this.showAlert('error', `Validation error: ${error.message}`);
        }
    }

    async testRule() {
        const jsonLogicText = document.getElementById('jsonLogicOutput').textContent;
        
        if (!jsonLogicText || jsonLogicText === 'Click "Compile Rule" to generate JSON-Logic...') {
            this.showAlert('warning', 'Please compile a rule first');
            return;
        }

        try {
            const jsonLogic = JSON.parse(jsonLogicText);
            
            const response = await fetch(`${this.apiBase}/rule-compiler/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ json_logic: jsonLogic })
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert('success', 
                    `Rule test ${result.passed ? 'passed' : 'failed'}. Result: ${result.result}`);
            } else {
                this.showAlert('error', `Test failed: ${result.error}`);
            }

        } catch (error) {
            this.showAlert('error', `Test error: ${error.message}`);
        }
    }

    // Kafka Consumer Methods
    async startKafkaConsumer() {
        try {
            const response = await fetch(`${this.apiBase}/kafka-consumer/start`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok) {
                this.updateConsumerStatus({ status: 'active', message: 'Consumer started' });
                this.showAlert('success', 'Kafka consumer started successfully');
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Failed to start consumer: ${error.message}`);
        }
    }

    async stopKafkaConsumer() {
        try {
            const response = await fetch(`${this.apiBase}/kafka-consumer/stop`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok) {
                this.updateConsumerStatus({ status: 'inactive', message: 'Consumer stopped' });
                this.showAlert('info', 'Kafka consumer stopped');
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Failed to stop consumer: ${error.message}`);
        }
    }

    async sendTestMessage() {
        const eventType = document.getElementById('eventType').value;
        const payload = document.getElementById('testPayload').value;

        try {
            const payloadObj = JSON.parse(payload);
            
            const response = await fetch(`${this.apiBase}/kafka-consumer/test-message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event_type: eventType,
                    payload: payloadObj
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert('success', 'Test message sent successfully');
                this.appendKafkaMessage({
                    timestamp: new Date().toISOString(),
                    event_type: eventType,
                    payload: payloadObj,
                    status: 'sent'
                });
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Failed to send test message: ${error.message}`);
        }
    }

    // Jurisdiction Handler Methods
    async testJurisdictionFiltering() {
        const customerCountry = document.getElementById('customerCountry').value;
        const businessCountry = document.getElementById('businessCountry').value;
        const conflictStrategy = document.getElementById('conflictStrategy').value;

        try {
            const response = await fetch(`${this.apiBase}/jurisdiction-handler/filter`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    customer_country: customerCountry,
                    business_country: businessCountry,
                    conflict_strategy: conflictStrategy
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.displayJurisdictionResults(result);
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Jurisdiction filtering failed: ${error.message}`);
        }
    }

    // Overlap Resolver Methods
    async detectOverlaps() {
        const rule1Text = document.getElementById('rule1Text').value;
        const rule2Text = document.getElementById('rule2Text').value;
        const threshold = document.getElementById('similarityThreshold').value / 100;

        if (!rule1Text.trim() || !rule2Text.trim()) {
            this.showAlert('warning', 'Please enter both rule texts');
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/overlap-resolver/detect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    rule1_text: rule1Text,
                    rule2_text: rule2Text,
                    similarity_threshold: threshold
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.displayOverlapResults(result);
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Overlap detection failed: ${error.message}`);
        }
    }

    async resolveOverlaps() {
        // Implementation for resolving detected overlaps
        this.showAlert('info', 'Overlap resolution feature coming soon');
    }

    async viewMergedRule() {
        // Implementation for viewing merged rules
        this.showAlert('info', 'Merged rule view feature coming soon');
    }

    // Audit Logger Methods
    async createAuditEntry() {
        const action = document.getElementById('auditAction').value;
        const details = document.getElementById('auditDetails').value;
        const user = document.getElementById('auditUser').value;

        try {
            const response = await fetch(`${this.apiBase}/audit-logger/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    details: details,
                    user_id: user
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert('success', 'Audit entry created successfully');
                this.addAuditEntry(result.entry);
                this.updateMetric('auditEntries', result.total_entries || 1);
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Failed to create audit entry: ${error.message}`);
        }
    }

    async queryAuditTrail() {
        const dateFrom = document.getElementById('queryDateFrom').value;
        const dateTo = document.getElementById('queryDateTo').value;
        const actionFilter = document.getElementById('queryAction').value;

        try {
            const params = new URLSearchParams({
                date_from: dateFrom,
                date_to: dateTo,
                action: actionFilter
            });

            const response = await fetch(`${this.apiBase}/audit-logger/query?${params}`);
            const result = await response.json();

            if (response.ok) {
                this.displayAuditResults(result.entries);
                this.showAlert('success', `Found ${result.entries.length} audit entries`);
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.showAlert('error', `Audit query failed: ${error.message}`);
        }
    }

    async exportAuditTrail() {
        const format = document.getElementById('exportFormat').value;

        try {
            const response = await fetch(`${this.apiBase}/audit-logger/export?format=${format}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `audit_trail.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showAlert('success', 'Audit trail exported successfully');
            } else {
                throw new Error('Export failed');
            }

        } catch (error) {
            this.showAlert('error', `Export failed: ${error.message}`);
        }
    }

    async verifyAuditIntegrity() {
        try {
            const response = await fetch(`${this.apiBase}/audit-logger/verify-integrity`);
            const result = await response.json();

            if (response.ok && result.valid) {
                this.showAlert('success', 'Audit trail integrity verified');
            } else {
                this.showAlert('error', `Integrity verification failed: ${result.error || 'Invalid integrity'}`);
            }

        } catch (error) {
            this.showAlert('error', `Integrity verification failed: ${error.message}`);
        }
    }

    // UI Helper Methods
    showAlert(type, message) {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Find the active tab and show alert there
        const activeTab = document.querySelector('.tab-pane.active');
        if (activeTab) {
            const existingAlert = activeTab.querySelector('.alert');
            if (existingAlert) {
                existingAlert.remove();
            }
            activeTab.insertAdjacentHTML('afterbegin', alertHtml);
        }
    }

    showCompilationProgress(show) {
        const resultsDiv = document.getElementById('compilationResults');
        if (show) {
            resultsDiv.style.display = 'block';
            resultsDiv.className = 'alert alert-info';
            resultsDiv.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-3" role="status"></div>
                    <span>Compiling rule...</span>
                </div>
            `;
        } else {
            resultsDiv.style.display = 'none';
        }
    }

    showCompilationResult(type, message) {
        const resultsDiv = document.getElementById('compilationResults');
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        
        resultsDiv.style.display = 'block';
        resultsDiv.className = `alert ${alertClass}`;
        resultsDiv.innerHTML = message;
    }

    updateMetric(metricId, value) {
        const element = document.getElementById(metricId);
        if (element) {
            element.textContent = value;
        }
    }

    updateConsumerStatus(status) {
        const statusElement = document.getElementById('consumerStatus');
        const statusClass = status.status === 'active' ? 'bg-success' : 'bg-secondary';
        
        statusElement.className = `badge ${statusClass}`;
        statusElement.textContent = status.status.charAt(0).toUpperCase() + status.status.slice(1);
    }

    appendKafkaMessage(message) {
        const messagesDiv = document.getElementById('kafkaMessages');
        const timestamp = new Date(message.timestamp).toLocaleTimeString();
        
        const messageHtml = `
            <div class="mb-2">
                <span class="text-success">[${timestamp}]</span> 
                <span class="text-info">${message.event_type}</span>: 
                ${JSON.stringify(message.payload)}
            </div>
        `;
        
        messagesDiv.insertAdjacentHTML('afterbegin', messageHtml);
        
        // Keep only last 50 messages
        const messages = messagesDiv.children;
        while (messages.length > 50) {
            messagesDiv.removeChild(messages[messages.length - 1]);
        }
    }

    displayJurisdictionResults(results) {
        const resultsDiv = document.getElementById('jurisdictionResults');
        
        if (results.applicable_rules && results.applicable_rules.length > 0) {
            let html = '<h6>Applicable Rules:</h6><ul class="list-group">';
            
            results.applicable_rules.forEach(rule => {
                html += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${rule.regulation_type}</strong> - ${rule.jurisdiction}
                            <br><small class="text-muted">${rule.description || 'No description'}</small>
                        </div>
                        <span class="badge bg-primary rounded-pill">${rule.confidence_score}%</span>
                    </li>
                `;
            });
            
            html += '</ul>';
            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = '<div class="text-muted text-center py-4">No applicable rules found</div>';
        }
    }

    displayOverlapResults(results) {
        const resultsDiv = document.getElementById('overlapResults');
        
        if (results.overlap_detected) {
            const html = `
                <div class="alert alert-warning">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Overlap Detected</h6>
                    <p><strong>Similarity Score:</strong> ${(results.similarity_score * 100).toFixed(1)}%</p>
                    <p><strong>Overlap Type:</strong> ${results.overlap_type}</p>
                    <p><strong>Common Elements:</strong> ${results.common_elements.join(', ')}</p>
                </div>
            `;
            resultsDiv.innerHTML = html;
            
            // Update overlap metrics
            this.updateMetric('totalOverlaps', results.total_overlaps || 1);
            this.updateMetric('avgSimilarity', (results.similarity_score * 100).toFixed(1) + '%');
        } else {
            resultsDiv.innerHTML = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle me-2"></i>No Overlap Detected</h6>
                    <p>Similarity score: ${(results.similarity_score * 100).toFixed(1)}% (below threshold)</p>
                </div>
            `;
        }
    }

    addAuditEntry(entry) {
        const tableBody = document.getElementById('auditTable');
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${new Date(entry.timestamp).toLocaleString()}</td>
            <td><span class="badge bg-secondary">${entry.action}</span></td>
            <td>${entry.user_id}</td>
            <td>${entry.details}</td>
            <td><i class="fas fa-shield-alt text-success" title="Verified"></i></td>
        `;
        
        tableBody.insertBefore(row, tableBody.firstChild);
        
        // Keep only last 20 entries visible
        while (tableBody.children.length > 20) {
            tableBody.removeChild(tableBody.lastChild);
        }
    }

    displayAuditResults(entries) {
        const tableBody = document.getElementById('auditTable');
        tableBody.innerHTML = '';
        
        entries.forEach(entry => {
            this.addAuditEntry(entry);
        });
    }

    async loadJurisdictionConfig() {
        try {
            const response = await fetch(`${this.apiBase}/jurisdiction-handler/config`);
            const config = await response.json();
            
            if (response.ok) {
                this.displayJurisdictionConfig(config.jurisdictions);
            }
        } catch (error) {
            console.error('Failed to load jurisdiction config:', error);
        }
    }

    displayJurisdictionConfig(jurisdictions) {
        const tableBody = document.getElementById('jurisdictionTable');
        tableBody.innerHTML = '';
        
        jurisdictions.forEach(jurisdiction => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${jurisdiction.code}</strong></td>
                <td>${jurisdiction.level}</td>
                <td>${jurisdiction.parent || '-'}</td>
                <td>${jurisdiction.active_rules || 0}</td>
                <td><span class="badge ${jurisdiction.enabled ? 'bg-success' : 'bg-secondary'}">${jurisdiction.enabled ? 'Active' : 'Inactive'}</span></td>
            `;
            tableBody.appendChild(row);
        });
    }

    async loadRecentAuditEntries() {
        try {
            const response = await fetch(`${this.apiBase}/audit-logger/recent`);
            const result = await response.json();
            
            if (response.ok) {
                this.displayAuditResults(result.entries);
            }
        } catch (error) {
            console.error('Failed to load recent audit entries:', error);
        }
    }

    async updateMetrics() {
        try {
            const response = await fetch(`${this.apiBase}/metrics`);
            const metrics = await response.json();
            
            if (response.ok) {
                this.updateMetricsDisplay(metrics);
            }
        } catch (error) {
            console.error('Failed to update metrics:', error);
        }
    }

    updateMetricsDisplay(metrics) {
        if (metrics.rules_compiled !== undefined) {
            this.updateMetric('rulesCompiled', metrics.rules_compiled);
        }
        if (metrics.avg_compile_time !== undefined) {
            this.updateMetric('avgCompileTime', metrics.avg_compile_time + 'ms');
        }
        if (metrics.audit_entries !== undefined) {
            this.updateMetric('auditEntries', metrics.audit_entries);
        }
        if (metrics.consumer_lag !== undefined) {
            this.updateMetric('consumerLag', metrics.consumer_lag);
        }
        if (metrics.messages_processed !== undefined) {
            this.updateMetric('messagesProcessed', metrics.messages_processed);
        }
        if (metrics.messages_failed !== undefined) {
            this.updateMetric('messagesFailed', metrics.messages_failed);
        }
    }

    startMetricsUpdate() {
        // Update metrics every 30 seconds
        setInterval(() => {
            this.updateMetrics();
        }, 30000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Phase3Dashboard();
});
