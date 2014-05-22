function HistoryController($scope, $location, $modal, $http, $routeParams) {
	$scope.ordinal = {
		'Uninitialized':0,
		'Initialized':1,
		'Pending':2,
		'Queried':3,
		'Received':4,
		'Completed':5
	};
	$scope.readable = {
		'Uninitialized': 'Waiting for Server',
		'Initialized': 'Preparing Transaction',
		'Pending': 'Waiting for User Activity',
		'Queried': 'In Progress',
		'Received': 'Finalizing Transaction',
		'Completed': 'Transaction Completed'
	};
	($scope.reloadTransactions = function() {
		$scope.reloading = true;
		$http.get('/api/transactions/').success(function(data) {
			if(!angular.equals(data, $scope.transactions)) {
				$scope.transactions = data;
			}
			$scope.reloading = false;
		});
	})();
}

