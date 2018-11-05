#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import json
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client["global_metrics"]

allMetrics = list(db.projectMetrics.find({}))

for repoMetrics in allMetrics:
    projectName = repoMetrics.get("projectName")
    print projectName
    namerepo = ""
    if "." in projectName:
        namerepo = projectName.replace(".","")
        namerepo = namerepo.replace("/","#")
    else:
        namerepo = projectName.replace("/","#")
    
    arq2 = open("./results/repo-index.csv","a")
    arq = open("./results/"+namerepo+".csv","w")
    
    users = []

    committers = repoMetrics.get("committers")
    if committers != []:
        for committer in committers:
            users.append(committer)
    
    members = repoMetrics.get("members")
    if members != []:
        for member in members:
            users.append(member)
    
    collaborators = repoMetrics.get("collaborators")
    if collaborators != []:
        for collaborator in collaborators:
            users.append(collaborator)
    
    contributors = repoMetrics.get("contributors")
    if contributors != []:
        for contributor in contributors:
            users.append(contributor)
    
    owner = repoMetrics.get("owner")
    if owner != None:
        users.append(owner)

    for user in users:
        status = user.get("status")
        participationWComments = user.get("participationWComments")
        sourceOfLearning = user.get("sourceOfLearning")
        participationWcode = user.get("participationWcode")
        longTimeInteraction = user.get("longTimeInteraction")
        login = user.get("login")
        statusInProject = user.get("statusInProject")
        association = user.get("association")
        contentValueInProject = user.get("contentValueInProject")
        if((association == "OWNER") or (association == "MEMBER")):
            closeness = user.get("closeness")
            if closeness == None:
                closeness = 0
            else:
                closeness = closeness[0]
            
            arq.write(("{};{};{};{};{};{};{};{};{};{}\n".format(login,association,closeness,longTimeInteraction,status,statusInProject,contentValueInProject,sourceOfLearning,participationWcode,participationWComments)))
        else:
            arq.write(("{};{};{};{};{};{};{};{};{}\n".format(login,association,longTimeInteraction,status,statusInProject,contentValueInProject,sourceOfLearning,participationWcode,participationWComments)))
        
    arq2.write("{}".format(projectName))