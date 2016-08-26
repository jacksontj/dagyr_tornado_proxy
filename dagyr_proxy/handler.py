import yaml
import logging

import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.httpclient

import state
import dagyr.dag

log = logging.getLogger(__name__)


class DagHandler(tornado.web.RequestHandler):
    '''Proxy handler that just executes the DAGs associated to make the request
    '''

    @tornado.gen.coroutine
    def prepare(self):
        '''Create our own DAGRunner, which will point at a dag config
        '''
        req_state = state.RequestState(self.request)

        # get an executor
        dag_executor = dagyr.dag.DagExecutor(
            self.application.dag_config,
            req_state,
        )
        # execute it!
        dag_executor.call_hook('ingress')

        # if the response is set-- then we need to set the state, run the egress
        # DAG, and serve the response
        if req_state.response != {}:
            req_state.set_response(req_state.response)
            # call egress hook
            dag_executor.call_hook('egress')
            self.serve_state(req_state.response)
            return

        # make downstream request
        http_client = tornado.httpclient.AsyncHTTPClient()
        try:
            ret = yield http_client.fetch(req_state.get_request())
        except tornado.httpclient.HTTPError as e:
            ret = e.response

        req_state.set_response(ret)

        # call egress hook
        dag_executor.call_hook('egress')

        # set state.response as response
        self.serve_state(req_state.response)
        return  # so we don't call other handlers

    def serve_state(self, req_state):
        if 'code' in req_state:
            self.set_status(req_state['code'])

        if 'headers' in req_state:
            for k, v in req_state['headers'].iteritems():
                if k in ('Content-Length',):
                    continue
                self.set_header(k, v)

        if 'body' in req_state:
            self.write(req_state['body'])

        self.finish()
