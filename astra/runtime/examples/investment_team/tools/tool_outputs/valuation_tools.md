# Valuation Tools

> Generated on **2026-03-03 19:55 UTC** with ticker **NVDA**

---

**Results: 4/4 tools succeeded**

---

## ✅ `get_current_market_data`

_Price, market cap, shares outstanding, EV, FCF_

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
  "current_price": 179.98,
  "market_cap": "$4374.29B",
  "enterprise_value": "$4383.12B",
  "shares_outstanding": "$24.30B",
  "free_cashflow": "$58.13B",
  "trailing_pe": 36.654808,
  "forward_pe": 16.851505,
  "ev_to_ebitda": 32.899,
  "price_to_book": 27.808266
}
```

---

## ✅ `calculate_dcf`

_DCF fair value with bear/base/bull scenarios_

### Input

```json
{
  "symbol": "NVDA",
  "growth_rate": 0.1,
  "discount_rate": 0.1,
  "terminal_growth": 0.03,
  "projection_years": 5
}
```

### Output

```json
{
  "symbol": "NVDA",
  "current_price": 179.98,
  "fcf_used": "$58.13B",
  "growth_rate": "10.0%",
  "discount_rate": "10.0%",
  "bear_case": 38.32,
  "base_case": 47.16,
  "bull_case": 57.65,
  "base_upside": "-73.8%"
}
```

---

## ✅ `calculate_multiple_valuation`

_P/E, EV/EBITDA, P/B, PEG multiples_

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
  "trailing_pe": 36.65,
  "forward_pe": 16.85,
  "peg_ratio": "N/A",
  "ev_to_ebitda": 32.9,
  "ev_to_revenue": 20.3,
  "price_to_book": 27.81,
  "price_to_sales": 20.26,
  "assessment": "Fairly valued"
}
```

---

## ✅ `calculate_margin_of_safety`

_Margin of safety % and buy/hold/pass verdict_

### Input

```json
{
  "current_price": 150.0,
  "fair_value": 200.0
}
```

### Output

```json
{
  "current_price": 150.0,
  "fair_value": 200.0,
  "margin_of_safety": "25.0%",
  "upside_potential": "33.3%",
  "verdict": "Attractive - adequate margin of safety"
}
```

---
