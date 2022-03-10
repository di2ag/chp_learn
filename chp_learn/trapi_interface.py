from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from enum import Enum
from collections import defaultdict
import os


from trapi_model.logger import Logger as TrapiLogger
from trapi_model.message import Message
from trapi_model.query_graph import QEdge, QueryGraph
from trapi_model.biolink.constants import *
from trapi_model.query_graph import QNode
from trapi_model.query import Query
from trapi_model.meta_knowledge_graph import MetaKnowledgeGraph
from trapi_model.knowledge_graph import KEdge, KnowledgeGraph
from trapi_model.results import Result, Results, Binding
from trapi_model.message import Message
from chp_utils.curie_database import CurieDatabase
from chp_utils.conflation import ConflationMap

from .trapi_exceptions import *
from .models import Gene, Disease, GeneToFillGeneResult, DiseaseToFillGeneResult

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))

class TrapiInterface:
    def __init__(self,
                 trapi_version='1.2',
                ):
        self.trapi_version = trapi_version
        # Get base handler for processing curies and meta kg requests
        self._get_curies()
        self.meta_knowledge_graph = self._get_meta_knowledge_graph()
        self.conflation_map = self._get_conflation_map()

        # Initialize interface level logger
        self.logger = TrapiLogger()

    def get_query_type(self, query):
        categories = set()
        for qnode_id, qnode in query.message.query_graph.nodes.items():
            categories.add(qnode.categories[0])
        # If there is only one category than its a gene to gene else its a gene to disease
        if len(categories) == 1:
            return 'g2g'
        return 'g2d'

    def get_response(self, query):
        # Get the edge object (there's only one)
        for qedge_id, qedge in query.message.query_graph.edges.items():
            # Get predicate inverse if there is one
            try:
                predicate_inverse = qedge.predicates[0].get_inverse()
            except:
                predicate_inverse = None
            predicates = [qedge.predicates[0].get_curie(), predicate_inverse.get_curie()]
            # Get q_subject and q_object nodes
            q_subject = query.message.query_graph.nodes[qedge.subject]
            q_object = query.message.query_graph.nodes[qedge.object]
        # Get response based on whether subject or object is specified
        if not q_subject.ids and not q_object.ids:
            return self._response_from_edge_no_ids(query, qedge_id, qedge, qedge.subject, q_subject, qedge.object, q_object, predicates)
        elif q_subject.ids and q_object.ids:
            return self._response_from_edge_both_ids(query, qedge_id, qedge, qedge.subject, q_subject, qedge.object, q_object, predicates)
        elif q_subject.ids and not q_object.ids:
            return self._response_from_qsubject(query, qedge_id, qedge, qedge.subject, q_subject, qedge.object, q_object, predicates)
        elif not q_subject.ids and q_object.ids:
            return self._response_from_qobject(query, qedge_id, qedge, qedge.subject, q_subject, qedge.object, q_object, predicates)
        raise UnidentifiedQueryType
    
    def _return_no_result(self, query, message):
        resp = query.get_copy()
        resp.logger.info(message)
        return resp, []

    def _response_from_qobject(self, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates):
        qs = []
        if q_subject.categories[0] == BIOLINK_GENE_ENTITY:
            if q_object.categories[0] == BIOLINK_GENE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    try:
                        qs.extend(
                                list(GeneToFillGeneResult.objects.filter(
                                    query_gene=Gene.objects.get(curie=q_object.ids[0]),
                                    predicate=predicate,
                                    ))
                                )
                    except GeneToFillGeneResult.DoesNotExist:
                        query.logger.info('Could not find Gene to Gene result for query.')
                        continue
                    except Gene.DoesNotExist:
                        query.logger.info(f'Gene with curie {q_object.ids[0]} does not exist in the database.')
                        continue
            elif q_object.categories[0] == BIOLINK_DISEASE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    try:
                        qs.extend(
                                list(DiseaseToFillGeneResult.objects.filter(
                                    query_disease=Disease.objects.get(curie=q_object.ids[0]),
                                    predicate=predicate,
                                    ))
                                )
                    except DiseaseToFillGeneResult.DoesNotExist:
                        query.logger.info('Could not find Disease to Gene result for query.')
                        continue
                    except Disease.DoesNotExist:
                        query.logger.info(f'Disease with curie {q_object.ids[0]} does not exist in the database.')
                        continue
        elif q_subject.categories[0] == BIOLINK_DISEASE_ENTITY:
            for predicate in predicates:
                if not predicate:
                    continue
                try:
                    qs.extend(
                            list(DiseaseToFillGeneResult.objects.filter(
                                fill_gene=Gene.objects.get(curie=q_object.ids[0]),
                                predicate=predicate,
                                ))
                            )
                except DiseaseToFillGeneResult.DoesNotExist:
                    query.logger.info('Could not find Disease to Gene result for query.')
                    continue
                except Gene.DoesNotExist:
                    query.logger.info(f'Gene with curie {q_object.ids[0]} does not exist in the database.')
                    continue
        return self._format_response(qs, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates)

    def _response_from_qsubject(self, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates):
        qs = []
        if q_subject.categories[0] == BIOLINK_GENE_ENTITY:
            if q_object.categories[0] == BIOLINK_GENE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    try:
                        qs.extend(
                                list(GeneToFillGeneResult.objects.filter(
                                    query_gene=Gene.objects.get(curie=q_subject.ids[0]),
                                    predicate=predicate,
                                    ))
                                )
                    except GeneToFillGeneResult.DoesNotExist:
                        query.logger.info('Could not find Gene to Gene result for query.')
                        continue
                    except Gene.DoesNotExist:
                        query.logger.info(f'Gene with curie {q_subject.ids[0]} does not exist in the database.')
                        continue
            elif q_object.categories[0] == BIOLINK_DISEASE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    try:
                        qs.extend(
                                list(DiseaseToFillGeneResult.objects.filter(
                                    fill_gene=Gene.objects.get(curie=q_subject.ids[0]),
                                    predicate=predicate,
                                    ))
                                )
                    except DiseaseToFillGeneResult.DoesNotExist:
                        query.logger.info('Could not find Disease to Gene result for query.')
                        continue
                    except Gene.DoesNotExist:
                        query.logger.info(f'Gene with curie {q_subject.ids[0]} does not exist in the database.')
                        continue
        elif q_subject.categories[0] == BIOLINK_DISEASE_ENTITY:
            for predicate in predicates:
                if not predicate:
                    continue
                try:
                    qs.extend(
                            list(DiseaseToFillGeneResult.objects.filter(
                                query_disease=Disease.objects.get(curie=q_subject.ids[0]),
                                predicate=predicate,
                                ))
                            )
                except DiseaseToFillGeneResult.DoesNotExist:
                    query.logger.info('Could not find Disease to Gene result for query.')
                    continue
                except Disease.DoesNotExist:
                    query.logger.info(f'Disease with curie {q_subject.ids[0]} does not exist in the database.')
                    continue
        return self._format_response(qs, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates)

    def _response_from_edge_no_ids(self, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates):
        qs = []
        if q_subject.categories[0] == BIOLINK_GENE_ENTITY:
            if q_object.categories[0] == BIOLINK_GENE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    qs.extend(
                            list(GeneToFillGeneResult.objects.filter(
                                predicate=predicate,
                                ))
                            )
            elif q_object.categories[0] == BIOLINK_DISEASE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    qs.extend(
                            list(DiseaseToFillGeneResult.objects.filter(
                                predicate=predicate,
                                ))
                            )
        elif q_subject.categories[0] == BIOLINK_DISEASE_ENTITY:
            for predicate in predicates:
                if not predicate:
                    continue
                qs.extend(
                        list(DiseaseToFillGeneResult.objects.filter(
                            predicate=predicate,
                            ))
                        )
        return self._format_response(qs, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates)


    def _response_from_edge_both_ids(self, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates):
        qs = []
        if q_subject.categories[0] == BIOLINK_GENE_ENTITY:
            if q_object.categories[0] == BIOLINK_GENE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    try:
                        gene_list = [
                                Gene.objects.get(curie=q_subject.ids[0]),
                                Gene.objects.get(curie=q_object.ids[0]),
                                ]
                        qs.extend(
                                GeneToFillGeneResult.objects.filter(
                                    Q(query_gene__in =gene_list) & Q(fill_gene__in=gene_list) & Q(predicate=predicate)
                                    )
                                )
                    except GeneToFillGeneResult.DoesNotExist:
                        query.logger.info('Could not find Gene to Gene result for query.')
                        continue
                    except Gene.DoesNotExist:
                        query.logger.info(f'Gene with curie {q_subject.ids[0]} or {q_object.ids[0]} does not exist in the database.')
                        continue
            elif q_object.categories[0] == BIOLINK_DISEASE_ENTITY:
                for predicate in predicates:
                    if not predicate:
                        continue
                    try:
                        qs.append(
                                DiseaseToFillGeneResult.objects.get(
                                    query_disease=Disease.objects.get(curie=q_object.ids[0]),
                                    fill_gene=Gene.objects.get(curie=q_subject.ids[0]),
                                    predicate=predicate,
                                    )
                                )
                    except DiseaseToFillGeneResult.DoesNotExist:
                        query.logger.info('Could not find Disease to Gene result for query.')
                        continue
                    except Gene.DoesNotExist:
                        query.logger.info(f'Gene with curie {q_subject.ids[0]} does not exist in the database.')
                        continue
                    except Disease.DoesNotExist:
                        query.logger.info(f'Disease with curie {q_object.ids[0]} does not exist in the database.')
                        continue
        elif q_subject.categories[0] == BIOLINK_DISEASE_ENTITY:
            for predicate in predicates:
                if not predicate:
                    continue
                try:
                    qs.append(
                            DiseaseToFillGeneResult.objects.get(
                                query_disease=Disease.objects.get(curie=q_subject.ids[0]),
                                fill_gene=Gene.objects.get(curie=q_object.ids[0]),
                                predicate=predicate,
                                )
                            )
                except DiseaseToFillGeneResult.DoesNotExist:
                    query.logger.info('Could not find Disease to Gene result for query.')
                    continue
                except Gene.DoesNotExist:
                    query.logger.info(f'Gene with curie {q_object.ids[0]} does not exist in the database.')
                    continue
                except Disease.DoesNotExist:
                    query.logger.info(f'Disease with curie {q_subject.ids[0]} does not exist in the database.')
                    continue
        return self._format_response(qs, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates)
                
    def _format_response(self, qs, query, qedge_id, qedge, qsubject_id, q_subject, qobject_id, q_object, predicates):
        if len(qs) == 0:
            return self._return_no_result(query, 'No results found.')
        else:
            resp = query.get_copy()
        results = resp.message.results
        knowledge_graph = resp.message.knowledge_graph
        for q in qs:
            # Get knodes based on result type
            if type(q) == GeneToFillGeneResult:
                # Add knowledge graph nodes if they don't already exist
                if q.query_gene.curie not in knowledge_graph.nodes:
                    _ksubject_id = knowledge_graph.add_node(q.query_gene.curie, q.query_gene.name, BIOLINK_GENE_ENTITY.get_curie())
                if q.fill_gene.curie not in knowledge_graph.nodes:
                    _kobject_id = knowledge_graph.add_node(q.fill_gene.curie, q.fill_gene.name, BIOLINK_GENE_ENTITY.get_curie())
            elif type(q) == DiseaseToFillGeneResult:
                # Add knowledge graph nodes if they don't already exist
                if q.fill_gene.curie not in knowledge_graph.nodes:
                    _ksubject_id = knowledge_graph.add_node(q.fill_gene.curie, q.fill_gene.name, BIOLINK_GENE_ENTITY.get_curie())
                if q.query_disease.curie not in knowledge_graph.nodes:
                    _kobject_id = knowledge_graph.add_node(q.query_disease.curie, q.query_disease.name, BIOLINK_DISEASE_ENTITY.get_curie())
            # Flip the subject and object if required (q.predicate is different from passed)
            if q.predicate != qedge.predicates[0].get_curie():
                ksubject_id = _kobject_id
                kobject_id = _ksubject_id
            else:
                ksubject_id = _ksubject_id
                kobject_id = _kobject_id
            # Add kg edge
            kge_id = knowledge_graph.add_edge(
                    ksubject_id,
                    kobject_id,
                    qedge.predicates[0],
                    )
            # Add weight
            knowledge_graph.add_attribute(
                attribute_type_id = 'Log probability',
                value = q.weight,
                value_type_id = BIOLINK_HAS_CONFIDENCE_LEVEL_ENTITY.get_curie(),
                description = 'Closer log probability is to zero the more probable the relationship.',
                edge_id=kge_id,
                )
            # Add result
            result = Result(resp.trapi_version, resp.biolink_version)
            result.add_node_binding(qsubject_id, ksubject_id)
            result.add_node_binding(qobject_id, kobject_id)
            result.add_edge_binding(qedge_id, kge_id)
            results.results.append(result)
        resp = self._add_provenance_info(resp)
        return resp, []

    def _add_provenance_info(self, resp):
        for kedge_id, kedge in resp.message.knowledge_graph.edges.items():
            # Add CHP InfoRes Attribute
            kedge.add_attribute(
                    attribute_type_id=BIOLINK_PRIMARY_KNOWLEDGE_SOURCE_ENTITY.get_curie(),
                    value='infores:connections-hypothesis',
                    value_type_id=BIOLINK_INFORMATION_RESOURCE_ENTITY.get_curie(),
                    value_url='http://chp.thayer.dartmouth.edu',
                    description='The Connections Hypothesis Provider (CHP Learn Module) from NCATS Translator.',
                    attribute_source='infores:connections-hypothesis',
                    )
            # Add DisGeNet Supporting data source
            kedge.add_attribute(
                attribute_type_id = BIOLINK_SUPPORTING_DATA_SOURCE_ENTITY.get_curie(),
                value = 'infores:disgenet',
                value_type_id = BIOLINK_INFORMATION_RESOURCE_ENTITY.get_curie(),
                value_url = 'https://www.disgenet.org',
                attribute_source = "infores:connections-hypothesis",
                description = 'DisGeNET is a discovery platform containing one of the largest publicly available collections of genes and variants associated to human diseases.',
                )
            # Add TCGA Supporting Data Source Attribute
            kedge.add_attribute(
                    attribute_type_id=BIOLINK_SUPPORTING_DATA_SOURCE_ENTITY.get_curie(),
                    value='infores:tcga',
                    value_type_id=BIOLINK_INFORMATION_RESOURCE_ENTITY.get_curie(),
                    value_url='https://portal.gdc.cancer.gov/',
                    description='The Cancer Genome Atlas provided by the GDC Data Portal.',
                    attribute_source='infores:gdc',
                    )
        return resp

    def _get_meta_knowledge_graph(self) -> MetaKnowledgeGraph:
        """
        Returns the meta knowledge graph for this app
        """
        meta_kg_file = os.path.join(MODULE_PATH, 'meta_knowledge_graph.json')
        return MetaKnowledgeGraph.load(
            self.trapi_version,
            None,
            filename=meta_kg_file,
        )

    def get_meta_knowledge_graph(self) -> MetaKnowledgeGraph:
        return self.meta_knowledge_graph

    def _get_curies(self) -> CurieDatabase:
        curies_db_file = os.path.join(MODULE_PATH, 'curies_database.json')
        self.curies_db = CurieDatabase(curies_filename=curies_db_file)

    def get_curies(self) -> CurieDatabase:
        self._get_curies()
        return self.curies_db
    
    def _get_conflation_map(self) -> ConflationMap:
        # There is currently no conflation map for this app
        return ConflationMap(conflation_map={})

    def get_conflation_map(self) -> ConflationMap:
        return self.conflation_map
