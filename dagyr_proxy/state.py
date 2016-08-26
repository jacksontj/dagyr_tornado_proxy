import tornado.httpclient

import pyrsistent
import copy


class RequestState(object):
    '''Encapsulate the request/response state in the proxy

    This includes:
        - pristine_request
        - request
        - pristine_response
        - response
    '''
    def __init__(self, request):
        self.pristine_request = {
            'headers': dict(request.headers),
            'path': request.path,
        }
        # TODO: namespace? also want to include options such as
        # follow redirects, timeouts, etc. (basically transaction overrideable
        # configuration)
        self.request = copy.deepcopy(self.pristine_request)

        # freeze the pristine request
        self.pristine_request = pyrsistent.freeze(self.pristine_request)

        self.pristine_response = {}
        self.response = {}

    def get_request(self):
        '''Return tornado.httpclient.HTTPRequest version of `request`
        '''
        return tornado.httpclient.HTTPRequest(
            'http://{host}{path}'.format(
                host=self.request['headers']['Host'],
                path=self.request['path'],
            ),
            headers=self.request['headers'],
        )

    def set_response(self, response):
        if self.pristine_response != {}:
            raise Exception('Response already set???')

        if isinstance(response, dict):
            # TODO: enforce a schema!
            if 'headers' not in response:
                response['headers'] = {}
            self.pristine_response = response
        else:
            self.pristine_response = {
                'code': response.code,
                'headers': dict(response.headers),
                'body': response.body,  # TODO: stream?
            }
        self.response = copy.deepcopy(self.pristine_response)
