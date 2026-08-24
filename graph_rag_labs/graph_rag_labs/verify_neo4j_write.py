from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
auth = ("neo4j", "abcd1234")
database = "kb-hops"

with GraphDatabase.driver(uri, auth=auth) as driver:
    with driver.session(database=database) as session:
        session.run("CREATE (n:Test {id: $id})", id="probe")
        count = session.run("MATCH (n:Test) RETURN count(n) AS cnt").single()["cnt"]
        print("count", count)
