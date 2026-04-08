# TourZen - Tourism Management & Forecasting Dashboard

TourZen is a modern tourism management application built with Flask and Firebase. It provides a comprehensive platform for managing tourism-related data, visualizing trends, and leveraging machine learning for predictive analysis.

## 🚀 Features

- **User Authentication**: Secure Login and Signup functionality.
- **Dynamic Dashboard**: Centralized view for tourism data and statistics.
- **Place Management**: Add, view, and manage various tourist attractions.
- **Review System**: Track and analyze user feedback on places.
- **Trend Forecasting**: Advanced analysis of tourism trends using predictive logic.
- **Event Coordination**: Manage and display tourism-related events.
- **Data Integration**: Processes raw, cleaned, and unstructured tourism data.

## 🛠️ Tech Stack

- **Backend**: Python (Flask)
- **Database**: Firebase Realtime Database
- **ML/Processing**: Scikit-learn, Pandas, NumPy
- **Frontend**: HTML5, Vanilla CSS, Bootstrap
- **Environment**: Dotenv for configuration, Firebase Admin SDK for secure access.

## 📁 Project Structure

```text
tourzen_app/
├── app.py                  # Main application entry point
├── routes/                 # Blueprints for modular route management
│   ├── auth_routes.py      # User authentication login/signup logic
│   ├── api_dashboard.py    # Core dashboard API endpoints
│   ├── trends_routes.py    # Predictive analytics and trend logic
│   └── ...                 # Additional feature routes
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JavaScript and image assets
├── data/                   # Data storage (Raw, Cleaned, Unstructured)
├── utils/                  # Helper functions and utilities
└── firebase_config.py      # Firebase Admin SDK initialization
```

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.8+
- A [Firebase Project](https://console.firebase.google.com/)

### 2. Environment Configuration
Create a `.env` file in the root directory and add your secret keys:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_tourzen_secret_key
# Other necessary environment variables
```

### 3. Firebase SDK Setup
Place your Firebase service account key in the root directory as `tourzen-firebase-adminsdk.json`.

### 4. Installation
Install the required Python packages:
```bash
pip install flask python-dotenv firebase-admin pandas scikit-learn numpy
```

### 5. Running the Application
```bash
python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

## 📈 ML Model Evaluation
The project includes tools for evaluating the predictive models:
- `evaluate_model.py`: Script for performance metrics.
- `model_evaluation_scatter.png`: Visual evaluation of prediction results.
- `model_selection_residuals.png`: Residual analysis for model accuracy.

