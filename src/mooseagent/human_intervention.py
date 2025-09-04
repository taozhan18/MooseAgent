"""Error analysis and human intervention utilities for MooseAgent."""

import re
from typing import Dict, List, Tuple
from collections import defaultdict


class ErrorAnalyzer:
    """Analyzes error patterns and determines when human intervention is needed."""
    
    def __init__(self, error_threshold: int = 3):
        self.error_threshold = error_threshold
    
    def extract_error_signature(self, error_message: str) -> str:
        """Extract a signature from the error message to identify similar errors."""
        # Remove specific numbers, paths, and line numbers
        cleaned_error = re.sub(r'\b\d+\b', '[NUM]', error_message)
        cleaned_error = re.sub(r'/[a-zA-Z0-9_/\-\.]+', '[PATH]', cleaned_error)
        cleaned_error = re.sub(r'line\s+\d+', 'line [NUM]', cleaned_error)
        
        # Extract key error type
        error_patterns = [
            r'([A-Z][a-zA-Z]*Error)',
            r'([A-Z][a-zA-Z]*\s*[Ee]xception)',
            r'([A-Z][a-zA-Z]*\s*[Ff]ailed)',
            r'([A-Z][a-zA-Z]*\s*[Nn]ot\s*[Ff]ound)',
            r'(undefined\s+[a-zA-Z_]+)',
            r'(invalid\s+[a-zA-Z_]+)',
            r'(missing\s+[a-zA-Z_]+)',
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, cleaned_error)
            if match:
                return match.group(1).lower()
        
        # If no specific pattern found, use first 50 chars
        return cleaned_error[:50].lower().strip()
    
    def analyze_error_patterns(self, error_history: List[str]) -> Dict[str, int]:
        """Analyze error patterns from error history."""
        error_patterns = defaultdict(int)
        
        for error in error_history:
            signature = self.extract_error_signature(error)
            error_patterns[signature] += 1
        
        return dict(error_patterns)
    
    def needs_human_intervention(self, error_patterns: Dict[str, int]) -> Tuple[bool, str]:
        """Determine if human intervention is needed based on error patterns."""
        for signature, count in error_patterns.items():
            if count >= self.error_threshold:
                return True, f"Repeated error pattern detected: '{signature}' occurred {count} times"
        
        return False, ""
    
    def get_most_frequent_error(self, error_patterns: Dict[str, int]) -> str:
        """Get the most frequent error pattern."""
        if not error_patterns:
            return ""
        
        return max(error_patterns.items(), key=lambda x: x[1])[0]


class HumanInterventionHandler:
    """Handles human intervention interactions."""
    
    @staticmethod
    def format_intervention_message(error_patterns: Dict[str, int], recent_errors: List[str]) -> str:
        """Format a message for human intervention."""
        message = "=== HUMAN INTERVENTION NEEDED ===\n\n"
        message += "The system has encountered repeated errors and needs your assistance.\n\n"
        
        message += "Error Patterns:\n"
        for signature, count in error_patterns.items():
            message += f"- '{signature}': {count} occurrences\n"
        
        message += f"\nMost Recent Error:\n{recent_errors[-1] if recent_errors else 'No error details'}\n"
        
        message += "\nPlease provide guidance on how to resolve this issue.\n"
        message += "Examples:\n"
        message += "- 'Check the mesh definition in the Geometry block'\n"
        message += "- 'Verify the boundary condition syntax'\n"
        message += "- 'Try using a different kernel for this physics'\n"
        message += "- 'Modify the time stepping parameters'\n\n"
        message += "Your feedback: "
        
        return message
    
    @staticmethod
    def format_alignment_message(simulation_description: str) -> str:
        """Format a message for alignment confirmation."""
        message = "=== SIMULATION REQUIREMENT ALIGNMENT ===\n\n"
        message += "Please review the following simulation description:\n\n"
        message += f"{simulation_description}\n\n"
        message += "Does this meet your requirements?\n"
        message += "- If yes, type: 'yes'\n"
        message += "- If no, provide your feedback for revision\n\n"
        message += "Your response: "
        
        return message
    
    @staticmethod
    def parse_human_feedback(feedback: str) -> Dict[str, any]:
        """Parse human feedback and extract actionable information."""
        feedback_lower = feedback.lower()
        
        result = {
            'is_approval': feedback_lower.strip() in ['yes', 'y', 'approve', 'confirmed'],
            'suggestions': [],
            'priority_changes': [],
            'parameter_adjustments': []
        }
        
        # Extract common suggestions
        suggestion_patterns = [
            r'(check|verify|examine)\s+([a-zA-Z_]+)',
            r'(modify|change|adjust)\s+([a-zA-Z_]+)',
            r'(use|try|switch\s+to)\s+([a-zA-Z_]+)',
            r'(increase|decrease)\s+([a-zA-Z_]+)',
            r'(add|remove)\s+([a-zA-Z_]+)',
        ]
        
        for pattern in suggestion_patterns:
            matches = re.findall(pattern, feedback_lower)
            for match in matches:
                if len(match) == 2:
                    result['suggestions'].append(f"{match[0]} {match[1]}")
        
        return result