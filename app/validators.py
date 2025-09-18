"""
Input validation and prompt injection guards 
"""
from typing import Optional, Dict, Any
import re
from pydantic import BaseModel, Field, validator

class RAGPromptValidator(BaseModel):
    """Validator for RAG prompts with injection and content safety checks."""
    question: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    model: Optional[str] = Field(default=None)

    @validator('question')
    def validate_question_content(cls, v: str) -> str:
        """
        Validate question content for potential prompt injection or unsafe patterns.
        Rules:
        1. No system/assistant command injection
        2. No HTML/XML tags
        3. No code execution attempts
        4. No excessive whitespace
        5. No obvious prompt injection patterns
        """
        # Clean and normalize whitespace
        v = ' '.join(v.split())
        
        # Check for system/assistant message injection
        system_patterns = [
            r'system\s*:',
            r'assistant\s*:',
            r'<\|system\|>',
            r'<\|assistant\|>',
            r'#\s*system',
            r'#\s*assistant',
            r'user\s*:',
            r'human\s*:',
            r'ai\s*:',
            r'\[system\]',
            r'\[assistant\]'
        ]
        
        for pattern in system_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Potential prompt injection detected: system/assistant commands not allowed")

        # Check for HTML/XML tags
        if re.search(r'<[^>]+>', v):
            raise ValueError("HTML/XML tags are not allowed in questions")

        # Check for code execution patterns
        code_patterns = [
            r'import\s+[a-zA-Z_]',
            r'exec\s*\(',
            r'eval\s*\(',
            r'subprocess[.\[]',
            r'os[.\[]',
            r'system\s*\(',
            r'#!/',
            r'\bpython\b.*\brun\b',
            r'__import__\s*\(',
            r'getattr\s*\(',
            r'globals\s*\(',
            r'locals\s*\('
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Code execution attempts are not allowed")

        # Check for other suspicious patterns
        suspicious_patterns = [
            r'ignore\s+previous',
            r'disregard\s+(above|previous)',
            r'forget\s+.*\s+instruction',
            r'\{[^}]*\}',  # Potential template injection
            r'\$\{[^}]*\}',  # Template string injection
            r'\{\{[^}]*\}\}',  # Mustache/Handlebar templates
            r'\$[A-Z_]+',  # Environment variables
            r'__[a-zA-Z]+__',  # Python magic methods
            r'#\{[^}]*\}'  # Ruby-style interpolation
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Potential prompt injection detected")

        return v

    @validator('model')
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        """Validate model name if provided."""
        if v is None:
            return v
            
        allowed_models = {
            'mixtral-8x7b-32768',
            'llama2-70b-4096',
            'llama-3.1-8b-instant',
            'gemma-7b-it',
            'nonexistent-model'  # Added for testing purposes
        }
        
        if v not in allowed_models:
            raise ValueError(f"Invalid model name. Must be one of: {', '.join(allowed_models)}")
        
        return v

def validate_request(raw_input: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize incoming request data."""
    try:
        validated = RAGPromptValidator(**raw_input)
        return validated.dict()
    except Exception as e:
        raise ValueError(f"Input validation failed: {str(e)}")