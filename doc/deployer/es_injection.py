from bson import json_util
import os
import sys
import json
from elasticsearch import Elasticsearch
from elasticsearch_dsl import *
from gnowsys_ndf.ndf.models import *

#from gnowsys_ndf.settings import GSTUDIO_SITE_NAME
#from gnowsys_ndf.local_settings import GSTUDIO_DOCUMENT_MAPPING
from gnowsys_ndf.settings import *

try:
    from bson import ObjectId
except ImportError:  # old pymongo
    from pymongo.objectid import ObjectId
##### use the below commented lines if you are working with Python 2.x   #####
# reload(sys)
# sys.setdefaultencoding('UTF8')

es = Elasticsearch(GSTUDIO_ELASTIC_SEARCH_PROTOCOL+"://"+GSTUDIO_ELASTIC_SEARCH_SUPERUSER+":"+GSTUDIO_ELASTIC_SEARCH_SUPERUSER_PASSWORD+"@"+GSTUDIO_ELASTIC_SEARCH_ALIAS+":"+GSTUDIO_ELASTIC_SEARCH_PORT,timeout=100, retry_on_timeout=True)

#author_index = "author_" + GSTUDIO_SITE_NAME.lower()
#index = GSTUDIO_SITE_NAME.lower()
#gsystemtype_index = "node_type_" + GSTUDIO_SITE_NAME.lower()
with open("/home/docker/code/clixoer/gnowsys-ndf/gnowsys_ndf/gstudio_configs/req_body.json") as req_body:
    request_body = json.load(req_body)
    print "request json",request_body
with open("/home/docker/code/clixoer/gnowsys-ndf/gnowsys_ndf/gstudio_configs/triples.json") as triples:
    triples_body = json.load(triples)
    print "triples json",triples_body


page_id = 0


def index_docs(all_docs,index,doc_type):
    k = 0
    all_docs_count = all_docs.count()
    for docs in all_docs:
        print "[ %s/%s ] : %s " % (k, all_docs_count, docs._id)


        doc = json.dumps(docs, cls=NodeJSONEncoder)  # convert mongoDB object to a JSON string
        # doc = json.loads(doc,object_hook=json_util.object_hook) ->get back mongoDB object from JSON string

        document = json.loads(doc)  # convert JSON string to a python dictionary
        # doc = json.dumps(document) #convert python dictionary to JSON string
        if document.get("_id") and document.get("_type"):
            document["id"] = document.pop("_id")
            document["type"] = document.pop("_type")

            #for docs in doc_type:
            print document["type"],doc_type[0]
            #print document
            # doc_type = document["type"].lower()
            es.index(index=index, doc_type=doc_type[0].lower(), id=document["id"], body=document)

        k += 1

    #file_name.close()



def get_document_type(document):

	if document["type"]=="GSystem":
		#for ids in document['member_of']:  #document is a member of the Page GSystemType
			#if(ids == page_id):
				#return "Page"
		if('if_file' in document.keys()):
			if(document["if_file"]["mime_type"] is not None):
				data = document["if_file"]["mime_type"].split("/")
				doc_type = data[0]
			else:
				doc_type = "notmedia"
		else:
			doc_type = "notmedia"

	else:
		doc_type = "dontcare"
	return doc_type



def main():
    #f = open("/data/nodes.txt", "w")
    #os.chmod("/data/nodes.txt", 0o777)

    nodes = {}
    triples = {}
    benchmarks = {}
    filehives = {}
    buddys = {}
    counters = {}

    #all_docs = [ triples, buddys, benchmarks, nodes, counters]

    print("Starting the indexing process...")
    print(GSTUDIO_SITE_NAME)
    for index, doc_type in GSTUDIO_ELASTIC_SEARCH_INDEX.items():
        temp = []
        mongodb_nd_ids = []
        if GSTUDIO_SITE_NAME == "clix":
            index_lower = index.lower()
        else:
            index_lower = GSTUDIO_SITE_NAME.lower()+"_"+index.lower()
        print index_lower
        if (not es.indices.exists(index_lower)):
            if (index_lower.find("triples") != -1):
                res = es.indices.create(index=index_lower, body=triples_body)
            else:
                print "inside not exists"
                res = es.indices.create(index=index_lower, body=request_body)

        if (es.indices.exists(index_lower)):

            res = es.search(index=index_lower, body={"query": {"match_all": {}}, "_source": ["id"]}, scroll="1m", size="10")
            print "search response:",res
            scrollid = res['_scroll_id']

            while len(res['hits']['hits']) > 0:

                for hit in res['hits']['hits']:
                    # print(hit["_source"]["id"])
                    # f.write(hit["_source"]["id"] + '\n')
                    # res = es.search(index="nodes", body={"scroll_id": '"' + scrollid + '"'}, search_type="scan",
                    #           scroll="1m", size="10")
                    temp.append(ObjectId(hit["_source"]["id"]))

                res = es.scroll(scrollid, scroll="1m")
            print "temp result:",temp
            if index_lower == 'nodes':
                nodeids = node_collection.find({},{'_id':1})
                for each in nodeids:
                    mongodb_nd_ids.append(str(each._id))
            elif index_lower == 'triples':
                nodeids = triple_collection.find({},{'_id':1})
                for each in nodeids:
                    mongodb_nd_ids.append(str(each._id))
            else:
                nodeids = filehive_collection.find({},{'_id':1})
                for each in nodeids:
                    mongodb_nd_ids.append(str(each._id))
            
            print len(mongodb_nd_ids),nodeids.count(),len(temp)
            if(nodeids.count() >= len(temp)):
                if(index_lower.find("nodes") !=-1):
                    nodes = node_collection.find({ '_id': {'$nin': temp} }).batch_size(5)
                    print "nodes:",nodes.count()
                    if(nodes.count() == 0):
                        print("All "+ index_lower +" documents has injected to elasticsearch")
                        continue
                    else:
                        index_docs(nodes, index_lower, doc_type)

                elif (index_lower.find("triples") !=-1):
                    triples = triple_collection.find({ '_id': {'$nin': temp} }).batch_size(5)
                    if (triples.count() == 0):
                        print("All " + index_lower + " documents has injected to elasticsearch")
                        continue
                    else:
                        # f = open("/data/triples.txt", "w")
                        # os.chmod("/data/triples.txt", 0o777)
                        index_docs(triples, index_lower, doc_type)

                elif (index_lower.find("benchmarks") !=-1 ):
                    benchmarks = benchmark_collection.find({ '_id': {'$nin': temp} }).batch_size(5)
                    if (benchmarks.count() == 0):
                        print("All " + index_lower + " documents has injected to elasticsearch")
                        continue
                    else:
                        index_docs(benchmarks, index_lower, doc_type)

                elif (index_lower.find("filehives")!=-1):
                    filehives = filehive_collection.find({ '_id': {'$nin': temp} }).batch_size(5)
                    print filehives.count()
                    if (filehives.count() == 0):
                        print("All " + index_lower + " documents has injected to elasticsearch")
                        continue
                    else:
                        index_docs(filehives, index_lower, doc_type)
                    
                elif (index_lower.find("buddies")!=-1):
                    buddys = buddy_collection.find({ '_id': {'$nin': temp} }).batch_size(5)
                    if (buddys.count() == 0):
                        print("All " + index_lower + " documents has injected to elasticsearch")
                        continue
                    else:
                        index_docs(buddys, index_lower, doc_type)

                elif (index_lower.find("counters")!=-1):
                    counters = counter_collection.find({ '_id': {'$nin': temp} }).batch_size(5)
                    if (counters.count() == 0):
                        print("All " + index_lower + " documents has injected to elasticsearch")
                        continue
                    else:
                        index_docs(counters, index_lower, doc_type)
            else:
                print "ES has more nodes than mongodb",index_lower,doc_type,len(mongodb_nd_ids)
                #mongodb_nd_ids = [ObjectId(each) for each in mongodb_nd_ids]
                q = Q('bool',must_not=[Q('terms',id = mongodb_nd_ids)])
                s = Search(using=es,index=index_lower, doc_type= doc_type[0].lower()).query(q)
                print "documents to b deleted:",s.count()
                s1 = s.delete()
            #print(res['_scroll_id'])
            #print(res['hits']['total'])

                #f = open("/data/nodes.txt", "w+")
                #os.chmod("/data/nodes.txt", 0o777)

                   # f = open("/data/nodes.txt", "w+")
                    # os.chmod("/data/nodes.txt", 0o777)

                    # es.scroll(scrollid, scroll="1m")

                    #print(temp)

                    # DELETING existing/old indexes

                    # for index in GSTUDIO_ELASTIC_SEARCH_INDEX.keys():
                    # if (es.indices.exists(index_lower)):
                    #   print("Deleting the existing index: " + index.lower() + " for reindexing")
                    #   res = es.indices.delete(index=index.lower())
                    #   print("The delete response is %s " % res)


                    # --- END of DELETING existing/old indexes


   
main()
