# Risk Tools

> Generated on **2026-03-03 19:55 UTC** with ticker **NVDA**

---

**Results: 5/5 tools succeeded**

---

## ✅ `get_stock_beta`

_Beta value and risk level_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "symbol": "NVDA",
  "beta": 2.38,
  "risk_level": "high"
}
```

---

## ✅ `calculate_volatility`

_Annualized volatility and regime classification_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "symbol": "NVDA",
  "annualized_vol": "42.8%",
  "regime": "very high"
}
```

---

## ✅ `get_correlation_with_portfolio`

_Correlation against top 5 portfolio holdings_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "symbol": "NVDA",
  "correlations": {
    "AAPL": 0.217,
    "MSFT": 0.254,
    "JNJ": -0.155,
    "JPM": 0.184,
    "XOM": 0.007
  },
  "avg_correlation": 0.101,
  "diversification_benefit": "good - adds diversification"
}
```

---

## ✅ `estimate_drawdown_risk`

_Max drawdown % and risk level_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "symbol": "NVDA",
  "max_drawdown": "-22.5%",
  "drawdown_risk": "high",
  "current_from_peak": "-13.1%"
}
```

---

## ✅ `get_portfolio_state`

_Current holdings, cash, NAV, sector weights_

### Input

```json
{}
```

### Output

```json
{
  "nav": 10000000,
  "cash": 1500000,
  "cash_pct": "15.0%",
  "num_positions": 5,
  "positions": [
    {
      "symbol": "AAPL",
      "shares": 500,
      "avg_cost": 165.0,
      "sector": "Technology",
      "entry_date": "2025-06-15"
    },
    {
      "symbol": "MSFT",
      "shares": 300,
      "avg_cost": 380.0,
      "sector": "Technology",
      "entry_date": "2025-07-20"
    },
    {
      "symbol": "JNJ",
      "shares": 400,
      "avg_cost": 155.0,
      "sector": "Healthcare",
      "entry_date": "2025-08-10"
    },
    {
      "symbol": "JPM",
      "shares": 200,
      "avg_cost": 195.0,
      "sector": "Financials",
      "entry_date": "2025-09-01"
    },
    {
      "symbol": "XOM",
      "shares": 350,
      "avg_cost": 105.0,
      "sector": "Energy",
      "entry_date": "2025-10-05"
    }
  ],
  "sector_weights": {
    "Technology": "2.0%",
    "Healthcare": "0.6%",
    "Financials": "0.4%",
    "Energy": "0.4%"
  }
}
```

---
