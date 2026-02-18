import os
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from .agent_executor import (
    EchoAgentExecutor,  # type: ignore[import-untyped]
)

port = int(os.getenv('PORT', 8000))
url = f"https://{os.getenv('CONTAINER_APP_HOSTNAME')}/" if os.getenv('CONTAINER_APP_HOSTNAME') else f'http://localhost:{port}/'

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
    )

    request_handler = DefaultRequestHandler(
        agent_executor=EchoAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(server.build(), host='0.0.0.0', port=port)