import pymongo
import config

client = pymongo.MongoClient(config.mongo_connection)

articles = client["forum"]["articles"]

# result = articles.find().limit(5)

# for x in result:
    # print(x)

# client.close()
