'use strict';

/**
 * Module dependencies.
 */
var mongoose = require('mongoose'),
	errorHandler = require('./errors'),
	Article = mongoose.model('Article'),
	_ = require('lodash');

/**
 * Create a article
 */
exports.create = function(req, res) {
	var article = new Article(req.body);
	article.user = req.user;

	article.save(function(err) {
		if (err) {
			return res.status(400).send({
				message: errorHandler.getErrorMessage(err)
			});
		} else {
			res.jsonp(article);
		}
	});
};

/**
 * Show the current article
 */
exports.read = function(req, res) {
	res.jsonp(req.article);
};

/**
 * Update a article
 */
exports.update = function(req, res) {
	var article = req.article;

	article = _.extend(article, req.body);

	article.save(function(err) {
		if (err) {
			return res.status(400).send({
				message: errorHandler.getErrorMessage(err)
			});
		} else {
			res.jsonp(article);
		}
	});
};

/**
 * Delete an article
 */
exports.delete = function(req, res) {
	var article = req.article;

	article.remove(function(err) {
		if (err) {
			return res.status(400).send({
				message: errorHandler.getErrorMessage(err)
			});
		} else {
			res.jsonp(article);
		}
	});
};

/**
 * List of Articles
 */
exports.list = function(req, res) {
	console.log('here babi in article list');
	console.log('query....: ');
	console.log(req.query);

	if (!req.session.articles) {
		req.session.articles = [];
	}
	// console.log('after session');
	// console.log(req.session.articles);

	if (req.query.currentUtc) {
		Article.find({   $and: [{_id: {$nin: req.session.articles }}, {saved_utc: {$lt: parseInt(req.query.currentUtc)}}] })
		// Article.find({   $and: [{saved_utc: {$lt: parseInt(req.query.currentUtc)}}] })
			.sort('-saved_utc')
			.exec(function(err, articles) {
				if (err) {
					return res.status(400).send({
						message: errorHandler.getErrorMessage(err)
					});					
				} else {
					var minArticleNumber = Math.min(articles.length, 25);
					var newArticles = articles.slice(0,minArticleNumber);
					console.log('number of the OLD req.session.articles: ');
					console.log(req.session.articles.length);
					req.session.articles = req.session.articles.concat(_.map(newArticles, function(article) { return article._id; }));
					console.log('number of the NEW req.session.articles: ');
					console.log(req.session.articles.length);

					console.log('=========================================\n number of newArticles:');
					console.log(newArticles.length);

					res.jsonp(newArticles);
				}
			});
	} else {


		Article.find().sort('-created').populate('user', 'displayName').exec(function(err, articles) {
			if (err) {
				return res.status(400).send({
					message: errorHandler.getErrorMessage(err)
				});
			} else {
				res.jsonp(articles);
			}
		});

	}


};

/**
 * Article middleware
 */
exports.articleByID = function(req, res, next, id) {
	Article.findById(id).populate('user', 'displayName').exec(function(err, article) {
		if (err) return next(err);
		if (!article) return next(new Error('Failed to load article ' + id));
		req.article = article;
		next();
	});
};

/**
 * Article authorization middleware
 */
exports.hasAuthorization = function(req, res, next) {
	if (req.article.user.id !== req.user.id) {
		return res.status(403).send({
			message: 'User is not authorized'
		});
	}
	next();
};