document.addEventListener('DOMContentLoaded', () => {
    const cashElement = document.getElementById('cash');
    const tickerInput = document.getElementById('ticker-input');
    const searchBtn = document.getElementById('search-btn');
    const stockTickerElement = document.getElementById('stock-ticker');
    const stockPriceElement = document.getElementById('stock-price');
    const quantityInput = document.getElementById('quantity-input');
    const buyBtn = document.getElementById('buy-btn');
    const sellBtn = document.getElementById('sell-btn');
    const stockList = document.getElementById('stock-list');

    let portfolio = {};
    let currentTicker = null;
    let currentPrice = null;

    async function searchStock() {
        const ticker = tickerInput.value.trim().toUpperCase();
        if (!ticker) return;

        try {
            const response = await fetch(`/api/stock/${ticker}`);
            if (!response.ok) {
                throw new Error('Stock not found');
            }
            const data = await response.json();
            currentTicker = data.ticker;
            currentPrice = data.price;
            stockTickerElement.textContent = currentTicker;
            stockPriceElement.textContent = currentPrice.toFixed(2);
        } catch (error) {
            alert(error.message);
        }
    }

    async function buyStock() {
        const quantity = parseInt(quantityInput.value);
        if (!currentTicker || !currentPrice || !quantity || quantity <= 0) {
            alert('Invalid ticker, price, or quantity.');
            return;
        }

        try {
            const response = await fetch('/api/buy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: currentTicker, quantity: quantity })
            });
            if (!response.ok) {
                throw new Error(await response.text());
            }
            updatePortfolio();
        } catch (error) {
            alert(`Error buying stock: ${error.message}`);
        }
    }

    async function sellStock() {
        const quantity = parseInt(quantityInput.value);
        if (!currentTicker || !quantity || quantity <= 0) {
            alert('Invalid ticker or quantity.');
            return;
        }

        try {
            const response = await fetch('/api/sell', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: currentTicker, quantity: quantity })
            });
            if (!response.ok) {
                throw new Error(await response.text());
            }
            updatePortfolio();
        } catch (error) {
            alert(`Error selling stock: ${error.message}`);
        }
    }

    async function updatePortfolio() {
        try {
            const response = await fetch('/api/portfolio');
            if (!response.ok) {
                throw new Error('Failed to fetch portfolio');
            }
            const data = await response.json();
            cashElement.textContent = data.cash.toFixed(2);
            stockList.innerHTML = '';
            for (const [ticker, quantity] of Object.entries(data.stocks)) {
                const li = document.createElement('li');
                li.textContent = `${ticker}: ${quantity}`;
                stockList.appendChild(li);
            }
        } catch (error) {
            console.error(error);
        }
    }

    searchBtn.addEventListener('click', searchStock);
    buyBtn.addEventListener('click', buyStock);
    sellBtn.addEventListener('click', sellStock);

    updatePortfolio();
});
