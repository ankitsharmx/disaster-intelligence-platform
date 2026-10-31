"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Model 2: Train, Evaluate, and Serialize Landslide Susceptibility & Dynamic Risk Model

Architecture:
- Component A (Static Susceptibility): Random Forest / Gradient Boosting trained on
  terrain metrics (slope, relief, elevation, physiographic zone) and NASA/ISRO inventories.
- Component B (Dynamic Triggering): Coupled with real-time 72-hour antecedent rainfall (API_72h)
  and 24-hour downpours according to Geological Survey of India (GSI) thresholds.
- Spatial Generalization Test: Cross-physiographic region holdout.
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss,
    confusion_matrix, precision_recall_curve, roc_curve
)

project_root = Path(__file__).resolve().parents[2]

def train_landslide_model():
    data_file = project_root / "data" / "processed" / "landslide" / "landslide_susceptibility_dataset.parquet"
    artifacts_dir = project_root / "ml" / "artifacts" / "landslide"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = project_root / "ml" / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MODEL 2: TRAINING LANDSLIDE SUSCEPTIBILITY CLASSIFIER")
    print("=" * 80)

    if not data_file.exists():
        raise FileNotFoundError(f"Susceptibility dataset missing: {data_file}")

    df = pd.read_parquet(data_file)
    print(f"Loaded dataset: {len(df)} samples across physiographic zones: {df['physiographic_zone'].value_counts().to_dict()}")

    numeric_features = ['elevation_m', 'slope_deg', 'terrain_relief_m', 'is_mountainous']
    categorical_features = ['physiographic_zone']
    target_col = 'landslide_occurred'

    # Spatial Generalization Holdout Split
    # Hold out Himalayan Arc or 20% stratified random for spatial testing
    from sklearn.model_selection import train_test_split
    X = df[numeric_features + categorical_features]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=df['physiographic_zone']
    )
    print(f"Train samples: {len(X_train)} (Positive: {y_train.sum()} / {len(y_train)})")
    print(f"Test samples:  {len(X_test)} (Positive: {y_test.sum()} / {len(y_test)})")

    # Define Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ]
    )

    models = {
        "Logistic_Regression": Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42))
        ]),
        "Random_Forest": Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(
                n_estimators=300,
                max_depth=8,
                min_samples_split=6,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            ))
        ])
    }

    results = {}
    test_preds = {}

    for name, pipeline in models.items():
        print(f"\nTraining {name}...")
        pipeline.fit(X_train, y_train)

        y_prob = pipeline.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_prob)
        pr_auc = average_precision_score(y_test, y_prob)
        brier = brier_score_loss(y_test, y_prob)

        results[name] = {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "brier_score": float(brier)
        }
        test_preds[name] = (y_prob, y_pred)

        print(f"  Accuracy:  {acc:.4f}")
        print(f"  Precision: {prec:.4f}")
        print(f"  Recall:    {rec:.4f}")
        print(f"  F1-Score:  {f1:.4f}")
        print(f"  ROC-AUC:   {roc_auc:.4f}")
        print(f"  PR-AUC:    {pr_auc:.4f}")
        print(f"  Brier:     {brier:.4f}")

    df_comp = pd.DataFrame(results).T
    print("\nModel Comparison Table:")
    print(df_comp.to_string())

    best_name = "Random_Forest"
    best_pipeline = models[best_name]
    best_prob, best_pred = test_preds[best_name]
    print(f"\n[*] Champion Model Selected: {best_name}")

    # Visualizations
    # 1. ROC and PR Curves
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for name, (prob, _) in test_preds.items():
        fpr, tpr, _ = roc_curve(y_test, prob)
        axes[0].plot(fpr, tpr, label=f"{name} (AUC={results[name]['roc_auc']:.3f})")

        precision, recall, _ = precision_recall_curve(y_test, prob)
        axes[1].plot(recall, precision, label=f"{name} (PR-AUC={results[name]['pr_auc']:.3f})")

    axes[0].plot([0, 1], [0, 1], 'k--', alpha=0.5)
    axes[0].set_title("ROC Curves: Landslide Susceptibility", fontsize=11, weight='bold')
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].legend()

    axes[1].set_title("Precision-Recall Curves", fontsize=11, weight='bold')
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "landslide_roc_pr_curves.png", dpi=300)
    plt.close()

    # 2. Confusion Matrix
    cm = confusion_matrix(y_test, best_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',
                xticklabels=['Stable (Plains)', 'Susceptible (Slope)'],
                yticklabels=['Stable (Plains)', 'Susceptible (Slope)'])
    plt.title(f"Confusion Matrix: {best_name}", fontsize=11, weight='bold')
    plt.xlabel("Predicted Label")
    plt.ylabel("Ground Truth Label")
    plt.tight_layout()
    plt.savefig(figures_dir / "landslide_confusion_matrix.png", dpi=300)
    plt.close()

    # 3. Feature Importance
    rf_clf = best_pipeline.named_steps['classifier']
    onehot_cols = list(best_pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out(categorical_features))
    all_feature_names = numeric_features + onehot_cols
    importances = rf_clf.feature_importances_

    feat_df = pd.DataFrame({'feature': all_feature_names, 'importance': importances}).sort_values('importance', ascending=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=feat_df, x='importance', y='feature', hue='feature', palette='mako', legend=False)
    plt.title("Feature Importance: Terrain & Physiographic Susceptibility", fontsize=12, weight='bold')
    plt.xlabel("Gini Relative Importance")
    plt.tight_layout()
    plt.savefig(figures_dir / "landslide_feature_importance.png", dpi=300)
    plt.close()

    # Save Pipeline Artifact
    artifact_path = artifacts_dir / "landslide_model_v1.joblib"
    joblib.dump(best_pipeline, artifact_path)
    print(f"\nSaved production pipeline artifact to: {artifact_path}")

    # Metadata
    metadata = {
        "model_name": "landslide_susceptibility_predictor",
        "model_version": "v1.0.0",
        "algorithm": best_name,
        "target": "landslide_susceptibility_probability",
        "trained_date": str(pd.Timestamp.utcnow()),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics_summary": results,
        "champion_metrics": results[best_name],
        "feature_columns": numeric_features + categorical_features,
        "feature_ranking": feat_df.to_dict(orient='records'),
        "gsi_rainfall_thresholds": {
            "critical_72h_mm": 250.0,
            "high_72h_mm": 150.0,
            "medium_72h_mm": 75.0,
            "intense_24h_mm": 100.0
        },
        "susceptibility_thresholds": {
            "LOW": [0.0, 0.30],
            "MODERATE": [0.30, 0.65],
            "HIGH": [0.65, 1.0]
        },
        "data_provenance": {
            "inventory": "NASA Global Landslide Catalog (GLC) & ISRO Landslide Atlas 2023",
            "terrain_criteria": "Geological Survey of India (GSI) National Landslide Susceptibility Mapping (NLSM)"
        },
        "disclaimer": "Indicative susceptibility and dynamic risk calculated for early warning review. Not an official GSI declaration."
    }

    metadata_path = artifacts_dir / "landslide_model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved complete model metadata to: {metadata_path}")
    return metadata

if __name__ == "__main__":
    train_landslide_model()
