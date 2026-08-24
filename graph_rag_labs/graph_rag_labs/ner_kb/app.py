from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from neo4j import GraphDatabase


DATA_DIR = Path(__file__).parent
load_dotenv(DATA_DIR / ".env")

st.set_page_config(page_title="Buoi 12 - Legal knowledge graph", page_icon=":material/account_tree:", layout="wide")


@st.cache_data(ttl="5m")
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, dtype="string")


@st.cache_resource
def neo4j_driver():
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )


@st.cache_data(ttl="60s")
def load_graph_summary() -> tuple[pd.DataFrame, pd.DataFrame]:
    driver = neo4j_driver()
    database = os.environ["NEO4J_DATABASE"]
    labels = driver.execute_query(
        "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS total ORDER BY total DESC",
        database_=database,
    ).records
    relationships = driver.execute_query(
        "MATCH ()-[r]->() RETURN type(r) AS relationship_type, count(*) AS total ORDER BY total DESC",
        database_=database,
    ).records
    return pd.DataFrame([dict(record) for record in labels]), pd.DataFrame([dict(record) for record in relationships])


st.title("Buoi 12 - Legal knowledge graph")
st.caption("Pipeline entity enrichment, relationship validation, and Neo4j import")

with st.sidebar:
    if st.button("Refresh dashboard", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    show_raw = st.checkbox("Show raw artifact tables", value=False)

try:
    documents = load_csv("cleaned_documents.csv")
    entities = load_csv("entities.csv")
    relationships = load_csv("relationships.csv")
    report = load_csv("validation_report.csv")
    labels_df, relationship_counts_df = load_graph_summary()
except Exception as error:
    st.error(f"Unable to load the knowledge graph: {type(error).__name__}: {error}")
    st.stop()

with st.container(horizontal=True):
    st.metric("Documents", len(documents), border=True)
    st.metric("Canonical entities", entities["entity_id"].nunique(), border=True)
    st.metric("Validated relationships", len(relationships), border=True)
    st.metric("Validation failures", int(report["validation_status"].eq("FAIL").sum()), border=True)

overview, entities_view, relationships_view, graph_view = st.tabs(
    ["Overview", "Entities", "Relationships", "Neo4j graph"]
)

with overview:
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader("Entities by type")
            st.bar_chart(entities["entity_type"].value_counts().rename_axis("entity_type").reset_index(name="total"), x="entity_type", y="total")
    with right:
        with st.container(border=True):
            st.subheader("Relationships by type")
            st.bar_chart(relationships["relationship_type"].value_counts().rename_axis("relationship_type").reset_index(name="total"), x="relationship_type", y="total")
    with st.container(border=True):
        st.subheader("Validation summary")
        st.dataframe(report["validation_status"].value_counts().rename_axis("status").reset_index(name="total"), hide_index=True)

with entities_view:
    selected_entity_types = st.multiselect(
        "Entity types", options=sorted(entities["entity_type"].unique()), default=sorted(entities["entity_type"].unique())
    )
    filtered_entities = entities[entities["entity_type"].isin(selected_entity_types)]
    st.dataframe(filtered_entities, hide_index=True)

with relationships_view:
    selected_relationship_types = st.multiselect(
        "Relationship types", options=sorted(relationships["relationship_type"].unique()), default=sorted(relationships["relationship_type"].unique())
    )
    filtered_relationships = relationships[relationships["relationship_type"].isin(selected_relationship_types)]
    st.dataframe(filtered_relationships, hide_index=True)

with graph_view:
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader("Nodes in Neo4j")
            st.dataframe(labels_df, hide_index=True)
    with right:
        with st.container(border=True):
            st.subheader("Relationships in Neo4j")
            st.dataframe(relationship_counts_df, hide_index=True)
    with st.container(border=True):
        st.subheader("Document relationships")
        driver = neo4j_driver()
        rows = driver.execute_query(
            "MATCH (source:Document)-[relationship:THAM_CHIEU|SUA_DOI_BO_SUNG|THAY_THE_BOI]->(target:Document) "
            "RETURN source.title AS source, type(relationship) AS relationship_type, target.title AS target LIMIT 50",
            database_=os.environ["NEO4J_DATABASE"],
        ).records
        st.dataframe(pd.DataFrame([dict(row) for row in rows]), hide_index=True)

if show_raw:
    with st.expander("Raw pipeline artifacts"):
        st.write("Cleaned documents")
        st.dataframe(documents, hide_index=True)
        st.write("Validation report")
        st.dataframe(report, hide_index=True)