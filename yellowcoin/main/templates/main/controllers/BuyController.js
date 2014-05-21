function BuyController($scope, $http) {
	$scope.limitOrder = false;
	$scope.$watchCollection('[price, limitOrder]', function(v1, v2) {
		if(!$scope.limitOrder) {
			if($scope.transaction.sourceLock) {
				$scope.transaction.ask_subtotal = $scope.transaction.bid_subtotal / parseFloat($scope.price);
			} else {
				$scope.transaction.bid_subtotal = $scope.transaction.ask_subtotal * parseFloat($scope.price);
			}
		}
	});
	// written separately to prevent infinite recursion
	$scope.$watch('transaction.bid_subtotal', function(value) {
		if(!$scope.limitOrder && $scope.transaction.sourceLock) {
			$scope.transaction.ask_subtotal = value / parseFloat($scope.price);
		}
		if($scope.limitOrder) {
			$scope.transaction.exchange_rate = $scope.transaction.bid_subtotal / $scope.transaction.ask_subtotal;
		}
	});
	$scope.$watch('transaction.ask_subtotal', function(value) {
		if(!$scope.limitOrder && !$scope.transaction.sourceLock) {
			$scope.transaction.bid_subtotal = value * parseFloat($scope.price);
		}
		if($scope.limitOrder) {
			$scope.transaction.exchange_rate = $scope.transaction.bid_subtotal / $scope.transaction.ask_subtotal;
		}
	});
	$scope.$watch('transaction.exchange_rate', function(value) {
		if($scope.transaction.sourceLock) {
			$scope.transaction.ask_subtotal = $scope.transaction.bid_subtotal / value;
		} else {
			$scope.transaction.bid_subtotal = $scope.transaction.ask_subtotal * value;
		}
	});
	$scope.open = function($event) {
		$event.preventDefault();
		$event.stopPropagation();
		$scope.datepickerOpen = !$scope.datepickerOpen;
	};
	$scope.recurrence = {
		recur:false,
		repeat:{interval:7, unit:'Days'},
		starting:{date:'', time:''}
	};
	$scope.transaction = {
		bid_subtotal:0,
		ask_subtotal:0,
		withdrawal_account:null,
		deposit_account:null,
		comment:'',
		sourceLock:true,
		exchange_rate:0
	};
	$scope.execute = function() {
		$scope.transaction.bid_subtotal = Math.round($scope.transaction.bid_subtotal * 100000000) / 100000000;
		$scope.transaction.ask_subtotal = Math.round($scope.transaction.ask_subtotal * 100000000) / 100000000;
		$scope.transaction.pending = true;
		$http.post('/api/orders/' + $scope.askCurrency +'/' + $scope.bidCurrency + '/', {
			bid_subtotal:$scope.transaction.bid_subtotal,
			ask_subtotal:$scope.transaction.ask_subtotal,
			withdrawal_account:$scope.transaction.withdrawal_account,
			deposit_account:$scope.transaction.deposit_account,
			comment:$scope.transaction.comment
		}).success(function(data) {
			$scope.transaction.pending = false;
			$scope.showSuccess("Your order was successfully placed.");
		}).error(function(data) {
			$scope.transaction.errors = data.detail;
			$scope.transaction.pending = false;
		});
		if($scope.recurrence.recur && !$scope.limitOrder) {
			$http.post('/api/orders/templates/' + $scope.askCurrency + '/' + $scope.bidCurrency + '/', {
				withdrawal_account:$scope.transaction.withdrawal_account,
				deposit_account:$scope.transaction.deposit_account,
				type:($scope.transaction.sourceLock ? 'B' : 'A'),
				subtotal:($scope.transaction.sourceLock ? $scope.transaction.bid_subtotal : $scope.transaction.ask_subtotal)
			}).success(function(data) {
				var time = $scope.recurrence.repeat.interval;
				if($scope.recurrence.repeat.unit == 'Days') {
					time *= 86400;
				} else if($scope.recurrence.repeat.unit == 'Hours') {
					time *= 3600;
				} else if($scope.recurrence.repeat.unit == 'Months') {
					time *= 86400 * 30;
				} else if($scope.recurrence.repeat.unit == 'Years') {
					time *= 86400 * 365;
				}
				$http.post('/api/orders/recurring/', {
					template:data.id,
					interval:time,
					first_run:(new Date()).toISOString()
				});
			});
		}
	};
}

