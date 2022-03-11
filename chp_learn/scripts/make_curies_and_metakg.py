from collections import defaultdict

from trapi_model.meta_knowledge_graph import MetaKnowledgeGraph
from trapi_model.biolink.constants import *
from chp_utils.curie_database import CurieDatabase

from ..models import Gene, Disease, GeneToFillGeneResult, DiseaseToFillGeneResult

# Instantiate metakg object with appropriate versioning
metakg = MetaKnowledgeGraph('1.2', None)

## Add Nodes.
# Add preferred gene prefixes
genes = ['ENSEMBL','NCBIGene','HGNC']
metakg.add_node(BIOLINK_GENE_ENTITY, genes)

# Add preferred disease prefixes
diseases = ['UMLS','DOID','MONDO','NCIT']
metakg.add_node(BIOLINK_DISEASE_ENTITY, diseases)

## Add Edges
# Add most specific gene to gene edges
metakg.add_edge(
        BIOLINK_GENE_ENTITY,
        BIOLINK_GENE_ENTITY,
        BIOLINK_INCREASES_EXPRESSION_OF_ENTITY,
        )
metakg.add_edge(
        BIOLINK_GENE_ENTITY,
        BIOLINK_GENE_ENTITY,
        BIOLINK_DECREASES_EXPRESSION_OF_ENTITY,
        )

# Add most specific disease to gene edges
metakg.add_edge(
        BIOLINK_DISEASE_ENTITY,
        BIOLINK_GENE_ENTITY,
        BIOLINK_INCREASES_EXPRESSION_OF_ENTITY,
        )
metakg.add_edge(
        BIOLINK_DISEASE_ENTITY,
        BIOLINK_GENE_ENTITY,
        BIOLINK_DECREASES_EXPRESSION_OF_ENTITY,
        )

## Expand metakg to support inverses
metakg = metakg.expand_with_inverses()

## Save file
metakg.json('meta_knowledge_graph.json')

## Test load
meta_kg = MetaKnowledgeGraph.load('1.2', None, filename='meta_knowledge_graph.json')

print('Saved meta_knowledge_graph to {}'.format(os.path.join(os.getcwd(), 'meta_knowledge_graph.json')))

# Make curies datafile
curies = defaultdict(dict)
for g in Gene.objects.all():
    curies[BIOLINK_GENE_ENTITY.get_curie()][g.curie] = [g.name]
for d in Disease.objects.all():
    curies[BIOLINK_DISEASE_ENTITY.get_curie()][d.curie] = [d.name]

# Build curies database
curie_database = CurieDatabase(curies=curies)

# Save file
curie_database.json('curies_database.json')

# Test load
curies_database = CurieDatabase(curies_filename='curies_database.json')

print('Saved curies database to {}'.format(os.path.join(os.getcwd(), 'curies_database.json')))
