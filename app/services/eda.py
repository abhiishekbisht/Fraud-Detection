import pandas as pd
import numpy as np
from typing import Dict, Any, List

def compute_eda(df: pd.DataFrame, target_col: str = "Class", amount_col: str = "Amount") -> Dict[str, Any]:
    """
    Computes EDA metrics on the dataset DataFrame and returns them as a JSON-serializable dict.
    
    Metrics included:
    - class_balance: count and percentage for each class
    - amount_stats: mean, median, min, max, std, and percentiles (25, 50, 75, 90, 95, 99) of Amount by class
    - correlation_matrix: Pearson correlation matrix of all numeric columns
    - top_features: top 10 features ranked by absolute difference in means between classes
    """
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset columns: {list(df.columns)}")
    
    # 1. Class Balance
    class_counts = df[target_col].value_counts().to_dict()
    total_count = len(df)
    
    # Convert keys to strings for JSON compliance and handle 0/1 labels
    # We map 0 -> "legit" and 1 -> "fraud" if they exist, or just use string representation
    class_mapping = {0: "legit", 1: "fraud"}
    
    counts_dict = {}
    percentages_dict = {}
    
    for val, count in class_counts.items():
        label = class_mapping.get(val, str(val))
        counts_dict[label] = int(count)
        percentages_dict[label] = float((count / total_count) * 100) if total_count > 0 else 0.0

    class_balance = {
        "counts": counts_dict,
        "percentages": percentages_dict
    }

    # 2. Amount Distribution Stats Grouped by Class
    amount_stats = {}
    if amount_col in df.columns:
        # Group by class
        grouped = df.groupby(target_col)[amount_col]
        for val, group in grouped:
            label = class_mapping.get(val, str(val))
            
            # Compute stats
            mean_val = group.mean()
            median_val = group.median()
            std_val = group.std()
            min_val = group.min()
            max_val = group.max()
            
            # Percentiles: 25, 50, 75, 90, 95, 99
            percentiles = {}
            for p in [25, 50, 75, 90, 95, 99]:
                # handle empty groups
                p_val = group.quantile(p / 100.0) if not group.empty else 0.0
                # replace NaN with None for JSON compliance
                percentiles[str(p)] = float(p_val) if pd.notna(p_val) else None
                
            amount_stats[label] = {
                "mean": float(mean_val) if pd.notna(mean_val) else None,
                "median": float(median_val) if pd.notna(median_val) else None,
                "std": float(std_val) if pd.notna(std_val) else None,
                "min": float(min_val) if pd.notna(min_val) else None,
                "max": float(max_val) if pd.notna(max_val) else None,
                "percentiles": percentiles
            }
    else:
        amount_stats = {"error": f"Amount column '{amount_col}' not found"}

    # 3. Correlation Matrix of all numeric features
    numeric_df = df.select_dtypes(include=[np.number])
    corr_df = numeric_df.corr()
    
    # Replace NaNs with None so it serializes to JSON null
    corr_df = corr_df.replace({np.nan: None})
    correlation_matrix = corr_df.to_dict()

    # 4. Top 10 features by absolute mean-difference between fraud (1) and legit (0) classes
    top_features: List[Dict[str, Any]] = []
    
    # Get all numeric columns excluding the target column, Time, and Amount to prevent scale distortion
    exclude_cols = {target_col.lower(), "time", "amount"}
    feature_cols = [col for col in numeric_df.columns if col.lower() not in exclude_cols]
    
    if len(feature_cols) > 0 and 0 in df[target_col].values and 1 in df[target_col].values:
        # Group by target column and calculate means
        means_df = df.groupby(target_col)[feature_cols].mean()
        
        diffs = []
        for col in feature_cols:
            mean_legit = means_df.loc[0, col]
            mean_fraud = means_df.loc[1, col]
            
            # Absolute difference
            mean_diff = abs(mean_fraud - mean_legit)
            
            diffs.append({
                "feature": col,
                "mean_legit": float(mean_legit) if pd.notna(mean_legit) else 0.0,
                "mean_fraud": float(mean_fraud) if pd.notna(mean_fraud) else 0.0,
                "mean_difference": float(mean_diff) if pd.notna(mean_diff) else 0.0
            })
            
        # Sort by mean difference descending and take top 10
        diffs.sort(key=lambda x: x["mean_difference"], reverse=True)
        top_features = diffs[:10]

    return {
        "class_balance": class_balance,
        "amount_stats": amount_stats,
        "correlation_matrix": correlation_matrix,
        "top_features": top_features
    }
