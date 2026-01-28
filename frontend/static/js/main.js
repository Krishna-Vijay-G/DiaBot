/**
 * DiaBot - Main JavaScript
 * AI-Powered Diabetes Screening Platform
 */

// ===== Theme Management =====
const ThemeManager = {
    STORAGE_KEY: 'diabot-theme',
    
    init() {
        const savedTheme = localStorage.getItem(this.STORAGE_KEY);
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        this.setTheme(theme);
        this.bindEvents();
    },
    
    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(this.STORAGE_KEY, theme);
        this.updateToggleIcon(theme);
    },
    
    toggle() {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        this.setTheme(next);
    },
    
    updateToggleIcon(theme) {
        const toggle = document.getElementById('theme-toggle') || document.getElementById('themeToggle');
        if (toggle) {
            const icon = toggle.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        }
    },
    
    bindEvents() {
        const toggle = document.getElementById('theme-toggle') || document.getElementById('themeToggle');
        if (toggle) {
            toggle.addEventListener('click', () => this.toggle());
        }
    }
};

// ===== Navigation =====
const Navigation = {
    init() {
        this.bindMobileToggle();
        this.bindDropdowns();
        this.handleScroll();
        this.setActiveLink();
    },
    
    bindMobileToggle() {
        const toggle = document.getElementById('nav-toggle') || document.getElementById('navToggle');
        const menu = document.getElementById('nav-menu') || document.getElementById('navMenu');
        
        if (toggle && menu) {
            toggle.addEventListener('click', () => {
                menu.classList.toggle('active');
                toggle.classList.toggle('active');
            });
            
            // Close on outside click
            document.addEventListener('click', (e) => {
                if (!toggle.contains(e.target) && !menu.contains(e.target)) {
                    menu.classList.remove('active');
                    toggle.classList.remove('active');
                }
            });
        }
    },
    
    bindDropdowns() {
        const dropdowns = document.querySelectorAll('.nav-dropdown');
        
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('click', (e) => {
                if (window.innerWidth <= 768) {
                    e.preventDefault();
                    dropdown.classList.toggle('active');
                }
            });
        });
    },
    
    handleScroll() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;
        
        let lastScroll = 0;
        
        window.addEventListener('scroll', () => {
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > 100) {
                navbar.style.boxShadow = 'var(--shadow-md)';
            } else {
                navbar.style.boxShadow = 'none';
            }
            
            lastScroll = currentScroll;
        });
    },
    
    setActiveLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPath || (currentPath === '/' && href === '/')) {
                link.classList.add('active');
            }
        });
    }
};

// ===== Flash Messages =====
const FlashMessages = {
    init() {
        const container = document.getElementById('flashContainer');
        if (!container) return;
        
        const messages = container.querySelectorAll('.flash-message');
        messages.forEach(msg => {
            // Auto dismiss after 5 seconds
            setTimeout(() => this.dismiss(msg), 5000);
            
            // Bind close button
            const closeBtn = msg.querySelector('.flash-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.dismiss(msg));
            }
        });
    },
    
    dismiss(element) {
        element.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => element.remove(), 300);
    },
    
    show(message, type = 'info') {
        const container = document.getElementById('flashContainer');
        if (!container) return;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        const flash = document.createElement('div');
        flash.className = `flash-message flash-${type}`;
        flash.innerHTML = `
            <i class="${icons[type]}"></i>
            <span>${message}</span>
            <button class="flash-close"><i class="fas fa-times"></i></button>
        `;
        
        container.appendChild(flash);
        
        const closeBtn = flash.querySelector('.flash-close');
        closeBtn.addEventListener('click', () => this.dismiss(flash));
        
        setTimeout(() => this.dismiss(flash), 5000);
    }
};

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(style);

// ===== Form Handling =====
const FormHandler = {
    init() {
        this.bindForms();
        this.bindToggleSwitches();
    },
    
    bindForms() {
        const forms = document.querySelectorAll('form[data-ajax]');
        
        forms.forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.submitForm(form);
            });
        });
    },
    
    bindToggleSwitches() {
        const toggleItems = document.querySelectorAll('.toggle-item');
        
        toggleItems.forEach(item => {
            const label = item.querySelector('.toggle-label');
            const input = item.querySelector('input');
            const toggle = item.querySelector('.toggle-switch');
            
            if (label && input && toggle) {
                [label, toggle].forEach(el => {
                    el.addEventListener('click', () => {
                        input.checked = !input.checked;
                        input.dispatchEvent(new Event('change'));
                    });
                });
            }
        });
    },
    
    async submitForm(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.innerHTML : '';
        
        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner"></span> Processing...';
            }
            
            const formData = new FormData(form);
            const action = form.getAttribute('action') || window.location.href;
            const method = form.getAttribute('method') || 'POST';
            
            const response = await fetch(action, {
                method: method,
                body: formData
            });
            
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                FlashMessages.show(data.message || 'Success!', 'success');
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                FlashMessages.show(data.message || 'An error occurred', 'error');
            }
        } catch (error) {
            console.error('Form submission error:', error);
            FlashMessages.show('An error occurred. Please try again.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        }
    },
    
    validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                this.showError(input, 'This field is required');
            } else {
                this.clearError(input);
            }
        });
        
        return isValid;
    },
    
    showError(input, message) {
        input.classList.add('error');
        let errorEl = input.parentNode.querySelector('.form-error');
        
        if (!errorEl) {
            errorEl = document.createElement('span');
            errorEl.className = 'form-error';
            input.parentNode.appendChild(errorEl);
        }
        
        errorEl.textContent = message;
    },
    
    clearError(input) {
        input.classList.remove('error');
        const errorEl = input.parentNode.querySelector('.form-error');
        if (errorEl) errorEl.remove();
    }
};

// ===== Chatbot =====
const Chatbot = {
    conversationId: null,
    
    init() {
        const chatForm = document.getElementById('chatForm');
        const chatInput = document.getElementById('chatInput');
        
        if (!chatForm || !chatInput) return;
        
        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
        });
        
        // Submit function
        const submitChat = async () => {
            const message = chatInput.value.trim();
            if (!message) return;
            await this.sendMessage(message);
            chatInput.value = '';
            chatInput.style.height = 'auto';
        };
        
        // Submit on Enter (but allow Shift+Enter for new lines)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitChat();
            }
        });
        
        // Form submission
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitChat();
        });
        
        // Get conversation ID from URL or data attribute
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            this.conversationId = chatContainer.dataset.conversationId;
        }
        
        // Scroll to bottom
        this.scrollToBottom();
    },
    
    async sendMessage(message) {
        if (!message) return;
        
        const messagesContainer = document.getElementById('chatMessages');
        const sendBtn = document.getElementById('chatSendBtn');
        
        // Add user message
        this.appendMessage(message, 'user');
        
        // Disable send button
        if (sendBtn) {
            sendBtn.disabled = true;
        }
        
        // Show typing indicator
        const typingId = this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/v1/chatbot/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_id: this.conversationId,
                    message: message
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);
            
            if (data.success) {
                this.appendMessage(data.response, 'assistant');
                if (!this.conversationId) {
                    // Redirect to the new conversation page
                    window.location.href = `/chatbot/conversation/${data.conversation_id}`;
                }
            } else {
                FlashMessages.show(data.message || 'Failed to get response', 'error');
            }
        } catch (error) {
            this.removeTypingIndicator(typingId);
            FlashMessages.show('Connection error. Please try again.', 'error');
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
            }
        }
    },
    
    appendMessage(content, role) {
        const container = document.getElementById('chatMessages');
        if (!container) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${role}`;
        
        const avatar = role === 'assistant' 
            ? '<i class="fas fa-robot"></i>' 
            : '<i class="fas fa-user"></i>';
        
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageEl.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-bubble">
                <div class="message-content">${this.formatMessage(content)}</div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        container.appendChild(messageEl);
        this.scrollToBottom();
    },
    
    formatMessage(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    },

    // Simple HTML escaper to prevent injection when inserting conversation titles
    escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
    
    showTypingIndicator() {
        const container = document.getElementById('chatMessages');
        if (!container) return null;
        
        const id = 'typing-' + Date.now();
        const typingEl = document.createElement('div');
        typingEl.id = id;
        typingEl.className = 'chat-message assistant typing';
        typingEl.innerHTML = `
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        
        container.appendChild(typingEl);
        this.scrollToBottom();
        
        return id;
    },
    
    removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    },
    
    scrollToBottom() {
        const container = document.getElementById('chatMessages');
        if (container) {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'smooth'
            });
        }
    }
    ,

    updateSidebar(conversations) {
        const list = document.querySelector('.chat-conversations');
        if (!list) return;

        // Build conversation items HTML and replace list contents
        const html = conversations.map(conv => {
            const title = (conv.title && conv.title.length) ? conv.title : 'New Conversation';
            const time = conv.created_at_dt ? (new Date(conv.created_at_dt)).toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : (conv.created_at || '');
            return `
                <div class="chat-conversation-item" onclick="window.location.href='/chatbot/conversation/${conv.id}'">
                    <div class="chat-conversation-icon"><i class="fas fa-message"></i></div>
                    <div class="chat-conversation-info">
                        <div class="chat-conversation-title">${this.escapeHtml(title)}</div>
                        <div class="chat-conversation-time">${this.escapeHtml(time)}</div>
                    </div>
                </div>`;
        }).join('');

        list.innerHTML = html;
    }
};

// Add typing indicator styles
const typingStyle = document.createElement('style');
typingStyle.textContent = `
    .typing-indicator {
        display: flex;
        gap: 4px;
        padding: 0.5rem 0;
    }
    
    .typing-indicator span {
        width: 8px;
        height: 8px;
        background: var(--gray-400);
        border-radius: 50%;
        animation: typingBounce 1.4s ease-in-out infinite;
    }
    
    .typing-indicator span:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-indicator span:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typingBounce {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-8px); }
    }
`;
document.head.appendChild(typingStyle);

// ===== Animations =====
const Animations = {
    init() {
        this.observeElements();
    },
    
    observeElements() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
        
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });
    }
};

// Add animation styles
const animStyle = document.createElement('style');
animStyle.textContent = `
    .animate-on-scroll {
        opacity: 0;
        transform: translateY(30px);
        transition: opacity 0.6s ease, transform 0.6s ease;
    }
    
    .animate-on-scroll.animate-in {
        opacity: 1;
        transform: translateY(0);
    }
`;
document.head.appendChild(animStyle);

// ===== Counter Animation =====
const CounterAnimation = {
    init() {
        const counters = document.querySelectorAll('[data-counter]');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        counters.forEach(counter => observer.observe(counter));
    },
    
    animateCounter(element) {
        const target = parseInt(element.dataset.counter);
        const duration = 2000;
        const start = performance.now();
        const suffix = element.dataset.suffix || '';
        const prefix = element.dataset.prefix || '';
        
        const update = (currentTime) => {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(easeOut * target);
            
            element.textContent = prefix + current.toLocaleString() + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        
        requestAnimationFrame(update);
    }
};

// ===== Smooth Scroll =====
const SmoothScroll = {
    init() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const href = anchor.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
};

// ===== Progress Bar (for results page) =====
const ProgressBar = {
    init() {
        const progressBars = document.querySelectorAll('.confidence-fill');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const width = entry.target.dataset.width || '0';
                    entry.target.style.width = width + '%';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        progressBars.forEach(bar => {
            bar.style.width = '0%';
            observer.observe(bar);
        });
    }
};

// ===== Utility Functions =====
const Utils = {
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    },
    
    formatPercentage(value, decimals = 1) {
        return (value * 100).toFixed(decimals) + '%';
    }
};

// ===== Diabetes Form Handler =====
const DiabetesForm = {
    init() {
        const form = document.getElementById('diabetesForm');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit(form);
        });
    },
    
    async handleSubmit(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Analyzing...';
            
            const formData = new FormData(form);
            
            const response = await fetch('/diabetes', {
                method: 'POST',
                body: formData
            });
            
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            const data = await response.json();
            
            if (data.error) {
                FlashMessages.show(data.error, 'error');
            } else if (data.redirect) {
                window.location.href = data.redirect;
            }
        } catch (error) {
            console.error('Submission error:', error);
            FlashMessages.show('An error occurred. Please try again.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
};

// ===== Initialize Everything =====
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    Navigation.init();
    FlashMessages.init();
    FormHandler.init();
    Chatbot.init();
    Animations.init();
    CounterAnimation.init();
    SmoothScroll.init();
    ProgressBar.init();
    DiabetesForm.init();
});

// Export for use in other scripts
window.DiaBot = {
    ThemeManager,
    Navigation,
    FlashMessages,
    FormHandler,
    Chatbot,
    Utils
};
