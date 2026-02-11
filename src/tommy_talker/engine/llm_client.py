"""
TommyTalker LLM Client
Ollama integration for text rewriting and analysis.
Supports Hybrid Cloud Uplink (OpenAI-compatible API offloading).
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ollama import
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False
    print("[WARNING] ollama not installed - local LLM features disabled")

# OpenAI-compatible API client
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    print("[WARNING] httpx not installed - Cloud Mode disabled")


@dataclass
class RewriteResult:
    """Result from LLM rewriting."""
    original: str
    rewritten: str
    model_used: str
    source: str = "local"  # "local" or "cloud"


class LLMClient:
    """
    Ollama LLM client for text rewriting and analysis.
    
    Features:
    - Professional rewriting for Editor mode
    - Style guide integration
    - Tier-based model selection
    - Advanced Mode for custom model tags
    - Cloud Mode for OpenAI-compatible API offloading
    """
    
    # Model map for each tier (updated with modern models)
    MODEL_MAP = {
        1: "llama3.2:3b",   # Efficient for low RAM
        2: "llama3.1:8b",   # Standard
        3: "gemma2:27b",    # High-performance for Max chips
    }
    
    # System prompts for different tasks
    PROMPTS = {
        "professional": """You are a professional writing assistant.
Rewrite the following text to be more professional, clear, and well-structured.
Maintain the original meaning but improve grammar, clarity, and tone.
Output ONLY the rewritten text, no explanations.""",

        "with_style_guide": """You are a professional writing assistant.
Rewrite the following text according to these style guidelines:

{style_guide}

Maintain the original meaning but follow the style guide exactly.
Output ONLY the rewritten text, no explanations.""",
    }

    # App-context-aware prompts keyed by TextInputFormat value
    APP_CONTEXT_PROMPTS = {
        "code": """You are a code-aware writing assistant.
Rewrite the dictated text as code comments, docstrings, or variable/function names as appropriate.
Preserve technical terms, acronyms, and code identifiers exactly.
If the text sounds like a code description, format it as a comment for the relevant language.
Output ONLY the formatted text, no explanations.""",

        "chat_message": """You are a messaging assistant.
Rewrite the dictated text as a casual, conversational chat message.
Keep it brief and natural. Fix grammar but maintain informal tone.
Do not add greetings or sign-offs unless the speaker included them.
Output ONLY the message text, no explanations.""",

        "email": """You are an email writing assistant.
Rewrite the dictated text as a professional email.
Include appropriate greeting and sign-off if the speaker implied them.
Maintain professional tone with clear, concise paragraphs.
Output ONLY the email text, no explanations.""",

        "terminal_command": """You are a command-line assistant.
Extract the terminal command from the dictated text.
Remove filler words, pleasantries, and explanations.
Output ONLY the command(s), one per line, no explanations or markdown.""",

        "markdown": """You are a Markdown writing assistant.
Rewrite the dictated text using proper Markdown formatting.
Use headers, lists, bold, italic, and code blocks as appropriate.
Output ONLY the Markdown text, no explanations.""",

        "search_query": """You are a search query assistant.
Extract the key search terms from the dictated text.
Remove filler words, articles, and unnecessary context.
Output a concise search query, no explanations.""",

        "document_text": """You are a document writing assistant.
Rewrite the dictated text as polished document prose.
Use clear, well-structured sentences with proper paragraph breaks.
Maintain formal tone appropriate for written documents.
Output ONLY the polished text, no explanations.""",

        "spreadsheet_formula": """You are a spreadsheet assistant.
Convert the dictated text into a spreadsheet formula or cell value.
If the text describes a calculation, output the formula (e.g., =SUM(A1:A10)).
If it's just data, clean it up for cell entry.
Output ONLY the formula or value, no explanations.""",
    }
    
    def __init__(self, tier: int = 2, custom_model: Optional[str] = None,
                 cloud_mode: bool = False, cloud_config: Optional[dict] = None):
        """
        Initialize LLM client with hardware-appropriate model.
        
        Args:
            tier: Hardware tier (1, 2, or 3) determines which model to use
            custom_model: Override model (for Advanced Mode)
            cloud_mode: Enable Cloud Mode for API offloading
            cloud_config: Cloud configuration with 'base_url', 'api_key', 'model'
        """
        self.tier = tier
        self.model = custom_model or self.MODEL_MAP.get(tier, self.MODEL_MAP[2])
        self.style_guide: Optional[str] = None
        
        # Cloud Mode configuration
        self.cloud_mode = cloud_mode
        self.cloud_config = cloud_config or {}
        
        if cloud_mode:
            print(f"[LLMClient] Cloud Mode enabled - API: {self.cloud_config.get('base_url', 'not set')}")
        elif HAS_OLLAMA:
            print(f"[LLMClient] Local Mode with model: {self.model}")
        else:
            print("[LLMClient] No LLM backend available")
            
    def load_style_guide(self, path: Path) -> bool:
        """
        Load a style guide from file.
        
        Args:
            path: Path to style_guide.txt
            
        Returns:
            True if loaded successfully
        """
        if not path.exists():
            print(f"[LLMClient] Style guide not found: {path}")
            return False
            
        try:
            self.style_guide = path.read_text()
            print(f"[LLMClient] Loaded style guide from: {path}")
            return True
        except Exception as e:
            print(f"[LLMClient] Error loading style guide: {e}")
            return False
            
    def rewrite_professional(self, text: str) -> Optional[RewriteResult]:
        """
        Rewrite text to be more professional.
        Uses style guide if loaded. Routes to cloud if Cloud Mode enabled.
        
        Args:
            text: Text to rewrite
            
        Returns:
            RewriteResult or None if rewriting failed
        """
        # Choose prompt based on whether style guide is loaded
        if self.style_guide:
            system_prompt = self.PROMPTS["with_style_guide"].format(
                style_guide=self.style_guide
            )
        else:
            system_prompt = self.PROMPTS["professional"]
            
        # Route to cloud or local
        if self.cloud_mode and self.cloud_config.get("api_key"):
            return self._rewrite_cloud(text, system_prompt)
        else:
            return self._rewrite_local(text, system_prompt)

    def rewrite_for_context(self, text: str, app_context) -> Optional[RewriteResult]:
        """
        Rewrite text using an app-context-aware prompt.

        Args:
            text: Text to rewrite
            app_context: AppContext with target app info

        Returns:
            RewriteResult or None. Falls back to rewrite_professional() if no
            specific prompt exists for this format.
        """
        fmt_value = app_context.text_input_format.value

        base_prompt = self.APP_CONTEXT_PROMPTS.get(fmt_value)
        if not base_prompt:
            return self.rewrite_professional(text)

        # Build the system prompt
        system_prompt = base_prompt

        # Append style guide if loaded
        if self.style_guide:
            system_prompt += f"\n\nAdditional style guide:\n{self.style_guide}"

        # Append app context hint
        app_hint = f"\nContext: typing in {app_context.app_name}"
        if app_context.profile:
            app_hint += f" ({app_context.profile.category})"
        system_prompt += app_hint

        print(f"[LLMClient] Using {fmt_value} prompt for {app_context.app_name}")

        if self.cloud_mode and self.cloud_config.get("api_key"):
            return self._rewrite_cloud(text, system_prompt)
        else:
            return self._rewrite_local(text, system_prompt)

    def _rewrite_local(self, text: str, system_prompt: str) -> Optional[RewriteResult]:
        """Rewrite using local Ollama."""
        if not HAS_OLLAMA:
            print("[LLMClient] Ollama not available")
            return None
            
        try:
            response = ollama.generate(
                model=self.model,
                prompt=text,
                system=system_prompt,
            )
            
            rewritten = response.get("response", "").strip()
            
            return RewriteResult(
                original=text,
                rewritten=rewritten,
                model_used=self.model,
                source="local"
            )
            
        except Exception as e:
            print(f"[LLMClient] Local rewrite error: {e}")
            return None
            
    def _rewrite_cloud(self, text: str, system_prompt: str) -> Optional[RewriteResult]:
        """Rewrite using OpenAI-compatible cloud API."""
        if not HAS_HTTPX:
            print("[LLMClient] httpx not available for Cloud Mode")
            return None
            
        # Get config from cloud_config or fall back to environment variables
        base_url = self.cloud_config.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = self.cloud_config.get("api_key") or os.getenv("OPENAI_API_KEY")
        model = self.cloud_config.get("model", "gpt-4o-mini")
        
        if not api_key:
            print("[LLMClient] Cloud API key not configured (set OPENAI_API_KEY in .env)")
            return None
            
        try:
            # OpenAI-compatible chat completion endpoint
            url = f"{base_url.rstrip('/')}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7,
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
            data = response.json()
            rewritten = data["choices"][0]["message"]["content"].strip()
            
            print(f"[LLMClient] Cloud rewrite successful via {base_url}")
            
            return RewriteResult(
                original=text,
                rewritten=rewritten,
                model_used=model,
                source="cloud"
            )
            
        except Exception as e:
            print(f"[LLMClient] Cloud rewrite error: {e}")
            return None
            
    def set_model(self, model: str):
        """
        Set a custom model (for Advanced Mode).
        
        Args:
            model: Ollama model tag (e.g., "mistral:latest", "custom-model")
        """
        self.model = model
        print(f"[LLMClient] Model changed to: {model}")
        
    def set_cloud_mode(self, enabled: bool, config: Optional[dict] = None):
        """
        Enable or disable Cloud Mode.
        
        Args:
            enabled: Whether to enable Cloud Mode
            config: Cloud configuration dict
        """
        self.cloud_mode = enabled
        if config:
            self.cloud_config = config
            
        if enabled:
            print(f"[LLMClient] Cloud Mode enabled")
        else:
            print(f"[LLMClient] Cloud Mode disabled, using local: {self.model}")
        
    def check_model_available(self, model: Optional[str] = None) -> bool:
        """
        Check if a model is available locally.
        
        Args:
            model: Model to check (defaults to currently set model)
            
        Returns:
            True if model is available
        """
        if not HAS_OLLAMA:
            return False
            
        target_model = model or self.model
        
        try:
            models = ollama.list()
            available = [m.get("name", "") for m in models.get("models", [])]
            return any(target_model in m for m in available)
        except Exception as e:
            print(f"[LLMClient] Error checking models: {e}")
            return False
            
    def pull_model(self, model: Optional[str] = None, progress_callback=None) -> bool:
        """
        Download a model from Ollama.
        
        Args:
            model: Model to download (defaults to currently set model)
            progress_callback: Optional callback(percent: float, status: str)
            
        Returns:
            True if download completed successfully
        """
        if not HAS_OLLAMA:
            return False
            
        target_model = model or self.model
        
        try:
            print(f"[LLMClient] Pulling model: {target_model}")
            
            for progress in ollama.pull(target_model, stream=True):
                if progress_callback:
                    status = progress.get("status", "downloading")
                    completed = progress.get("completed", 0)
                    total = progress.get("total", 1)
                    percent = (completed / total) * 100 if total > 0 else 0
                    progress_callback(percent, status)
                    
            print(f"[LLMClient] Model pulled successfully: {target_model}")
            return True
            
        except Exception as e:
            print(f"[LLMClient] Error pulling model: {e}")
            return False
            
    def test_cloud_connection(self) -> bool:
        """
        Test the cloud API connection.
        
        Returns:
            True if connection is successful
        """
        if not self.cloud_mode or not self.cloud_config.get("api_key"):
            return False
            
        try:
            result = self._rewrite_cloud("Hello, test.", "Respond with 'OK'")
            return result is not None
        except Exception:
            return False
