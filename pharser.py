import json, os, sys, getopt
import numpy as np
from collections import defaultdict as dd
import pprint
import csv
from cdfer import makeGraphs as msg
from urllib.parse import urlparse
from datetime import datetime

to_print = False

def csv_print(string):
    if to_print:
        print(string)

def parse_perf_file(perf_file):
    perf_info_data = {}
    with open(perf_file, 'r') as f:
        x = json.loads(f.read())
        try:
            perf_data = x['result']['metrics']
            for metric in perf_data:
                perf_info_data[metric['name']] = metric['value']
        except Exception as e:
            print(e)
    return perf_info_data

def read_har_file(har_file):
    reqs = dd(list)
    with open(har_file, 'r') as f:
        har = json.loads(f.read())
        for entry in har['log']['entries']:
            entry['onContentLoad'] = har['log']['pages'][0]['pageTimings']['onContentLoad']
            if 'mss' in har_file:
                entry['network'] = 'mss'
            elif 'reg_3G' in har_file:
                entry['network'] = 'reg_3G'
            elif 'no_change' in har_file:
                entry['network'] = 'no_change'
            entry['onLoad'] = har['log']['pages'][0]['pageTimings']['onLoad']
            reqs[entry['serverIPAddress']].append(entry)            
    return reqs

def print_har_file(har):
    urls = []
    domains = []
    urls_per_domain = dd(int)
    times = []
    byte_spread = []
    all_byte_spread = []
    all_times = []
    onload = 0
    e = False
    for server in har:
        for entry in har[server]:
            e = True
            urls.append(entry['request']['url'])
            parsed_uri = urlparse(entry['request']['url'])
            domain = '{uri.netloc}'.format(uri=parsed_uri)
            t = float(datetime.strptime(entry['startedDateTime'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp() * 1000)
            request_size = (0 if entry['request']['bodySize'] == -1 else entry['request']['bodySize']) + (0 if entry['request']['headersSize'] == -1 else entry['request']['headersSize'])
            response_size = entry['response']['content']['size']
            if len(domains) > 0:
                # if domain not in domains:
                if domain in domains:
                    times.append(t)
                    # byte_spread.append({'size': request_size + response_size, 'start_time': t, 'duration': entry['time']})
                    # byte_spread.append({'size': request_size + response_size, 'start_time': t, 'duration': entry['time'], 'url': entry['request']['url'], 'ip': server, 'network': entry['network']})
            else:
                domains.append(domain)
            all_times.append(t)
            byte_spread.append({'size': request_size + response_size, 'start_time': t, 'duration': entry['time'], 'url': entry['request']['url'], 'ip': server, 'network': entry['network'], 'connection_id': entry['connection'], 'proto': entry['request']['httpVersion'], 'domain': domain})
            urls_per_domain[domain] += 1
            # if entry['request']['httpVersion'] == 'h2':
            #     print(entry['request']['url'], domain)
            if request_size > 0:
                csv_print("%s, %s, %s, %s, %.4f, %.4f, %.4f, %.4f, %s" %(entry['startedDateTime'], entry['serverIPAddress'], entry['connection'], entry['request']['httpVersion'], entry['time'], request_size, response_size, response_size/request_size, entry['request']['url']))
            else:
                csv_print("%s, %s, %s, %s, %.4f, %.4f, %.4f, %.4f, %s" %(entry['startedDateTime'], entry['serverIPAddress'], entry['connection'], entry['request']['httpVersion'], entry['time'], request_size, response_size, 0, entry['request']['url']))
    if len(all_times) == 0:
        first_time = 0
    else:
        first_time = min(all_times)
    # time_spread = sorted([t - first_time for t in times if (t - first_time) < entry['onContentLoad']])
    time_spread = sorted([t - first_time for t in times if (t - first_time) < entry['onLoad']])
    # time_spread = sorted(times)
    if len(urls) == 0:
        ratio = 0.0
    else:
        ratio = (len(domains)/len(urls))* 100.0
    if e:
        ol = entry['onLoad']
    else:
        ol = 0.0
    return len(urls), len(urls_per_domain), ratio, time_spread, ol,  urls_per_domain, byte_spread

def parse_results_dir(results_dir, test_network):
    h1_data = {}
    h2_data = {}
    for filename in os.listdir(results_dir):
        if os.path.isdir(results_dir + "/" + filename):
            num_urls = dd(list)
            num_domains = dd(list)
            num_ratios = dd(list)
            num_times = dd(list)
            num_bytes = dd(list)
            num_load_times = dd(list)
            num_per_domains = dd(list) 
            num_perf_info = dd(list)
            for fname in os.listdir(results_dir + "/" + filename):
                u = fname.split(".")[1]
                if u not in h1_data:
                    h1_data[u] ={} 
                    h2_data[u] = {}
                network = fname.split("-")[-2]
                if network != test_network: 
                    # print("%s, %s"%(network, test_network))
                    continue
                if fname.endswith(".har"):
                    har = read_har_file(results_dir + "/" + filename + "/" + fname)
                    urls, domains, ratio, times, on_content_load, urls_per_domain, byte_spread = print_har_file(har)
                    num_urls[u].append(urls)
                    num_domains[u].append(domains)
                    num_ratios[u].append(ratio)
                    num_times[u] = num_times[u] + times
                    num_bytes[u] = num_bytes[u] + byte_spread
                    num_load_times[u].append((on_content_load, len(times)))
                    num_per_domains[u].append(urls_per_domain) 
                elif fname.endswith('.perf'):
                    num_perf_info[u].append(parse_perf_file(results_dir + "/" + filename + "/" + fname))

            if 'h1' in filename:
                for url in num_urls:
                    h1_data[url]["num_urls"] = num_urls[url]
                    h1_data[url]["num_domains"] = num_domains[url]
                    h1_data[url]["num_ratios"] = num_ratios[url]
                    h1_data[url]["req_times"] = num_times[url]
                    h1_data[url]["req_bytes"] = num_bytes[url]
                    h1_data[url]["content_load_x_num_reqs"] = num_load_times[url]
                    h1_data[url]["num_per_domain"] = num_per_domains[url]
                    h1_data[url]["perf_info"] = num_perf_info[url]
            elif 'h2' in filename:
                for url in num_urls:
                    h2_data[url]["num_urls"] = num_urls[url]
                    h2_data[url]["num_domains"] = num_domains[url]
                    h2_data[url]["num_ratios"] = num_ratios[url]
                    h2_data[url]["req_times"] = num_times[url]
                    h2_data[url]["req_bytes"] = num_bytes[url]
                    h2_data[url]["content_load_x_num_reqs"] = num_load_times[url]
                    h2_data[url]["num_per_domain"] = num_per_domains[url]
                    h2_data[url]["perf_info"] = num_perf_info[url]
    return h1_data, h2_data

