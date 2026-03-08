"""
Predictive Analysis Script for Pregnancy AI
Analyzes the maternal health risk dataset and provides comprehensive insights
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
import pickle
import warnings
warnings.filterwarnings('ignore')

# Set style for better visualizations
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# ============ LOAD DATA ============
print("=" * 60)
print("PREGNANCY AI - PREDICTIVE ANALYSIS")
print("=" * 60)

df = pd.read_csv('Maternal_Health_Risk.csv')
print(f"\n✓ Dataset loaded: {df.shape[0]} records, {df.shape[1]} features")
print("\nFirst few records:")
print(df.head())

# ============ EXPLORATORY DATA ANALYSIS ============
print("\n" + "=" * 60)
print("EXPLORATORY DATA ANALYSIS")
print("=" * 60)

print("\nDataset Info:")
print(df.info())

print("\nBasic Statistics:")
print(df.describe())

print("\nMissing Values:")
print(df.isnull().sum())

print("\nRisk Distribution:")
print(df['RiskLevel'].value_counts())
print("\nRisk Distribution (%):")
print(df['RiskLevel'].value_counts(normalize=True) * 100)

# ============ DATA PREPROCESSING ============
print("\n" + "=" * 60)
print("DATA PREPROCESSING")
print("=" * 60)

# Encode risk levels (Medium -> High for binary classification)
def encode_risk(risk_level):
    risk_lower = str(risk_level).lower().strip()
    if 'low' in risk_lower:
        return 0
    else:
        return 1

df['RiskLevel_encoded'] = df['RiskLevel'].apply(encode_risk)

# Separate features and target
X = df.drop(['RiskLevel', 'RiskLevel_encoded'], axis=1)
y = df['RiskLevel_encoded']

print(f"\nFeatures: {list(X.columns)}")
print(f"Target variable: RiskLevel (0=Low Risk, 1=High Risk)")
print(f"\nClass distribution:")
print(f"  Low Risk:  {(y == 0).sum()} samples ({(y == 0).sum() / len(y) * 100:.1f}%)")
print(f"  High Risk: {(y == 1).sum()} samples ({(y == 1).sum() / len(y) * 100:.1f}%)")

# ============ FEATURE CORRELATION ANALYSIS ============
print("\n" + "=" * 60)
print("FEATURE CORRELATION ANALYSIS")
print("=" * 60)

correlation_with_risk = df[list(X.columns) + ['RiskLevel_encoded']].corr()['RiskLevel_encoded'].drop('RiskLevel_encoded')
print("\nCorrelation with Risk Level (sorted):")
print(correlation_with_risk.sort_values(ascending=False))

# ============ TRAIN-TEST SPLIT & MODEL TRAINING ============
print("\n" + "=" * 60)
print("MODEL TRAINING")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"\nTrain set: {X_train.shape[0]} samples")
print(f"Test set:  {X_test.shape[0]} samples")

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train Random Forest
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
model.fit(X_train_scaled, y_train)

print("\n✓ Model trained successfully!")

# ============ MODEL EVALUATION ============
print("\n" + "=" * 60)
print("MODEL EVALUATION")
print("=" * 60)

# Predictions
y_pred = model.predict(X_test_scaled)
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

# Accuracy
train_accuracy = model.score(X_train_scaled, y_train)
test_accuracy = model.score(X_test_scaled, y_test)

print(f"\nAccuracy:")
print(f"  Training: {train_accuracy:.4f} ({train_accuracy*100:.2f}%)")
print(f"  Testing:  {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")

# Classification Report
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Low Risk', 'High Risk']))

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(f"                 Predicted")
print(f"                 Low  High")
print(f"Actual Low   {cm[0][0]:3d}  {cm[0][1]:3d}")
print(f"       High  {cm[1][0]:3d}  {cm[1][1]:3d}")

# ============ FEATURE IMPORTANCE ============
print("\n" + "=" * 60)
print("FEATURE IMPORTANCE ANALYSIS")
print("=" * 60)

feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nFeature Importance (sorted):")
for idx, row in feature_importance.iterrows():
    bar = "█" * int(row['importance'] * 100)
    print(f"{row['feature']:20s} {bar} {row['importance']:.4f}")

# ============ SAMPLE PREDICTIONS ============
print("\n" + "=" * 60)
print("SAMPLE PREDICTIONS")
print("=" * 60)

# Make predictions on random samples
sample_indices = np.random.choice(X_test.index, 5, replace=False)
print("\nSample predictions from test set:")
print("-" * 80)

for idx, sample_idx in enumerate(sample_indices, 1):
    sample = X_test.loc[sample_idx].values.reshape(1, -1)
    sample_scaled = scaler.transform(sample)
    prediction = model.predict(sample_scaled)[0]
    confidence = model.predict_proba(sample_scaled)[0]
    actual = y_test.loc[sample_idx]
    
    pred_label = "High Risk" if prediction == 1 else "Low Risk"
    actual_label = "High Risk" if actual == 1 else "Low Risk"
    confidence_pct = max(confidence) * 100
    
    print(f"\nSample {idx}:")
    print(f"  Age: {sample[0][0]:.0f}, BMI: {sample[0][1]:.1f}, SysBP: {sample[0][2]:.0f}, DiaBP: {sample[0][3]:.0f}")
    print(f"  Blood Sugar: {sample[0][4]:.0f}, Body Temp: {sample[0][5]:.1f}, Heart Rate: {sample[0][6]:.0f}")
    print(f"  Prediction: {pred_label} (Confidence: {confidence_pct:.1f}%)")
    print(f"  Actual: {actual_label}")
    print(f"  {'✓ Correct' if prediction == actual else '✗ Incorrect'}")

# ============ SAVE MODEL ============
print("\n" + "=" * 60)
print("SAVING MODEL")
print("=" * 60)

with open('pregnancy_risk_model.pkl', 'wb') as f:
    pickle.dump(model, f)
print("✓ Model saved to 'pregnancy_risk_model.pkl'")

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)
print("✓ Scaler saved to 'scaler.pkl'")

# ============ STATISTICAL INSIGHTS ============
print("\n" + "=" * 60)
print("STATISTICAL INSIGHTS")
print("=" * 60)

print("\nHigh Risk vs Low Risk Patients:")
print("-" * 60)

for feature in X.columns:
    high_risk_mean = df[df['RiskLevel_encoded'] == 1][feature].mean()
    low_risk_mean = df[df['RiskLevel_encoded'] == 0][feature].mean()
    diff_pct = ((high_risk_mean - low_risk_mean) / low_risk_mean * 100) if low_risk_mean != 0 else 0
    
    print(f"\n{feature}:")
    print(f"  High Risk mean: {high_risk_mean:.2f}")
    print(f"  Low Risk mean:  {low_risk_mean:.2f}")
    print(f"  Difference:     {diff_pct:+.1f}%")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE!")
print("=" * 60)
