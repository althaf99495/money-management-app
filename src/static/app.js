// Money Manager App JavaScript

class MoneyManager {
    constructor() {
        this.currentUser = null;
        this.categories = [];
        this.transactions = [];
        this.currentEditingTransaction = null;
        this.currentEditingBudget = null;
        this.currentEditingRecurring = null; // Added for recurring transactions
        
        this.init();
    }

    async init() {
        this.showLoading();
        await this.checkAuth();
        this.setupEventListeners();
        this.hideLoading();
    }

    showLoading() { document.getElementById('loading-screen').classList.remove('hidden'); }
    hideLoading() { document.getElementById('loading-screen').classList.add('hidden'); }

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
        document.getElementById('user-name').textContent = this.currentUser.username;
        
        await this.loadCategories();
        await this.loadDashboardData();
        
        this.showSection('dashboard');
    }

    setupEventListeners() {
        document.getElementById('show-signup').addEventListener('click', (e) => { e.preventDefault(); this.toggleAuthForms('signup'); });
        document.getElementById('show-login').addEventListener('click', (e) => { e.preventDefault(); this.toggleAuthForms('login'); });
        document.getElementById('login-form-element').addEventListener('submit', (e) => { e.preventDefault(); this.handleLogin(); });
        document.getElementById('signup-form-element').addEventListener('submit', (e) => { e.preventDefault(); this.handleSignup(); });
        document.getElementById('logout-btn').addEventListener('click', () => this.handleLogout());

        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => this.showSection(item.dataset.section));
        });

        // Quick actions & Add buttons
        document.getElementById('quick-add-income').addEventListener('click', () => this.openTransactionModal('income'));
        document.getElementById('quick-add-expense').addEventListener('click', () => this.openTransactionModal('expense'));
        document.getElementById('add-transaction-btn').addEventListener('click', () => this.openTransactionModal());
        document.getElementById('add-budget-btn').addEventListener('click', () => this.openBudgetModal());
        document.getElementById('add-recurring-btn').addEventListener('click', () => this.openRecurringModal()); // ADDED
        document.getElementById('view-all-transactions').addEventListener('click', () => this.showSection('transactions'));

        // Modal close/cancel buttons
        ['close-modal', 'cancel-transaction'].forEach(id => document.getElementById(id).addEventListener('click', () => this.closeTransactionModal()));
        ['close-budget-modal', 'cancel-budget'].forEach(id => document.getElementById(id).addEventListener('click', () => this.closeBudgetModal()));
        ['close-recurring-modal', 'cancel-recurring'].forEach(id => document.getElementById(id).addEventListener('click', () => this.closeRecurringModal())); // ADDED

        // Form submissions
        document.getElementById('transaction-form').addEventListener('submit', (e) => { e.preventDefault(); this.handleTransactionSubmit(); });
        document.getElementById('budget-form').addEventListener('submit', (e) => { e.preventDefault(); this.handleBudgetSubmit(); });
        document.getElementById('recurring-form').addEventListener('submit', (e) => { e.preventDefault(); this.handleRecurringSubmit(); }); // ADDED

        // Filters
        document.getElementById('apply-filters').addEventListener('click', () => this.applyFilters());
        document.getElementById('clear-filters').addEventListener('click', () => this.clearFilters());
        document.getElementById('apply-budget-filters').addEventListener('click', () => this.loadBudgets());
        document.getElementById('apply-recurring-filters').addEventListener('click', () => this.loadRecurringTransactions()); // ADDED

        // Modal outside click
        document.getElementById('transaction-modal').addEventListener('click', (e) => { if (e.target.id === 'transaction-modal') this.closeTransactionModal(); });
        document.getElementById('budget-modal').addEventListener('click', (e) => { if (e.target.id === 'budget-modal') this.closeBudgetModal(); });
        document.getElementById('recurring-modal').addEventListener('click', (e) => { if (e.target.id === 'recurring-modal') this.closeRecurringModal(); }); // ADDED

        document.getElementById('transaction-type').addEventListener('change', () => this.updateModalCategories());
    }

    toggleAuthForms(form) {
        document.getElementById('login-form').classList.toggle('hidden', form === 'signup');
        document.getElementById('signup-form').classList.toggle('hidden', form !== 'signup');
    }

    async handleApiAuth(endpoint, body) {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await response.json();
            if (response.ok) {
                this.currentUser = data.user;
                this.showMessage(data.message || 'Success!', 'success');
                await this.showMainApp();
            } else {
                this.showMessage(data.error || 'Operation failed', 'error');
            }
        } catch (error) {
            console.error('Auth error:', error);
            this.showMessage('An error occurred. Please try again.', 'error');
        }
    }

    handleLogin() {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        this.handleApiAuth('/api/auth/login', { username, password });
    }

    handleSignup() {
        const username = document.getElementById('signup-username').value;
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;
        this.handleApiAuth('/api/auth/signup', { username, email, password });
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
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.section === sectionName);
        });
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.toggle('active', section.id === `${sectionName}-section`);
        });

        if (sectionName === 'transactions') this.loadTransactions();
        else if (sectionName === 'reports') this.loadReports();
        else if (sectionName === 'budgets') this.loadBudgets();
        else if (sectionName === 'recurring') this.loadRecurringTransactions(); // ADDED
    }

    async loadCategories() {
        try {
            const response = await fetch('/api/categories');
            this.categories = await response.json();
            this.populateCategorySelects();
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    }

    populateCategorySelects() {
        const selects = document.querySelectorAll('#transaction-category, #filter-category, #budget-category, #recurring-category');
        selects.forEach(select => {
            while (select.children.length > 1) select.removeChild(select.lastChild);
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
            document.getElementById('current-balance').textContent = this.formatCurrency(data.balance);
            document.getElementById('total-income').textContent = this.formatCurrency(data.total_income);
            document.getElementById('total-expense').textContent = this.formatCurrency(data.total_expense);
            this.displayRecentTransactions(data.recent_transactions);
            this.updateSpendingChart(data.category_spending);
            this.updateCategoryChart(data.category_spending); // For reports page
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showMessage('Failed to load dashboard data', 'error');
        }
    }

    displayRecentTransactions(transactions) {
        this.renderItems('recent-transactions-list', transactions, this.renderTransactionItem, 'No recent transactions.');
    }

    async loadTransactions() {
        try {
            const response = await fetch('/api/transactions');
            this.transactions = await response.json();
            this.displayTransactions(this.transactions);
        } catch (error) {
            console.error('Failed to load transactions:', error);
        }
    }

    displayTransactions(transactions) {
        this.renderItems('transactions-list', transactions, this.renderTransactionItem, 'No transactions found.');
    }

    // Modal Management
    openTransactionModal(type = '') {
        this.currentEditingTransaction = null;
        document.getElementById('modal-title').textContent = 'Add Transaction';
        document.getElementById('transaction-form').reset();
        if (type) document.getElementById('transaction-type').value = type;
        document.getElementById('transaction-date').valueAsDate = new Date();
        this.updateModalCategories();
        document.getElementById('transaction-modal').classList.remove('hidden');
    }

    closeTransactionModal() {
        document.getElementById('transaction-modal').classList.add('hidden');
    }

    openBudgetModal(budget = null) {
        document.getElementById('budget-form').reset();
        this.currentEditingBudget = budget ? budget.id : null;
        document.getElementById('budget-modal-title').textContent = budget ? 'Edit Budget' : 'Add Budget';
        
        if (budget) {
            document.getElementById('budget-category').value = budget.category_id;
            document.getElementById('budget-amount').value = budget.amount;
            document.getElementById('budget-month-input').value = budget.budget_month;
        } else {
            document.getElementById('budget-month-input').value = new Date().toISOString().slice(0, 7);
        }
        document.getElementById('budget-modal').classList.remove('hidden');
    }

    closeBudgetModal() {
        document.getElementById('budget-modal').classList.add('hidden');
    }

    openRecurringModal(item = null) {
        document.getElementById('recurring-form').reset();
        this.currentEditingRecurring = item ? item.id : null;
        document.getElementById('recurring-modal-title').textContent = item ? 'Edit Recurring' : 'Add Recurring';

        if (item) {
            document.getElementById('recurring-description').value = item.description;
            document.getElementById('recurring-amount').value = item.amount;
            document.getElementById('recurring-type').value = item.transaction_type;
            document.getElementById('recurring-category').value = item.category_id || '';
            document.getElementById('recurring-frequency').value = item.frequency;
            document.getElementById('recurring-interval').value = item.interval;
            document.getElementById('recurring-start-date').value = item.start_date;
            document.getElementById('recurring-end-date').value = item.end_date || '';
        } else {
            document.getElementById('recurring-start-date').valueAsDate = new Date();
        }
        document.getElementById('recurring-modal').classList.remove('hidden');
    }

    closeRecurringModal() {
        document.getElementById('recurring-modal').classList.add('hidden');
    }


    updateModalCategories() {
        const type = document.getElementById('transaction-type').value;
        const categorySelect = document.getElementById('transaction-category');
        const currentVal = categorySelect.value;
        
        while (categorySelect.children.length > 1) categorySelect.removeChild(categorySelect.lastChild);

        const incomeCats = ['Salary'];
        let filtered = this.categories;
        if (type === 'income') {
            filtered = this.categories.filter(c => incomeCats.includes(c.name) || c.name === 'Other');
        } else if (type === 'expense') {
            filtered = this.categories.filter(c => !incomeCats.includes(c.name));
        }
        
        filtered.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            categorySelect.appendChild(opt);
        });

        if (filtered.some(c => c.id.toString() === currentVal)) {
            categorySelect.value = currentVal;
        }
    }

    // Form Submissions
    async handleTransactionSubmit() {
        const isEditing = !!this.currentEditingTransaction;
        const url = isEditing ? `/api/transactions/${this.currentEditingTransaction}` : '/api/transactions';
        const method = isEditing ? 'PUT' : 'POST';

        const body = {
            amount: parseFloat(document.getElementById('transaction-amount').value),
            transaction_type: document.getElementById('transaction-type').value,
            category_id: document.getElementById('transaction-category').value || null,
            date: document.getElementById('transaction-date').value,
            description: document.getElementById('transaction-description').value
        };

        try {
            const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            const data = await response.json();
            if (response.ok) {
                this.showMessage(data.message || 'Success!', 'success');
                this.closeTransactionModal();
                this.loadDashboardData();
                if (document.getElementById('transactions-section').classList.contains('active')) this.loadTransactions();
            } else {
                this.showMessage(data.error || 'Failed.', 'error');
            }
        } catch (error) {
            this.showMessage('Operation failed.', 'error');
        }
    }

    async handleBudgetSubmit() {
        const isEditing = !!this.currentEditingBudget;
        const url = isEditing ? `/api/budgets/${this.currentEditingBudget}` : '/api/budgets';
        const method = isEditing ? 'PUT' : 'POST';

        const body = {
            category_id: document.getElementById('budget-category').value,
            amount: parseFloat(document.getElementById('budget-amount').value),
            budget_month_str: document.getElementById('budget-month-input').value,
            period: 'monthly'
        };

        if (!body.category_id || isNaN(body.amount) || !body.budget_month_str) {
            this.showMessage('Please fill all required fields.', 'error');
            return;
        }

        try {
            const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            const data = await response.json();
            if (response.ok) {
                this.showMessage(data.message, 'success');
                this.closeBudgetModal();
                this.loadBudgets();
            } else {
                this.showMessage(data.error, 'error');
            }
        } catch (error) {
            this.showMessage('Operation failed.', 'error');
        }
    }

    async handleRecurringSubmit() {
        const isEditing = !!this.currentEditingRecurring;
        const url = isEditing ? `/api/recurring-transactions/${this.currentEditingRecurring}` : '/api/recurring-transactions';
        const method = isEditing ? 'PUT' : 'POST';

        const body = {
            description: document.getElementById('recurring-description').value,
            amount: parseFloat(document.getElementById('recurring-amount').value),
            transaction_type: document.getElementById('recurring-type').value,
            category_id: document.getElementById('recurring-category').value || null,
            frequency: document.getElementById('recurring-frequency').value,
            interval: parseInt(document.getElementById('recurring-interval').value),
            start_date_str: document.getElementById('recurring-start-date').value,
            end_date_str: document.getElementById('recurring-end-date').value || null,
        };
        
        try {
            const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            const data = await response.json();
            if (response.ok) {
                this.showMessage(data.message, 'success');
                this.closeRecurringModal();
                this.loadRecurringTransactions();
            } else {
                this.showMessage(data.error, 'error');
            }
        } catch (error) {
            this.showMessage('Operation failed.', 'error');
        }
    }

    // Edit/Delete
    async editTransaction(id) {
        try {
            const response = await fetch(`/api/transactions/${id}`);
            if (!response.ok) throw new Error('Failed to fetch transaction');
            const transaction = await response.json();
            this.currentEditingTransaction = id;
            document.getElementById('modal-title').textContent = 'Edit Transaction';
            document.getElementById('transaction-amount').value = transaction.amount;
            document.getElementById('transaction-type').value = transaction.transaction_type;
            this.updateModalCategories(); // Update categories before setting value
            document.getElementById('transaction-category').value = transaction.category_id || '';
            document.getElementById('transaction-date').value = transaction.date;
            document.getElementById('transaction-description').value = transaction.description || '';
            document.getElementById('transaction-modal').classList.remove('hidden');
        } catch (error) {
            this.showMessage('Failed to load transaction', 'error');
        }
    }

    async deleteTransaction(id) {
        if (!confirm('Are you sure?')) return;
        try {
            const response = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
            if (response.ok) {
                this.showMessage('Transaction deleted!', 'success');
                this.loadDashboardData();
                if (document.getElementById('transactions-section').classList.contains('active')) this.loadTransactions();
            } else {
                this.showMessage('Failed to delete transaction', 'error');
            }
        } catch (error) {
            this.showMessage('Failed to delete transaction', 'error');
        }
    }

    // Filtering
    async applyFilters() {
        const params = new URLSearchParams({
            type: document.getElementById('filter-type').value,
            category_id: document.getElementById('filter-category').value,
            start_date: document.getElementById('filter-start-date').value,
            end_date: document.getElementById('filter-end-date').value
        });
        const url = `/api/transactions?${params.toString().replace(/&[^=]+=&/g, '&').replace(/&[^=]+=$/, '')}`;
        try {
            const response = await fetch(url);
            this.displayTransactions(await response.json());
        } catch (error) {
            console.error('Filter error:', error);
        }
    }

    clearFilters() {
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-category').value = '';
        document.getElementById('filter-start-date').value = '';
        document.getElementById('filter-end-date').value = '';
        this.loadTransactions();
    }

    // Budgets
    async loadBudgets() {
        let monthFilter = document.getElementById('filter-budget-month').value;
        if (!monthFilter) {
            monthFilter = new Date().toISOString().slice(0, 7);
            document.getElementById('filter-budget-month').value = monthFilter;
        }
        try {
            const response = await fetch(`/api/budgets/summary?month_year=${monthFilter}`);
            const summary = await response.json();
            this.displayBudgets(summary);
        } catch (error) {
            console.error('Failed to load budgets:', error);
        }
    }
    
    displayBudgets(budgets) {
        this.renderItems('budgets-list', budgets, this.renderBudgetItem, 'No budgets for this period.');
        document.querySelectorAll('.edit-budget-btn').forEach(btn => 
            btn.addEventListener('click', (e) => this.editBudget(e.currentTarget.dataset.id, budgets)));
        document.querySelectorAll('.delete-budget-btn').forEach(btn => 
            btn.addEventListener('click', (e) => this.deleteBudget(e.currentTarget.dataset.id)));
    }

    editBudget(id, budgets) {
        const budget = budgets.find(b => b.budget_id.toString() === id);
        if (budget) {
            this.openBudgetModal({
                id: budget.budget_id,
                category_id: budget.category_id,
                amount: budget.budgeted_amount,
                budget_month: budget.budget_month
            });
        }
    }

    async deleteBudget(id) {
        if (!confirm('Are you sure?')) return;
        try {
            const response = await fetch(`/api/budgets/${id}`, { method: 'DELETE' });
            if (response.ok) {
                this.showMessage('Budget deleted!', 'success');
                this.loadBudgets();
            } else {
                this.showMessage('Failed to delete budget', 'error');
            }
        } catch (error) {
            this.showMessage('Failed to delete budget', 'error');
        }
    }

    // Recurring Transactions (NEW)
    async loadRecurringTransactions() {
        const activeOnly = document.getElementById('filter-recurring-status').value;
        try {
            const response = await fetch(`/api/recurring-transactions?active_only=${activeOnly}`);
            const items = await response.json();
            this.displayRecurringTransactions(items);
        } catch(e) {
            console.error('Failed to load recurring txns', e);
        }
    }

    displayRecurringTransactions(items) {
        this.renderItems('recurring-list', items, this.renderRecurringItem, 'No recurring transactions found.');
        document.querySelectorAll('.edit-recurring-btn').forEach(btn => 
            btn.addEventListener('click', (e) => this.editRecurring(e.currentTarget.dataset.id, items)));
        document.querySelectorAll('.delete-recurring-btn').forEach(btn => 
            btn.addEventListener('click', (e) => this.deleteRecurring(e.currentTarget.dataset.id)));
    }

    editRecurring(id, items) {
        const item = items.find(i => i.id.toString() === id);
        if (item) this.openRecurringModal(item);
    }

    async deleteRecurring(id) {
        if (!confirm('This will deactivate the recurring transaction. Continue?')) return;
        try {
            const response = await fetch(`/api/recurring-transactions/${id}`, { method: 'DELETE' });
            if (response.ok) {
                this.showMessage('Recurring transaction deactivated!', 'success');
                this.loadRecurringTransactions();
            } else {
                this.showMessage('Failed to deactivate.', 'error');
            }
        } catch (error) {
            this.showMessage('Operation failed.', 'error');
        }
    }

    // Charting
    updateSpendingChart(data) {
        const canvas = document.getElementById('spending-chart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (this.spendingChart) this.spendingChart.destroy();
        this.spendingChart = this.createBarChart(ctx, data);
    }
    updateCategoryChart(data) {
        const canvas = document.getElementById('category-chart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (this.categoryChart) this.categoryChart.destroy();
        this.categoryChart = this.createBarChart(ctx, data);
    }
    
    createBarChart(ctx, data) {
         if (data.length === 0) {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No spending data available', ctx.canvas.width / 2, ctx.canvas.height / 2);
            return;
        }

        const maxAmount = Math.max(...data.map(item => item.amount));
        const barWidth = ctx.canvas.width / data.length - 20;
        const barMaxHeight = ctx.canvas.height - 60;

        data.forEach((item, index) => {
            const barHeight = (item.amount / maxAmount) * barMaxHeight;
            const x = index * (barWidth + 20) + 10;
            const y = ctx.canvas.height - barHeight - 30;
            ctx.fillStyle = `hsl(${index * 60}, 70%, 60%)`;
            ctx.fillRect(x, y, barWidth, barHeight);
            ctx.fillStyle = '#333';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(item.category, x + barWidth / 2, ctx.canvas.height - 10);
            ctx.fillText(this.formatCurrency(item.amount), x + barWidth / 2, y - 5);
        });
    }


    async loadReports() {
        await this.loadDashboardData(); // For now, reports just reuses dashboard data
    }
    
    // RENDER HELPERS
    renderItems(containerId, items, renderer, emptyMessage) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        if (!items || items.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>${emptyMessage}</p></div>`;
            return;
        }
        container.innerHTML = items.map(item => renderer.call(this, item)).join('');
    }

    renderTransactionItem(t) {
        const isIncome = t.transaction_type === 'income';
        return `
            <div class="transaction-item ${t.transaction_type}">
                <div class="transaction-info">
                    <div class="transaction-icon"><i class="fas fa-${isIncome ? 'arrow-up' : 'arrow-down'}"></i></div>
                    <div>
                        <h4>${t.description || 'No description'}</h4>
                        <p>${t.category_name || 'Uncategorized'} &bull; ${this.formatDate(t.date)}</p>
                    </div>
                </div>
                <div class="transaction-amount">${isIncome ? '+' : '-'}${this.formatCurrency(t.amount)}</div>
                <div class="transaction-actions">
                    <button class="action-btn-small" onclick="app.editTransaction(${t.id})"><i class="fas fa-edit"></i></button>
                    <button class="action-btn-small" onclick="app.deleteTransaction(${t.id})"><i class="fas fa-trash"></i></button>
                </div>
            </div>`;
    }

    renderBudgetItem(b) {
        const isOver = b.remaining_amount < 0;
        return `
            <div class="budget-item">
                <div class="budget-info">
                    <h4>${b.category_name} - <span style="font-weight:normal; font-size: 0.9em;">${this.formatMonthYear(b.budget_month)}</span></h4>
                    <p>Budgeted: ${this.formatCurrency(b.budgeted_amount)} | Spent: ${this.formatCurrency(b.spent_amount)}</p>
                    <progress value="${b.spent_amount}" max="${b.budgeted_amount}" class="${isOver ? 'overspent' : ''}"></progress>
                    <p>Remaining: <span style="color:${isOver ? '#f44336' : '#4CAF50'}; font-weight: bold;">${this.formatCurrency(b.remaining_amount)}</span></p>
                </div>
                <div class="budget-actions">
                    <button class="action-btn-small edit-budget-btn" data-id="${b.budget_id}"><i class="fas fa-edit"></i></button>
                    <button class="action-btn-small delete-budget-btn" data-id="${b.budget_id}"><i class="fas fa-trash"></i></button>
                </div>
            </div>`;
    }

    renderRecurringItem(r) {
        const statusClass = r.is_active ? 'active' : 'inactive';
        return `
            <div class="recurring-item ${statusClass}">
                <div class="recurring-info">
                    <h4>${r.description} (${r.transaction_type})</h4>
                    <p>Amount: ${this.formatCurrency(r.amount)} | Category: ${r.category_name || 'N/A'}</p>
                    <p>Schedule: Every ${r.interval} ${r.frequency} | Next Due: ${this.formatDate(r.next_due_date)}</p>
                    <p>Status: <span class="status-${statusClass}">${r.is_active ? 'Active' : 'Inactive'}</span></p>
                </div>
                <div class="recurring-actions">
                    <button class="action-btn-small edit-recurring-btn" data-id="${r.id}"><i class="fas fa-edit"></i></button>
                    <button class="action-btn-small delete-recurring-btn" data-id="${r.id}"><i class="fas fa-power-off"></i></button>
                </div>
            </div>`;
    }

    // UTILITY HELPERS
    formatCurrency(amount) {
        // FIX: Added fallback for null/undefined amount
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount || 0);
    }
    formatDate(dateString) { return new Date(dateString).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' }); }
    formatMonthYear(monthYearStr) { // e.g., "2025-06"
        if (!monthYearStr || !monthYearStr.includes('-')) return monthYearStr; // Fallback
        const parts = monthYearStr.split('-');
        if (parts.length !== 2) return monthYearStr; // Fallback for malformed string
        const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, 1); // Month is 0-indexed
        return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }); // e.g., "June 2025"
    }
    showMessage(message, type = 'success') {
        const container = document.getElementById('message-container');
        const msgEl = document.createElement('div');
        msgEl.className = `message ${type}`;
        msgEl.textContent = message;
        container.appendChild(msgEl);
        setTimeout(() => { if (msgEl.parentNode) msgEl.parentNode.removeChild(msgEl); }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => { window.app = new MoneyManager(); });