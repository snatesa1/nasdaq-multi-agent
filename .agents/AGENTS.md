# Workspace Coding Rules — nasdaq-multi-agent

## 1. CodeGraph Usage (Mandatory Default)
- Always use the CodeGraph explore tool (`codegraph_explore`) as the primary method to explore codebase structure, trace function dependencies, locate symbol definitions, and determine the blast radius of modifications.
- Do NOT perform manual grep loops or broad, sequential file-reading loops for codebase research. Keep token usage minimal and efficient.

## 2. Automatic Project Memory Documentation
- Whenever any feature, component, API route, database schema, or agent logic is added, modified, or deleted, the agent MUST automatically document these changes in the project's permanent memory file (`GEMINI.md`).
- This documentation must update the project details, architecture, design constraints, and scope by default at the end of each task without requiring explicit instructions from the user.
