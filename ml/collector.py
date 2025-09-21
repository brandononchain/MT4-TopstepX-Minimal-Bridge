import pandas as pd, os, glob


def load_events(base='data/order_events'):
days = sorted(glob.glob(os.path.join(base,'*','events_*.parquet')))
dfs = [pd.read_parquet(p) for p in days]
return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def build_features(df: pd.DataFrame):
if df.empty: return df
df['hourofday'] = pd.to_datetime(df['ts']).dt.hour
df['is_buy'] = (df['side']=='BUY').astype(int)
df['root_GC'] = (df['mapped_root']=='GC').astype(int)
# Target candidates: latency_ms now; later: realized slippage from fills (add when available)
feats = df[['hourofday','is_buy','root_GC','qty']].copy()
y = df['latency_ms'].values
return feats, y


if __name__=='__main__':
df = load_events()
if df.empty:
print('No data yet. Place trades to collect.'); exit()
X,y = build_features(df)
print('Feature shape:', X.shape, 'Target shape:', y.shape)
X.to_parquet('data/features/latest_features.parquet', index=False)
