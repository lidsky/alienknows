'use strict';

angular.module('articles').controller('ArticlesController', ['$scope', '$stateParams', '$location', 'Authentication', 'Articles',
	function($scope, $stateParams, $location, Authentication, Articles) {
		$scope.authentication = Authentication;
		$scope.articleList = [];



		var getCurrentUTC = function() {
			var curTime = (new Date()).getTime();
			return Math.round(curTime/1000);
		};
		$scope.lastArticleUTC = getCurrentUTC();

		$scope.create = function() {
			var article = new Articles({
				title: this.title,
				content: this.content
			});
			article.$save(function(response) {
				$location.path('articles/' + response._id);

				$scope.title = '';
				$scope.content = '';
			}, function(errorResponse) {
				$scope.error = errorResponse.data.message;
			});
		};

		$scope.remove = function(article) {
			if (article) {
				article.$remove();

				for (var i in $scope.articles) {
					if ($scope.articles[i] === article) {
						$scope.articles.splice(i, 1);
					}
				}
			} else {
				$scope.article.$remove(function() {
					$location.path('articles');
				});
			}
		};

		$scope.update = function() {
			var article = $scope.article;

			article.$update(function() {
				$location.path('articles/' + article._id);
			}, function(errorResponse) {
				$scope.error = errorResponse.data.message;
			});
		};

		$scope.find = function() {
			$scope.articles = Articles.query();
		};

		$scope.findOne = function() {
			$scope.article = Articles.get({
				articleId: $stateParams.articleId
			});
		};

		$scope.loadMore = function() {
			Articles.query({currentUtc: $scope.lastArticleUTC}, function(articles) {
				angular.forEach(articles, function(article, index) {
					if ($scope.articleList.indexOf(article) === -1) {
						$scope.articleList.push(article);
					} else {
						console.log('DUPLICATE!: ');
						console.log(article);
					}
				
				});

				$scope.lastArticleUTC = articles[articles.length - 1].saved_utc;

			});

		};



	}
]);