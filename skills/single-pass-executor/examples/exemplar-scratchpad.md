# Exemplar: Single-Pass Scratchpad & Execution

## Example Task: Safe Currency Converter Function

### Scratchpad Section (Emitted before code generation)

```markdown
### 1. Contracts & Types
- Inputs:
  - `amount`: float, MUST be >= 0.0
  - `source_curr`: str, ISO 4217, exactly 3 uppercase chars
  - `target_curr`: str, ISO 4217, exactly 3 uppercase chars
  - `rates`: Dict[str, float], MUST contain source and target rates relative to base
- Outputs:
  - float rounded to 4 decimal places
- Exceptions:
  - ValueError on negative amount or missing rate

### 2. Failure Mode Analysis
1. Target currency missing from rates dictionary -> KeyError if unchecked.
2. Source rate is zero -> ZeroDivisionError.
3. Lowercase currency codes passed -> Lookup failure.

### 3. Implementation Invariants
- Normalize currency codes with `.upper().strip()`.
- Validate rates exist before performing division.
- Guard against zero division explicitly.
```

### Synthesis Section (Clean production artifact)

```python
from typing import Dict


def convert_currency(amount: float, source: str, target: str, rates: Dict[str, float]) -> float:
    if amount < 0:
        raise ValueError("Amount MUST be non-negative.")

    s = source.strip().upper()
    t = target.strip().upper()

    if s not in rates:
        raise ValueError(f"Missing exchange rate for source currency: {s}")
    if t not in rates:
        raise ValueError(f"Missing exchange rate for target currency: {t}")

    base_rate = rates[s]
    if base_rate <= 0:
        raise ValueError(f"Invalid non-positive exchange rate for {s}: {base_rate}")

    converted = (amount / base_rate) * rates[t]
    return round(converted, 4)
```
