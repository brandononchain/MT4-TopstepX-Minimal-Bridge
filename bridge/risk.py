import yaml


class RiskManager:
def __init__(self, path='./bridge/risk_rules.yaml'):
with open(path,'r') as f:
self.cfg = yaml.safe_load(f)


def size(self, resolved, intent):
# If explicit qty provided by EA, use it
qty = intent.get('qty') or intent.get('quantity')
if qty: return max(1, int(qty))
risk_usd = float(self.cfg.get('per_trade_risk_usd', 100))
price = float(intent.get('price') or 0)
sl = float(intent.get('sl') or 0)
dist = abs(price - sl)
ticks = max(self.cfg.get('min_distance_ticks',2), dist / resolved.tick_size if dist>0 else 0)
if ticks <= 0: return 1
contracts = int(max(1, risk_usd / (ticks * resolved.tick_value)))
# per-root cap
cap = self.cfg.get('max_position_per_root', {}).get(resolved.root, 3)
return min(contracts, cap)
