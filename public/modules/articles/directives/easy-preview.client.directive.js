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
				var imgElt = element.find('img');

				element.css('color','#428bca');

				console.log(imgElt.length)

				imgElt.css({
					color:'#428bca',
					border:'solid 1px #428bca', 
					'box-shadow': '0 0 7px #428bca'
				});
				

				element.bind('mouseover', function(){
					if (!scope.more) {
						element.css('cursor','progress');
					}
					var timeoutId = $timeout(function(){
						scope.$apply(function(){
							scope.more = true;
							element.css('color','rgb(180, 180, 180)');
							element.css('cursor','inherit');
							imgElt.css({
								color:'rgb(180, 180, 180)',
								border:'none', 
								'box-shadow': 'none'
							});
							

						});
					}, delay);

					element.bind('mouseout', function(){
						$timeout.cancel(timeoutId);
						element.css('cursor','inherit');
					});
					
				});
				


			}
		};
	}
]);