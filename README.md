# RouteMinds

RouteMinds is an intelligent transit routing and delay prediction system designed to optimize bus routes and provide accurate travel time estimates for Delhi's bus network. It combines historical data, real-time traffic information, and machine learning to deliver efficient transit solutions.

## 🚀 Features

- **Intelligent Route Optimization**: Recommends optimal bus routes based on historical performance and real-time conditions
- **Delay Prediction**: Predicts bus delays using machine learning models trained on historical data
- **Real-Time Integration**: Supports real-time traffic data integration for accurate predictions
- **Scalable Architecture**: Built on FastAPI with a modular, service-oriented design
- **Production-Ready**: Includes health checks, exception handling, and CORS support

## 🛠️ Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python web framework
- **Machine Learning**: [TensorFlow/Keras](https://www.tensorflow.org/), [Scikit-learn](https://scikit-learn.org/), [XGBoost](https://xgboost.ai/)
- **Data Processing**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Database**: [Firebase Firestore](https://firebase.google.com/docs/firestore) (NoSQL)
- **Deployment**: Docker, Uvicorn, Gunicorn

## 📂 Project Structure

```
api/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── health.py         # Health check endpoints
│   │   │   ├── predictions.py    # Delay prediction endpoints
│   │   │   └── routes.py         # Route optimization endpoints
│   │   ├── __init__.py
│   ├── core/
│   │   ├── config.py             # Configuration management
│   │   ├── exceptions.py         # Custom exception handling
│   │   └── __init__.py
│   ├── ml/                       # Machine learning models and utilities
│   │   ├── __init__.py
│   ├── schemas/                  # Pydantic data models
│   │   ├── __init__.py
│   ├── services/                 # Business logic and external integrations
│   │   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   └── __init__.py
├── .env                          # Environment variables (not in git)
├── requirements.txt              # Python dependencies
├── environment.yml               # Conda environment configuration
└── Dockerfile                    # Docker build configuration
```

## ⚙️ Setup

### Prerequisites

- Python 3.11+
- Conda (recommended for environment management)
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd RouteMinds/api
   ```

2. **Create Conda environment**
   ```bash
   conda env create -f environment.yml
   conda activate route_minds
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the `api/` directory:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration:
   ```env
   # Application settings
   APP_NAME="RouteMinds API"
   APP_VERSION="1.0.0"
   DEBUG=true

   # Firebase configuration
   FIREBASE_CREDENTIALS_PATH="path/to/serviceAccountKey.json"
   FIREBASE_PROJECT_ID="your-project-id"

   # Model paths
   MODEL_PATH="path/to/your/model.pkl"
   ```

## 🏃 Running the Server

### Development Mode

```bash
uvicorn app.main:app --reload --host [IP_ADDRESS] --port 8000
```

### Production Mode

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b [IP_ADDRESS]:8000
```

## 🧪 Testing

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Architecture

### Service Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│  (Routing, Middleware, Exception Handling)                  │
└─────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                         API Layer                             │
│  /health, /routes, /predictions                             │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                        Services Layer                         │
│  - RouteService: Route optimization logic                   │
│  - PredictionService: Delay prediction logic                │
│  - FirebaseService: Database integration                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                        ML Layer                             │
│  - DelayPredictionModel: TensorFlow/Keras models            │
│  - RouteOptimizationModel: XGBoost/Scikit-learn             │
│  - FeatureEngineering: Data preprocessing                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                        Data Layer                           │
│  - Firebase Firestore: Real-time data storage               │
│  - Local Files: Model artifacts, historical data            │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 ML Models

### Delay Prediction Model
- **Framework**: TensorFlow/Keras
- **Input Features**: Time-based (hour, day, month), route-based, weather conditions
- **Output**: Predicted delay in minutes
- **Location**: `api/app/ml/models/delay_prediction_model.h5`

### Route Optimization Model
- **Framework**: XGBoost, Scikit-learn
- **Input Features**: Route characteristics, demand patterns, traffic data
- **Output**: Optimal route recommendations
- **Location**: `api/app/ml/models/route_optimization_model.pkl`

## 📦 Deployment

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t routeminds-api .
   ```

2. **Run the container**
   ```bash
   docker run -d -p 8000:8000 --env-file .env routeminds-api
   ```

### Kubernetes Deployment

See `kubernetes/` directory for deployment manifests:

```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Create a feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
3. Push to the branch (`git push origin feature/AmazingFeature`)
4. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For issues or questions, please open an issue in the repository.
