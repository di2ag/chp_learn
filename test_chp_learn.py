import os
import pickle
import json
import logging
import unittest
import requests

from trapi_model.query import Query
LOCAL_URL = 'http://localhost:8000'
#LOCAL_URL = 'http://localhost:80'
#LOCAL_URL = 'http://chp-dev.thayer.dartmouth.edu'

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

class TestChpLearn(unittest.TestCase):
    def setUp(self):
        self.query_endpoint = '/query/'
        self.curies_endpoint = '/curies/'
        self.meta_knowledge_graph_endpoint = '/meta_knowledge_graph/'
        self.relpath_to_test_queries = 'chp_learn/test_queries'

    @staticmethod
    def _get(url, params=None):
        params = params or {}
        res = requests.get(url, json=params)
        print(res.content)
        ret = res.json()
        return ret

    @staticmethod
    def _post(url, params):
        res = requests.post(url, json=params)
        if res.status_code != 200:
            print(res.status_code)
            print(res.content)
            return res.content
        else:
            ret = res.json()
            return ret, res.status_code

    @staticmethod
    def _strip_query(query):
        q_dict = query.to_dict()
        return {key: value for key, value in q_dict.items() if key == 'message'}

    @staticmethod
    def _print_query(query):
        print(json.dumps(query, indent=2))

    def test_curies(self):
        url = LOCAL_URL + self.curies_endpoint
        resp = self._get(url)

    def test_meta_knowledge_graph(self):
        url = LOCAL_URL + self.meta_knowledge_graph_endpoint
        resp = self._get(url)

    def test_all_increase_expr_results(self):
        print('This will be a huge object, and will probably take a while.')
        query = Query.load('1.2', None, query_filepath=os.path.join(MODULE_DIR, self.relpath_to_test_queries, 'all_increase_expr.json'))
        q_dict = self._strip_query(query)
        url = LOCAL_URL + self.query_endpoint
        resp, status = self._post(url, q_dict)
        # Print out at your own warning
        #self._print_query(resp)

    def test_all_disease_related_to_gene(self):
        query_names = [
                'all_disease_related_to_gene_subject.json',
                'all_disease_related_to_gene_object.json',
                ]
        for qname in query_names:
            path = os.path.join(MODULE_DIR, self.relpath_to_test_queries, qname)
            query = Query.load('1.2', None, query_filepath=path)
            q_dict = self._strip_query(query)
            url = LOCAL_URL + self.query_endpoint
            resp, status = self._post(url, q_dict)
            self._print_query(resp)
    
    def test_all_gene_related_to_disease(self):
        query_names = [
                'all_gene_related_to_disease_subject.json',
                'all_gene_related_to_disease_object.json',
                ]
        for qname in query_names:
            path = os.path.join(MODULE_DIR, self.relpath_to_test_queries, qname)
            query = Query.load('1.2', None, query_filepath=path)
            q_dict = self._strip_query(query)
            url = LOCAL_URL + self.query_endpoint
            resp, status = self._post(url, q_dict)
            self._print_query(resp)
    
    def test_all_gene_related_to_gene(self):
        query_names = [
                'all_gene_related_to_gene_subject.json',
                'all_gene_related_to_gene_object.json',
                ]
        for qname in query_names:
            path = os.path.join(MODULE_DIR, self.relpath_to_test_queries, qname)
            query = Query.load('1.2', None, query_filepath=path)
            q_dict = self._strip_query(query)
            url = LOCAL_URL + self.query_endpoint
            resp, status = self._post(url, q_dict)
            self._print_query(resp)
    
    def test_direct_gene_related_to_gene(self):
        query_names = [
                'direct_gene_related_to_gene_subject.json',
                'direct_gene_related_to_gene_object.json',
                ]
        for qname in query_names:
            path = os.path.join(MODULE_DIR, self.relpath_to_test_queries, qname)
            query = Query.load('1.2', None, query_filepath=path)
            q_dict = self._strip_query(query)
            url = LOCAL_URL + self.query_endpoint
            resp, status = self._post(url, q_dict)
            self._print_query(resp)
    
    def test_direct_disease_related_to_gene(self):
        query_names = [
                'direct_disease_related_to_gene_subject.json',
                'direct_disease_related_to_gene_object.json',
                ]
        for qname in query_names:
            path = os.path.join(MODULE_DIR, self.relpath_to_test_queries, qname)
            query = Query.load('1.2', None, query_filepath=path)
            q_dict = self._strip_query(query)
            url = LOCAL_URL + self.query_endpoint
            resp, status = self._post(url, q_dict)
            self._print_query(resp)

if __name__ == '__main__':
    unittest.main()
