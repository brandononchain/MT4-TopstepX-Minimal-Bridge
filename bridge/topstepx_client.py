import requests, yaml


class TopstepXClient:
def __init__(self, cfg_path='./bridge/config.yaml'):
self.cfg = yaml.safe_load(open(cfg_path))
self.base = self.cfg['projectx']['base_url'].rstrip('/')
self.key = self.cfg['projectx']['api_key']
self.account = self.cfg['projectx']['account_id']


def _headers(self):
return { 'Authorization': f'Bearer {self.key}', 'Content-Type':'application/json' }


def place_order(self, symbol, side, qty, tif='GTC', tp=None, sl=None):
payload = {
'accountId': self.account,
'symbol': symbol,
'side': side,
'quantity': int(qty),
'type': 'MARKET',
'timeInForce': tif,
'bracket': {
'takeProfit': None if tp is None else { 'type':'LIMIT', 'offsetTicks': None },
'stopLoss' : None if sl is None else { 'type':'STOP', 'offsetTicks': None },
'linkage': 'OCO'
}
}
r = requests.post(f"{self.base}/v1/orders", json=payload, headers=self._headers(), timeout=3)
if r.status_code >= 300:
raise RuntimeError(f"TopstepX error {r.status_code}: {r.text}")
return r.json()
