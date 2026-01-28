"""
DiaBot - Chatbot Service
AI-powered medical chatbot for health consultations
"""

import os
import logging
from typing import Dict, List, Optional
import dotenv

dotenv.load_dotenv()


class MedicalChatbot:
    """
    AI-powered medical chatbot (Dr. DiaBot)
    Provides educational health information and diagnostic result analysis
    """
    
    def __init__(self):
        self.system_prompt = """You are Dr. DiaBot, an AI medical assistant designed to provide educational health information and analyze medical diagnostic results. Your role is to:

1. EDUCATIONAL SUPPORT: Provide clear, patient-friendly explanations of medical conditions, symptoms, and general health guidance.

2. DIAGNOSTIC ANALYSIS: When presented with diagnostic results, analyze them and provide:
   - Clinical interpretation of findings
   - Risk assessment and significance
   - Recommended follow-up actions

3. DIABETES FOCUS: Pay special attention to diabetes-related queries:
   - Explain symptoms like polyuria, polydipsia, sudden weight loss
   - Provide dietary tips for high-risk users (reduce refined sugars, increase fiber)
   - Recommend lifestyle changes (regular exercise, weight management)
   - Emphasize the importance of blood glucose monitoring

4. SAFETY GUIDELINES:
   - Always include medical disclaimers
   - Emphasize the need for professional medical evaluation
   - Never provide specific drug dosages or replace clinical judgment

5. COMMUNICATION STYLE:
   - Use clear, accessible language
   - Be empathetic and supportive
   - Provide structured, actionable information

Remember: You are an educational tool to complement, not replace, professional medical care."""

    def generate_response(self, user_message: str, conversation_history: List[Dict],
                         diagnostic_context: Optional[Dict] = None,
                         image_data: Optional[bytes] = None) -> str:
        """
        Generate AI response
        
        Args:
            user_message: User's question
            conversation_history: Previous messages
            diagnostic_context: Optional diagnostic result context
            image_data: Optional image for analysis
            
        Returns:
            AI-generated response
        """
        try:
            import LLM
            return LLM.generate_chat_response(
                user_message, 
                conversation_history, 
                diagnostic_context, 
                self.system_prompt
            )
        except Exception as e:
            logging.error(f"Error generating chatbot response: {str(e)}")
            return self._get_fallback_response()
    
    def analyze_diagnostic_result(self, diagnostic_result: Dict, 
                                  image_path: Optional[str] = None) -> str:
        """Analyze diagnostic results with AI"""
        try:
            from backend.LLM import analyze_diagnostic
            return analyze_diagnostic(diagnostic_result, self.system_prompt)
        except Exception as e:
            logging.error(f"Error analyzing diagnostic result: {str(e)}")
            return self._get_fallback_analysis()
    
    def _get_fallback_response(self) -> str:
        """Fallback response when AI fails"""
        return """I apologize, but I'm experiencing technical difficulties right now. 

For immediate medical concerns, please contact:
- Your healthcare provider
- Emergency services (if urgent)
- A medical helpline

I'll be back online shortly to assist with your health questions.

⚠️ **MEDICAL DISCLAIMER:** This platform provides educational information only and should not replace professional medical advice."""
    
    def _get_fallback_analysis(self) -> str:
        """Fallback analysis when AI fails"""
        return """I'm unable to provide a detailed analysis at this moment.

**Important Next Steps:**
1. **Consult a Healthcare Professional:** Share these results with your doctor
2. **Schedule Follow-up:** Book an appointment for comprehensive evaluation
3. **Keep Records:** Save these results for your medical records

⚠️ **MEDICAL DISCLAIMER:** Diagnostic results require professional medical interpretation."""


# Global chatbot instance
_chatbot = MedicalChatbot()


def get_chatbot_response(user_message: str, conversation_history: List[Dict],
                        diagnostic_context: Optional[Dict] = None,
                        image_data: Optional[bytes] = None) -> str:
    """
    Get response from medical chatbot
    
    Args:
        user_message: User's question
        conversation_history: Previous messages
        diagnostic_context: Optional diagnostic result context
        image_data: Optional image for analysis
        
    Returns:
        AI-generated response
    """
    return _chatbot.generate_response(
        user_message, conversation_history, diagnostic_context, image_data
    )


def analyze_diagnostic_with_ai(diagnostic_result: Dict, 
                               image_path: Optional[str] = None) -> str:
    """
    Analyze diagnostic result with AI
    
    Args:
        diagnostic_result: The result to analyze
        image_path: Optional image path
        
    Returns:
        Detailed analysis
    """
    return _chatbot.analyze_diagnostic_result(diagnostic_result, image_path)
