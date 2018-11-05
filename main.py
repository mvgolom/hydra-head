#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import sys
import json
import time
import datetime
import requests
import unicodedata
import pathos.pools as mp
import pymongo as Pymongo
import multiprocessing as mtp
from itertools import chain
from collections import Counter
from pymongo import MongoClient
from joblib import Parallel, delayed
try:
    from Octopus import crawler, search, repository
except ImportError as error:
    raise ImportError(error)
try:
    from CrawlerLibs import follow, cyclopslair
except ImportError as error:
    raise ImportError(error)

authentication = []
"""add here authenticates keys"""
#authentication.append({"client_id":'',"client_secret":''})



projectUserAssociation = {"COMMITTER":"committers","MEMBER":"members","OWNER":"owner","CONTRIBUTOR":"contributors","COLLABORATOR":"collaborators"}


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

def getInfo(projetoName,authen):
    client = MongoClient('localhost', 27017)
    inicio = time.time()
    arg = projetoName.split("/")
    namerepo = ""
    if "." in arg[1]:
        namerepo = arg[1].replace(".","Dot")
    else:
        namerepo = arg[1]
    
    db = client[namerepo]

    stateClose = "closed"
    stateOpen = "open"

    crawlerP = crawler.Crawler(authen)

    repo_object = repository.Repository(arg[0], arg[1], crawlerP)
    
    commits = repo_object.commits()
    for item in commits:
        try:
            db.commits.insert(item)
        except TypeError, e:
            print 'I got a TypeError - reason "%s"' % str(e)
            pass
    
    pullRequestsOpen = repo_object.pull_requests(stateOpen)
    for item in pullRequestsOpen:
        try:
            db.pullrequests.insert(item)
        except TypeError, e:
            print 'I got a TypeError - reason "%s"' % str(e)
            pass

    pullRequestsClosed = repo_object.pull_requests(stateClose)
    for item in pullRequestsClosed:
        try:
            db.pullrequests.insert(item)
        except TypeError, e:
            print 'I got a TypeError - reason "%s"' % str(e)
            pass

    contributors = repo_object.contributors()
    for item in contributors:
        try:
            db.contributors.insert(item)
        except TypeError, e:
            print 'I got a TypeError - reason "%s"' % str(e)
            pass

    issuesOpen = repo_object.issues(stateOpen)
    for item in issuesOpen:
        try:
            db.issues.insert(item)
        except TypeError, e:
            print 'I got a TypeError - reason "%s"' % str(e)
            pass

    issuesClose = repo_object.issues(stateClose)
    for item in issuesClose:
        try:
            db.issues.insert(item)
        except TypeError, e:
            print 'I got a TypeError - reason "%s"' % str(e)
            pass
            


def getLoginAssociation(userObj):
    try:
        login = userObj.get("user").get("user").get("login")
        association = userObj.get("user").get("author_association")

        if association == "NONE":
            association = "COMMITTER"
        elif login == owner:
            association = "OWNER"
        aux ={
            "login":login,
            "association":association
        }
        return aux
    except KeyError, e:
        print ('I got a KeyError - reason "{}"').format(str(e))
    except IndexError, e:
        print 'I got an IndexError - reason "%s"' % str(e)


def getAllContributors(owner,repo):
    client = MongoClient('localhost', 27017)
    print "Get all Users ......."
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]
    cursor = list(db.contributors.find({},{"_id":0,"login":1}))
    
    userType = ["userAssociates","owner","members","contributors","collaborators","committers"]
    index_name = "uniqueLogin"
    for types in userType:
        my_collection = db2[types]
        my_collection.create_index([('login',1)], name=index_name, unique=True)
    
    
    for contributor in cursor:
        data = byteify(contributor)
        try:
            db2.committers.insert({"login":data.get("login"),"association":"COMMITTER"})
        except Pymongo.errors.DuplicateKeyError:
            continue
    
    final = db.pullrequests.aggregate([
    {"$sort": { "user.login": 1}}, 
    {"$group":{ 
        "_id": "$user.login", 
        "user": { "$last": "$$ROOT" } 
    }
    } 
    ],allowDiskUse=True)
    
    final = list(final)
    print "Extract Associations ....."
    results = Parallel(n_jobs=mtp.cpu_count())(delayed(getLoginAssociation)(x) for x in final)
    for user in results:
        login = str(user.get("login"))
        associ = user.get("association")
        try:
            association = user.get("association")
            login = login.strip()
            owner = owner.strip()
            if(login == owner):
                association = "OWNER"
            userDB = projectUserAssociation.get(association)
            db2[userDB].insert({"login":login,"association":associ})
            db2.userAssociates.insert({"login":login,"association":associ})
        except Pymongo.errors.DuplicateKeyError:
            continue

        userType = ["owner","members","contributors","collaborators"]
        for types in userType:
            aux = db2[types].find({})
            for x in aux:
                try:
                    db2.committers.delete_one({"login":x.get("login")})
                except Pymongo.errors.OperationFailure,e:
                    print e
                    continue
        

def getAllComments(owner,repo):
    client = MongoClient('localhost', 27017)
    db = client[repo]

    #get issues with range less than 30 elements
    allIssuesComments = list(db.issues.find({"comments": {"$exists":True,"$lt":31,"$gt":0}}))
    print len(allIssuesComments)
    resultList = cyclopslair.getIssuesCommentsList(allIssuesComments,owner,repo)
    for issue in allIssuesComments:
        issue["number"]
        try:
            db.issuesComments.insert({"number":issue.get("number"),"qtComments":issue.get("comments"),"comments":resultList.get(issue.get("number"))})
        except KeyError, e:
            print 'I got a KeyError - reason "%s"' % str(e)
        except IndexError, e:
            db.issuesComments.insert({"number":issue.get("number"),"qtComments":0,"comments":0})
            print 'I got an IndexError - reason "%s"' % str(e)
    
    #get issues with range great than 30 elements
    allIssuesComments = list(db.issues.find({"comments": {"$exists":True,"$gte":31}}))
    print len(allIssuesComments)
    for issue in allIssuesComments:
        resultList = cyclopslair.getIssuesCommentsOne(issue.get("comments_url"),owner,repo)
        db.issuesComments.insert({"number":issue.get("number"),"qtComments":issue.get("comments"),"comments":resultList})
    
    #get issues with 0 comments
    allIssuesComments = list(db.issues.find({"comments": {"$exists":True,"$eq":0}}))
    print len(allIssuesComments)
    for issue in allIssuesComments:
        db.issuesComments.insert({"number":issue.get("number"),"qtComments":0,"comments":0})

def getMentions(issueComments):
    pattern = re.compile(r"(\@\w*)")
    mentions = []
    participants = {}
    arrayParticipants = []
    comments = issueComments.get("comments")
    if comments != None:
        for comment in comments:
            aux = pattern.findall(comment.get("body"))
            if aux != []:
                mentions.append(aux)
            else:
                mentions.append(aux)

            try:
                if comment.get("user").get("login") in arrayParticipants:
                    aux = comment.get("user").get("login")
                    participants[aux] = participants[aux]+1
                else:
                    participants[comment["user"]["login"]] = 1
                    arrayParticipants.append(comment["user"]["login"])
            except KeyError, e:
                print 'I got a KeyError - reason "%s"' % str(e)
            except IndexError, e:
                print 'I got an IndexError - reason "%s"' % str(e)

        itemsMentions = list(chain.from_iterable(mentions[i] for i in xrange(len(mentions))))
        itemsAux = [i.replace('@', '') for i in itemsMentions]
        items = []
        for k in itemsAux:
            if k != "":
                items.append(k)
        
        item = {
            "number":issueComments.get("number"),
            "participants":participants,
            "mentions":items
        }
        return item

def getIssuesMentions(owner,repo):
    print "get Issues Mentions ......"
    client = MongoClient('localhost', 27017)
    db = client[repo]
    allIssueComments = list(db.issuesComments.find({"qtComments": {"$exists":True,"$gt":0}}))
    itemsComments = Parallel(n_jobs=mtp.cpu_count())(delayed(getMentions)(x)for x in allIssueComments)
    return itemsComments

def getAllCommentsTypes(owner,repo):
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]

    #All Commenters get here-------
    getAllComments(owner,repo)
    #------------------------------
    
    commentF = getIssuesMentions(owner,repo)
    for commentBox in commentF:
        if commentBox != None:
            try:
                if(commentBox["mentions"] != []):
                    db.issuesComments.update({"number":commentBox.get("number")},{"$set": {"mentions":commentBox.get("mentions")}})
                else:
                    db.issuesComments.update({"number":commentBox.get("number")},{"$set": {"mentions":0}})

                db.issuesComments.update({"number":commentBox.get("number")},{"$set": {"participants":commentBox.get("participants")}})
            except Pymongo.errors.OperationFailure,e:
                print e

def getlistUsers(owner,repo):
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]

    allUsers = []
    aux = []
    
    allcommitters = list(db2.committers.find({}))
    aux.append(allcommitters)
    allowner = list(db2.owner.find({}))
    aux.append(allowner)
    allcontributors = list(db2.contributors.find({}))
    aux.append(allcontributors)
    allmembers = list(db2.members.find({}))
    aux.append(allmembers)
    allcollaborators = list(db2.collaborators.find({}))
    aux.append(allcollaborators)
    allUsers = list(chain.from_iterable(aux[i] for i in xrange(len(aux))))
    return allUsers



def codeGetterInfo(owner,repo):
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]
    allCommits = list(db.commits.find({}))
    print len(allCommits)
    resultListCommit = cyclopslair.getCommitInfoList(allCommits,owner,repo)
    print len(resultListCommit)
    for commit in resultListCommit:
        db.commitsInfo.insert({"sha":commit.get("sha"),"author":commit.get("author"),"committer":commit.get("committer"),\
        "filequantity":commit.get("filequantity"),"deletions":commit.get("deletions"),"additions":commit.get("additions"),\
        "totalModified":commit.get("totalModified"),"contentValue":commit.get("contentValue")})
    
    allIssue = list(db.pullrequests.find({}))
    print len(allIssue)
    resultListIssues = cyclopslair.getPRInfoList(allIssue,owner,repo)
    for pr in resultListIssues:
        db.prInfo.insert({"number":pr.get("number"),"author":pr.get("author"),"merged":pr.get("merged"),\
        "mergedby":pr.get("mergedby"),"filequantity":pr.get("filequantity"),"deletions":pr.get("deletions"),"additions":pr.get("additions"),\
        "prState":pr.get("prState"),"mergedInCommit":pr.get("mergedInCommit"),"created_at":pr.get("created_at"),"merged_at":pr.get("merged_at"),\
        "totalModified":pr.get("totalModified"),"contentValue":pr.get("contentValue")})


#nao funciona sem a validacao certa, somente se o usuario pesquisado tiver instalado um app que vc criou
#https://developer.github.com/v3/users/followers/#check-if-one-user-follows-another
def closenessOwner(owner,repo):
    client = MongoClient('localhost', 27017)
    print("closeness in project .....")
    dbname = (repo+"_metrics")
    db = client[dbname]
    ownerList = db.owner.find_one({})
    members = list(db.members.find({},{"_id":0}))
    users = getlistUsers(owner,repo)
    allUsers = list(users)
    memberLen = len(members)
    ownerLen = 0
    if ownerList != None:
        ownerLen = 1
    
    if (ownerLen > 0) and (memberLen > 0):
        followings = follow.followingsList(ownerList.get("login"))
        if followings != 0:
            for user in allUsers:
                if user in followings:
                    db.owner.update({"login":ownerList.get("login")},{"$push":{"closeness":user}})
        else:
            db.owner.update({"login":ownerList.get("login")},{"$push":{"closeness":0}})

        memberList = byteify(list(members))
        for member in memberList:
            results = follow.followingsList(member.get("login"))
            if results != 0:
                followings = list(results)
                flag = False
                for user in allUsers:
                    if user in followings:
                        print("{}:{}").format(member.get("login"),user.get("login"))
                        flag = True
                        db.members.update({"login":member.get("login")},{"$push":{"closeness":user}})
                if(flag == False):
                    db.members.update({"login":member.get("login")},{"$push":{"closeness":0}})
            else:
                print("{}:{}").format(member.get("login"),0)
                db.members.update({"login":member.get("login")},{"$push":{"closeness":0}})

    elif(ownerLen > 0) and (memberLen == 0):
        followings = follow.followingsList(ownerList.get("login"))
        if followings != 0:
            for user in allUsers:
                if user in followings:
                    db.owner.update({"login":ownerList.get("login")},{"$push":{"closeness":user}})
        else:
            db.owner.update({"login":ownerList.get("login")},{"$push":{"closeness":0}})
    
    elif(ownerLen == 0) and (memberLen > 0):
        memberList = byteify(list(members))
        for member in memberList:
            results = follow.followingsList(member.get("login"))
            if results != 0:
                followings = list(results)
                flag = False
                for user in allUsers:
                    if user in followings:
                        print("{}:{}").format(member.get("login"),user.get("login"))
                        flag = True
                        db.members.update({"login":member.get("login")},{"$push":{"closeness":user}})
                if(flag == False):
                    db.members.update({"login":member.get("login")},{"$push":{"closeness":0}})
            else:
                print("{}:{}").format(member.get("login"),0)
                db.members.update({"login":member.get("login")},{"$push":{"closeness":0}})

def daysInProject(user,dbclient):
    commitlist = list(dbclient.commits.find({'author.login':user}).sort('commit.author.date', 1).limit(1))
    issuelist = list(dbclient.issues.find({'user.login':user}).sort('created_at', 1).limit(1))
    firstcommit = 0
    firstIssue = 0
    datenow = str(datetime.datetime.date(datetime.datetime.now()))
    d2 = datetime.datetime.strptime(datenow, "%Y-%m-%d")
    if len(commitlist) > 0:
        commit = commitlist[0]
        date1 = commit.get("commit").get("author").get("date")
        date1f = str(date1.split("T")[0])
        d1 = datetime.datetime.strptime(date1f, "%Y-%m-%d")
        firstcommit = abs((d2 - d1).days)
    
    if len(issuelist) > 0:
        issue = issuelist[0]
        date1 = issue.get("created_at")
        date1f = date1.split("T")[0]
        d1 = datetime.datetime.strptime(date1f, "%Y-%m-%d")
        firstIssue = abs((d2 - d1).days)
    
    if(firstcommit >= firstIssue):
        return firstcommit
    else:
        return firstIssue

def status(owner,repo):
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db2 = client[dbname]
    userList = getlistUsers(owner,repo)
    allUsers = list(userList)
    followers = follow.followersList(allUsers)
    for user in allUsers:
        print user["login"]
        followersqtd = followers[user["login"]]
        try:
            association = user.get("association")
            userDB = projectUserAssociation.get(association)
            db2[userDB].update({"login":user.get("login")},{"$set": {"status": followersqtd}})
        except Pymongo.errors.OperationFailure,e:
            print e


def sourceOfLearning(owner,repo):
    print("sourceOfLearning .....")
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]
    userMentions = {}
    userMentionsArray = []
    
    allUsers = getlistUsers(owner,repo)
    
    for user in allUsers:
        allMentionUser = list(db.issuesComments.find({"mentions":user.get("login")}))
        if len(allMentionUser) > 0:
            userlogin = user.get("login")
            for usermention in allMentionUser:
                mentionsN = usermention.get("mentions")
                occurrence = Counter(mentionsN)
                if userlogin in userMentionsArray:
                    value = occurrence.get(userlogin)
                    userMentions[userlogin] = userMentions[userlogin]+int(value)
                else:
                    userMentions[userlogin] = int(occurrence.get(userlogin))
                    userMentionsArray.append(userlogin)
            if userlogin in userMentionsArray:
                try:
                    association = user.get("association")
                    userDB = projectUserAssociation.get(association)
                    db2[userDB].update({"login":user.get("login")},{"$set": {"sourceOfLearning": userMentions.get(userlogin)}})
                except Pymongo.errors.OperationFailure,e:
                    print e
        else:
            try:
                print user.get("login")
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"sourceOfLearning": 0}})
            except Pymongo.errors.OperationFailure,e:
                print e



def ParticipationWcode(owner,repo):
    print ("participation With Comments .......")
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]
    allUsers = getlistUsers(owner,repo)
    for user in allUsers:
        allprOpen = list(db.pullrequests.find({"author.login":user.get("login")}))
        qtprOpen = len(allprOpen)
        allprClosed = list(db.prInfo.find({"mergedby":user.get("login")}))
        qtprClosed = len(allprClosed)
        ParticipationWcode = int(qtprClosed+qtprOpen)
        if ParticipationWcode > 0:
            try:
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"participationWcode": ParticipationWcode}})
            except Pymongo.errors.OperationFailure,e:
                print e
        else:
            try:
                print user.get("login")
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"participationWcode": 0}})
            except Pymongo.errors.OperationFailure,e:
                print e


def contentValueInProject(owner,repo):
    print ("content Value In Project .......")
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]

    
    userCommits = {}
    userCommitsArray = []

    allUsers = getlistUsers(owner,repo)

    for user in allUsers:
        allcommitsInfo = list(db.commitsInfo.find({"author":user.get("login")}))
        userlogin = user.get("login")
        for commitsInfo in allcommitsInfo:
            value = float(commitsInfo.get("contentValue"))
            
            if userlogin in userCommitsArray:
                userCommits[userlogin] = userCommits[userlogin]+value
            else:
                userCommits[userlogin] = float(value)
                userCommitsArray.append(userlogin)
            
        if userlogin in userCommitsArray:
            contentValueInProject = userCommits.get(userlogin)
            try:
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"contentValueInProject": contentValueInProject}})
            except Pymongo.errors.OperationFailure,e:
                print e
        else:
            try:
                print user.get("login")
                collect = user.get("association")
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"contentValueInProject": 0}})    
            except Pymongo.errors.OperationFailure,e:
                print e


def longTimeInteractionWproject(owner,repo):
    print ("long Time Interaction With Project .......")
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]
    allUsers = getlistUsers(owner,repo)
    global projectUserAssociation
    for user in allUsers:
        association = user.get("association")
        userDB = projectUserAssociation.get(association)
        userLogin = user.get("login")
        userAux = db2[userDB].find_one({"login":userLogin})
        if userAux != None:
            qtComments = userAux.get("participationWComments")
            qtCommits = len(list(db.commits.find({"author.login":userLogin})))
            actions = qtComments+qtCommits
            timeInRepo = daysInProject(userLogin,db)
            if(timeInRepo > 0):
                longTimeInteraction = float(actions)/float(timeInRepo)
            else:
                longTimeInteraction = 0
            db2[userDB].update({"login":userLogin},{"$set": {"longTimeInteraction": longTimeInteraction}})
        

        
def participationWComments(owner,repo):
    print ("participation With Comments .......")
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[repo]
    db2 = client[dbname]
    global projectUserAssociation

    userComments = {}
    userCommentsArray = []

    allUsers = getlistUsers(owner,repo)

    allCommentsUser = list(db.issuesComments.find({}))
    for usercomment in allCommentsUser:
        occurrence = usercomment.get("participants")
        if occurrence != None:
            occurrenceKeys = occurrence.keys()
            for userlogin in occurrenceKeys:
                if userlogin in userCommentsArray:
                    value = occurrence.get(userlogin)
                    userComments[userlogin] = userComments[userlogin]+int(value)
                else:
                    userComments[userlogin] = int(occurrence.get(userlogin))
                    userCommentsArray.append(userlogin)
    
    for user in allUsers:
        userlogin = user.get("login")
        if userlogin in userCommentsArray:
            try:
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"participationWComments": userComments.get(userlogin)}})
            except Pymongo.errors.OperationFailure,e:
                print e
        else:
            try:
                print user.get("login")
                collect = user.get("association")
                association = user.get("association")
                userDB = projectUserAssociation.get(association)
                db2[userDB].update({"login":user.get("login")},{"$set": {"participationWComments": 0}})
            except Pymongo.errors.OperationFailure,e:
                print e

def createInit(owner, repo):
    print("Create and Intializing ........")
    db_names = ["global_metrics","global_status"]
    conn = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    
    db = conn[repo]
    db2 = conn[dbname]
    
    db = conn[str(db_names[0])]
    for db_name in db_names:
        if bool(db_name in conn.database_names()):
            print "Base {} found".format(db_name)
        else:
            if ("global_status" == db_name):
                db = conn[db_name]
                index_name = "uniqueLogin"
                my_collection = db["global_status_names"]
                my_collection.create_index([('login',1)], name=index_name, unique=True)
                print "Base {} create".format(db_name)

            elif ("global_metrics" == db_name):
                db = conn[db_name]
                index_name = "uniqueProjectName"
                my_collection = db["projectMetrics"]
                my_collection.create_index([('projectName',1)], name=index_name, unique=True)
                print "Base {} create".format(db_name)

def statusGlobalSave(owner, repo):
    client = MongoClient('localhost', 27017)
    db4 = client["projects"]
    allUsers = getlistUsers(owner,namerepo)
    for user in allUsers:
        userLogin = user.get("login")
        db4 = client["global_status"]
        foundUser = db4.global_status_names.find_one({"login":userLogin})
        if foundUser != None:
            qtProject = foundUser.get("qtProject")
            qtProject = qtProject+1
            db4.global_status_names.update({"login":userLogin},{"$push":{"project":project}})
            db4.global_status_names.update({"login":userLogin},{"$set":{"qtProject":qtProject}})
        else:
            db4.global_status_names.insert_one({"login":user.get("login"),"qtProject":1})
            db4.global_status_names.update({"login":userLogin},{"$push":{"project":project}})

def archiveProject(owner, repo,rpname):
    client = MongoClient('localhost', 27017)
    dbname = (rpname+"_metrics")
    db = client[dbname]
    archiveRepos = client["global_metrics"]
    reponame = (owner+"/"+repo)
    collaborators = list(db.collaborators.find({}))
    committers = list(db.committers.find({}))
    contributors = list(db.contributors.find({}))
    members = list(db.members.find({}))
    owner = db.owner.find_one({})

    repository = {
        "projectName":reponame,
        "collaborators":collaborators,
        "committers":committers,
        "contributors":contributors,
        "members":members,
        "owner":owner
    }
    
    archiveRepos.projectMetrics.insert_one(repository)

    client.drop_database(dbname)
    client.drop_database(rpname)

def ownerSearch(ownerRepo,repo):
    client = MongoClient('localhost', 27017)
    dbname = (repo+"_metrics")
    db = client[dbname]
    global projectUserAssociation
    members = list(db.members.find({}))
    ownerList = list(db.owner.find({}))
    alluser = getlistUsers(owner,repo)
    if(len(members) == 0):
        if(len(ownerList) == 0):
            for user in alluser:
                login = user.get("login")
                association = user.get("association")
                dbName = projectUserAssociation[association]
                if login == ownerRepo:
                    auxUser = db[dbName].find_one({"login":login})
                    db[dbName].delete_one({"login":login})
                    auxUser["association"] = "OWNER"
                    db.owner.insert_one(auxUser)

def statusInProject():
    client = MongoClient('localhost', 27017)
    db = client["global_metrics"]
    db2 = client["global_status"]

    allMetrics = list(db.projectMetrics.find({}))
    
    auxstate = list(db2.global_status_names.find({}))
    auxStatusGlobal = []
    for projectState in auxstate:
         auxStatusGlobal.append(projectState.get("login"))

    statusGlobal = {}

    print len(allMetrics)
    print len(auxStatusGlobal)
    
    for status in auxstate:
        loginStatus = status.get("login")
        qtProject = status.get("qtProject")
        statusGlobal[loginStatus] = qtProject

    
    for repoMetrics in allMetrics:
        projectName = repoMetrics.get("projectName")
        committers = repoMetrics.get("committers")
        auxCommitters = []
        if committers != []:
            for committer in committers:
                committerlogin = committer.get("login")
                if committerlogin in auxStatusGlobal:
                    value = statusGlobal[committerlogin]
                    committer["statusInProject"] = value

                auxCommitters.append(committer)

        
        members = repoMetrics.get("members")
        auxMembers = []
        if members != []:
            for member in members:
                memberlogin = member.get("login")
                if memberlogin in auxStatusGlobal:
                    value = statusGlobal[memberlogin]
                    member["statusInProject"] = value

                auxMembers.append(member)
        
        collaborators = repoMetrics.get("collaborators")
        auxCollaborators = []
        if collaborators != []:
            for collaborator in collaborators:
                collaboratorlogin = collaborator.get("login")
                if collaboratorlogin in auxStatusGlobal:
                    value = statusGlobal[collaboratorlogin]
                    collaborator["statusInProject"] = value
                auxCollaborators.append(collaborator)
        
        contributors = repoMetrics.get("contributors")
        auxContributors = []
        if contributors != []:
            for contributor in contributors:
                contributorlogin = contributor.get("login")
                if contributorlogin in auxStatusGlobal:
                    value = statusGlobal[contributorlogin]
                    contributor["statusInProject"] = value
                
                auxContributors.append(contributor)
        
        owner = repoMetrics.get("owner")
        auxOwner = {}
        if owner != None:
            ownerlogin = owner.get("login") 
            if ownerlogin in auxStatusGlobal:
                value = statusGlobal[ownerlogin]
                owner["statusInProject"] = value
            auxOwner = owner
        else:
            auxOwner = None

        newProject = {
            "projectName":projectName,
            "members":auxMembers,
            "committers":auxCommitters,
            "contributors":auxContributors,
            "collaborators":auxCollaborators,
            "owner":auxOwner
        }

        db.projectMetrics.delete_one({"projectName":projectName})
        db.projectMetrics.insert_one(newProject)


if __name__ == '__main__':
    #owner/projectname
 
    client = MongoClient('localhost', 27017)
    db = client["projects"]
    createInit("davisking","dlib")
    
    projectsName = list(db.projectsNames.find({"visited":{"$eq":False}}).limit(1))

    # name = {"name":"davisking/dlib","visited":False}
    # projectsName = [name]

    for project in projectsName:
        name = project.get("name")
        arg = name.split("/")
        owner = arg[0]
        repo = arg[1]
        namerepo = ""
        flag404 = False
        if "." in arg[1]:
            namerepo = arg[1].replace(".","Dot")
        else:
            namerepo = arg[1]
        print "{}:{}".format(owner,namerepo)       

        now = datetime.datetime.now()
        print ("{}:{}:{}").format(now.hour,now.minute,now.second)
        url = ("https://api.github.com/repos/{}/{}/commits?client_id={}&client_secret={}").format(owner,repo,authentication[0].get("client_id"),authentication[0].get("client_secret"))
        rqt404 = requests.get(url)
        statusCode = int(rqt404.status_code)
        
        aux = rqt404.json()
        try:
            msg = aux.get("message")    
            if("is empty" in msg):
                flag404 = True
        except AttributeError, e:
            print ("AttributeError list")
            pass
        
        if (statusCode == 404):
            aux = rqt404.json()
            msg = aux.get("message")
            print msg
            if("Not Found" in msg):
                flag404 = True

        if(flag404 != True):
            """"Get All Commits,Issues,PRs and Contributors"""
            getInfo(name,authentication)
            """Get all Contributors, Owner, Members and Committers"""
            getAllContributors(owner,namerepo)
            ownerSearch(owner,namerepo)
            """Get All Comments in Repository Issues and PRs """
            getAllCommentsTypes(owner,namerepo)
            """Get Code Information """
            codeGetterInfo(owner,namerepo)
            print "Working in Metrics ....."

            closenessOwner(owner,namerepo)
            status(owner,namerepo)
            ParticipationWcode(owner,namerepo)
            participationWComments(owner,namerepo)
            contentValueInProject(owner,namerepo)
            sourceOfLearning(owner,namerepo)
            longTimeInteractionWproject(owner,namerepo)
            statusGlobalSave(owner,namerepo)
            archiveProject(owner,repo,namerepo)
            db.projectsNames.update({"name":name},{"$set":{"visited":True}})
        else:
            now = datetime.datetime.now()
            date = "{}:{}:{}".format(now.hour,now.minute,now.second)
            log = {
                "name": name,
                "date": date
            }
            with open("logNotFound.txt.json","a") as fp:
                json.dump(log, fp)
            db.projectsNames.update({"name":name},{"$set":{"visited":True}}) 
        

    # statusInProject()
    now = datetime.datetime.now()
    print ("{}:{}:{}").format(now.hour,now.minute,now.second)