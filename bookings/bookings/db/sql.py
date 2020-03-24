OPERATORS = {
    "or": "UNION\n",
    "and": "INTERSECT\n"
}
ORDER = {
    "asc": "ASC",
    "desc": "DESC"
}


def index(schema, table, field):
    return f"""
    SELECT {table}_id FROM
    {schema}.{table}_{field}_idx
    WHERE {field}=%s
    """


def name(table, fields):
    return '_'.join((table,) + fields)


def create(schema, table, fields):
    op = 'and'
    order = 'desc'
    limit = 'NULL'
    offset = 0
    vname = name(table, fields)

    return f"""
    CREATE MATERIALIZED VIEW IF NOT EXISTS {schema}.{vname}
    AS
    WITH table_ids AS (
    {OPERATORS[op].strip().join([index(schema, table, field)
                         for field in fields]).strip()}
    )
    SELECT id, body FROM {schema}.{table}
    WHERE {table}.id IN (SELECT {table}_id FROM table_ids)
    ORDER BY id {ORDER[order]}
    OFFSET {offset} LIMIT {limit};
    CREATE UNIQUE INDEX IF NOT EXISTS
    mv_{vname}_idx ON {schema}.{vname}(id);
    """


def refresh(schema, table, fields):
    return f"""
    REFRESH MATERIALIZED VIEW CONCURRENTLY {schema}.{name(table,fields)};
    """


def fetch(schema, table, fields, **kwargs):
    offset = kwargs['offset']
    limit = kwargs['limit']
    return f"""
    SELECT body FROM {schema}.{name(table,fields)} OFFSET {offset} LIMIT {limit}
    """
