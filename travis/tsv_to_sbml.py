import csv
import datetime
import json
import os
import sys
import uuid
from copy import deepcopy

import pyparsing
import requests
from lxml import etree
from helper_classes import ModelSystem

OUTPUT_NAME = "WormJam.xml"

DISCORD_ENDPOINT = sys.argv[1]
TRAVIS_BUILD_NUMBER = sys.argv[2]

#!/usr/bin/env python

"""SBTabReader.py - converts a csv with WormBase RNAi identifiers in the first column to a list of corresponding target genes

Requires (use pip to install):
openpyxl
"""


__author__ = "Jake Hattwell"
__copyright__ = "None"
__credits__ = ["Jake Hattwell"]
__license__ = "CCO"
__version__ = "1"
__maintainer__ = "Jake Hattwell"
__email__ = "j.hattwell@uq.edu.au"
__status__ = "Live"


######################
######################
## 
## Utility Functions
##
######################
######################

def genID():
    return str(uuid.uuid4())

######################
######################
## 
## Load tsv files
##
######################
######################


compiler = ModelSystem()
compiler.load_folder("curation","tsv")

metabolite_validation = compiler.validate_rxn_mets()

try:
    assert len(metabolite_validation) == 0, "Missing metabolites"
except:
    text = "Reaction: Missing Metabolites"
    for key,val in metabolite_validation.items():
        text += "\n"+key+": " + ", ".join(val)
    payload_json = {
        "embeds": [{
            "title": "WormJam CI Report",
            "color": 10027008,
            "description": "Missing Metabolites - Build aborted",
            "fields":[
                {
                    "name": "Build Number",
                    "value":str(TRAVIS_BUILD_NUMBER)
                },
                {
                    "name":"Notes",
                    "value":text
                }
            ],
            "thumbnail": {
                "url": "https://travis-ci.com/images/logos/Tessa-1.png"
            },
            "timestamp": str(datetime.datetime.now().isoformat())
        }]
    }
    r =requests.post(DISCORD_ENDPOINT,data=json.dumps(payload_json), headers={"Content-Type": "application/json"})
    exit(1)

active_gene_list = []
for key,val in compiler.tables.get("Reaction").data.items():
    genes = val["!GeneAssociation"].split(" ")
    genes = [i.replace("(","").replace(")","") for i in genes]
    while "and" in genes:
        genes.remove("and")
    while "or" in genes:
        genes.remove("or")
    active_gene_list.extend(genes)
active_gene_list = set(active_gene_list)
print(len(active_gene_list))

######################
######################
## 
## Build Model
##
######################
######################

output_model = open(OUTPUT_NAME,"wb")

#define xml namespaces
xmlns = "http://www.sbml.org/sbml/level3/version1/core"
fbc="http://www.sbml.org/sbml/level3/version1/fbc/version2"
groups="http://www.sbml.org/sbml/level3/version1/groups/version1"
xhtml="http://www.w3.org/1999/xhtml"
rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" 
dc="http://purl.org/dc/elements/1.1/"
vCard="http://www.w3.org/2001/vcard-rdf/3.0#"
dcterms="http://purl.org/dc/terms/"
bqbiol="http://biomodels.net/biology-qualifiers/"

NS_MAP = {
    'fbc': fbc,
    'groups':groups,
    'xhtml':xhtml,
    'rdf':rdf,
    'dc':dc,
    'vCard':vCard,
    'dcterms':dcterms,
    'bqbiol':bqbiol,
    None: xmlns}

#create sbml structure

sbml = etree.Element("sbml",metaid=genID(),attrib={"{%s}"%fbc+"required":"false","{%s}"%groups+"required":"false"},nsmap=NS_MAP)
other_attribs = {
    "level":"3",
    "version":"1",
}
for key,val in other_attribs.items():
    sbml.set(key,val)

model = etree.SubElement(sbml,"model",id="WormJamTestBuild",attrib={"{%s}"%fbc+"strict":"false"},metaid=genID(),name="WormJam Draft Model")
model_notes = etree.SubElement(model,"notes")
model_notes_desc = etree.SubElement(model_notes,"{%s}"%xhtml+"p")
model_notes_desc.text="Genome Scale Model of the organism Caenorhabditis elegans"

#
# curators
#

model_annotation = etree.SubElement(model,"annotation")
model_annotation_RDF = etree.SubElement(model_annotation,"{%s}"%rdf+"RDF")
model_annotation_RDF_description_DC_bag = etree.SubElement(etree.SubElement(etree.SubElement(model_annotation_RDF,"{%s}"%rdf+"Description",attrib={"{%s}"%rdf+"about":"#"+model.get("metaid")}),"{%s}"%dc+"creator"),"{%s}"%rdf+"Bag")

for key,val in compiler.tables.get("Curator").data.items():
    rdf_li = etree.SubElement(model_annotation_RDF_description_DC_bag,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"parseType":"Resource"})
    vCard_N = etree.SubElement(rdf_li,"{%s}"%vCard+"N",attrib={"{%s}"%rdf+"parseType":"Resource"})
    etree.SubElement(vCard_N,"{%s}"%vCard+"Family").text = val["!family-name"]
    etree.SubElement(vCard_N,"{%s}"%vCard+"Given").text = val["!given-name"]
    etree.SubElement(rdf_li,"{%s}"%vCard+"EMAIL").text = val["!email"]
    vCard_ORG = etree.SubElement(rdf_li,"{%s}"%vCard+"ORG",attrib={"{%s}"%rdf+"parseType":"Resource"})
    etree.SubElement(vCard_ORG,"{%s}"%vCard+"Orgname").text = val["!organization-name"]
#
# genes
# I should add a gene filter here probably to prevent export of EVERY gene in the model
#

identifier_lib = {
    "!Identifiers:refseq":"https://identifiers.org/refseq",
    "!Identifiers:uniprot":"https://identifiers.org/uniprot",
    "!Identifiers:ecogene":"https://identifiers.org/ecogene",
    "!Identifiers:kegg.genes":"https://identifiers.org/kegg.genes",
    "!Identifiers:ncbigi":"https://identifiers.org/ncbigi",
    "!Identifiers:ncbiprotein":"https://identifiers.org/ncbiprotein",
    "!Identifiers:ccds":"https://identifiers.org/ccds",
    "!Identifiers:hprd":"https://identifiers.org/hprd",
    "!Identifiers:asap":"https://identifiers.org/asap",
    "!Identifiers:ec-code":"https://identifiers.org/ec-code",
}
model_listOfGeneProducts = etree.SubElement(model,"{%s}"%fbc+"listOfGeneProducts")

for key,val in compiler.tables.get("Gene").data.items():
    if key in active_gene_list: #filter for only used genes
        attribs = {
            "{%s}"%fbc+"id":"G_"+key,
            "{%s}"%fbc+"label":key,
            "{%s}"%fbc+"name":val["!Locus"],
            "metaid":genID()
        }
        fbc_gene_prod = etree.SubElement(model_listOfGeneProducts,"{%s}"%fbc+"geneProduct",attrib=attribs)
        annotation = etree.SubElement(fbc_gene_prod,"annotation")
        rdf_RDF = etree.SubElement(annotation,"{%s}"%rdf+"RDF")
        rdf_desc = etree.SubElement(rdf_RDF,"{%s}"%rdf+"Description",attrib={"{%s}"%rdf+"about":"#"+attribs["metaid"]})
        rdf_bag_and_bqbio_is = etree.SubElement(etree.SubElement(etree.SubElement(rdf_desc,"{%s}"%bqbiol+"is"),"{%s}"%rdf+"Bag"),"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":"http://identifiers.org/wormbase/"+key})
        if val["!GO_process"] != "":
            rdf_bqbiol_occurs_in_bag = etree.SubElement(etree.SubElement(rdf_desc,"{%s}"%bqbiol+"occursIn"),"{%s}"%rdf+"Bag")
            for i in val["!GO_process"].split(";"):
                etree.SubElement(rdf_bqbiol_occurs_in_bag,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":"http://identifiers.org/go/"+i})

        if any([val[i] for i in identifier_lib if val[i] != ""]):
            for i in identifier_lib:
                if val[i]!="":
                    etree.SubElement(rdf_bqbiol_occurs_in_bag,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":identifier_lib[i]+":"+val[i]})
#
# Pathways
#
group_tree = etree.SubElement(model,"{%s}"%groups+"listOfGroups")

for key,val in compiler.tables.get("Pathway").data.items():
    attribs = {
        "{%s}"%groups+"id":"P_"+key.replace(" ","_"),
        "{%s}"%groups+"kind":"partonomy",
        "{%s}"%groups+"name":key,
        "metaid":genID()
    }
    groups_group = etree.SubElement(group_tree,"{%s}"%groups+"group",attrib=attribs)
    descriptors = [val["!Identifiers:GO_process"],val["!Identifiers:kegg:pathway"],val["!Identifiers:BioCyc"],val["!Identifiers:pw"]]
    links = ["http://identifiers.org/go/","http://identifiers.org/kegg:","http://identifiers.org/biocyc/","http://identifiers.org/pw/"]
    merge = zip(links,descriptors)
    new = []
    for i in merge:
        if i[1] != "":
            ids = i[1].replace(" ","").split(";")
            ids = [i[0] + j for j in ids]
            new += ids
    if new != []:
        annotation = etree.SubElement(groups_group,"annotation")
        rdf_desc = etree.SubElement(etree.SubElement(annotation,"{%s}"%rdf+"RDF"),"{%s}"%rdf+"Description",attrib={"{%s}"%rdf+"about":"#"+attribs["metaid"]})
        is_bag = etree.SubElement(etree.SubElement(rdf_desc,"{%s}"%bqbiol+"is"),"{%s}"%rdf+"Bag")
        for i in new:
            etree.SubElement(is_bag,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":i})
    listOfMembers = [rxn for rxn,info in compiler.tables.get("Reaction").data.items() if info["!Pathway"] == key]
    group_listOfMemebers = etree.SubElement(groups_group,"{%s}"%groups+"listOfMembers")
    for i in listOfMembers:
        etree.SubElement(group_listOfMemebers,"{%s}"%groups+"member",attrib={"{%s}"%groups+"id":"GM_"+i,"{%s}"%groups+"idRef":i})

#
# Compartments
#
compartment_tree = etree.SubElement(model,"listOfCompartments")

for key,val in compiler.tables.get("Compartment").data.items():
    metaid = genID()
    compartment = etree.SubElement(compartment_tree,"compartment",attrib={"constant":"true","id":key,"metaid":metaid,"name":val["!Name"],"size":"1","spatialDimensions":"3"})
    if val["!Comment"] != "":
        etree.SubElement(etree.SubElement(compartment,"notes"),"{%s}"%xhtml+"p").text = val["!Comment"]
    if val["!Identifiers:go"] != "":
        annotation = etree.SubElement(compartment,"annotation")
        rdf_desc = etree.SubElement(etree.SubElement(annotation,"{%s}"%rdf+"RDF"),"{%s}"%rdf+"Description",attrib={"{%s}"%rdf+"about":"#"+metaid})
        is_bag = etree.SubElement(etree.SubElement(rdf_desc,"{%s}"%bqbiol+"is"),"{%s}"%rdf+"Bag")
        etree.SubElement(is_bag,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":"http://identifiers.org/go/"+val["!Identifiers:go"]})

#
# Species
#

identifier_lib = {
    "!Identifiers:bigg.metabolite":"https://identifiers.org/bigg.metabolite",
    "!Identifiers:biocyc":"https://identifiers.org/biocyc",
    "!Identifiers:chebi":"https://identifiers.org/chebi",
    "!Identifiers:doi":"https://identifiers.org/doi",
    "!Identifiers:eco":"https://identifiers.org/eco",
    "!Identifiers:hmbd":"https://identifiers.org/hmdb",
    "!Identifiers:inchi":"https://identifiers.org/inchi",
    "!Identifiers:inchikey":"https://identifiers.org/inchikey",
    "!Identifiers:kegg.compound":"https://identifiers.org/kegg.compound",
    "!Identifiers:metanetx.compound":"https://identifiers.org/metanetx.compound",
    "!Identifiers:pubmed.compound":"https://identifiers.org/pubmed.compound",
    "!Identifiers:reactome":"https://identifiers.org/reactome",
    "!Identifiers:seed.compound":"https://identifiers.org/seed.compound",

}
species_tree = etree.SubElement(model,"listOfSpecies")

for key,val in compiler.tables.get("Compound").data.items():
    attribs = {
        "boundaryCondition":"false",
        "compartment":val["!Location"],
        "constant":"false",
        "{%s}"%fbc+"charge":val["!Charge"],
        "{%s}"%fbc+"chemicalFormula":val["!Formula"],
        "hasOnlySubstanceUnits":"false",
        "id":key,
        "initialConcentration":"0",
        "name":"!Name"
    }
    if attribs["{%s}"%fbc+"charge"] == "":
        attribs["{%s}"%fbc+"charge"] = "0"
    metaid = genID()
    metabolite = etree.SubElement(species_tree,"species",metaid=metaid,attrib=attribs)
    notes_body = etree.SubElement(etree.SubElement(metabolite,"notes"),"{%s}"%xhtml+"body")
    for i in [key for key in list(val.keys()) if "!Identifier" not in key]:
        if val[i]!="":
            if key=="!Charge" and val[i]=="":
                val[i] == "0"
            etree.SubElement(notes_body,"{%s}"%xhtml+"p").text=i.replace("!","").replace("Notes:","").upper() + ": " + val[i]
    if any([val[i] for i in identifier_lib if val[i] != ""]):
        annotation_tree = etree.SubElement(etree.SubElement(etree.SubElement(metabolite,"annotation"),"{%s}"%rdf+"RDF"),"{%s}"%rdf+"Description",attrib={"{%s}"%rdf+"about":"#"+metaid})
        next_level = etree.SubElement(etree.SubElement(annotation_tree,"{%s}"%bqbiol+"is"),"{%s}"%rdf+"Bag")
        for i in identifier_lib:
            if val[i]!="":
                etree.SubElement(next_level,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":identifier_lib[i]+":"+val[i]})

#
# Parameters
#

parameter_tree = etree.SubElement(model,"listOfParameters")
etree.SubElement(parameter_tree,"parameter",attrib={"constant":"true","id":"LOWER_BOUND","value":"-1000"})
etree.SubElement(parameter_tree,"parameter",attrib={"constant":"true","id":"ZERO_BOUND","value":"0"})
etree.SubElement(parameter_tree,"parameter",attrib={"constant":"true","id":"UPPER_BOUND","value":"1000"})

#
# Reactions
#

identifier_lib = {
    "!Identifiers:kegg.reaction":"https://identifiers.org/kegg.reaction",
    "!Identifiers:rhea":"https://identifiers.org/rhea",
    "!Identifiers:rheadb_fuzzy":"https://identifiers.org/rheadb_fuzzy",
    "!Identifiers:pubmed":"https://identifiers.org/pubmed",
    "!Identifiers:doi":"https://identifiers.org/doi",
    "!Identifiers:eco":"https://identifiers.org/eco",
    "!Identifiers:metanetx.reaction":"https://identifiers.org/metanetx.reaction",
    "!Identifiers:bigg.reaction":"https://identifiers.org/bigg.reaction",
    "!Identifiers:reactome":"https://identifiers.org/reactome",
    "!Identifiers:ec-code":"https://identifiers.org/ec-code",
    "!Identifiers:brenda":"https://identifiers.org/brenda",
    "!Identifiers:biocyc":"https://identifiers.org/biocyc",

}

# GPR helper functions

def genHead(parent,booltype):
    #function to generate the and/or xml field
    if booltype == "or":
        branch = etree.SubElement(parent,"{%s}"%fbc+"or",attrib={"sboTerm":"SBO:0000174"})
    else:
        branch = etree.SubElement(parent,"{%s}"%fbc+"and",attrib={"sboTerm":"SBO:0000173"})
    return branch

def parse(parent,my_list):
    if my_list == []: #handle empty gene associations
        result =  None
        return None
    while type(my_list) == list and len(my_list) == 1: #whilst there is a single entry in the list, unpack it
        my_list = my_list[0]
    if type(my_list) == str: #Handling single genes
        result = ("single",my_list)
    else:
        if any(type(i) == list for i in my_list): #If there are lists (nested Gene associations)
            for index,item in enumerate(my_list):
                #unpack
                if type(item) == list and len(item) == 1:
                    my_list[index] = item[0]
            types = None
            op_type = my_list[1]
            types = op_type
            while op_type in my_list:
                my_list.remove(op_type)
            for index,item in enumerate(my_list): #start diving down levels
                if type(item)==list:
                    op_type=item[1]
                    while op_type in item:
                        item.remove(op_type)
                    for index2,item2 in enumerate(item):
                        if type(item2)==list:
                            op_type2=item2[1]
                            while op_type2 in item2:
                                item2.remove(op_type2)
                            item[index2]=(op_type2,item2)
                    my_list[index] = (op_type,item)
            result = (types,my_list)
        else:
            op_type = my_list[1]
            while op_type in my_list:
                my_list.remove(op_type)
            result = (op_type,my_list)
    #create the xml tree
    gpr = etree.SubElement(parent,"{%s}"%fbc+"GeneProductAssociation")
    #simple case
    if result[0] == 'single':
        etree.SubElement(gpr,"{%s}"%fbc+"geneProductRef",attrib={"{%s}"%fbc+"geneProduct":"G_"+result[1]})
    #No nesting bool
    elif all(type(i) != tuple for i in result[1]):
        branch = genHead(gpr,result[0])
        for i in result[1]:
            etree.SubElement(branch,"{%s}"%fbc+"geneProductRef",attrib={"{%s}"%fbc+"geneProduct":"G_"+i})
    #complex case
    else:
        branch = genHead(gpr,result[0])
        for i in result[1]: #level diving
            if type(i) == tuple:
                inner = genHead(branch,i[0])
                for j in i[1]:
                    if type(j) == tuple:
                        inner2 = genHead(branch,j[0])
                        for k in j[1]:
                            etree.SubElement(inner2,"{%s}"%fbc+"geneProductRef",attrib={"{%s}"%fbc+"geneProduct":"G_"+k})
                    else:
                        etree.SubElement(inner,"{%s}"%fbc+"geneProductRef",attrib={"{%s}"%fbc+"geneProduct":"G_"+j})

            else:
                etree.SubElement(branch,"{%s}"%fbc+"geneProductRef",attrib={"{%s}"%fbc+"geneProduct":"G_"+i[1]})
    return gpr

    ##reaction string handling
def react_proc(rxn):
    r,p = rxn.split("<=>")
    def quick(frag):
        frag = frag.split("+")
        frag = [i.rstrip().lstrip() for i in frag]
        frag = [i.split(" ") for i in frag]
        return frag
    r = quick(r)
    p = quick(p)
    #packaging
    reactants = {(i[1] if len(i) == 2 else i[0]):(i[0] if len(i)==2 else "1") for i in r}
    products = {(i[1] if len(i) == 2 else i[0]):(i[0] if len(i)==2 else "1") for i in p}
    for d in [reactants,products]:
        for key,val in d.items():
            try:
                d[key] = str(float(val))
            except:
                pass

    return (reactants,products)   




#### Actually doing the reactions
 
reaction_tree = etree.SubElement(model,"listOfReactions")

# IDs !Identifiers:kegg.reaction	!Identifiers:rheadb_exact	!Identifiers:rheadb_fuzzy	!Identifiers:pubmed	!Identifiers:doi	!Identifiers:eco
# Other !Reaction	!Name	!ReactionFormula	!IsReversible	!GeneAssociation	!Pathway	!SuperPathway	!Comment	!Curator	!Notes:EC NUMBER	!Notes:AUTHORS
ignore = ["!Identifiers:kegg.reaction","!Identifiers:rheadb_exact","!Identifiers:rheadb_fuzzy","!Identifiers:pubmed","!Identifiers:doi","!Identifiers:eco",
"!Authors","!ReactionFormula","!SuperPathway","!Name","!IsReversible"]

for key,val in compiler.tables.get("Reaction").data.items():
    metaid = genID()
    attribs = {
        "fast":"false",
        "reversible":val["!IsReversible"].lower(),
        "metaid":metaid,
        "id":key,
        "name":val["!Name"],
        "{%s}"%fbc+"upperFluxBound":"UPPER_BOUND"
    }
    if attribs["reversible"] == "true":
        attribs["{%s}"%fbc+"lowerFluxBound"] = "LOWER_BOUND"
    else:
        attribs["{%s}"%fbc+"lowerFluxBound"] = "ZERO_BOUND"
    reaction_field = etree.SubElement(reaction_tree,"reaction",attrib=attribs)
    notes_body = etree.SubElement(etree.SubElement(reaction_field,"notes"),"{%s}"%xhtml+"body")
    for i in [key2 for key2 in list(val.keys()) if key2 not in ignore]:
        if val[i]!="":
            etree.SubElement(notes_body,"{%s}"%xhtml+"p").text=i.replace("!","").replace("Notes:","").replace("Pathway","Subsystem").upper() + ": " + val[i]

    if any([val[i] for i in identifier_lib if val[i] != ""]):
        annotation_tree = etree.SubElement(etree.SubElement(etree.SubElement(reaction_field,"annotation"),"{%s}"%rdf+"RDF"),"{%s}"%rdf+"Description",attrib={"{%s}"%rdf+"about":"#"+metaid})
        next_level = etree.SubElement(etree.SubElement(annotation_tree,"{%s}"%bqbiol+"is"),"{%s}"%rdf+"Bag")

        for i in list(identifier_lib.keys()):
            if val[i]!="":
                for j in val[i].replace(" ","").split(";"):
                    etree.SubElement(next_level,"{%s}"%rdf+"li",attrib={"{%s}"%rdf+"resource":identifier_lib[i]+":"+j})

    
    genes = "("+val["!GeneAssociation"]+")"
    parens = pyparsing.nestedExpr( '(', ')', content=pyparsing.Word(pyparsing.alphanums) | ' or ' | " and " )
    r = parens.parseString(genes)[0].asList()
    er = deepcopy(r)
    try:
        parse(reaction_field,r)
    except Exception as e:
        print(key,er)
        print(e)
    
    reactants,products = react_proc(val["!ReactionFormula"])
    if "" not in reactants:
        listOfReactants = etree.SubElement(reaction_field,"listOfReactants")
        for key2,val2 in reactants.items():
            etree.SubElement(listOfReactants,"speciesReference",attrib={"constant":"true","species":key2,"stoichiometry":val2})
    if "" not in products:       
        listOfProducts = etree.SubElement(reaction_field,"listOfProducts")
        for key2,val2 in products.items():
            etree.SubElement(listOfProducts,"speciesReference",attrib={"constant":"true","species":key2,"stoichiometry":val2})



######################
######################
## 
## Output
##
######################
######################

output_model.write(etree.tostring(sbml,encoding="UTF-8",standalone=False,xml_declaration=True,pretty_print=True))
output_model.close()





#######################################################################################################################
## pretty print fragment
# with open(OUTPUT_NAME,"rb") as f:
#     parser = etree.XMLParser(remove_blank_text=True)
#     tree = etree.parse(f, parser)
#     print(etree.tostring(root,encoding="UTF-8",standalone=False,xml_declaration=True,pretty_print=True).decode())
