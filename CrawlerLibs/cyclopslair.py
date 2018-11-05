#!/usr/bin/python
# -*- coding: utf-8 -*-
#Author: Marcos Golom
#Contact: viniciusgolom@gmail.com

import time
import json
import joblib
import cyclops
import urllib2
import requests
import datetime
import urlparse
import multiprocessing as mtp
from itertools import chain
from itertools import cycle
from pymongo import MongoClient
from joblib import Parallel, delayed


authentication = []

"""add here Authentication Keys this part need a lot of keys"""
#authentication.append({"client_id":'',"client_secret":''})


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

def getcommitsInfos(commit):
    if commit != None:
        commitInfo = commit.get("commitInfo")
        sha = commit.get("sha")

        author = ""
        authorAux = commitInfo.get("author")
        if authorAux != None:
            author = authorAux.get("login")
        else:
            author = authorAux
        
        committer = ""
        committerAux = commitInfo.get("committer")
        if committerAux != None:
            committer = committerAux.get("login")
        else:
            committer = committerAux
        
        
        filequantity = len(commitInfo.get("files"))
        deletions = commitInfo.get("stats").get("deletions")
        additions = commitInfo.get("stats").get("additions")
        totalModified = commitInfo.get("stats").get("total")
        if int(totalModified) > 0:
            contentValue = filequantity/totalModified
            contentValue = float(float(filequantity)/float(totalModified))
        else:
            contentValue = float(0)
        
        aux = {
            "sha":sha,
            "author":author,
            "committer":committer,
            "filequantity":filequantity,
            "deletions":deletions,
            "additions":additions,
            "totalModified":totalModified,
            "contentValue":contentValue
        }
        return aux
    else:
        print commit


def getprsInfos(pull):
    pr = pull.get("prInfo")
    author = ""
    authorAux = pr.get("user")
    if authorAux != None:
        author = authorAux.get("login")
    else:
        author = authorAux

    mergedby = ""
    mergedbyAux = pr.get("merged_by")
    if mergedbyAux != None:
            mergedby = mergedbyAux.get("login")
    else:
        mergedby = mergedbyAux
    
    number = pull.get("number")
    merged = pr.get("merged")
    filequantity = pr.get("changed_files")
    deletions = pr.get("deletions")
    additions = pr.get("additions")
    prState = pr.get("state")
    merge_commit_sha = pr.get("merge_commit_sha")
    created_at = pr.get("created_at")
    merged_at = pr.get("merged_at")
    totalModified = float(float(deletions)+float(additions))
    if totalModified > 0:
        contentValue = float(filequantity/totalModified)
    else:
        contentValue = float(0)
    aux = {
        "number":int(number),
        "author":author,
        "merged":merged,
        "mergedby":mergedby,
        "filequantity":filequantity,
        "deletions":deletions,
        "additions":additions,
        "prState":prState,
        "mergedInCommit":merge_commit_sha,
        "created_at":created_at,
        "merged_at":merged_at,
        "totalModified":totalModified,
        "contentValue":contentValue
    }
    return aux

def getIssuesCommentsOne(url,owner,repo):
    cyc = cyclops.Cyclops(authentication)
    result = cyc.requestOne(url)
    return result

def dictUrlNumber(issue):
    aux = {
        "number":int(issue.get("number")),
        "url":issue.get("comments_url")
    }
    return aux

def dictUrlCommit(commit):
    aux = {
        "sha":commit.get("sha"),
        "url":commit.get("url")
    }
    return aux

def dictUrlPRs(pr):
    aux = {
        "number":pr.get("number"),
        "url":pr.get("url")
    }
    return aux

def chunckGenerator(nrange):
    qtmaxpacket = 1000
    blockSizeMax = 1000
    fator = nrange / blockSizeMax
    fator += 1
    ini = 0
    final = blockSizeMax
    divsConf = []
    for j in xrange(fator):
        if final > nrange:
            x = [int(ini), int(nrange)]
        else:
            x = [int(ini), int(final)]
        divsConf.append(x)
        ini = final
        final += blockSizeMax
    return divsConf

def getIssuesCommentsList(issueList,owner,repo):
    cyc = cyclops.Cyclops(authentication)
    print "get Issues Comments List ......."
    urlList = Parallel(n_jobs=mtp.cpu_count())(delayed(dictUrlNumber)(x)for x in issueList)
    subArrays = chunckGenerator(len(issueList))
    arraySwap = []
    for index in subArrays:
        print("sub array {}:{}".format(index[0],index[1]))
        result = cyc.requestMany(urlList[index[0]:index[1]],"issues")
        arraySwap.append(result)
    response = list(chain.from_iterable(arraySwap[i] for i in xrange(len(arraySwap))))
    resultList = {}
    for item in response:
        if item != []:
            resultList[item.get("number")] = item.get("comments")

    return resultList

def getCommitInfoList(commitList,owner,repo):
    cyc = cyclops.Cyclops(authentication)
    print "get commits Info List ......."
    urlList = Parallel(n_jobs=mtp.cpu_count())(delayed(dictUrlCommit)(x)for x in commitList)
    subArrays = chunckGenerator(len(commitList))
    arraySwap = []
    for index in subArrays:
        print("sub array {}:{}".format(index[0],index[1]))
        result = cyc.requestMany(urlList[index[0]:index[1]],"commits")
        arraySwap.append(result)
    
    response = list(chain.from_iterable(arraySwap[i] for i in xrange(len(arraySwap))))
    commitsList = Parallel(n_jobs=mtp.cpu_count())(delayed(getcommitsInfos)(x)for x in response)
    return commitsList

def getPRInfoList(prList,owner,repo):
    cyc = cyclops.Cyclops(authentication)
    print "get commits Info List ......."
    urlList = Parallel(n_jobs=mtp.cpu_count())(delayed(dictUrlPRs)(x)for x in prList)
    subArrays = chunckGenerator(len(prList))
    
    arraySwap = []
    for index in subArrays:
        print("sub array {}:{}".format(index[0],index[1]))
        try:
            result = cyc.requestMany(urlList[int(index[0]):int(index[1])],"prs")
        except TypeError,e:
            print index
            print 'I got a TypeError - reason "%s"' % str(e)
        arraySwap.append(result)
    
    response = list(chain.from_iterable(arraySwap[i] for i in xrange(len(arraySwap))))
    print len(response)
    prsList = Parallel(n_jobs=mtp.cpu_count())(delayed(getprsInfos)(x)for x in response)
    return prsList


if __name__ == '__main__':
    client = MongoClient('localhost', 27017)
    name = "davisking/dlib"
    arg = name.split("/")
    owner = arg[0]
    namerepo = arg[1]
    db = client[arg[1]]
    
    issueList = list(db.issues.find({"comments": {"$exists":True,"$lt":31,"$gt":0}}).limit(20))
    
    resultList = getIssuesCommentsList(issueList,owner,namerepo)
    for issue in issueList:
        try:
            print ("{}:{}").format(issue.get("number"),resultList.get(issue.get("number")))
            db.issuesComments.insert({"number":issue.get("number"),"qtComments":issue.get("comments"),"comments":resultList.get(issue.get("number"))})
        except KeyError, e:
            print 'I got a KeyError - reason "%s"' % str(e)
        except IndexError, e:
            print issue.get("number")
            db.issuesComments.insert({"number":issue.get("number"),"qtComments":0,"comments":0})
            print 'I got an IndexError - reason "%s"' % str(e)