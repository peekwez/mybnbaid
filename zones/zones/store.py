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


class ZoneStore(object):
    def __init__(self):
        self._con = sqlite3.connect(':memory:')
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
            NotFound('there is not location for {fsa}')
        return data[0]

    def _filter(self, column):
        self._cur.execute(_filter(column))
        return self._cur.fetchall()

    def city(self, fsa):
        return self._get(fsa)[1]

    def region(self, fsa):
        return self._get(fsa)[2]

    def area(self, fsa):
        return self._get(fsa)

    def cities(self):
        return self._filter('city')

    def regions(self):
        return self._filter('region')

    def areas(self):
        self._cur.execute(_all())
        return self._cur.fetchall()
