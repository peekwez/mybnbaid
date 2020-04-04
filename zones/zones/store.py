import csv
import sqlite3
import pkg_resources


class NotFound(Exception):
    pass


def _table():
    return f"""
    CREATE TABLE zones (
        fsa TEXT PRIMARY KEY,
        city TEXT,
        region TEXT
    );
    """


def _insert():
    return """
    INSERT INTO zones (fsa,city,region)
    VALUES (?,?,?);
    """


def _get():
    return """
    SELECT * from zones WHERE fsa=?;
    """


def _all():
    return """
    SELECT * FROM zones
    """


def _filter(column):
    return f"""
    SELECT DISTINCT {column} FROM zones;
    """


class ZonesStore(object):
    def __init__(self):
        self._con = sqlite3.connect(':memory:')
        self._con.row_factory = sqlite3.Row
        self._cur = self._con.cursor()
        self._setup()

    def _setup(self):
        self._cur.execute(_table())
        datafile = pkg_resources.resource_filename(
            'zones', 'zones.csv'
        )
        with open(datafile, 'r') as z:
            data = csv.DictReader(z)
            rows = [(row['fsa'], row['city'], row['region']) for row in data]
        self._cur.executemany(_insert(), rows)
        self._con.commit()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._con.close()

    def _get(self, fsa):
        self._cur.execute(_get(), (fsa,))
        data = self._cur.fetchall()
        if not data:
            raise NotFound(f'there is no location for {fsa}')
        return dict(data[0])

    def _filter(self, column):
        self._cur.execute(_filter(column))
        data = [dict(row) for row in self._cur.fetchall()]
        return data

    def city(self, fsa):
        return {'city': self._get(fsa)['city']}

    def region(self, fsa):
        return {'region': self._get(fsa)['region']}

    def location(self, fsa):
        return self._get(fsa)

    def cities(self):
        return {'items': self._filter('city')}

    def regions(self):
        return {'items': self._filter('region')}

    def locations(self):
        self._cur.execute(_all())
        data = [dict(row) for row in self._cur.fetchall()]
        return {'items': data}


memdata = ZoneStore()
