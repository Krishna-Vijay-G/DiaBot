"""
DiaBot - LLM Integration (Google Gemini)
Provides AI-powered responses and content generation
"""

import os
import logging
import time
from typing import Dict, List, Optional
import dotenv

dotenv.load_dotenv()

# Try to import Google Gemini API
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Gemini SDK not installed. Using fallback responses.")

# Initialize Gemini client
gemini_api_key = os.getenv("GEMINI_API_KEY")
client = None

if GEMINI_AVAILABLE and gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
    try:
        client = genai.Client(api_key=gemini_api_key)
        logging.info("Gemini API client initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing Gemini client: {e}")
        client = None
else:
    if not GEMINI_AVAILABLE:
        logging.warning("Gemini SDK not available")
    else:
        logging.warning("Gemini API key not set")


def _retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry a function with exponential backoff on rate limit errors"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logging.warning(f"Rate limit hit, retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
            raise e


def generate_chat_response(user_message: str, conversation_history: List[Dict],
                           diagnostic_context: Optional[Dict] = None,
                           system_prompt: str = "") -> str:
    """
    Generate chat response using Gemini
    
    Args:
        user_message: User's message
        conversation_history: Previous conversation
        diagnostic_context: Optional diagnostic context
        system_prompt: System instruction
        
    Returns:
        Generated response
    """
    if client is None:
        return _get_fallback_chat_response(user_message)
    
    try:
        messages = []
        
        # Add diagnostic context if available
        if diagnostic_context:
            context_message = f"""
PATIENT DIAGNOSTIC CONTEXT:
- Analysis Type: {diagnostic_context.get('result_type', 'Unknown')}
- Results: {diagnostic_context.get('prediction', {})}
- Confidence: {diagnostic_context.get('confidence', 'N/A')}
- Risk Level: {diagnostic_context.get('risk_level', 'N/A')}

Please keep this context in mind when providing guidance."""
            messages.append(types.Content(role="user", parts=[types.Part(text=context_message)]))
        
        # Add conversation history
        for msg in conversation_history[-10:]:
            role = "user" if msg['role'] == 'user' else "model"
            messages.append(types.Content(role=role, parts=[types.Part(text=msg['content'])]))
        
        # Add current message
        messages.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
        
        # Generate response with retry
        def _generate():
            return client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=1500
                )
            )
        
        response = _retry_with_backoff(_generate)
        
        if response.text:
            return _format_medical_response(response.text)
        return _get_fallback_chat_response(user_message)
        
    except Exception as e:
        logging.error(f"Error generating chat response: {str(e)}")
        return _get_fallback_chat_response(user_message)


def analyze_diagnostic(diagnostic_result: Dict, system_prompt: str = "") -> str:
    """
    Analyze diagnostic results using Gemini
    
    Args:
        diagnostic_result: Diagnostic result data
        system_prompt: System instruction
        
    Returns:
        Analysis text
    """
    if client is None:
        return _get_fallback_analysis()
    
    try:
        analysis_prompt = f"""
Please provide a comprehensive medical analysis of the following diagnostic result:

**Diagnostic Type:** {diagnostic_result.get('result_type', 'Unknown')}
**Prediction:** {diagnostic_result.get('prediction', {})}
**Input Parameters:** {diagnostic_result.get('input_data', {})}

Please provide:
1. **Clinical Interpretation:** What these results mean
2. **Risk Assessment:** Severity and implications
3. **Recommended Actions:** Immediate and long-term steps
4. **Lifestyle Recommendations:** Preventive measures

Include appropriate medical disclaimers."""

        def _analyze():
            return client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[types.Content(role="user", parts=[types.Part(text=analysis_prompt)])],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    max_output_tokens=2000
                )
            )
        
        response = _retry_with_backoff(_analyze)
        
        if response.text:
            return _format_medical_response(response.text)
        return _get_fallback_analysis()
        
    except Exception as e:
        logging.error(f"Error analyzing diagnostic: {str(e)}")
        return _get_fallback_analysis()


def get_educational_content(condition: str, confidence: float, module_type: str) -> str:
    """
    Generate educational content for a condition
    
    Args:
        condition: Predicted condition
        confidence: Confidence score
        module_type: Type of diagnostic module
        
    Returns:
        Educational content
    """
    if client is None:
        return _get_fallback_educational_content(condition, module_type)
    
    try:
        if module_type == 'diabetes':
            prompt = f"""
Provide educational information about diabetes risk assessment. Our analysis indicates 
{condition} with {confidence*100:.1f}% confidence. Explain:

- What diabetes risk levels mean
- Lifestyle factors that influence diabetes risk
- Prevention strategies and healthy habits
- When to seek medical evaluation
- Diet and exercise recommendations
- Symptoms to watch for (polyuria, polydipsia, sudden weight loss)

Emphasize this is a risk assessment, not a diagnosis."""
        else:
            prompt = f"""
Provide general health education about {condition} identified with 
{confidence*100:.1f}% confidence. Focus on general health maintenance 
and the importance of professional medical consultation."""
        
        def _educate():
            return client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                )
            )
        
        response = _retry_with_backoff(_educate)
        
        if response.text:
            return _format_medical_response(response.text)
        return _get_fallback_educational_content(condition, module_type)
        
    except Exception as e:
        logging.error(f"Error generating educational content: {str(e)}")
        return _get_fallback_educational_content(condition, module_type)


def _format_medical_response(response: str) -> str:
    """Add medical disclaimer if not present"""
    if "disclaimer" not in response.lower() and "medical professional" not in response.lower():
        disclaimer = """

⚠️ **IMPORTANT MEDICAL DISCLAIMER:**
This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for medical decisions."""
        return response + disclaimer
    return response


def _get_fallback_chat_response(user_message: str) -> str:
    """Fallback chat response"""
    return """I apologize, but I'm experiencing technical difficulties right now. 

For immediate medical concerns, please contact:
- Your healthcare provider
- Emergency services (if urgent)
- A medical helpline

⚠️ **MEDICAL DISCLAIMER:** This platform provides educational information only and should not replace professional medical advice."""


def _get_fallback_analysis() -> str:
    """Fallback diagnostic analysis"""
    return """I'm unable to provide a detailed analysis at this moment.

**Important Next Steps:**
1. **Consult a Healthcare Professional:** Share these results with your doctor
2. **Schedule Follow-up:** Book an appointment for comprehensive evaluation
3. **Keep Records:** Save these results for your medical records

⚠️ **MEDICAL DISCLAIMER:** Diagnostic results require professional medical interpretation."""


def _get_fallback_educational_content(condition: str, module_type: str) -> str:
    """Fallback educational content"""
    if module_type == 'diabetes':
        return f"""
**Diabetes Risk Information: {condition}**

Understanding diabetes risk factors can help you take preventive measures.

**Common diabetes symptoms include:**
• Excessive urination (polyuria)
• Excessive thirst (polydipsia)
• Sudden weight loss
• Excessive hunger (polyphagia)
• Visual blurring
• Delayed wound healing

**Prevention tips:**
• Maintain a healthy weight
• Follow a balanced diet low in refined sugars
• Exercise regularly (150+ minutes per week)
• Monitor blood sugar levels as recommended
• Stay hydrated and get adequate sleep

**Next steps for professional evaluation:**
• HbA1c test
• Fasting plasma glucose test
• Oral glucose tolerance test

⚠️ **IMPORTANT:** This is educational only and not a medical diagnosis. 
Consult with a healthcare professional for proper evaluation."""
    
    return f"""
**Educational Information: {condition}**

This analysis provides general health information. For accurate diagnosis and treatment, 
please consult with qualified healthcare professionals.

⚠️ **MEDICAL DISCLAIMER:** This information is for educational purposes only."""
