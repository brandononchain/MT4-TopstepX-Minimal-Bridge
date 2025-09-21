import os, time, json
from datetime import datetime
import pandas as pd


class DataStore:
def __init__(self, data_dir='data'):
self.base = data_dir
os.makedirs(self.base, exist_ok=True)


def _path(self, topic):
day = datetime.utcnow().strftime('%Y%m%d')
d = os.path.join(self.base, topic, day)
os.makedirs(d, exist_ok=True)
return os.path.join(d, f"events_{day}.parquet")


def append(self, topic, record: dict):
record = {**record, 'ts': datetime.utcnow().isoformat()}
path = self._path(topic)
df = pd.DataFrame([record])
if os.path.exists(path):
# append by concatenating (small volumes). For heavy volume, switch to Delta/duckdb.
old = pd.read_parquet(path)
pd.concat([old, df], ignore_index=True).to_parquet(path, index=False)
else:
df.to_parquet(path, index=False)
