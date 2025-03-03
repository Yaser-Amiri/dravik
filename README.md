# 📖 Dravik

![PyPI - Version](https://img.shields.io/pypi/v/dravik?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/Yaser-Amiri/dravik?style=for-the-badge)

Dravik is a terminal-based user interface (TUI) for `hledger`, designed to streamline personal and business accounting for users who prefer a fast, keyboard-driven workflow. It provides an intuitive interface on top of `hledger`, making it easier to interact with your financial data without relying on manual text edits. 

**Note:** Dravik does **not** support all of hledger's features—only the ones I personally use. But you are welcome to add yours.

**Tested hledger version:** 1.32


---

## 📦 Installation

### **Recommended: Install via UV**
Dravik can be installed using `uv`, a fast Rust-based package manager that automatically handles dependencies, including Python.

#### **Linux & macOS**
```bash
# Install uv (package manager):
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal or run:
source $HOME/.local/bin/env

# Install Dravik
uv tool install --python 3.13 dravik
```
Now you can start using Dravik with:
```bash
dravik-init  # Initialize configuration files
dravik       # Start Dravik
```

### **Alternative: Install via Pip**
If you prefer using pip:
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

