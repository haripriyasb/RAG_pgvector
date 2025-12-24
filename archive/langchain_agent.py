from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.prompts import StringPromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import LLMResult, ChatGeneration
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain_community.tools import DuckDuckGoSearchRun
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import re
from typing import List, Union, Optional, Any
from langchain.schema import AgentAction, AgentFinish
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.agents.format_scratchpad import format_log_to_str
from anthropic import Anthropic as AnthropicClient
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

load_dotenv()

# Load models
print("Loading models...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("[OK] Embedding model loaded")

# Create a lightweight wrapper around the Anthropic client for LangChain
class ClaudeWrapper(BaseChatModel):
    """Wrapper around Anthropic's Claude that works with LangChain"""
    
    model_name: str = "claude-3-haiku-20240307"
    api_key: Optional[str] = None
    temperature: float = 0
    
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra attributes
    
    def __init__(self, model_name: str = "claude-3-haiku-20240307", api_key: Optional[str] = None, temperature: float = 0, **kwargs):
        # Initialize with minimal data to avoid proxy issues
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )
        self._create_client()
    
    def _create_client(self):
        """Create the Anthropic client, handling proxy issues"""
        try:
            _client = AnthropicClient(api_key=self.api_key)
        except TypeError as e:
            if "proxies" in str(e):
                # Work around the proxies issue by creating httpx client manually
                import httpx
                _client = AnthropicClient(
                    api_key=self.api_key,
                    http_client=httpx.Client()
                )
            else:
                raise
        object.__setattr__(self, '_client_instance', _client)
    
    @property
    def client(self) -> AnthropicClient:
        """Get the Anthropic client"""
        if not hasattr(self, '_client_instance') or getattr(self, '_client_instance') is None:
            self._create_client()
        return getattr(self, '_client_instance')
    
    @property
    def _llm_type(self) -> str:
        return "anthropic"
    
    @property
    def model(self) -> str:
        return self.model_name
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate text from messages"""
        message_dicts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                message_dicts.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                message_dicts.append({"role": "assistant", "content": msg.content})
            else:
                message_dicts.append({"role": "user", "content": str(msg.content)})
        
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=message_dicts,
            temperature=self.temperature,
        )
        
        text = response.content[0].text
        # Create AIMessage and wrap in ChatGeneration
        message = AIMessage(content=text)
        return LLMResult(generations=[[ChatGeneration(message=message)]])
    
    def invoke(self, input: Union[List[BaseMessage], str], config: Optional[Any] = None, **kwargs: Any) -> AIMessage:
        """Invoke the model with a string or list of messages"""
        if isinstance(input, str):
            # If input is a string, wrap it in a HumanMessage
            messages = [HumanMessage(content=input)]
        elif isinstance(input, (list, tuple)):
            # If it's a list or tuple, check if it contains BaseMessage objects
            if input and isinstance(input[0], BaseMessage):
                messages = list(input)
            else:
                # Otherwise, assume it's a string that got converted
                messages = [HumanMessage(content=str(input))]
        else:
            # Fallback: convert to string
            messages = [HumanMessage(content=str(input))]
        
        message_dicts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                message_dicts.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                message_dicts.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, BaseMessage):
                message_dicts.append({"role": "user", "content": msg.content})
            else:
                message_dicts.append({"role": "user", "content": str(msg)})
        
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=message_dicts,
            temperature=self.temperature,
        )
        
        text = response.content[0].text
        return AIMessage(content=text)
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Async generate - not implemented"""
        raise NotImplementedError("Async generation not implemented")

llm = ClaudeWrapper(
    model_name=os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
    api_key=os.getenv('ANTHROPIC_API_KEY')
)
print(f"[OK] Claude LLM initialized (model: {llm.model})")

# ============================================
# TOOLS
# ============================================

def search_blog_func(query: str) -> str:
    """Search blog posts for relevant content."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    register_vector(conn)
    cur = conn.cursor()
    
    query_embedding = embedding_model.encode(query).tolist()
    
    cur.execute('''
        SELECT title, content, url
        FROM sql_docs
        ORDER BY embedding <=> %s::vector
        LIMIT 3
    ''', (query_embedding,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        return "No relevant blog posts found."
    
    output = "Found these blog posts (from gohigh.substack.com):\n\n"
    for i, (title, content, url) in enumerate(results, 1):
        output += f"{i}. {title}\n"
        output += f"   Summary: {content[:200]}...\n"
        output += f"   URL: {url}\n\n"
    
    return output

def search_web_func(query: str) -> str:
    """Search the internet using DuckDuckGo."""
    try:
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        return results if results else "No internet results found."
    except Exception as e:
        return f"Web search error: {str(e)}"

def count_posts_func(topic: str = "") -> str:
    """Count blog posts about a topic."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    if topic:
        cur.execute("""
            SELECT COUNT(*) 
            FROM sql_docs 
            WHERE title ILIKE %s OR content ILIKE %s
        """, (f'%{topic}%', f'%{topic}%'))
        count = cur.fetchone()[0]
        result = f"Found {count} blog posts about '{topic}' on gohigh.substack.com."
    else:
        cur.execute("SELECT COUNT(*) FROM sql_docs")
        count = cur.fetchone()[0]
        result = f"Total blog posts on gohigh.substack.com: {count}"
    
    cur.close()
    conn.close()
    return result

def list_recent_func(limit: str = "5") -> str:
    """List recent blog posts."""
    try:
        limit_int = int(limit)
    except:
        limit_int = 5
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT title, url, created_at 
        FROM sql_docs 
        ORDER BY created_at DESC 
        LIMIT %s
    """, (limit_int,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        return "No posts found."
    
    output = f"Most recent {len(results)} posts from gohigh.substack.com:\n\n"
    for i, (title, url, created_at) in enumerate(results, 1):
        output += f"{i}. {title}\n   Date: {created_at}\n   URL: {url}\n\n"
    
    return output

def search_web_func(query: str) -> str:
    """Search the internet using DuckDuckGo."""
    try:
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        return results if results else "No internet results found."
    except Exception as e:
        return f"Web search error: {str(e)}"

def get_stats_func(query: str = "") -> str:
    """Get blog statistics."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM sql_docs")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT MIN(created_at), MAX(created_at) FROM sql_docs")
    min_date, max_date = cur.fetchone()
    
    cur.execute("SELECT title FROM sql_docs")
    titles = [row[0].lower() for row in cur.fetchall()]
    
    keywords = {
        'sql server': 0, 'performance': 0, 'index': 0, 
        'query': 0, 'tempdb': 0, 'rcsi': 0
    }
    
    for title in titles:
        for keyword in keywords:
            if keyword in title:
                keywords[keyword] += 1
    
    top_topics = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
    
    cur.close()
    conn.close()
    
    output = f"Blog Statistics:\n\n"
    output += f"Total Posts: {total}\n"
    output += f"Date Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}\n\n"
    output += f"Top Topics:\n"
    for topic, count in top_topics:
        if count > 0:
            output += f"  - {topic.title()}: {count} posts\n"
    
    return output

# Define tools
tools = [
    Tool(
        name="SearchBlog",
        func=search_blog_func,
        description="Search blog posts by topic. Input: search query like 'SQL Server performance'"
    ),
    Tool(
        name="CountPosts",
        func=count_posts_func,
        description="Count blog posts. Input: topic name or empty string for total"
    ),
    Tool(
        name="ListRecent",
        func=list_recent_func,
        description="List recent posts. Input: number like '5' or '10'"
    ),
    Tool(
        name="GetStats",
        func=get_stats_func,
        description="Get blog statistics. Input: empty string"
    ),
    # Tool(
    #     name="WebSearch",
    #     func=search_web_func,
    #     description="Search the internet for blog posts and information using DuckDuckGo. Input: search query"
    # )
]

# ============================================
# Create Custom Prompt
# ============================================

template = """Answer the following question as best you can. You have access to these tools:

{tools}

Use this format:

Question: the input question
Thought: think about what to do
Action: tool to use, must be one of [{tool_names}]
Action Input: input for the tool
Observation: result from the tool
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer

Begin!

Question: {input}
{agent_scratchpad}"""

class CustomPromptTemplate(StringPromptTemplate):
    template: str
    tools: List[Tool]
    
    def format(self, **kwargs) -> str:
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += f"Thought: {action.log}\n"
            thoughts += f"Action: {action.tool}\n"
            thoughts += f"Action Input: {action.tool_input}\n"
            thoughts += f"Observation: {observation}\n"
        
        kwargs["agent_scratchpad"] = thoughts
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        return self.template.format(**kwargs)

prompt = CustomPromptTemplate(
    template=template,
    tools=tools,
    input_variables=["input", "intermediate_steps"]
)

# ============================================
# Output Parser
# ============================================

from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.schema import AgentAction, AgentFinish

class CustomOutputParser(ReActSingleInputOutputParser):
    """Custom output parser for Claude ReAct format with better error handling."""
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        # Check if agent is done - PRIORITY: Check Final Answer first
        if "Final Answer:" in text or "Final answer:" in text:
            # Extract everything after "Final Answer:"
            final_answer = re.search(r"(?:Final Answer|Final answer)\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
            if final_answer:
                answer_text = final_answer.group(1).strip()
                # Take only the first line if there are multiple
                answer_text = answer_text.split('\n')[0].strip()
                return AgentFinish(
                    return_values={"output": answer_text},
                    log=text
                )
        
        # Try to parse Action and Action Input
        action_match = re.search(r"Action\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        action_input_match = re.search(r"Action\s+Input\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
        
        if action_match:
            action = action_match.group(1).strip()
            action_input = action_input_match.group(1).strip() if action_input_match else ""
            
            # Clean up action input (remove extra quotes if present)
            action_input = action_input.strip('"').strip()
            
            return AgentAction(tool=action, tool_input=action_input, log=text)
        
        # If no action and no final answer, return an error as a finish
        return AgentFinish(
            return_values={"output": text[:500]},
            log=text
        )

output_parser = CustomOutputParser()

# ============================================
# Create Agent
# ============================================

# Use create_react_agent instead of deprecated LLMSingleActionAgent
from langchain_core.prompts import PromptTemplate

# Simple ReAct prompt - optimized for Claude (stop after Final Answer)
react_prompt = PromptTemplate.from_template("""Answer the following question as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT: Output ONLY the next step. Do NOT include observations or previous steps.

Begin!

Question: {input}
{agent_scratchpad}""")

agent = create_react_agent(llm, tools, react_prompt)

agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=3,
    max_time_limit=60,
    handle_parsing_errors=True,
    early_stopping_method="force"
)

# ============================================
# Interactive Loop
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print("   LangChain Blog Agent")
    print("=" * 70)
    print("\nTry asking:")
    print("  - 'How many posts do I have?'")
    print("  - 'Search for RCSI'")
    print("  - 'Show me 5 recent posts'")
    print("  - 'Get blog statistics'")
    print("=" * 70)
    print()
    
    while True:
        print("\n" + "-" * 70)
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n[Goodbye!]")
            break
        
        if not user_input:
            continue
        
        print("\n[Agent is thinking...]\n")
        
        try:
            result = agent_executor.invoke({"input": user_input})
            print(f"\n[OK] Agent: {result['output']}")
        except Exception as e:
            import traceback
            print(f"\n[ERROR] {e}")
            traceback.print_exc()