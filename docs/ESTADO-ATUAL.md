# Estado atual — PrintReady CAD Agent

Revisão documental: **13/10/2026**, America/Sao_Paulo. Git inicial limpo em `main`, HEAD `112682f`.

## Observado e documentado

`pyproject.toml` requer Python >=3.11,<3.14, CadQuery, trimesh, FastAPI, Pydantic, MCP e rank-bm25; publica `printready-api`/`printready-mcp`. O frontend usa React/TypeScript/Three.js/Vite e Playwright.

`src/printready/service.py` contém geração por `generate_geometry`, busca de evidências, escrita de report e estado inicial de slicer `not_run`. A árvore separa modelos, CAD, knowledge, planner, service, store, slicer, API e MCP.

[Arquitetura](ARCHITECTURE.md) explica parâmetros tipados, templates confiáveis, milímetros/metros, validação CAD/mesh e distinção entre `geometry_validated`, slicer e impressão física. O README descreve três famílias, exportações e parser local limitado; não é text-to-CAD irrestrito. O limite público exclui comandos físicos de impressora.

## Evidências anteriores e operação

O README relata resultados de retrieval e slicing local; permanecem **documentação anterior**, sem repetição/validação nesta sessão. Nenhum job/arquivo de `_data/`, perfil privado, G-code ou banco foi aberto.

Comandos encontrados: `uv run printready-api`, `uv run printready-mcp`, Ruff, `uv run pytest`, `uv run python -m printready.evaluate`, format/build/E2E frontend. Requisitos do README: uv, Python 3.11 e Node 24; Bambu Studio opcional. Todos **não executado nesta tarefa**; nem `start.bat`, instalações ou Playwright browser install foram executados.

## Roadmap existente e retomada

O README propõe casos de slicing/calibração, corpus licenciado, adapters FreeCAD/Blender, Orca K1C e edição privada. São milestones já documentados, não nova autorização. A arquitetura chama a edição privada de futura; outra raiz Live tem aviso próprio de arquivamento. Não se reescreveu história nem presumiu integração entre cópias.

Última etapa comprovada: índice/estado e instruções conferidos. Fit, resistência, slicing efetivo e impressão continuam sem validação atual.

Sugestões não aprovadas:

1. Confirmar qual milestone está autorizado nesta edição pública.
2. Quando autorizado, registrar testes/artefatos e separar CAD, slicer e resultado físico.
3. Rever referências de edição privada somente com evidência da cópia correta.

[Índice](INDEX.md).
