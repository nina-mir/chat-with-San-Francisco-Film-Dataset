# src/chatbot_coordinator.py

from typing import Dict, Any, Optional
import time


class ChatbotCoordinator:
    """
    Routes user messages to appropriate handlers.
    Acts as the bridge between Streamlit UI and QueryProcessor.
    """

    def __init__(self):
        """Initialize coordinator with QueryProcessor"""
        # Import here to avoid circular imports
        from src.pandas_script import QueryProcessor
        import inspect

        # 🔍 DEBUG: Show which file is actually being loaded
        qp_file = inspect.getfile(QueryProcessor)
        print(f"\n🔥🔥🔥 LOADED QueryProcessor FROM: {qp_file} 🔥🔥🔥\n")
        

        self.query_processor = QueryProcessor()
        self.intent_classifier = IntentClassifier()

    def handle_message(self, user_message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point: route message based on intent.

        Args:
            user_message: The user's input text
            context: Optional context (last_result, conversation state, etc.)

        Returns:
            Structured result dict with 'type', 'content', and optional 'data'
        """
        if context is None:
            context = {}

        # Classify the user's intent
        intent = self.intent_classifier.classify(user_message, context)

        # Route to appropriate handler
        if intent == 'greeting':
            return self._handle_greeting()

        elif intent == 'help':
            return self._handle_help()

        elif intent == 'data_query':
            return self._handle_data_query(user_message)

        elif intent == 'followup':
            return self._handle_followup(user_message, context)

        else:
            # Default: treat as data query
            return self._handle_data_query(user_message)

    def _handle_greeting(self) -> Dict[str, Any]:
        """Handle greeting messages"""
        return {
            'type': 'greeting',
            'content': """👋 Hi! I'm your SF Film Locations assistant.

I can help you explore thousands of filming locations across San Francisco!

**Try asking:**
- "What films were shot at the Golden Gate Bridge?"
- "Show me Hitchcock filming locations"
- "Which actor appeared in the most films?"
- "How many movies from the 1980s?"

What would you like to know?"""
        }

    def _handle_help(self) -> Dict[str, Any]:
        """Handle help requests"""
        return {
            'type': 'help',
            'content': """🎬 **What I Can Do:**

**Search for Films:**
- By location: "Films shot at Union Square"
- By person: "Movies directed by Spielberg"
- By title: "Films with 'star' in the title"
- By year: "Movies from 1999"

**Get Statistics:**
- "How many films were made in the 1980s?"
- "Which actor appeared in the most movies?"
- "Top 10 filming locations"

**View Maps:**
- I'll automatically show maps when relevant!

Just ask in natural language - I'll figure it out! 😊"""
        }

    def _handle_data_query(self, query: str) -> Dict[str, Any]:
        """
        Handle data queries by calling QueryProcessor.
        This is where the magic happens!
        """
        try:
            # Call your existing QueryProcessor
            result = self.query_processor.process_query(query, wait_time=3)

            # Check if we got valid results
            if result and 'code' in result:
                # Extract execution result
                execution_result = result.get('execution_result')

                return {
                    'type': 'data_result',
                    'content': 'query_processed',  # Formatter will handle this
                    'query_result': result,
                    'execution_result': execution_result,
                    'map_html': result.get('map_html'),
                    'original_query': query
                }
            else:
                return {
                    'type': 'error',
                    'content': "⚠️ I couldn't process that query. Could you rephrase it?"
                }

        except Exception as e:
            return self._handle_error(e, query)

    def _handle_followup(self, query: str, context: Dict) -> Dict[str, Any]:
        """
        Handle follow-up questions (for now, treat as new query).
        TODO: Could enhance this to use context in future.
        """
        # For MVP, just treat as regular query
        return self._handle_data_query(query)

    def _handle_error(self, error: Exception, query: str) -> Dict[str, Any]:
        """Convert technical errors to user-friendly messages"""
        error_msg = str(error)

        # Categorize common errors
        if "modification" in error_msg.lower() or "modify" in error_msg.lower():
            friendly_msg = """⚠️ I can only search and analyze the database, not modify it.

Try asking me to find or show you information instead!"""

        elif "rate limit" in error_msg.lower():
            friendly_msg = """⚠️ I'm getting too many requests right now.

Please wait a moment and try again."""

        elif "timeout" in error_msg.lower():
            friendly_msg = """⚠️ That query took too long to process.

Try asking something simpler or more specific."""

        else:
            friendly_msg = f"""⚠️ Hmm, I ran into an issue processing that query.

**Error details:** {error_msg}

Try rephrasing your question or ask something else!"""

        return {
            'type': 'error',
            'content': friendly_msg,
            'technical_error': error_msg
        }


class IntentClassifier:
    """
    Rules-based intent classification.
    Fast, deterministic, no AI needed.
    """

    # Keywords for each intent type
    GREETING_PATTERNS = [
        'hello', 'hi', 'hey', 'good morning', 'good afternoon',
        'good evening', 'greetings', 'howdy', 'sup', "what's up"
    ]

    HELP_PATTERNS = [
        'help', 'what can you do', 'how do i', 'how can i',
        'what are you', 'capabilities', 'features', 'instructions'
    ]

    DATA_QUERY_KEYWORDS = [
        # Question words
        'what', 'which', 'who', 'where', 'when', 'how many', 'how much',

        # Action verbs
        'show', 'find', 'list', 'search', 'get', 'display', 'tell',
        'count', 'give me', 'looking for',

        # Domain-specific
        'film', 'movie', 'actor', 'director', 'location', 'shot',
        'filmed', 'starring', 'year', 'title', 'tv'
    ]

    FOLLOWUP_INDICATORS = [
        'also', 'what about', 'how about', 'and', 'more',
        'tell me more', 'details', 'explain', 'too', 'as well'
    ]

    def classify(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Classify user message intent using rules.

        Returns one of: 'greeting', 'help', 'data_query', 'followup'
        """
        if context is None:
            context = {}

        msg_lower = message.lower().strip()

        # Rule 1: Exact match greetings (highest priority)
        if msg_lower in self.GREETING_PATTERNS:
            return 'greeting'

        # Rule 2: Help requests
        if any(pattern in msg_lower for pattern in self.HELP_PATTERNS):
            return 'help'

        # Rule 3: Follow-up questions (context-dependent)
        if context.get('last_result') is not None:
            # Short messages after a result are likely follow-ups
            if len(msg_lower.split()) <= 3:
                return 'followup'

            # Contains follow-up indicators
            if any(indicator in msg_lower for indicator in self.FOLLOWUP_INDICATORS):
                return 'followup'

        # Rule 4: Data query indicators
        if any(keyword in msg_lower for keyword in self.DATA_QUERY_KEYWORDS):
            return 'data_query'

        # Default: assume data query (safest default)
        return 'data_query'
