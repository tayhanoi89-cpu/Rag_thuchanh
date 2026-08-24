# Wiki Risk Graph MVP

This project normalizes four synthetic seed CSV files into an Obsidian Wiki and optional Neo4j graph.

## Run order

Run these commands from `RAG/rag_advance/buoi_13`:

```powershell
& "C:\Users\ngocngothi\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts\inspect_data.py
& "C:\Users\ngocngothi\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts\build_entities.py
& "C:\Users\ngocngothi\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts\build_wiki.py
& "C:\Users\ngocngothi\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts\validate_wiki.py
```

Open the `wiki/` directory as an Obsidian vault and start with `Home.md`.

## Neo4j (optional)

Create or update `.env` with `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, and optionally `NEO4J_DATABASE`. Do not commit `.env` or passwords.

After Neo4j is running, execute the following steps in order:

1. Open `cypher/schema.cypher` in Neo4j Browser (or run it with `cypher-shell`) to create the unique `id` constraints.
2. Run the loader:

```powershell
& "C:\Users\ngocngothi\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts\load_neo4j.py
```

3. Open `cypher/demo_queries.cypher` in Neo4j Browser and run queries A-F. Queries B and C use the `$risk_id` parameter, for example `RR-001`.

The loader uses `MERGE`, the entity `id` as the key, and parameterized values. Labels and relationship types are restricted to the MVP allowlist. If Neo4j is unavailable, the loader prints a connection message and exits without changing the CSV or Wiki outputs.

## Current data limitation

The seed data has no `MITIGATES` relation for `RR-011` and `RR-012`. The validator reports these as data gaps; no relationship is invented by the scripts.