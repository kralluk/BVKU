from pymongo import MongoClient

def get_mongo_client():
    return MongoClient("mongodb://localhost:27017/")

def save_network_info_to_db(client, network_info):
    db = client["cybertest_tool"]
    network_collection = db["network_info"]
    network_collection.delete_many({})  # Clear old entries
    network_data = [{"interface": iface, "ip_address": ip, "network": str(net)} for iface, ip, net in network_info]
    network_collection.insert_many(network_data)

def get_network_info():
    client = get_mongo_client()
    db = client["cybertest_tool"]
    return list(db["network_info"].find({}, {"_id": 0}))