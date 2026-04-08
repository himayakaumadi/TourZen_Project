import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings

warnings.filterwarnings('ignore')

# ---------------------------------------------------------
# 1. LOAD AND PREPROCESS DATA
# ---------------------------------------------------------
DATA_PATH = r"C:\Users\DELL\Downloads\tourzen_app\data_cleaned\national_monthly_arrivals_fixed.csv"
df = pd.read_csv(DATA_PATH)

# Convert Month to Number
month_map = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12
}
df['MONTH_NUM'] = df['MONTH'].map(month_map)

# Focus on "Modern Era" (Post-July 2022) for high-accuracy evaluation
# This matches the core forecasting engine logic of TourZen
df_modern = df[((df['YEAR'] == 2022) & (df['MONTH_NUM'] >= 7)) | (df['YEAR'] > 2022)].copy()
df_modern = df_modern.sort_values(['YEAR', 'MONTH_NUM'])

# Features for Traditional ML
X = df_modern[['YEAR', 'MONTH_NUM']]
y = df_modern['TOTAL_ARRIVALS']

# ---------------------------------------------------------
# 2. TRAIN MODELS & PREDICT
# ---------------------------------------------------------

results = {}

# --- Model A: Linear Regression ---
lr = LinearRegression()
lr.fit(X, y)
y_pred_lr = lr.predict(X)
results['Linear Regression'] = y_pred_lr

# --- Model B: Random Forest ---
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X, y)
y_pred_rf = rf.predict(X)
results['Random Forest'] = y_pred_rf

# --- Model C: Facebook Prophet (The TourZen Engine) ---
# Prophet requires ds and y, and we use log normalization for max accuracy
prophet_df = pd.DataFrame({
    'ds': pd.to_datetime(df_modern['YEAR'].astype(str) + '-' + df_modern['MONTH_NUM'].astype(str) + '-01'),
    'y': np.log1p(df_modern['TOTAL_ARRIVALS'])
})

m = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    seasonality_mode='multiplicative'
)
m.fit(prophet_df)
forecast = m.predict(prophet_df)
y_pred_prophet = np.expm1(forecast['yhat'])
results['Facebook Prophet'] = y_pred_prophet

# ---------------------------------------------------------
# 3. CALCULATE METRICS
# ---------------------------------------------------------
metrics_list = []
for name, y_pred in results.items():
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    metrics_list.append({
        'Model': name,
        'MAE': mae,
        'RMSE': rmse,
        'R2': r2
    })

metrics_df = pd.DataFrame(metrics_list)
print("\n--- MODEL COMPARISON SUMMARY ---")
print(metrics_df.to_string(index=False))

# ---------------------------------------------------------
# 4. VISUALIZATION 1: ACTUAL VS PREDICTED (Model Evaluation)
# ---------------------------------------------------------
plt.figure(figsize=(15, 5))
sns.set(style="whitegrid")

for i, (name, y_pred) in enumerate(results.items()):
    plt.subplot(1, 3, i+1)
    
    # Metrics for title
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    
    # Plot Scatter
    plt.scatter(y, y_pred, alpha=0.6, edgecolors='w', s=60, color='#3B82F6')
    
    # Diagonal line
    max_val = max(y.max(), y_pred.max())
    plt.plot([0, max_val], [0, max_val], '--', color='#EF4444', lw=2)
    
    plt.title(f"{name}\nMAE: {mae:.2f} | R2: {r2:.4f}", fontsize=12, fontweight='bold')
    plt.xlabel("Actual Arrivals", fontsize=10)
    plt.ylabel("Predicted Arrivals", fontsize=10)
    plt.tight_layout()

plt.savefig('model_evaluation_scatter.png', dpi=300, bbox_inches='tight')
print("\nSaved: model_evaluation_scatter.png")

# ---------------------------------------------------------
# 5. VISUALIZATION 2: RESIDUALS (Model Selection)
# ---------------------------------------------------------
plt.figure(figsize=(15, 5))

for i, (name, y_pred) in enumerate(results.items()):
    plt.subplot(1, 3, i+1)
    
    # Robust residual calculation for both Series and numpy arrays
    y_actual = np.asarray(y)
    y_predict = np.asarray(y_pred)
    residuals = y_actual - y_predict
    
    # 1. Plot the histogram (Counts)
    counts, bins, _ = plt.hist(residuals, color='#10B981', bins=15, alpha=0.5, label='Frequency')
    
    # 2. Manually calculate and scale the KDE curve to match "Peak Frequency"
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(residuals)
    x_range = np.linspace(min(residuals), max(residuals), 500)
    density = kde(x_range)
    
    # Scaling factor logic: ensure the peak of the KDE matches the highest bar
    max_freq = max(counts)
    max_density = max(density)
    scale_factor = max_freq / max_density
    scaled_density = density * scale_factor
    
    # 3. Plot the scaled curve
    plt.plot(x_range, scaled_density, color='#059669', lw=2.5)
    
    plt.title(f"{name} Residuals", fontsize=12, fontweight='bold')
    plt.xlabel("Residual (Error)", fontsize=10)
    plt.ylabel("Frequency", fontsize=10)
    plt.tight_layout()

plt.savefig('model_selection_residuals.png', dpi=300, bbox_inches='tight')
print("Saved: model_selection_residuals.png")

plt.show()
