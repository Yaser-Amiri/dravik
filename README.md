# Dravik

### Development
Look at the Makefile.

Sample config file (by default in `~/.config/dravik/config.json` after first run):  
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

Also there is a sample ledger file named `sample.ledger` in the root of the project for developmet.
