function ProfileController($scope, $http, $timeout) {
	$scope.notify = {{ notifications|safe }};
	$scope.limits = {{ limits|safe }};
	$scope.records = {{ login_records|safe }};
	$scope.oneClickErrors = {};
	$scope.working = false;
	var oneClickTemplateSubmitDelay = null;
	$scope.$watch('settings.one_click_order_template', function(value, old) {
		if(value == old) { return; }
		$scope.working = true;
		if(oneClickTemplateSubmitDelay) {
			$timeout.cancel(oneClickTemplateSubmitDelay);
		}
		oneClickTemplateSubmitDelay = $timeout(function() {
			$http.put('/api/orders/templates/{{ user.one_click_order_template.id }}/', $.extend({}, value, {
				bid_currency:$scope.bidCurrency,
				ask_currency:$scope.askCurrency,
			})).success(function() {
				$scope.oneClickErrors = {};
				$scope.working = false;
			}).error(function(data) {
				$scope.oneClickErrors = data;
				$scope.settings.one_click = false;
				$scope.working = false;
			});
		}, 1000);
	}, true);
	$scope.oneClickDisabled = function() {
		return !$.isEmptyObject($scope.oneClickErrors)
			|| $scope.settings.one_click_order_template.deposit_account == ''
			|| $scope.settings.one_click_order_template.withdrawal_account == '';
	};
	$scope.$watchCollection('[settings.two_factor_authentication, settings.api_access, settings.one_click]', function(value, old) { 
		if(value == old) { return; }
		$http.put('/api/settings/', {one_click:value[2], api_access:value[1], two_factor_authentication:value[0]});
	});


	var notificationSubmitDelay = null;
	$scope.$watch('notify', function(value, old) {
		if(value == old) { return; }
		$scope.working = true;
		if(notificationSubmitDelay) {
			$timeout.cancel(notificationSubmitDelay);
		}
		notificationsSubmitDelay = $timeout(function() {
			$http.put('/api/notifications/', $scope.notify).then(function() {
				$scope.working = false;
			});
		}, 1000);
	}, true);
	$scope.delta = {};
	$scope.deltaChanged = false;
	$scope.$watch('delta', $scope.evaluateDelta = function(value, old) {
		if(value == old) { return; }
		for(var key in value) {
			if(value[key] != $scope.user[key]) {
				$scope.deltaChanged = true;
				return;
			}
		}
		$scope.deltaChanged = false;
	}, true);
	$scope.saveChanges = function() {
		$("input").tooltip('destroy').parent().removeClass('has-error');
		if($scope.delta['password']) {
			if($("#new-password").val() != $("#new-password-confirm").val()) {
				$("#new-password-confirm").tooltip({trigger:'manual', title:"This doesn't match the password above."}).tooltip('show');
				return;
			}
		}
		$http.put('/api/profile/', $scope.delta).success(function(data) {
			$.extend(true, $scope.user, data);
			// must retain reference to object, can't do $scope.delta = {}
			for(var key in $scope.delta) {
				if(key == 'phone') {
					$scope.isTwoFactorAuthenticationEnabled = false;
				}
				delete $scope.delta[key];
			}
			$scope.$broadcast('clearEditing');
		}).error(function(data) {
			for(var error in data.detail) {
				$("#" + error).tooltip({trigger:'manual', tile:data.detail[error][0]}).tooltip('show').parent().addClass('has-error');
			}
		});
	};
	$scope.geocode = function(val) {
		return $http.get('http://maps.googleapis.com/maps/api/geocode/json', {
			params: {
				address:val,
				region:'us',
				sensor:false
			}
		}).then(function(res){
			var addresses = [];
			angular.forEach(res.data.results, function(item){
				if(item.types.indexOf('street_address') != -1) {
					addresses.push(item);
				}
			});
			return addresses;
		});
	};
	$scope.selectAddress = function($item, $model, $label) {
		for(var i = 0; i < $item.address_components.length; i++) {
			var component = $item.address_components[i];
			var types = component.types;
			if(types.indexOf('street_number') != -1) {
				$scope.delta.address1 = component.short_name;
			} else if(types.indexOf('route') != -1) {
				$scope.delta.address1 += ' ' + component.long_name;
			} else if(types.indexOf('locality') != -1) {
				$scope.delta.city = component.short_name;
			} else if(types.indexOf('administrative_area_level_1') != -1) {
				$scope.delta.state = component.short_name;
			} else if(types.indexOf('postal_code') != -1) {
				$scope.delta.zip = component.short_name;
			}
		}
	};
	function setStrength(str) {
		var $parent = $("#new-password").parent();
		$parent.removeClass('has-success has-warning has-error');
		if(str > 80) {
			$parent.addClass('has-success');
		} else if(str > 60) {
			$parent.addClass('has-warning');
		} else {
			$parent.addClass('has-error');
		}
	}
	function scorePassword(pass) {
	    var score = 0;
	    if (!pass)
	        return score;
	    var letters = new Object();
	    for (var i=0; i<pass.length; i++) {
	        letters[pass[i]] = (letters[pass[i]] || 0) + 1;
	        score += 5.0 / letters[pass[i]];
	    }

	    var variations = {
	        digits: /\d/.test(pass),
	        lower: /[a-z]/.test(pass),
	        upper: /[A-Z]/.test(pass),
	        nonWords: /\W/.test(pass),
	    }
	    variationCount = 0;
	    for (var check in variations) {
	        variationCount += (variations[check] == true) ? 1 : 0;
	    }
	    score += (variationCount - 1) * 10;
	    return parseInt(score);
	}
	$scope.invokePasswordMeter = function() {
		var $password = $("#new-password");
		var $confirm = $("#new-password-confirm");
		$password.keypress(function() {
			setStrength(scorePassword($password.val()));
		});
	};
}
app.directive('toggleSwitch', function () {
	return {
		restrict: 'EA',
		replace: true,
		scope: {
			model: '=',
			disabled: '@',
			onLabel: '@',
			offLabel: '@',
			knobLabel: '@'
		},
		template: '<div class="switch" ng-click="toggle()" ng-class="{ \'disabled\': disabled }"><div ng-class="{\'switch-off\': !model, \'switch-on\': model}"><span class="switch-left" ng-bind-html-unsafe="onLabel">On</span><span class="knob" ng-bind="knobLabel">&nbsp;</span><span class="switch-right" ng-bind-html-unsafe="offLabel">Off</span></div></div>',
		link: function ($scope, element, attrs) {
			attrs.$observe('onLabel', function(val) {
				$scope.onLabel = angular.isDefined(val) ? val : 'On';
			});

			attrs.$observe('offLabel', function(val) {
				$scope.offLabel = angular.isDefined(val) ? val : 'Off';
			});

			attrs.$observe('knobLabel', function(val) {
				$scope.knobLabel = angular.isDefined(val) ? val : '\u00A0';
			});

			attrs.$observe('disabled', function(val) {
				$scope.disabled = angular.isDefined(val) ? (val == 'false' ? false : true) : false;
			});

			$scope.toggle = function toggle() {
				if(!$scope.disabled) {
					element.children().addClass('switch-animate');
					$scope.model = !$scope.model;
				}
			};
		}
	};
});
app.directive('notification', function() {
	return {
		scope:{
			title:'@',
			attribute:'@',
			bind:'=notification'
		},
		template:'<div class="row"><div class="form-control-static col-xs-4">{[title]}</div>'
				+ '<div class="col-xs-4" ng-if="phoneEnabled"><div toggle-switch knob-label="SMS" model="notify.sms"></div></div>'
				+ '<div class="col-xs-4"><div toggle-switch knob-label="Email" model="notify.email"></div></div>'
			+ '</div>',
		link:function($scope, $element) {
			$element.addClass('checkbox');
			$scope.notify = {email:$scope.bind['email'][$scope.attribute], sms:$scope.bind['sms'][$scope.attribute]};
			$scope.$watch('notify', function(value, old) {
				for(var key in value) {
					$scope.bind[key][$scope.attribute] = value[key];
				}
			}, true);
			$scope.phoneEnabled = ($scope.$parent.user.phone && $scope.$parent.user.is_valid.phone);
		}
	}
});
app.directive('profileInput', function() {
	return {
		scope: {
			display:'=',
			title: '@',
			bind:'=profileInput',
			affects:'@',
			warning:'@',
			onOpen:'&'
		},
		transclude:true,
		template: '<div class="form-group row">'
			+ '<label class="col-sm-3 control-label">{[title]}</label>'
			+ '<div class="col-sm-7 form-control-static" ng-hide="editing">{[display || "Not set"]}'
			+ '&nbsp;<span class="label label-warning" ng-if="warning">{[warning]}</span></div>'
			+ '<div class="col-sm-7" ng-show="editing" ng-transclude></div>'
			+ '<div class="col-sm-2 form-control-static"><button ng-click="toggle()" class="btn btn-link">{[(editing ? "Cancel" : "Change")]}</button></div>'
			+ '</div>',
		link:function($scope, $element, $attrs) {
			$scope.editing = false;
			$scope.$on('clearEditing', function() { $scope.editing = false });
			$attrs.$observe('affects', function(value) {
				if(!angular.isDefined(value)) {
					// attempt to identify matches
					$scope.affects = [];
					var re = /ng-model="delta\.(.*?)"/g
					var str = $element.html();
					var match;
					while(match = re.exec(str)) {
						$scope.affects.push(match[1]);
					}
				} else {
					$scope.affects = $scope.$eval($scope.affects);
				}
			});
			($scope.reset = function() {
				angular.forEach($scope.affects, function(affect) {
					delete $scope.$parent.delta[affect];
					$scope.$parent.evaluateDelta(); // delete doesn't trigger a digest apparently
				});
			})();
			$scope.load = function() {
				angular.forEach($scope.affects, function(affect) {
					$scope.$parent.delta[affect] = $scope.bind[affect];
				});
			}
			$scope.toggle = function(){
				if($scope.editing) {
					$scope.reset();
				} else {
					$scope.load();
					if($scope.onOpen) {
						$scope.onOpen();
					}
				}
				$scope.editing = !$scope.editing;
			};
			$scope.$$nextSibling.delta = $scope.$parent.delta;
		}
	}
});
app.filter('tel', function() {
	return function(tel) {
		tel = (tel ? tel.toString() : tel);
		if(!tel) {
			return '';
		} else if(tel.length != 10) {
			return tel;
		} else {
			return '(' + tel.substring(0, 3) + ') ' + tel.substring(3, 6) + '-' + tel.substring(6);
		}
	};
});
