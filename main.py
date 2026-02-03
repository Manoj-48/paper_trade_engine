from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yfinance as yf

app = FastAPI()

# In-memory data stores
portfolio = {
    "cash": 100000.0,
    "stocks": {}
}

class Trade(BaseModel):
    ticker: str
    quantity: int

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/manifest.json")
async def read_manifest():
    return FileResponse('manifest.json')

@app.get("/service-worker.js")
async def read_service_worker():
    return FileResponse('service-worker.js')

@app.get("/api/stock/{ticker}")
async def get_stock_price(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return {"ticker": ticker, "price": price}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stock not found: {e}")

@app.post("/api/buy")
async def buy_stock(trade: Trade):
    try:
        stock = yf.Ticker(trade.ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        cost = price * trade.quantity

        if portfolio["cash"] >= cost:
            portfolio["cash"] -= cost
            portfolio["stocks"][trade.ticker] = portfolio["stocks"].get(trade.ticker, 0) + trade.quantity
            return {"message": "Trade successful"}
        else:
            raise HTTPException(status_code=400, detail="Not enough cash")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sell")
async def sell_stock(trade: Trade):
    if trade.ticker not in portfolio["stocks"] or portfolio["stocks"][trade.ticker] < trade.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock to sell")

    try:
        stock = yf.Ticker(trade.ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        revenue = price * trade.quantity

        portfolio["stocks"][trade.ticker] -= trade.quantity
        if portfolio["stocks"][trade.ticker] == 0:
            del portfolio["stocks"][trade.ticker]
        
        portfolio["cash"] += revenue
        return {"message": "Trade successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio")
async def get_portfolio():
    return portfolio
