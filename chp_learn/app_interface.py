from trapi_model.knowledge_graph import KnowledgeGraph
from trapi_model.meta_knowledge_graph import MetaKnowledgeGraph
from chp_utils.curie_database import CurieDatabase
from chp_utils.conflation import ConflationMap

from .trapi_interface import TrapiInterface
from .apps import *

def get_app_config(query):
    return ChpLearnConfig

def get_trapi_interface(chp_look_up_config = get_app_config(None)):
    return TrapiInterface(trapi_version='1.2')

def get_meta_knowledge_graph() -> MetaKnowledgeGraph:
    interface = get_trapi_interface()
    return interface.get_meta_knowledge_graph()

def get_curies() -> CurieDatabase:
    interface = get_trapi_interface()
    return interface.get_curies()

def get_conflation_map() -> ConflationMap:
    interface = get_trapi_interface()
    return interface.get_conflation_map()
    
def get_response(consistent_queries) -> tuple:
    """ Should return app responses plus app_logs, status, and description information.
    """
    responses = []
    status:str = None
    description:str = None
    app_logs = []
    interface = get_trapi_interface()
    for consistent_query in consistent_queries:
        try:
            resp, log = interface.get_response(consistent_query)
        except Exception as ex:
            raise ex
            responses = []
            app_logs.extend(interface.logger.to_dict())
            status = 'Unexpected error. See description.'
            description = 'Error during lookup. {}'.format(ex)
            return responses, app_logs, status, description
        responses.append(resp)
        app_logs.extend(interface.logger.to_dict())
    status = 'Success'
    return responses, app_logs, status, description
    
