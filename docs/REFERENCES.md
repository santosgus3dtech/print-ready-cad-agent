# References and intended integrations

These projects inform the architecture. Their capabilities are not all implemented here, and
listing them does not mean their source code has been bundled into this repository.

| Reference | Role | Current status here |
| --- | --- | --- |
| [text-to-cad](https://github.com/earthtojake/text-to-cad) | Agent-oriented CAD workflow and exports | Architectural reference |
| [freecad-mcp](https://github.com/neka-nat/freecad-mcp) | FreeCAD creation and inspection | Planned adapter |
| [codex-cad](https://github.com/alexanderkoller/codex-cad) | Printer-aware geometry and local slicer checks | Reference for validation stages |
| [BlenderRAG](https://github.com/MaxRondelli/BlenderRAG) | Retrieval-augmented code generation | Reference; current corpus is text-only |
| [mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Blender editing and visual inspection | Planned adapter |
| [bambu-printer-mcp](https://github.com/DMontgomery40/bambu-printer-mcp) | Bambu slicing and printer integration | Reference; physical control deferred |
| [mcp-3D-printer-server](https://github.com/DMontgomery40/mcp-3D-printer-server) | Multi-vendor printer adapters | Reference; K1C needs direct validation |
| [simple-3d-modeling-mcp](https://github.com/mazzanfar/simple-3d-modeling-mcp) | OpenSCAD/WASM prototyping | Optional future engine |

Existing personal portfolio projects informing the design are `parametric-fit-validation-lab`,
`mcp-blender-test`, `meshy-image-to-3d-toolkit`, `3d-nameplate-generator`,
`manufacturing-knowledge-agent` and `pi-sentinel`. Operational data and private models from those
projects are not copied here. The `parametric-design-mcp` concept is incorporated into this project.

Authoritative implementation documentation:

- [CadQuery](https://cadquery.readthedocs.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Bambu Studio CLI](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage)
- [3MF specification](https://github.com/3MFConsortium/spec_core)
- [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)

The BlenderRAG study's code-execution rate is not a physical-print success rate. This project's
metrics must be evaluated on its own corpus and geometry cases.
