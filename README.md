# Dravik

### Usage
To install Dravik, use the following command to install the package from PyPI::  
`pip install dravik`  
After installation, run the command below to initialize the configuration files:  
`dravik-init`  
This will create the configuration files and display the file path in the terminal. You can then run Dravik using the following command:  
`dravik`  

**Note**: Dravik does not automatically install hledger. If you don't have it installed, you will need to install and configure it manually.

### Configuration

By default, Dravik creates a config file at ~/.config/dravik/config.json after the initial setup. Here is an example of what it might look like:
```json
{
    "ledger": "/home/yaser/hledger/2025.ledger",
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

__

### Development
To get started with development, refer to the Makefile for available commands and instructions.  
Additionally, there is a sample ledger file named sample.ledger located at the root of the project for testing and development purposes.
