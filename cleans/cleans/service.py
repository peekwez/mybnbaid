import backless as bk

from . import exceptions as exc


class CleansService(bk.svc.BaseService):
    _name = 'cleans'
    _version = '0.0.1'

    def _check_owner(self, user, user_id, zone, clean_id):
        clean = self._repo.get(zone, 'cleans', clean_id)
        key = f'{user}_id'
        if clean[key] != user_id:
            raise exc.NotOwner('user cannot modify this resource')
        return clean

    def create_clean(self, user_id, data):
        fields = ('id', 'created', 'updated')
        for field in fields:
            data.pop(field)

        zone = clean['zone']
        clean = self._repo.put(zone, 'cleans', data)
        return clean

    def review_clean(self, user_id, zone, clean_id, review):
        _ = self._check_owner('host', user_id, zone, clean_id)
        data = dict(review=review)
        clean = self._repo.edit(zone, 'cleans', clean_id, data)
        return clean

    def rate_clean(self, user_id, zone, clean_id, rating):
        _ = self._check_owner('host', user_id, zone, clean_id)
        data = dict(rating=rating)
        clean = self._repo.edit(zone, 'cleans', clean_id, data)
        return clean

    def get_property_cleans(self, user_id, zone, property_id, limit=20, offset=0):
        params = dict(property_id=property_id)
        kwargs = dict(offset=offset, limit=limit)
        cleans = self._repo.filter(zone, 'cleans', params, **kwargs)
        return cleans

    def get_aid_cleans(self, user_id, zone, limit=20, offset=0):
        params = dict(aid_id=user_id)
        kwargs = dict(offset=offset, limit=limit)
        cleans = self._repo.filter(zone, 'cleans', params, **kwargs)
        return cleans


def main():
    bk.utils.start_service(CleansService)


if __name__ == "__main__":
    main()
