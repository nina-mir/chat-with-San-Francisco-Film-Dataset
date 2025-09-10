"""
System Instructions Module
Manages loading and caching of AI instruction templates from markdown files.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any
import json


class SystemInstructions:
    """
    Manages system instruction templates for the query processing pipeline.
    Loads markdown templates once and caches them in memory for efficient access.
    """
    
    def __init__(self, instructions_dir: str = "instructions"):
        """
        Initialize the SystemInstructions class.
        
        Args:
            instructions_dir: Directory containing markdown instruction files
        """
        self.instructions_dir = Path(instructions_dir)
        self._cache: Dict[str, str] = {}
        
        # Define the instruction file mapping
        self._instruction_files = {
            'preprocessing': 'preprocessing.md',
            'nlp_plan': 'nlp_plan.md',
            'code_generation': 'code_generation.md'
        }
        
        # Load all instructions at initialization
        self._load_all_instructions()
    
    def _load_all_instructions(self) -> None:
        """
        Load all instruction templates from markdown files and cache them.
        Handles missing files gracefully by logging warnings.
        """
        for instruction_type, filename in self._instruction_files.items():
            try:
                self._cache[instruction_type] = self._load_template_file(filename)
            except FileNotFoundError:
                print(f"Warning: Instruction file '{filename}' not found in '{self.instructions_dir}'")
                self._cache[instruction_type] = ""
            except Exception as e:
                print(f"Error loading instruction file '{filename}': {str(e)}")
                self._cache[instruction_type] = ""
    
    def _load_template_file(self, filename: str) -> str:
        """
        Load a single template file from disk.
        
        Args:
            filename: Name of the markdown file to load
            
        Returns:
            Content of the template file as string
            
        Raises:
            FileNotFoundError: If the template file doesn't exist
            IOError: If there's an error reading the file
        """
        file_path = self.instructions_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except IOError as e:
            raise IOError(f"Error reading template file '{file_path}': {str(e)}")
    
    def get_preprocessing_instructions(self) -> str:
        """
        Get the preprocessing step instructions.
        
        Returns:
            Preprocessing instructions as string
        """
        return self._cache.get('preprocessing', '')
    
    def get_nlp_plan_instructions(self) -> str:
        """
        Get the NLP planning step instructions.
        
        Returns:
            NLP planning instructions as string
        """
        return self._cache.get('nlp_plan', '')
    
    def get_code_generation_instructions(
        self, 
        preprocessing_result: Dict[str, Any], 
        nlp_plan: Dict[str, str]
    ) -> str:
        """
        Get the code generation instructions with dynamic content injection.
        
        Args:
            preprocessing_result: The result from the preprocessing step
            nlp_plan: The NLP action plan
            
        Returns:
            Code generation instructions with injected content
        """
        base_instructions = self._cache.get('code_generation', '')
        
        if not base_instructions:
            return ''
        
        # Convert inputs to formatted JSON strings for injection
        preprocessing_str = json.dumps(preprocessing_result, indent=2)
        nlp_plan_str = json.dumps(nlp_plan, indent=2)
        
        # Replace placeholders using string replacement instead of .format()
        # This avoids issues with curly braces in the template content
        try:
            formatted_instructions = base_instructions.replace(
                '{preprocessing_result}', preprocessing_str
            ).replace(
                '{nlp_plan}', nlp_plan_str
            )
            return formatted_instructions
        except Exception as e:
            print(f"Error formatting code generation instructions: {str(e)}")
            return base_instructions
    
    def reload_instructions(self) -> None:
        """
        Reload all instruction templates from disk.
        Useful for development when templates are being modified.
        """
        self._cache.clear()
        self._load_all_instructions()
    
    def is_instruction_loaded(self, instruction_type: str) -> bool:
        """
        Check if a specific instruction type has been successfully loaded.
        
        Args:
            instruction_type: Type of instruction ('preprocessing', 'nlp_plan', 'code_generation')
            
        Returns:
            True if instruction is loaded and non-empty, False otherwise
        """
        return instruction_type in self._cache and bool(self._cache[instruction_type])
    
    def get_instruction_status(self) -> Dict[str, bool]:
        """
        Get the loading status of all instruction types.
        
        Returns:
            Dictionary mapping instruction types to their loaded status
        """
        return {
            instruction_type: self.is_instruction_loaded(instruction_type)
            for instruction_type in self._instruction_files.keys()
        }