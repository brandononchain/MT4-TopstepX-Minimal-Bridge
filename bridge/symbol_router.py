from datetime import datetime, timedelta
import yaml, os


MONTH_CODES = "FGHJKMNQUVXZ" # Jan..Dec


class Resolved:
def __init__(self, root, contracted, tick_size, tick_value):
self.root = root
self.contracted = contracted
self.tick_size = tick_size
self.tick_value = tick_value


class SymbolRouter:
def __init__(self, path='./bridge/symbol_map.yaml'):
with open(path,'r') as f:
self.map = yaml.safe_load(f)


def _business_days_before_month_end(self, today):
# Count business days remaining this month
d = today
end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
days = 0
t = today
while t <= end:
if t.weekday() < 5: days += 1
t += timedelta(days=1)
return days


def _front_or_next(self, root_cfg):
now = datetime.utcnow()
months = root_cfg.get('active_months')
if months:
# pick nearest active month ≥ current month
m = now.month
for step in range(0, 24):
cand = (m + step - 1) % 12
code = MONTH_CODES[cand]
if code in months:
# simple roll: if within 2 business days of month end → choose next eligible month
if root_cfg.get('roll_rule') == 'FRONT_NEXT_2BD':
if self._business_days_before_month_end(now) <= 2:
# choose next eligible beyond code
for step2 in range(1, 24):
cand2 = (m + step + step2 - 1) % 12
code2 = MONTH_CODES[cand2]
if code2 in months:
code = code2
break
year = str(now.year)[-1]
return f"{root_cfg['root']}{code}{year}"
# default to next calendar month if no active_months
code = MONTH_CODES[(now.month) % 12]
year = str(now.year)[-1]
return f"{root_cfg['root']}{code}{year}"


def resolve(self, mt_symbol: str) -> Resolved:
sym = mt_symbol.upper()
cfg = self.map.get(sym)
if not cfg:
# passthrough (already a futures root like GC/MNQ/etc.)
root = sym
tick_size = 0.25
tick_value = 5.0
contracted = f"{root}{MONTH_CODES[(datetime.utcnow().month)%12]}{str(datetime.utcnow().year)[-1]}"
return Resolved(root, contracted, tick_size, tick_value)
contracted = self._front_or_next(cfg)
return Resolved(cfg['root'], contracted, cfg['tick_size'], cfg['tick_value'])
