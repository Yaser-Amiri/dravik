# Dravik

[![PyPI - Version](https://img.shields.io/pypi/v/dravik)](https://pypi.org/project/dravik/)
[![GitHub License](https://img.shields.io/github/license/Yaser-Amiri/dravik)](https://github.com/Yaser-Amiri/dravik/blob/main/LICENSE)

Dravik is a TUI for `hledger`, focused on a fast, keyboard-driven workflow for personal accounting. It provides a simple interface to interact with financial data without manual text edits.  

![Transactions List](./screenshots/tx_list.png)  
You can see more screenshots in `screenshots` directory in the root of the project.

Main Features:  
- Accounts tree  
- Transaction list with internal filters (shortcuts for time filters, autocomplete for account path input, etc)  
- Historical balance chart  
- Balance change chart  
- Financial reports: income statement, balance sheet, cash flow  
- Account labeling (e.g., label "Electricity" instead of `expenses:housing:utilities:electricity`)  
- Pin accounts on the home page to see their balance  
- Currency labels (e.g., label `$` instead of `USD`)  

**Note:** Dravik supports only the `hledger` features I use. You're welcome to add more. For currency conversion, I use the [equity method](https://hledger.org/currency-conversion.html#conversion-using-equity), so only that is supported.  
**Tested hledger version:** 1.32

---

## 📦 Installation

### **Recommended: Install via UV**
Dravik can be installed using `uv`, a fast Rust-based package manager that automatically handles dependencies, including Python.

```bash
# Install uv (package manager):
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal or run:
source $HOME/.local/bin/env

# Install python 3.13 if you don't have it already
uv python install 3.13

# Install Dravik
uv tool install --python 3.13 dravik
```
Now you can start using Dravik with:
```bash
dravik-init  # Initialize configuration files
dravik       # Start Dravik
```

### **Alternative: Install via Pip**
First make sure you have Python 3.13 and then install the package with your Python package manager (pip, etc)  
```bash
pip install dravik
```
However, `uv` is the recommended method due to its speed and dependency management.

---

## ⚙️ Configuration
After the initial setup, Dravik creates a config file at `~/.config/dravik/config.json`. Below is an example:
```json
{
    "ledger": "/home/user/hledger/2025.ledger",
    "account_labels": {
        "assets:bank": "Banks",
        "assets:binance": "Binance",
        "assets:bank:revolut": "Revolut",
        "assets:bank:sparkasse": "Sparkasse",
        "assets:bank:paypal": "PayPal",
        "assets:cash": "Cash"
    },
    "currency_labels": {
        "USDT": "₮",
        "EUR": "€"
    },
    "pinned_accounts": [
        {"account": "assets:bank", "color": "#2F4F4F"},
        {"account": "assets:cash", "color": "#8B4513"},
        {"account": "assets:binance", "color": "#556B2F"}
    ]
}
```

**Note:** If `ledger` is set to `null`, Dravik will use hledger's default file.

**Note:** Dravik does **not** install `hledger` automatically. You must install and configure it separately.

---

## 🛠️ Development Setup
Refer to the `Makefile` for available commands and setup instructions.

---

## 📜 License
Dravik is licensed under **GPL-3.0**. See the [LICENSE](https://github.com/Yaser-Amiri/dravik/blob/main/LICENSE) file for details.

