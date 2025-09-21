# Simple online regressor to model latency from features
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import pandas as pd


X = pd.read_parquet('data/features/latest_features.parquet')
y = pd.read_parquet('data/order_events/*/events_*.parquet')['latency_ms'][:len(X)].values


model = make_pipeline(StandardScaler(with_mean=False), SGDRegressor(loss='huber', max_iter=1, learning_rate='optimal'))
model.fit(X, y)
# Save via joblib if desired
print('Trained on', len(X), 'samples')
