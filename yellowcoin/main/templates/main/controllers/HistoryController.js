function HistoryController($scope, $location, $modal, $http, $routeParams) {
	$scope.ordinal = {
		'Uninitialized':0,
		'Initialized':1,
		'Pending':2,
		'Queried':3,
		'Received':4,
		'Completed':5
	};
	($scope.reloadTransactions = function() {
		$scope.reloading = true;
		$http.get('/api/transactions/').success(function(data) {
			$scope.transactions = data;
			$scope.reloading = false;
		});
	})();
}

