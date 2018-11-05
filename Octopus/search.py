# -*- coding: utf-8 -*-
# Author:  Felipe Fronchetti
# Contact: fronchettiemail@gmail.com

# Contributor: Marcos Vinicius Golom 
# Contact: viniciusgolom@gmail.com

# < Search >
# This class allows the developer to find repositories, commits, issues and users at GitHub
# Crawler = A crawler object. (Check crawler.py module)


class Search:
    def __init__(self, crawler):
        self.github = crawler

    # Gives a list of repositories based on keywords
    # https://developer.github.com/v3/search/#search-repositories

    def repositories(self, keywords=None, sort=None, order=None, page_range=None):
        parameters = []

        if keywords is not None:
            parameters.append('q=' + keywords)

            if sort is not None:
                parameters.append('sort=' + sort)

            if order is not None:
                parameters.append('order=' + order)

            if page_range is not None:
                repositories = []

                first_page = page_range[0]
                last_page = page_range[1]

                for page_number in range(first_page, last_page):
                    request = self.github.request(
                        'search/repositories', parameters + ['page=' + str(page_number)])
                    repositories.append(request)

                return repositories

            else:
                request = self.github.request(
                    'search/repositories', parameters)
                return request
        else:
            raise ValueError('Keywords have not been defined')

    def users(self, keywords=None):
        if keywords is not None:
            request = self.github.request(
                'users/'+keywords)
            user = request
            return user
        else:
            raise ValueError('User have not been defined')
