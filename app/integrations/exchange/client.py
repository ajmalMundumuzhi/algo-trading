import ccxt.async_support as ccxt

from app.core.config import settings 

def create_exchange_client():
    exchange_id = settings.exchange_id

    if not exchange_id:
        raise ValueError("Exchange ID is not configured.")

    exchange_class = getattr(ccxt, exchange_id, None)

    if exchange_class is None:
        raise ValueError(f"Unsupported exchange ID: {exchange_id}")

    return exchange_class({
        "enableRateLimit": True,
        "timeout": 30000,
        "options": {
            "defaultType": "spot"
        },
    })