# README (usage quickstart)

pip install -r bridge/requirements.txt

Edit bridge/config.yaml (tenant URL, API key, account).

Verify Gold mapping in symbol_map.yaml (XAUUSD → root GC, active months, tick specs).

Run the bridge: python bridge/tsx_bridge.py

Compile/attach TSX_Sender.mq4 to your MT4 chart. Place a test order on XAUUSD.

Check console log + bridge/data/order_events/YYYYMMDD/events_*.parquet for records.

Notes on GC contract months

Configured active months: G, J, M, Q, Z (common GC). The router rolls to next month when ≤ 2 business days left in the current month.

Adjust in symbol_map.yaml if your TSX tenant expects a different month ladder.

Next steps (when fills streaming is available)

Enrich dataset with parent fill price, bracket attach times, and exec venue latencies.

Compute realized slippage (fill − intent price) as learning target.

Extend features with spread, depth, vol-of-vol, and clock time.
