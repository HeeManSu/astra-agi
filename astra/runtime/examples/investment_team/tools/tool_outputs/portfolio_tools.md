# Portfolio Tools

> Generated on **2026-03-03 19:55 UTC** with ticker **NVDA**

---

**Results: 4/4 tools succeeded**

---

## ✅ `get_portfolio_state`

_Full portfolio: holdings, cash, NAV, weights_

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
  "max_positions": 15,
  "positions": [
    {
      "symbol": "AAPL",
      "shares": 500,
      "avg_cost": 165.0,
      "sector": "Technology",
      "entry_date": "2025-06-15",
      "market_value": 82500.0,
      "weight": "0.8%"
    },
    {
      "symbol": "MSFT",
      "shares": 300,
      "avg_cost": 380.0,
      "sector": "Technology",
      "entry_date": "2025-07-20",
      "market_value": 114000.0,
      "weight": "1.1%"
    },
    {
      "symbol": "JNJ",
      "shares": 400,
      "avg_cost": 155.0,
      "sector": "Healthcare",
      "entry_date": "2025-08-10",
      "market_value": 62000.0,
      "weight": "0.6%"
    },
    {
      "symbol": "JPM",
      "shares": 200,
      "avg_cost": 195.0,
      "sector": "Financials",
      "entry_date": "2025-09-01",
      "market_value": 39000.0,
      "weight": "0.4%"
    },
    {
      "symbol": "XOM",
      "shares": 350,
      "avg_cost": 105.0,
      "sector": "Energy",
      "entry_date": "2025-10-05",
      "market_value": 36750.0,
      "weight": "0.4%"
    }
  ]
}
```

---

## ✅ `calculate_portfolio_beta`

_Weighted portfolio beta with compliance check_

### Input

```json
{}
```

### Output

```json
{
  "portfolio_beta": 0.029,
  "target_range": "0.8 - 1.2",
  "in_range": false,
  "details": [
    {
      "symbol": "AAPL",
      "beta": 1.12,
      "weight": "0.8%"
    },
    {
      "symbol": "MSFT",
      "beta": 1.11,
      "weight": "1.1%"
    },
    {
      "symbol": "JNJ",
      "beta": 0.33,
      "weight": "0.6%"
    },
    {
      "symbol": "JPM",
      "beta": 1.06,
      "weight": "0.4%"
    },
    {
      "symbol": "XOM",
      "beta": 0.35,
      "weight": "0.4%"
    }
  ]
}
```

---

## ✅ `sector_exposure`

_Sector weights and cap compliance_

### Input

```json
{}
```

### Output

```json
{
  "sectors": {
    "Technology": {
      "value": 196500.0,
      "weight": "2.0%",
      "cap": "30%",
      "compliant": true
    },
    "Healthcare": {
      "value": 62000.0,
      "weight": "0.6%",
      "cap": "30%",
      "compliant": true
    },
    "Financials": {
      "value": 39000.0,
      "weight": "0.4%",
      "cap": "30%",
      "compliant": true
    },
    "Energy": {
      "value": 36750.0,
      "weight": "0.4%",
      "cap": "30%",
      "compliant": true
    }
  },
  "violations": [],
  "compliant": true
}
```

---

## ✅ `cash_available`

_Available cash after 5% reserve_

### Input

```json
{}
```

### Output

```json
{
  "total_cash": 1500000.0,
  "minimum_reserve": 500000.0,
  "available_for_deployment": 1000000.0,
  "cash_pct": "15.0%"
}
```

---
