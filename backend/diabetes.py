"""
DiaBot - Diabetes Model Controller
Handles diabetes prediction model loading and inference
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
import warnings
from typing import Dict, List, Tuple, Optional, Union

warnings.filterwarnings('ignore')


class DiabetesPredictor:
    """
    Diabetes prediction model integration
    Uses LightGBM model trained on UCI Early Stage Diabetes dataset
    98.1% accuracy, 16 symptom-based features
    """
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'backend', 'Diabetes_Model'
        )
        self.model = None
        self.label_encoders = None
        self.feature_names = None
        self.is_loaded = False
        
        self.input_features = [
            'Age', 'Gender', 'Polyuria', 'Polydipsia', 'sudden weight loss',
            'weakness', 'Polyphagia', 'Genital thrush', 'visual blurring',
            'Itching', 'Irritability', 'delayed healing', 'partial paresis',
            'muscle stiffness', 'Alopecia', 'Obesity'
        ]
        
        self.load_model()
    
    def load_model(self) -> bool:
        """Load the diabetes model"""
        try:
            model_file = os.path.join(self.model_path, 'diab_model.joblib')
            
            if not os.path.exists(model_file):
                print(f"❌ Model file not found: {model_file}")
                raise FileNotFoundError(f"Model file not found: {model_file}")
            
            print(f"📁 Loading model from: {model_file}")
            model_data = joblib.load(model_file)
            
            if isinstance(model_data, dict):
                self.model = model_data.get('model')
                self.label_encoders = model_data.get('label_encoders')
                self.feature_names = model_data.get('feature_names')
                print(f"✅ Loaded model dictionary with keys: {model_data.keys()}")
            else:
                self.model = model_data
                print(f"✅ Loaded model directly: {type(model_data)}")
            
            if self.model is None:
                print("❌ Model is None after loading")
                self.is_loaded = False
                return False
            
            self.is_loaded = True
            print(f"✅ Model loaded successfully. Type: {type(self.model)}")
            return True
        except Exception as e:
            print(f"❌ Error loading diabetes model: {e}")
            import traceback
            traceback.print_exc()
            self.is_loaded = False
            return False
    
    def validate_input(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate input data"""
        errors = []
        
        for feature in self.input_features:
            if feature not in data:
                errors.append(f"Missing: {feature}")
        
        if 'Age' in data:
            age = data['Age']
            if not isinstance(age, (int, float)) or age < 0 or age > 120:
                errors.append("Age must be 0-120")
        
        if 'Gender' in data:
            gender = data['Gender']
            if gender not in [0, 1, 'Male', 'Female']:
                errors.append("Gender must be 0 (Female) or 1 (Male)")
        
        # Check binary values for symptom features
        binary_features = [f for f in self.input_features if f not in ['Age', 'Gender']]
        for feature in binary_features:
            if feature in data:
                val = data[feature]
                if val not in [0, 1, 'Yes', 'No']:
                    errors.append(f"{feature} must be 0, 1, Yes, or No")
        
        return len(errors) == 0, errors
    
    def _create_features(self, data: Dict) -> np.ndarray:
        """Create feature array from input data"""
        df = pd.DataFrame([data])
        
        # Normalize binary inputs (convert Yes/No to 1/0 if needed)
        for col in df.columns:
            if col not in ['Age', 'Gender']:
                if df[col].dtype == 'object':
                    df[col] = df[col].map({'Yes': 1, 'No': 0}).fillna(df[col])
        
        # Normalize Gender (convert Male/Female to 1/0 if needed)
        if 'Gender' in df.columns and df['Gender'].dtype == 'object':
            df['Gender'] = df['Gender'].map({'Male': 1, 'Female': 0}).fillna(df['Gender'])
        
        if self.label_encoders:
            for col in df.columns:
                if col in self.label_encoders and col != 'Age':
                    try:
                        df[col] = self.label_encoders[col].transform(df[col])
                    except:
                        pass  # Already numeric
        
        if self.feature_names:
            features = df[self.feature_names].values
        else:
            features = df[self.input_features].values
        
        return features
    
    def predict(self, patient_data: Dict) -> Dict:
        """
        Predict diabetes risk
        
        Args:
            patient_data: Dictionary with 16 symptom features
            
        Returns:
            Dictionary with prediction, probability, risk_level, etc.
        """
        if not self.is_loaded:
            return {'error': 'Model not loaded', 'success': False}
        
        is_valid, errors = self.validate_input(patient_data)
        if not is_valid:
            return {'error': f"Invalid input: {'; '.join(errors)}", 'success': False}
        
        try:
            features = self._create_features(patient_data)
            prediction = self.model.predict(features)[0]
            
            probability = 0.5
            if hasattr(self.model, 'predict_proba'):
                prob_array = self.model.predict_proba(features)[0]
                probability = prob_array[1]
            
            # Determine risk level
            if probability < 0.3:
                risk_level = 'Low'
                confidence = min(0.95, 0.7 + (0.3 - probability) * 0.8)
            elif probability < 0.7:
                risk_level = 'Medium'
                confidence = min(0.85, 0.6 + min(abs(probability - 0.3), abs(probability - 0.7)) * 2)
            else:
                risk_level = 'High'
                confidence = min(0.95, 0.7 + (probability - 0.7) * 0.8)
            
            interpretation = f"{'High' if prediction == 1 else 'Low'} risk based on symptoms (Probability: {probability:.1%})"
            risk_factors = self._identify_risk_factors(patient_data)
            
            return {
                'prediction': int(prediction),
                'probability': float(probability),
                'risk_level': risk_level,
                'confidence': float(confidence),
                'interpretation': interpretation,
                'risk_factors': risk_factors,
                'success': True
            }
        except Exception as e:
            return {'error': str(e), 'success': False}
    
    def _identify_risk_factors(self, patient_data: Dict) -> List[str]:
        """Identify risk factors from symptoms"""
        risk_factors = []
        
        symptom_map = {
            'Polyuria': 'Frequent urination',
            'Polydipsia': 'Excessive thirst',
            'sudden weight loss': 'Sudden weight loss',
            'weakness': 'General weakness',
            'Polyphagia': 'Excessive hunger',
            'Genital thrush': 'Genital thrush',
            'visual blurring': 'Blurred vision',
            'Itching': 'Persistent itching',
            'Irritability': 'Irritability',
            'delayed healing': 'Delayed wound healing',
            'partial paresis': 'Partial paralysis',
            'muscle stiffness': 'Muscle stiffness',
            'Alopecia': 'Hair loss',
            'Obesity': 'Obesity'
        }
        
        for symptom, description in symptom_map.items():
            val = patient_data.get(symptom)
            if val == 1 or val == 'Yes':
                risk_factors.append(description)
        
        age = patient_data.get('Age', 0)
        if age > 45:
            risk_factors.append(f"Age ({age} years)")
        
        return risk_factors
    
    def fallback_prediction(self, input_data: Dict) -> Dict:
        """Fallback prediction using symptom counting"""
        try:
            symptom_features = [
                'Polyuria', 'Polydipsia', 'sudden weight loss', 'weakness',
                'Polyphagia', 'Genital thrush', 'visual blurring', 'Itching',
                'Irritability', 'delayed healing', 'partial paresis',
                'muscle stiffness', 'Alopecia', 'Obesity'
            ]
            
            symptom_count = sum(1 for s in symptom_features if input_data.get(s) in ['Yes', 1])
            symptom_ratio = symptom_count / len(symptom_features)
            
            if symptom_ratio > 0.5:
                prediction = 'High Risk'
                confidence = min(0.90, 0.70 + symptom_ratio * 0.3)
            elif symptom_ratio > 0.25:
                prediction = 'Moderate Risk'
                confidence = min(0.85, 0.65 + symptom_ratio * 0.3)
            else:
                prediction = 'Low Risk'
                confidence = min(0.90, 0.75 + (1 - symptom_ratio) * 0.2)
            
            return {
                'prediction': prediction,
                'confidence': round(float(confidence), 3),
                'symptom_count': symptom_count,
                'model_type': 'fallback',
                'success': True
            }
        except Exception as e:
            return {'prediction': 'Analysis Error', 'error': str(e), 'success': False}


# Convenience function
def create_diabetes_predictor(model_path: str = None) -> DiabetesPredictor:
    """Create a diabetes predictor instance"""
    return DiabetesPredictor(model_path)


if __name__ == "__main__":
    predictor = create_diabetes_predictor()
    
    sample = {
        'Age': 45, 'Gender': 'Male',
        'Polyuria': 'Yes', 'Polydipsia': 'Yes',
        'sudden weight loss': 'No', 'weakness': 'Yes',
        'Polyphagia': 'No', 'Genital thrush': 'No',
        'visual blurring': 'Yes', 'Itching': 'No',
        'Irritability': 'No', 'delayed healing': 'No',
        'partial paresis': 'No', 'muscle stiffness': 'No',
        'Alopecia': 'No', 'Obesity': 'Yes'
    }
    
    result = predictor.predict(sample)
    print(f"Result: {result}")
