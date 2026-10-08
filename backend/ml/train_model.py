"""
Standalone script and module for training the Urban Flood Machine Learning Surrogate Model.
Run via:
    python backend/ml/train_model.py
"""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.ml.dataset import FloodDatasetGenerator
from backend.ml.model import FloodSurrogateMLModel, get_ml_model
from backend.data.city_generator import get_city_data

def train_surrogate_model(epochs: int = 150, num_storm_scenarios: int = 12) -> dict:
    print("==================================================================")
    print("🤖 TRAINING HYDRODYNAMIC SURROGATE MACHINE LEARNING MODEL")
    print("==================================================================")
    
    city = get_city_data()
    dataset_gen = FloodDatasetGenerator(city)
    
    print(f"[1/3] Generating multi-storm hydrodynamic training dataset...")
    X, y, stats = dataset_gen.generate_training_data(num_storm_scenarios=num_storm_scenarios)
    print(f"      Synthesized {stats['num_samples']} samples across {stats['num_features']} features.")
    print(f"      Target Water Depth: min={y.min():.1f}cm, mean={y.mean():.1f}cm, max={y.max():.1f}cm")

    print(f"[2/3] Training Regularized Neural/Polynomial Surrogate Model ({epochs} epochs)...")
    ml_model = get_ml_model()
    metrics = ml_model.train(X, y, epochs=epochs, learning_rate=0.04)

    print(f"[3/3] Training Complete!")
    print(f"      Validation R² Score:   {metrics['r2_score']:.3f}")
    print(f"      Depth RMSE:           ±{metrics['rmse_depth_cm']:.2f} cm")
    print(f"      Mean Absolute Error:   {metrics['mae_depth_cm']:.2f} cm")
    print(f"      Training Latency:      {metrics['training_time_ms']:.1f} ms")
    print("\nFeature Importances:")
    for feat, imp in metrics["feature_importances"].items():
        bar = "█" * int(imp * 30)
        print(f"  - {feat:28s} {imp:.3f} | {bar}")

    print("==================================================================")
    return metrics

if __name__ == "__main__":
    train_surrogate_model()
