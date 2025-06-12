// Money Manager App JavaScript

class MoneyManager {
    constructor() {
        this.currentUser = null;
        this.categories = [];
        this.transactions = [];
        this.currentEditingTransaction = null;
        
        this.init();
    }

    async init() {
        // Show loading screen
        this.showLoading();
        
        // Check if user is already authenticated
        await this.checkAuth();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Hide loading screen
        this.hideLoading();
    }

    showLoading() {
        document.getElementById('loading-screen').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-screen').classList.add('hidden');
    }

    async checkAuth() {
        try {
            const response = await fetch('/api/auth/check');
            const data = await response.json();
            
            if (data.authenticated) {
                this.currentUser = data.user;
                await this.showMainApp();
            } else {
                this.showAuthSection();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.showAuthSection();
        }
    }

    showAuthSection() {
        document.getElementById('auth-section').classList.remove('hidden');
        document.getElementById('main-app').classList.add('hidden');
    }

    async showMainApp() {
        document.getElementById('auth-section').classList.add('hidden');
        document.getElementById('main-app').classList.remove('hidden');
        
        // Update user name in nav
        document.getElementById('user-name').textContent = this.currentUser.username;
        
        // Load initial data
        await this.loadCategories();
        await this.loadDashboardData();
        
        // Show dashboard by default
        this.showSection('dashboard');
    }

    setupEventListeners() {
        // Auth form toggles
        document.getElementById('show-signup').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAuthForms('signup');
        });

        document.getElementById('show-login').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAuthForms('login');
        });

        // Auth form submissions
        document.getElementById('login-form-element').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        document.getElementById('signup-form-element').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSignup();
        });

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const section = item.dataset.section;
                this.showSection(section);
            });
        });

        // Quick actions
        document.getElementById('quick-add-income').addEventListener('click', () => {
            this.openTransactionModal('income');
        });

        document.getElementById('quick-add-expense').addEventListener('click', () => {
            this.openTransactionModal('expense');
        });

        document.getElementById('add-transaction-btn').addEventListener('click', () => {
            this.openTransactionModal();
        });

        document.getElementById('view-all-transactions').addEventListener('click', () => {
            this.showSection('transactions');
        });

        // Modal controls
        document.getElementById('close-modal').addEventListener('click', () => {
            this.closeTransactionModal();
        });

        document.getElementById('cancel-transaction').addEventListener('click', () => {
            this.closeTransactionModal();
        });

        document.getElementById('transaction-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleTransactionSubmit();
        });

        // Filters
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });

        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });

        // Close modal when clicking outside
        document.getElementById('transaction-modal').addEventListener('click', (e) => {
            if (e.target.id === 'transaction-modal') {
                this.closeTransactionModal();
            }
        });

        // Update modal categories when transaction type changes
        document.getElementById('transaction-type').addEventListener('change', () => {
            this.updateModalCategories();
        });
    }

    toggleAuthForms(form) {
        const loginForm = document.getElementById('login-form');
        const signupForm = document.getElementById('signup-form');

        if (form === 'signup') {
            loginForm.classList.add('hidden');
            signupForm.classList.remove('hidden');
        } else {
            signupForm.classList.add('hidden');
            loginForm.classList.remove('hidden');
        }
    }

    async handleLogin() {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (response.ok) {
                this.currentUser = data.user;
                this.showMessage('Login successful!', 'success');
                await this.showMainApp();
            } else {
                this.showMessage(data.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Login failed. Please try again.', 'error');
        }
    }

    async handleSignup() {
        const username = document.getElementById('signup-username').value;
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;

        try {
            const response = await fetch('/api/auth/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, email, password }),
            });

            const data = await response.json();

            if (response.ok) {
                this.currentUser = data.user;
                this.showMessage('Account created successfully!', 'success');
                await this.showMainApp();
            } else {
                this.showMessage(data.error || 'Signup failed', 'error');
            }
        } catch (error) {
            console.error('Signup error:', error);
            this.showMessage('Signup failed. Please try again.', 'error');
        }
    }

    async handleLogout() {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            this.currentUser = null;
            this.showMessage('Logged out successfully', 'success');
            this.showAuthSection();
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        // Show section
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`${sectionName}-section`).classList.add('active');

        // Load section-specific data
        if (sectionName === 'transactions') {
            this.loadTransactions();
        } else if (sectionName === 'reports') {
            this.loadReports();
        }
    }

    async loadCategories() {
        try {
            const response = await fetch('/api/categories');
            const categories = await response.json();
            this.categories = categories;
            this.populateCategorySelects();
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    }

    populateCategorySelects() {
        const selects = [
            document.getElementById('transaction-category'),
            document.getElementById('filter-category')
        ];

        selects.forEach(select => {
            // Clear existing options (except first one)
            while (select.children.length > 1) {
                select.removeChild(select.lastChild);
            }

            // Add category options
            this.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                select.appendChild(option);
            });
        });
    }

    async loadDashboardData() {
        try {
            const response = await fetch('/api/dashboard');
            const data = await response.json();

            // Update balance cards
            document.getElementById('current-balance').textContent = this.formatCurrency(data.balance);
            document.getElementById('total-income').textContent = this.formatCurrency(data.total_income);
            document.getElementById('total-expense').textContent = this.formatCurrency(data.total_expense);

            // Update recent transactions
            this.displayRecentTransactions(data.recent_transactions);

            // Update spending chart
            this.updateSpendingChart(data.category_spending);

        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showMessage('Failed to load dashboard data', 'error');
        }
    }

    displayRecentTransactions(transactions) {
        const container = document.getElementById('recent-transactions-list');
        
        if (transactions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-receipt"></i>
                    <h3>No transactions yet</h3>
                    <p>Start by adding your first transaction</p>
                </div>
            `;
            return;
        }

        container.innerHTML = transactions.map(transaction => `
            <div class="transaction-item ${transaction.transaction_type}">
                <div class="transaction-info">
                    <div class="transaction-icon">
                        <i class="fas fa-${transaction.transaction_type === 'income' ? 'arrow-up' : 'arrow-down'}"></i>
                    </div>
                    <div class="transaction-details">
                        <h4>${transaction.description || 'No description'}</h4>
                        <p>${transaction.category_name || 'No category'}</p>
                    </div>
                </div>
                <div class="transaction-amount">
                    <div class="amount">${transaction.transaction_type === 'income' ? '+' : '-'}${this.formatCurrency(transaction.amount)}</div>
                    <div class="date">${this.formatDate(transaction.date)}</div>
                </div>
            </div>
        `).join('');
    }

    async loadTransactions() {
        try {
            const response = await fetch('/api/transactions');
            const transactions = await response.json();
            this.transactions = transactions;
            this.displayTransactions(transactions);
        } catch (error) {
            console.error('Failed to load transactions:', error);
            this.showMessage('Failed to load transactions', 'error');
        }
    }

    displayTransactions(transactions) {
        const container = document.getElementById('transactions-list');
        
        if (transactions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-receipt"></i>
                    <h3>No transactions found</h3>
                    <p>Add some transactions to see them here</p>
                </div>
            `;
            return;
        }

        container.innerHTML = transactions.map(transaction => `
            <div class="transaction-item ${transaction.transaction_type}">
                <div class="transaction-info">
                    <div class="transaction-icon">
                        <i class="fas fa-${transaction.transaction_type === 'income' ? 'arrow-up' : 'arrow-down'}"></i>
                    </div>
                    <div class="transaction-details">
                        <h4>${transaction.description || 'No description'}</h4>
                        <p>${transaction.category_name || 'No category'} • ${this.formatDate(transaction.date)}</p>
                    </div>
                </div>
                <div class="transaction-amount">
                    <div class="amount">${transaction.transaction_type === 'income' ? '+' : '-'}${this.formatCurrency(transaction.amount)}</div>
                </div>
                <div class="transaction-actions">
                    <button class="action-btn-small" onclick="app.editTransaction(${transaction.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn-small" onclick="app.deleteTransaction(${transaction.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    openTransactionModal(type = '') {
        this.currentEditingTransaction = null;
        document.getElementById('modal-title').textContent = 'Add Transaction';
        document.getElementById('transaction-form').reset();
        
        if (type) {
            document.getElementById('transaction-type').value = type;
        }
        
        // Set today's date as default
        document.getElementById('transaction-date').value = new Date().toISOString().split('T')[0];
        this.updateModalCategories(); // Update categories based on default/selected type
        
        document.getElementById('transaction-modal').classList.remove('hidden');
    }

    closeTransactionModal() {
        document.getElementById('transaction-modal').classList.add('hidden');
        this.currentEditingTransaction = null;
    }

    updateModalCategories() {
        const transactionTypeSelect = document.getElementById('transaction-type');
        const categorySelect = document.getElementById('transaction-category');
        const selectedType = transactionTypeSelect.value;

        const currentCategoryId = categorySelect.value;

        // Clear existing options (except the first "Select Category" option)
        while (categorySelect.children.length > 1) {
            categorySelect.removeChild(categorySelect.lastChild);
        }

        let categoriesToShow = [];
        const incomeCategoryNames = ['Salary'];
        const generalCategoryNames = ['Other'];

        if (selectedType === 'income') {
            categoriesToShow = this.categories.filter(cat => 
                incomeCategoryNames.includes(cat.name) || generalCategoryNames.includes(cat.name)
            );
        } else if (selectedType === 'expense') {
            categoriesToShow = this.categories.filter(cat => 
                !incomeCategoryNames.includes(cat.name)
            );
        } else {
            // If no type or an unknown type is selected, show all categories
            categoriesToShow = [...this.categories];
        }

        categoriesToShow.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            categorySelect.appendChild(option);
        });

        // Try to re-select the previously selected category if it's still in the list
        if (categoriesToShow.some(cat => cat.id.toString() === currentCategoryId)) {
            categorySelect.value = currentCategoryId;
        } else {
            categorySelect.value = ""; // Default to "Select Category"
        }
    }

    async handleTransactionSubmit() {
        const formData = {
            amount: parseFloat(document.getElementById('transaction-amount').value),
            transaction_type: document.getElementById('transaction-type').value,
            category_id: document.getElementById('transaction-category').value || null,
            date: document.getElementById('transaction-date').value,
            description: document.getElementById('transaction-description').value
        };

        try {
            let response;
            if (this.currentEditingTransaction) {
                response = await fetch(`/api/transactions/${this.currentEditingTransaction}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            } else {
                response = await fetch('/api/transactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            }

            const data = await response.json();

            if (response.ok) {
                this.showMessage(
                    this.currentEditingTransaction ? 'Transaction updated!' : 'Transaction added!', 
                    'success'
                );
                this.closeTransactionModal();
                await this.loadDashboardData();
                if (document.getElementById('transactions-section').classList.contains('active')) {
                    await this.loadTransactions();
                }
            } else {
                this.showMessage(data.error || 'Failed to save transaction', 'error');
            }
        } catch (error) {
            console.error('Transaction submit error:', error);
            this.showMessage('Failed to save transaction', 'error');
        }
    }

    async editTransaction(id) {
        try {
            const response = await fetch(`/api/transactions/${id}`);
            const transaction = await response.json();

            if (response.ok) {
                this.currentEditingTransaction = id;
                document.getElementById('modal-title').textContent = 'Edit Transaction';
                
                // Populate form
                document.getElementById('transaction-amount').value = transaction.amount;
                document.getElementById('transaction-type').value = transaction.transaction_type;
                document.getElementById('transaction-category').value = transaction.category_id || '';
                document.getElementById('transaction-date').value = transaction.date;
                document.getElementById('transaction-description').value = transaction.description || '';
                
                this.updateModalCategories(); // Ensure category dropdown is correctly filtered
                document.getElementById('transaction-modal').classList.remove('hidden');
            } else {
                this.showMessage('Failed to load transaction', 'error');
            }
        } catch (error) {
            console.error('Edit transaction error:', error);
            this.showMessage('Failed to load transaction', 'error');
        }
    }

    async deleteTransaction(id) {
        if (!confirm('Are you sure you want to delete this transaction?')) {
            return;
        }

        try {
            const response = await fetch(`/api/transactions/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showMessage('Transaction deleted!', 'success');
                await this.loadDashboardData();
                if (document.getElementById('transactions-section').classList.contains('active')) {
                    await this.loadTransactions();
                }
            } else {
                this.showMessage('Failed to delete transaction', 'error');
            }
        } catch (error) {
            console.error('Delete transaction error:', error);
            this.showMessage('Failed to delete transaction', 'error');
        }
    }

    async applyFilters() {
        const filters = {
            type: document.getElementById('filter-type').value,
            category_id: document.getElementById('filter-category').value,
            start_date: document.getElementById('filter-start-date').value,
            end_date: document.getElementById('filter-end-date').value
        };

        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });

        try {
            const response = await fetch(`/api/transactions?${params}`);
            const transactions = await response.json();
            this.displayTransactions(transactions);
        } catch (error) {
            console.error('Filter error:', error);
            this.showMessage('Failed to apply filters', 'error');
        }
    }

    clearFilters() {
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-category').value = '';
        document.getElementById('filter-start-date').value = '';
        document.getElementById('filter-end-date').value = '';
        this.loadTransactions();
    }

    updateSpendingChart(categorySpending) {
        const canvas = document.getElementById('spending-chart');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (categorySpending.length === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No spending data available', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Simple bar chart
        const maxAmount = Math.max(...categorySpending.map(item => item.amount));
        const barWidth = canvas.width / categorySpending.length - 20;
        const barMaxHeight = canvas.height - 60;

        categorySpending.forEach((item, index) => {
            const barHeight = (item.amount / maxAmount) * barMaxHeight;
            const x = index * (barWidth + 20) + 10;
            const y = canvas.height - barHeight - 30;

            // Draw bar
            ctx.fillStyle = `hsl(${index * 60}, 70%, 60%)`;
            ctx.fillRect(x, y, barWidth, barHeight);

            // Draw label
            ctx.fillStyle = '#333';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(item.category, x + barWidth / 2, canvas.height - 10);
            
            // Draw amount
            ctx.fillText(this.formatCurrency(item.amount), x + barWidth / 2, y - 5);
        });
    }

    async loadReports() {
        // This would load more detailed analytics
        // For now, we'll just update the charts with existing data
        await this.loadDashboardData();
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', { // Changed from en-US
            style: 'currency',
            currency: 'INR' // Changed from USD
        }).format(amount || 0); // Added fallback for amount
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    showMessage(message, type = 'success') {
        const container = document.getElementById('message-container');
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        messageEl.textContent = message;
        
        container.appendChild(messageEl);
        
        // Remove message after 5 seconds
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 5000);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MoneyManager();
});
