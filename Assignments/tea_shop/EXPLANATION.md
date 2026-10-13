# Tea Shop Order Simulator — Explanation

1. Returning `"Ready"` inside the `setTimeout` callback does not return it from the outer `tea()` function; the outer function has already finished and returns `undefined`. See the **Incorrect timer return** demo in `static/app.js`.
2. A Promise is returned immediately in its pending state, while its fulfillment value or rejection reason becomes available later. See the Promise demo in `static/app.js`.
3. `await` pauses only the current `async` function until the awaited Promise settles; it does not freeze the browser or prevent the cashier from submitting another order. See the `await fetch(...)` call in the form submit handler in `static/app.js`.
4. A later order can finish first because each order has its own preparation deadline and status check. See `pollUntilFinished()` in `static/app.js` and `update_order_states()` in `app.py`.
5. Flask saves orders, their creation timestamps, and preparation deadlines in MySQL. When a status API is queried, the backend compares the deadline with the current time and persists Ready or Failed, so refreshing the browser does not reset the order. See `create_order()`, `list_orders()`, and `update_order_states()` in `app.py`.
6. A network failure or rejected Promise enters `catch`, but `fetch()` normally resolves even when the server responds with HTTP 400 or 500. The code checks `response.ok` and throws an error for unsuccessful HTTP responses. See the form submit handler and `loadOrders()` in `static/app.js`.
7. Flask validates the customer name, tea type, preparation duration, and failure flag before inserting an order. Invalid input receives HTTP 400 with JSON error details; a successful creation receives HTTP 201. See `create_order()` in `app.py`.
8. The activity log records order submissions, state transitions, errors, and demo results with browser timestamps. See `logActivity()` and `renderOrders()` in `static/app.js`.
