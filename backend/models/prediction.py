# import joblib
# import pandas as pd
# import numpy as np
# import json
# import os
# from typing import Dict, Any

# class DelayPredictor:
#     def __init__(self):
#         self.model = None
#         self.feature_columns = None
#         self.model_type = None
#         self.label_encoder = None
#         self.load_model()
    
#     def load_model(self):#loading trained model&its metadata
#         try:
#             model_path = os.path.join(os.path.dirname(__file__), 'trained_model.pkl')
#             metadata_path = os.path.join(os.path.dirname(__file__), 'model_metadata.json')
#             encoder_path = os.path.join(os.path.dirname(__file__), 'route_label_encoder.pkl')
            
#             self.model = joblib.load(model_path)
            
#             with open(metadata_path, 'r') as f:
#                 metadata = json.load(f)
#                 self.feature_columns = metadata['feature_columns']
#                 self.model_type = metadata['model_type']

#             self.label_encoder = joblib.load(encoder_path)
                
#             print(f"Loaded {self.model_type} model with {len(self.feature_columns)} features")
            
#         except Exception as e:
#             print(f"Error loading model: {e}")
#             raise
    
#     def prepare_features(self, input_data: Dict[str, Any]) -> pd.DataFrame:
#         #prepare input data
#         features_dict = {}

#         if 'route_short_name' in input_data and self.label_encoder:
#             try:
#                 route_encoded = self.label_encoder.transform([input_data['route_short_name']])[0]
#                 features_dict['route_encoded'] = route_encoded
#             except:

#                 features_dict['route_encoded'] = 0

#         for feature in ['stop_sequence', 'day_of_week', 'hour_of_day', 
#                        'holiday_flag', 'stop_lat', 'stop_lon']:
#             if feature in input_data:
#                 features_dict[feature] = input_data[feature]
        
#         features_df = pd.DataFrame([features_dict])
        
#         for col in self.feature_columns:
#             if col not in features_df.columns:
#                 features_df[col] = 0
        
#         features_df = features_df[self.feature_columns]
        
#         return features_df
    
#     def predict_delay(self, input_data: Dict[str, Any]) -> float:
#         """Predict delay for given input data"""
#         try:
#             features = self.prepare_features(input_data)
#             prediction = self.model.predict(features)
#             return float(prediction[0])
#         except Exception as e:
#             print(f"Error making prediction: {e}")
#             raise

# delay_predictor = DelayPredictor()