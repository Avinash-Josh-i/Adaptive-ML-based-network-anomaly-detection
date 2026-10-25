# Adaptive ML-Based Network Anomaly Detection

An experimental machine-learning-based Intrusion Detection System (IDS) designed to analyze network traffic, extract traffic-flow features, and identify potentially anomalous network activity.

The project combines a C++ network traffic feature-extraction component with Python-based machine learning, model evaluation, and a Streamlit monitoring interface.

It includes scripts for training and evaluating multiple machine learning models, comparing their classification performance, and examining detection results.

> **Project status:** Research and development project. Detection accuracy, real-time performance, and operational readiness must be evaluated in the intended environment before deployment.

## Key Features

### 1. Network Traffic Feature Extraction

The `feature_extract/` component contains C++ source code and Windows batch scripts for building and running the feature extractor.

Its included executable is intended to support operations such as listing network interfaces and collecting traffic statistics.

The extractor and monitoring application are designed to work with generated traffic-flow and statistics files.

### 2. Machine Learning-Based Detection

The project contains Python scripts for training and evaluating several machine learning classifiers.

The included model-training scripts cover:

- Decision Tree.
- Random Forest.
- LightGBM.
- XGBoost.

These models can be compared to investigate their suitability for network anomaly detection.

### 3. Model Evaluation and Comparison

The `testingMinor/compare/` directory contains scripts and generated figures for comparing model performance.

Evaluation artifacts include:

- F1 and ROC-AUC comparisons.
- Confusion matrices.
- Precision-recall curves.
- ROC curves.
- False-positive analysis.
- Classification threshold metrics.

These metrics help assess the trade-offs between detecting malicious activity and incorrectly flagging normal traffic.

### 4. Streamlit Monitoring Interface

The Streamlit application in `testingMinor/app.py` provides a graphical interface intended to display network monitoring information.

Its code includes functionality for:

- Selecting a network interface.
- Starting a traffic-capture session.
- Tracking captured packet statistics.
- Loading generated statistics and flow records.
- Displaying anomaly history.
- Reading model prediction output.
- Clearing locally stored monitoring history.

Some operations depend on the external feature-extraction executable and its expected output files.

### 5. Data Processing and Prediction

The project includes scripts for preparing data, merging CICIDS-related datasets, collecting predictions, and evaluating model outputs.

These components support experimentation with anomaly detection pipelines.

## Technology Stack

| Technology | Purpose |
|---|---|
| C++ | Network traffic feature extraction |
| Python | Data processing and model training |
| scikit-learn | Machine learning algorithms and evaluation |
| LightGBM | Gradient-boosting classifier |
| XGBoost | Gradient-boosting classifier |
| NumPy | Numerical computation |
| pandas | Dataset processing |
| Matplotlib | Evaluation plots |
| Streamlit | Monitoring interface |
| Altair | Interactive data visualization |
| psutil | System and process information |
| Windows executable | Included feature-extraction binary |

**Important:** The current `requirements.txt` does not list every dependency imported by the Streamlit application. In particular, `streamlit`, `psutil`, and `altair` should be checked and installed if they are missing.

## Project Structure

```text
adaptive_ml_based_anomaly_detection-main/
├── README.md
├── requirements.txt
├── .gitignore
├── feature_extract/
│   ├── build.bat
│   ├── run.bat
│   ├── bin/
│   │   └── main.exe
│   ├── data/
│   │   └── .gitkeep
│   └── src/
│       └── main.cpp
└── testingMinor/
    ├── app.py
    ├── merge_cicids.py
    ├── predic_anomalypkl.py
    ├── predict_anomalyjson.py
    ├── train_decision_tree.py
    ├── train_lightgbm.py
    ├── train_random_forest.py
    └── compare/
        ├── collect_predictions.py
        ├── evaluate_models.py
        ├── prepare_test_set.py
        └── figures/
            ├── compare_f1_rocauc.png
            ├── confusion_DecisionTree.png
            ├── confusion_LightGBM.png
            ├── confusion_RandomForest.png
            ├── confusion_XGBoost.png
            ├── false_positives.png
            ├── pr_curves_all_models.png
            ├── roc_curves_all_models.png
            ├── roc_curves_zoomed.png
            └── threshold_metrics.png
```

*The repository may contain additional generated files and directories.*

## Prerequisites

- Python 3.10 or newer is recommended.
- pip.
- A C++ compiler for rebuilding the feature extractor.
- Windows for the supplied `.exe` and batch scripts, unless the feature extractor is adapted for another operating system.
- Network interface access and any required packet-capture permissions.
- Suitable network traffic datasets for model training and evaluation.
- Administrator privileges or appropriate capture permissions where required by the capture implementation.

The Streamlit dashboard and model evaluation scripts may be usable independently of the Windows executable, but their exact dependencies and file-path assumptions must be satisfied.

## Installation

### Step 1: Clone or extract the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd adaptive_ml_based_anomaly_detection-main
```

Alternatively, extract the project ZIP and open a terminal in the extracted directory.

### Step 2: Create a virtual environment

On Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install the listed dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The repository's requirements file pins versions of several scientific Python libraries.

**Compatibility note:** Some pinned versions may not be available for every Python version or operating system. If installation fails, check the Python version and the availability of compatible package wheels.

### Step 4: Install the dashboard dependencies

The monitoring application imports Streamlit, pandas, psutil, and Altair.

Install any missing dependencies:

```bash
pip install streamlit psutil altair
```

Check that the packages are available:

```bash
python -c "import streamlit, pandas, psutil, altair; print('Dashboard dependencies are available.')"
```

## Running the Monitoring Dashboard

From the repository root, activate your virtual environment and run:

```bash
streamlit run testingMinor/app.py
```

Streamlit will print a local address in the terminal. Open that address in your browser.

**Important:** The dashboard currently uses relative paths that point to a different project directory:

```text
adaptive_ml_based_network_anamoly_detection/
```

However, the supplied repository is named:

```text
adaptive_ml_based_anomaly_detection-main/
```

Because of this discrepancy, the dashboard may fail to find `main.exe` and its associated CSV files when run directly from the extracted repository.

Before using the live capture functionality, update the path constants in `testingMinor/app.py` to match the actual location of the `feature_extract/bin/` directory.

The application also uses Windows-specific process-launching behavior. Running the capture workflow on Linux will require adapting that code and ensuring the feature extractor is available as a compatible Linux executable.

## Building the Feature Extractor

The repository includes:

```text
feature_extract/src/main.cpp
feature_extract/build.bat
feature_extract/run.bat
feature_extract/bin/main.exe
```

The included executable and batch scripts target Windows.

To rebuild the executable on Windows:

1. Install the C++ compiler and other build dependencies required by the source code.
2. Inspect `build.bat` to understand the compiler and build configuration it expects.
3. Run the build script from the appropriate directory.
4. Confirm that the executable is generated successfully.
5. Test interface discovery before starting a capture session.

The exact build command depends on the compiler and external libraries referenced by the C++ source.

On Linux, you will need to create a compatible build process rather than relying on the supplied Windows executable and batch files.

## Model Training and Evaluation

The `testingMinor/` directory contains scripts for model training, data preparation, prediction, and evaluation.

### Train a Decision Tree

```bash
python testingMinor/train_decision_tree.py
```

### Train a Random Forest

```bash
python testingMinor/train_random_forest.py
```

### Train a LightGBM Model

```bash
python testingMinor/train_lightgbm.py
```

### Prepare the Test Set

```bash
python testingMinor/compare/prepare_test_set.py
```

### Collect Model Predictions

```bash
python testingMinor/compare/collect_predictions.py
```

### Evaluate the Models

```bash
python testingMinor/compare/evaluate_models.py
```

**Note:** These commands identify the repository's available scripts; successful execution depends on the input datasets, expected file locations, trained model artifacts, and configuration referenced by each script. Inspect each script before running it to confirm the required inputs.

The XGBoost model is represented in the evaluation artifacts, but the supplied file listing does not establish a dedicated XGBoost training script.

## Dataset Requirements

Machine learning results depend on the quality and representativeness of the training and evaluation data.

The repository includes a dataset-merging script:

```bash
python testingMinor/merge_cicids.py
```

Inspect the script to determine the expected source dataset files and their locations before executing it.

For reliable evaluation:

- Use consistent feature definitions during training and prediction.
- Separate training and test data appropriately.
- Avoid data leakage between datasets.
- Examine class imbalance.
- Report precision, recall, F1-score, ROC-AUC, and false-positive rates where appropriate.
- Evaluate performance on data representative of the intended deployment environment.

Do not assume that a model trained on a benchmark dataset will reliably identify every real-world attack.

## Output Files and Monitoring Data

The dashboard references generated files for statistics, traffic flows, anomaly history, and predictions.

Examples include:

```text
stats.csv
stats_history.csv
anomaly_log.csv
flows.csv
prediction_output.csv
```

Their exact locations depend on the application's configured paths.

Some files are created or updated by the feature extractor, while others are used by the dashboard or prediction workflow.

Ensure the necessary directories exist and that the application has permission to read and write the files.

## Troubleshooting

### Streamlit is not installed

Activate the project's virtual environment and run:

```bash
pip install streamlit
```

### The feature extractor cannot be found

Check the executable path in `testingMinor/app.py`.

Ensure that it points to the actual location of `feature_extract/bin/main.exe` and that the process working directory is correct.

### The dashboard runs, but no statistics appear

Verify that:

- The feature extractor starts successfully.
- The correct network interface is selected.
- The capture session has permission to collect traffic.
- The expected output CSV files are being generated.
- The dashboard reads from the same directory in which the extractor writes its files.

### The application fails on Linux

The supplied executable and batch scripts are Windows-oriented. Porting the live capture workflow requires rebuilding the C++ component for Linux and adapting Windows-specific process-management code.

### Model evaluation fails

Check that the input datasets exist, that their columns match the expected features, and that the required model artifacts have been generated.

## Security and Ethical Considerations

This project is intended for authorized network monitoring, research, and defensive security analysis.

- Capture traffic only on networks you own or are authorized to monitor.
- Obtain the required permissions before collecting packet or flow data.
- Protect traffic logs because they may contain sensitive information.
- Avoid storing unnecessary personal or confidential data.
- Evaluate false positives and false negatives before relying on automated alerts.
- Do not use model predictions as the sole basis for high-impact security decisions.

## Future Improvements

Potential enhancements include:

- Cross-platform support for the feature extractor.
- A consistent configuration system for executable and data paths.
- Automated dependency and environment checks.
- Improved real-time prediction integration.
- More robust model artifact management.
- Additional evaluation on representative network traffic.
- Unit and integration tests.
- Improved alert handling and anomaly explanations.
- Documented setup instructions for Linux and Windows.
- Continuous monitoring with appropriate performance and resource limits.

## License

Add the applicable license information before distributing the project.

---

**Adaptive ML-Based Network Anomaly Detection** — Exploring machine learning for network traffic analysis and intrusion detection.