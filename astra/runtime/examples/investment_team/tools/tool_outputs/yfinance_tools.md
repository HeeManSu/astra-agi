# YFinance Tools

> Generated on **2026-03-03 19:55 UTC** with ticker **NVDA**

---

**Results: 9/9 tools succeeded**

---

## ✅ `get_current_stock_price`

_Current stock price_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
179.9751
```

---

## ✅ `get_company_info`

_Company overview: name, sector, P/E, market cap_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "Name": "NVIDIA Corporation",
  "Symbol": "NVDA",
  "Current Stock Price": "179.9751 USD",
  "Market Cap": "4374294953984 USD",
  "Sector": "Technology",
  "Industry": "Semiconductors",
  "Address": "2788 San Tomas Expressway",
  "City": "Santa Clara",
  "State": "CA",
  "Zip": "95051",
  "Country": "United States",
  "EPS": 4.91,
  "P/E Ratio": 36.654808,
  "52 Week Low": 86.62,
  "52 Week High": 212.19,
  "50 Day Average": 185.7162,
  "200 Day Average": 175.22015,
  "Website": "https://www.nvidia.com",
  "Summary": "NVIDIA Corporation, a computing infrastructure company, provides graphics and compute and networking solutions in the United States, Taiwan, China, Hong Kong, and internationally. It operates through Compute & Networking and Graphics segments. The Compute & Networking segment includes its Data Center accelerated computing and networking platforms and artificial intelligence solutions and software and automotive platforms and autonomous and electric vehicle solutions, including software. The Graphics segment offers GeForce GPUs for gaming and PCs; Quadro/NVIDIA RTX GPUs for enterprise workstation graphics; GeForce NOW cloud gaming service; and NVIDIA vGPU software for graphics- virtual desktops and workstations. It also develops standalone software solutions, including NVIDIA AI Enterprise, NVIDIA Omniverse, NVIDIA DRIVE, and other software products. The company's products are used in gaming, professional visualization, data center, and automotive markets. It sells its products to original equipment manufacturers, original device manufacturers, system integrators and distributors, independent software vendors, cloud service providers, add-in board manufacturers, distributors, automotive manufacturers and tier-1 automotive suppliers, and other ecosystem participants. NVIDIA Corporation was incorporated in 1993 and is headquartered in Santa Clara, California.",
  "Analyst Recommendation": "strong_buy",
  "Number Of Analyst Opinions": 58,
  "Employees": 42000,
  "Total Cash": 62556000256,
  "Free Cash flow": 58128998400,
  "Operating Cash flow": 102717997056,
  "EBITDA": 133230002176,
  "Revenue Growth": 0.732,
  "Gross Margins": 0.71068,
  "Ebitda Margins": 0.61698
}
```

---

## ✅ `get_historical_stock_prices`

_Historical OHLCV (last 5 days)_

### Input

```json
{
  "symbol": "NVDA",
  "period": "5d",
  "interval": "1d"
}
```

### Output

```json
{
  "1771995600000": {
    "Open": 194.4499969482,
    "High": 197.6300048828,
    "Low": 193.7899932861,
    "Close": 195.5599975586,
    "Volume": 250637100,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772082000000": {
    "Open": 194.2700042725,
    "High": 194.2899932861,
    "Low": 184.3200073242,
    "Close": 184.8899993896,
    "Volume": 360807900,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772168400000": {
    "Open": 181.25,
    "High": 182.5899963379,
    "Low": 176.3800048828,
    "Close": 177.1900024414,
    "Volume": 311636500,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772427600000": {
    "Open": 175.0099945068,
    "High": 183.4600067139,
    "Low": 174.6399993896,
    "Close": 182.4799957275,
    "Volume": 209095300,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772514000000": {
    "Open": 178.4774932861,
    "High": 180.8999938965,
    "Low": 176.9199981689,
    "Close": 179.9750976562,
    "Volume": 138426492,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  }
}
```

---

## ✅ `get_stock_fundamentals`

_Fundamentals: P/E, beta, 52-week high, market cap_

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
  "company_name": "NVIDIA Corporation",
  "sector": "Technology",
  "industry": "Semiconductors",
  "market_cap": 4374294953984,
  "pe_ratio": 16.851505,
  "pb_ratio": 27.808266,
  "dividend_yield": 0.02,
  "eps": 4.91,
  "beta": 2.375,
  "52_week_high": 212.19,
  "52_week_low": 86.62
}
```

---

## ✅ `get_income_statements`

_Income statement: revenue, net income, gross profit_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "Tax Effect Of Unusual Items": {
    "1769817600000": 0.0,
    "1738281600000": 0.0,
    "1706659200000": 0.0,
    "1675123200000": -284130000.0,
    "1643587200000": null
  },
  "Tax Rate For Calcs": {
    "1769817600000": 0.15117,
    "1738281600000": 0.132649,
    "1706659200000": 0.12,
    "1675123200000": 0.21,
    "1643587200000": null
  },
  "Normalized EBITDA": {
    "1769817600000": 144552000000.0,
    "1738281600000": 86137000000.0,
    "1706659200000": 35583000000.0,
    "1675123200000": 7339000000.0,
    "1643587200000": null
  },
  "Total Unusual Items": {
    "1769817600000": null,
    "1738281600000": 0.0,
    "1706659200000": 0.0,
    "1675123200000": -1353000000.0,
    "1643587200000": 0.0
  },
  "Total Unusual Items Excluding Goodwill": {
    "1769817600000": null,
    "1738281600000": 0.0,
    "1706659200000": 0.0,
    "1675123200000": -1353000000.0,
    "1643587200000": 0.0
  },
  "Net Income From Continuing Operation Net Minority Interest": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Reconciled Depreciation": {
    "1769817600000": 2843000000.0,
    "1738281600000": 1864000000.0,
    "1706659200000": 1508000000.0,
    "1675123200000": 1543000000.0,
    "1643587200000": null
  },
  "Reconciled Cost Of Revenue": {
    "1769817600000": 62475000000.0,
    "1738281600000": 32639000000.0,
    "1706659200000": 16621000000.0,
    "1675123200000": 11618000000.0,
    "1643587200000": null
  },
  "EBITDA": {
    "1769817600000": 144552000000.0,
    "1738281600000": 86137000000.0,
    "1706659200000": 35583000000.0,
    "1675123200000": 5986000000.0,
    "1643587200000": null
  },
  "EBIT": {
    "1769817600000": 141709000000.0,
    "1738281600000": 84273000000.0,
    "1706659200000": 34075000000.0,
    "1675123200000": 4443000000.0,
    "1643587200000": null
  },
  "Net Interest Income": {
    "1769817600000": 2041000000.0,
    "1738281600000": 1539000000.0,
    "1706659200000": 609000000.0,
    "1675123200000": 5000000.0,
    "1643587200000": null
  },
  "Interest Expense": {
    "1769817600000": 259000000.0,
    "1738281600000": 247000000.0,
    "1706659200000": 257000000.0,
    "1675123200000": 262000000.0,
    "1643587200000": null
  },
  "Interest Income": {
    "1769817600000": 2300000000.0,
    "1738281600000": 1786000000.0,
    "1706659200000": 866000000.0,
    "1675123200000": 267000000.0,
    "1643587200000": null
  },
  "Normalized Income": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 5436870000.0,
    "1643587200000": null
  },
  "Net Income From Continuing And Discontinued Operation": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Total Expenses": {
    "1769817600000": 85551000000.0,
    "1738281600000": 49044000000.0,
    "1706659200000": 27950000000.0,
    "1675123200000": 21397000000.0,
    "1643587200000": null
  },
  "Total Operating Income As Reported": {
    "1769817600000": 130387000000.0,
    "1738281600000": 81453000000.0,
    "1706659200000": 32972000000.0,
    "1675123200000": 4224000000.0,
    "1643587200000": null
  },
  "Diluted Average Shares": {
    "1769817600000": 24514000000.0,
    "1738281600000": 24804000000.0,
    "1706659200000": 24940000000.0,
    "1675123200000": 25070000000.0,
    "1643587200000": null
  },
  "Basic Average Shares": {
    "1769817600000": 24359000000.0,
    "1738281600000": 24555000000.0,
    "1706659200000": 24690000000.0,
    "1675123200000": 24870000000.0,
    "1643587200000": null
  },
  "Diluted EPS": {
    "1769817600000": 4.9,
    "1738281600000": 2.94,
    "1706659200000": 1.19,
    "1675123200000": 0.174,
    "1643587200000": null
  },
  "Basic EPS": {
    "1769817600000": 4.93,
    "1738281600000": 2.97,
    "1706659200000": 1.21,
    "1675123200000": 0.176,
    "1643587200000": null
  },
  "Diluted NI Availto Com Stockholders": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Net Income Common Stockholders": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Net Income": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Net Income Including Noncontrolling Interests": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Net Income Continuous Operations": {
    "1769817600000": 120067000000.0,
    "1738281600000": 72880000000.0,
    "1706659200000": 29760000000.0,
    "1675123200000": 4368000000.0,
    "1643587200000": null
  },
  "Tax Provision": {
    "1769817600000": 21383000000.0,
    "1738281600000": 11146000000.0,
    "1706659200000": 4058000000.0,
    "1675123200000": -187000000.0,
    "1643587200000": null
  },
  "Pretax Income": {
    "1769817600000": 141450000000.0,
    "1738281600000": 84026000000.0,
    "1706659200000": 33818000000.0,
    "1675123200000": 4181000000.0,
    "1643587200000": null
  },
  "Other Income Expense": {
    "1769817600000": 9022000000.0,
    "1738281600000": 1034000000.0,
    "1706659200000": 237000000.0,
    "1675123200000": -1401000000.0,
    "1643587200000": null
  },
  "Other Non Operating Income Expenses": {
    "1769817600000": 9022000000.0,
    "1738281600000": 1034000000.0,
    "1706659200000": 237000000.0,
    "1675123200000": -48000000.0,
    "1643587200000": null
  },
  "Special Income Charges": {
    "1769817600000": null,
    "1738281600000": 0.0,
    "1706659200000": 0.0,
    "1675123200000": -1353000000.0,
    "1643587200000": 0.0
  },
  "Restructuring And Mergern Acquisition": {
    "1769817600000": null,
    "1738281600000": 0.0,
    "1706659200000": 0.0,
    "1675123200000": 1353000000.0,
    "1643587200000": 0.0
  },
  "Net Non Operating Interest Income Expense": {
    "1769817600000": 2041000000.0,
    "1738281600000": 1539000000.0,
    "1706659200000": 609000000.0,
    "1675123200000": 5000000.0,
    "1643587200000": null
  },
  "Interest Expense Non Operating": {
    "1769817600000": 259000000.0,
    "1738281600000": 247000000.0,
    "1706659200000": 257000000.0,
    "1675123200000": 262000000.0,
    "1643587200000": null
  },
  "Interest Income Non Operating": {
    "1769817600000": 2300000000.0,
    "1738281600000": 1786000000.0,
    "1706659200000": 866000000.0,
    "1675123200000": 267000000.0,
    "1643587200000": null
  },
  "Operating Income": {
    "1769817600000": 130387000000.0,
    "1738281600000": 81453000000.0,
    "1706659200000": 32972000000.0,
    "1675123200000": 5577000000.0,
    "1643587200000": null
  },
  "Operating Expense": {
    "1769817600000": 23076000000.0,
    "1738281600000": 16405000000.0,
    "1706659200000": 11329000000.0,
    "1675123200000": 9779000000.0,
    "1643587200000": null
  },
  "Research And Development": {
    "1769817600000": 18497000000.0,
    "1738281600000": 12914000000.0,
    "1706659200000": 8675000000.0,
    "1675123200000": 7339000000.0,
    "1643587200000": null
  },
  "Selling General And Administration": {
    "1769817600000": 4579000000.0,
    "1738281600000": 3491000000.0,
    "1706659200000": 2654000000.0,
    "1675123200000": 2440000000.0,
    "1643587200000": null
  },
  "Gross Profit": {
    "1769817600000": 153463000000.0,
    "1738281600000": 97858000000.0,
    "1706659200000": 44301000000.0,
    "1675123200000": 15356000000.0,
    "1643587200000": null
  },
  "Cost Of Revenue": {
    "1769817600000": 62475000000.0,
    "1738281600000": 32639000000.0,
    "1706659200000": 16621000000.0,
    "1675123200000": 11618000000.0,
    "1643587200000": null
  },
  "Total Revenue": {
    "1769817600000": 215938000000.0,
    "1738281600000": 130497000000.0,
    "1706659200000": 60922000000.0,
    "1675123200000": 26974000000.0,
    "1643587200000": null
  },
  "Operating Revenue": {
    "1769817600000": 215938000000.0,
    "1738281600000": 130497000000.0,
    "1706659200000": 60922000000.0,
    "1675123200000": 26974000000.0,
    "1643587200000": null
  }
}
```

---

## ✅ `get_key_financial_ratios`

_Financial ratios: P/E, P/B, ROE, debt-to-equity_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "address1": "2788 San Tomas Expressway",
  "city": "Santa Clara",
  "state": "CA",
  "zip": "95051",
  "country": "United States",
  "phone": "408-486-2000",
  "website": "https://www.nvidia.com",
  "industry": "Semiconductors",
  "industryKey": "semiconductors",
  "industryDisp": "Semiconductors",
  "sector": "Technology",
  "sectorKey": "technology",
  "sectorDisp": "Technology",
  "longBusinessSummary": "NVIDIA Corporation, a computing infrastructure company, provides graphics and compute and networking solutions in the United States, Taiwan, China, Hong Kong, and internationally. It operates through Compute & Networking and Graphics segments. The Compute & Networking segment includes its Data Center accelerated computing and networking platforms and artificial intelligence solutions and software and automotive platforms and autonomous and electric vehicle solutions, including software. The Graphics segment offers GeForce GPUs for gaming and PCs; Quadro/NVIDIA RTX GPUs for enterprise workstation graphics; GeForce NOW cloud gaming service; and NVIDIA vGPU software for graphics- virtual desktops and workstations. It also develops standalone software solutions, including NVIDIA AI Enterprise, NVIDIA Omniverse, NVIDIA DRIVE, and other software products. The company's products are used in gaming, professional visualization, data center, and automotive markets. It sells its products to original equipment manufacturers, original device manufacturers, system integrators and distributors, independent software vendors, cloud service providers, add-in board manufacturers, distributors, automotive manufacturers and tier-1 automotive suppliers, and other ecosystem participants. NVIDIA Corporation was incorporated in 1993 and is headquartered in Santa Clara, California.",
  "fullTimeEmployees": 42000,
  "companyOfficers": [
    {
      "maxAge": 1,
      "name": "Mr. Jen-Hsun  Huang",
      "age": 62,
      "title": "Co-Founder, CEO, President & Director",
      "yearBorn": 1963,
      "fiscalYear": 2025,
      "totalPay": 11054945,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Ms. Colette M. Kress",
      "age": 58,
      "title": "Executive VP & CFO",
      "yearBorn": 1967,
      "fiscalYear": 2025,
      "totalPay": 1512641,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Ms. Debora  Shoquist",
      "age": 70,
      "title": "Executive Vice President of Operations",
      "yearBorn": 1955,
      "fiscalYear": 2025,
      "totalPay": 1379071,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Mr. Timothy S. Teter J.D.",
      "age": 58,
      "title": "Executive VP, General Counsel & Secretary",
      "yearBorn": 1967,
      "fiscalYear": 2025,
      "totalPay": 1362989,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Mr. Ajay K. Puri",
      "age": 70,
      "title": "Executive Vice President of Worldwide Field Operations",
      "yearBorn": 1955,
      "fiscalYear": 2025,
      "totalPay": 2313851,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Mr. Chris A. Malachowsky",
      "title": "Co-Founder",
      "fiscalYear": 2025,
      "totalPay": 320000,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Mr. Donald F. Robertson Jr.",
      "age": 56,
      "title": "VP & Chief Accounting Officer",
      "yearBorn": 1969,
      "fiscalYear": 2025,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Prof. William J. Dally Ph.D.",
      "age": 64,
      "title": "Chief Scientist & Senior VP of Research",
      "yearBorn": 1961,
      "fiscalYear": 2025,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Mr. Toshiya  Hari",
      "title": "Vice President of Investor Relations & Strategic Finance",
      "fiscalYear": 2025,
      "exercisedValue": 0,
      "unexercisedValue": 0
    },
    {
      "maxAge": 1,
      "name": "Ms. Mylene  Mangalindan",
      "title": "Vice President of Corporate Communications",
      "fiscalYear": 2025,
      "exercisedValue": 0,
      "unexercisedValue": 0
    }
  ],
  "auditRisk": 5,
  "boardRisk": 9,
  "compensationRisk": 4,
  "shareHolderRightsRisk": 8,
  "overallRisk": 8,
  "governanceEpochDate": 1772323200,
  "compensationAsOfEpochDate": 1767139200,
  "irWebsite": "http://phx.corporate-ir.net/phoenix.zhtml?c=116466&p=irol-IRHome",
  "executiveTeam": [],
  "maxAge": 86400,
  "priceHint": 2,
  "previousClose": 182.373,
  "open": 178.4775,
  "dayLow": 176.92,
  "dayHigh": 180.9,
  "regularMarketPreviousClose": 182.373,
  "regularMarketOpen": 178.4775,
  "regularMarketDayLow": 176.92,
  "regularMarketDayHigh": 180.9,
  "dividendRate": 0.04,
  "dividendYield": 0.02,
  "exDividendDate": 1773187200,
  "payoutRatio": 0.0082,
  "fiveYearAvgDividendYield": 0.05,
  "beta": 2.375,
  "trailingPE": 36.654808,
  "forwardPE": 16.851505,
  "volume": 138429125,
  "regularMarketVolume": 138426492,
  "averageVolume": 175255515,
  "averageVolume10days": 211040200,
  "averageDailyVolume10Day": 211040200,
  "bid": 177.0,
  "ask": 180.34,
  "bidSize": 1,
  "askSize": 2,
  "marketCap": 4374294953984,
  "nonDilutedMarketCap": 4434264000000,
  "fiftyTwoWeekLow": 86.62,
  "fiftyTwoWeekHigh": 212.19,
  "allTimeHigh": 212.19,
  "allTimeLow": 0.033333,
  "priceToSalesTrailing12Months": 20.257168,
  "fiftyDayAverage": 185.7162,
  "twoHundredDayAverage": 175.22015,
  "trailingAnnualDividendRate": 0.04,
  "trailingAnnualDividendYield": 0.0002193307,
  "currency": "USD",
  "tradeable": false,
  "enterpriseValue": 4383120031744,
  "profitMargins": 0.55603004,
  "floatShares": 23330673000,
  "sharesOutstanding": 24300000000,
  "sharesShort": 254311707,
  "sharesShortPriorMonth": 261838673,
  "sharesShortPreviousMonthDate": 1768435200,
  "dateShortInterest": 1770940800,
  "sharesPercentSharesOut": 0.0105,
  "heldPercentInsiders": 0.04354,
  "heldPercentInstitutions": 0.6965,
  "shortRatio": 1.45,
  "shortPercentOfFloat": 0.0109,
  "impliedSharesOutstanding": 24305000000,
  "bookValue": 6.472,
  "priceToBook": 27.808266,
  "lastFiscalYearEnd": 1769299200,
  "nextFiscalYearEnd": 1800835200,
  "mostRecentQuarter": 1769299200,
  "earningsQuarterlyGrowth": 0.945,
  "netIncomeToCommon": 120066998272,
  "trailingEps": 4.91,
  "forwardEps": 10.68006,
  "lastSplitFactor": "10:1",
  "lastSplitDate": 1717977600,
  "enterpriseToRevenue": 20.298,
  "enterpriseToEbitda": 32.899,
  "52WeekChange": 0.5732391,
  "SandP52WeekChange": 0.19097292,
  "lastDividendValue": 0.01,
  "lastDividendDate": 1764806400,
  "quoteType": "EQUITY",
  "currentPrice": 179.975,
  "targetHighPrice": 380.0,
  "targetLowPrice": 140.0,
  "targetMeanPrice": 264.24878,
  "targetMedianPrice": 263.915,
  "recommendationMean": 1.28333,
  "recommendationKey": "strong_buy",
  "numberOfAnalystOpinions": 58,
  "totalCash": 62556000256,
  "totalCashPerShare": 2.574,
  "ebitda": 133230002176,
  "totalDebt": 11411999744,
  "quickRatio": 3.141,
  "currentRatio": 3.905,
  "totalRevenue": 215938007040,
  "debtToEquity": 7.255,
  "revenuePerShare": 8.865,
  "returnOnAssets": 0.51188,
  "returnOnEquity": 1.01485,
  "grossProfits": 153462996992,
  "freeCashflow": 58128998400,
  "operatingCashflow": 102717997056,
  "earningsGrowth": 0.956,
  "revenueGrowth": 0.732,
  "grossMargins": 0.71068,
  "ebitdaMargins": 0.61698,
  "operatingMargins": 0.65024,
  "financialCurrency": "USD",
  "symbol": "NVDA",
  "language": "en-US",
  "region": "US",
  "typeDisp": "Equity",
  "quoteSourceName": "Nasdaq Real Time Price",
  "triggerable": true,
  "customPriceAlertConfidence": "HIGH",
  "exchange": "NMS",
  "messageBoardId": "finmb_32307",
  "exchangeTimezoneName": "America/New_York",
  "exchangeTimezoneShortName": "EST",
  "gmtOffSetMilliseconds": -18000000,
  "market": "us_market",
  "esgPopulated": false,
  "corporateActions": [
    {
      "header": "Dividend",
      "message": "NVDA announced a cash dividend of 0.01$ with an ex-date of Mar. 11, 2026",
      "meta": {
        "eventType": "DIVIDEND",
        "dateEpochMs": 1773205200000,
        "amount": "0.01"
      }
    }
  ],
  "regularMarketTime": 1772567724,
  "shortName": "NVIDIA Corporation",
  "longName": "NVIDIA Corporation",
  "marketState": "REGULAR",
  "priceEpsCurrentYear": 21.820505,
  "fiftyDayAverageChange": -5.741104,
  "fiftyDayAverageChangePercent": -0.03091332,
  "twoHundredDayAverageChange": 4.754944,
  "twoHundredDayAverageChangePercent": 0.027136968,
  "sourceInterval": 15,
  "exchangeDataDelayedBy": 0,
  "prevName": "Usual Stablecoin",
  "nameChangeDate": "2026-03-03",
  "averageAnalystRating": "1.3 - Strong Buy",
  "cryptoTradeable": false,
  "regularMarketChangePercent": -1.3148353,
  "regularMarketPrice": 179.9751,
  "hasPrePostMarketData": true,
  "firstTradeDateMilliseconds": 917015400000,
  "regularMarketChange": -2.3979034,
  "regularMarketDayRange": "176.92 - 180.9",
  "fullExchangeName": "NasdaqGS",
  "averageDailyVolume3Month": 175255515,
  "fiftyTwoWeekLowChange": 93.355095,
  "fiftyTwoWeekLowChangePercent": 1.0777545,
  "fiftyTwoWeekRange": "86.62 - 212.19",
  "fiftyTwoWeekHighChange": -32.214905,
  "fiftyTwoWeekHighChangePercent": -0.15182103,
  "fiftyTwoWeekChangePercent": 57.32391,
  "dividendDate": 1766707200,
  "earningsTimestamp": 1779310800,
  "earningsTimestampStart": 1779310800,
  "earningsTimestampEnd": 1779310800,
  "earningsCallTimestampStart": 1772056800,
  "earningsCallTimestampEnd": 1772056800,
  "isEarningsDateEstimate": false,
  "epsTrailingTwelveMonths": 4.91,
  "epsForward": 10.68006,
  "epsCurrentYear": 8.24798,
  "displayName": "NVIDIA",
  "trailingPegRatio": 1.1073
}
```

---

## ✅ `get_analyst_recommendations`

_Analyst recommendations: buy/hold/sell counts_

### Input

```json
{
  "symbol": "NVDA"
}
```

### Output

```json
{
  "0": {
    "period": "0m",
    "strongBuy": 9,
    "buy": 48,
    "hold": 2,
    "sell": 1,
    "strongSell": 0
  },
  "1": {
    "period": "-1m",
    "strongBuy": 11,
    "buy": 47,
    "hold": 2,
    "sell": 1,
    "strongSell": 0
  },
  "2": {
    "period": "-2m",
    "strongBuy": 12,
    "buy": 48,
    "hold": 3,
    "sell": 1,
    "strongSell": 0
  },
  "3": {
    "period": "-3m",
    "strongBuy": 11,
    "buy": 49,
    "hold": 3,
    "sell": 1,
    "strongSell": 0
  }
}
```

---

## ✅ `get_company_news`

_Recent company news (3 stories)_

### Input

```json
{
  "symbol": "NVDA",
  "num_stories": 3
}
```

### Output

```json
[
  {
    "id": "19cd1080-a43d-4393-8ed1-77d2b30d3322",
    "content": {
      "id": "19cd1080-a43d-4393-8ed1-77d2b30d3322",
      "contentType": "STORY",
      "title": "Earnings live: Best Buy stock jumps despite softer holiday demand, Target stock rises",
      "description": "",
      "summary": "The S&P 500 was on track for double-digit earnings growth, with more than half of companies having reported Q4 results so far.",
      "pubDate": "2026-03-03T12:24:51Z",
      "displayTime": "2026-03-03T19:19:04Z",
      "isHosted": true,
      "bypassModal": false,
      "previewUrl": null,
      "thumbnail": {
        "originalUrl": "https://s.yimg.com/os/creatr-uploaded-images/2026-02/f16a6480-16fb-11f1-b5fb-f73252b7ef26",
        "originalWidth": 6000,
        "originalHeight": 4000,
        "caption": "",
        "resolutions": [
          {
            "url": "https://s.yimg.com/uu/api/res/1.2/R.zQ6wfFoR4jiSVHyPvofQ--~B/aD00MDAwO3c9NjAwMDthcHBpZD15dGFjaHlvbg--/https://s.yimg.com/os/creatr-uploaded-images/2026-02/f16a6480-16fb-11f1-b5fb-f73252b7ef26",
            "width": 6000,
            "height": 4000,
            "tag": "original"
          },
          {
            "url": "https://s.yimg.com/uu/api/res/1.2/.wC3iZoqW1jJJwJdvYFInw--~B/Zmk9c3RyaW07aD0xMjg7dz0xNzA7YXBwaWQ9eXRhY2h5b24-/https://s.yimg.com/os/creatr-uploaded-images/2026-02/f16a6480-16fb-11f1-b5fb-f73252b7ef26",
            "width": 170,
            "height": 128,
            "tag": "170x128"
          }
        ]
      },
      "provider": {
        "displayName": "Yahoo Finance",
        "url": "http://finance.yahoo.com/"
      },
      "canonicalUrl": {
        "url": "https://finance.yahoo.com/news/live/earnings-live-best-buy-stock-jumps-despite-softer-holiday-demand-target-stock-rises-122451670.html",
        "site": "finance",
        "region": "US",
        "lang": "en-US"
      },
      "clickThroughUrl": {
        "url": "https://finance.yahoo.com/news/live/earnings-live-best-buy-stock-jumps-despite-softer-holiday-demand-target-stock-rises-122451670.html",
        "site": "finance",
        "region": "US",
        "lang": "en-US"
      },
      "metadata": {
        "editorsPick": true
      },
      "finance": {
        "premiumFinance": {
          "isPremiumNews": false,
          "isPremiumFreeNews": false
        }
      },
      "storyline": {
        "storylineItems": [
          {
            "content": {
              "id": "47322c07-a462-46eb-946b-659cf1d2a811",
              "contentType": "STORY",
              "isHosted": true,
              "title": "Tech stocks today: OpenAI makes changes to military contract, Amazon data centers struck in Middle East warfare",
              "thumbnail": {
                "originalUrl": "https://s.yimg.com/os/creatr-uploaded-images/2023-07/646901d0-21b3-11ee-bffa-743947f3f0fe",
                "originalWidth": 8451,
                "originalHeight": 5634,
                "caption": "",
                "resolutions": null
              },
              "provider": {
                "displayName": "Yahoo Finance",
                "sourceId": "yahoofinance.com"
              },
              "previewUrl": null,
              "providerContentUrl": "",
              "canonicalUrl": {
                "url": "https://finance.yahoo.com/news/live/tech-stocks-today-openai-makes-changes-to-military-contract-amazon-data-centers-struck-in-middle-east-warfare-133637453.html"
              },
              "clickThroughUrl": {
                "url": "https://finance.yahoo.com/news/live/tech-stocks-today-openai-makes-changes-to-military-contract-amazon-data-centers-struck-in-middle-east-warfare-133637453.html"
              }
            }
          },
          {
            "content": {
              "id": "0b4d82a9-3f6c-3047-942a-ea15ba232eb2",
              "contentType": "VIDEO",
              "isHosted": true,
              "title": "Nvidia\u2013Coherent deal, Paramount+ to be combined with HBO Max",
              "thumbnail": {
                "originalUrl": "https://s.yimg.com/os/creatr-uploaded-images/2026-02/f8831f40-167a-11f1-a4ef-214be70ba01d",
                "originalWidth": 6128,
                "originalHeight": 3450,
                "caption": "",
                "resolutions": null
              },
              "provider": {
                "displayName": "Yahoo Finance Video",
                "sourceId": "video.yahoofinance.com"
              },
              "previewUrl": null,
              "providerContentUrl": "",
              "canonicalUrl": {
                "url": "https://finance.yahoo.com/video/nvidia-coherent-deal-paramount-combined-210151599.html"
              },
              "clickThroughUrl": {
                "url": "https://finance.yahoo.com/video/nvidia-coherent-deal-paramount-combined-210151599.html"
              }
            }
          }
        ]
      }
    }
  },
  {
    "id": "afb3f01b-9ce6-3e7d-84ad-fa66ad89624b",
    "content": {
      "id": "afb3f01b-9ce6-3e7d-84ad-fa66ad89624b",
      "contentType": "STORY",
      "title": "9 Years Ago, Warren Buffett Predicted This Investment Would Pay Off: Here's How It's Doing",
      "description": "",
      "summary": "Berkshire Hathaway's GM investment made the conglomerate some money, but it could have been a lot more profitable.",
      "pubDate": "2026-03-03T19:50:00Z",
      "displayTime": "2026-03-03T19:50:00Z",
      "isHosted": true,
      "bypassModal": false,
      "previewUrl": null,
      "thumbnail": {
        "originalUrl": "https://media.zenfs.com/en/motleyfool.com/c08d9db0220598dca70d100f1603de60",
        "originalWidth": 1400,
        "originalHeight": 789,
        "caption": "An automobile assembly line.",
        "resolutions": [
          {
            "url": "https://s.yimg.com/uu/api/res/1.2/3nZUhMaNS5qdk6G9Lf94Dw--~B/aD03ODk7dz0xNDAwO2FwcGlkPXl0YWNoeW9u/https://media.zenfs.com/en/motleyfool.com/c08d9db0220598dca70d100f1603de60",
            "width": 1400,
            "height": 789,
            "tag": "original"
          },
          {
            "url": "https://s.yimg.com/uu/api/res/1.2/rPt1HIvHDHke3fwBAwwTzw--~B/Zmk9c3RyaW07aD0xMjg7dz0xNzA7YXBwaWQ9eXRhY2h5b24-/https://media.zenfs.com/en/motleyfool.com/c08d9db0220598dca70d100f1603de60",
            "width": 170,
            "height": 128,
            "tag": "170x128"
          }
        ]
      },
      "provider": {
        "displayName": "Motley Fool",
        "url": "http://www.fool.com/"
      },
      "canonicalUrl": {
        "url": "https://www.fool.com/investing/2026/03/03/9-years-ago-warren-buffett-predicted-this-investme/",
        "site": "finance",
        "region": "US",
        "lang": "en-US"
      },
      "clickThroughUrl": {
        "url": "https://finance.yahoo.com/news/9-years-ago-warren-buffett-195000978.html",
        "site": "finance",
        "region": "US",
        "lang": "en-US"
      },
      "metadata": {
        "editorsPick": false
      },
      "finance": {
        "premiumFinance": {
          "isPremiumNews": false,
          "isPremiumFreeNews": false
        }
      },
      "storyline": null
    }
  },
  {
    "id": "f0000287-d212-366b-ae65-16900288439b",
    "content": {
      "id": "f0000287-d212-366b-ae65-16900288439b",
      "contentType": "STORY",
      "title": "Here's Everything Investors Need to Know About Oklo's Meta Deal",
      "description": "",
      "summary": "Oklo is working with tech giant Meta Platforms to build a nuclear power plant, but this deal is really about funding.",
      "pubDate": "2026-03-03T19:49:00Z",
      "displayTime": "2026-03-03T19:49:00Z",
      "isHosted": true,
      "bypassModal": false,
      "previewUrl": null,
      "thumbnail": {
        "originalUrl": "https://media.zenfs.com/en/motleyfool.com/bbff04b1ce422c1ad6d04366e28c6f75",
        "originalWidth": 1400,
        "originalHeight": 934,
        "caption": "A happy person with money raining down around them.",
        "resolutions": [
          {
            "url": "https://s.yimg.com/uu/api/res/1.2/LzOYCotx0hwGlHx5i0_CeA--~B/aD05MzQ7dz0xNDAwO2FwcGlkPXl0YWNoeW9u/https://media.zenfs.com/en/motleyfool.com/bbff04b1ce422c1ad6d04366e28c6f75",
            "width": 1400,
            "height": 934,
            "tag": "original"
          },
          {
            "url": "https://s.yimg.com/uu/api/res/1.2/0pB3YpJX28.0F5DivhFlpg--~B/Zmk9c3RyaW07aD0xMjg7dz0xNzA7YXBwaWQ9eXRhY2h5b24-/https://media.zenfs.com/en/motleyfool.com/bbff04b1ce422c1ad6d04366e28c6f75",
            "width": 170,
            "height": 128,
            "tag": "170x128"
          }
        ]
      },
      "provider": {
        "displayName": "Motley Fool",
        "url": "http://www.fool.com/"
      },
      "canonicalUrl": {
        "url": "https://www.fool.com/investing/2026/03/03/investors-need-to-know-about-oklo-meta-deal/",
        "site": "finance",
        "region": "US",
        "lang": "en-US"
      },
      "clickThroughUrl": {
        "url": "https://finance.yahoo.com/news/heres-everything-investors-know-oklos-194900865.html",
        "site": "finance",
        "region": "US",
        "lang": "en-US"
      },
      "metadata": {
        "editorsPick": false
      },
      "finance": {
        "premiumFinance": {
          "isPremiumNews": false,
          "isPremiumFreeNews": false
        }
      },
      "storyline": null
    }
  }
]
```

---

## ✅ `get_technical_indicators`

_Technical indicators: OHLCV with volume (1 month)_

### Input

```json
{
  "symbol": "NVDA",
  "period": "1mo"
}
```

### Output

```json
{
  "1770094800000": {
    "Open": 186.2400054932,
    "High": 186.2700042725,
    "Low": 176.2299957275,
    "Close": 180.3399963379,
    "Volume": 204019600,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770181200000": {
    "Open": 179.4600067139,
    "High": 179.5800018311,
    "Low": 171.9100036621,
    "Close": 174.1900024414,
    "Volume": 207014100,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770267600000": {
    "Open": 174.9299926758,
    "High": 176.8200073242,
    "Low": 171.0299987793,
    "Close": 171.8800048828,
    "Volume": 206312900,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770354000000": {
    "Open": 176.6900024414,
    "High": 187.0,
    "Low": 174.6000061035,
    "Close": 185.4100036621,
    "Volume": 231346200,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770613200000": {
    "Open": 184.2599945068,
    "High": 193.6600036621,
    "Low": 183.9499969482,
    "Close": 190.0399932861,
    "Volume": 196387400,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770699600000": {
    "Open": 191.3800048828,
    "High": 192.4799957275,
    "Low": 188.1199951172,
    "Close": 188.5399932861,
    "Volume": 136764800,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770786000000": {
    "Open": 192.4499969482,
    "High": 193.2599945068,
    "Low": 188.7700042725,
    "Close": 190.0500030518,
    "Volume": 144192700,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770872400000": {
    "Open": 193.0299987793,
    "High": 193.6100006104,
    "Low": 186.5099945068,
    "Close": 186.9400024414,
    "Volume": 189932500,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1770958800000": {
    "Open": 187.4799957275,
    "High": 187.5,
    "Low": 181.5899963379,
    "Close": 182.8099975586,
    "Volume": 161888000,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771304400000": {
    "Open": 181.75,
    "High": 187.1499938965,
    "Low": 179.1799926758,
    "Close": 184.9700012207,
    "Volume": 162276900,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771390800000": {
    "Open": 188.75,
    "High": 190.3699951172,
    "Low": 186.7599945068,
    "Close": 187.9799957275,
    "Volume": 164749100,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771477200000": {
    "Open": 187.0599975586,
    "High": 188.4299926758,
    "Low": 185.6600036621,
    "Close": 187.8999938965,
    "Volume": 126554500,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771563600000": {
    "Open": 186.5700073242,
    "High": 190.3300018311,
    "Low": 185.9400024414,
    "Close": 189.8200073242,
    "Volume": 178422300,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771822800000": {
    "Open": 191.3999938965,
    "High": 193.9499969482,
    "Low": 189.5800018311,
    "Close": 191.5500030518,
    "Volume": 171584800,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771909200000": {
    "Open": 191.4900054932,
    "High": 193.7700042725,
    "Low": 187.3999938965,
    "Close": 192.8500061035,
    "Volume": 175123600,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1771995600000": {
    "Open": 194.4499969482,
    "High": 197.6300048828,
    "Low": 193.7899932861,
    "Close": 195.5599975586,
    "Volume": 250637100,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772082000000": {
    "Open": 194.2700042725,
    "High": 194.2899932861,
    "Low": 184.3200073242,
    "Close": 184.8899993896,
    "Volume": 360807900,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772168400000": {
    "Open": 181.25,
    "High": 182.5899963379,
    "Low": 176.3800048828,
    "Close": 177.1900024414,
    "Volume": 311636500,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772427600000": {
    "Open": 175.0099945068,
    "High": 183.4600067139,
    "Low": 174.6399993896,
    "Close": 182.4799957275,
    "Volume": 209095300,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  },
  "1772514000000": {
    "Open": 178.4774932861,
    "High": 180.8999938965,
    "Low": 176.9199981689,
    "Close": 179.9750061035,
    "Volume": 138429125,
    "Dividends": 0.0,
    "Stock Splits": 0.0
  }
}
```

---
