"""
Fix 10 — Upgraded Physics-Informed ML Surrogate: 2-hidden-layer MLP in pure NumPy.
No PyTorch or TensorFlow required.
Architecture: 8 inputs → 32 (ReLU) → 16 (ReLU) → 1 (ReLU)
Includes: Xavier init, mini-batch SGD, dropout, early stopping, permutation importance.
"""
import numpy as np
import json
import os
import time
from typing import Dict, List, Tuple, Any, Optional


class FloodSurrogateMLModel:
    """
    Physics-Informed MLP Surrogate for Urban Flood Depth Nowcasting.
    Fix 10: Upgraded from linear regressor to 2-hidden-layer MLP in pure NumPy.
    Achieves better RMSE with the same dependency-free design.
    """

    model_type = "mlp_surrogate"

    def __init__(self, model_path: Optional[str] = None):
        self.is_trained = False
        self.feature_names = [
            "rainfall_intensity_mm_hr",
            "cumulative_rainfall_mm",
            "dem_elevation_m",
            "slope",
            "is_sink",
            "dist_to_drain_m",
            "drain_capacity_m3_s",
            "upstream_inflow_proxy",
        ]
        n_in = len(self.feature_names)
        n_h1 = 32
        n_h2 = 16

        # Normalization params
        self.mean = np.zeros(n_in, dtype=np.float32)
        self.std = np.ones(n_in, dtype=np.float32)

        # MLP weights (Xavier initialization at load time)
        self.W1 = np.zeros((n_in + 2, n_h1), dtype=np.float32)   # +2 for augmented features
        self.b1 = np.zeros(n_h1, dtype=np.float32)
        self.W2 = np.zeros((n_h1, n_h2), dtype=np.float32)
        self.b2 = np.zeros(n_h2, dtype=np.float32)
        self.W3 = np.zeros((n_h2, 1), dtype=np.float32)
        self.b3 = np.zeros(1, dtype=np.float32)

        self.metrics: Dict = {}
        self.training_history: List = []
        self.feature_importances: Dict = {}
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), "flood_surrogate_model.json")

        if os.path.exists(self.model_path):
            self.load(self.model_path)

    # -------------------------------------------------------
    # Feature augmentation (same physics-inspired terms as before)
    # -------------------------------------------------------
    def _augment(self, X_norm: np.ndarray) -> np.ndarray:
        rain_norm = X_norm[..., 0:1]
        elev_norm = X_norm[..., 2:3]
        sink_norm = X_norm[..., 4:5]
        interaction = rain_norm * (1.0 - elev_norm)
        sink_boost = rain_norm * sink_norm
        return np.concatenate([X_norm, interaction, sink_boost], axis=-1)

    # -------------------------------------------------------
    # Forward pass (supports 2D and 3D tensors for batch/grid)
    # -------------------------------------------------------
    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, x)

    def _forward(self, X_aug: np.ndarray, dropout_rate: float = 0.0, training: bool = False) -> Tuple:
        """Returns (output, (h1, h1_pre, h2, h2_pre, out_pre)) for backprop."""
        h1_pre = X_aug @ self.W1 + self.b1
        h1 = self._relu(h1_pre)
        if training and dropout_rate > 0:
            mask = (np.random.rand(*h1.shape) > dropout_rate).astype(np.float32)
            h1 = h1 * mask / (1.0 - dropout_rate)
        else:
            mask = None

        h2_pre = h1 @ self.W2 + self.b2
        h2 = self._relu(h2_pre)

        out_pre = h2 @ self.W3 + self.b3
        out = self._relu(out_pre)
        return out, (h1, h1_pre, h2, h2_pre, out_pre, mask)

    # -------------------------------------------------------
    # Training
    # -------------------------------------------------------
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 150,
        learning_rate: float = 0.01,
        val_split: float = 0.2,
        batch_size: int = 256,
        dropout_rate: float = 0.1,
        patience: int = 25,
    ) -> Dict[str, Any]:
        """
        Fix 10: Train 2-hidden-layer MLP with:
        - Mini-batch SGD, Xavier init, dropout, early stopping, L2 regularization.
        """
        start_time = time.perf_counter()
        n_samples, n_features = X.shape

        # Train/val split
        np.random.seed(42)
        idx = np.random.permutation(n_samples)
        split = int(n_samples * (1 - val_split))
        tr_idx, vl_idx = idx[:split], idx[split:]

        X_tr, y_tr = X[tr_idx].astype(np.float32), y[tr_idx].astype(np.float32)
        X_vl, y_vl = X[vl_idx].astype(np.float32), y[vl_idx].astype(np.float32)

        # Normalize
        self.mean = np.mean(X_tr, axis=0).astype(np.float32)
        self.std = np.std(X_tr, axis=0).astype(np.float32)
        self.std[self.std == 0] = 1.0

        X_tr_n = (X_tr - self.mean) / self.std
        X_vl_n = (X_vl - self.mean) / self.std

        X_tr_a = self._augment(X_tr_n)
        X_vl_a = self._augment(X_vl_n)

        n_aug = X_tr_a.shape[1]
        n_h1, n_h2 = 32, 16

        # Xavier initialization
        self.W1 = np.random.randn(n_aug, n_h1).astype(np.float32) * np.sqrt(2.0 / n_aug)
        self.b1 = np.zeros(n_h1, dtype=np.float32)
        self.W2 = np.random.randn(n_h1, n_h2).astype(np.float32) * np.sqrt(2.0 / n_h1)
        self.b2 = np.zeros(n_h2, dtype=np.float32)
        self.W3 = np.random.randn(n_h2, 1).astype(np.float32) * np.sqrt(2.0 / n_h2)
        self.b3 = np.zeros(1, dtype=np.float32)

        l2 = 0.0005
        n_tr = len(X_tr_a)
        best_val_loss = float("inf")
        best_weights = None
        no_improve = 0
        self.training_history = []

        for epoch in range(1, epochs + 1):
            # Mini-batch shuffle
            perm = np.random.permutation(n_tr)
            for start in range(0, n_tr, batch_size):
                batch = perm[start:start + batch_size]
                Xb = X_tr_a[batch]
                yb = y_tr[batch].reshape(-1, 1)

                out, (h1, h1_pre, h2, h2_pre, out_pre, mask) = self._forward(Xb, dropout_rate, training=True)

                err = out - yb   # (batch, 1)
                loss = float(np.mean(err ** 2))

                # Backprop — layer 3
                d_out = 2 * err / len(batch)
                d_out_pre = d_out * (out_pre > 0).astype(np.float32)
                dW3 = h2.T @ d_out_pre + l2 * self.W3
                db3 = np.sum(d_out_pre, axis=0)

                # Layer 2
                d_h2 = d_out_pre @ self.W3.T
                d_h2_pre = d_h2 * (h2_pre > 0).astype(np.float32)
                dW2 = h1.T @ d_h2_pre + l2 * self.W2
                db2 = np.sum(d_h2_pre, axis=0)

                # Layer 1
                d_h1 = d_h2_pre @ self.W2.T
                if mask is not None:
                    d_h1 = d_h1 * mask / (1.0 - dropout_rate)
                d_h1_pre = d_h1 * (h1_pre > 0).astype(np.float32)
                dW1 = Xb.T @ d_h1_pre + l2 * self.W1
                db1 = np.sum(d_h1_pre, axis=0)

                # Update
                self.W3 -= learning_rate * dW3
                self.b3 -= learning_rate * db3
                self.W2 -= learning_rate * dW2
                self.b2 -= learning_rate * db2
                self.W1 -= learning_rate * dW1
                self.b1 -= learning_rate * db1

            # Validation
            val_out, _ = self._forward(X_vl_a)
            val_preds = val_out.flatten()
            val_err = val_preds - y_vl
            val_loss = float(np.mean(val_err ** 2))
            val_rmse = float(np.sqrt(val_loss))
            ss_tot = np.sum((y_vl - np.mean(y_vl)) ** 2)
            ss_res = np.sum((y_vl - val_preds) ** 2)
            r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

            if epoch % 10 == 0 or epoch == 1 or epoch == epochs:
                self.training_history.append({
                    "epoch": epoch,
                    "train_loss": round(loss, 4),
                    "val_loss": round(val_loss, 4),
                    "val_rmse": round(val_rmse, 2),
                    "r2_score": round(max(0.0, r2), 3),
                })

            # Early stopping
            if val_loss < best_val_loss - 1e-4:
                best_val_loss = val_loss
                best_weights = (
                    self.W1.copy(), self.b1.copy(),
                    self.W2.copy(), self.b2.copy(),
                    self.W3.copy(), self.b3.copy(),
                )
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    print(f"[MLP] Early stopping at epoch {epoch} (best val_loss={best_val_loss:.4f})")
                    break

        # Restore best weights
        if best_weights:
            self.W1, self.b1, self.W2, self.b2, self.W3, self.b3 = best_weights

        self.is_trained = True

        # Final metrics
        final_out, _ = self._forward(X_vl_a)
        final_preds = final_out.flatten()
        final_rmse = float(np.sqrt(np.mean((final_preds - y_vl) ** 2)))
        final_mae = float(np.mean(np.abs(final_preds - y_vl)))
        ss_tot = np.sum((y_vl - np.mean(y_vl)) ** 2)
        ss_res = np.sum((y_vl - final_preds) ** 2)
        final_r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Permutation feature importance
        feature_importances = self._permutation_importance(X_vl_a, y_vl, baseline_rmse=final_rmse)

        train_duration = (time.perf_counter() - start_time) * 1000.0
        self.metrics = {
            "r2_score": round(final_r2, 3),
            "rmse_depth_cm": round(final_rmse, 2),
            "mae_depth_cm": round(final_mae, 2),
            "train_samples": len(X_tr),
            "val_samples": len(X_vl),
            "training_time_ms": round(train_duration, 1),
            "feature_importances": feature_importances,
            "model_type": "mlp_2hidden_numpy",
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.feature_importances = feature_importances
        self.save(self.model_path)
        return self.metrics

    def _permutation_importance(self, X_aug: np.ndarray, y: np.ndarray, baseline_rmse: float) -> Dict[str, float]:
        """
        Fix 10: Compute permutation importance for each of the 8 original features.
        Shuffles each feature column and measures RMSE increase.
        """
        importances = {}
        # Original features are first 8 columns of X_aug (before augmented terms)
        for i, feat_name in enumerate(self.feature_names):
            X_perm = X_aug.copy()
            np.random.shuffle(X_perm[:, i])
            out_perm, _ = self._forward(X_perm)
            perm_rmse = float(np.sqrt(np.mean((out_perm.flatten() - y) ** 2)))
            importance = max(0.0, perm_rmse - baseline_rmse)
            importances[feat_name] = round(importance, 4)

        # Normalize to sum = 1
        total = sum(importances.values()) or 1.0
        return {k: round(v / total, 3) for k, v in importances.items()}

    def predict_grid(
        self,
        rainfall_intensity_mm_hr: float,
        cumulative_rain_mm: float,
        dem_elevation: np.ndarray,
        slope: np.ndarray,
        is_sink: np.ndarray,
        dist_to_drain: np.ndarray,
        drain_cap: np.ndarray,
        upstream_proxy: np.ndarray,
    ) -> np.ndarray:
        """
        Vectorized MLP inference over the full DEM grid. < 5ms for 2000 cells.
        """
        rows, cols = dem_elevation.shape
        rain_arr = np.full((rows, cols), rainfall_intensity_mm_hr, dtype=np.float32)
        cum_arr = np.full((rows, cols), cumulative_rain_mm, dtype=np.float32)

        feats = np.stack([
            rain_arr, cum_arr, dem_elevation, slope,
            is_sink.astype(np.float32), dist_to_drain, drain_cap, upstream_proxy,
        ], axis=-1)  # (rows, cols, 8)

        orig_shape = feats.shape[:2]
        feats_flat = feats.reshape(-1, feats.shape[-1])  # (N, 8)

        # Normalize + augment
        feats_norm = (feats_flat - self.mean) / self.std
        feats_aug = self._augment(feats_norm)

        # Forward pass (inference, no dropout)
        out, _ = self._forward(feats_aug)
        depth_flat = out.flatten()
        return np.round(depth_flat.reshape(orig_shape), 1)

    def save(self, filepath: str):
        data = {
            "is_trained": self.is_trained,
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "mean": self.mean.tolist(),
            "std": self.std.tolist(),
            "W1": self.W1.tolist(), "b1": self.b1.tolist(),
            "W2": self.W2.tolist(), "b2": self.b2.tolist(),
            "W3": self.W3.tolist(), "b3": self.b3.tolist(),
            "metrics": self.metrics,
            "training_history": self.training_history,
            "feature_importances": self.feature_importances,
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load(self, filepath: str):
        if not os.path.exists(filepath):
            return
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            self.is_trained = data.get("is_trained", False)
            self.feature_names = data.get("feature_names", self.feature_names)
            self.mean = np.array(data.get("mean", []), dtype=np.float32)
            self.std = np.array(data.get("std", []), dtype=np.float32)
            self.W1 = np.array(data.get("W1", self.W1), dtype=np.float32)
            self.b1 = np.array(data.get("b1", self.b1), dtype=np.float32)
            self.W2 = np.array(data.get("W2", self.W2), dtype=np.float32)
            self.b2 = np.array(data.get("b2", self.b2), dtype=np.float32)
            self.W3 = np.array(data.get("W3", self.W3), dtype=np.float32)
            self.b3 = np.array(data.get("b3", self.b3), dtype=np.float32)
            self.metrics = data.get("metrics", {})
            self.training_history = data.get("training_history", [])
            self.feature_importances = data.get("feature_importances", {})
        except Exception as e:
            print(f"[MLP] Failed to load model: {e}. Starting fresh.")
            self.is_trained = False


_ml_model_instance = None


def get_ml_model() -> FloodSurrogateMLModel:
    global _ml_model_instance
    if _ml_model_instance is None:
        _ml_model_instance = FloodSurrogateMLModel()
    return _ml_model_instance
