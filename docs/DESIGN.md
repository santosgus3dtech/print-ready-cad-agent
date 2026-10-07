# Workbench design

The generated concept is retained in `design/workbench-concept.png` as a design reference,
not as a screenshot of implemented behavior.

- White application chrome, pale neutral canvas, charcoal type.
- Emerald commands, teal geometry, blue interaction accents, amber review states.
- 64 px header, 290 px parameters rail, full remaining 3D viewport, 300 px inspector.
- 13 px base type; compact labels and controls; 5 px control radius.
- Three part tabs; explicit numerical inputs; a select for printer/material/nozzle.
- Inspector tabs for validation, evidence and local history.
- Small icon tools for rotation, wireframe, fit and grid, with labels/tooltips.
- Mobile shows the model first, then parameters and inspector in document flow.

Intentional implementation differences from the concept: no invented account/settings controls,
no unsupported pan/zoom modes, actual generation measurements, a clearly labeled local parser,
and an explicit distinction between geometry exports and sliced output.

## Fidelity verification

| Area | Rendered evidence | Decision |
| --- | --- | --- |
| Work-focused layout | Three rails at desktop, model first at mobile | Retained without decorative cards |
| Real object visibility | STEP-derived GLB, distinct body/lid, pixel framing assertions | Actual solids replace concept-only rounded geometry |
| Restraint and hierarchy | Compact header, numerical controls, white chrome | Retained; no account controls without account functionality |
| Inspection workflow | Expandable geometry checks, retrieval evidence and saved history | Retained with measured values rather than illustrative numbers |
| Print readiness | Separate geometry and slicer stages | Exact-profile slicing; no implied physical-print certification |

Verified at 1536 x 1024, 1024 x 768 and 390 x 844. Chromium capture can emit a GPU
ReadPixels performance warning during screenshots; only that specific driver message is annotated
separately from application errors in the test. The in-app browser also receives manual interaction
checks. Browser plugin is not available in this session; regular Playwright supplies reproducible
tests and screenshot files.
