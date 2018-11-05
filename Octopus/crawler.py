# -*- coding: utf-8 -*-
# Felipe Fronchetti

# Contributor: Marcos Vinicius Golom 
# Contact: viniciusgolom@gmail.com

try:
    import urllib2
    import time
    import datetime
    import requests
    import json
    import urlparse
    import multiprocessing as mtp
    import pathos.pools as mp
    from itertools import chain
    from itertools import cycle
    from pathos.pools import ParallelPool as Pool
    
    import sys
except ImportError as error:
    raise ImportError(error)

# < Crawler >
# This class is responsible for performing each API request.
# Our crawler uses OAuth2 authentication. Learn more at:
# https://developer.github.com/v3/oauth/


class Crawler:

    def __init__(self, authen, qt_threads=mtp.cpu_count()):
        print authen
        clientAuths = cycle(authen)
        clientInfo = next(clientAuths)
        self.credencials = clientAuths
        self.id = clientInfo["client_id"]
        self.secret = clientInfo["client_secret"]
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.num_threads = qt_threads

    # Makes the request using OAuth Client ID and Client Secret
    # Returns a json object with the requested data
    # https://developer.github.com/v3/#schema

    def request(self, request, parameters=None):
        try:
            if parameters is None:
                print 'Processing request: ' + request
                url = 'https://api.github.com/' + request + '?client_id=' + \
                    self.id + '&client_secret=' + self.secret
            else:
                print 'Processing request: ' + request + ' ' + str(parameters)
                url = 'https://api.github.com/' + request + '?client_id=' + self.id + \
                    '&client_secret=' + self.secret + \
                    '&' + '&'.join(parameters)

            if 'stargazer' in url:
                headers = {'Accept':'application/vnd.github.v3.star+json'}
                response = requests.get(url,headers=headers)
            else:
                response = requests.get(url)
            
            header = response.headers
            body = response.json()

            self.verify_rate_limit(header)

            return body

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
    
    # Makes the request using OAuth Client ID and Client Secret
    # Makes multithreading requests
    # Returns a json object with the requested data
    # https://developer.github.com/v3/#schema

    def request2(self, request, parameters=None):
        responses = []
        vetDivs = []
        results_list = []
        if(parameters != None):
            range_pages = self.range_max_verify(request,parameters)
        else:
            range_pages = self.range_max_verify(request)
        try:
            print range_pages
            print 'Processing request: ' + request
            
            url = 'https://api.github.com/' + request + '?client_id=' + \
                    self.id + '&client_secret=' + self.secret
    
            if (parameters != None) and ("page=" not in parameters[0]):
                print 'Processing request: ' + request + ' ' + str(parameters)
                url = url+"&"+"&".join(parameters)
            
            print url

            
            rate_limite = requests.get(url)
            header = rate_limite.headers
            self.verify_rate_limit(header)

            if(range_pages == 1 ):
                responses = self.requester(url)
                results_list.append(responses)
            else:
                link_vet = self.link_generator(url,range_pages)

                #fracionar vetor para a pool
                vetDivs = self.tuple_generator(range_pages)
                
                #pool of workers
                p =  mp.ThreadPool(self.num_threads)
                print len(link_vet)
                #minimize memory control 
                if (range_pages <= 100):
                    results_list = p.map(self.requester, link_vet)
                else:
                    for elem in vetDivs:
                        print 'Processing request: ' + str(elem[0]) + " -> " + str(elem[1])
                        subvet = link_vet[elem[0]:elem[1]]
                        aux = p.map(self.requester, subvet)
                        results_list.append(aux)
                
                #join requests list
                if (range_pages <= 100):
                    responses = list(chain.from_iterable(results_list[i] for i in xrange(len(results_list))))
                else:
                    aux1 = list(chain.from_iterable(results_list[i] for i in xrange(len(results_list))))
                    responses = list(chain.from_iterable(aux1[i] for i in xrange(len(aux1))))
        
            
            rate_limite = requests.get(url)
            header = rate_limite.headers
            self.verify_rate_limit(header)

            return responses
        
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


    def requester(self,url):
        if 'stargazer' in url:
            headers = {'Accept':'application/vnd.github.v3.star+json'}
            response = requests.get(url,headers=headers)
        else:
            response = requests.get(url)
        print url
        header = response.headers
        body = response.json()
        return body

    def tuple_generator(self,nrange):
        qtmaxpacket = 100
        fator = nrange / qtmaxpacket
        fator += 1
        ini = 0
        final = qtmaxpacket
        divsConf = []
        for j in xrange(fator):
            if final > nrange:
                x = [ini, nrange + 1]
            else:
                x = [ini, final]
            divsConf.append(x)
            ini = final
            final += qtmaxpacket
        return divsConf
    
    def link_generator(self,url,finalRange):
        link_list = []
        for page_number in xrange(finalRange):
            params = ['page=' + str(page_number+1)]
            urlf = url+"&"+"&".join(params)
            link_list.append(urlf)
        return link_list
    

    def range_max_verify(self, request,parameters=None):
        try:
            print 'Processing request: ' + request
            url = 'https://api.github.com/' + request + '?client_id=' + \
                self.id + '&client_secret=' + self.secret
            if(parameters!=None):
                url = url+"&"+"&".join(parameters)
            if 'stargazer' in url:
                request_header = urllib2.Request(url)
                request_header.add_header('Accept','application/vnd.github.v3.star+json')
                response = urllib2.urlopen(request_header)
            else:
                response = urllib2.urlopen(url)

            header = response.info()
            rangeMax = self.get_pages_range_max(header)
            
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

    # Verify if GitHub API requests limit is over. If it's, the crawler process goes sleep.
    # https://developer.github.com/v3/#rate-limiting

    def verify_rate_limit(self, header):
        self.rate_limit_remaining = header.get("X-RateLimit-Remaining")
        self.rate_limit_reset = header.get("X-ratelimit-reset")
        # for item in header.items():
        #     if 'x-ratelimit-remaining' in item:
        #         self.rate_limit_remaining = int(item[1])
        #     if 'x-ratelimit-reset' in item:
        #         self.rate_limit_reset = int(item[1])

        datetime_format = '%Y-%m-%d %H:%M:%S'
        # datetime_reset = datetime.datetime.fromtimestamp(float(self.rate_limit_reset)).strftime(datetime_format)
        # datetime_reset = datetime.datetime.fromtimestamp(float(self.x_RateLimit_Reset)).strftime(dateTimeFormat)
        datetime_now = datetime.datetime.now().strftime(datetime_format)

        print '[API] Requests Remaining:' + str(self.rate_limit_remaining)

        if self.rate_limit_remaining <= 50:
            clientCredencials = next(self.credencials)
            self.id = clientCredencials["client_id"]
            self.secret = clientCredencials["client_secret"]

    def get_rate_limit_remaining(self):
        return self.rate_limit_remaining

    def get_rate_limit_reset(self):
        return self.rate_limit_reset

    def get_pages_range_max(self,header):
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

    def wait_internet_connection(self, request, parameters):
        number_of_attempts = 0

        while number_of_attempts < 10:
            try:
                response = urllib2.urlopen('https://github.com', timeout=1)
                if response:
                    self.request(request, parameters)
                return
            except urllib2.URLError:
                number_of_attempts = number_of_attempts + 1
                print 'The connection does not seem to be working. Trying again. (' + str(number_of_attempts) + '/10)'
                time.sleep(30)
                pass
