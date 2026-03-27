# RouteMinds by Yajush

RouteMinds is an intelligent transit routing and delay prediction system designed to optimize bus routes and provide accurate travel time estimates for Delhi's bus network. It combines historical data, real-time traffic information, and machine learning to deliver efficient transit solutions.

## 🚀 Features

- **Intelligent Route Optimization**: Recommends optimal bus routes based on historical performance and real-time conditions
- **Delay Prediction**: Predicts bus delays using machine learning models trained on historical data
- **Real-Time Integration**: Supports real-time traffic data integration for accurate predictions
- **Scalable Architecture**: Built on FastAPI with a modular, service-oriented design
- **Production-Ready**: Includes health checks, exception handling, and CORS support

## 🛠️ Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python web framework
- **Frontend Framework**: [React](https://react.dev/) + [Vite](https://vite.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **UI Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Machine Learning**: [TensorFlow/Keras](https://www.tensorflow.org/), [Scikit-learn](https://scikit-learn.org/), [XGBoost](https://xgboost.ai/)
- **Data Processing**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Database**: [Firebase Firestore](https://firebase.google.com/docs/firestore) (NoSQL)
- **Deployment**: Docker, Uvicorn, Gunicorn

## 📂 Project Structure

```
RouteMinds/
├── apps/
│   └── web/                          # React + Vite frontend app
│       ├── src/
│       ├── public/
│       ├── package.json
│       ├── vite.config.ts
│       └── tsconfig.json
├── packages/
│   └── ui/                           # Shared UI components/utilities
│       ├── src/components/
│       ├── src/hooks/
│       ├── src/lib/
│       └── package.json
├── api/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py         # Health check endpoints
│   │   │       ├── predictions.py    # Delay prediction endpoints
│   │   │       └── routes.py         # Route optimization endpoints
│   │   ├── core/
│   │   │   ├── config.py             # Configuration management
│   │   │   └── exceptions.py         # Custom exception handling
│   │   ├── ml/                       # Machine learning models and utilities
│   │   ├── schemas/                  # Pydantic data models
│   │   ├── services/                 # Business logic and external integrations
│   │   └── main.py                   # FastAPI application entry point
│   ├── requirements.txt              # Python dependencies
│   └── environment.yml               # Conda environment configuration
├── bun.lock                          # Bun lockfile
├── package.json                      # Workspace + Turbo scripts
├── turbo.json                        # Turbo task pipeline
└── data/                             # Datasets and model artifacts
```

## ⚙️ Setup

### Prerequisites

- Bun 1.2+ (workspace package manager/runtime)
- Python 3.11+
- Node.js 20+ (optional, recommended for compatibility)
- Conda (recommended for backend environment management)
- Docker (optional, for containerized backend deployment)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd RouteMinds
   ```

2. **Set up backend (`api/`)**

   ```bash
   cd api
   conda env create -f environment.yml
   conda activate route_minds
   pip install -r requirements.txt
   ```

3. **Configure backend environment variables**
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

4. **Install monorepo dependencies (root workspace)**

   ```bash
   bun install
   ```

## 🏃 Running the App

### Backend (Development Mode)

```bash
cd api
uvicorn app.main:app --reload --host [IP_ADDRESS] --port 8000
```

### Frontend (Development Mode)

```bash
bun run dev
```

This runs the Turbo `dev` pipeline and starts the web app (`apps/web`) locally.

### Frontend (Other common tasks)

```bash
bun run typecheck
bun run lint
bun run build
```

### Backend (Production Mode)

```bash
cd api
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

### Frontend App

- **Vite Dev Server**: shown in terminal (usually http://localhost:5173)

## 🏗️ Architecture

### Backend Architecture

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
