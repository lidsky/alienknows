'use strict';

angular.module('articles').directive('easyPreview', ['$timeout',
	function($timeout) {
		return {
			template: '<span data-ng-transclude></span>',
			restrict: 'A',
			// replace:true,
			transclude: true,
			scope: {
				more: '='
			},
			link: function (scope, element, attrs) {
				// element.text('this is the easyPreview directive');


				if (!scope.more) {
					element.bind('mouseover', function(){
						var timeoutId = $timeout(function(){
							scope.$apply(function(){
								console.log('in directive easyPreview, scope more BEFORE: ', scope.more);
								scope.more = true;
								console.log('in directive easyPreview, scope more AFTER: ', scope.more);

							});
						}, 200);

						element.bind('mouseout', function(){
							$timeout.cancel(timeoutId);
						});


					});
				}


			}
		};
	}
]);