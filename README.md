# Personal Wallet Web Application

A comprehensive web-based solution for tracking personal finances, managing multiple accounts, and monitoring expenses across different categories. This application helps users maintain better control over their financial activities by providing detailed insights and reports.

Live Demo: [[https://taskforce-n9sg.onrender.com](https://taskforce-n9sg.onrender.com)](https://taskforce-n9sg.onrender.com)

## Features and Functionalities

1. **User Authentication**
   - Secure registration and login system
   - Password hashing for enhanced security
   - Session management

2. **Account Management**
   - Create and manage multiple accounts (bank accounts, mobile money, cash, etc.)
   - Track real-time balance for each account
   - View account-specific transaction history

3. **Transaction Tracking**
   - Record income and expenses
   - Detailed transaction history with date, description, and category
   - Filter transactions by date, account, or category
   - Search functionality for finding specific transactions

4. **Category Management**
   - Create custom categories and subcategories
   - Organize expenses by categories
   - Link transactions to specific categories
   - Hierarchical category structure

5. **Budgeting System**
   - Set budget limits for different categories
   - Real-time budget tracking
   - Automated notifications when approaching or exceeding budget limits
   - Visual representation of budget utilization

6. **Reporting and Analytics**
   - Generate detailed financial reports
   - Customizable date ranges for reports
   - Export reports in PDF format
   - Visual data representation through charts and graphs
   - Income vs. Expenses analysis
   - Category-wise expense breakdown

7. **Dashboard**
   - Overview of total balance across all accounts
   - Recent transaction summary
   - Monthly income and expense trends
   - Budget alerts and notifications
   - Visual representations of financial data

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Python 3.8 or higher
- pip (Python package manager)
- SQLite3
- Git

## Project Setup

1. **Clone the Repository**
   ```bash
   git clone <your-repository-url>
   cd wallet-app
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   ```

3. **Activate Virtual Environment**
   - For Windows:
     ```bash
     venv\Scripts\activate
     ```
   - For macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize Database**
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. **Run the Application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## Project Structure
```
wallet_app/
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── templates/
│   ├── auth/
│   │   ├── register.html
│   │   └── login.html
│   ├── base.html
│   ├── dashboard.html
│   ├── accounts.html
│   ├── categories.html
│   ├── transactions.html
│   ├── budgets.html
│   └── reports.html
└── app.py
```

## Deployment

The application is currently deployed on Render and can be accessed at [https://taskforce-n9sg.onrender.com](https://taskforce-n9sg.onrender.com)

To deploy your own instance:
1. Create an account on Render
2. Connect your GitHub repository
3. Create a new Web Service
4. Configure the build and start commands
5. Set up environment variables if necessary

## Application Screenshots

### 1. Login Page
- Secure authentication interface
- User-friendly login form
- Registration link for new users

### 2. Registration Page
- New user registration form
- Password requirements
- Account creation interface

### 3. Dashboard
- Overview of total balance
- Recent transactions
- Income vs Expenses charts
- Budget alerts
- Category distribution

### 4. Accounts Page
- List of all accounts
- Account balances
- Add new account functionality
- Transaction history per account

### 5. Categories Page
- Category management interface
- Add/Edit categories and subcategories
- Category hierarchy view
- Budget allocation per category

### 6. Transactions Page
- Transaction list with filters
- Add new transaction form
- Search and sort functionality
- Transaction details view

### 7. Budgets Page
- Budget setting interface
- Budget progress tracking
- Category-wise budget allocation
- Budget alerts and notifications

### 8. Reports Page
- Customizable report generation
- Date range selection
- Account and category filters
- PDF export functionality

### 9. Transaction Details
- Detailed view of individual transactions
- Edit transaction capability
- Category and account information

### 10. Budget Alerts
- Visual budget warnings
- Progress bars for budget tracking
- Notification system

### 11. Analytics Dashboard
- Visual representations of financial data
- Trend analysis
- Category distribution charts
- Income vs Expense comparisons

## Contributing

Feel free to fork the repository and submit pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
