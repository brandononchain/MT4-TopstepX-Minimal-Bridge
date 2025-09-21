from http.server import BaseHTTPRequestHandler, HTTPServer
import json, yaml, time
from symbol_router import SymbolRouter
from risk import RiskManager
from datastore import DataStore
from topstepx_client import TopstepXClient


CFG = yaml.safe_load(open('./bridge/config.yaml'))


class Bridge:
def __init__(self):
self.router = SymbolRouter('./bridge/symbol_map.yaml')
self.risk = RiskManager('./bridge/risk_rules.yaml')
self.ds = DataStore(CFG['logging']['data_dir'])
self.client = TopstepXClient('./bridge/config.yaml')


def handle(self, intent: dict):
t0 = time.time()
res = self.router.resolve(intent['symbol'])
qty = self.risk.size(res, intent)
order_resp = self.client.place_order(
symbol=res.contracted,
side=intent['side'].upper(),
qty=qty,
tif=CFG['routing']['time_in_force'],
tp=intent.get('tp'), sl=intent.get('sl')
)
latency_ms = int((time.time()-t0)*1000)
record = {
'source':'MT4',
'mt_symbol': intent['symbol'],
'mapped_root': res.root,
'fut_symbol': res.contracted,
'side': intent['side'].upper(),
'price': intent.get('price'),
'sl': intent.get('sl'),
'tp': intent.get('tp'),
'qty': qty,
'latency_ms': latency_ms,
'order_id': order_resp.get('orderId') if isinstance(order_resp, dict) else None
}
self.ds.append(CFG['ml']['topic'], record)
return { 'ok': True, 'latency_ms': latency_ms, 'mapped': res.contracted, 'qty': qty, 'order': order_resp }


BRIDGE = Bridge()


class H(BaseHTTPRequestHandler):
def _send(self, code, obj):
self.send_response(code)
self.send_header('Content-Type','application/json')
self.end_headers()
self.wfile.write(json.dumps(obj).encode())


def do_GET(self):
if self.path.startswith('/health'):
return self._send(200, {'ok':True})
return self._send(404, {'error':'not found'})


def do_POST(self):
if self.path != '/intent':
return self._send(404, {'error':'not found'})
ln = int(self.headers.get('Content-Length','0'))
payload = json.loads(self.rfile.read(ln) or '{}')
try:
resp = BRIDGE.handle(payload)
return self._send(200, resp)
except Exception as e:
return self._send(500, {'ok':False, 'error': str(e)})


if __name__ == '__main__':
srv = HTTPServer((CFG['server']['host'], CFG['server']['port']), H)
print(f"Bridge up http://{CFG['server']['host']}:{CFG['server']['port']}")
srv.serve_forever()
