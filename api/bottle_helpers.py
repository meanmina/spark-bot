'''
Helper functions for the bottle server stuff
Mainly for setting up the routes
'''
import json
from bottle import request, response, static_file


def webapi(method, route):
    '''Decorator to tag class methods for the webapi'''
    def outer(fn):

        def inner(self, *args, **kwargs):

            # Could implement a bearer check here maybe
            # or some input validation

            # GET's are always in JSON
            if method == 'GET':
                response.content_type = 'application/json'
                return json.dumps(fn(self, *args, **kwargs))
            elif method == 'POST':
                kwargs['data'] = json.loads(request.body.read().decode('utf-8'))
                return fn(self, *args, **kwargs)
            else:
                return fn(self, *args, **kwargs)

        setattr(
            inner,
            'route_{}'.format(method),
            route
        )
        return inner
    return outer


def picture(route):
    ''' Decorator to tag a method as an image source '''
    def outer(fn):
        def inner(self):
            filename = fn(self)
            return static_file(filename, 'images')
        setattr(
            inner,
            'route_GET',
            route,
        )
        return inner
    return outer


def init_routes(app):
    '''Initialise the bottle routes for an object'''
    for attr_name in dir(app):
        attr = getattr(app, attr_name)
        for method_name in ['GET', 'POST']:
            route = getattr(attr, 'route_{}'.format(method_name), None)
            if route is not None:
                app._app.route(
                    route,
                    method=method_name,
                    callback=attr,
                )
