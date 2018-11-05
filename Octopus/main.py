# -*- coding: utf-8 -*-
# Author:  Felipe Fronchetti
# Contact: fronchettiemail@gmail.com

try:
	import crawler as GitCrawler
	import repository as GitRepository
	import search as GitSearch
except ImportError as error:
	raise ImportError(error)

if __name__ == "__main__":
	# This code is just an axample of Octopus usage. You don't need to use this code to use our script.
	# To use Octopus, simply import our classes as imported above, and instantiate each one as necessary.

	# Retrieve your own client id and secret in this page: https://github.com/settings/applications/new
	client_id = '4246e027fcc217b24452'
	client_secret = '41abfc5154c8d46b46143ec39b2f2bb2f756c0ac'
	crawler = GitCrawler.Crawler(client_id,client_secret)

	# Usage of GitSearch
	search = GitSearch.Search(crawler)

	languages = ['C','C++','Clojure','CoffeeScript','Erlang','Go','Haskell','Java','JavaScript','Objective-C','Perl','PHP','Python','Ruby','Scala','TypeScript']


	# Usage of GitRepository
	repository_organization = 'npm'
	repository_name = 'npm'
	repository_object = GitRepository.Repository(repository_organization, repository_name, crawler)

	list_of_forks = repository_object.forks()
	list_of_stars = repository_object.stars()
	list_of_pulls = repository_object.pull_requests()

