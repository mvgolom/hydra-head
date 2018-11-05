#!/usr/bin/python
# -*- coding: utf-8 -*-
#Author: Marcos Golom
#Contact: viniciusgolom@gmail.com

import time
import json
import joblib
import urllib2
import requests
import datetime
import urlparse
import multiprocessing as mtp
from itertools import chain
from itertools import cycle
from joblib import Parallel, delayed


authentication = []

"""Add here authetications"""
#authentication.append({"client_id":'',"client_secret":''})


clientAuths = cycle(authentication)
clientInfo = next(clientAuths)

rate_limit_remaining = 0
rate_limit_reset = 0

def range_max_verify(url):
    try:
        
        response = urllib2.urlopen(url)

        header = response.info()
        rangeMax = get_pages_range_max(header)
        
        return int(rangeMax)

    except urllib2.URLError as error:
        if 'HTTP Error 404' in error:
            self.wait_internet_connection(request, parameters)

        with open('error.log', 'a') as error_file:
            error_file.write('Found a error in request: \n')

            if parameters is None:
                error_file.write('https://api.github.com/' + request + 'client_id=' +
                                    self.id + '&client_secret=' + self.secret + '\n')
            else:
                error_file.write('https://api.github.com/' + request + '?client_id=' + self.id +
                                    '&client_secret=' + self.secret +
                                    '&' + '&'.join(parameters) + '\n')
            error_file.write('Error type: ' + str(error) + '\n\n')
        pass


def get_pages_range_max(header):
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
        
        max_range = "".join(link_components["page"])
    else:
        max_range = 1
    
    return int(max_range)

def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def requester(url,index):
    flag = False
    params = ['page=' + str(index)]
    urlf = url+"&"+"&".join(params)
    response = urllib2.urlopen(urlf)
    header = response.info()
    body = json.load(response)
    return body

def verify_rate_limit(header, name):
        global clientAuths
        global clientInfo
        global rate_limit_remaining
        global rate_limit_reset
        for item in header.items():
            if 'x-ratelimit-remaining' in item:
                rate_limit_remaining = int(item[1])
            if 'x-ratelimit-reset' in item:
                rate_limit_reset = int(item[1])

        datetime_format = '%Y-%m-%d %H:%M:%S'
        datetime_reset = datetime.datetime.fromtimestamp(rate_limit_reset).strftime(datetime_format)
        datetime_now = datetime.datetime.now().strftime(datetime_format)

        print '[API] Requests Remaining:' + str(rate_limit_remaining)

        if rate_limit_remaining <= 50:
            clientCredencials = next(clientAuths)
            clientAuths = clientCredencials
            return True
        else:
            return False

def getFollowers(name):
    global clientInfo
    auths = clientInfo
    bodyEmpty = False
    url = 'https://api.github.com/users/'+name+'/followers'+'?client_id='+auths["client_id"]+\
    '&client_secret='+auths["client_secret"]

    results_list = []

    response = urllib2.urlopen(url)

    header = response.info()
    num_pages = get_pages_range_max(header)

    
    if num_pages > 1:
        results_list = Parallel(n_jobs=mtp.cpu_count())(delayed(requester)(url,x+1)for x in range(0,num_pages))
        print len(results_list)
        flag = verify_rate_limit(header,name)
        if flag == True:
            url = 'https://api.github.com/users/'+name+'/following'+'?client_id='+clientInfo["client_id"]+\
                '&client_secret='+clientInfo["client_secret"]
    else:
        response = urllib2.urlopen(url)
        body = json.load(response)
        if body != []:
            results_list.append(byteify(body))
        else:
            bodyEmpty = True
    
    if bodyEmpty == False:
        followers = list(chain.from_iterable(results_list[i] for i in xrange(len(results_list))))
        return len(followers)
    else:
        return 0

def getFollowersLazy(name):
    print "followers -> {}".format(name)
    global clientInfo
    auths = clientInfo
    bodyEmpty = False

    url = 'https://api.github.com/users/'+name+'/followers'+'?client_id='+auths["client_id"]+\
    '&client_secret='+auths["client_secret"]

    results_list = []
    try:
        response = urllib2.urlopen(url)
    except urllib2.HTTPError, e:
        print e.fp.read()
        pass

    header = response.info()
    num_pages = get_pages_range_max(header)

    if(num_pages > 1):
        lastPage = num_pages
        fullPages = num_pages-1
        fullPages = fullPages*30

        params = ("page={}").format(lastPage)

        urlf = ("{}&{}").format(url,params)
        try:
            response = urllib2.urlopen(urlf)
        except urllib2.HTTPError, e:
            print e.fp.read()
            pass

        body = json.load(response)
        lastPageTam = len(body)
        countFinal = fullPages+lastPageTam
        aux = {"login":name,"followers":countFinal}
        return aux
    else:
        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            print e.fp.read()
            pass

        body = json.load(response)
        if body != []:
            aux = {"login":name,"followers":len(body)}
            return aux
        else:
            aux = {"login":name,"followers":0}
            return aux



def getFollowing(name):
    global clientInfo
    auths = clientInfo
    flag = False
    bodyEmpty = False
    url = 'https://api.github.com/users/'+name+'/following'+'?client_id='+auths["client_id"]+\
    '&client_secret='+auths["client_secret"]

    results_list = []

    response = urllib2.urlopen(url)

    header = response.info()
    num_pages = get_pages_range_max(header)

    print "qtd de pages: "+str(num_pages)
    if num_pages > 1:
        results_list = Parallel(n_jobs=mtp.cpu_count())(delayed(requester)(url,x+1)for x in range(0,num_pages))

        flag = verify_rate_limit(header,name)
        if flag == True:
            url = 'https://api.github.com/users/'+name+'/following'+'?client_id='+clientInfo["client_id"]+\
                '&client_secret='+clientInfo["client_secret"]
    else:
        response = urllib2.urlopen(url)
        body = json.load(response)
        if body != []:
            results_list.append(byteify(body))
        else:
            bodyEmpty = True
    if bodyEmpty == False:
        followings = list(chain.from_iterable(results_list[i] for i in xrange(len(results_list))))
        return byteify(followings)
    else:
        return 0

def getLogin(userObj):
    if userObj != "[]":
        try:
            login = userObj["login"]
            return login
        except KeyError, e:
            print 'I got a KeyError - reason "%s"' % str(e)
        except IndexError, e:
            print 'I got an IndexError - reason "%s"' % str(e)

def followingsList(login):
    followings = getFollowing(login)
    if followings != 0:
        results = Parallel(n_jobs=mtp.cpu_count())(delayed(getLogin)(x)for x in followings)
    else:
        results = 0
    
    return results 

def followers(login):
    followers = getFollowers(login)
    return followers

def followersList(listLogin):
    followersfinal = Parallel(n_jobs=mtp.cpu_count())(delayed(getFollowersLazy)(x["login"])for x in listLogin)
    aux = {}
    for x in followersfinal:
        aux[x["login"]] = x["followers"] 
    return aux

if __name__ == '__main__':
    name = "davisking"
    followers = getFollowersLazy("dunk-emesent")  
    # results = Parallel(n_jobs=4)(delayed(getLogin)(x)for x in followings)
    # print results
    print followers