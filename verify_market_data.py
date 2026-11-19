
from sqlalchemy import text
from app.core.database import SessionLocal

symbols = [
    "XLM/USDT",
    "XAUT/USDT",
    "SUI/USDT",
    "HBAR/USDT",
    "QNT/USDT",
    "PAXG/USDT",
    "AAVE/USDT",
]

db = SessionLocal()

try:
    assets = db.execute(
        text("""
            SELECT COUNT(*)
            FROM market_assets
            WHERE binance_pair = ANY(:symbols)
        """),
        {"symbols": symbols},
    ).scalar()

    candles = db.execute(
        text("""
            SELECT symbol, COUNT(*)
            FROM market_candles
            WHERE symbol = ANY(:symbols)
              AND timeframe = :timeframe
            GROUP BY symbol
            ORDER BY symbol
        """),
        {"symbols": symbols, "timeframe": "1h"},
    ).all()

    print("ASSETS:", assets)
    print("CANDLES:")

    for symbol, count in candles:
        print(f"{symbol}: {count}")

finally:
    db.close()
