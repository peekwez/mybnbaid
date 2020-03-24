import schemaless as sm

from . import sql


class PGViewClient(sm.client.PGClient):
    def fetch_view(self, schema, table, fields, **kwargs):
        self._check_fields(schema, table, fields)
        kwargs = self._get_kwargs(**kwargs)
        command = sql.fetch(schema, table, fields, **kwargs)
        items = self.run(command, callback=sm.client.fetchall)
        next_page = self._next_page(kwargs['offset'], kwargs['limit'])
        return {'items': items, **next_page}

    def create_view(self, schema, table, params):
        self._check_fields(schema, table, params[0])
        command = sql.create(schema, table, params[0])
        self.run(command, values=params[1])
        return True

    def refresh_view(self, schema, table, fields):
        self._check_fields(schema, table, fields)
        command = sql.refresh(schema, table, fields)
        self.run(command)
        return True
