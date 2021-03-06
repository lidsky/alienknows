'use strict';

angular.module('articles').directive('hoverMedia', [ '$compile', 
	function($compile) {
		/*
					video directive:
					1. check format .sfw .mp4
					2. contains '?'

					Don't append:
					1. hulu

					Rules:

					1. endswith .mp4, videos tag

			        <video  width="500" height="283" autoplay controls>     
		                <source src="http://content_us.fashiontube.com/103/ce41eaf4-6c5b-4402-bf47-3da69dfeb5c2/640x.mp4" type="video/mp4">
		            </video> 


					2.skip:
					a) endswith .sfw
					c) banned domain list ['']

					3.check:
					a) '?' in url? append '&': append '?'
					b) append: '&autoplay=true&autoPlay=true&autostart=true&autoStart=true'


					<object width="400" height="400" data=""></object>

		*/

		var validAutoplay = function(videoUrl) {
			return videoUrl.substring(videoUrl.length - 4) !== '.mp4' && 
						 videoUrl.substring(videoUrl.length - 4) !== '.swf' &&  
						 videoUrl.indexOf('hulu') === -1;
		};


		var autoplayUrl = function(videoUrl) {
			if (validAutoplay(videoUrl)) {
				if (videoUrl.indexOf('?') === -1) {
					return videoUrl + '?autoplay=true&autoPlay=true&autostart=true&autoStart=true' + '&output=embed';
				} else {
					return videoUrl + '&autoplay=true&autoPlay=true&autostart=true&autoStart=true' + '&output=embed';
				}
			} else {
				return videoUrl;
			}			
		};

		// ref 1: http://stackoverflow.com/questions/23065165/angularjs-directive-dynamic-templates
		// ref 2: http://onehungrymind.com/angularjs-dynamic-templates/ 
		var getTemplate = function(video, picture) {
			if (video) {
				if (video.substring(video.length - 4) === '.mp4') {
					console.log('in mp4 for url vid', video);
					return '<div class="preview-video"><video controls autoplay><source data-ng-src="{{article.video_preview}}" type="video/mp4"></video></div>';
				} else {
					return '<div class="preview-video"><object data-ng-attr-data="{{article.video_preview}}"></object></div>';
				}
			} else {
				return '';
			}
		};


		return {
			template: '<div></div>',
			restrict: 'E',
			scope: {
				article: '='
			},
			link: function postLink(scope, element, attrs) {

				if (!!scope.article.video_preview) {
					scope.article.video_preview = autoplayUrl(scope.article.video_preview);
					element.html(getTemplate(scope.article.picture_preview, scope.article.video_preview)).show();

					scope.$watch('article', function(newVal) {
						$compile(element.contents())(scope);
					});
				}

			}
		};
	}
]);