
import asyncio

from app.integrations.exchange import create_exchange_client
from app.agents.market_data.collector import fetch_market_snapshot
from app.agents.technical.multi_timeframe import (
    analyze_multiple_timeframes,
)


async def main():
    exchange = create_exchange_client()
    symbol = "BTC/USDT"

    snapshots = {}

    try:
        await exchange.load_markets()

        for timeframe in ("15m", "1h", "4h", "1d"):
            print(f"\nFetching {timeframe} candles...")

            snapshot = await fetch_market_snapshot(
                exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=100,
            )

            snapshots[timeframe] = snapshot["candles"]

            print(
                f"{timeframe}: {len(snapshot['candles'])} closed candles"
            )

        print("\nRunning multi-timeframe analysis...")

        report = analyze_multiple_timeframes(
            snapshots=snapshots,
            symbol=symbol,
        )

        print("\nMULTI-TIMEFRAME TECHNICAL REPORT")

        for timeframe, result in report["timeframes"].items():
            print(f"\n{timeframe}:")

            if result["status"] == "ok":
                technical = result["technical_score"]

                print("Trend:", result["trend"]["trend"])  
                print("RSI:", result["indicators"]["rsi"]) 
                print("Direction:", technical["direction"])
                print("Score:", technical["score"])        
                print("Coverage:", technical["coverage"])

            else:
                print("Status:", result["status"])
                print("Reason:", result.get("reason"))

        print(
            "\nSuccessful timeframes:",
            report["successful_timeframes"],
            "/",
            report["total_timeframes"],
        )

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(main())
