import re

from qaequilibrae.modules.common_tools.sql_identifiers import quote_identifier

# Node ids below this one are left free for centroids, which the user numbers themselves and is
# much easier to keep track of in a small, tidy range.
FIRST_NETWORK_NODE_ID = 10_000

# AequilibraE has no sequence for node_id: each of the four triggers that drops a node under a
# link endpoint picks `max(node_id) + 1` inline. An expression this function has already raised
# is matched as well as a stock one, so re-running with a different floor replaces it instead of
# nesting a second max() around it.
_NEW_NODE_ID = re.compile(
    r"(?:max\s*\(\s*)?coalesce\s*\(\s*max\s*\(\s*node_id\s*\)\s*\+\s*1\s*,\s*1\s*\)(?:\s*,\s*\d+\s*\))?",
    re.IGNORECASE,
)


def reserve_node_ids_for_centroids(project, first_node_id: int = FIRST_NETWORK_NODE_ID) -> None:
    """Raises the ids the project hands to nodes created by digitizing, leaving the low ones free.

    The triggers are rewritten in the project database itself - there is nowhere else to put this,
    since the ids are minted by SQL while the link is being inserted. They are found by what they
    contain rather than by name, because projects written before AequilibraE prefixed its triggers
    still carry them as `new_link_a_node` and friends.

    Nothing is renumbered: the floor only applies to nodes created from here on, and a project
    already past it keeps counting from where it was.
    """
    with project.db_connection as conn:
        triggers = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'trigger' AND sql LIKE '%coalesce%'"
        ).fetchall()

        for name, sql in triggers:
            floored = _NEW_NODE_ID.sub(f"max(coalesce(max(node_id) + 1,1), {int(first_node_id)})", sql)
            if floored == sql:
                continue

            conn.execute(f"DROP TRIGGER {quote_identifier(name)}")
            conn.execute(floored)
