# DiaBot

DiaBot is an AI-powered chatbot designed to assist with diabetes management. It integrates machine learning models for diabetes prediction, a conversational interface, and blockchain technology for secure data handling.

## Features

- **Diabetes Prediction**: Uses machine learning models trained on diabetes datasets to predict risk levels.
- **Chatbot Interface**: Interactive chatbot for user queries and guidance on diabetes management.
- **Blockchain Integration**: Secure storage and verification of health data using blockchain.
- **Web Frontend**: User-friendly web interface built with HTML, CSS, and JavaScript.
- **Flask Backend**: Python-based backend handling API requests and model inference.

## Project Structure

- `backend/`: Contains Python scripts for the Flask server, ML models, chatbot logic, and blockchain integration.
- `frontend/`: Web interface files including templates and static assets.
- `instance/`: Instance-specific data.
- `uploads/`: Directory for uploaded files.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Krishna-Vijay-G/DiaBot.git
   cd DiaBot
   ```

2. Install Python dependencies (ensure you have Python 3.8+):
   ```
   pip install -r requirements.txt
   ```
   (Note: Create `requirements.txt` if not present with necessary packages like Flask, scikit-learn, etc.)

3. Run the backend server:
   ```
   python backend/run.py
   ```

4. Open the frontend in a web browser by navigating to `http://localhost:5000` or the configured port.

## Usage

- Access the web interface to interact with the chatbot.
- Upload data for diabetes prediction.
- View results and blockchain-verified information.

## Contributing

Contributions are welcome. Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.