// Risk Assessment AI - Enhanced Chat Application
class RiskAssessmentChat {
  constructor() {
    this.ws = null;
    this.username = "";
    this.isConnected = false;
    this.messageHistory = [];
    this.currentTheme = "light";

    this.initializeElements();
    this.attachEventListeners();
    this.loadFromLocalStorage();
    this.initializeProgressTracking();
  }

  initializeElements() {
    // Main elements
    this.usernameInput = document.getElementById("usernameInput");
    this.connectBtn = document.getElementById("connectBtn");
    this.messageInput = document.getElementById("messageInput");
    this.sendBtn = document.getElementById("sendBtn");
    this.messagesContainer = document.getElementById("messagesContainer");
    this.connectionStatus = document.getElementById("connectionStatus");
    this.typingIndicator = document.getElementById("typingIndicator");
    this.charCount = document.getElementById("charCount");

    // Stats elements
    this.statsElements = {
      totalRisks: document.getElementById("totalRisks"),
      approvedRisks: document.getElementById("approvedRisks"),
      pendingRisks: document.getElementById("pendingRisks"),
      currentStep: document.getElementById("currentStep"),
    };

    // Progress elements
    this.progressItems = document.querySelectorAll(".progress-item");
    this.actionButtons = document.querySelectorAll(".action-btn");
  }

  attachEventListeners() {
    // Connection
    this.connectBtn.addEventListener("click", () => this.toggleConnection());
    this.usernameInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.toggleConnection();
    });
    this.usernameInput.addEventListener("input", () => this.validateUsername());

    // Messaging
    this.sendBtn.addEventListener("click", () => this.sendMessage());
    this.messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
    this.messageInput.addEventListener("input", () => this.updateCharCount());

    // Auto-resize textarea
    this.messageInput.addEventListener("input", () => this.autoResizeTextarea());

    // Window resize
    window.addEventListener("resize", () => this.adjustLayout());
  }

  initializeProgressTracking() {
    this.progressSteps = {
      user: { element: document.querySelector('[data-step="user"]'), completed: false },
      org: { element: document.querySelector('[data-step="org"]'), completed: false },
      risks: { element: document.querySelector('[data-step="risks"]'), completed: false },
      review: { element: document.querySelector('[data-step="review"]'), completed: false },
      report: { element: document.querySelector('[data-step="report"]'), completed: false },
    };
  }

  loadFromLocalStorage() {
    const savedUsername = localStorage.getItem("riskAssessmentUsername");
    const savedTheme = localStorage.getItem("riskAssessmentTheme") || "light";

    if (savedUsername) {
      this.usernameInput.value = savedUsername;
    }

    this.currentTheme = savedTheme;
    document.body.setAttribute("data-theme", savedTheme);
    this.updateThemeToggle();
  }

  saveToLocalStorage() {
    localStorage.setItem("riskAssessmentUsername", this.username);
    localStorage.setItem("riskAssessmentTheme", this.currentTheme);
  }

  validateUsername() {
    const username = this.usernameInput.value.trim();
    const isValid = username.length >= 2 && username.length <= 50;

    this.connectBtn.disabled = !isValid || this.isConnected;

    if (username.length > 0 && username.length < 2) {
      this.usernameInput.style.borderColor = "#fc466b";
    } else if (isValid) {
      this.usernameInput.style.borderColor = "#11998e";
    } else {
      this.usernameInput.style.borderColor = "";
    }
  }

  toggleConnection() {
    if (this.isConnected) {
      this.disconnect();
    } else {
      this.connect();
    }
  }

  connect() {
    const username = this.usernameInput.value.trim();
    if (!username || username.length < 2) {
      this.showNotification("Please enter a valid username (2-50 characters)", "error");
      return;
    }

    this.username = username;
    this.saveToLocalStorage();

    // Show connecting status
    this.updateConnectionStatus("connecting", "Connecting...");
    this.connectBtn.disabled = true;
    this.connectBtn.innerHTML = `
            <span class="btn-content">
                <i class="fas fa-spinner fa-spin"></i>
                <span class="btn-text">Connecting...</span>
            </span>
            <div class="btn-glow"></div>
        `;

    try {
      // Create WebSocket connection
      const wsUrl = `ws://${window.location.hostname}:8000/api/chat/ws/${encodeURIComponent(this.username)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => this.onConnected();
      this.ws.onmessage = (event) => this.onMessage(event);
      this.ws.onclose = (event) => this.onDisconnected(event);
      this.ws.onerror = (error) => this.onError(error);

      // Timeout for connection
      this._connectionTimeout = setTimeout(() => {
        if (!this.isConnected) {
          this.showNotification("Connection timeout. Please check if the server is running on port 8000", "error");
          this.disconnect();
        }
      }, 10000);
    } catch (error) {
      this.showNotification(`Connection failed: ${error.message}`, "error");
      this.disconnect();
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
    }
    this.onDisconnected();
  }

  onConnected() {
    this.isConnected = true;
    clearTimeout(this._connectionTimeout);
    this.updateConnectionStatus("connected", "Connected");
    this.connectBtn.innerHTML = `
            <span class="btn-content">
                <i class="fas fa-plug"></i>
                <span class="btn-text">Disconnect</span>
            </span>
            <div class="btn-glow"></div>
        `;
    this.connectBtn.disabled = false;
    this.enableMessaging();
    this.updateProgress("user", "completed");
    this.addSystemMessage(`🚀 Successfully connected as ${this.username}! Ready to start your risk assessment journey.`);
    this.enableActionButtons();
    this.showNotification("Connected successfully! You can now chat with the AI.", "success");
  }

  onDisconnected(event) {
    this.isConnected = false;
    clearTimeout(this._connectionTimeout);
    this.updateConnectionStatus("disconnected", "Disconnected");
    this.connectBtn.innerHTML = `
            <span class="btn-content">
                <i class="fas fa-rocket"></i>
                <span class="btn-text">Launch Connection</span>
            </span>
            <div class="btn-glow"></div>
        `;
    this.connectBtn.disabled = false;
    this.disableMessaging();
    this.disableActionButtons();
    if (this.ws) {
      this.ws = null;
    }
    if (event && event.wasClean === false) {
      this.showNotification("Disconnected from server unexpectedly.", "error");
    }
  }

  onError(error) {
    console.error("WebSocket error:", error);
    this.showNotification("Connection error occurred. Please try again.", "error");
    this.disconnect();
  }

  onMessage(event) {
    try {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    } catch (error) {
      console.error("Failed to parse message:", error);
      this.showNotification("Failed to parse server message", "error");
    }
  }

  handleMessage(data) {
    const { type, message, workflow_status, risks, report, timestamp } = data;
    switch (type) {
      case "welcome":
        this.addSystemMessage(message);
        break;
      case "response":
        this.addBotMessage(message);
        if (workflow_status) {
          this.updateWorkflowStatus(workflow_status);
          // Check if metadata popup should be shown (only if not already completed)
          if (workflow_status.show_metadata_popup && !workflow_status.metadata_completed && risks && risks.length > 0) {
            this.showMetadataPopup(risks);
          }
        }
        if (risks && risks.length > 0) {
          this.displayRisks(risks);
        }
        if (report) {
          this.displayReport(report);
        }
        break;
      case "typing":
        this.showTyping(message);
        break;
      case "error":
        this.hideTyping();
        this.addErrorMessage(message);
        this.showNotification("An error occurred while processing your request", "error");
        break;
      case "status":
        if (workflow_status) {
          this.updateWorkflowStatus(workflow_status);
        }
        break;
      case "reset":
        this.addSystemMessage(message);
        this.resetProgress();
        break;
      default:
        console.log("Unknown message type:", type, data);
    }
    this.hideTyping();
  }

  sendMessage(text = null) {
    if (!this.isConnected) {
      this.showNotification("Please connect first", "warning");
      return;
    }

    const message = text || this.messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    this.addUserMessage(message);

    // Send to server
    const messageData = {
      type: "chat",
      message: message,
      timestamp: new Date().toISOString(),
    };

    try {
      this.ws.send(JSON.stringify(messageData));
    } catch (error) {
      this.showNotification("Failed to send message", "error");
      return;
    }

    // Clear input and show typing
    if (!text) {
      this.messageInput.value = "";
      this.updateCharCount();
      this.autoResizeTextarea();
    }
    this.showTyping();
  }

  // UI Update Methods
  updateConnectionStatus(status, text) {
    this.connectionStatus.className = `connection-status ${status}`;
    this.connectionStatus.querySelector(".status-text").textContent = text;

    // Add pulse animation for connecting state
    if (status === "connecting") {
      this.connectionStatus.style.animation = "pulse 1s infinite";
    } else {
      this.connectionStatus.style.animation = "";
    }
  }

  enableMessaging() {
    this.messageInput.disabled = false;
    this.sendBtn.disabled = false;
    this.usernameInput.disabled = true;
    this.messageInput.focus();
  }

  disableMessaging() {
    this.messageInput.disabled = true;
    this.sendBtn.disabled = true;
    this.usernameInput.disabled = false;
  }

  enableActionButtons() {
    this.actionButtons.forEach((btn) => {
      btn.disabled = false;
      btn.style.opacity = "1";
    });
  }

  disableActionButtons() {
    this.actionButtons.forEach((btn) => {
      btn.disabled = true;
      btn.style.opacity = "0.5";
    });
  }

  updateWorkflowStatus(status) {
    // Store current workflow status for later reference
    this.currentWorkflowStatus = status;

    const { current_step, intent, total_risks, approved_risks, pending_risks, needs_clarification } = status;

    // Update stats with animations
    this.animateStatUpdate("totalRisks", total_risks || 0);
    this.animateStatUpdate("approvedRisks", approved_risks || 0);
    this.animateStatUpdate("pendingRisks", pending_risks || 0);

    const stepText = this.formatStepName(current_step || "not_started");
    this.statsElements.currentStep.textContent = stepText;

    // Update progress based on current step
    this.updateProgressBasedOnStep(current_step);

    // Show clarification indicator
    if (needs_clarification) {
      this.showNotification("The AI needs clarification about your request", "info");
    }
  }

  animateStatUpdate(statId, newValue) {
    const element = this.statsElements[statId];
    if (!element) return;

    const currentValue = parseInt(element.textContent) || 0;
    if (currentValue === newValue) return;

    // Add animation class
    element.style.transform = "scale(1.2)";
    element.style.color = "#4facfe";

    // Animate the number change
    const duration = 500;
    const steps = 10;
    const stepValue = (newValue - currentValue) / steps;
    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep++;
      const interpolatedValue = Math.round(currentValue + stepValue * currentStep);
      element.textContent = interpolatedValue;

      if (currentStep >= steps) {
        clearInterval(interval);
        element.textContent = newValue;

        // Reset styles
        setTimeout(() => {
          element.style.transform = "";
          element.style.color = "";
        }, 100);
      }
    }, duration / steps);
  }

  formatStepName(step) {
    const stepNames = {
      not_started: "Not Started",
      intent_parsing: "Understanding Request",
      context_manager: "Processing Context",
      gather_data: "Gathering Data",
      generate_risks: "Generating Risks",
      review_risks: "Reviewing Risks",
      select_risks: "Selecting Risks",
      generate_report: "Creating Report",
    };
    return stepNames[step] || step.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  }

  updateProgressBasedOnStep(step) {
    // Reset all progress items
    Object.values(this.progressSteps).forEach(({ element }) => {
      element.classList.remove("active", "completed");
      const progressFill = element.querySelector(".progress-fill");
      if (progressFill) progressFill.style.width = "0%";
    });

    // Update based on current step
    switch (step) {
      case "intent_parsing":
      case "context_manager":
        this.updateProgress("user", "active");
        break;
      case "gather_data":
        this.updateProgress("user", "completed");
        this.updateProgress("org", "active");
        break;
      case "generate_risks":
        this.updateProgress("user", "completed");
        this.updateProgress("org", "completed");
        this.updateProgress("risks", "active");
        break;
      case "review_risks":
        this.updateProgress("user", "completed");
        this.updateProgress("org", "completed");
        this.updateProgress("risks", "completed");
        this.updateProgress("review", "active");
        break;
      case "select_risks":
        this.updateProgress("user", "completed");
        this.updateProgress("org", "completed");
        this.updateProgress("risks", "completed");
        this.updateProgress("review", "completed");
        this.updateProgress("report", "active");
        break;
      case "generate_report":
        this.updateProgress("user", "completed");
        this.updateProgress("org", "completed");
        this.updateProgress("risks", "completed");
        this.updateProgress("review", "completed");
        this.updateProgress("report", "completed");
        break;
    }
  }

  updateProgress(type, status) {
    const step = this.progressSteps[type];
    if (!step) return;

    const { element } = step;
    element.classList.remove("active", "completed");

    if (status === "active") {
      element.classList.add("active");
      const progressFill = element.querySelector(".progress-fill");
      if (progressFill) progressFill.style.width = "50%";
    } else if (status === "completed") {
      element.classList.add("completed");
      const progressFill = element.querySelector(".progress-fill");
      if (progressFill) progressFill.style.width = "100%";
    }

    step.completed = status === "completed";
  }

  resetProgress() {
    Object.values(this.progressSteps).forEach(({ element }) => {
      element.classList.remove("active", "completed");
      const progressFill = element.querySelector(".progress-fill");
      if (progressFill) progressFill.style.width = "0%";
    });

    Object.values(this.statsElements).forEach((el, index) => {
      if (index < 3) {
        // First 3 are numbers
        el.textContent = "0";
      } else {
        el.textContent = "Not Started";
      }
    });
  }

  // Message Display Methods
  addUserMessage(message) {
    this.addMessage(message, "user", "👤 You");
  }

  addBotMessage(message) {
    this.addMessage(message, "bot", "🤖 Risk Assessment AI");
  }

  addSystemMessage(message) {
    this.addMessage(message, "system", "🔔 System");
  }

  addErrorMessage(message) {
    this.addMessage(message, "error", "⚠️ Error");
  }

  addMessage(content, type, sender) {
    // Remove welcome screen on first message
    const welcomeScreen = this.messagesContainer.querySelector(".welcome-screen");
    if (welcomeScreen && (type === "user" || type === "bot")) {
      welcomeScreen.style.animation = "fadeInUp 0.3s reverse";
      setTimeout(() => welcomeScreen.remove(), 300);
    }

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}`;

    const timestamp = new Date().toLocaleTimeString();

    messageDiv.innerHTML = `
            <div class="message-content">
                ${this.formatMessage(content)}
            </div>
        `;

    this.messagesContainer.appendChild(messageDiv);
    this.scrollToBottom();

    // Add to message history
    this.messageHistory.push({ content, type, sender, timestamp });
  }

  formatMessage(content) {
    // Convert line breaks to HTML and handle basic formatting
    return content
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code>$1</code>");
  }

  displayRisks(risks) {
    if (!risks || risks.length === 0) return;

    // Store current risks for modal display
    this.currentRisks = risks;

    const risksDiv = document.createElement("div");
    risksDiv.className = "risks-display";
    risksDiv.innerHTML = `
            <div class="risks-header">
                <i class="fas fa-exclamation-triangle"></i>
                <h4>Generated Risks (${risks.length})</h4>
            </div>
            <div class="risks-grid">
                ${risks
                  .map(
                    (risk, index) => `
                    <div class="risk-card ${risk.is_approved ? "risk-approved" : "risk-pending"}" onclick="showRiskDetails('${risk.risk_id}')" data-risk-index="${index}">
                        <div class="risk-header">
                            <span class="risk-id">#${risk.risk_id}</span>
                            <span class="risk-likelihood">L: ${risk.likelihood?.value || "N/A"}</span>
                            <span class="risk-impact">I: ${risk.impact?.value || "N/A"}</span>
                            ${risk.is_approved ? '<span class="approval-badge">✓</span>' : ""}
                        </div>
                        <div class="risk-content">
                            <div class="risk-description">${risk.risk_description && risk.risk_description.length > 100 ? risk.risk_description.substring(0, 100) + "..." : risk.risk_description || "No description"}</div>
                            <div class="risk-treatment">
                                <span class="treatment-tag">${risk.treatment_strategy || "N/A"}</span>
                                <span class="status-indicator">${risk.is_approved ? "Approved" : "Pending"}</span>
                            </div>
                        </div>
                    </div>
                `
                  )
                  .join("")}
            </div>
        `;

    this.messagesContainer.appendChild(risksDiv);
    this.scrollToBottom();

    // Animate risk cards
    setTimeout(() => {
      risksDiv.querySelectorAll(".risk-card").forEach((card, index) => {
        setTimeout(() => {
          card.style.animation = "slideIn 0.3s forwards";
        }, index * 100);
      });
    }, 100);
  }

  displayReport(report) {
    if (!report || !report.content) return;

    const reportDiv = document.createElement("div");
    reportDiv.className = "report-display";
    reportDiv.innerHTML = `
      <div class="report-header">
        <i class="fas fa-file-shield"></i>
        <h4>${report.title || "Risk Assessment Report"}</h4>
        <div class="report-actions">
          <button class="btn btn-primary" onclick="viewReportInModal('${encodeURIComponent(report.content)}', '${encodeURIComponent(report.title || "Risk Assessment Report")}')">
            <i class="fas fa-eye"></i> View Report
          </button>
          <button class="btn btn-secondary" onclick="downloadReport('${encodeURIComponent(report.content)}', '${encodeURIComponent(report.title || "Risk Assessment Report")}')">
            <i class="fas fa-download"></i> Download
          </button>
        </div>
      </div>
      <div class="report-preview">
        <p><i class="fas fa-info-circle"></i> Your comprehensive risk assessment report has been generated. Click "View Report" to see the full details or "Download" to save it to your device.</p>
        <div class="report-meta">
          <span><i class="fas fa-calendar"></i> Generated: ${new Date(report.generated_at || Date.now()).toLocaleString()}</span>
        </div>
      </div>
    `;

    this.messagesContainer.appendChild(reportDiv);
    this.scrollToBottom();

    // Store report for later access
    this.currentReport = report;

    // Animate report display
    setTimeout(() => {
      reportDiv.style.animation = "slideIn 0.5s forwards";
    }, 100);

    // Show notification
    this.showNotification("📊 Your risk assessment report is ready!", "success");
  }

  showTyping(message = "AI is analyzing...") {
    this.typingIndicator.style.display = "block";
    this.typingIndicator.querySelector(".typing-text").textContent = message;
    this.scrollToBottom();
  }

  hideTyping() {
    this.typingIndicator.style.display = "none";
  }

  scrollToBottom() {
    setTimeout(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }, 100);
  }

  updateCharCount() {
    const count = this.messageInput.value.length;
    this.charCount.textContent = count;

    if (count > 900) {
      this.charCount.style.color = "#fc466b";
    } else if (count > 700) {
      this.charCount.style.color = "#f093fb";
    } else {
      this.charCount.style.color = "";
    }
  }

  autoResizeTextarea() {
    this.messageInput.style.height = "auto";
    const scrollHeight = this.messageInput.scrollHeight;
    this.messageInput.style.height = Math.min(scrollHeight, 120) + "px";
  }

  adjustLayout() {
    // Responsive adjustments can be added here
  }

  showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;

    const container = document.getElementById("notifications");
    container.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
      notification.style.animation = "slideInRight 0.3s reverse";
      setTimeout(() => notification.remove(), 300);
    }, 5000);
  }

  getNotificationIcon(type) {
    const icons = {
      success: "check-circle",
      error: "exclamation-triangle",
      warning: "exclamation-circle",
      info: "info-circle",
    };
    return icons[type] || "info-circle";
  }

  // Metadata Collection Methods
  showMetadataPopup(risks) {
    const approvedRisks = risks.filter((risk) => risk.is_approved);
    if (approvedRisks.length === 0) {
      this.showNotification("No approved risks found for metadata collection", "warning");
      return;
    }

    this.populateMetadataTable(approvedRisks);
    const modal = document.getElementById("metadataModal");
    modal.style.display = "flex";

    // Add form submit handler
    const form = document.getElementById("metadataForm");
    form.onsubmit = (e) => this.handleMetadataSubmit(e, approvedRisks);
  }

  populateMetadataTable(risks) {
    const tbody = document.getElementById("metadataTableBody");
    tbody.innerHTML = "";

    risks.forEach((risk) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="risk-id">${risk.risk_id}</td>
        <td class="risk-description" title="${risk.risk_description}">
          ${risk.risk_description.length > 50 ? risk.risk_description.substring(0, 50) + "..." : risk.risk_description}
        </td>
        <td>
          <input type="number" 
                 name="asset_value_${risk.risk_id}" 
                 placeholder="0.00" 
                 step="0.01" 
                 min="0" 
                 required
                 value="${risk.asset_value || ""}"
                 class="metadata-input">
        </td>
        <td>
          <input type="text" 
                 name="department_${risk.risk_id}" 
                 placeholder="IT, Finance, etc." 
                 required
                 value="${risk.department || ""}"
                 class="metadata-input">
        </td>
        <td>
          <input type="text" 
                 name="risk_owner_${risk.risk_id}" 
                 placeholder="John Doe" 
                 required
                 value="${risk.risk_owner || ""}"
                 class="metadata-input">
        </td>
        <td>
          <input type="date" 
                 name="target_date_${risk.risk_id}" 
                 required
                 value="${risk.target_date || ""}"
                 class="metadata-input">
        </td>
        <td>
          <select name="risk_progress_${risk.risk_id}" required class="metadata-select">
            <option value="">Select...</option>
            <option value="Not Started" ${risk.risk_progress === "Not Started" ? "selected" : ""}>Not Started</option>
            <option value="In Progress" ${risk.risk_progress === "In Progress" ? "selected" : ""}>In Progress</option>
            <option value="Completed" ${risk.risk_progress === "Completed" ? "selected" : ""}>Completed</option>
          </select>
        </td>
        <td>
          <select name="residual_exposure_${risk.risk_id}" required class="metadata-select">
            <option value="">Select...</option>
            <option value="Very Low" ${risk.residual_exposure?.value === "Very Low" ? "selected" : ""}>Very Low</option>
            <option value="Low" ${risk.residual_exposure?.value === "Low" ? "selected" : ""}>Low</option>
            <option value="Medium" ${risk.residual_exposure?.value === "Medium" ? "selected" : ""}>Medium</option>
            <option value="High" ${risk.residual_exposure?.value === "High" ? "selected" : ""}>High</option>
            <option value="Very High" ${risk.residual_exposure?.value === "Very High" ? "selected" : ""}>Very High</option>
          </select>
        </td>
      `;
      tbody.appendChild(row);
    });
  }

  async handleMetadataSubmit(event, risks) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Update each risk with metadata directly
    risks.forEach((risk) => {
      const riskId = risk.risk_id;
      const assetValue = parseFloat(formData.get(`asset_value_${riskId}`));
      const department = formData.get(`department_${riskId}`);
      const riskOwner = formData.get(`risk_owner_${riskId}`);
      const targetDate = formData.get(`target_date_${riskId}`);
      const riskProgress = formData.get(`risk_progress_${riskId}`);
      const residualExposure = formData.get(`residual_exposure_${riskId}`);

      // Convert residual exposure to proper format
      const residualExposureObj = {
        value: residualExposure,
        weight: { "Very Low": 1, Low: 2, Medium: 3, High: 4, "Very High": 5 }[residualExposure] || 3,
      };

      // Update the risk object directly with metadata
      risk.asset_value = assetValue;
      risk.department = department;
      risk.risk_owner = riskOwner;
      risk.target_date = targetDate;
      risk.risk_progress = riskProgress;
      risk.residual_exposure = residualExposureObj;

      // Mark that this risk has metadata
      risk.has_metadata = true;
    });

    try {
      // Show loading state
      const submitBtn = document.getElementById("saveMetadataBtn");
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

      // Close modal first
      this.closeMetadataModal();
      this.showNotification("✅ Metadata saved! Processing for report generation...", "success");

      // Mark metadata as completed in current state
      if (this.currentWorkflowStatus) {
        this.currentWorkflowStatus.metadata_completed = true;
        this.currentWorkflowStatus.show_metadata_popup = false;
      }

      // Send report generation request to workflow via WebSocket
      this.sendMessage("proceed to report generation");
    } catch (error) {
      console.error("Error saving metadata:", error);
      this.showNotification("❌ Failed to save metadata. Please try again.", "error");

      // Reset button
      const submitBtn = document.getElementById("saveMetadataBtn");
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Save All Metadata';
    }
  }

  closeMetadataModal() {
    const modal = document.getElementById("metadataModal");
    modal.style.display = "none";
  }
}

// Global functions
function sendQuickMessage(message) {
  if (window.chat && window.chat.isConnected) {
    window.chat.sendMessage(message);
  } else {
    window.chat && window.chat.showNotification('Please connect first by entering your username and clicking "Launch Connection"', "warning");
  }
}

function showRiskDetails(riskId) {
  const modal = document.getElementById("riskModal");
  const modalBody = document.getElementById("riskModalBody");

  // Find the risk data from the stored risks
  let riskData = null;
  if (window.chat && window.chat.currentRisks) {
    riskData = window.chat.currentRisks.find((risk) => risk.risk_id === riskId);
  }

  if (riskData) {
    modalBody.innerHTML = `
        <div class="risk-detail-content">
            <div class="risk-detail-header">
                <h3>Risk Details: ${riskData.risk_id}</h3>
                <span class="risk-status-badge status-${riskData.is_approved ? "approved" : "pending"}">${riskData.is_approved ? "Approved" : "Pending"}</span>
            </div>
            
            <div class="risk-detail-section">
                <h4><i class="fas fa-exclamation-triangle"></i> Description</h4>
                <p>${riskData.risk_description || "No description available"}</p>
            </div>
            
            <div class="risk-detail-grid">
                <div class="risk-detail-item">
                    <h4><i class="fas fa-chart-line"></i> Likelihood</h4>
                    <span class="risk-value ${riskData.likelihood?.value?.toLowerCase() || "unknown"}">${riskData.likelihood?.value || "N/A"}</span>
                </div>
                <div class="risk-detail-item">
                    <h4><i class="fas fa-impact"></i> Impact</h4>
                    <span class="risk-value ${riskData.impact?.value?.toLowerCase() || "unknown"}">${riskData.impact?.value || "N/A"}</span>
                </div>
            </div>
            
            <div class="risk-detail-section">
                <h4><i class="fas fa-shield-alt"></i> Treatment Strategy</h4>
                <p>${riskData.treatment_strategy}</p>
            </div>
            
            <div class="risk-detail-section">
                <h4><i class="fas fa-tools"></i> Treatment Measures</h4>
                <p>${Array.isArray(riskData.treatment_measures) ? riskData.treatment_measures.join(", ") : riskData.treatment_measures || "No measures defined"}</p>
            </div>
            
            <div class="risk-actions">
                <button class="btn btn-primary" onclick="editRisk('${riskId}')" ${riskData.is_approved ? "disabled" : ""}>
                    <i class="fas fa-edit"></i> ${riskData.is_approved ? "Risk Approved" : "Edit Risk"}
                </button>
                <button class="btn btn-success" onclick="approveRisk('${riskId}')" ${riskData.is_approved ? "disabled" : ""}>
                    <i class="fas fa-check"></i> ${riskData.is_approved ? "Already Approved" : "Approve Risk"}
                </button>
                <button class="btn btn-danger" onclick="rejectRisk('${riskId}')" ${riskData.is_approved ? "disabled" : ""}>
                    <i class="fas fa-times"></i> ${riskData.is_approved ? "Cannot Reject" : "Reject Risk"}
                </button>
            </div>
        </div>
    `;
  } else {
    modalBody.innerHTML = `
        <div class="risk-detail-error">
            <i class="fas fa-exclamation-circle"></i>
            <h4>Risk Not Found</h4>
            <p>Could not find details for risk ID: ${riskId}</p>
            <p>Please try refreshing the risk data.</p>
        </div>
    `;
  }

  modal.style.display = "block";
}

function editRisk(riskId) {
  closeRiskModal();
  if (window.chat && window.chat.isConnected) {
    // Suggest some common edit commands
    const editMessage = `Edit risk ${riskId}. You can say things like:
- "Change likelihood of ${riskId} to High"
- "Change impact of ${riskId} to Medium"  
- "Update description of ${riskId} to [new description]"
- "Change treatment strategy of ${riskId} to Mitigate"`;

    window.chat.addSystemMessage(editMessage);
    window.chat.messageInput.focus();
    window.chat.messageInput.placeholder = `Type your edit command for ${riskId}...`;
  }
}

function closeRiskModal() {
  const modal = document.getElementById("riskModal");
  modal.style.display = "none";
}

function closeMetadataModal() {
  if (window.chat) {
    window.chat.closeMetadataModal();
  }
}

function approveRisk(riskId) {
  if (window.chat && window.chat.isConnected) {
    window.chat.sendMessage(`Approve risk ${riskId}`);
    closeRiskModal();
  }
}

function rejectRisk(riskId) {
  if (window.chat && window.chat.isConnected) {
    window.chat.sendMessage(`Reject risk ${riskId}`);
    closeRiskModal();
  }
}

function clearChat() {
  if (window.chat && window.chat.messagesContainer) {
    const messages = window.chat.messagesContainer.querySelectorAll(".message, .risks-display");
    messages.forEach((msg) => msg.remove());

    // Reset to welcome screen
    window.chat.messagesContainer.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-content">
                    <div class="ai-avatar">
                        <i class="fas fa-robot"></i>
                        <div class="avatar-pulse"></div>
                    </div>
                    <h2>Chat Cleared</h2>
                    <p>Ready for a fresh conversation! What would you like to know about risk assessment?</p>
                </div>
            </div>
        `;

    window.chat.showNotification("Chat history cleared", "info");
  }
}

function exportChat() {
  if (window.chat && window.chat.messageHistory.length > 0) {
    const chatData = {
      username: window.chat.username,
      timestamp: new Date().toISOString(),
      messages: window.chat.messageHistory,
    };

    const dataStr = JSON.stringify(chatData, null, 2);
    const dataUri = "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);

    const exportFileDefaultName = `risk-assessment-chat-${window.chat.username}-${new Date().toISOString().split("T")[0]}.json`;

    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();

    window.chat.showNotification("Chat history exported successfully", "success");
  } else {
    window.chat && window.chat.showNotification("No chat history to export", "warning");
  }
}

function toggleTheme() {
  const newTheme = document.body.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.body.setAttribute("data-theme", newTheme);

  if (window.chat) {
    window.chat.currentTheme = newTheme;
    window.chat.saveToLocalStorage();
    window.chat.updateThemeToggle();
    window.chat.showNotification(`Switched to ${newTheme} theme`, "info");
  }
}

// Add theme toggle update method
RiskAssessmentChat.prototype.updateThemeToggle = function () {
  const themeToggle = document.querySelector(".theme-toggle i");
  if (themeToggle) {
    themeToggle.className = this.currentTheme === "dark" ? "fas fa-sun" : "fas fa-moon";
  }
};

// Close modal when clicking outside
window.onclick = function (event) {
  const modal = document.getElementById("riskModal");
  if (event.target === modal) {
    closeRiskModal();
  }
};

// Report viewing and download functions
function viewReportInModal(encodedContent, encodedTitle) {
  const content = decodeURIComponent(encodedContent);
  const title = decodeURIComponent(encodedTitle);
  
  // Create report modal
  const modal = document.createElement("div");
  modal.className = "report-modal";
  modal.innerHTML = `
    <div class="report-modal-backdrop" onclick="closeReportModal()"></div>
    <div class="report-modal-content">
      <div class="report-modal-header">
        <h3><i class="fas fa-file-shield"></i> ${title}</h3>
        <button class="modal-close" onclick="closeReportModal()">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="report-modal-body">
        ${content}
      </div>
      <div class="report-modal-footer">
        <button class="btn btn-secondary" onclick="closeReportModal()">
          <i class="fas fa-times"></i> Close
        </button>
        <button class="btn btn-primary" onclick="downloadReport('${encodedContent}', '${encodedTitle}')">
          <i class="fas fa-download"></i> Download Report
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Store reference for closing
  window.currentReportModal = modal;
}

function closeReportModal() {
  if (window.currentReportModal) {
    document.body.removeChild(window.currentReportModal);
    window.currentReportModal = null;
  }
}

function downloadReport(encodedContent, encodedTitle) {
  const content = decodeURIComponent(encodedContent);
  const title = decodeURIComponent(encodedTitle);
  
  // Create blob and download
  const blob = new Blob([content], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.html`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  URL.revokeObjectURL(url);
  
  if (window.chat) {
    window.chat.showNotification("Report downloaded successfully!", "success");
  }
}

// Initialize the chat application
document.addEventListener("DOMContentLoaded", () => {
  window.chat = new RiskAssessmentChat();

  // Show welcome notification
  setTimeout(() => {
    if (!window.chat.isConnected) {
      window.chat.showNotification("Welcome! Enter your username and connect to start chatting with the AI.", "info");
    }
  }, 1000);
});
