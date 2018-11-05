#!/usr/bin/python
# -*- coding: utf-8 -*-
#Author: Marcos Golom
#Contact: viniciusgolom@gmail.com

import urllib2
import requests
import time
import datetime
import json
import urlparse
import joblib
import multiprocessing as mtp
from pathos.pools import ParallelPool as Pool
from functools import partial
from itertools import chain
from itertools import cycle
import pathos.pools as mp
from joblib import Parallel, delayed

class Cyclops:
    def __init__(self,authens,qt_threads=mtp.cpu_count()):
        self.clientAuths = authens
        self.client_id = self.clientAuths[0].get("client_id")          
        self.client_secret = self.clientAuths[0].get("client_secret")
        self.x_RateLimit_Limit = 5000
        self.x_RateLimit_Remaining = 0
        self.x_RateLimit_Reset = 0
        self.rollIndex = 0
        self.maxRollIndex = len(authens)
        self.num_threads = qt_threads
        

    def multiRequester(self,index,url):
        while True:
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(url,credencial)
            urlf2 = "{}&page={}".format(urlf,index)
            # print("{}&page={}").format(url,index)
            response = requests.get(urlf2)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            elif int(response.status_code) == 403:
                self.rollAuths()

        body = response.json()
        return body

    def requester(self,url):
        results_list = []
        while True:
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(url,credencial)
            response = requests.get(urlf)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            elif int(response.status_code) == 403:
                self.rollAuths()

        body = response.json()
        if body != []:
            results_list.append(self.byteify(body))
            return body
        else:
            final = []
            return final
    
    def requesterIssueComments(self,url):
        print("{}:{}").format(url.get("number"),url.get("url"))
        while True:
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(url.get("url"),credencial)
            response = requests.get(urlf)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            elif int(response.status_code) == 403:
                self.rollAuths()

        body = response.json()
        if body != []:
            aux = {
                "number":int(url.get("number")),
                "comments":body
            }
            return aux
        else:
            final = []
            return final
    
    def requesterCommitInfo(self,commit):
        # print("{} : {}").format("commit",commit.get("sha"))
        while True:
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(commit.get("url"),credencial) 
            response = requests.get(urlf)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            elif int(response.status_code) == 403:
                self.rollAuths()
        
        body = response.json()
        if body != []:
            aux = {
                "sha":commit.get("sha"),
                "commitInfo":body
            }
            return aux
        else:
            final = []
            return final

    def requesterPRInfo(self,pr):
        # print("{} : {}").format("Pull Request",pr.get("number"))
        while True:
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(pr.get("url"),credencial)
            response = requests.get(urlf)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            elif int(response.status_code) == 403:
                self.rollAuths()

        body = response.json()
        if body != []:
            aux = {
                "number":pr.get("number"),
                "prInfo":body
            }
            return aux
        else:
            final = []
            return final

    #get request of 1 page with many return pages
    def requestOne(self,url):
        results_list = []
        bodyEmpty = False
        #connection test and 
        while True:
            urlBase = "https://api.github.com/repos/mvgolom/letroca/commits"
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(urlBase,credencial)
            response = requests.get(urlf)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            if int(response.status_code) == 404:
                self.wait_for_internet_connection()
        
        numPages = self.getRange(url)
        p =  mp.ThreadPool(self.num_threads)
        if(numPages > 1):
            results_list = p.map(partial(self.multiRequester, url=url), range(1,numPages+1))
            # results_list = Parallel(n_jobs=self.num_threads)(delayed(unwrap_self)(url,x+1)for x in range(0,numPages))
        else:
            response = self.requester(url)
            if response != -1:
                results_list.append(self.byteify(response))
            else:
                bodyEmpty = True

        self.getRange(url)

        if bodyEmpty == False:
            response = list(chain.from_iterable(results_list[i] for i in xrange(len(results_list))))
            return response
        else:
            final = []
            return final 


    #get many pages with one return
    def requestMany(self,urlList,category):
        print "request Many in once ....."
        results_list = []
        bodyEmpty = False

        while True:
            urlBase = "https://api.github.com/repos/mvgolom/letroca/commits"
            credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
            urlf = ("{}{}").format(urlBase,credencial)
            response = requests.get(urlf)
            header = response.headers
            self.verifyRequestLimit(header)
            if int(response.status_code) == 200:
                break
            if int(response.status_code) == 404:
                self.wait_for_internet_connection()

        p =  mp.ThreadPool(self.num_threads)
        if(category == "issues"):
            try:
                results_list = p.map(self.requesterIssueComments, urlList)
            except TypeError,e:
                print urlList
                print 'I got a TypeError - reason "%s"' % str(e)
        elif(category == "commits"):
            try:
                results_list = p.map(self.requesterCommitInfo, urlList)
            except TypeError,e:
                print urlList
                print 'I got a TypeError - reason "%s"' % str(e)
        elif(category == "prs"):
            try:
                results_list = p.map(self.requesterPRInfo, urlList)
            except TypeError,e:
                print urlList
                print 'I got a TypeError - reason "%s"' % str(e)

        return results_list


    def getLimitRemaining(self,header):
        RateLimit_Remaining = 0
        for item in header.items():
            if 'x-ratelimit-remaining' in item:
                RateLimit_Remaining = int(item[1])
        return RateLimit_Remaining

    def getlimitReset(self):
        return self.x_RateLimit_Reset
    
    def getLimitRemaining(self,header):
        RateLimit_Remaining = header.get("X-RateLimit-Remaining")
        return int(RateLimit_Remaining)

    def rollAuths(self):
        print ("Credencials Updated !!!!!")
        print "[Cyclops] RateLimit Remaining: {}".format(self.x_RateLimit_Remaining)
        if self.rollIndex < (self.maxRollIndex-1):
            self.rollIndex += 1
            clientCredencials = self.clientAuths[self.rollIndex]
        else:
            self.rollIndex = 0
            clientCredencials = self.clientAuths[self.rollIndex]
        
        self.client_id = clientCredencials.get("client_id")
        self.client_secret = clientCredencials.get("client_secret")
        print ("{}:{}").format(self.client_id,self.client_secret)


    def verifyRequestLimit(self, header):
        self.x_RateLimit_Remaining = header.get("X-RateLimit-Remaining")
        self.x_RateLimit_Reset = header.get("X-ratelimit-reset")
        
        dateTimeFormat = '%Y-%m-%d %H:%M:%S'
        time_reset = datetime.datetime.fromtimestamp(
            float(self.x_RateLimit_Reset)).strftime(dateTimeFormat)
        
        datetime_now = datetime.datetime.now().strftime(dateTimeFormat)
        # print "[Cyclops] RateLimit Remaining: {}".format(self.x_RateLimit_Remaining)
        if int(self.x_RateLimit_Remaining) <= 50:
            while True:
                self.rollAuths()
                urlBase = "https://api.github.com/repos/mvgolom/letroca/commits"
                credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
                urlf = ("{}{}").format(urlBase,credencial)
                response = requests.get(urlf)
                header = response.headers
                remaining = self.getLimitRemaining(header)
                if remaining > 4500:
                    print ("Credencials Updated !!!!!")
                    break

    def getRange(self,url):
        credencial = '?client_id='+self.client_id+'&client_secret='+self.client_secret
        urlf = ("{}{}").format(url,credencial)
        response = urllib2.urlopen(urlf)
        header = response.info()
        return self.getPagesRange(header)

    #get number of pages
    def getPagesRange(self,header):
        page_range = ""
        if "link" in header:
            for item in header.items():
                if 'link' in item:
                    page_range = item[1]
            
            page_range = page_range.replace('; rel="last"','')
            page_range = page_range.replace(">",'')
            page_range = page_range.replace("<",'')
            page_range_link = page_range.split(",")

            link_components = urlparse.urlparse(page_range_link[1])
            link_components = urlparse.parse_qs(urlparse.urlsplit(page_range_link[1]).query)
            
            max_range = "".join(link_components.get("page"))
        else:
            max_range = 1
        
        return int(max_range)

    #clear unicode
    def byteify(self,input):
        if isinstance(input, dict):
            return {self.byteify(key): self.byteify(value)
                    for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    #connection handler
    def wait_for_internet_connection(self):
        while True:
            try:
                response = urllib2.urlopen('https://dns.google.com/resolve?name=example',timeout=1)
                return
            except urllib2.URLError:
                time.sleep(10)
                pass

if __name__ == '__main__':
    cyc = Cyclops(authentication)
    result = cyc.request("https://api.github.com/repos/davisking/dlib/issues")
    # print len(result)
    # for x in result:
    #     print x