#!/usr/bin/env python3
"""
UCI Diabetes Model Benchmarking Script

This script evaluates the accuracy of the UCI Diabetes prediction model on test data.
It provides comprehensive metrics including accuracy, precision, recall, F1-score, AUC-ROC,
and confidence analysis for the symptom-based diabetes prediction model.
"""

import os
import sys
import logging
import argparse
import pandas as pd
import numpy as np
from tqdm import tqdm
import time
import joblib
import colorama
from colorama import Fore, Style
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                            roc_auc_score, roc_curve, precision_recall_curve)
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# Initialize colorama for colored output
colorama.init()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Ensure project root is importable (two directories up) so `diab_model` can be imported
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    logger.info(f"Added project root to sys.path: {PROJECT_ROOT}")

# Benchmark configuration
BENCHMARK_CONFIG = {
    'use_held_out_set': True,  # Use held-out test set when available
    'random_seed': 42,         # Random seed for reproducible sampling
    'test_samples': 100        # Number of test samples if not using held-out set
}

# Define paths for UCI model
DIABETES_DIR = os.path.join(os.path.dirname(__file__))
DATA_PATH = os.path.join(DIABETES_DIR, 'early_diabetes.csv')

def print_color(text, color=Fore.WHITE, style=Style.NORMAL, end='\n'):
    """Print colored text to terminal"""
    print(f"{style}{color}{text}{Style.RESET_ALL}", end=end)

def print_section_header(title):
    """Print a section header with formatting"""
    print("\n" + "=" * 80)
    print_color(f" {title.upper()} ", Fore.CYAN, Style.BRIGHT)
    print("=" * 80)

def load_model_components():
    """Load the trained UCI model components directly"""
    try:
        logger.info("Loading UCI Diabetes model components...")
        
        # Import the diabetes model integration
        from diabetes import DiabetesPredictor
        
        # Create predictor instance
        predictor = DiabetesPredictor()
        
        if not predictor.is_loaded:
            logger.error("Model failed to load")
            return None, None, None
        
        logger.info("Loaded UCI model successfully")
        
        # Extract components from predictor
        model = predictor.model
        label_encoders = predictor.label_encoders
        feature_names = predictor.feature_names
        
        if model:
            logger.info("Model extracted successfully")
        if label_encoders:
            logger.info(f"Label encoders found: {len(label_encoders)} encoders")
        if feature_names:
            logger.info(f"Feature names found: {len(feature_names)} features")
        
        # Return model, label_encoders, and None for training_history (not needed for benchmarking)
        return model, label_encoders, None

    except Exception as e:
        logger.error(f"Failed to load UCI model: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def load_test_data(use_held_out=True):
    """Load test data for UCI model"""
    try:
        if use_held_out and os.path.exists(DATA_PATH):
            logger.info(f"Loading UCI dataset from: {DATA_PATH}")
            df = pd.read_csv(DATA_PATH)

            # Convert 'class' to 'Outcome' if needed
            if 'class' in df.columns:
                df['Outcome'] = (df['class'] == 'Positive').astype(int)
                df = df.drop('class', axis=1)

            # Use 20% as test set (same as training)
            from sklearn.model_selection import train_test_split
            _, test_df = train_test_split(
                df,
                test_size=0.2,
                random_state=BENCHMARK_CONFIG['random_seed'],
                stratify=df['Outcome']
            )

            logger.info(f"Loaded {len(test_df)} UCI test samples")
            return test_df

        else:
            logger.warning("Held-out test set not available, using full dataset split")
            df = pd.read_csv(DATA_PATH)

            # Convert 'class' to 'Outcome' if needed
            if 'class' in df.columns:
                df['Outcome'] = (df['class'] == 'Positive').astype(int)
                df = df.drop('class', axis=1)

            # Use a subset for testing
            from sklearn.model_selection import train_test_split
            _, test_df = train_test_split(
                df,
                test_size=min(BENCHMARK_CONFIG['test_samples'], len(df)) / len(df),
                random_state=BENCHMARK_CONFIG['random_seed'],
                stratify=df['Outcome']
            )

            logger.info(f"Using {len(test_df)} samples for UCI testing")
            return test_df

    except Exception as e:
        logger.error(f"Failed to load UCI test data: {e}")
        return None

def preprocess_features(df, label_encoders):
    """Preprocess features for UCI model (no feature engineering needed)"""
    logger.info("Preprocessing UCI features...")

    # Separate features and target
    X = df.drop('Outcome', axis=1)
    y = df['Outcome']

    # Apply label encoding to categorical features
    if label_encoders:
        for col in X.columns:
            if col in label_encoders:
                X[col] = label_encoders[col].transform(X[col])
                logger.info(f"Encoded {col}: {len(label_encoders[col].classes_)} classes")
            else:
                # Fallback: encode any remaining categorical columns
                if X[col].dtype == 'object':
                    le = LabelEncoder()
                    X[col] = le.fit_transform(X[col])
                    logger.info(f"Auto-encoded {col}: {len(le.classes_)} classes")

    logger.info(f"Feature matrix shape: {X.shape}")
    logger.info(f"Feature names: {list(X.columns)}")

    return X, y

def evaluate_model(test_df, model, label_encoders):
    """Evaluate the UCI model on test data"""
    print_section_header("UCI MODEL EVALUATION")

    # Separate features and target
    if 'Outcome' not in test_df.columns:
        logger.error("Test data must contain 'Outcome' column")
        return None, None, None

    # Check if model is actually a model object
    if isinstance(model, dict):
        logger.error("Model is still a dictionary. Cannot make predictions.")
        logger.info(f"Available keys: {model.keys()}")
        return None, None, None

    # Preprocess features (no engineering needed for UCI)
    X_test, y_test = preprocess_features(test_df, label_encoders)

    # Convert to numpy array for compatibility
    X_test_array = X_test.values

    start_time = time.time()

    # Make predictions (no scaling/feature selection needed)
    try:
        logger.info("Making predictions on UCI data...")
        y_pred = model.predict(X_test_array)

        # Get probabilities if available
        if hasattr(model, 'predict_proba'):
            y_proba = model.predict_proba(X_test_array)[:, 1]
        else:
            y_proba = y_pred.astype(float)  # Fallback

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

    total_time = time.time() - start_time
    avg_time = total_time / len(test_df)

    print_color(f"\nProcessed {len(test_df)} UCI samples in {total_time:.2f} seconds", Fore.CYAN)
    print_color(f"Average processing time: {avg_time*1000:.2f} ms per sample", Fore.CYAN)

    return y_test, y_pred, y_proba

def calculate_metrics(y_test, y_pred, y_proba):
    """Calculate and display performance metrics for UCI model"""
    print_section_header("UCI PERFORMANCE METRICS")

    # Overall accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print_color(f"Overall Accuracy: {accuracy:.1%}", Fore.GREEN, Style.BRIGHT)

    # AUC-ROC
    auc = roc_auc_score(y_test, y_proba)
    print_color(f"AUC-ROC Score: {auc:.3f}", Fore.GREEN, Style.BRIGHT)

    # Classification report
    class_report = classification_report(y_test, y_pred,
                                        target_names=['Negative', 'Positive'],
                                        output_dict=True)

    print_color("\nPer-Class Performance:", Fore.CYAN, Style.BRIGHT)
    print(f"{'Class':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<8}")
    print("-" * 59)

    for class_name in ['Negative', 'Positive']:
        metrics = class_report[class_name]
        precision = metrics['precision']
        recall = metrics['recall']
        f1 = metrics['f1-score']
        support = metrics['support']

        # Color based on performance
        if f1 >= 0.95:
            color = Fore.GREEN
        elif f1 >= 0.90:
            color = Fore.CYAN
        else:
            color = Fore.YELLOW

        print_color(
            f"{class_name:<15} {precision:.1%}       {recall:.1%}       {f1:.1%}       {int(support):<8}",
            color
        )

    # Confusion matrix
    print_color("\nConfusion Matrix:", Fore.CYAN, Style.BRIGHT)
    cm = confusion_matrix(y_test, y_pred)

    print("                Predicted")
    print("              Negative  Positive")
    print("-" * 40)
    print(f"Actual Negative    {cm[0,0]:>4}       {cm[0,1]:>4}")
    print(f"       Positive    {cm[1,0]:>4}       {cm[1,1]:>4}")

    # Probability distribution analysis
    print_color("\nProbability Distribution Analysis:", Fore.CYAN, Style.BRIGHT)

    # Split by correct/incorrect predictions
    correct_mask = (y_test == y_pred)
    correct_probs = y_proba[correct_mask]
    incorrect_probs = y_proba[~correct_mask]

    print(f"Correct predictions: {len(correct_probs)}")
    print(f"  Mean probability: {np.mean(correct_probs):.1%}")
    print(f"  Std deviation: {np.std(correct_probs):.3f}")

    print(f"Incorrect predictions: {len(incorrect_probs)}")
    if len(incorrect_probs) > 0:
        print(f"  Mean probability: {np.mean(incorrect_probs):.1%}")
        print(f"  Std deviation: {np.std(incorrect_probs):.3f}")

    # Risk stratification
    print_color("\nRisk Stratification:", Fore.CYAN, Style.BRIGHT)
    low_risk = np.sum(y_proba < 0.3)
    medium_risk = np.sum((y_proba >= 0.3) & (y_proba < 0.7))
    high_risk = np.sum(y_proba >= 0.7)

    print(f"Low Risk (<30%): {low_risk} patients ({low_risk/len(y_proba)*100:.1f}%)")
    print(f"Medium Risk (30-70%): {medium_risk} patients ({medium_risk/len(y_proba)*100:.1f}%)")
    print(f"High Risk (>70%): {high_risk} patients ({high_risk/len(y_proba)*100:.1f}%)")

    # Performance summary
    print_section_header("UCI SUMMARY")

    correct_count = np.sum(y_test == y_pred)
    total_count = len(y_test)

    print_color(f"🎯 Overall Accuracy: {correct_count}/{total_count} = {accuracy:.1%}",
             Fore.GREEN, Style.BRIGHT)
    print_color(f"📊 AUC-ROC: {auc:.3f}", Fore.GREEN, Style.BRIGHT)

    # Performance assessment for UCI (higher standards)
    if accuracy >= 0.98:
        print_color("🎉 OUTSTANDING: Model achieves near-perfect accuracy (98%+)",
                   Fore.GREEN, Style.BRIGHT)
    elif accuracy >= 0.95:
        print_color("✅ EXCELLENT: Model exceeds clinical deployment target (95%+)",
                   Fore.GREEN, Style.BRIGHT)
    elif accuracy >= 0.90:
        print_color("✅ VERY GOOD: Model shows strong performance (90%+)",
                   Fore.CYAN, Style.BRIGHT)
    elif accuracy >= 0.85:
        print_color("⚠️ GOOD: Model meets requirements but could be improved",
                   Fore.YELLOW, Style.BRIGHT)
    else:
        print_color("❌ NEEDS IMPROVEMENT: Model performance below acceptable thresholds",
                   Fore.RED, Style.BRIGHT)

    return {
        'accuracy': accuracy,
        'auc': auc,
        'confusion_matrix': cm,
        'classification_report': class_report
    }

def run_multi_seed_benchmark(seeds, use_held_out):
    """Run benchmark across multiple seeds for UCI model"""
    print_section_header("UCI MULTI-SEED BENCHMARK ANALYSIS")

    # Load model
    model, label_encoders, training_history = load_model_components()
    if model is None:
        logger.error("Failed to load UCI model")
        return

    all_results = []

    for seed in seeds:
        print_color(f"\n{'='*60}", Fore.BLUE)
        print_color(f"UCI SEED {seed}", Fore.BLUE, Style.BRIGHT)
        print_color(f"{'='*60}", Fore.BLUE)

        # Load test data with this seed
        BENCHMARK_CONFIG['random_seed'] = seed
        test_df = load_test_data(use_held_out=use_held_out)

        if test_df is None:
            logger.error(f"Failed to load test data for seed {seed}")
            continue

        # Evaluate
        y_test, y_pred, y_proba = evaluate_model(test_df, model, label_encoders)

        if y_test is None:
            continue

        # Calculate metrics
        metrics = calculate_metrics(y_test, y_pred, y_proba)

        # Store results
        all_results.append({
            'seed': seed,
            'accuracy': metrics['accuracy'],
            'auc': metrics['auc'],
            'samples': len(y_test)
        })

    # Aggregate analysis
    if len(all_results) > 1:
        print_section_header("UCI AGGREGATE ANALYSIS")

        accuracies = [r['accuracy'] for r in all_results]
        aucs = [r['auc'] for r in all_results]

        print_color("📊 Performance Across Seeds:", Fore.CYAN, Style.BRIGHT)
        print(f"  Mean Accuracy: {np.mean(accuracies):.1%} ± {np.std(accuracies):.1%}")
        print(f"  Mean AUC: {np.mean(aucs):.3f} ± {np.std(aucs):.3f}")
        print(f"  Min Accuracy: {np.min(accuracies):.1%}")
        print(f"  Max Accuracy: {np.max(accuracies):.1%}")

        print_color("\n📋 Per-Seed Breakdown:", Fore.CYAN, Style.BRIGHT)
        print(f"{'Seed':<8} {'Accuracy':<12} {'AUC':<10} {'Samples':<10}")
        print("-" * 40)

        for result in all_results:
            acc_color = Fore.GREEN if result['accuracy'] >= 0.95 else Fore.CYAN
            print_color(
                f"{result['seed']:<8} {result['accuracy']:.1%}        {result['auc']:.3f}    {result['samples']:<10}",
                acc_color
            )

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Benchmark the UCI Diabetes model')
    parser.add_argument('--use-held-out', action='store_true',
                       default=BENCHMARK_CONFIG['use_held_out_set'],
                       help='Use held-out test set instead of random sampling')
    parser.add_argument('--samples', type=int, default=BENCHMARK_CONFIG['test_samples'],
                       help='Number of test samples if not using held-out set')
    parser.add_argument('--multi-seed', type=int, nargs='+', default=None,
                       help='Run benchmark with multiple seeds')
    parser.add_argument('--seed', type=int, default=BENCHMARK_CONFIG['random_seed'],
                       help='Random seed for sampling')

    args = parser.parse_args()

    # Update config
    BENCHMARK_CONFIG['use_held_out_set'] = args.use_held_out
    BENCHMARK_CONFIG['test_samples'] = args.samples
    BENCHMARK_CONFIG['random_seed'] = args.seed

    print_section_header("UCI DIABETES MODEL BENCHMARK")
    print_color("Evaluating symptom-based diabetes prediction model", Fore.CYAN)
    print_color(f"Configuration: {BENCHMARK_CONFIG}", Fore.CYAN)

    # Handle multi-seed testing
    if args.multi_seed:
        seeds = args.multi_seed
        run_multi_seed_benchmark(seeds, args.use_held_out)
    else:
        # Single seed testing
        # Load model
        model, label_encoders, training_history = load_model_components()
        if model is None:
            sys.exit(1)

        # Load test data
        test_df = load_test_data(use_held_out=args.use_held_out)
        if test_df is None:
            sys.exit(1)

        # Evaluate
        y_test, y_pred, y_proba = evaluate_model(test_df, model, label_encoders)

        if y_test is not None:
            # Calculate metrics
            calculate_metrics(y_test, y_pred, y_proba)

if __name__ == "__main__":
    main()