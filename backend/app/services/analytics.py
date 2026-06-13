"""
Analytics and Aggregation Service.
Utilizes pandas for grouping, resampling, and rolling averages, preserving volatility and detail.
"""
import pandas as pd
import numpy as np

def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Group and sort data daily, calculating basic metrics."""
    if df.empty:
        return df
    
    df_temp = df.copy()
    df_temp['sales_date'] = pd.to_datetime(df_temp['sales_date'])
    
    daily = df_temp.groupby('sales_date').agg({
        'revenue': 'sum',
        'profit': 'sum',
        'quantity_sold': 'sum'
    }).reset_index()
    
    daily['avg_order_value'] = np.where(
        daily['quantity_sold'] > 0,
        daily['revenue'] / daily['quantity_sold'],
        0.0
    )
    daily['sales_date'] = daily['sales_date'].dt.strftime('%Y-%m-%d')
    return daily.sort_values('sales_date')

def aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily data weekly (Monday as start of week)."""
    if df.empty:
        return df
        
    df_temp = df.copy()
    df_temp['sales_date'] = pd.to_datetime(df_temp['sales_date'])
    
    # Resample weekly and sum metrics
    weekly = df_temp.set_index('sales_date').resample('W-MON').agg({
        'revenue': 'sum',
        'profit': 'sum',
        'quantity_sold': 'sum'
    }).reset_index()
    
    weekly['avg_order_value'] = np.where(
        weekly['quantity_sold'] > 0,
        weekly['revenue'] / weekly['quantity_sold'],
        0.0
    )
    weekly['sales_date'] = weekly['sales_date'].dt.strftime('%Y-%m-%d')
    return weekly.sort_values('sales_date')

def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily data monthly (Month Start)."""
    if df.empty:
        return df
        
    df_temp = df.copy()
    df_temp['sales_date'] = pd.to_datetime(df_temp['sales_date'])
    
    # Resample monthly and sum metrics
    monthly = df_temp.set_index('sales_date').resample('MS').agg({
        'revenue': 'sum',
        'profit': 'sum',
        'quantity_sold': 'sum'
    }).reset_index()
    
    monthly['avg_order_value'] = np.where(
        monthly['quantity_sold'] > 0,
        monthly['revenue'] / monthly['quantity_sold'],
        0.0
    )
    monthly['sales_date'] = monthly['sales_date'].dt.strftime('%Y-%m-%d')
    return monthly.sort_values('sales_date')

def apply_rolling_average(df: pd.DataFrame, column: str, window: int) -> pd.Series:
    """
    Computes a rolling average for the specified column and window.
    Uses min_periods=1 to preserve volatility at the boundaries and avoid flat-lining/dropoffs.
    """
    if df.empty or column not in df.columns:
        return pd.Series(dtype='float64')
    return df[column].rolling(window=window, min_periods=1).mean()
