/**
 * Risk Management Agent - Frontend Application
 * Complete integration with the backend API and real-time features
 */

class RiskManagementApp {
  constructor() {
    // Configuration
    this.config = {
      apiBaseUrl: "http://localhost:8000",
      wsBaseUrl: "ws://localhost:8000",
      version: "1.0.0",
    };

    // Application state
    this.state = {
      isAuthenticated: false,
      user: null,
      currentSection: "chat",
      threadId: null,
      token: null,
      websocket: null,
      isConnected: false,
      currentPopup: null,
      risks: {
        generated: [],
        finalized: [],
      },
      reports: [],
      metrics: null,
      matrix: {
        size: "3x3",
        likelihoodScale: ["Low", "Medium", "High"],
        impactScale: ["Low", "Medium", "High"],
      },
    };

    // DOM elements
    this.elements = {};

    // Initialize the application
    this.init();
  }

  /**
   * Initialize the application
   */
  async init() {
    try {
      console.log("🚀 Initializing Risk Management Agent...");

      // Cache DOM elements
      this.cacheElements();

      // Setup event listeners
      this.setupEventListeners();

      // Check for existing authentication
      await this.checkExistingAuth();

      // Hide loading screen
      this.hideLoadingScreen();

      console.log("✅ Application initialized successfully");
    } catch (error) {
      console.error("❌ Application initialization failed:", error);
      this.showNotification("Application initialization failed", "error");
      this.hideLoadingScreen();
    }
  }

  /**
   * Cache DOM elements for better performance
   */
  cacheElements() {
    // Containers
    this.elements.loadingScreen = document.getElementById("loading-screen");
    this.elements.authContainer = document.getElementById("auth-container");
    this.elements.appContainer = document.getElementById("app-container");

    // Auth forms
    this.elements.loginForm = document.getElementById("login-form");
    this.elements.registerForm = document.getElementById("register-form");
    this.elements.loginFormElement = document.getElementById("login-form-element");
    this.elements.registerFormElement = document.getElementById("register-form-element");

    // Navigation
    this.elements.navItems = document.querySelectorAll(".nav-item");
    this.elements.contentSections = document.querySelectorAll(".content-section");

    // Header elements
    this.elements.userName = document.getElementById("user-name");
    this.elements.userOrganization = document.getElementById("user-organization");
    this.elements.progressFill = document.getElementById("progress-fill");
    this.elements.progressText = document.getElementById("progress-text");

    // Chat elements
    this.elements.chatMessages = document.getElementById("chat-messages");
    this.elements.chatInput = document.getElementById("chat-input");
    this.elements.sendMessage = document.getElementById("send-message");
    this.elements.connectionStatus = document.getElementById("connection-status");
    this.elements.quickActionBtns = document.querySelectorAll(".quick-action-btn");

    // Risk elements
    this.elements.risksContainer = document.getElementById("risks-container");
    this.elements.riskFilter = document.getElementById("risk-filter");

    // Reports elements
    this.elements.reportsContainer = document.getElementById("reports-container");

    // Matrix elements
    this.elements.matrixSize = document.getElementById("matrix-size");
    this.elements.matrixVisualization = document.getElementById("matrix-visualization");

    // Dashboard elements
    this.elements.workflowProgress = document.getElementById("workflow-progress");
    this.elements.riskChart = document.getElementById("risk-chart");
    this.elements.recentActivity = document.getElementById("recent-activity");
    this.elements.systemStatus = document.getElementById("system-status");

    // Stats elements
    this.elements.statGenerated = document.getElementById("stat-generated");
    this.elements.statFinalized = document.getElementById("stat-finalized");
    this.elements.statReports = document.getElementById("stat-reports");

    // Popups
    this.elements.riskSelectionPopup = document.getElementById("risk-selection-popup");
    this.elements.dataCollectionPopup = document.getElementById("data-collection-popup");
    this.elements.settingsPopup = document.getElementById("settings-popup");
    this.elements.notificationToast = document.getElementById("notification-toast");

    // Popup content areas
    this.elements.riskSelectionTable = document.getElementById("risk-selection-table");
    this.elements.dataCollectionForm = document.getElementById("data-collection-form");
  }

  /**
   * Setup all event listeners
   */
  setupEventListeners() {
    // Auth form listeners
    document.getElementById("show-register").addEventListener("click", (e) => {
      e.preventDefault();
      this.showRegisterForm();
    });

    document.getElementById("show-login").addEventListener("click", (e) => {
      e.preventDefault();
      this.showLoginForm();
    });

    this.elements.loginFormElement.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleLogin();
    });

    this.elements.registerFormElement.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleRegister();
    });

    // Navigation listeners
    this.elements.navItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const section = item.dataset.section;
        this.switchSection(section);
      });
    });

    // Header button listeners
    document.getElementById("logout-btn").addEventListener("click", () => {
      this.handleLogout();
    });

    document.getElementById("settings-btn").addEventListener("click", () => {
      this.showPopup("settings-popup");
    });

    // Chat listeners
    this.elements.sendMessage.addEventListener("click", () => {
      this.sendChatMessage();
    });

    this.elements.chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendChatMessage();
      }
    });

    document.getElementById("clear-chat").addEventListener("click", () => {
      this.clearChatHistory();
    });

    // Quick action listeners
    this.elements.quickActionBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const message = btn.dataset.message;
        this.elements.chatInput.value = message;
        this.sendChatMessage();
      });
    });

    // Risk management listeners
    document.getElementById("generate-risks-btn").addEventListener("click", () => {
      this.generateRisks();
    });

    this.elements.riskFilter.addEventListener("change", () => {
      this.filterRisks();
    });

    // Report listeners
    document.getElementById("generate-report-btn").addEventListener("click", () => {
      this.generateReport();
    });

    document.getElementById("export-report-btn").addEventListener("click", () => {
      this.exportReport();
    });

    document.getElementById("download-pdf-btn").addEventListener("click", () => {
      this.downloadReportPDF();
    });

    // Matrix listeners
    document.getElementById("update-matrix-btn").addEventListener("click", () => {
      this.updateMatrix();
    });

    // Popup listeners
    document.querySelectorAll(".popup-close").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const popupId = btn.dataset.popup;
        this.hidePopup(popupId);
      });
    });

    // Risk selection popup listeners
    document.getElementById("cancel-risk-selection").addEventListener("click", () => {
      this.hidePopup("risk-selection-popup");
    });

    document.getElementById("finalize-risks").addEventListener("click", () => {
      this.finalizeSelectedRisks();
    });

    // Data collection popup listeners
    document.getElementById("cancel-data-collection").addEventListener("click", () => {
      this.hidePopup("data-collection-popup");
    });

    document.getElementById("submit-additional-data").addEventListener("click", () => {
      this.submitAdditionalData();
    });

    // Settings listeners
    document.getElementById("save-settings").addEventListener("click", () => {
      this.saveSettings();
    });

    // Notification close listener
    document.querySelector(".notification-close").addEventListener("click", () => {
      this.hideNotification();
    });

    // Popup overlay listeners (close on outside click)
    document.querySelectorAll(".popup-overlay").forEach((overlay) => {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
          this.hidePopup(overlay.id);
        }
      });
    });
  }

  /**
   * Check for existing authentication token
   */
  async checkExistingAuth() {
    const token = localStorage.getItem("risk_agent_token");
    if (token) {
      try {
        const response = await this.apiCall("/api/auth/validate", "GET", null, token);
        if (response.success) {
          this.handleAuthSuccess(response, token);
          return;
        }
      } catch (error) {
        console.log("Existing token invalid, showing login");
        localStorage.removeItem("risk_agent_token");
      }
    }

    // Show auth container if no valid token
    this.showAuthContainer();
  }

  /**
   * Handle user login
   */
  async handleLogin() {
    console.log("handleLogin function called");
    try {
      const username = document.getElementById("login-username").value;
      const password = document.getElementById("login-password").value;

      console.log("Login attempt:", { username, hasPassword: !!password });

      if (!username || !password) {
        console.log("Missing username or password");
        this.showNotification("Please fill in all fields", "error");
        return;
      }

      console.log("Making login API call to:", `${this.config.apiBaseUrl}/api/auth/login`);
      const loginData = {
        name: username,
        password: password,
      };
      console.log("Login data:", loginData);

      const response = await this.apiCall("/api/auth/login", "POST", loginData);

      console.log("Login response received:", response);

      if (response && response.success) {
        console.log("Login successful, calling handleAuthSuccess");
        this.handleAuthSuccess(response, response.token);
        this.showNotification("Login successful!", "success");
      } else {
        console.log("Login failed:", response?.message || "No response");
        this.showNotification(response?.message || "Login failed", "error");
      }
    } catch (error) {
      console.error("Login error caught:", error);
      console.error("Error stack:", error.stack);
      this.showNotification(`Login failed: ${error.message}`, "error");
    }
  }

  /**
   * Handle user registration
   */
  async handleRegister() {
    try {
      const username = document.getElementById("register-username").value;
      const password = document.getElementById("register-password").value;
      const organization = document.getElementById("register-organization").value;
      const industry = document.getElementById("register-industry").value;

      if (!username || !password || !organization || !industry) {
        this.showNotification("Please fill in all fields", "error");
        return;
      }

      const response = await this.apiCall("/api/auth/register", "POST", {
        name: username,
        password: password,
        organization: organization,
        industry: industry,
      });

      if (response.success) {
        this.handleAuthSuccess(response, response.token);
        this.showNotification("Registration successful! Welcome!", "success");
      } else {
        this.showNotification(response.message || "Registration failed", "error");
      }
    } catch (error) {
      console.error("Registration error:", error);
      this.showNotification("Registration failed. Please try again.", "error");
    }
  }

  /**
   * Handle successful authentication
   */
  handleAuthSuccess(response, token) {
    // Update application state
    this.state.isAuthenticated = true;
    this.state.user = response.user_data;
    this.state.threadId = response.thread_id;
    this.state.token = token;

    // Store token
    localStorage.setItem("risk_agent_token", token);

    // Update UI
    this.elements.userName.textContent = this.state.user.name;
    this.elements.userOrganization.textContent = this.state.user.organization;

    // Update navigation counts
    this.updateNavigationCounts();

    // Show main application
    this.showMainApp();

    // Initialize WebSocket connection
    this.connectWebSocket();

    // Load initial data
    this.loadInitialData();
  }

  /**
   * Handle user logout
   */
  async handleLogout() {
    try {
      // Close WebSocket connection
      if (this.state.websocket) {
        this.state.websocket.close();
      }

      // Call logout API
      await this.apiCall("/api/auth/logout", "POST");

      // Clear local state
      this.state.isAuthenticated = false;
      this.state.user = null;
      this.state.threadId = null;
      this.state.token = null;
      this.state.websocket = null;
      this.state.isConnected = false;

      // Clear stored token
      localStorage.removeItem("risk_agent_token");

      // Show auth container
      this.showAuthContainer();

      this.showNotification("Logged out successfully", "success");
    } catch (error) {
      console.error("Logout error:", error);
      // Force logout even if API call fails
      this.showAuthContainer();
    }
  }

  /**
   * Check if the current token is expired
   */
  isTokenExpired() {
    if (!this.state.token) return true;

    try {
      // Decode JWT token to check expiration
      const tokenParts = this.state.token.split(".");
      if (tokenParts.length !== 3) return true;

      const payload = JSON.parse(atob(tokenParts[1]));
      const currentTime = Math.floor(Date.now() / 1000);

      return payload.exp && payload.exp < currentTime;
    } catch (error) {
      console.error("Error checking token expiration:", error);
      return true;
    }
  }

  /**
   * Connect to WebSocket for real-time communication
   */
  connectWebSocket() {
    if (!this.state.user || !this.state.token) return;

    // Check if token is expired before connecting
    if (this.isTokenExpired()) {
      console.log("Token expired, forcing logout");
      this.showNotification("Session expired. Please log in again.", "warning");
      this.handleLogout();
      return;
    }

    try {
      const wsUrl = `${this.config.wsBaseUrl}/api/ws/chat/${this.state.user.user_id}?token=${this.state.token}`;
      this.state.websocket = new WebSocket(wsUrl);

      this.state.websocket.onopen = () => {
        console.log("🔌 WebSocket connected");
        this.state.isConnected = true;
        this.updateConnectionStatus(true);
      };

      this.state.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleWebSocketMessage(data);
        } catch (error) {
          console.error("WebSocket message parsing error:", error);
        }
      };

      this.state.websocket.onclose = (event) => {
        console.log("🔌 WebSocket disconnected", event.code, event.reason);
        this.state.isConnected = false;
        this.updateConnectionStatus(false);

        // If connection was rejected due to authentication (403), force logout
        if (event.code === 1008 || event.code === 1002) {
          // 1008 = Policy Violation, 1002 = Protocol Error
          console.log("WebSocket authentication failed, logging out...");
          this.showNotification("Session expired. Please log in again.", "warning");
          this.handleLogout();
          return;
        }

        // Attempt to reconnect after 3 seconds for other errors
        if (this.state.isAuthenticated) {
          setTimeout(() => {
            this.connectWebSocket();
          }, 3000);
        }
      };

      this.state.websocket.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.updateConnectionStatus(false);

        // Check if it's likely an authentication error
        if (error.target && error.target.readyState === WebSocket.CLOSED) {
          console.log("WebSocket closed due to error, possibly authentication");
        }
      };
    } catch (error) {
      console.error("WebSocket connection error:", error);
      this.updateConnectionStatus(false);
    }
  }

  /**
   * Handle WebSocket messages
   */
  handleWebSocketMessage(data) {
    console.log("WebSocket message received:", data);

    switch (data.type) {
      case "chat_response":
        console.log("Handling chat_response:", data.data);
        this.handleChatResponse(data.data);
        break;

      case "popup":
        console.log("Handling popup:", data.data);
        console.log("Calling handlePopupTrigger with:", data.data);
        try {
          // Ensure we have the required fields
          if (!data.data) {
            console.error("Missing data in popup message");
            return;
          }

          // Check if we need to adapt the data format
          const popupData = data.data;
          if (!popupData.popup_type && popupData.type) {
            console.log("Adapting popup data format - using 'type' as 'popup_type'");
            popupData.popup_type = popupData.type;
          }

          // If we have risks directly without being nested in popup_data
          if (popupData.risks && !popupData.popup_data) {
            console.log("Adapting popup data format - wrapping 'risks' in 'popup_data'");
            popupData.popup_data = { risks: popupData.risks };

            // Assume this is a risk selection popup if not specified
            if (!popupData.popup_type) {
              popupData.popup_type = "risk_selection_popup";
            }
          }

          this.handlePopupTrigger(popupData);
          console.log("handlePopupTrigger completed successfully");
        } catch (error) {
          console.error("Error in handlePopupTrigger:", error);
        }
        break;

      case "stage_update":
        console.log("Handling stage_update:", data.data);
        this.handleStageUpdate(data.data);
        break;

      case "chat_complete":
        console.log("Handling chat_complete:", data.data);
        this.handleChatComplete(data.data);
        break;

      case "error":
        console.log("Handling error:", data.data);
        this.handleWebSocketError(data.data);
        break;

      case "notification":
        console.log("Handling notification:", data.data);
        this.showNotification(data.data.message, "info");
        break;

      case "connection_established":
        console.log("WebSocket connection established:", data.data);
        break;

      default:
        console.log("Unknown WebSocket message type:", data.type, data);
    }
  }

  /**
   * Send chat message via WebSocket
   */
  sendChatMessage() {
    const message = this.elements.chatInput.value.trim();
    if (!message) return;

    // Add user message to chat
    this.addChatMessage(message, "user");

    // Clear input
    this.elements.chatInput.value = "";

    // Send via WebSocket if connected
    if (this.state.websocket && this.state.isConnected) {
      this.state.websocket.send(
        JSON.stringify({
          type: "chat",
          data: {
            message: message,
            thread_id: this.state.threadId,
          },
        })
      );
    } else {
      // Fallback to HTTP API
      this.sendChatMessageHttp(message);
    }
  }

  /**
   * Send chat message via HTTP API (fallback)
   */
  async sendChatMessageHttp(message) {
    try {
      const response = await this.apiCall("/api/chat/message", "POST", {
        message: message,
        thread_id: this.state.threadId,
      });

      if (response.success) {
        this.addChatMessage(response.response, "assistant");

        // Handle popup if present - use the standard envelope structure
        if (response.popup_type && response.popup_data) {
          console.log("Popup data detected in HTTP response, creating proper envelope");
          // Create the standard envelope structure
          this.handleWebSocketMessage({
            type: "popup",
            data: {
              popup_type: response.popup_type,
              popup_data: response.popup_data,
            },
          });
        }
      } else {
        this.addChatMessage("Sorry, I encountered an error. Please try again.", "assistant");
      }
    } catch (error) {
      console.error("Chat message error:", error);
      this.addChatMessage("Connection error. Please check your connection and try again.", "assistant");
    }
  }

  /**
   * Handle chat response from WebSocket
   */
  handleChatResponse(data) {
    console.log("Processing chat response data:", data);

    if (data.status === "processing") {
      console.log("Showing typing indicator for processing");
      // Show typing indicator if not already present
      this.showTypingIndicator();
    } else if (data.message && !data.partial) {
      console.log("Adding chat message:", data.message);
      // Hide typing indicator and show message
      this.hideTypingIndicator();
      this.addChatMessage(data.message, "assistant");
      
      // Check for report completion and show PDF download button
      this.checkForReportCompletion(data.message);
    } else if (data.message && data.partial) {
      console.log("Received partial message (not adding to chat):", data.message);
    } else {
      console.log("Chat response data doesn't match expected format:", data);
    }
  }

  /**
   * Check if message indicates report completion and show PDF download button
   */
  checkForReportCompletion(message) {
    if (message && (
      message.includes("Risk Management Report is Ready") ||
      message.includes("report is now available") ||
      message.includes("report generated") ||
      message.includes("Congratulations on completing your risk assessment")
    )) {
      this.togglePDFDownloadButton(true);
      this.showNotification("Your report is ready! You can now download it as a PDF.", "success");
      
      // Add download button in chat
      this.addDownloadButtonToChat();
    }
  }

  /**
   * Add a download button directly in the chat interface
   */
  addDownloadButtonToChat() {
    const downloadMessage = `
      <div class="chat-download-container">
        <div class="download-message">
          <i class="fas fa-file-pdf"></i>
          <span>Your risk assessment report is ready!</span>
        </div>
        <button class="btn btn-primary chat-download-btn" onclick="app.downloadReportPDF()">
          <i class="fas fa-download"></i> Download PDF Report
        </button>
      </div>
    `;
    
    this.addChatMessage(downloadMessage, "assistant", true); // true indicates HTML content
  }

  /**
   * Toggle PDF download button visibility
   */
  togglePDFDownloadButton(show = false) {
    const downloadBtn = document.getElementById("download-pdf-btn");
    if (downloadBtn) {
      downloadBtn.style.display = show ? "inline-block" : "none";
    }
  }

  /**
   * Handle popup trigger
   */
  handlePopupTrigger(data) {
    console.log("handlePopupTrigger called with full data:", data);
    console.log("Data keys:", Object.keys(data));
    console.log("Data type:", typeof data);

    if (!data) {
      console.error("Error: No data provided to handlePopupTrigger");
      return;
    }

    const popupType = data.popup_type;
    const popupData = data.popup_data;

    console.log("Extracted popup type:", popupType, "type:", typeof popupType);
    console.log("Extracted popup data:", popupData);

    if (!popupType) {
      console.error("Error: No popup_type in data");
      return;
    }

    if (!popupData) {
      console.error("Error: No popup_data in data");
      return;
    }

    // Additional debugging for exact match
    console.log("popupType === 'risk_selection':", popupType === "risk_selection");
    console.log("popupType === 'risk_selection_popup':", popupType === "risk_selection_popup");

    // Normalize popup type (trim whitespace, convert to lowercase for comparison)
    const normalizedPopupType = String(popupType || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
    console.log("Normalized popup type:", normalizedPopupType);

    switch (normalizedPopupType) {
      case "risk_selection":
      case "risk_selection_popup":
        console.log("Matching risk_selection popup type, calling showRiskSelectionPopup");
        this.showRiskSelectionPopup(popupData);
        break;

      case "data_collection":
      case "data_collection_popup":
        console.log("Matching data_collection popup type, calling showDataCollectionPopup");
        this.showDataCollectionPopup(popupData);
        break;

      default:
        console.log("Unknown popup type:", popupType);
        console.log("Normalized popup type:", normalizedPopupType);
        console.log("Available popup types should be: risk_selection, risk_selection_popup, data_collection, data_collection_popup");

        // Fallback check for risk selection
        if (normalizedPopupType.includes("risk") && normalizedPopupType.includes("selection")) {
          console.log("Fallback: detected risk selection popup, calling showRiskSelectionPopup");
          this.showRiskSelectionPopup(popupData);
        }
    }
  }

  /**
   * Add message to chat interface
   */
  addChatMessage(message, sender, isHtml = false) {
    const messageElement = document.createElement("div");
    messageElement.className = `chat-message ${sender}`;

    const timestamp = new Date().toLocaleTimeString();

    // Use raw HTML if isHtml is true, otherwise format the message
    const messageContent = isHtml ? message : this.formatMessage(message);

    messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-text">${messageContent}</div>
                <div class="message-time">${timestamp}</div>
            </div>
        `;

    this.elements.chatMessages.appendChild(messageElement);
    this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
  }

  /**
   * Format message content (handle markdown, links, etc.)
   */
  formatMessage(message) {
    // Basic formatting - can be enhanced with a markdown library
    return message
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/\n/g, "<br>")
      .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
  }

  /**
   * Show typing indicator
   */
  showTypingIndicator() {
    // Remove existing typing indicator
    this.hideTypingIndicator();

    const typingElement = document.createElement("div");
    typingElement.className = "chat-message assistant typing";
    typingElement.id = "typing-indicator";

    typingElement.innerHTML = `
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

    this.elements.chatMessages.appendChild(typingElement);
    this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
  }

  /**
   * Hide typing indicator
   */
  hideTypingIndicator() {
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  /**
   * Clear chat history
   */
  async clearChatHistory() {
    try {
      const response = await this.apiCall(`/api/chat/clear/${this.state.threadId}`, "DELETE");

      if (response.success) {
        this.elements.chatMessages.innerHTML = "";
        this.showNotification("Chat history cleared", "success");
      }
    } catch (error) {
      console.error("Clear chat error:", error);
      this.showNotification("Failed to clear chat history", "error");
    }
  }

  /**
   * Show risk selection popup
   */
  showRiskSelectionPopup(popupData) {
    console.log("showRiskSelectionPopup called with data:", popupData);

    // Handle different data structures that might be passed
    let risks = [];
    if (Array.isArray(popupData)) {
      console.log("popupData is an array, using directly as risks");
      risks = popupData;
    } else if (popupData && popupData.risks) {
      console.log("popupData contains risks property");
      risks = popupData.risks;
    } else if (popupData && popupData.popup_data && popupData.popup_data.risks) {
      console.log("popupData contains nested popup_data.risks property");
      risks = popupData.popup_data.risks;
    } else {
      console.error("Unable to extract risks from popupData:", popupData);
    }

    console.log("Number of risks:", risks.length);

    let cardHTML = `
            <div class="risk-finalization-container">
                <div class="finalization-header">
                    <h3><i class="fas fa-clipboard-check"></i> Complete Risk Information</h3>
                    <p>Fill in all details for each risk. This will finalize them directly to your risk register.</p>
                    <div class="bulk-actions">
                        <button type="button" id="select-all-risks" class="btn btn-secondary btn-sm">
                            <i class="fas fa-check-square"></i> Select All
                        </button>
                        <span class="selected-count">0 risks selected</span>
                    </div>
                </div>
                <div class="risks-grid">
        `;

    risks.forEach((risk, index) => {
      cardHTML += `
                <div class="risk-card" data-risk-id="${risk.risk_id}">
                    <div class="risk-card-header">
                        <div class="risk-selection">
                            <input type="checkbox" class="risk-checkbox" data-risk-id="${risk.risk_id}" id="risk-${risk.risk_id}">
                            <label for="risk-${risk.risk_id}" class="risk-title">Risk ${index + 1}</label>
                        </div>
                        <button class="btn btn-sm btn-outline-primary preview-risk-btn" data-risk-id="${risk.risk_id}">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                    
                    <div class="risk-card-content">
                        <!-- Basic Risk Information -->
                        <div class="form-section">
                            <h4><i class="fas fa-exclamation-triangle"></i> Risk Details</h4>
                            <div class="form-group">
                                <label>Description</label>
                                <textarea class="form-control risk-description" data-field="description" 
                                        maxlength="500" rows="3" placeholder="Describe the risk...">${risk.description}</textarea>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Impact</label>
                                    <select class="form-control risk-impact" data-field="impact">
                                        ${this.state.matrix.impactScale.map((level) => 
                                            `<option value="${level}" ${level === risk.impact ? "selected" : ""}>${level}</option>`
                                        ).join("")}
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>Likelihood</label>
                                    <select class="form-control risk-likelihood" data-field="likelihood">
                                        ${this.state.matrix.likelihoodScale.map((level) => 
                                            `<option value="${level}" ${level === risk.likelihood ? "selected" : ""}>${level}</option>`
                                        ).join("")}
                                    </select>
                                </div>
                            </div>
                        </div>

                        <!-- Treatment Information -->
                        <div class="form-section">
                            <h4><i class="fas fa-shield-alt"></i> Treatment Strategy</h4>
                            <div class="form-group">
                                <label>Strategy</label>
                                <select class="form-control risk-strategy" data-field="treatment_strategy">
                                    <option value="Accept" ${risk.treatment_strategy === "Accept" ? "selected" : ""}>Accept</option>
                                    <option value="Avoid" ${risk.treatment_strategy === "Avoid" ? "selected" : ""}>Avoid</option>
                                    <option value="Mitigate" ${risk.treatment_strategy === "Mitigate" ? "selected" : ""}>Mitigate</option>
                                    <option value="Transfer" ${risk.treatment_strategy === "Transfer" ? "selected" : ""}>Transfer</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Treatment Measures</label>
                                <textarea class="form-control risk-measures" data-field="treatment_measures" 
                                        rows="2" placeholder="Specific measures to address this risk...">${risk.treatment_measures || ''}</textarea>
                            </div>
                        </div>

                        <!-- Additional Data Collection Fields -->
                        <div class="form-section">
                            <h4><i class="fas fa-database"></i> Additional Information</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Asset Value</label>
                                    <input type="text" class="form-control" data-field="asset_value" 
                                           placeholder="e.g., $100,000" value="${risk.asset_value || ''}">
                                </div>
                                <div class="form-group">
                                    <label>Department</label>
                                    <input type="text" class="form-control" data-field="department" 
                                           placeholder="e.g., IT Operations" value="${risk.department || ''}">
                                </div>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Risk Owner</label>
                                    <input type="text" class="form-control" data-field="risk_owner" 
                                           placeholder="e.g., John Smith" value="${risk.risk_owner || ''}">
                                </div>
                                <div class="form-group">
                                    <label>Target Date</label>
                                    <input type="date" class="form-control" data-field="target_date" 
                                           value="${risk.target_date || ''}">
                                </div>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Risk Progress</label>
                                    <select class="form-control" data-field="risk_progress">
                                        <option value="Not Started" ${(risk.risk_progress || 'Not Started') === 'Not Started' ? 'selected' : ''}>Not Started</option>
                                        <option value="In Progress" ${risk.risk_progress === 'In Progress' ? 'selected' : ''}>In Progress</option>
                                        <option value="Completed" ${risk.risk_progress === 'Completed' ? 'selected' : ''}>Completed</option>
                                        <option value="On Hold" ${risk.risk_progress === 'On Hold' ? 'selected' : ''}>On Hold</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>Residual Exposure</label>
                                    <select class="form-control" data-field="residual_exposure">
                                        <option value="Low" ${(risk.residual_exposure || 'Low') === 'Low' ? 'selected' : ''}>Low</option>
                                        <option value="Medium" ${risk.residual_exposure === 'Medium' ? 'selected' : ''}>Medium</option>
                                        <option value="High" ${risk.residual_exposure === 'High' ? 'selected' : ''}>High</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
    });

    cardHTML += `
                </div>
            </div>
        `;

    this.elements.riskSelectionTable.innerHTML = cardHTML;

    // Add event listeners for select all
    document.getElementById("select-all-risks").addEventListener("click", (e) => {
      const checkboxes = document.querySelectorAll(".risk-checkbox");
      const allChecked = Array.from(checkboxes).every(cb => cb.checked);
      checkboxes.forEach((cb) => (cb.checked = !allChecked));
      
      // Update button text and selected count
      const button = e.target.closest('button');
      const selectedCount = document.querySelector('.selected-count');
      if (!allChecked) {
        button.innerHTML = '<i class="fas fa-square"></i> Deselect All';
        selectedCount.textContent = `${checkboxes.length} risks selected`;
      } else {
        button.innerHTML = '<i class="fas fa-check-square"></i> Select All';
        selectedCount.textContent = '0 risks selected';
      }
    });

    // Add event listeners for individual checkboxes
    document.querySelectorAll(".risk-checkbox").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        const checkedBoxes = document.querySelectorAll(".risk-checkbox:checked");
        const selectedCount = document.querySelector('.selected-count');
        const selectAllBtn = document.getElementById("select-all-risks");
        
        selectedCount.textContent = `${checkedBoxes.length} risks selected`;
        
        // Update select all button state
        const totalBoxes = document.querySelectorAll(".risk-checkbox");
        if (checkedBoxes.length === totalBoxes.length) {
          selectAllBtn.innerHTML = '<i class="fas fa-square"></i> Deselect All';
        } else {
          selectAllBtn.innerHTML = '<i class="fas fa-check-square"></i> Select All';
        }
      });
    });

    // Add event listeners for preview buttons
    document.querySelectorAll(".preview-risk-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const riskId = btn.dataset.riskId;
        this.previewRisk(riskId, risks);
      });
    });

    console.log("About to call showPopup for risk-selection-popup");
    this.showPopup("risk-selection-popup");
    console.log("showRiskSelectionPopup function completed");
  }

  /**
   * Finalize selected risks
   */
  async finalizeSelectedRisks() {
    try {
      const selectedRisks = [];
      const editedRisks = [];

      // Get selected risks and their complete data
      document.querySelectorAll(".risk-checkbox:checked").forEach((checkbox) => {
        const riskId = checkbox.dataset.riskId;
        const card = checkbox.closest(".risk-card");

        selectedRisks.push(riskId);

        // Collect all form data from the card
        const editedRisk = {
          risk_id: riskId,
          // Basic risk information
          description: card.querySelector(".risk-description").value,
          impact: card.querySelector(".risk-impact").value,
          likelihood: card.querySelector(".risk-likelihood").value,
          treatment_strategy: card.querySelector(".risk-strategy").value,
          treatment_measures: card.querySelector(".risk-measures").value,
          // Additional data collection fields
          asset_value: card.querySelector("[data-field='asset_value']").value,
          department: card.querySelector("[data-field='department']").value,
          risk_owner: card.querySelector("[data-field='risk_owner']").value,
          target_date: card.querySelector("[data-field='target_date']").value,
          risk_progress: card.querySelector("[data-field='risk_progress']").value,
          residual_exposure: card.querySelector("[data-field='residual_exposure']").value
        };

        editedRisks.push(editedRisk);
      });

      if (selectedRisks.length === 0) {
        this.showNotification("Please select at least one risk", "warning");
        return;
      }

      // Send finalization request
      const response = await this.apiCall("/api/risks/finalize", "POST", {
        thread_id: this.state.threadId,
        selected_risk_ids: selectedRisks,
        edited_risks: editedRisks,
      });

      if (response.success) {
        this.hidePopup("risk-selection-popup");
        
        // Show completion message with next steps
        const completionMessage = `🎉 Successfully finalized ${selectedRisks.length} risk${selectedRisks.length > 1 ? 's' : ''}! 
        
What would you like to do next?
• Generate more risks for your organization
• Proceed to generate your comprehensive risk report`;
        
        this.addChatMessage(completionMessage, "assistant");
        this.showNotification(`${selectedRisks.length} risks finalized successfully!`, "success");
        
        // Refresh data
        this.loadRisks();
        this.updateQuickStats();
      } else {
        this.showNotification(response.message || "Failed to finalize risks", "error");
      }
    } catch (error) {
      console.error("Risk finalization error:", error);
      this.showNotification("Failed to finalize risks", "error");
    }
  }

  /**
   * Show data collection popup
   */
  showDataCollectionPopup(popupData) {
    const risks = popupData.risks || [];

    let formHTML = '<div class="data-collection-grid">';

    risks.forEach((risk, index) => {
      formHTML += `
                <div class="risk-data-card" data-risk-id="${risk.risk_id}">
                    <h4>Risk ${index + 1}</h4>
                    <p class="risk-description-preview">${risk.description.substring(0, 100)}...</p>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>Asset Value</label>
                            <input type="text" class="form-control" data-field="asset_value" 
                                   value="${risk.current_data?.asset_value || ""}" placeholder="e.g., $100,000">
                        </div>
                        <div class="form-group">
                            <label>Department</label>
                            <input type="text" class="form-control" data-field="department" 
                                   value="${risk.current_data?.department || ""}" placeholder="e.g., IT Operations">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>Risk Owner</label>
                            <input type="text" class="form-control" data-field="risk_owner" 
                                   value="${risk.current_data?.risk_owner || ""}" placeholder="e.g., John Smith">
                        </div>
                        <div class="form-group">
                            <label>Target Date</label>
                            <input type="date" class="form-control" data-field="target_date" 
                                   value="${risk.current_data?.target_date || ""}">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>Risk Progress</label>
                            <select class="form-control" data-field="risk_progress">
                                <option value="">Select Status</option>
                                <option value="Not Started" ${risk.current_data?.risk_progress === "Not Started" ? "selected" : ""}>Not Started</option>
                                <option value="Planning" ${risk.current_data?.risk_progress === "Planning" ? "selected" : ""}>Planning</option>
                                <option value="In Progress" ${risk.current_data?.risk_progress === "In Progress" ? "selected" : ""}>In Progress</option>
                                <option value="Completed" ${risk.current_data?.risk_progress === "Completed" ? "selected" : ""}>Completed</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Residual Exposure</label>
                            <select class="form-control" data-field="residual_exposure">
                                <option value="">Select Level</option>
                                ${this.state.matrix.impactScale.map((level) => `<option value="${level}" ${risk.current_data?.residual_exposure === level ? "selected" : ""}>${level}</option>`).join("")}
                            </select>
                        </div>
                    </div>
                </div>
            `;
    });

    formHTML += "</div>";

    this.elements.dataCollectionForm.innerHTML = formHTML;
    this.showPopup("data-collection-popup");
  }

  /**
   * Submit additional data
   */
  async submitAdditionalData() {
    try {
      const risksData = [];

      // Collect data from form
      document.querySelectorAll(".risk-data-card").forEach((card) => {
        const riskId = card.dataset.riskId;
        const riskData = { risk_id: riskId };

        // Collect all form fields
        card.querySelectorAll("[data-field]").forEach((field) => {
          const fieldName = field.dataset.field;
          riskData[fieldName] = field.value;
        });

        risksData.push(riskData);
      });

      // Send data to API
      const response = await this.apiCall("/api/risks/data-collection", "POST", {
        thread_id: this.state.threadId,
        risks_data: risksData,
      });

      if (response.success) {
        this.hidePopup("data-collection-popup");
        this.showNotification("Additional data saved successfully", "success");
        this.loadRisks();

        // Check if we should show report approval
        if (response.awaiting_approval) {
          this.showReportApprovalDialog();
        }
      } else {
        this.showNotification(response.message || "Failed to save additional data", "error");
      }
    } catch (error) {
      console.error("Data collection error:", error);
      this.showNotification("Failed to save additional data", "error");
    }
  }

  /**
   * Show report approval dialog
   */
  showReportApprovalDialog() {
    const message = `
            <div class="approval-dialog">
                <h3>Ready for Report Generation</h3>
                <p>Your risk assessment is complete! Would you like me to generate your comprehensive risk report?</p>
                <div class="approval-actions">
                    <button id="approve-report" class="btn btn-primary">
                        <i class="fas fa-check"></i> Yes, Generate Report
                    </button>
                    <button id="reject-report" class="btn btn-secondary">
                        <i class="fas fa-times"></i> Let me review first
                    </button>
                </div>
            </div>
        `;

    this.addChatMessage(message, "assistant");

    // Add event listeners for approval buttons
    setTimeout(() => {
      document.getElementById("approve-report")?.addEventListener("click", () => {
        this.approveReport(true);
      });

      document.getElementById("reject-report")?.addEventListener("click", () => {
        this.approveReport(false);
      });
    }, 100);
  }

  /**
   * Handle report approval
   */
  async approveReport(approved) {
    try {
      const response = await this.apiCall("/api/reports/approve", "POST", {
        thread_id: this.state.threadId,
        approved: approved,
      });

      if (response.success) {
        if (approved) {
          this.addChatMessage("Great! I'm generating your comprehensive risk report now...", "assistant");
          if (response.report_id) {
            this.showNotification("Risk report generated successfully!", "success");
            this.loadReports();
          }
        } else {
          this.addChatMessage("No problem! You can review your risks and let me know when you're ready for the report.", "assistant");
        }
      } else {
        this.showNotification(response.message || "Report approval failed", "error");
      }
    } catch (error) {
      console.error("Report approval error:", error);
      this.showNotification("Report approval failed", "error");
    }
  }

  /**
   * Generate risks via button
   */
  async generateRisks() {
    try {
      console.log("generateRisks called, sending API request...");
      const response = await this.apiCall("/api/risks/generate", "POST", {
        thread_id: this.state.threadId,
        additional_context: "",
      });

      console.log("Risk generation response:", response);

      if (response.success) {
        // Using the standard envelope format to ensure consistency with WebSocket handling
        if (response.popup_type && response.popup_data) {
          console.log("Received popup data from API, creating standard envelope");
          // Pass through the WebSocket message handler with the standard envelope
          this.handleWebSocketMessage({
            type: "popup",
            data: {
              popup_type: response.popup_type,
              popup_data: response.popup_data,
            },
          });
        } else if (response.popup_data) {
          // Legacy format - try to adapt
          console.log("Received legacy popup_data format, adapting to standard envelope");
          this.handleWebSocketMessage({
            type: "popup",
            data: {
              popup_type: "risk_selection_popup", // Assume this type if not specified
              popup_data: response.popup_data,
            },
          });
        } else {
          console.error("Response successful but missing popup_data");
          this.showNotification("Risks generated but display data is missing", "warning");
        }
      } else {
        console.error("Risk generation failed:", response.message || "Unknown error");
        this.showNotification(response.message || "Failed to generate risks", "error");
      }
    } catch (error) {
      console.error("Risk generation error:", error);
      this.showNotification("Failed to generate risks", "error");
    }
  }

  /**
   * Load and display risks
   */
  async loadRisks() {
    try {
      const filter = this.elements.riskFilter.value;
      let riskType = "finalized";

      if (filter === "generated") {
        riskType = "generated";
      }

      const response = await this.apiCall(`/api/risks/view?risk_type=${riskType}`, "GET");

      if (response.success) {
        this.displayRisks(response.risks, riskType);

        // Update state
        if (riskType === "finalized") {
          this.state.risks.finalized = response.risks;
        } else {
          this.state.risks.generated = response.risks;
        }
      }
    } catch (error) {
      console.error("Load risks error:", error);
      this.showNotification("Failed to load risks", "error");
    }
  }

  /**
   * Display risks in the UI
   */
  displayRisks(risks, type) {
    let html = "";

    if (risks.length === 0) {
      html = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>No ${type} risks found</h3>
                    <p>Start by generating some risks for your organization.</p>
                    <button class="btn btn-primary" onclick="app.generateRisks()">
                        <i class="fas fa-plus"></i> Generate Risks
                    </button>
                </div>
            `;
    } else {
      risks.forEach((risk) => {
        html += `
                    <div class="risk-card">
                        <div class="risk-header">
                            <div class="risk-priority ${this.getRiskPriority(risk.impact, risk.likelihood)}">
                                ${risk.impact} Impact, ${risk.likelihood} Likelihood
                            </div>
                            <div class="risk-actions">
                                <button class="btn btn-sm btn-secondary" onclick="app.editRisk('${risk.risk_id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                ${
                                  type === "generated"
                                    ? `
                                    <button class="btn btn-sm btn-danger" onclick="app.deleteRisk('${risk.risk_id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                `
                                    : ""
                                }
                            </div>
                        </div>
                        <div class="risk-content">
                            <p class="risk-description">${risk.description}</p>
                            <div class="risk-details">
                                <div class="risk-detail">
                                    <strong>Strategy:</strong> ${risk.treatment_strategy}
                                </div>
                                ${
                                  risk.department
                                    ? `
                                    <div class="risk-detail">
                                        <strong>Department:</strong> ${risk.department}
                                    </div>
                                `
                                    : ""
                                }
                                ${
                                  risk.risk_owner
                                    ? `
                                    <div class="risk-detail">
                                        <strong>Owner:</strong> ${risk.risk_owner}
                                    </div>
                                `
                                    : ""
                                }
                            </div>
                        </div>
                    </div>
                `;
      });
    }

    this.elements.risksContainer.innerHTML = html;
  }

  /**
   * Get risk priority class based on impact and likelihood
   */
  getRiskPriority(impact, likelihood) {
    const impactIndex = this.state.matrix.impactScale.indexOf(impact);
    const likelihoodIndex = this.state.matrix.likelihoodScale.indexOf(likelihood);

    if (impactIndex >= 2 && likelihoodIndex >= 2) return "high";
    if (impactIndex >= 1 && likelihoodIndex >= 1) return "medium";
    return "low";
  }

  /**
   * Load and display reports
   */
  async loadReports() {
    try {
      const response = await this.apiCall("/api/reports/view", "GET");

      if (response.success) {
        this.displayReports(response.reports_list || []);
        this.state.reports = response.reports_list || [];
      }
    } catch (error) {
      console.error("Load reports error:", error);
      this.showNotification("Failed to load reports", "error");
    }
  }

  /**
   * Display reports in the UI
   */
  displayReports(reports) {
    let html = "";

    if (reports.length === 0) {
      html = `
                <div class="empty-state">
                    <i class="fas fa-file-alt"></i>
                    <h3>No reports generated yet</h3>
                    <p>Complete your risk assessment to generate reports.</p>
                </div>
            `;
    } else {
      reports.forEach((report) => {
        const date = new Date(report.generated_at).toLocaleDateString();
        html += `
                    <div class="report-card">
                        <div class="report-header">
                            <h3>${report.organization} - Risk Report</h3>
                            <span class="report-date">${date}</span>
                        </div>
                        <div class="report-stats">
                            <div class="stat">
                                <span class="stat-value">${report.total_risks}</span>
                                <span class="stat-label">Total Risks</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">${report.high_priority_risks}</span>
                                <span class="stat-label">High Priority</span>
                            </div>
                        </div>
                        <div class="report-actions">
                            <button class="btn btn-primary" onclick="app.viewReport('${report.report_id}')">
                                <i class="fas fa-eye"></i> View Report
                            </button>
                            <button class="btn btn-secondary" onclick="app.downloadReportPDF('${report.report_id}')">
                                <i class="fas fa-file-pdf"></i> Download PDF
                            </button>
                            <button class="btn btn-secondary" onclick="app.exportReport('${report.report_id}')">
                                <i class="fas fa-download"></i> Export
                            </button>
                        </div>
                    </div>
                `;
      });
    }

    this.elements.reportsContainer.innerHTML = html;
  }

  /**
   * Update matrix configuration
   */
  async updateMatrix() {
    try {
      const newSize = this.elements.matrixSize.value;

      const response = await this.apiCall("/api/matrix/update", "PUT", {
        matrix_size: newSize,
        thread_id: this.state.threadId,
      });

      if (response.success) {
        this.state.matrix.size = newSize;
        this.state.matrix.likelihoodScale = response.new_likelihood_scale;
        this.state.matrix.impactScale = response.new_impact_scale;

        this.renderMatrixVisualization();
        this.showNotification("Matrix updated successfully", "success");
      } else {
        this.showNotification(response.message || "Failed to update matrix", "error");
      }
    } catch (error) {
      console.error("Matrix update error:", error);
      this.showNotification("Failed to update matrix", "error");
    }
  }

  /**
   * Render matrix visualization
   */
  renderMatrixVisualization() {
    const { likelihoodScale, impactScale } = this.state.matrix;

    let html = `
            <div class="matrix-grid">
                <div class="matrix-header">
                    <div class="matrix-corner"></div>
                    ${impactScale.map((level) => `<div class="matrix-header-cell">${level}</div>`).join("")}
                </div>
        `;

    likelihoodScale.forEach((likelihood, i) => {
      html += `<div class="matrix-row">`;
      html += `<div class="matrix-row-header">${likelihood}</div>`;

      impactScale.forEach((impact, j) => {
        const riskLevel = this.calculateMatrixRiskLevel(i, j, likelihoodScale.length);
        html += `
                    <div class="matrix-cell ${riskLevel}" 
                         data-likelihood="${likelihood}" 
                         data-impact="${impact}">
                        <span class="cell-label">${riskLevel.toUpperCase()}</span>
                    </div>
                `;
      });

      html += `</div>`;
    });

    html += `</div>`;

    this.elements.matrixVisualization.innerHTML = html;
  }

  /**
   * Calculate risk level for matrix cell
   */
  calculateMatrixRiskLevel(likelihoodIndex, impactIndex, size) {
    const score = likelihoodIndex + impactIndex;
    const maxScore = (size - 1) * 2;

    if (score >= maxScore * 0.7) return "high";
    if (score >= maxScore * 0.4) return "medium";
    return "low";
  }

  /**
   * Load dashboard data
   */
  async loadDashboard() {
    try {
      const [metricsResponse, dashboardResponse] = await Promise.all([this.apiCall("/api/metrics/workflow", "GET"), this.apiCall("/api/metrics/dashboard", "GET")]);

      if (metricsResponse.success) {
        this.state.metrics = metricsResponse;
        this.renderWorkflowProgress();
      }

      if (dashboardResponse.success) {
        console.log("Dashboard response successful, checking function:", typeof this.renderDashboardCharts);
        if (typeof this.renderDashboardCharts === "function") {
          this.renderDashboardCharts(dashboardResponse.dashboard);
        } else {
          console.error("renderDashboardCharts is not a function, type:", typeof this.renderDashboardCharts);
        }
      }
    } catch (error) {
      console.error("Dashboard load error:", error);
    }
  }

  /**
   * Render workflow progress
   */
  renderWorkflowProgress() {
    if (!this.state.metrics) return;

    const progress = this.state.metrics.completion_percentage;

    // Update header progress
    this.elements.progressFill.style.width = `${progress}%`;
    this.elements.progressText.textContent = `${Math.round(progress)}%`;

    // Render progress circle in dashboard
    const progressHtml = `
            <div class="progress-circle-container">
                <div class="progress-circle" style="--progress: ${progress}">
                    <span class="progress-percentage">${Math.round(progress)}%</span>
                </div>
                <div class="progress-details">
                    <p>Steps completed: ${this.state.metrics.steps_completed}/${this.state.metrics.total_steps}</p>
                </div>
            </div>
        `;

    this.elements.workflowProgress.innerHTML = progressHtml;
  }

  /**
   * Render dashboard charts
   */
  renderDashboardCharts(dashboardData) {
    console.log("Rendering dashboard charts:", dashboardData);

    // TODO: Implement dashboard charts rendering
    // For now, just log the data to prevent errors

    if (!dashboardData) {
      console.log("No dashboard data provided");
      return;
    }

    // You can implement actual chart rendering here using Chart.js or similar
    // For now, this prevents the "function not found" error
  }

  /**
   * Load initial data after authentication
   */
  async loadInitialData() {
    try {
      // Load current matrix configuration
      const matrixResponse = await this.apiCall("/api/matrix/current", "GET");
      if (matrixResponse.success) {
        this.state.matrix.size = matrixResponse.matrix_size;
        this.state.matrix.likelihoodScale = matrixResponse.likelihood_scale;
        this.state.matrix.impactScale = matrixResponse.impact_scale;
        this.elements.matrixSize.value = matrixResponse.matrix_size;
        this.renderMatrixVisualization();
      }

      // Load initial sections
      this.loadRisks();
      this.loadReports();
      this.loadDashboard();
      this.updateQuickStats();
    } catch (error) {
      console.error("Initial data load error:", error);
    }
  }

  /**
   * Update quick stats in sidebar
   */
  async updateQuickStats() {
    try {
      const [finalizedResponse, generatedResponse, reportsResponse] = await Promise.all([this.apiCall("/api/risks/view?risk_type=finalized", "GET"), this.apiCall("/api/risks/view?risk_type=generated", "GET"), this.apiCall("/api/reports/view", "GET")]);

      const finalizedCount = finalizedResponse.success ? finalizedResponse.total_count : 0;
      const generatedCount = generatedResponse.success ? generatedResponse.total_count : 0;
      const reportsCount = reportsResponse.success ? reportsResponse.reports_list?.length || 0 : 0;

      this.elements.statFinalized.textContent = finalizedCount;
      this.elements.statGenerated.textContent = generatedCount;
      this.elements.statReports.textContent = reportsCount;

      // Update navigation counts
      this.updateNavigationCounts(finalizedCount + generatedCount, reportsCount);

      // Update next step hint
      this.updateNextStepHint(finalizedCount, generatedCount, reportsCount);
    } catch (error) {
      console.error("Quick stats update error:", error);
    }
  }

  /**
   * Update navigation item counts
   */
  updateNavigationCounts(riskCount = 0, reportCount = 0) {
    const navRiskCount = document.getElementById("nav-risk-count");
    const navReportCount = document.getElementById("nav-report-count");

    if (navRiskCount) navRiskCount.textContent = riskCount;
    if (navReportCount) navReportCount.textContent = reportCount;
  }

  /**
   * Update next step hint based on progress
   */
  updateNextStepHint(finalizedCount, generatedCount, reportsCount) {
    const hintElement = document.getElementById("next-step-hint");
    if (!hintElement) return;

    let hintText = "";
    let hintIcon = "fas fa-arrow-right";

    if (finalizedCount === 0 && generatedCount === 0) {
      hintText = "Ready to start? Begin with the AI Assistant!";
      hintIcon = "fas fa-magic";
    } else if (generatedCount > 0 && finalizedCount === 0) {
      hintText = "You have generated risks! Review them in the Risk Register.";
      hintIcon = "fas fa-exclamation-triangle";
    } else if (finalizedCount > 0 && reportsCount === 0) {
      hintText = "Great! Generate your comprehensive risk report.";
      hintIcon = "fas fa-file-alt";
    } else if (reportsCount > 0) {
      hintText = "Assessment complete! View your dashboard for insights.";
      hintIcon = "fas fa-chart-line";
    }

    hintElement.innerHTML = `<i class="${hintIcon}"></i><span>${hintText}</span>`;
  }

  /**
   * Switch between sections
   */
  switchSection(sectionName) {
    // Update navigation
    this.elements.navItems.forEach((item) => {
      item.classList.toggle("active", item.dataset.section === sectionName);
    });

    // Update content sections with fade transition
    this.elements.contentSections.forEach((section) => {
      if (section.id === `${sectionName}-section`) {
        section.classList.add("active");
        // Trigger reflow to ensure transition works
        section.offsetHeight;
      } else {
        section.classList.remove("active");
      }
    });

    // Update progress steps
    this.updateProgressSteps(sectionName);

    // Load section-specific data
    switch (sectionName) {
      case "risks":
        this.loadRisks();
        break;
      case "reports":
        this.loadReports();
        break;
      case "matrix":
        this.renderMatrixVisualization();
        break;
      case "dashboard":
        this.loadDashboard();
        break;
    }

    this.state.currentSection = sectionName;
  }

  /**
   * Update progress steps in sidebar
   */
  updateProgressSteps(currentSection) {
    const steps = document.querySelectorAll(".progress-step");

    steps.forEach((step, index) => {
      step.classList.remove("active", "completed");

      if (currentSection === "chat" && index === 0) {
        step.classList.add("active");
      } else if (currentSection === "risks" && index === 1) {
        step.classList.add("active");
        if (steps[0]) steps[0].classList.add("completed");
      } else if (currentSection === "reports" && index === 2) {
        step.classList.add("active");
        if (steps[0]) steps[0].classList.add("completed");
        if (steps[1]) steps[1].classList.add("completed");
      } else if (index < this.getCurrentStepIndex(currentSection)) {
        step.classList.add("completed");
      }
    });
  }

  /**
   * Get current step index based on section
   */
  getCurrentStepIndex(section) {
    switch (section) {
      case "chat":
        return 1;
      case "risks":
      case "matrix":
        return 2;
      case "reports":
      case "dashboard":
        return 3;
      default:
        return 0;
    }
  }

  /**
   * Show/hide UI sections
   */
  showAuthContainer() {
    this.elements.authContainer.classList.remove("hidden");
    this.elements.appContainer.classList.add("hidden");
  }

  showMainApp() {
    this.elements.authContainer.classList.add("hidden");
    this.elements.appContainer.classList.remove("hidden");
  }

  hideLoadingScreen() {
    this.elements.loadingScreen.classList.add("hidden");
  }

  showLoginForm() {
    this.elements.loginForm.classList.remove("hidden");
    this.elements.registerForm.classList.add("hidden");
  }

  showRegisterForm() {
    this.elements.loginForm.classList.add("hidden");
    this.elements.registerForm.classList.remove("hidden");
  }

  /**
   * Popup management
   */
  showPopup(popupId) {
    console.log("showPopup called with popupId:", popupId);
    const popup = document.getElementById(popupId);
    console.log("Popup element found:", popup);

    if (popup) {
      console.log("Removing hidden class from popup");
      popup.classList.remove("hidden");
      this.state.currentPopup = popupId;
      console.log("Popup should now be visible");
    } else {
      console.error("Popup element not found:", popupId);
    }
  }

  hidePopup(popupId) {
    const popup = document.getElementById(popupId);
    if (popup) {
      popup.classList.add("hidden");
      if (this.state.currentPopup === popupId) {
        this.state.currentPopup = null;
      }
    }
  }

  /**
   * Notification system
   */
  showNotification(message, type = "info", duration = 5000) {
    const toast = this.elements.notificationToast;
    const icon = toast.querySelector(".notification-icon");
    const messageElement = toast.querySelector(".notification-message");

    // Set icon based on type
    const icons = {
      success: "fas fa-check-circle",
      error: "fas fa-exclamation-circle",
      warning: "fas fa-exclamation-triangle",
      info: "fas fa-info-circle",
    };

    icon.className = `notification-icon ${icons[type] || icons.info}`;
    messageElement.textContent = message;

    // Set color based on type
    toast.className = `notification-toast ${type}`;
    toast.classList.remove("hidden");

    // Add entrance animation
    toast.style.transform = "translateX(100%)";
    toast.style.opacity = "0";

    // Trigger animation
    requestAnimationFrame(() => {
      toast.style.transform = "translateX(0)";
      toast.style.opacity = "1";
    });

    // Auto-hide after specified duration
    if (duration > 0) {
      setTimeout(() => {
        this.hideNotification();
      }, duration);
    }
  }

  hideNotification() {
    const toast = this.elements.notificationToast;

    // Add exit animation
    toast.style.transform = "translateX(100%)";
    toast.style.opacity = "0";

    setTimeout(() => {
      toast.classList.add("hidden");
      toast.style.transform = "";
      toast.style.opacity = "";
    }, 300);
  }

  /**
   * Update connection status indicator
   */
  updateConnectionStatus(connected) {
    const statusIcon = this.elements.connectionStatus.querySelector("i");
    const statusText = this.elements.connectionStatus.childNodes[1];

    if (connected) {
      statusIcon.style.color = "#10b981"; // green
      statusText.textContent = " Connected";
    } else {
      statusIcon.style.color = "#ef4444"; // red
      statusText.textContent = " Disconnected";
    }
  }

  /**
   * API call helper
   */
  async apiCall(endpoint, method = "GET", data = null, token = null) {
    console.log("apiCall called:", { endpoint, method, hasData: !!data, hasToken: !!token });

    // Don't check token expiration for auth endpoints
    const isAuthEndpoint = endpoint.includes("/api/auth/");
    console.log("Is auth endpoint:", isAuthEndpoint);

    // Check if token is expired before making API calls (skip for auth)
    if (!isAuthEndpoint && !token && this.isTokenExpired()) {
      console.log("Token expired, forcing logout");
      this.showNotification("Session expired. Please log in again.", "warning");
      this.handleLogout();
      throw new Error("Token expired");
    }

    const url = `${this.config.apiBaseUrl}${endpoint}`;
    console.log("Making request to URL:", url);

    const headers = {
      "Content-Type": "application/json",
    };

    // Add authorization header
    const authToken = token || this.state.token;
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
      console.log("Adding auth header");
    }

    const options = {
      method,
      headers,
    };

    if (data && (method === "POST" || method === "PUT")) {
      options.body = JSON.stringify(data);
      console.log("Request body:", options.body);
    }

    console.log("Fetch options:", options);

    try {
      const response = await fetch(url, options);
      console.log("Response received:", response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.log("Error response body:", errorText);

        if (response.status === 401) {
          // Token expired, redirect to login
          this.handleLogout();
          throw new Error("Authentication required");
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const jsonResponse = await response.json();
      console.log("JSON response:", jsonResponse);
      return jsonResponse;
    } catch (error) {
      console.error("Fetch error:", error);
      throw error;
    }
  }

  /**
   * Utility methods for specific actions
   */
  async filterRisks() {
    this.loadRisks();
  }

  async editRisk(riskId) {
    // Implementation for editing individual risks
    console.log("Edit risk:", riskId);
  }

  async deleteRisk(riskId) {
    if (confirm("Are you sure you want to delete this risk?")) {
      try {
        const response = await this.apiCall(`/api/risks/delete/${riskId}`, "DELETE");
        if (response.success) {
          this.showNotification("Risk deleted successfully", "success");
          this.loadRisks();
        }
      } catch (error) {
        this.showNotification("Failed to delete risk", "error");
      }
    }
  }

  async viewReport(reportId) {
    // Implementation for viewing specific reports
    console.log("View report:", reportId);
  }

  async exportReport(reportId) {
    try {
      const response = await this.apiCall("/api/reports/export", "POST", {
        format: "pdf",
        include_reports: true,
        include_risks: true,
      });

      if (response.success) {
        this.showNotification("Export started. Download will begin shortly.", "success");
      }
    } catch (error) {
      this.showNotification("Export failed", "error");
    }
  }

  /**
   * Download report as PDF
   */
  async downloadReportPDF(reportId = null) {
    try {
      this.showNotification("Generating PDF report...", "info");

      // Construct download URL
      let downloadUrl = `${this.config.apiBaseUrl}/api/reports/download-pdf`;
      if (reportId) {
        downloadUrl += `?report_id=${reportId}`;
      }

      // Create authenticated fetch request
      const response = await fetch(downloadUrl, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${this.state.token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        // Get the blob data
        const blob = await response.blob();
        
        // Extract filename from response headers or use default
        const contentDisposition = response.headers.get("content-disposition");
        let filename = "risk_report.pdf";
        if (contentDisposition) {
          const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
          if (matches && matches[1]) {
            filename = matches[1].replace(/['"]/g, "");
          }
        }

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.style.display = "none";
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up
        window.URL.revokeObjectURL(url);
        
        this.showNotification("PDF report downloaded successfully!", "success");
      } else {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error("PDF download error:", error);
      this.showNotification("Failed to download PDF report. Please try again.", "error");
    }
  }

  async generateReport() {
    this.sendChatMessage("I'm ready to generate my risk report");
  }

  previewRisk(riskId, risks) {
    const risk = risks.find((r) => r.risk_id === riskId);
    if (risk) {
      alert(`Risk Preview:\n\n${risk.description}\n\nTreatment Measures:\n${risk.treatment_measures}`);
    }
  }

  saveSettings() {
    // Implementation for saving user settings
    this.hidePopup("settings-popup");
    this.showNotification("Settings saved successfully", "success");
  }

  // Handle various WebSocket message types
  handleStageUpdate(data) {
    console.log("Stage updated:", data.stage);
    this.loadDashboard(); // Refresh dashboard data
  }

  handleChatComplete(data) {
    console.log("Chat completion received:", data);
    this.hideTypingIndicator();

    // Check if there's a final message to display
    if (data.final_message) {
      console.log("Displaying final message from chat complete:", data.final_message);
      this.addChatMessage(data.final_message, "assistant");
    } else {
      console.log("No final message in chat completion data");
    }
  }

  handleWebSocketError(data) {
    console.error("WebSocket error:", data);
    this.showNotification(data.error || "WebSocket error occurred", "error");
  }
}

// Initialize the application when the page loads
let app;

document.addEventListener("DOMContentLoaded", () => {
  app = new RiskManagementApp();
});

// Make app globally accessible for inline event handlers
window.app = app;
