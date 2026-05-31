# Swing Trade Setup Prompt

Identify swing trade candidates with at least 10% upside over a 5-week swing horizon.

## Screening Criteria

### Technical Setup
- Price is pulling back into or bouncing from a key support area, such as a major moving average, trendline, or prior consolidation zone.
- Daily RSI is between 40 and 60, indicating a momentum reset without a confirmed breakdown.
- MACD is showing a bullish crossover or a positive momentum inflection.
- Volume has expanded over the last 1-3 sessions, indicating potential institutional participation.
- The stock remains in a confirmed daily uptrend, defined by higher highs and higher lows.

### Fundamental and Event Filters
- Market capitalization is between $500M and $20B.
- (SKIP_NOW) No major earnings report is scheduled within the next 2 weeks.
- (SKIP_NOW) There is a recent bullish catalyst, such as an analyst upgrade, earnings beat, sector tailwind, or other material news.

### Risk and Trade Construction
- Average daily volume exceeds 500K shares.
- Entry must have a clearly defined stop-loss 3-5% below the proposed entry zone.
- Minimum reward-to-risk ratio is 2:1.

## Required Output
Return a ranked list of candidates with the following fields:
- Ticker
- Current price
- Entry zone
- Price target
- Stop-loss
- Reward-to-risk ratio
- Setup rationale
- Relevant catalyst

Rank candidates by the strongest technical confluence, cleanest trend-continuation structure, and best reward-to-risk profile.
