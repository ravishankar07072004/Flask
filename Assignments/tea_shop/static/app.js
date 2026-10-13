const form = document.querySelector("#order-form");
const formMessage = document.querySelector("#form-message");
const activityLog = document.querySelector("#activity-log");
const demoOutput = document.querySelector("#demo-output");

const orderElements = {
  Preparing: document.querySelector("#preparing-orders"),
  Ready: document.querySelector("#ready-orders"),
  Failed: document.querySelector("#failed-orders")
};
const countElements = {
  Preparing: document.querySelector("#preparing-count"),
  Ready: document.querySelector("#ready-count"),
  Failed: document.querySelector("#failed-count")
};
const knownStates = new Map();
const activePollers = new Set();

function timestamp() {
  return new Date().toLocaleTimeString();
}
function logActivity(message) {
  const li = document.createElement("li");
  const time = document.createElement("time");
  time.textContent = `[${timestamp()}]`;
  li.append(time, document.createTextNode(message));
  activityLog.prepend(li);
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[ch]);
}
function renderOrders(orders) {
  const grouped = { Preparing: [], Ready: [], Failed: [] };
  for (const order of orders) {
    if (grouped[order.status]) grouped[order.status].push(order);
    const old = knownStates.get(order.id);
    if (old && old !== order.status) {
      logActivity(`${order.order_number} changed from ${old} to ${order.status}. ${order.explanation || ""}`);
    }
    knownStates.set(order.id, order.status);
  }

  for (const state of Object.keys(grouped)) {
    countElements[state].textContent = grouped[state].length;
    const list = grouped[state];
    orderElements[state].innerHTML = list.length ? list.map(order => `
      <article class="order-item">
        <strong>#${escapeHtml(order.id)} · ${escapeHtml(order.customer_name)} <span>(${escapeHtml(order.order_number)})</span></strong>
        <p>${escapeHtml(order.tea_type)} tea · ${escapeHtml(order.preparation_seconds)} seconds</p>
        ${order.status === "Failed" ? `<p class="explanation">${escapeHtml(order.explanation || "Preparation failed.")}</p>` : ""}
        ${order.status === "Preparing" ? `<p>${order.simulate_failure ? "Failure simulation enabled" : "Preparing…"}</p>` : ""}
      </article>
    `).join("") : '<p class="empty">No orders</p>';
  }
}
async function loadOrders() {
  try {
    const response = await fetch("/api/orders");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderOrders(data.orders);
  } catch (error) {
    logActivity(`Could not load orders: ${error.message}`);
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  formMessage.textContent = "";

  const customerName = document.querySelector("#customer-name").value.trim();
  const teaType = document.querySelector("#tea-type").value;
  const seconds = Number(document.querySelector("#preparation-seconds").value);
  const simulateFailure = document.querySelector("#simulate-failure").checked;

  if (customerName.length < 2 || customerName.length > 50) {
    formMessage.textContent = "Customer name must contain 2–50 characters.";
    return;
  }
  if (!["Regular", "Ginger", "Green"].includes(teaType)) {
    formMessage.textContent = "Choose Regular, Ginger, or Green tea.";
    return;
  }
  if (![2, 4, 6].includes(seconds)) {
    formMessage.textContent = "Preparation time must be 2, 4, or 6 seconds.";
    return;
  }

  logActivity(`Order request sent for ${customerName} (${teaType}, ${seconds}s).`);
  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: customerName,
        tea_type: teaType,
        preparation_seconds: seconds,
        simulate_failure: simulateFailure
      })
    });
    const data = await response.json();
    if (!response.ok) {
      const details = data.fields ? Object.values(data.fields).join(" ") : "";
      throw new Error(details || data.error || `HTTP ${response.status}`);
    }
    const order = data.order;
    knownStates.set(order.id, "Preparing");
    logActivity(`${order.order_number} saved in MySQL. Status: Preparing.`);
    form.reset();
    await loadOrders();
    watchOrder(order.id);
  } catch (error) {
    formMessage.textContent = error.message || "Unable to save the order. Check Flask and MySQL.";
    logActivity(`Order submission error: ${formMessage.textContent}`);
  }
});

async function watchOrder(orderId) {
  if (activePollers.has(orderId)) return;
  activePollers.add(orderId);
  try {
    while (true) {
      await new Promise(resolve => setTimeout(resolve, 300));
      const response = await fetch(`/api/orders/${orderId}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      await loadOrders();
      if (data.order.status !== "Preparing") break;
    }
  } catch (error) {
    logActivity(`Status check for order ${orderId} failed: ${error.message}`);
  } finally {
    activePollers.delete(orderId);
  }
}

document.querySelector("#clear-log").addEventListener("click", () => {
  activityLog.replaceChildren();
  logActivity("Activity log cleared.");
});
document.querySelectorAll(".demo-button").forEach(button => {
  button.addEventListener("click", () => {
    const demo = button.dataset.demo;
    if (demo === "broken") {
      function tea() { setTimeout(() => { return "Ready"; }, 1000); }
      const result = tea();
      demoOutput.textContent = `Immediate result: ${result} (undefined). The timer callback's return is not returned by tea().`;
      logActivity(`Broken return demo: tea() immediately returned ${result}.`);
      setTimeout(() => logActivity("Broken return demo: timer callback ran later, but its return value was lost."), 1000);
    } else if (demo === "callback") {
      function tea(done) { setTimeout(() => done("Ready"), 1000); }
      demoOutput.textContent = "Callback scheduled; waiting for tea…";
      logActivity("Callback demo started.");
      tea(value => {
        demoOutput.textContent = `Callback received tea later: ${value}.`;
        logActivity(`Callback received tea later: ${value}.`);
      });
    } else if (demo === "promise") {
      demoOutput.textContent = "Promise created; waiting for .then()…";
      logActivity("Promise demo started.");
      new Promise(resolve => setTimeout(() => resolve("Ginger tea is ready"), 1000))
        .then(value => {
          demoOutput.textContent = `.then() received: ${value}.`;
          logActivity(`Promise .then(): ${value}.`);
        })
        .catch(error => {
          demoOutput.textContent = `Promise rejected: ${error.message}`;
          logActivity(`Promise demo failed: ${error.message}`);
        });
    }
  });
});

loadOrders();
setInterval(loadOrders, 1000);
