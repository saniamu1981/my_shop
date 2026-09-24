// Based On https://github.com/chrisdavidmills/push-api-demo/blob/283df97baf49a9e67705ed08354238b83ba7e9d3/main.js

var isPushEnabled = false,
    registration,
    subBtn;

// Возвращает реальную кнопку, если она есть на странице,
// или объект-заглушку, чтобы код не падал на страницах без кнопки
function safeBtn() {
  if (subBtn) return subBtn;
  return {
    textContent: '',
    disabled: false,
    dataset: {},
    addEventListener: function() {},
  };
}

window.addEventListener('load', function() {
  subBtn = document.getElementById('webpush-subscribe-button');

  // Работаем с кнопкой только если она есть на странице
  if (subBtn) {
    safeBtn().textContent = 'Подписаться на уведомления';
    safeBtn().addEventListener('click',
      function() {
        safeBtn().disabled = true;
        if (isPushEnabled) {
          return unsubscribe(registration);
        }
        return subscribe(registration);
      }
    );
  }

  // Do everything if the Browser Supports Service Worker
  if ('serviceWorker' in navigator) {
    const serviceWorker = document.querySelector('meta[name="service-worker-js"]').content;
    navigator.serviceWorker.register(serviceWorker).then(
      function(reg) {
        registration = reg;
        initialiseState(reg);
      });
  }
  // If service worker not supported, show warning to the message box
  else {
    showMessage(gettext('Service workers are not supported in your browser.'));
  }

  // Once the service worker is registered set the initial state
  function initialiseState(reg) {
    // Are Notifications supported in the service worker?
    if (!(reg.showNotification)) {
        // Show a message and activate the button
        showMessage('Ваш браузер не поддерживает показ уведомлений.');
        return;
    }

    // Check the current Notification permission.
    // If its denied, it's a permanent block until the
    // user changes the permission
    if (Notification.permission === 'denied') {
      safeBtn().disabled = false;
      showMessage('Уведомления заблокированы в вашем браузере.');
      return;
    }

    // Check if push messaging is supported
    if (!('PushManager' in window)) {
      // Show a message and activate the button
      safeBtn().disabled = false;
      showMessage('Уведомления недоступны в вашем браузере.');
      return;
    }

    // We need to get subscription state for push notifications and send the information to server
    reg.pushManager.getSubscription().then(
      function(subscription) {
        if (subscription){
          postSubscribeObj('subscribe', subscription,
            function(response) {
              // Check the information is saved successfully into server
              if (response.status === 201) {
                // Show unsubscribe button instead
                safeBtn().textContent = 'Отписаться от уведомлений';
                safeBtn().disabled = false;
                isPushEnabled = true;
                showMessage('Вы успешно подписались на уведомления.');
              }
            });
        }
      });
  }
}
);

function showMessage(message) {
  const messageBox = document.getElementById('webpush-message');
  if (messageBox) {
    messageBox.textContent = message;
    messageBox.style.display = 'block';
  }
}

function subscribe(reg) {
  // Get the Subscription or register one
  reg.pushManager.getSubscription().then(
    function(subscription) {
      var metaObj, applicationServerKey, options;
      // Check if Subscription is available
      if (subscription) {
        return subscription;
      }

      metaObj = document.querySelector('meta[name="django-webpush-vapid-key"]');
      applicationServerKey = metaObj.content;
      options = {
        userVisibleOnly: true
      };
      if (applicationServerKey){
        options.applicationServerKey = urlB64ToUint8Array(applicationServerKey)
      }
      // If not, register one
      reg.pushManager.subscribe(options)
        .then(
          function(subscription) {
            postSubscribeObj('subscribe', subscription,
              function(response) {
                // Check the information is saved successfully into server
                if (response.status === 201) {
                  // Show unsubscribe button instead
                  safeBtn().textContent = 'Отписаться от уведомлений';
                  safeBtn().disabled = false;
                  isPushEnabled = true;
                  showMessage('Вы успешно подписались на уведомления.');
                }
              });
          })
        .catch(
          function() {
            console.log('Ошибка при подписке на уведомления.', arguments);
          })
    }
  );
}

function urlB64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (var i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function unsubscribe(reg) {
  // Get the Subscription to unregister
  reg.pushManager.getSubscription()
    .then(
      function(subscription) {

        // Check we have a subscription to unsubscribe
        if (!subscription) {
          // No subscription object, so set the state
          // to allow the user to subscribe to push
          safeBtn().disabled = false;
          showMessage('Подписка недоступна.');
          return;
        }
        postSubscribeObj('unsubscribe', subscription,
          function(response) {
            // Check if the information is deleted from server
            if (response.status === 202) {
              // Get the Subscription
              // Remove the subscription
              subscription.unsubscribe()
                .then(
                  function(successful) {
                    safeBtn().textContent = 'Подписаться на уведомления';
                    showMessage('Вы отписались от уведомлений.');
                    isPushEnabled = false;
                    safeBtn().disabled = false;
                  }
                )
                .catch(
                  function(error) {
                    safeBtn().textContent = 'Отписаться от уведомлений';
                    showMessage('Ошибка при отписке от уведомлений.');
                    safeBtn().disabled = false;
                  }
                );
            }
          });
      }
    )
}

function postSubscribeObj(statusType, subscription, callback) {
  // Send the information to the server with fetch API.
  // the type of the request, the name of the user subscribing,
  // and the push subscription endpoint + key the server needs
  // to send push messages

  var browser = navigator.userAgent.match(/(firefox|msie|chrome|safari|trident)/ig)[0].toLowerCase(),
    user_agent = navigator.userAgent,
    data = {  status_type: statusType,
              subscription: subscription.toJSON(),
              browser: browser,
              user_agent: user_agent,
              group: safeBtn().dataset.group
           };

  fetch(safeBtn().dataset.url, {
    method: 'post',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data),
    credentials: 'include'
  }).then(callback);
}
