import joblib
import pandas as pd
import numpy as np
import json
import os
from typing import Dict, Any

class DelayPredictor:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.model_type = None
        self.label_encoder = None
        self.load_model()
    
    def load_model(self):
        #load the trained model and its metadata
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            model_path = os.path.join(current_dir, 'trained_model.pkl')
            metadata_path = os.path.join(current_dir, 'model_metadata.json')
            encoder_path = os.path.join(current_dir, 'route_label_encoder.pkl')

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")
            if not os.path.exists(metadata_path):
                raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
            if not os.path.exists(encoder_path):
                raise FileNotFoundError(f"Encoder file not found: {encoder_path}")
            
            self.model = joblib.load(model_path)
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.feature_columns = metadata['feature_columns']
                self.model_type = metadata['model_type']
            
            self.label_encoder = joblib.load(encoder_path)
                
            print(f"✅ Loaded {self.model_type} model with {len(self.feature_columns)} features")
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def prepare_features(self, input_data: Dict[str, Any]) -> pd.DataFrame:#prepare input
        try:

            features_dict = {}
            
            if 'route_short_name' in input_data and self.label_encoder is not None:
                try:
                    route_encoded = self.label_encoder.transform([input_data['route_short_name']])[0]
                    features_dict['route_encoded'] = route_encoded
                except ValueError:
                    features_dict['route_encoded'] = 0
                    print(f"Route '{input_data['route_short_name']}' not in training data, using default encoding")
            
            feature_mapping = {
                'stop_sequence': 'stop_sequence',
                'day_of_week': 'day_of_week', 
                'hour_of_day': 'hour_of_day',
                'holiday_flag': 'holiday_flag',
                'stop_lat': 'stop_lat',
                'stop_lon': 'stop_lon'
            }
            
            for api_feature, model_feature in feature_mapping.items():
                if api_feature in input_data:
                    features_dict[model_feature] = input_data[api_feature]
            
            #creating datafarames
            features_df = pd.DataFrame([features_dict])
            
            if self.feature_columns:
                for col in self.feature_columns:
                    if col not in features_df.columns:
                        features_df[col] = 0
                features_df = features_df[self.feature_columns]
            
            return features_df
            
        except Exception as e:
            print(f"Error preparing features: {e}")
            raise
    
    def predict_delay(self, input_data: Dict[str, Any]) -> float:
        """Predict delay for given input data"""
        try:
            if self.model is None:
                raise ValueError("Model not loaded. Call load_model() first.")
            
            features = self.prepare_features(input_data)
            prediction = self.model.predict(features)
            return float(prediction[0])
            
        except Exception as e:
            print(f"Error making prediction: {e}")
            raise

#Create a singleton instance
delay_predictor = DelayPredictor()