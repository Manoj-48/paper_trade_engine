import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
from datetime import datetime
import os

app = FastAPI(title="Paper Trade Engine V2")

# --- Configuration ---
DATA_FOLDER = "data"
LOG_FILE = os.path.join(DATA_FOLDER, "trade_log.csv")

# --- Data Models ---
class Signal(BaseModel):
    source: str
    ticker: str
    action: str  # "BUY" or "SELL"
    sl: float
    target: float

class Trade:
    def __init__(self, signal: Signal, entry_price: float):
        self.id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        self.signal = signal
        self.entry_price = entry_price
        self.entry_time = datetime.now()
        self.status = "OPEN"
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0

    def close(self, exit_price: float):
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.status = "CLOSED"
        if self.signal.action == "BUY":
            self.pnl = self.exit_price - self.entry_price
        else: # SELL
            self.pnl = self.entry_price - self.exit_price
        log_trade(self)

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.signal.source,
            "ticker": self.signal.ticker,
            "action": self.signal.action,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "sl": self.signal.sl,
            "target": self.signal.target,
            "status": self.status,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time,
            "pnl": self.pnl,
        }

# --- In-Memory State ---
# Using a dictionary to store trades by ID for quick access
open_trades = {}

# --- Helper Functions ---
def setup():
    """Create necessary folders and files on startup."""
    os.makedirs(DATA_FOLDER, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=[
            "id", "source", "ticker", "action", "entry_price", "entry_time",
            "sl", "target", "status", "exit_price", "exit_time", "pnl"
        ]).to_csv(LOG_FILE, index=False)

def log_trade(trade: Trade):
    """Appends a closed trade to the CSV log file."""
    try:
        trade_df = pd.DataFrame([trade.to_dict()])
        trade_df.to_csv(LOG_FILE, mode='a', header=False, index=False)
    except Exception as e:
        print(f"Error logging trade: {e}")

def get_live_price(ticker: str) -> float:
    """Fetches the last closing price for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        # Using '1d' period to get the most recent price data available.
        price_history = stock.history(period="1d", interval="1m")
        if price_history.empty:
            # Fallback for less frequent tickers
            price_history = stock.history(period="1d")
        
        if price_history.empty:
            raise ValueError("No price data found.")
            
        return price_history["Close"].iloc[-1]
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None

# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    setup()

@app.post("/signal", status_code=201)
async def process_signal(signal: Signal):
    """
    Receives a signal, creates a new trade, and adds it to our open trades.
    This is the "Manual paste JM signal" entry point.
    """
    print(f"Received signal: {signal.dict()}")

    live_price = get_live_price(signal.ticker)
    if not live_price:
        raise HTTPException(status_code=404, detail=f"Could not fetch live price for {signal.ticker}")

    trade = Trade(signal=signal, entry_price=live_price)
    open_trades[trade.id] = trade
    
    print(f"New trade created: {trade.to_dict()}")
    return {"message": "Trade created successfully", "trade": trade.to_dict()}

@app.get("/trades/open")
async def get_open_trades():
    """Returns a list of all currently open trades."""
    return [trade.to_dict() for trade in open_trades.values()]

@app.get("/trades/log")
async def get_trade_log():
    """Returns all logged trades from the CSV file."""
    try:
        df = pd.read_csv(LOG_FILE)
        return df.to_dict(orient="records")
    except FileNotFoundError:
        return []

# This would be run in a background task in a real application
# For now, we can have a manual endpoint to trigger it.
@app.post("/engine/run")
async def run_trade_engine():
    """
    This function simulates the core engine logic.
    It iterates through open trades and checks for SL/Target hits.
    """
    closed_trades_count = 0
    trades_to_remove = []
    
    for trade_id, trade in open_trades.items():
        live_price = get_live_price(trade.signal.ticker)
        if not live_price:
            continue

        print(f"Checking trade {trade.id} ({trade.signal.ticker}). Live price: {live_price}")

        # Check SL/Target
        if trade.signal.action == "BUY":
            if live_price <= trade.signal.sl:
                print(f"SL hit for {trade.id}")
                trade.close(live_price)
                closed_trades_count += 1
                trades_to_remove.append(trade_id)
            elif live_price >= trade.signal.target:
                print(f"Target hit for {trade.id}")
                trade.close(live_price)
                closed_trades_count += 1
                trades_to_remove.append(trade_id)
        
        # TODO: Add SELL logic for SL/Target check

    # Clean up closed trades from the in-memory dictionary
    for trade_id in trades_to_remove:
        del open_trades[trade_id]

    return {"message": f"Engine run complete. Closed {closed_trades_count} trades."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)