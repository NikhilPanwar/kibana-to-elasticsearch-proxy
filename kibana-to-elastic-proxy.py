import argparse
import requests
import base64
import sys, json
from rich.pretty import pprint
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

headers = {}

def initialize_kibana_settings(url, username, password):
    global headers
    if username and password:
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers['Authorization'] = f"Basic {encoded_credentials}"
    headers['kbn-xsrf'] = 'kibana'

def fetch_kibana_indices(url, json_format=False):
    if json_format:
        response = requests.post(url + '/api/console/proxy?path=/_cat/indices?format=json&method=GET', headers=headers, verify=False)
        pprint(response.json())
    else:
        response = requests.post(url + '/api/console/proxy?path=/_cat/indices&method=GET', headers=headers, verify=False)
        print(response.text)

def get_cluster_stats(url):
    response = requests.post(url + '/api/console/proxy?path=/_cluster/stats?format=json&method=GET', headers=headers, verify=False)
    pprint(response.json())

def wildcard_term_search(url, search_term, indice='*'):
    if indice == '*':
        response = requests.post(url + f'/api/console/proxy?path=/_search?q=*{search_term}*&method=GET', headers=headers, verify=False, timeout=100)
    else:
        print(f"Searching in indice: {indice}")
        response = requests.post(url + f'/api/console/proxy?path=/{indice}/_search?q=*{search_term}*&method=GET', headers=headers, verify=False, timeout=100)
    pprint(response.json())

# its broken right now
def raw_query_search(url, query, indice='*'):
    if indice == '*':
        response = requests.post(url + '/api/console/proxy?path=/_search&method=POST', headers=headers, json=query, verify=False, timeout=100)
    else:
        print(f"Searching in indice: {indice}")
        response = requests.post(url + '/api/console/proxy?path=/{indice}/_search&method=POST', headers=headers, json=query, verify=False, timeout=100)
    pprint(response.json())

def dump_index(url, index):
    print(f"Dumping index: {index}")
    with open(f"{index}.json", "w", encoding='utf-8') as output_file:
        response = requests.post(url + f'/api/console/proxy?path=/{index}/_search?scroll=1m&method=GET', headers=headers, json={"size": 1000}, verify=False)
        for record in response.json()['hits']['hits']:
            output_file.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"Fetched {len(response.json()["hits"]["hits"])} records")
        scroll_id = response.json()['_scroll_id']
        while len(response.json()['hits']['hits']) > 0:
            response = requests.post(url + '/api/console/proxy?path=/_search/scroll&method=GET', headers=headers, json={"scroll": "1m", "scroll_id": scroll_id}, verify=False)
            for record in response.json()['hits']['hits']:
                output_file.write(json.dumps(record, ensure_ascii=False) + '\n')
            print(f"Fetched {len(response.json()["hits"]["hits"])} records")
            scroll_id = response.json()['_scroll_id']

def main():
    parser = argparse.ArgumentParser(description="Kibana to Elasticsearch proxy")
    parser.add_argument('-s', '--server_url', required=True, help="Server URL (including http/https)")
    parser.add_argument('-u', '--username', help="Username for Kibana, do not provide if no auth is required")
    parser.add_argument('-p', '--password', help="Password for Kibana, do not provide if no auth is required")
    parser.add_argument('--get-indices', action='store_true', help="Fetch indices from Kibana")
    parser.add_argument('--get-stats', action='store_true', help="Fetch cluster stats from Kibana")
    parser.add_argument('--json', action='store_true', help="Output in JSON format")
    # use --search and take term as input
    parser.add_argument('--search', help="Wildcard search term")
    parser.add_argument('--raw-query', help="Raw json query to search")
    parser.add_argument('--indice', help="Indice to search in")
    parser.add_argument('--dump-index', action='store_true', help="Dump entire index")

    args = parser.parse_args()
    initialize_kibana_settings(args.server_url, args.username, args.password)

    if args.get_indices:
        fetch_kibana_indices(args.server_url, args.json)
    elif args.get_stats:
        get_cluster_stats(args.server_url)
    elif args.search:
        if args.indice:
            wildcard_term_search(args.server_url, args.search, args.indice)
        else:
            wildcard_term_search(args.server_url, args.search)
    elif args.raw_query:
        pprint(args.raw_query)
        if args.indice:
            raw_query_search(args.server_url, args.raw_query, args.indice)
        else:
            raw_query_search(args.server_url, args.raw_query)
    elif args.dump_index:
        if not args.indice:
            print("Please provide indice to dump")
            sys.exit(1)
        dump_index(args.server_url, args.indice)

if __name__ == "__main__":
    main()
