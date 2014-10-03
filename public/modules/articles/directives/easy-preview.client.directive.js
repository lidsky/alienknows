'use strict';

angular.module('articles').directive('easyPreview', ['$timeout',
	function($timeout) {
		return {
			template: '<span data-ng-transclude></span>',
			restrict: 'A',
			// replace:true,
			transclude: true,
			scope: {
				more: '=',
				delay: '='
			},
			link: function (scope, element, attrs) {
				// element.text('this is the easyPreview directive');
				var delay = scope.delay || 200;

				
				element.bind('mouseover', function(){
					if (!scope.more) {
						element.css('cursor','progress');
					}
					var timeoutId = $timeout(function(){
						scope.$apply(function(){
							element.css('cursor','default');
							scope.more = true;

						});
					}, delay);

					element.bind('mouseout', function(){
						$timeout.cancel(timeoutId);
						element.css('cursor','default');
					});


				});
				


			}
		};
	}
]);