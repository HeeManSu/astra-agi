# Technical Tools

> Generated on **2026-03-03 19:55 UTC** with ticker **NVDA**

---

**Results: 6/6 tools succeeded**

---

## ✅ `get_price_history`

_Recent OHLCV data (last 10 days)_

### Input

```json
{
  "symbol": "NVDA",
  "days": 10
}
```

### Output

```json
{
  "symbol": "NVDA",
  "period": "Last 10 trading days",
  "current_price": 179.99,
  "prices": [
    {
      "date": "2026-02-18",
      "open": 188.75,
      "high": 190.37,
      "low": 186.76,
      "close": 187.98,
      "volume": 164749100
    },
    {
      "date": "2026-02-19",
      "open": 187.06,
      "high": 188.43,
      "low": 185.66,
      "close": 187.9,
      "volume": 126554500
    },
    {
      "date": "2026-02-20",
      "open": 186.57,
      "high": 190.33,
      "low": 185.94,
      "close": 189.82,
      "volume": 178422300
    },
    {
      "date": "2026-02-23",
      "open": 191.4,
      "high": 193.95,
      "low": 189.58,
      "close": 191.55,
      "volume": 171584800
    },
    {
      "date": "2026-02-24",
      "open": 191.49,
      "high": 193.77,
      "low": 187.4,
      "close": 192.85,
      "volume": 175123600
    },
    {
      "date": "2026-02-25",
      "open": 194.45,
      "high": 197.63,
      "low": 193.79,
      "close": 195.56,
      "volume": 250637100
    },
    {
      "date": "2026-02-26",
      "open": 194.27,
      "high": 194.29,
      "low": 184.32,
      "close": 184.89,
      "volume": 360807900
    },
    {
      "date": "2026-02-27",
      "open": 181.25,
      "high": 182.59,
      "low": 176.38,
      "close": 177.19,
      "volume": 311636500
    },
    {
      "date": "2026-03-02",
      "open": 175.01,
      "high": 183.46,
      "low": 174.64,
      "close": 182.48,
      "volume": 209095300
    },
    {
      "date": "2026-03-03",
      "open": 178.48,
      "high": 180.9,
      "low": 176.92,
      "close": 179.99,
      "volume": 138413401
    }
  ]
}
```

---

## ✅ `calculate_rsi`

_RSI value and overbought/oversold signal_

### Input

```json
{
  "symbol": "NVDA",
  "period": 14
}
```

### Output

```json
{
  "symbol": "NVDA",
  "rsi": 41.1,
  "period": 14,
  "signal": "neutral"
}
```

---

## ✅ `calculate_macd`

_MACD line, signal line, histogram, crossover_

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
  "macd": -0.5135,
  "signal_line": 0.4365,
  "histogram": -0.95,
  "crossover": "bearish"
}
```

---

## ✅ `calculate_moving_averages`

_SMA 20/50/200, current price, trend classification_

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
  "current_price": 179.99,
  "sma_20": 185.27,
  "sma_50": 185.9,
  "sma_200": 175.43,
  "trend": "sideways",
  "ma_cross": "none"
}
```

---

## ✅ `detect_trend`

_Trend direction, strength, key levels_

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
  "trend": "sideways",
  "strength": "weak",
  "sma20_slope": -0.0468,
  "sma50_slope": 0.1293,
  "higher_highs": true,
  "lower_lows": false,
  "52w_range_position": "76.0%",
  "52w_high": 207.03,
  "52w_low": 94.29
}
```

---

## ✅ `detect_support_resistance`

_Support and resistance levels from pivot analysis_

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
  "current_price": 179.99,
  "support_levels": [
    86.6,
    95.02,
    104.74
  ],
  "resistance_levels": [
    186.25,
    195.31,
    212.18
  ],
  "nearest_support": 104.74,
  "nearest_resistance": 186.25
}
```

---
