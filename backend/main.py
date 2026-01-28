"""
DiaBot - AI-Powered Diabetes Screening Platform
Main Application File

Combines: Flask app, routes, database models, and configuration
"""

import os
import uuid
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
import dotenv

# Load environment variables
dotenv.load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

db = SQLAlchemy()

def _make_db_uri(db_filename):
    """Create SQLite database URI with proper path handling - stored in instance folder"""
    db_path = os.path.join(BASE_DIR, 'instance', db_filename)
    return f"sqlite:///{db_path.replace(chr(92), '/')}"


class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get("SESSION_SECRET") or "dev-secret-key-change-in-production-12345"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or _make_db_uri('diabot.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configure engine options based on database type
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
        # SQLite-specific configuration for better concurrency
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"check_same_thread": False},  # Allow multi-threaded access
            "poolclass": None,  # Disable connection pooling for SQLite
            "isolation_level": None,  # SQLite handles transactions differently
        }
    else:
        # PostgreSQL/MySQL configuration
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 300, "pool_pre_ping": True}
    
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    DIABETES_MODEL_PATH = os.path.join(MODELS_DIR, 'Diabetes_Model', 'diab_model.joblib')
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'frontend', 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'frontend', 'static')
    INSTANCE_FOLDER = os.path.join(BASE_DIR, 'instance')


# =============================================================================
# Database Models
# =============================================================================

class User(db.Model):
    """Model for storing user accounts"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.BigInteger, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    admin = db.Column(db.Boolean, default=False)
    
    # Relationship to diagnostic results
    diagnostic_results = db.relationship('DiagnosticResult', backref='user', lazy=True)
    
    def set_password(self, password: str):
        """Hash and set the password"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'admin': self.admin
        }


class DiagnosticResult(db.Model):
    """Model for storing diagnostic results"""
    __tablename__ = 'diagnostic_results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    result_type = db.Column(db.String(50), nullable=False)
    input_data = db.Column(db.JSON, nullable=False)
    prediction = db.Column(db.JSON, nullable=False)
    educational_content = db.Column(db.Text, default="")
    image_path = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    disclaimer_shown = db.Column(db.Boolean, default=True)
    
    chat_conversations = db.relationship('ChatConversation', backref='diagnostic_result', lazy=True)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'result_type': self.result_type,
            'input_data': self.input_data,
            'prediction': self.prediction,
            'educational_content': self.educational_content,
            'image_path': self.image_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'disclaimer_shown': self.disclaimer_shown
        }
    
    @classmethod
    def create(cls, result_data: Dict) -> 'DiagnosticResult':
        return cls(
            result_type=result_data['result_type'],
            input_data=result_data['input_data'],
            prediction=result_data['prediction'],
            educational_content=result_data.get('educational_content', ''),
            image_path=result_data.get('image_path', '')
        )


class ChatConversation(db.Model):
    """Model for storing chat conversations"""
    __tablename__ = 'chat_conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), default="Medical Consultation")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    diagnostic_result_id = db.Column(db.String(36), db.ForeignKey('diagnostic_results.id'), nullable=True)
    
    messages = db.relationship('ChatMessage', backref='conversation', lazy=True, order_by='ChatMessage.created_at')
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'session_id': self.session_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_at_dt': self.created_at,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_at_dt': self.updated_at,
            'diagnostic_result_id': self.diagnostic_result_id,
            'messages': [msg.to_dict() for msg in self.messages]
        }


class ChatMessage(db.Model):
    """Model for storing chat messages"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('chat_conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='text')
    message_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'message_type': self.message_type,
            'metadata': self.message_metadata,
            'timestamp': self.created_at,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BlockchainBlock(db.Model):
    """Model for storing blockchain blocks"""
    __tablename__ = 'blockchain_blocks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    index = db.Column(db.Integer, nullable=False, unique=True)
    timestamp = db.Column(db.String(100), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    previous_hash = db.Column(db.String(64), nullable=False)
    hash = db.Column(db.String(64), nullable=False, unique=True)
    nonce = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce
        }


# =============================================================================
# Database Service Functions
# =============================================================================

def save_result(result_data: Dict, user_id: Optional[str] = None) -> str:
    """Save diagnostic result and return ID"""
    try:
        result = DiagnosticResult.create(result_data)
        result.user_id = user_id
        db.session.add(result)
        db.session.commit()
        
        # Get username for blockchain
        username = "Anonymous"
        if user_id:
            user = User.query.get(user_id)
            if user:
                username = user.username
        
        # Get prediction info for blockchain
        prediction = result_data.get('prediction', {})
        risk_level = prediction.get('prediction', 'Unknown')
        probability = prediction.get('raw_probability', prediction.get('confidence', 0))
        
        # Add to blockchain with user info and result
        try:
            from blockchain import Blockchain
            blockchain = Blockchain(db.session)
            blockchain.add_diagnostic_record({
                'result_id': result.id,
                'result_type': result.result_type,
                'timestamp': result.created_at.isoformat() if result.created_at else None,
                'user': username,
                'risk_level': risk_level,
                'probability': probability
            })
            logging.info(f"Added result {result.id} to blockchain")
        except Exception as e:
            logging.warning(f"Failed to add result to blockchain: {e}", exc_info=True)
        
        return result.id
    except Exception as e:
        logging.error(f"Error saving result: {e}")
        db.session.rollback()
        raise


def get_result(result_id: str) -> Optional[Dict]:
    """Retrieve diagnostic result by ID"""
    try:
        result = DiagnosticResult.query.get(result_id)
        return result.to_dict() if result else None
    except Exception as e:
        logging.error(f"Error retrieving result: {e}")
        return None


def create_chat_conversation(session_id: str, diagnostic_result_id: Optional[str] = None,
                              title: str = "Medical Consultation") -> str:
    """Create a new chat conversation"""
    try:
        conversation = ChatConversation(
            session_id=session_id,
            diagnostic_result_id=diagnostic_result_id,
            title=title
        )
        db.session.add(conversation)
        db.session.commit()
        return conversation.id
    except Exception as e:
        logging.error(f"Error creating conversation: {e}")
        db.session.rollback()
        raise


def get_chat_conversation(conversation_id: str) -> Optional[Dict]:
    """Retrieve chat conversation by ID"""
    try:
        conversation = ChatConversation.query.get(conversation_id)
        if not conversation:
            return None
        conv = conversation.to_dict()
        # Ensure datetime objects available for templates
        try:
            if conv.get('created_at') and not conv.get('created_at_dt'):
                conv['created_at_dt'] = datetime.fromisoformat(conv['created_at'])
        except Exception:
            conv['created_at_dt'] = None

        # Normalize message timestamps
        for m in conv.get('messages', []):
            try:
                if isinstance(m.get('timestamp'), str):
                    m['timestamp'] = datetime.fromisoformat(m['timestamp'])
            except Exception:
                # leave as-is if parsing fails
                pass

        return conv
    except Exception as e:
        logging.error(f"Error retrieving conversation: {e}")
        return None


def get_conversations_by_session(session_id: str) -> List[Dict]:
    """Get all conversations for a session"""
    try:
        conversations = ChatConversation.query.filter_by(
            session_id=session_id
        ).order_by(ChatConversation.updated_at.desc()).all()
        convs = [conv.to_dict() for conv in conversations]
        # Ensure datetime objects for created_at and message timestamps
        for conv in convs:
            try:
                if conv.get('created_at') and not conv.get('created_at_dt'):
                    conv['created_at_dt'] = datetime.fromisoformat(conv['created_at'])
            except Exception:
                conv['created_at_dt'] = None

            for m in conv.get('messages', []):
                try:
                    if isinstance(m.get('timestamp'), str):
                        m['timestamp'] = datetime.fromisoformat(m['timestamp'])
                except Exception:
                    pass

        return convs
    except Exception as e:
        logging.error(f"Error retrieving conversations: {e}")
        return []


def add_chat_message(conversation_id: str, role: str, content: str,
                     message_type: str = 'text', metadata: Optional[Dict] = None) -> str:
    """Add a message to a conversation"""
    try:
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_type=message_type,
            message_metadata=metadata
        )
        db.session.add(message)
        
        conversation = ChatConversation.query.get(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        return message.id
    except Exception as e:
        logging.error(f"Error adding message: {e}")
        db.session.rollback()
        raise


def save_blockchain_block(block_data: Dict) -> bool:
    """Save a blockchain block to the database"""
    try:
        block = BlockchainBlock(
            index=block_data['index'],
            timestamp=block_data['timestamp'],
            data=block_data['data'],
            previous_hash=block_data['previous_hash'],
            hash=block_data['hash'],
            nonce=block_data.get('nonce', 0)
        )
        db.session.add(block)
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving blockchain block: {e}")
        db.session.rollback()
        return False


def get_blockchain_blocks() -> List:
    """Retrieve all blockchain blocks"""
    try:
        return BlockchainBlock.query.order_by(BlockchainBlock.index.asc()).all()
    except Exception as e:
        logging.error(f"Error retrieving blockchain blocks: {e}")
        return []


# =============================================================================
# Result Explanations
# =============================================================================

DIABETES_EXPLANATIONS = {
    'High Risk': {
        'explanation': 'Your symptom profile indicates a high likelihood of diabetes mellitus based on multiple clinical indicators.',
        'causes': [
            'Excessive urination (polyuria)', 'Excessive thirst (polydipsia)',
            'Sudden weight loss', 'Excessive hunger (polyphagia)',
            'Recurrent infections', 'Slow wound healing', 'Visual disturbances'
        ],
        'advice': [
            'Seek immediate medical evaluation with an endocrinologist',
            'Request comprehensive diabetes testing: HbA1c, fasting glucose',
            'Begin blood sugar monitoring if recommended',
            'Start dietary modifications: reduce refined sugars',
            'Increase physical activity gradually with medical supervision'
        ]
    },
    'Moderate Risk': {
        'explanation': 'You show some symptoms that may indicate prediabetes or early diabetes development.',
        'causes': ['Some classic diabetes symptoms present', 'Possible insulin resistance developing'],
        'advice': [
            'Schedule appointment for glucose screening',
            'Implement lifestyle changes: healthy diet, regular exercise',
            'Monitor symptoms and report any worsening'
        ]
    },
    'Low Risk': {
        'explanation': 'Your symptom profile suggests a lower likelihood of current diabetes.',
        'causes': ['Few or no classic diabetes symptoms present', 'Normal glucose regulation likely'],
        'advice': [
            'Continue healthy lifestyle habits',
            'Maintain regular health check-ups',
            'Stay active with regular exercise and balanced nutrition'
        ]
    }
}


def get_result_explanation(model_type: str, risk_level: str) -> Dict:
    """Get predefined explanation for a result"""
    if model_type == 'diabetes' and risk_level in DIABETES_EXPLANATIONS:
        return DIABETES_EXPLANATIONS[risk_level]
    return {
        'explanation': 'Assessment completed. Please consult with healthcare provider.',
        'causes': ['Multiple factors may contribute to this result.'],
        'advice': ['Follow up with appropriate medical specialist.']
    }


# =============================================================================
# Application Factory
# =============================================================================

def create_app() -> Flask:
    """Create and configure Flask application"""
    app = Flask(
        __name__,
        template_folder=Config.TEMPLATE_FOLDER,
        static_folder=Config.STATIC_FOLDER
    )
    
    app.config.from_object(Config)
    
    # Enable CORS for frontend-backend separation
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5500", "http://127.0.0.1:5500"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Ensure directories exist
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.INSTANCE_FOLDER, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get('FLASK_DEBUG') else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    db.init_app(app)
    
    # Enable WAL mode for SQLite to improve concurrency
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        with app.app_context():
            # Enable WAL mode and other optimizations for SQLite
            db.session.execute(db.text("PRAGMA journal_mode=WAL"))
            db.session.execute(db.text("PRAGMA synchronous=NORMAL"))
            db.session.execute(db.text("PRAGMA cache_size=1000"))
            db.session.execute(db.text("PRAGMA temp_store=MEMORY"))
            db.session.commit()
    
    with app.app_context():
        # Check if database needs to be created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.get_table_names():
            db.create_all()
            logging.info("Database tables created")
        else:
            logging.info("Database tables already exist")
        register_routes(app)
    
    logging.info("DiaBot backend initialized")
    return app


# =============================================================================
# Routes
# =============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def register_routes(app):
    """Register all routes"""
    
    # =========================================================================
    # Authentication Routes
    # =========================================================================
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if session.get('logged_in'):
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Please enter email and password', 'error')
                return render_template('login.html', email=email)
            
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['logged_in'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.admin
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password', 'error')
                return render_template('login.html', email=email)
        
        return render_template('login.html', email='')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if session.get('logged_in'):
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not email or not phone or not password:
                flash('All fields are required', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            # Validate phone
            try:
                phone_int = int(phone)
                if len(phone) < 10:
                    flash('Phone number must be at least 10 digits', 'error')
                    return render_template('register.html', username=username, email=email, phone=phone)
            except ValueError:
                flash('Phone number must contain only digits', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            # Check if user exists
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            if User.query.filter_by(username=username).first():
                flash('Username already taken', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            if User.query.filter_by(phone=phone_int).first():
                flash('Phone number already registered', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
            
            # Create user
            try:
                user = User(username=username, email=email, phone=phone_int)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                logging.error(f"Registration error: {e}")
                db.session.rollback()
                flash('Registration failed. Please try again.', 'error')
                return render_template('register.html', username=username, email=email, phone=phone)
        
        return render_template('register.html', username='', email='', phone='')
    
    @app.route('/logout')
    def logout():
        """User logout"""
        session.clear()
        flash('You have been logged out', 'success')
        return redirect(url_for('index'))
    
    # =========================================================================
    # Main Routes
    # =========================================================================
    
    @app.route('/')
    def index():
        """Homepage"""
        return render_template('index.html')
    
    @app.route('/diabetes', methods=['GET', 'POST'])
    def diabetes():
        """Diabetes risk assessment"""
        if request.method == 'POST':
            # Check if user is logged in
            if not session.get('logged_in'):
                flash('Please login or register to analyze your results', 'error')
                return redirect(url_for('login'))
            
            try:
                from model_bridge import predict_diabetes
                
                # Helper function to convert checkbox values to binary
                def get_binary(field_name):
                    """Convert checkbox value (1 or None) to 1 or 0"""
                    return 1 if request.form.get(field_name) == '1' else 0
                
                # Get age directly from input
                age = int(request.form.get('age', 0))
                
                # Get gender and convert to binary (0=Female, 1=Male)
                gender_value = request.form.get('gender', '1')
                gender = int(gender_value)
                
                input_data = {
                    'Age': age,
                    'Gender': gender,
                    'Polyuria': get_binary('polyuria'),
                    'Polydipsia': get_binary('polydipsia'),
                    'sudden weight loss': get_binary('sudden_weight_loss'),
                    'weakness': get_binary('weakness'),
                    'Polyphagia': get_binary('polyphagia'),
                    'Genital thrush': get_binary('genital_thrush'),
                    'visual blurring': get_binary('visual_blurring'),
                    'Itching': get_binary('itching'),
                    'Irritability': get_binary('irritability'),
                    'delayed healing': get_binary('delayed_healing'),
                    'partial paresis': get_binary('partial_paresis'),
                    'muscle stiffness': get_binary('muscle_stiffness'),
                    'Alopecia': get_binary('alopecia'),
                    'Obesity': get_binary('obesity')
                }
                
                prediction = predict_diabetes(input_data)
                risk_level = prediction.get('prediction', 'Unknown')
                explanation_data = get_result_explanation('diabetes', risk_level)
                
                result_data = {
                    'result_type': 'diabetes',
                    'input_data': input_data,
                    'prediction': prediction,
                    'explanation': explanation_data['explanation'],
                    'causes': explanation_data['causes'],
                    'advice': explanation_data['advice']
                }
                
                # Get current user ID if logged in
                current_user_id = session.get('user_id') if session.get('logged_in') else None
                result_id = save_result(result_data, user_id=current_user_id)
                
                return redirect(url_for('results', result_id=result_id))
                
            except Exception as e:
                logging.error(f"Error in diabetes assessment: {str(e)}", exc_info=True)
                flash('An error occurred. Please try again.', 'error')
        
        return render_template('diabetes.html')
    
    @app.route('/results/<result_id>')
    def results(result_id):
        """Display diagnostic results"""
        result = get_result(result_id)
        if not result:
            flash('Result not found', 'error')
            return redirect(url_for('index'))
        
        verification_status = None
        try:
            from blockchain import Blockchain
            blockchain = Blockchain(db.session)
            if blockchain.chain:
                verification_status = blockchain.validate_chain()
        except Exception as e:
            logging.error(f"Blockchain verification error: {str(e)}", exc_info=True)
        
        # Extract prediction data for template
        prediction_data = result['prediction']
        result_type = result['result_type']
        
        # Get the numeric prediction (0 or 1) and probability
        if prediction_data.get('prediction') == 'High Risk':
            prediction = 1
        else:
            prediction = 0
        
        probability = prediction_data.get('raw_probability', prediction_data.get('confidence', 0))
        
        return render_template('results.html', 
                             result=result,
                             prediction=prediction,
                             probability=probability,
                             result_type=result_type,
                             verification_status=verification_status)
    
    @app.route('/blockchain')
    def view_blockchain():
        """View blockchain ledger - Admin only"""
        # Check if user is logged in and is admin
        if not session.get('logged_in'):
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        
        if not session.get('is_admin'):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        from blockchain import Blockchain
        blockchain_obj = Blockchain(db.session)
        blockchain = []
        valid = False
        
        if blockchain_obj:
            for block in blockchain_obj.chain:
                try:
                    ts = float(block.timestamp)
                    formatted_ts = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    formatted_ts = str(block.timestamp)
                blockchain.append({
                    "index": block.index,
                    "timestamp": formatted_ts,
                    "data": block.data,
                    "previous_hash": block.previous_hash,
                    "hash": block.hash
                })
            valid = blockchain_obj.validate_chain()
        
        return render_template('blockchain.html', blockchain=blockchain, valid=valid)
    
    # Chatbot Routes
    @app.route('/chatbot')
    def chatbot():
        """Main chatbot interface"""
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        conversations = get_conversations_by_session(session['user_id'])
        return render_template('chatbot.html', 
                             conversations=conversations, 
                             conversation_id=None, 
                             messages=[])
    
    @app.route('/chatbot/conversation/<conversation_id>')
    def chatbot_conversation(conversation_id):
        """View specific conversation"""
        conversation = get_chat_conversation(conversation_id)
        if not conversation:
            flash('Conversation not found', 'error')
            return redirect(url_for('chatbot'))
        
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        conversations = get_conversations_by_session(session['user_id'])
        
        return render_template('chatbot_conversation.html', 
                             conversation=conversation, 
                             conversations=conversations,
                             messages=conversation.get('messages', []))
    
    @app.route('/chatbot/new', methods=['POST'])
    def new_chatbot_conversation():
        """Create new chatbot conversation"""
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        title = request.form.get('title', 'Medical Consultation')
        diagnostic_result_id = request.form.get('diagnostic_result_id')
        
        conversation_id = create_chat_conversation(
            session_id=session['user_id'],
            title=title,
            diagnostic_result_id=diagnostic_result_id
        )
        return redirect(url_for('chatbot_conversation', conversation_id=conversation_id))
    
    @app.route('/chatbot/message', methods=['POST'])
    def send_chatbot_message():
        """Send message to chatbot"""
        try:
            try:
                from chatbot import get_chatbot_response
            except Exception:
                from chatbot import get_chatbot_response
            
            data = request.get_json()
            conversation_id = data.get('conversation_id')
            user_message = data.get('message')
            
            if not conversation_id or not user_message:
                return jsonify({'error': 'Missing required fields'}), 400
            
            conversation = get_chat_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            
            add_chat_message(conversation_id, 'user', user_message)
            
            conversation_history = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in conversation.get('messages', [])
            ]
            
            diagnostic_context = None
            if conversation.get('diagnostic_result_id'):
                result = get_result(conversation['diagnostic_result_id'])
                if result:
                    diagnostic_context = {
                        'result_type': result['result_type'],
                        'prediction': result['prediction'],
                        'confidence': result['prediction'].get('confidence'),
                        'risk_level': result['prediction'].get('risk_level')
                    }
            
            ai_response = get_chatbot_response(user_message, conversation_history[:-1], diagnostic_context)
            add_chat_message(conversation_id, 'assistant', ai_response)
            
            return jsonify({
                'success': True,
                'message': {
                    'role': 'assistant',
                    'content': ai_response,
                    'created_at': datetime.utcnow().isoformat()
                }
            })
        except Exception as e:
            logging.error(f"Error in chatbot message: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/chatbot/analyze/<result_id>')
    def analyze_result_with_chatbot(result_id):
        """Start chatbot with diagnostic result analysis"""
        try:
            from chatbot import analyze_diagnostic_with_ai
        except Exception:
            from chatbot import analyze_diagnostic_with_ai
        
        result = get_result(result_id)
        if not result:
            flash('Diagnostic result not found', 'error')
            return redirect(url_for('chatbot'))
        
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        title = f"Analysis: {result['result_type'].replace('_', ' ').title()} Results"
        conversation_id = create_chat_conversation(
            session_id=session['user_id'],
            title=title,
            diagnostic_result_id=result['id']
        )
        
        ai_analysis = analyze_diagnostic_with_ai(result, result.get('image_path'))
        add_chat_message(
            conversation_id, 'assistant',
            f"I've analyzed your {result['result_type'].replace('_', ' ')} results:\n\n{ai_analysis}",
            'image_analysis'
        )
        
        return redirect(url_for('chatbot_conversation', conversation_id=conversation_id))
    
    # API Routes
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'service': 'DiaBot Backend', 'version': '1.0.0'})
    
    @app.route('/api/v1/predict/diabetes', methods=['POST'])
    def predict_diabetes_api():
        """Diabetes prediction API"""
        try:
            from model_bridge import predict_diabetes
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            input_data = {
                'Age': data.get('Age', data.get('age', 0)),
                'Gender': data.get('Gender', data.get('gender', 'Male')),
                'Polyuria': data.get('Polyuria', 'No'),
                'Polydipsia': data.get('Polydipsia', 'No'),
                'sudden weight loss': data.get('sudden_weight_loss', 'No'),
                'weakness': data.get('weakness', 'No'),
                'Polyphagia': data.get('Polyphagia', 'No'),
                'Genital thrush': data.get('Genital_thrush', 'No'),
                'visual blurring': data.get('visual_blurring', 'No'),
                'Itching': data.get('Itching', 'No'),
                'Irritability': data.get('Irritability', 'No'),
                'delayed healing': data.get('delayed_healing', 'No'),
                'partial paresis': data.get('partial_paresis', 'No'),
                'muscle stiffness': data.get('muscle_stiffness', 'No'),
                'Alopecia': data.get('Alopecia', 'No'),
                'Obesity': data.get('Obesity', 'No')
            }
            
            result = predict_diabetes(input_data)
            return jsonify({'success': True, **result})
        except Exception as e:
            logging.error(f"Error in diabetes prediction API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v1/chat', methods=['POST'])
    def chat_api():
        """Chatbot API endpoint"""
        try:
            try:
                from chatbot import get_chatbot_response
            except Exception:
                from chatbot import get_chatbot_response
            
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({'error': 'Message is required'}), 400
            
            message = data.get('message')
            history = data.get('conversation_history', [])
            context = data.get('diagnostic_context')
            
            response = get_chatbot_response(message, history, context)
            return jsonify({'success': True, 'response': response})
        except Exception as e:
            logging.error(f"Error in chat API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v1/chatbot/message', methods=['POST'])
    def chatbot_message_api():
        """Chatbot message API for conversations"""
        try:
            try:
                from chatbot import get_chatbot_response
            except Exception:
                from chatbot import get_chatbot_response
            
            data = request.get_json()
            conversation_id = data.get('conversation_id')
            user_message = data.get('message')
            
            if not user_message:
                return jsonify({'error': 'Message is required'}), 400
            
            # Create new conversation if needed - use server-side session id
            if not conversation_id:
                # ensure server session has user_id so conversations tie to the same user
                if 'user_id' not in session:
                    session['user_id'] = str(uuid.uuid4())
                conversation_id = create_chat_conversation(
                    session_id=session['user_id'],
                    title="General Health Consultation"
                )
            
            conversation = get_chat_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            
            add_chat_message(conversation_id, 'user', user_message)
            
            conversation_history = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in conversation.get('messages', [])
            ]
            
            diagnostic_context = None
            if conversation.get('diagnostic_result_id'):
                diagnostic_result = get_result(conversation['diagnostic_result_id'])
                if diagnostic_result:
                    diagnostic_context = {
                        'prediction': diagnostic_result.get('prediction'),
                        'risk_level': diagnostic_result.get('risk_level'),
                        'confidence': diagnostic_result.get('confidence')
                    }
            
            bot_response = get_chatbot_response(user_message, conversation_history, diagnostic_context)
            add_chat_message(conversation_id, 'assistant', bot_response)
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'conversation_id': conversation_id
            })
        except Exception as e:
            logging.error(f"Error in chatbot message API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # =============================================================================
    # REST API Endpoints
    # =============================================================================
    
    @app.route('/api/v1/auth/register', methods=['POST'])
    def api_register():
        """API endpoint for user registration"""
        try:
            data = request.get_json()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            password = data.get('password', '')
            
            if not username or not email or not phone or not password:
                return jsonify({'success': False, 'error': 'All fields are required'}), 400
            
            if len(password) < 6:
                return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
            
            # Validate phone
            try:
                phone_int = int(phone)
                if len(phone) < 10:
                    return jsonify({'success': False, 'error': 'Phone number must be at least 10 digits'}), 400
            except ValueError:
                return jsonify({'success': False, 'error': 'Phone number must contain only digits'}), 400
            
            if User.query.filter_by(email=email).first():
                return jsonify({'success': False, 'error': 'Email already registered'}), 400
            
            if User.query.filter_by(username=username).first():
                return jsonify({'success': False, 'error': 'Username already taken'}), 400
            
            if User.query.filter_by(phone=phone_int).first():
                return jsonify({'success': False, 'error': 'Phone number already registered'}), 400
            
            user = User(username=username, email=email, phone=phone_int)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Account created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }), 201
        except Exception as e:
            logging.error(f"Registration API error: {e}")
            db.session.rollback()
            return jsonify({'success': False, 'error': 'Registration failed'}), 500
    
    @app.route('/api/v1/auth/login', methods=['POST'])
    def api_login():
        """API endpoint for user login"""
        try:
            data = request.get_json()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            
            if not email or not password:
                return jsonify({'success': False, 'error': 'Email and password required'}), 400
            
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['logged_in'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.admin
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'is_admin': user.admin
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
        except Exception as e:
            logging.error(f"Login API error: {e}")
            return jsonify({'success': False, 'error': 'Login failed'}), 500
    
    @app.route('/api/v1/auth/logout', methods=['POST'])
    def api_logout():
        """API endpoint for user logout"""
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    
    @app.route('/api/v1/auth/me', methods=['GET'])
    def api_current_user():
        """API endpoint to get current user"""
        if session.get('logged_in'):
            return jsonify({
                'logged_in': True,
                'user': {
                    'id': session.get('user_id'),
                    'username': session.get('username'),
                    'is_admin': session.get('is_admin', False)
                }
            })
        else:
            return jsonify({'logged_in': False, 'user': None})
    
    @app.route('/api/v1/diabetes/analyze', methods=['POST'])
    def api_diabetes_analyze():
        """API endpoint for diabetes analysis"""
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        try:
            from model_bridge import predict_diabetes
            
            data = request.get_json()
            
            input_data = {
                'Age': data.get('age', 0),
                'Gender': data.get('gender', 1),
                'Polyuria': data.get('polyuria', 0),
                'Polydipsia': data.get('polydipsia', 0),
                'sudden weight loss': data.get('sudden_weight_loss', 0),
                'weakness': data.get('weakness', 0),
                'Polyphagia': data.get('polyphagia', 0),
                'Genital thrush': data.get('genital_thrush', 0),
                'visual blurring': data.get('visual_blurring', 0),
                'Itching': data.get('itching', 0),
                'Irritability': data.get('irritability', 0),
                'delayed healing': data.get('delayed_healing', 0),
                'partial paresis': data.get('partial_paresis', 0),
                'muscle stiffness': data.get('muscle_stiffness', 0),
                'Alopecia': data.get('alopecia', 0),
                'Obesity': data.get('obesity', 0)
            }
            
            prediction = predict_diabetes(input_data)
            risk_level = prediction.get('prediction', 'Unknown')
            explanation_data = get_result_explanation('diabetes', risk_level)
            
            result_data = {
                'result_type': 'diabetes',
                'input_data': input_data,
                'prediction': prediction,
                'explanation': explanation_data['explanation'],
                'causes': explanation_data['causes'],
                'advice': explanation_data['advice']
            }
            
            current_user_id = session.get('user_id')
            result_id = save_result(result_data, user_id=current_user_id)
            
            return jsonify({
                'success': True,
                'result_id': result_id,
                'prediction': prediction
            })
        except Exception as e:
            logging.error(f"Diabetes API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v1/results/<result_id>', methods=['GET'])
    def api_get_result(result_id):
        """API endpoint to get result by ID"""
        result = get_result(result_id)
        if not result:
            return jsonify({'success': False, 'error': 'Result not found'}), 404
        
        return jsonify({'success': True, 'result': result})
    
    @app.route('/api/v1/blockchain', methods=['GET'])
    def api_blockchain():
        """API endpoint to get blockchain - Admin only"""
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
        
        try:
            from blockchain import Blockchain
            blockchain_obj = Blockchain(db.session)
            blockchain = []
            
            if blockchain_obj:
                for block in blockchain_obj.chain:
                    try:
                        ts = float(block.timestamp)
                        formatted_ts = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_ts = str(block.timestamp)
                    blockchain.append({
                        "index": block.index,
                        "timestamp": formatted_ts,
                        "data": block.data,
                        "previous_hash": block.previous_hash,
                        "hash": block.hash
                    })
                valid = blockchain_obj.validate_chain()
            else:
                valid = False
            
            return jsonify({'success': True, 'blockchain': blockchain, 'valid': valid})
        except Exception as e:
            logging.error(f"Blockchain API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v1/chatbot/conversations', methods=['GET'])
    def api_get_conversations():
        """API endpoint to get user conversations"""
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        conversations = get_conversations_by_session(session['user_id'])
        return jsonify({'success': True, 'conversations': conversations})
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        """Serve uploaded files"""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
