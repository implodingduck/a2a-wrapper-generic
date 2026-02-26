import logging
import os
import uvicorn

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    APIKeySecurityScheme
)
from .agent_executor import (
    create_generic_agent_executor,  # type: ignore[import-untyped]
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check for API key authentication."""
    
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key
    
    async def dispatch(self, request: Request, call_next):
        # Allow access to the agent card endpoints without authentication
        if (request.url.path == "/.well-known/agent-card.json" and request.method == "GET"):
            return await call_next(request)
        
        # Check for X-API-Key header
        provided_key = request.headers.get("X-API-Key")
        
        if not provided_key:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "X-API-Key header is required"}
            )
        
        if provided_key != self.api_key:
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "message": "Invalid API key"}
            )
        
        return await call_next(request)


port = int(os.getenv('PORT', 8000))
url = f"https://{os.getenv('CONTAINER_APP_HOSTNAME')}/" if os.getenv('CONTAINER_APP_HOSTNAME') else f'http://localhost:{port}/'
api_key = os.getenv('API_KEY', '')

if __name__ == '__main__':
    # --8<-- [start:AgentSkill]
    skill = AgentSkill(
        id='echo',
        name='Echo Skill',
        description='Echoes the input text',
        tags=['echo', 'test'],
        examples=['hi', 'hello world'],
    )

    # --8<-- [start:AgentCard]
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Echo Agent',
        description='Just an echo agent',
        url=f'{url}',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        security=[{ "api-key": [] }],
        security_schemes={
            "api-key": APIKeySecurityScheme(
                type="apiKey",
                name="X-API-Key",
                in_="header",
            )
        },
    )

    agent_executor = create_generic_agent_executor(public_agent_card)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )
    routes = server.routes()

    async def health_check(request: Request):
        return JSONResponse(content={"status": "ok"})
    
    routes.append(Route(path='/healthz', methods=['GET'], endpoint=health_check))

    
    # Build the app and add authentication middleware
    app = Starlette(routes=routes)
    
    # Add API key authentication middleware if API_KEY is configured
    if api_key:
        app.add_middleware(APIKeyAuthMiddleware, api_key=api_key)
    else:
        print("Warning: API_KEY not set. Authentication is disabled.")

    uvicorn.run(app, host='0.0.0.0', port=port)